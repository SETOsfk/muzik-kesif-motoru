"""Aday medyası: kapak, sanatçı görseli ve ÇALINABİLİR bir parça.

## Neden gerekli

Ölçüldü (2026-09-23, seto'nun etkin çalışması): 621 adayın HİÇBİRİNDE kapak
yoktu, albüm adaylarının hiçbirinde önizleme yoktu. Keşfet destesi görsel ve
sesle karar verdirmek üzerine kurulu; ikisi de yoksa kart bir metin kutusuna
dönüşüyor ve "dinle, karar ver" döngüsü kırılıyor.

## Kaynak: Deezer'ın anahtarsız genel API'si

Önizlemede zaten kullanılıyor (bkz. `discover/onizleme.py`, K11). Üç uç:

- `track/{id}`            parça adayı: albüm kapağı + sanatçı fotoğrafı
- `search/album`          albüm adayı: albümü bul (sanatçı + albüm DOĞRULANIR)
- `album/{id}/tracks`     o albümün EN POPÜLER parçası (`rank`) çalınır

Kapak adresleri imzasız ve kalıcı (`cdn-images.dzcdn.net/images/cover/<md5>`),
saklanabilir. Önizleme adresi kısa ömürlü imzalı — SAKLANMAZ, yalnız çağrı
anında taze olarak döner (`taze_onizleme` ile aynı gerekçe).

## Doğrulama

Yanlış albümün kapağını göstermek, hiç göstermemekten kötü: kullanıcı görsele
bakıp karar veriyor. Albüm eşleşmesi `onizleme.py`'nin ölçülmüş kurallarıyla
denetleniyor (sanatçı normalize eşitlik/kapsama + albüm sözcük örtüşmesi ≥ 0,6);
geçemeyen sonuç "yok" sayılır ve kart görselsiz, dürüst bir yer tutucu gösterir.

## Maliyet

Aday başına en çok 2 çağrı; ham yanıtlar `onbellek.ApiIstemci` ile diskte
(K5). Sonuç `medya` tablosunda (paylaşımlı) tutulur — ikinci kullanıcı ya da
ikinci görüntüleme ağa hiç çıkmaz. Deezer'ın sınırı 5 sn'de 50 istek; burada
iki çağrı arası 0,15 sn ve tek kilit, yani sunucu iş parçacıkları arasında da
sınır aşılmaz.

Kullanım:
    python -m python.medya --calisma <id>      # etkin çalışmanın adaylarını ısıt
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.discover.onizleme import _album_uyuyor_mu, _uyuyor_mu
from python.onbellek import AgYok, ApiIstemci, IstekBasarisiz

#: Deezer: 5 saniyede 50 istek. 0,15 sn ≈ saniyede 6,6 — sınırın altında pay.
ISTEK_ARALIGI = 0.15

_KILIT = threading.Lock()
_ISTEMCI: ApiIstemci | None = None


def deezer_medya() -> ApiIstemci:
    """Paylaşılan istemci. Her çağrıda yenisi kurulursa hız sayacı sıfırlanır
    ve eşzamanlı istekler sınırı birlikte aşar (onizleme.py'de ölçülmüş hata)."""
    global _ISTEMCI
    if _ISTEMCI is None:
        _ISTEMCI = ApiIstemci(
            servis="deezer", temel_url="https://api.deezer.com",
            istek_araligi=ISTEK_ARALIGI, zaman_asimi=10.0, azami_deneme=2,
            basliklar={"User-Agent": "muzik-kesif-motoru/0.1"},
        )
    return _ISTEMCI


@dataclass
class Medya:
    kapak: str | None = None
    sanatci_gorsel: str | None = None
    parca_id: int | None = None
    parca_adi: str | None = None
    album_adi: str | None = None
    deezer_album: int | None = None
    #: Önerilen parça çalınamadığı için sanatçının başka parçası konuldu.
    yedek: int = 0
    #: Çağrı anında alınmış TAZE önizleme; veritabanına yazılmaz.
    onizleme: str | None = None

    @property
    def bulundu(self) -> bool:
        return bool(self.kapak or self.parca_id)


def _get(istemci: ApiIstemci, yol: str, params: dict | None = None,
         *, yenile: bool = False):
    with _KILIT:
        return istemci.get_json(yol, params or {}, yenile=yenile)


def parcadan(istemci: ApiIstemci, parca_id: int) -> Medya:
    """Parça adayı: kimlik zaten doğrulanmış (hasat anında), yalnız oku.

    `yenile=True`: yanıttaki önizleme imzası ancak taze çağrıda geçerli.
    Kapak alanları bu çağrıdan zaten geliyor, ayrı bir istek gerekmiyor.
    """
    bilgi = _get(istemci, f"track/{parca_id}", yenile=True) or {}
    if bilgi.get("error"):
        return Medya()
    album = bilgi.get("album") or {}
    sanatci = bilgi.get("artist") or {}
    medya = Medya(
        kapak=album.get("cover_xl") or album.get("cover_big"),
        sanatci_gorsel=sanatci.get("picture_xl") or sanatci.get("picture_big"),
        parca_id=int(parca_id), parca_adi=bilgi.get("title"),
        album_adi=album.get("title"), deezer_album=album.get("id"),
        onizleme=bilgi.get("preview") or None,
    )
    if not medya.onizleme and sanatci.get("id"):
        # Lisans yüzünden önizlemesi olmayan parçalar var (ölçüldü: Miki
        # Matsubara «Wash»). Sessiz kart "dinle, karar ver" döngüsünü
        # kesiyor; sanatçının en popüler ÇALINABİLİR parçası konur ve
        # `yedek=1` ile işaretlenir — arayüz "yerine şu çalıyor" der.
        enler = (_get(istemci, f"artist/{sanatci['id']}/top", {"limit": 10},
                      yenile=True) or {}).get("data", [])
        calinabilir = [p for p in enler if p.get("preview")]
        if calinabilir:
            p = calinabilir[0]
            medya.parca_id, medya.parca_adi = int(p["id"]), p.get("title")
            medya.onizleme, medya.yedek = p["preview"], 1
    return medya


def albumden(istemci: ApiIstemci, sanatci: str, album: str) -> Medya:
    """Albüm adayı: önce albümü DOĞRULAYARAK bul, sonra en popüler parçası.

    Aramada iki sorgu biçimi deneniyor. Deezer'ın gelişmiş sözdizimi
    (`artist:"x" album:"y"`) kesin ama katı — "Mint Jams" canlı kaydı
    "MINT JAMS(Live)" olarak geçiyor ve kaçıyor (ölçüldü). Düz sorgu gevşek;
    yanlışını doğrulama eliyor.
    """
    sorgular = (f'artist:"{sanatci}" album:"{album}"', f"{sanatci} {album}")
    bulunan = None
    for q in sorgular:
        govde = _get(istemci, "search/album", {"q": q, "limit": 10}) or {}
        for kayit in govde.get("data", []):
            if not _uyuyor_mu(sanatci, (kayit.get("artist") or {}).get("name", "")):
                continue
            if not _album_uyuyor_mu(album, kayit.get("title", "")):
                continue
            bulunan = kayit
            break
        if bulunan:
            break
    if not bulunan:
        return Medya()

    medya = Medya(
        kapak=bulunan.get("cover_xl") or bulunan.get("cover_big"),
        sanatci_gorsel=(bulunan.get("artist") or {}).get("picture_xl"),
        album_adi=bulunan.get("title"), deezer_album=bulunan.get("id"),
    )
    # En popüler parça: albümün "kancası". İlk parça çoğu zaman bir giriş
    # (intro) ve 30 saniyede albüm hakkında hiçbir şey söylemiyor.
    parcalar = (_get(istemci, f"album/{bulunan['id']}/tracks", {"limit": 50},
                     yenile=True) or {}).get("data", [])
    calinabilir = [p for p in parcalar if p.get("preview")]
    if calinabilir:
        en_iyi = max(calinabilir, key=lambda p: p.get("rank") or 0)
        medya.parca_id = int(en_iyi["id"])
        medya.parca_adi = en_iyi.get("title")
        medya.onizleme = en_iyi.get("preview")
    return medya


def medya_oku(conn: sqlite3.Connection, aday_id: str) -> dict | None:
    satir = conn.execute("SELECT * FROM medya WHERE aday_id = ?", (aday_id,)).fetchone()
    return dict(satir) if satir else None


def medya_yaz(conn: sqlite3.Connection, aday_id: str, medya: Medya) -> None:
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO medya
               (aday_id, kapak, sanatci_gorsel, parca_id, parca_adi, album_adi,
                deezer_album, yedek, durum, tarih)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (aday_id, medya.kapak, medya.sanatci_gorsel, medya.parca_id,
             medya.parca_adi, medya.album_adi, medya.deezer_album, medya.yedek,
             "bulundu" if medya.bulundu else "yok",
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )


def medya_coz(
    conn: sqlite3.Connection, aday: dict, *, istemci: ApiIstemci | None = None,
    taze: bool = True,
) -> dict:
    """Adayın medyası — tabloda varsa oradan, yoksa Deezer'dan.

    `aday`: en az `aday_id`, `artist`, `title`; parça adayında `parca_id`.
    `taze=True` ise çalınacak parçanın TAZE önizlemesi de döner (bir çağrı).
    Ağ yoksa ya da Deezer hata verirse sessizce "bulunamadı" döner; arayüz
    görselsiz yer tutucu gösterir, uygulama çalışmaya devam eder.
    """
    istemci = istemci or deezer_medya()
    kayitli = medya_oku(conn, aday["aday_id"])
    try:
        if kayitli is None:
            if aday.get("parca_id"):
                medya = parcadan(istemci, int(aday["parca_id"]))
            else:
                medya = albumden(istemci, aday["artist"], aday["title"])
            medya_yaz(conn, aday["aday_id"], medya)
            sonuc = asdict(medya)
        else:
            sonuc = {**kayitli, "onizleme": None}
            if taze and kayitli.get("parca_id"):
                bilgi = _get(istemci, f"track/{kayitli['parca_id']}", yenile=True) or {}
                sonuc["onizleme"] = bilgi.get("preview") or None
    except (AgYok, IstekBasarisiz, OSError, ValueError) as hata:
        print(f"[medya] {aday.get('aday_id')}: {type(hata).__name__}: {hata}",
              file=sys.stderr)
        sonuc = asdict(Medya()) if kayitli is None else {**kayitli, "onizleme": None}
    sonuc.pop("durum", None)
    sonuc.pop("tarih", None)
    sonuc["aday_id"] = aday["aday_id"]
    return sonuc


def calismayi_isit(conn: sqlite3.Connection, calisma_id: str,
                   limit: int | None = None) -> dict[str, int]:
    """Bir çalışmanın medyası olmayan adaylarını önceden çöz (CLI)."""
    sorgu = """
        SELECT a.aday_id, a.artist, a.title, MAX(a.parca_id) parca_id, MAX(a.skor) s
          FROM adaylar a LEFT JOIN medya m ON m.aday_id = a.aday_id
         WHERE a.calisma_id = ? AND m.aday_id IS NULL
         GROUP BY a.aday_id ORDER BY s DESC
    """
    satirlar = conn.execute(sorgu, (calisma_id,)).fetchall()
    if limit:
        satirlar = satirlar[:limit]
    sayac = {"bakilan": 0, "bulunan": 0}
    for satir in satirlar:
        sonuc = medya_coz(conn, dict(satir), taze=False)
        sayac["bakilan"] += 1
        sayac["bulunan"] += bool(sonuc.get("kapak") or sonuc.get("parca_id"))
        if sayac["bakilan"] % 25 == 0:
            print(f"  {sayac['bakilan']}/{len(satirlar)} · {sayac['bulunan']} bulundu",
                  file=sys.stderr)
    return sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Aday kapak/parça ısıtma.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--calisma", help="calisma_id (varsayılan: en yenisi)")
    ayristirici.add_argument("--limit", type=int)
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        calisma_id = args.calisma or conn.execute(
            "SELECT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 1"
        ).fetchone()[0]
        sayac = calismayi_isit(conn, calisma_id, args.limit)
    finally:
        conn.close()
    print(f"Bakılan aday: {sayac['bakilan']}, medyası bulunan: {sayac['bulunan']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
