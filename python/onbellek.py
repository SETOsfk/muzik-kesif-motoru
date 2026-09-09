"""Önbellekli ve rate-limitli HTTP istemcisi (K5).

Aynı sorgu iki kez ağa çıkmaz. Bu yalnızca nezaket değil, işin yürümesinin şartı:
MusicBrainz saniyede 1 istek veriyor, 2000 albümlük bir kütüphane yarım saat sürüyor.
Kümeleme parametreleriyle oynarken bu bedel tekrar ödenemez.

Boş sonuç da önbelleklenir — "bu albümün Discogs'ta karşılığı yok" bilgisi de
pahalıdır ve her çalıştırmada yeniden öğrenilmesi anlamsızdır.

Ağ bağlantısı olmadan çalıştırıldığında önbellekteki her şey yine kullanılabilir;
önbellekte olmayan istek `AgYok` hatası verir (`--cevrimdisi`).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

VARSAYILAN_ONBELLEK = Path("data/cache")


class AgYok(RuntimeError):
    """Çevrimdışı moddayız ve istek önbellekte değil."""


class IstekBasarisiz(RuntimeError):
    """Yeniden denemelere rağmen istek başarısız oldu."""


def _env(anahtar: str) -> str | None:
    """.env dosyasını (varsa) yükleyip ortam değişkenini oku."""
    if not _env.yuklendi:  # type: ignore[attr-defined]
        _env.yuklendi = True  # type: ignore[attr-defined]
        try:
            from dotenv import load_dotenv
        except ImportError:  # python-dotenv yoksa .env elle okunur
            dosya = Path(".env")
            if dosya.is_file():
                for satir in dosya.read_text(encoding="utf-8").splitlines():
                    satir = satir.strip()
                    if not satir or satir.startswith("#") or "=" not in satir:
                        continue
                    ad, _, deger = satir.partition("=")
                    os.environ.setdefault(ad.strip(), deger.strip())
        else:
            load_dotenv()
    return os.environ.get(anahtar) or None


_env.yuklendi = False  # type: ignore[attr-defined]


@dataclass
class Sayaclar:
    isabet: int = 0       # önbellekten
    istek: int = 0        # ağdan
    hata: int = 0

    def ozet(self) -> str:
        return f"önbellek isabeti: {self.isabet}, ağ isteği: {self.istek}, hata: {self.hata}"


@dataclass
class ApiIstemci:
    """Tek bir servis için önbellekli GET.

    istek_araligi: iki *ağ* isteği arasındaki asgari saniye. Önbellek isabetinde
    beklenmez — 2000 albümlük ikinci tur saniyeler içinde biter.
    """

    servis: str
    temel_url: str
    istek_araligi: float = 1.0
    basliklar: dict[str, str] = field(default_factory=dict)
    onbellek_kok: Path = VARSAYILAN_ONBELLEK
    cevrimdisi: bool = False
    azami_deneme: int = 4
    zaman_asimi: float = 30.0
    sayac: Sayaclar = field(default_factory=Sayaclar)
    _oturum: requests.Session | None = field(default=None, repr=False)
    _son_istek: float = field(default=0.0, repr=False)

    @property
    def oturum(self) -> requests.Session:
        if self._oturum is None:
            self._oturum = requests.Session()
            self._oturum.headers.update(self.basliklar)
        return self._oturum

    # ------------------------------------------------------------------ #
    # Önbellek
    # ------------------------------------------------------------------ #

    def _dosya(self, yol: str, params: dict[str, Any]) -> Path:
        ham = json.dumps([yol, sorted(params.items())], ensure_ascii=False, sort_keys=True)
        ozet = hashlib.sha1(ham.encode("utf-8")).hexdigest()
        # İki basamaklı alt klasör: tek dizinde on binlerce dosya olmasın.
        return self.onbellek_kok / self.servis / ozet[:2] / f"{ozet}.json"

    def onbellekte_mi(self, yol: str, params: dict[str, Any] | None = None) -> bool:
        return self._dosya(yol, params or {}).is_file()

    # ------------------------------------------------------------------ #
    # İstek
    # ------------------------------------------------------------------ #

    def _bekle(self) -> None:
        gecen = time.monotonic() - self._son_istek
        if gecen < self.istek_araligi:
            time.sleep(self.istek_araligi - gecen)
        self._son_istek = time.monotonic()

    def get_json(
        self,
        yol: str,
        params: dict[str, Any] | None = None,
        *,
        yenile: bool = False,
    ) -> Any:
        """JSON döndür. 404 → None (ve bu da önbelleklenir)."""
        params = params or {}
        dosya = self._dosya(yol, params)

        if dosya.is_file() and not yenile:
            self.sayac.isabet += 1
            return json.loads(dosya.read_text(encoding="utf-8"))["govde"]

        if self.cevrimdisi:
            raise AgYok(f"çevrimdışı mod, önbellekte yok: {self.servis} {yol} {params}")

        url = f"{self.temel_url.rstrip('/')}/{yol.lstrip('/')}"
        son_hata: Exception | None = None

        for deneme in range(1, self.azami_deneme + 1):
            self._bekle()
            try:
                yanit = self.oturum.get(url, params=params, timeout=self.zaman_asimi)
            except requests.RequestException as hata:
                son_hata = hata
                time.sleep(min(2 ** deneme, 30))
                continue

            if yanit.status_code == 404:
                self._yaz(dosya, url, params, 404, None)
                self.sayac.istek += 1
                return None

            # 403: Apple iTunes Search hız sınırını böyle bildiriyor (kalıcı bir
            # yetki hatası değil). Yeniden denenebilir sayılır; kalıcı olsaydı
            # denemeler tükenip IstekBasarisiz'e düşerdi zaten.
            if yanit.status_code in (403, 429, 500, 502, 503, 504):
                bekle = yanit.headers.get("Retry-After")
                time.sleep(float(bekle) if bekle and bekle.isdigit() else min(2 ** deneme, 30))
                son_hata = IstekBasarisiz(f"{yanit.status_code} {url}")
                continue

            if not yanit.ok:
                self.sayac.hata += 1
                raise IstekBasarisiz(f"{yanit.status_code} {url}: {yanit.text[:200]}")

            try:
                govde = yanit.json()
            except ValueError as hata:
                self.sayac.hata += 1
                raise IstekBasarisiz(f"JSON değil: {url}") from hata

            self._yaz(dosya, url, params, yanit.status_code, govde)
            self.sayac.istek += 1
            return govde

        self.sayac.hata += 1
        raise IstekBasarisiz(f"{self.azami_deneme} denemede alınamadı: {url}") from son_hata

    def _yaz(self, dosya: Path, url: str, params: dict, durum: int, govde: Any) -> None:
        dosya.parent.mkdir(parents=True, exist_ok=True)
        paket = {
            "url": url,
            "params": params,
            "durum": durum,
            "alinma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "govde": govde,
        }
        gecici = dosya.with_suffix(".tmp")
        gecici.write_text(json.dumps(paket, ensure_ascii=False), encoding="utf-8")
        gecici.replace(dosya)  # yarım dosya kalmasın


# --------------------------------------------------------------------------- #
# Hazır istemciler
# --------------------------------------------------------------------------- #

def musicbrainz(**kwargs) -> ApiIstemci:
    """MusicBrainz: saniyede 1 istek, user-agent zorunlu."""
    ajan = _env("MUSICBRAINZ_USER_AGENT") or "muzik-kesif-motoru/0.1 (ornek@ornek.com)"
    return ApiIstemci(
        servis="musicbrainz",
        temel_url="https://musicbrainz.org/ws/2",
        istek_araligi=1.05,
        basliklar={"User-Agent": ajan, "Accept": "application/json"},
        **kwargs,
    )


def discogs(**kwargs) -> ApiIstemci | None:
    """Discogs: token yoksa None döner — çağıran zenginleştirmeyi atlar."""
    token = _env("DISCOGS_TOKEN")
    if not token:
        return None
    return ApiIstemci(
        servis="discogs",
        temel_url="https://api.discogs.com",
        istek_araligi=1.1,  # token'lı kullanıcı: dakikada 60 istek
        basliklar={
            "User-Agent": _env("MUSICBRAINZ_USER_AGENT") or "muzik-kesif-motoru/0.1",
            "Authorization": f"Discogs token={token}",
        },
        **kwargs,
    )
