"""Spotify OAuth ve kütüphane okuma.

## Neden `onbellek.ApiIstemci` kullanılmıyor

`ApiIstemci` önbellek dosyasını **yol + parametre** özetiyle adlandırıyor;
`Authorization` başlığı anahtara girmiyor. Spotify'da her istek kullanıcıya
özel: iki kullanıcının `/v1/me` çağrısı aynı dosyaya düşer ve biri ötekinin
kütüphanesini görürdü. Bu yüzden burada önbelleksiz, doğrudan `requests`
kullanılıyor. (Aynı sınıf ağ hatası çok kullanıcılığa geçerken dört
`lru_cache` işlevinde yakalanmıştı — bkz. karar günlüğü.)

## Neden PKCE değil, klasik akış

Sunucu gizli anahtarı saklayabiliyor (`SPOTIFY_CLIENT_SECRET`), yani bu
"confidential client". Klasik Authorization Code akışı + kriptografik `state`
bu durumda yeterli ve Spotify'ın en iyi belgelenmiş yolu. PKCE'yi de eklemek
OAuth 2.1 ruhuna daha uygun olurdu; eklemedim çünkü gerçek bir Spotify
girişini ben sınayamıyorum (kullanıcı adına parola giremem) ve belgelenmemiş
bir bileşimin sınanmamış hâlde kalması riskli.

`state` CSRF'i durduruyor: saldırganın kendi yetki kodunu kurbanın oturumuna
enjekte etmesi (authorization code injection) ancak geçerli bir state
üretebilirse mümkün, o da sunucunun belleğinde duruyor.

## Kapsamlar

Yalnız arayüzün vaat ettiği kadarı isteniyor (`giris.html`: "kayıtlı
albümlerini, en çok dinlediğin sanatçıları ve son çaldıklarını okurum"):

- `user-library-read`        → kayıtlı albümler
- `user-top-read`            → en çok dinlenen sanatçılar
- `user-read-recently-played`→ son çalınanlar
- `user-read-email`          → hesap eşleme anahtarı (aşağıya bakınız)

E-posta şunun için: kullanıcı önce e-postayla hesap açtıysa ve sonra Spotify
ile bağlanırsa, iki hesabı ayırmak yerine aynı hesaba bağlamak gerekiyor.
Spotify kimliği tek başına bunu yapamaz — ilk bağlanışta ortak bir anahtar
lazım. Yazma kapsamı hiç istenmiyor: uygulama Spotify'da hiçbir şey
değiştirmiyor.
"""

from __future__ import annotations

import base64
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import requests

from python.onbellek import _env

YETKI_URL = "https://accounts.spotify.com/authorize"
JETON_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"

KAPSAMLAR = (
    "user-read-email",
    "user-library-read",
    "user-top-read",
    "user-read-recently-played",
)

#: Spotify panelindeki "Redirect URI" ile HARFİ HARFİNE aynı olmalı.
#: Yayına çıkınca ortam değişkeniyle https adresine çevrilecek.
VARSAYILAN_DONUS = "http://127.0.0.1:8800/giris/spotify/donus"

#: Yetki turu bu süre içinde bitmezse state düşer (kullanıcı sekmeyi açık
#: unutmuşsa yeniden başlar). Bellekte tutuluyor: beş kullanıcılı tek süreçli
#: uygulamada her yetki denemesi için veritabanına yazmak gereksiz.
DURUM_OMRU = 900.0

ZAMAN_ASIMI = 20.0

_durumlar: dict[str, float] = {}


class SpotifyHatasi(RuntimeError):
    """Spotify tarafı beklenen yanıtı vermedi."""


# --------------------------------------------------------------------------- #
# Yapılandırma
# --------------------------------------------------------------------------- #

def kimlik() -> str | None:
    return _env("SPOTIFY_CLIENT_ID")


def gizli_anahtar() -> str | None:
    return _env("SPOTIFY_CLIENT_SECRET")


def donus_adresi() -> str:
    return _env("KESIF_SPOTIFY_DONUS") or VARSAYILAN_DONUS


def yapilandirildi_mi() -> bool:
    return bool(kimlik() and gizli_anahtar())


# --------------------------------------------------------------------------- #
# Yetki turu
# --------------------------------------------------------------------------- #

def _durumlari_temizle(simdi: float) -> None:
    for durum, zaman in list(_durumlar.items()):
        if simdi - zaman > DURUM_OMRU:
            del _durumlar[durum]


def yetki_baslat() -> tuple[str, str]:
    """(yönlendirilecek_url, durum) döner."""
    if not yapilandirildi_mi():
        raise SpotifyHatasi("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET yok")

    simdi = time.monotonic()
    _durumlari_temizle(simdi)
    durum = secrets.token_urlsafe(32)
    _durumlar[durum] = simdi

    sorgu = urlencode({
        "client_id": kimlik(),
        "response_type": "code",
        "redirect_uri": donus_adresi(),
        "scope": " ".join(KAPSAMLAR),
        "state": durum,
        # Kullanıcı hesabı değiştirmek isterse Spotify'ın "zaten girişlisin"
        # kestirmesine takılmasın.
        "show_dialog": "true",
    })
    return f"{YETKI_URL}?{sorgu}", durum


def durum_gecerli_mi(durum: str | None) -> bool:
    """Durumu TÜKETİR: aynı state ikinci kez kullanılamaz (replay)."""
    if not durum:
        return False
    zaman = _durumlar.pop(durum, None)
    return zaman is not None and time.monotonic() - zaman <= DURUM_OMRU


