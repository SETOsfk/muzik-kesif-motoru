"""Müzisyen fotoğrafı (kullanıcı isteği, 2026-09-28).

Müzisyen sayfası ve müzisyen destesi yüzsüzdü: yalnız sanatçıdan türeyen yer
tutucu. Albüm kapağı zaten Deezer'dan geliyor (`medya.py`); kişi için iki yol,
bu sırayla:

1. **MusicBrainz → Wikidata → Wikimedia Commons.** Kredideki kişi kimliği bir
   MusicBrainz MBID'siyse, MB kaydındaki Wikidata bağlantısı izlenir ve
   Wikidata'daki resim (P18) alınır. KİMLİKLE eşleşiyor, adla değil — aynı adlı
   iki kişi karışmaz. Commons görselleri açık lisanslı; kaynak sayfası
   (`sayfa`) arayüzde atıf olarak bağlanır.
2. **Deezer sanatçı araması, TAM ad eşitliği.** Birçok icracının kendi Deezer
   sayfası var. `medya.py`'nin kapsama kuralı burada GEVŞEK kalırdı ("Matt
   Cameron" ↔ "Matt Cameron Band"): yalnız normalize edilmiş ad birebir eşitse.

Hiçbiri tutmazsa "yok" yazılır ve `YENIDEN_DENE_GUN` sonra yeniden denenir;
arayüz yer tutucuyu gösterir. Yanlış kişinin yüzü, yüz olmamasından kötü.

Sonuç `kisi_gorsel` tablosunda (paylaşımlı): kişi bir kez çözülür, herkes
yararlanır. Görsel herkese açık veri olduğu için kullanıcılar arası sızıntı
sorunu yok (K20'nin sorusu soruldu).
"""

from __future__ import annotations

import re
import sqlite3
import sys
import threading
from datetime import datetime, timezone
from urllib.parse import quote

from python.metin import normalize_esleme
from python.onbellek import AgYok, ApiIstemci, IstekBasarisiz

YENIDEN_DENE_GUN = 7
GENISLIK = 400

_MBID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_QID = re.compile(r"/(Q\d+)$")

_KILIT = threading.Lock()
_ISTEMCILER: dict[str, ApiIstemci] = {}


def _istemci(ad: str) -> ApiIstemci:
    with _KILIT:
        if ad not in _ISTEMCILER:
            if ad == "musicbrainz":
                from python.onbellek import musicbrainz
                _ISTEMCILER[ad] = musicbrainz(zaman_asimi=10.0, azami_deneme=2)
            elif ad == "wikidata":
                _ISTEMCILER[ad] = ApiIstemci(
                    servis="wikidata", temel_url="https://www.wikidata.org",
                    istek_araligi=0.2, zaman_asimi=10.0, azami_deneme=2,
                    basliklar={"User-Agent": "muzik-kesif-motoru/0.1"})
            else:
                from python.medya import deezer_medya
                _ISTEMCILER[ad] = deezer_medya()
        return _ISTEMCILER[ad]


def commons_adresi(dosya: str, genislik: int = GENISLIK) -> tuple[str, str]:
    """Commons dosya adı → (küçük resim adresi, dosya sayfası)."""
    ad = dosya.replace(" ", "_")
    return (f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(ad)}?width={genislik}",
            f"https://commons.wikimedia.org/wiki/File:{quote(ad)}")