def _temel_yetki() -> str:
    ham = f"{kimlik()}:{gizli_anahtar()}".encode("utf-8")
    return "Basic " + base64.b64encode(ham).decode("ascii")


def _jeton_iste(govde: dict[str, str]) -> dict[str, Any]:
    yanit = requests.post(
        JETON_URL, data=govde,
        headers={"Authorization": _temel_yetki(),
                 "Content-Type": "application/x-www-form-urlencoded"},
        timeout=ZAMAN_ASIMI,
    )
    if not yanit.ok:
        # Spotify hata gövdesi jeton TAŞIMAZ; yine de kullanıcıya gösterilmiyor,
        # yalnız günlüğe düşüyor (bkz. web/sunucu.py).
        raise SpotifyHatasi(f"jeton alınamadı ({yanit.status_code}): {yanit.text[:200]}")
    return yanit.json()


def jeton_al(kod: str) -> dict[str, Any]:
    """Yetki kodunu erişim + yenileme jetonuyla takas et."""
    return _jeton_iste({
        "grant_type": "authorization_code",
        "code": kod,
        "redirect_uri": donus_adresi(),
    })


def jeton_tazele(yenile_jetonu: str) -> dict[str, Any]:
    """Erişim jetonunu tazele.

    Spotify yanıtta YENİ bir `refresh_token` verebilir de vermeyebilir de;
    vermezse eskisi geçerli kalır. Çağıran taraf bunu varsaymamalı —
    `hesap.spotify_bagla` COALESCE ile eskisini koruyor.
    """
    return _jeton_iste({
        "grant_type": "refresh_token",
        "refresh_token": yenile_jetonu,
    })


# --------------------------------------------------------------------------- #
# API okuma
# --------------------------------------------------------------------------- #

def _get(erisim: str, yol: str, params: dict[str, Any] | None = None) -> Any:
    yanit = requests.get(
        f"{API_URL}/{yol.lstrip('/')}",
        params=params or {},
        headers={"Authorization": f"Bearer {erisim}"},
        timeout=ZAMAN_ASIMI,
    )
    if yanit.status_code == 401:
        raise SpotifyHatasi("erişim jetonu geçersiz ya da süresi dolmuş")
    if not yanit.ok:
        raise SpotifyHatasi(f"{yanit.status_code} {yol}: {yanit.text[:200]}")
    return yanit.json()


def ben(erisim: str) -> dict[str, Any]:
    """Kullanıcının Spotify kimliği, adı, e-postası."""
    veri = _get(erisim, "me")
    return {
        "spotify_id": veri.get("id"),
        "ad": veri.get("display_name") or veri.get("id"),
        "eposta": (veri.get("email") or "").strip().lower() or None,
    }


def _sayfalar(erisim: str, yol: str, params: dict[str, Any], azami: int):
    """Spotify sayfalamasını tüketir; en çok `azami` kayıt döner."""
    alinan = 0
    sonraki: str | None = None
    while alinan < azami:
        if sonraki is None:
            veri = _get(erisim, yol, {**params, "limit": min(50, azami - alinan),
                                      "offset": alinan})
        else:
            veri = requests.get(
                sonraki, headers={"Authorization": f"Bearer {erisim}"},
                timeout=ZAMAN_ASIMI).json()
        ogeler = veri.get("items") or []
        if not ogeler:
            return
        for oge in ogeler:
            yield oge
            alinan += 1
            if alinan >= azami:
                return
        sonraki = veri.get("next")
        if not sonraki:
            return


def kayitli_albumler(erisim: str, *, azami: int = 2000) -> list[dict[str, Any]]:
    """Kullanıcının kaydettiği albümler — kütüphanenin omurgası."""
    cikti = []
    for oge in _sayfalar(erisim, "me/albums", {}, azami):
        albom = oge.get("album") or {}
        sanatcilar = [s.get("name") for s in albom.get("artists") or [] if s.get("name")]
        if not (albom.get("name") and sanatcilar):
            continue
        cikti.append({
            "spotify_album_id": albom.get("id"),
            "sanatci": sanatcilar[0],
            "sanatcilar": sanatcilar,
            "album": albom.get("name"),
            "yil": (albom.get("release_date") or "")[:4] or None,
            "eklenme": oge.get("added_at"),
        })
    return cikti


def en_cok_sanatcilar(
    erisim: str, *, aralik: str = "medium_term", azami: int = 50,
) -> list[dict[str, Any]]:
    """`aralik`: short_term (~4 hafta) | medium_term (~6 ay) | long_term."""
    return [
        {"spotify_sanatci_id": s.get("id"), "sanatci": s.get("name"),
         "turler": s.get("genres") or [], "populerlik": s.get("popularity")}
        for s in _sayfalar(erisim, "me/top/artists", {"time_range": aralik}, azami)
        if s.get("name")
    ]


def son_calinanlar(erisim: str, *, azami: int = 50) -> list[dict[str, Any]]:
    """Son çalınanlar. Spotify bu uçta OFFSET kabul etmiyor, tek sayfa."""
    veri = _get(erisim, "me/player/recently-played", {"limit": min(50, azami)})
    cikti = []
    for oge in veri.get("items") or []:
        parca = oge.get("track") or {}
        sanatcilar = [s.get("name") for s in parca.get("artists") or [] if s.get("name")]
        if not (parca.get("name") and sanatcilar):
            continue
        cikti.append({
            "sanatci": sanatcilar[0], "parca": parca.get("name"),
            "album": (parca.get("album") or {}).get("name"),
            "calma_zamani": oge.get("played_at"),
        })
    return cikti