def wikidata_yolu(mbid: str, *, mb: ApiIstemci, wd: ApiIstemci) -> tuple[str, str] | None:
    """MBID → (görsel, sayfa) ya da None."""
    kayit = mb.get_json(f"artist/{mbid}", {"inc": "url-rels", "fmt": "json"}) or {}
    qid = None
    for iliski in kayit.get("relations", []):
        if iliski.get("type") == "wikidata":
            eslesme = _QID.search((iliski.get("url") or {}).get("resource", ""))
            if eslesme:
                qid = eslesme.group(1)
                break
    if not qid:
        return None
    varlik = (wd.get_json(f"wiki/Special:EntityData/{qid}.json") or {}).get("entities", {})
    iddialar = (varlik.get(qid) or next(iter(varlik.values()), {})).get("claims", {})
    for iddia in iddialar.get("P18", []):
        dosya = ((iddia.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(dosya, str) and dosya:
            return commons_adresi(dosya)
    return None


def deezer_yolu(ad: str, *, dz: ApiIstemci) -> tuple[str, str] | None:
    """Tam ad eşitliğiyle Deezer sanatçı fotoğrafı."""
    from python.medya import _gercek_gorsel

    hedef = normalize_esleme(ad)
    for aday in (dz.get_json("search/artist", {"q": ad, "limit": 5}) or {}).get("data", []):
        if normalize_esleme(aday.get("name", "")) != hedef:
            continue
        gorsel = _gercek_gorsel(aday.get("picture_big") or aday.get("picture_medium"))
        if gorsel:
            return gorsel, aday.get("link") or ""
    return None


def oku(conn: sqlite3.Connection, anahtar: str) -> dict | None:
    satir = conn.execute("SELECT * FROM kisi_gorsel WHERE anahtar = ?", (anahtar,)).fetchone()
    return dict(satir) if satir else None


def okunanlar(conn: sqlite3.Connection, anahtarlar: list[str]) -> dict[str, str]:
    """Çözülmüş görseller (ağsız) — liste çizerken tek sorgu."""
    if not anahtarlar:
        return {}
    yer = ",".join("?" * len(anahtarlar))
    return {r[0]: r[1] for r in conn.execute(
        f"SELECT anahtar, gorsel FROM kisi_gorsel WHERE gorsel IS NOT NULL AND anahtar IN ({yer})",
        anahtarlar)}


def _yaz(conn: sqlite3.Connection, anahtar: str, sonuc: tuple[str, str] | None, kaynak: str | None) -> None:
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO kisi_gorsel (anahtar, gorsel, kaynak, sayfa, durum, tarih) "
            "VALUES (?,?,?,?,?,?)",
            (anahtar, sonuc[0] if sonuc else None, kaynak, sonuc[1] if sonuc else None,
             "bulundu" if sonuc else "yok",
             datetime.now(timezone.utc).isoformat(timespec="seconds")))


def _taze_mi(kayit: dict) -> bool:
    if kayit.get("gorsel"):
        return True
    try:
        tarih = datetime.fromisoformat(kayit["tarih"])
    except (KeyError, TypeError, ValueError):
        return False
    return (datetime.now(timezone.utc) - tarih).days < YENIDEN_DENE_GUN


def kimlikler(conn: sqlite3.Connection, anahtar: str) -> tuple[str | None, list[str]]:
    """Profil anahtarının görünen adı ve MusicBrainz kimlikleri (kredilerden)."""
    from python.enrich.kisi_birlestir import eslesmeleri_oku

    eslesme = eslesmeleri_oku(conn)
    ad, mbidler = None, []
    for kimlik, isim in conn.execute("SELECT DISTINCT person_id, person_name FROM credits"):
        a = normalize_esleme(isim or "")
        if eslesme.get(a, a) != anahtar:
            continue
        ad = ad or isim
        if kimlik and _MBID.match(kimlik) and kimlik not in mbidler:
            mbidler.append(kimlik)
    return ad, mbidler


def coz(conn: sqlite3.Connection, anahtar: str, *, mb: ApiIstemci | None = None,
        wd: ApiIstemci | None = None, dz: ApiIstemci | None = None) -> dict | None:
    """Kişinin görseli — tabloda varsa oradan, yoksa ağdan. Yoksa None."""
    kayit = oku(conn, anahtar)
    if kayit and _taze_mi(kayit):
        return kayit if kayit.get("gorsel") else None
    ad, mbidler = kimlikler(conn, anahtar)
    if not ad:
        return None
    sonuc = kaynak = None
    try:
        for mbid in mbidler[:2]:
            sonuc = wikidata_yolu(mbid, mb=mb or _istemci("musicbrainz"),
                                  wd=wd or _istemci("wikidata"))
            if sonuc:
                kaynak = "wikidata"
                break
        if not sonuc:
            sonuc = deezer_yolu(ad, dz=dz or _istemci("deezer"))
            kaynak = "deezer" if sonuc else None
    except (AgYok, IstekBasarisiz, OSError, ValueError) as hata:
        # Ağ hatası "yok" diye yazılmaz: bir sonraki istekte yeniden denenir.
        print(f"[kisi_gorsel] {anahtar}: {type(hata).__name__}: {hata}", file=sys.stderr)
        return None
    _yaz(conn, anahtar, sonuc, kaynak)
    return oku(conn, anahtar) if sonuc else None
