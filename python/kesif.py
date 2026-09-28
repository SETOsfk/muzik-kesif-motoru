"""Keşfet destesi ve Listem — kaydırarak karar, edinme listesi, liste analizi.

## Neden bir deste

README'nin kendi tespiti: "En yüksek getirili adım daha fazla geri bildirim."
Öneriler sayfası sanatçı kartlarını alt alta diziyor; karar vermek için
okumak, kaydırmak, doğru düğmeyi bulmak gerekiyor. Ölçüldü: 23 günde 129
karar. Deste aynı kararı TEK HAREKETE indiriyor (sağ = listeye, sol = geç,
yukarı = zaten biliyorum) ve kartı sesle birlikte sunuyor. Her kaydırma
`feedback`e yazılıyor — yani deste bir arayüz süsü değil, ölçüm düzeneğinin
(`geri_bildirim.py`, K19) yakıt pompası.

## Sıralama: strateji İÇİ ölçülmüş skor, strateji ARASI senin kararların

Strateji skorları aynı ölçekte değil (bkz. `web/sunucu.py`, geri bildirim
etkisi); birleştirmek ölçülmemiş bir sıralayıcı olurdu. Bu yüzden:

1. Strateji İÇİNDE kendi skoru + Öneriler sayfasındaki geri bildirim kayması
   (`yakinlik_etkisi`, ETKI_TAVANI · σ). Aynı istisna, aynı tavan.
2. Stratejiler ARASINDA pay, kullanıcının GERÇEK kararlarından: her strateji
   için sanatçı düzeyinde Beta(1 + beğendim, 1 + tutmadı) ve her kartta
   Thompson örneklemesi. İlk sürüm stratejileri gizleme sınamasının sırasıyla
   (melez → liste → ses) diziyordu; ölçüldü (2026-09-23, seto'nun kararları):

       strateji            zevk isabeti   %90 Wilson
       melez                   %25 (3/12)  [10–49]
       liste_birlikteligi      %11 (1/9)   [ 3–38]
       ses_benzerligi          %67 (2/3)   [25–92]

   Vekil ölçütün "en iyi"si gerçek tercihte en iyi değil — ve n küçük. Sabit
   bir sıra ne o sırayı ne de alternatifini sınayabiliyordu. Thompson hem
   her yoldan örnek getirir (ölçüm verisi birikir) hem de veri biriktikçe
   tutan yola kayar. Rastgelelik karar sayısıyla tohumlanır: aynı durum aynı
   desteyi verir (K2, tekrarlanabilirlik).
3. Eksenler arasında sırayla dönülür (round-robin). Eksen İÇİNDEKİ sırayı
   değiştirmez; yalnız on kartın on'unun aynı eksenden gelmesini önler.

## Karar sanatçı düzeyinde

Kart bir öğe gösterir (en iyi albüm ya da parça) ama karar o SANATÇININ bu
çalışmadaki tüm aday satırlarına yazılır — Öneriler sayfasının "bir kart =
bir sanatçı" ilkesiyle ve `yargilanan_sanatcilar`ın sanatçı düzeyindeki
okumasıyla aynı. Bir sanatçı hakkında HERHANGİ bir çalışmada karar verildiyse
deste onu bir daha göstermez.

## Liste

Sağa kaydırmak iki şey yazar: `feedback` (begendim — ölçüm) ve `liste`
(gösterilen öğe — iş listesi). Ayrı tutulmalarının gerekçesi `db.py`'de.
"""

from __future__ import annotations

import csv
import io
import json
import random
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, quote_plus

from python.ceviri import etiket_adi
from python.dil import t
from python.gerekce import gerekce as gerekce_yaz, strateji_adi
from python.metin import normalize_esleme

#: Ölçülmüş sıra (README, leave-one-artist-out @50). Değişirse önce ölçülür.
ANA_SIRA = ("melez", "liste_birlikteligi", "ses_benzerligi")

#: Kadro grafiği yolları. Ölçütü tam onların işini ölçmüyor (bkz.
#: `web/sunucu.py:NIS_STRATEJILER`); destede yalnız istenirse ("cesur" kaynak).
NIS_SIRA = ("kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik")

KAYNAKLAR = {"ana": ANA_SIRA, "cesur": NIS_SIRA, "hepsi": ANA_SIRA + NIS_SIRA}

#: Strateji adları iki dilde: `python/gerekce.py:STRATEJI_ADI`.

KARARLAR = ("begendim", "tutmadi", "zaten_biliyorum")
DURUMLAR = ("yeni", "dinlendi", "edinildi")

#: Destenin büyütülebileceği en uzak sıra. Değerlendirme @50'ye kadar ölçüyor;
#: ötesi ölçülmemiş bölge (K19). Tavan ölçüm genişletilmeden artırılmaz.
BUYUTME_TAVANI = 50
BUYUTME_ADIMI = 20


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Deste
# --------------------------------------------------------------------------- #

def eksen_etiketi(kume_id) -> str:
    """Adsız eksen: "Eksen 3" / "Axis 3"."""
    return t(f"Eksen {kume_id}", f"Axis {kume_id}")


def kutuphane_adlari(conn: sqlite3.Connection) -> dict[str, str]:
    """{normalize ad: okunur ad} — gerekçede "duman" değil "Duman" yazsın."""
    return {normalize_esleme(r[0]): r[0] for r in conn.execute(
        "SELECT DISTINCT artist FROM albums") if r[0]}


def eksenler(conn: sqlite3.Connection, calisma_id: str) -> list[dict]:
    """Adayı olan eksenler; kullanıcının adlandırdıkları önce."""
    satirlar = conn.execute(
        """
        SELECT c.kume_id, c.kullanici_adi, c.stabil_mi,
               (SELECT COUNT(DISTINCT a.artist) FROM adaylar a
                 WHERE a.calisma_id = c.calisma_id AND a.eksen = c.kume_id) sanatci
          FROM clusters c WHERE c.calisma_id = ?
        """, (calisma_id,)).fetchall()
    liste = [
        {"eksen": int(r["kume_id"]), "ad": r["kullanici_adi"] or eksen_etiketi(r["kume_id"]),
         "adli": bool(r["kullanici_adi"]), "sanatci": int(r["sanatci"] or 0)}
        for r in satirlar if r["sanatci"]
    ]
    return sorted(liste, key=lambda e: (not e["adli"], e["eksen"]))


def yargilanan_anahtarlar(conn: sqlite3.Connection) -> set[str]:
    """Hakkında HERHANGİ bir çalışmada karar verilmiş ya da listede duran
    sanatçılar. Deste bunları bir daha göstermez."""
    anahtarlar = {
        normalize_esleme(r[0]) for r in conn.execute(
            """SELECT DISTINCT a.artist FROM feedback f
                 JOIN adaylar a ON a.aday_id = f.aday_id
                               AND a.calisma_id = f.calisma_id""")
    }
    anahtarlar |= {normalize_esleme(r[0]) for r in conn.execute(
        "SELECT DISTINCT artist FROM liste")}
    anahtarlar.discard("")
    return anahtarlar


@dataclass
class _Satir:
    aday_id: str
    eksen: int
    strateji: str
    artist: str
    title: str
    year: int | None
    birim: str
    parca_id: int | None
    onizleme_parca: str | None
    gerekce: str
    skor: float
    dayanak: str | None = None


def strateji_sonsallari(conn: sqlite3.Connection) -> dict[str, tuple[int, int]]:
    """{strateji: (beğendim, tutmadı)} — SANATÇI düzeyinde, tüm çalışmalar.

    Bir sanatçıya dört albümü için dört satır yazılıyor; satır saymak o
    sanatçıyı dört karar sayardı. "Zaten biliyorum" zevk hakkında bilgi
    taşımaz (bkz. `geri_bildirim.py`), paya da paydaya da girmez.
    """
    son: dict[tuple[str, str], str] = {}
    for strateji, artist, karar in conn.execute(
        """SELECT a.strateji, a.artist, f.karar FROM feedback f
             JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
            WHERE f.karar IN ('begendim', 'tutmadi')
            ORDER BY f.tarih"""):
        son[(strateji, normalize_esleme(artist))] = karar
    sayim: dict[str, list[int]] = {}
    for (strateji, _), karar in son.items():
        c = sayim.setdefault(strateji, [0, 0])
        c[0 if karar == "begendim" else 1] += 1
    return {st: (b, t) for st, (b, t) in sayim.items()}


def _strateji_sirasi(satirlar: list[_Satir], etki: dict[str, tuple[float, str]],
                     tavan: float) -> list[_Satir]:
    """Bir stratejinin kendi sırası — skor + geri bildirim kayması (σ, o
    stratejinin kendi skorlarından). Eşitlikte çalınabilir olan öne geçer."""
    if not satirlar:
        return []
    skorlar = [s.skor for s in satirlar]
    ort = sum(skorlar) / len(skorlar)
    sigma = (sum((x - ort) ** 2 for x in skorlar) / len(skorlar)) ** 0.5

    def ayarli(s: _Satir) -> float:
        pay = etki.get(normalize_esleme(s.artist), (0.0, ""))[0]
        return s.skor + tavan * pay * sigma

    return sorted(satirlar, key=lambda s: (-ayarli(s), s.parca_id is None))


def _eksen_sirasi(satirlar: list[_Satir], stratejiler: tuple[str, ...],
                  etki: dict[str, tuple[float, str]], tavan: float,
                  sonsal: dict[str, tuple[int, int]], rng) -> list[_Satir]:
    """Bir eksenin sanatçı sırası — her sanatçı bir kez.

    Her adımda kaynak strateji Thompson örneklemesiyle seçilir: her yolun
    Beta(1+beğendim, 1+tutmadı) dağılımından bir çekiliş, en büyüğü kazanır.
    Seçilen yolun sıradaki (henüz görülmemiş) sanatçısı alınır.
    """
    kuyruklar = {
        st: _strateji_sirasi([s for s in satirlar if s.strateji == st], etki, tavan)
        for st in stratejiler
    }
    imlec = {st: 0 for st in kuyruklar}
    gorulen: set[str] = set()
    sira: list[_Satir] = []

    def siradaki(st: str) -> _Satir | None:
        k = kuyruklar[st]
        while imlec[st] < len(k):
            s = k[imlec[st]]
            imlec[st] += 1
            if normalize_esleme(s.artist) not in gorulen:
                return s
        return None

    while True:
        canli = [st for st in kuyruklar if imlec[st] < len(kuyruklar[st])]
        if not canli:
            break
        cekilis = {st: rng.betavariate(1 + sonsal.get(st, (0, 0))[0],
                                       1 + sonsal.get(st, (0, 0))[1])
                   for st in canli}
        st = max(canli, key=lambda x: (cekilis[x], -stratejiler.index(x)))
        s = siradaki(st)
        if s is None:
            continue
        gorulen.add(normalize_esleme(s.artist))
        sira.append(s)
    return sira


def deste(
    conn: sqlite3.Connection, calisma_id: str, *,
    eksen: int | None = None, kaynak: str = "ana", adet: int = 10,
    haric: set[str] | frozenset[str] = frozenset(),
    etki: dict[str, tuple[float, str]] | None = None,
    baglam: dict[str, list[str]] | None = None,
    olcum: dict[str, list[str]] | None = None,
    eksen_adlari: dict[int, str] | None = None,
) -> dict:
    """Sıradaki `adet` kart ve geride kalan sanatçı sayısı.

    `haric`: istemcinin kuyruğunda duran (henüz karar verilmemiş) aday
    kimlikleri — aynı kart iki kez gelmesin. `etki`, `baglam`, `olcum`
    pahalı ve web katmanında önbelleklenerek veriliyor; verilmezse boş.
    """
    from python.geri_bildirim import ETKI_TAVANI

    stratejiler = KAYNAKLAR.get(kaynak, ANA_SIRA)
    etki = etki or {}
    baglam = baglam or {}
    olcum = olcum or {}
    eksen_adlari = eksen_adlari or {}

    parametre: list = [calisma_id, *stratejiler]
    kosul = f"calisma_id = ? AND strateji IN ({','.join('?' * len(stratejiler))})"
    if eksen is not None:
        kosul += " AND eksen = ?"
        parametre.append(eksen)
    satirlar = [
        _Satir(r["aday_id"], int(r["eksen"] if r["eksen"] is not None else -1),
               r["strateji"], r["artist"], r["title"],
               int(r["year"]) if r["year"] else None, r["birim"] or "album",
               int(r["parca_id"]) if r["parca_id"] else None,
               r["onizleme_parca"], r["gerekce"] or "", float(r["skor"] or 0),
               r["dayanak"])
        for r in conn.execute(
            f"""SELECT aday_id, eksen, strateji, artist, title, year, birim,
                       parca_id, onizleme_parca, gerekce, skor, dayanak
                  FROM adaylar WHERE {kosul}""", parametre)
    ]

    engelli = yargilanan_anahtarlar(conn)
    haric_sanatci = {normalize_esleme(s.artist) for s in satirlar if s.aday_id in haric}
    engelli |= haric_sanatci

    eksene_gore: dict[int, list[_Satir]] = {}
    for s in satirlar:
        if normalize_esleme(s.artist) not in engelli:
            eksene_gore.setdefault(s.eksen, []).append(s)
    # Tohum: çalışma + karar sayısı. Aynı durum aynı desteyi verir; her yeni
    # karar tohumu değiştirir, yani deste kararlarla birlikte yeniden çekilir.
    sonsal = strateji_sonsallari(conn)
    karar_sayisi = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    rng = random.Random(f"{calisma_id}:{karar_sayisi}")
    siralar = {
        e: _eksen_sirasi(g, stratejiler, etki, ETKI_TAVANI, sonsal, rng)
        for e, g in sorted(eksene_gore.items())
    }

    # Eksenler arası sırayla dön: kullanıcının adlandırdığı eksenler önce —
    # ad vermek, o eksenin kullanıcı için anlamlı olduğunun en açık işareti.
    adli = {r[0] for r in conn.execute(
        "SELECT kume_id FROM clusters WHERE calisma_id = ? "
        "AND COALESCE(kullanici_adi, '') != ''", (calisma_id,))}
    eksen_sirasi = sorted(siralar, key=lambda e: (e not in adli, e))
    secilen: list[_Satir] = []
    gorulen: set[str] = set()
    imlec = {e: 0 for e in eksen_sirasi}
    toplam = sum(len(v) for v in siralar.values())
    while len(secilen) < adet and any(imlec[e] < len(siralar[e]) for e in eksen_sirasi):
        for e in eksen_sirasi:
            while imlec[e] < len(siralar[e]):
                s = siralar[e][imlec[e]]
                imlec[e] += 1
                anahtar = normalize_esleme(s.artist)
                if anahtar not in gorulen:       # iki eksende birden aday olabilir
                    gorulen.add(anahtar)
                    secilen.append(s)
                    break
            if len(secilen) >= adet:
                break

    # Kalan TEKİL sanatçı: eksenler arası yinelenenler bir kez sayılır.
    tum_sanatci = {normalize_esleme(s.artist) for v in siralar.values() for s in v}
    kalan = len(tum_sanatci) - len(gorulen)

    adlar = kutuphane_adlari(conn)
    kartlar = [_kart(conn, calisma_id, s, etki, baglam, olcum, eksen_adlari, adlar)
               for s in secilen]
    return {"kartlar": kartlar, "kalan": max(0, kalan), "toplam": toplam}


def _kart(conn, calisma_id: str, s: _Satir, etki, baglam, olcum,
          eksen_adlari, adlar) -> dict:
    anahtar = normalize_esleme(s.artist)
    kimlikler = [r[0] for r in conn.execute(
        "SELECT DISTINCT aday_id FROM adaylar WHERE calisma_id = ? AND artist = ?",
        (calisma_id, s.artist))]
    m = conn.execute("SELECT * FROM medya WHERE aday_id = ?", (s.aday_id,)).fetchone()
    etki_pay, etki_gerekce = etki.get(anahtar, (0.0, ""))
    eksen_ad = eksen_adlari.get(s.eksen) or eksen_etiketi(s.eksen)
    return {
        "aday_id": s.aday_id, "kimlikler": kimlikler,
        "artist": s.artist, "title": s.title, "year": s.year, "birim": s.birim,
        "parca_id": (m["parca_id"] if m and m["parca_id"] else s.parca_id),
        "parca_adi": (m["parca_adi"] if m and m["parca_adi"] else s.onizleme_parca)
                     or (s.title if s.birim == "parca" else None),
        "album_adi": m["album_adi"] if m else None,
        "kapak": m["kapak"] if m else None,
        "sanatci_gorsel": m["sanatci_gorsel"] if m else None,
        # Tabloda satır varsa (bulundu ya da yok) istemci tekrar sormaz.
        "medya_hazir": m is not None,
        "eksen": s.eksen, "eksen_ad": eksen_ad,
        "strateji": s.strateji, "strateji_ad": strateji_adi(s.strateji),
        "gerekce": gerekce_yaz(s.strateji, s.dayanak, eksen=eksen_ad,
                               saklanan=s.gerekce, adlar=adlar),
        "geri_bildirim": etki_gerekce if abs(etki_pay) > 0 else "",
        "geri_bildirim_yon": "arti" if etki_pay > 0 else ("eksi" if etki_pay < 0 else ""),
        "baglam": [etiket_adi(e) for e in baglam.get(anahtar, [])[:3]],
        "olcum": [etiket_adi(e) for e in sorted(olcum.get(s.aday_id, []))[:3]],
    }


# --------------------------------------------------------------------------- #
# Karar
# --------------------------------------------------------------------------- #

def _sanatci_satirlari(conn, calisma_id: str, aday_id: str) -> list[sqlite3.Row]:
    """Gösterilen adayın sanatçısının bu çalışmadaki TÜM aday satırları."""
    return conn.execute(
        """SELECT DISTINCT aday_id, eksen FROM adaylar
            WHERE calisma_id = ? AND artist = (
                  SELECT artist FROM adaylar WHERE aday_id = ? AND calisma_id = ?
                  LIMIT 1)""",
        (calisma_id, aday_id, calisma_id)).fetchall()


def karar_kaydet(conn: sqlite3.Connection, calisma_id: str, aday_id: str,
                 karar: str) -> dict:
    """Deste kararı: sanatçı düzeyinde feedback + beğenide listeye ekleme.

    Tek işlemde (transaction): yarım yazılmış bir karar ölçümü bozar.
    """
    if karar not in KARARLAR:
        raise ValueError(f"geçersiz karar: {karar}")
    satirlar = _sanatci_satirlari(conn, calisma_id, aday_id)
    if not satirlar:
        raise LookupError(f"aday yok: {aday_id}")
    gorulen: set[str] = set()
    with conn:
        for r in satirlar:
            if r["aday_id"] in gorulen:
                continue
            gorulen.add(r["aday_id"])
            conn.execute(
                "INSERT OR REPLACE INTO feedback (aday_id, calisma_id, eksen, karar, tarih) "
                "VALUES (?,?,?,?,date('now'))",
                (r["aday_id"], calisma_id, r["eksen"], karar))
        if karar == "begendim":
            _listeye_ekle(conn, calisma_id, aday_id)
    return {"karar": karar, "adet": len(gorulen), "liste": liste_sayisi(conn),
            "bugun": gunluk_ozet(conn)}


def karar_geri_al(conn: sqlite3.Connection, calisma_id: str, aday_id: str) -> dict:
    """Son kaydırmayı geri al. Deste yalnız kararsız sanatçı gösterdiği için
    önceki durum "karar yok"tur; liste satırı yalnız hâlâ 'yeni' ise silinir
    (dinlenmiş ya da edinilmiş bir öğe bir geri al ile kaybolmamalı)."""
    kimlikler = sorted({r["aday_id"] for r in _sanatci_satirlari(conn, calisma_id, aday_id)})
    if not kimlikler:
        return {"adet": 0, "liste": liste_sayisi(conn)}
    yer = ",".join("?" * len(kimlikler))
    with conn:
        conn.execute(f"DELETE FROM feedback WHERE calisma_id = ? AND aday_id IN ({yer})",
                     (calisma_id, *kimlikler))
        conn.execute(f"DELETE FROM liste WHERE durum = 'yeni' AND aday_id IN ({yer})",
                     kimlikler)
    return {"adet": len(kimlikler), "liste": liste_sayisi(conn),
            "bugun": gunluk_ozet(conn)}


# --------------------------------------------------------------------------- #
# Liste
# --------------------------------------------------------------------------- #

def _listeye_ekle(conn: sqlite3.Connection, calisma_id: str, aday_id: str) -> bool:
    """Adayı listeye kopyala. Zaten varsa DURUMUNA dokunma (edinilmiş bir
    albüm yeniden beğenilince 'yeni'ye dönmemeli). İşlem çağıranın."""
    a = conn.execute(
        """SELECT * FROM adaylar WHERE aday_id = ? AND calisma_id = ?
            ORDER BY skor DESC LIMIT 1""", (aday_id, calisma_id)).fetchone()
    if a is None:
        return False
    imlec = conn.execute(
        """INSERT OR IGNORE INTO liste
           (aday_id, calisma_id, eksen, strateji, artist, title, year, birim,
            parca_id, mbid, gerekce, dayanak, durum, eklenme)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'yeni', ?)""",
        (a["aday_id"], calisma_id, a["eksen"], a["strateji"], a["artist"],
         a["title"], a["year"], a["birim"] or "album", a["parca_id"], a["mbid"],
         a["gerekce"], a["dayanak"], _simdi()))
    return imlec.rowcount > 0


def listeye_ekle(conn: sqlite3.Connection, calisma_id: str,
                 aday_kimlikleri: list[str]) -> int:
    """Öneriler sayfasındaki 👍 için: grubun tüm öğeleri listeye."""
    with conn:
        return sum(_listeye_ekle(conn, calisma_id, k) for k in aday_kimlikleri)


def listeden_cikar_yeni(conn: sqlite3.Connection, aday_kimlikleri: list[str]) -> None:
    """👍 geri alınınca: yalnız 'yeni' durumdakiler çıkar (bkz. karar_geri_al)."""
    if not aday_kimlikleri:
        return
    with conn:
        conn.execute(
            f"DELETE FROM liste WHERE durum = 'yeni' AND aday_id IN "
            f"({','.join('?' * len(aday_kimlikleri))})", aday_kimlikleri)


def liste_sayisi(conn: sqlite3.Connection) -> int:
    try:
        return int(conn.execute("SELECT COUNT(*) FROM liste").fetchone()[0])
    except sqlite3.Error:
        return 0


def durum_guncelle(conn: sqlite3.Connection, aday_id: str, durum: str) -> bool:
    if durum not in DURUMLAR:
        raise ValueError(f"geçersiz durum: {durum}")
    with conn:
        return conn.execute(
            "UPDATE liste SET durum = ?, guncelleme = ? WHERE aday_id = ?",
            (durum, _simdi(), aday_id)).rowcount > 0


def listeden_sil(conn: sqlite3.Connection, aday_id: str) -> bool:
    with conn:
        return conn.execute("DELETE FROM liste WHERE aday_id = ?",
                            (aday_id,)).rowcount > 0


def _kutuphane_anahtarlari(conn) -> set[tuple[str, str]]:
    return {
        (normalize_esleme(r[0]), normalize_esleme(r[1]))
        for r in conn.execute("SELECT artist, title FROM albums")
    }


def liste_ogeleri(conn: sqlite3.Connection, durum: str | None = None) -> list[dict]:
    """Liste + medya + "kütüphanende mi".

    `kutuphanede`: öğenin albümü artık `albums`ta (normalize sanatçı + albüm).
    Kütüphane taraması (`kutuphane_tara`) edindiğin albümü okuyunca liste
    bunu kendiliğinden görür — DAP kullanıcısı için döngünün kapanışı.
    Durumu OTOMATİK değiştirmiyor; rozet gösterir, karar kullanıcının.
    """
    # Eksen adı öğenin KENDİ çalışmasından: liste kümelemeden uzun yaşar ve
    # eski bir çalışmanın 3 numaralı ekseni bugünkü 3 numara değildir.
    sorgu = """
        SELECT l.*, m.kapak, m.sanatci_gorsel, m.album_adi, m.deezer_album,
               m.parca_id AS m_parca_id, m.parca_adi, m.yedek,
               NULLIF(c.kullanici_adi, '') AS eksen_ad
          FROM liste l
          LEFT JOIN medya m ON m.aday_id = l.aday_id
          LEFT JOIN clusters c ON c.calisma_id = l.calisma_id AND c.kume_id = l.eksen
    """
    parametre: tuple = ()
    if durum in DURUMLAR:
        sorgu += " WHERE l.durum = ?"
        parametre = (durum,)
    sorgu += " ORDER BY l.eklenme DESC"
    kutuphane = _kutuphane_anahtarlari(conn)
    ogeler = []
    for r in conn.execute(sorgu, parametre):
        o = dict(r)
        o["eksen_ad"] = o["eksen_ad"] or (eksen_etiketi(o["eksen"]) if o["eksen"] is not None else "")
        o["album"] = o["title"] if o["birim"] == "album" else (o.get("album_adi") or "")
        o["parca"] = o["title"] if o["birim"] == "parca" else o.get("parca_adi")
        o["parca_id"] = o["parca_id"] or o.pop("m_parca_id", None)
        o["kutuphanede"] = bool(o["album"]) and (
            normalize_esleme(o["artist"]), normalize_esleme(o["album"])) in kutuphane
        o["baglantilar"] = edinme_baglantilari(o)
        ogeler.append(o)
    return ogeler


def edinme_baglantilari(o: dict) -> list[tuple[str, str]]:
    """"Nereden edinirim" — satın alma önce, akış sonra.

    Bandcamp ve Qobuz kayıpsız DOSYA satıyor: DAP'tan dinleyen bir kullanıcı
    için edinmenin asıl yolu bu. Akış servisleri tam dinleme içindir.
    Hepsi yalnız arama bağlantısı; hiçbir servise istek atılmıyor.
    """
    hedef = o.get("album") or o.get("title") or ""
    q = f"{o['artist']} {hedef}".strip()
    baglantilar = [
        ("Bandcamp", f"https://bandcamp.com/search?q={quote_plus(q)}&item_type=a"),
        ("Qobuz", f"https://www.qobuz.com/us-en/search?q={quote_plus(q)}"),
    ]
    if o.get("deezer_album"):
        baglantilar.append(("Deezer", f"https://www.deezer.com/album/{o['deezer_album']}"))
    else:
        baglantilar.append(("Deezer", f"https://www.deezer.com/search/{quote(q)}"))
    baglantilar += [
        ("Spotify", f"https://open.spotify.com/search/{quote(q)}"),
        ("YouTube Music", f"https://music.youtube.com/search?q={quote_plus(q)}"),
        ("Apple Music", f"https://music.apple.com/search?term={quote_plus(q)}"),
    ]
    if o.get("mbid"):
        baglantilar.append(("MusicBrainz", f"https://musicbrainz.org/release-group/{o['mbid']}"))
    return baglantilar


# --------------------------------------------------------------------------- #
# Dışa aktarım
# --------------------------------------------------------------------------- #

CSV_SUTUNLARI = ("sanatci", "album", "parca", "yil", "birim", "durum", "eksen",
                 "strateji", "eklenme", "kutuphanede", "mbid", "deezer",
                 "bandcamp", "qobuz", "gerekce")

#: Dışa aktarım sütun başlıkları. İngilizce dosya İngilizce başlık taşır —
#: Türkçe başlıklı bir CSV İngilizce konuşan için okunmaz.
CSV_BASLIK = {
    "sanatci": ("sanatçı", "artist"), "album": ("albüm", "album"),
    "parca": ("parça", "track"), "yil": ("yıl", "year"), "birim": ("birim", "unit"),
    "durum": ("durum", "status"), "eksen": ("eksen", "axis"),
    "strateji": ("kaynak", "source"), "eklenme": ("eklenme", "added"),
    "kutuphanede": ("kütüphanede", "in_library"), "mbid": ("mbid", "mbid"),
    "deezer": ("deezer", "deezer"), "bandcamp": ("bandcamp", "bandcamp"),
    "qobuz": ("qobuz", "qobuz"), "gerekce": ("gerekçe", "reason"),
}
DURUM_ADI = {"yeni": ("yeni", "new"), "dinlendi": ("dinlendi", "listened"),
             "edinildi": ("edinildi", "acquired")}


def _satir(o: dict) -> dict:
    baglanti = dict(o["baglantilar"])
    return {
        "sanatci": o["artist"], "album": o["album"], "parca": o.get("parca") or "",
        "yil": o.get("year") or "",
        "birim": t("albüm", "album") if o["birim"] == "album" else t("parça", "track"),
        "durum": t(*DURUM_ADI.get(o["durum"], (o["durum"], o["durum"]))),
        "eksen": o.get("eksen_ad") or "",
        "strateji": strateji_adi(o.get("strateji") or ""),
        "eklenme": (o.get("eklenme") or "")[:10],
        "kutuphanede": t("evet", "yes") if o["kutuphanede"] else "",
        "mbid": o.get("mbid") or "", "deezer": baglanti.get("Deezer", ""),
        "bandcamp": baglanti.get("Bandcamp", ""), "qobuz": baglanti.get("Qobuz", ""),
        "gerekce": gerekce_yaz(o.get("strateji") or "", o.get("dayanak"),
                               eksen=o.get("eksen_ad") or "", saklanan=o.get("gerekce") or ""),
    }


def disa_aktar(ogeler: list[dict], bicim: str) -> tuple[str, str]:
    """(içerik, medya türü). Biçimler:

    - `csv`  tam tablo. UTF-8 BOM'lu: Excel BOM'suz UTF-8'i Latin-1 sanıp
      "Şebnem"i "Å\u009eebnem" gösteriyor; Türkçe kullanıcı için şart.
    - `txt`  alışveriş listesi: "Sanatçı — Albüm (Yıl)", albüm başına bir satır.
      Herhangi bir mağazanın arama kutusuna yapıştırılabilir.
    - `json` makine için: betiklerle işlenebilir tam kayıt.
    """
    satirlar = [_satir(o) for o in ogeler]
    if bicim == "csv":
        cikti = io.StringIO()
        yazici = csv.writer(cikti)
        yazici.writerow([t(*CSV_BASLIK[s]) for s in CSV_SUTUNLARI])
        yazici.writerows([[r[s] for s in CSV_SUTUNLARI] for r in satirlar])
        return "﻿" + cikti.getvalue(), "text/csv; charset=utf-8"
    if bicim == "txt":
        gorulen, cizgiler = set(), []
        for s in satirlar:
            anahtar = (normalize_esleme(s["sanatci"]), normalize_esleme(s["album"]))
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            ad = s["album"] or s["parca"]
            yil = f" ({s['yil']})" if s["yil"] else ""
            cizgiler.append(f"{s['sanatci']} — {ad}{yil}")
        return "\n".join(cizgiler) + ("\n" if cizgiler else ""), "text/plain; charset=utf-8"
    if bicim == "json":
        return json.dumps(satirlar, ensure_ascii=False, indent=2), "application/json"
    raise ValueError(f"bilinmeyen biçim: {bicim}")


# --------------------------------------------------------------------------- #
# Analiz ve günlük özet
# --------------------------------------------------------------------------- #

def gunluk_ozet(conn: sqlite3.Connection, bugun: date | None = None) -> dict:
    """Bugünkü sanatçı kararı sayısı ve kesintisiz gün serisi.

    SANATÇI düzeyinde sayılıyor: tek bir kaydırma birkaç aday satırına
    yazılıyor ve satır saymak "bugün 12 karar" diye şişirirdi.
    Tarih `date('now')` ile yazılıyor (UTC); bugün de UTC'den alınır ki gün
    sınırı iki tarafta aynı olsun.
    """
    bugun = bugun or datetime.now(timezone.utc).date()
    gunler = {}
    for tarih, karar, adet in conn.execute(
        """SELECT f.tarih, f.karar, COUNT(DISTINCT a.artist)
             FROM feedback f JOIN adaylar a
               ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
            GROUP BY f.tarih, f.karar"""):
        gunler.setdefault(tarih, Counter())[karar] += adet
    seri, gun = 0, bugun
    if bugun.isoformat() not in gunler:
        gun = bugun - timedelta(days=1)     # bugün henüz karar yoksa seri bozulmaz
    while gun.isoformat() in gunler:
        seri += 1
        gun -= timedelta(days=1)
    b = gunler.get(bugun.isoformat(), Counter())
    return {"karar": sum(b.values()), "begendim": b["begendim"], "seri": seri}


def etkinlik(conn: sqlite3.Connection, gun: int = 21,
             bugun: date | None = None) -> list[tuple[str, int]]:
    """Son `gun` günün sanatçı kararı sayıları (boş günler 0)."""
    bugun = bugun or datetime.now(timezone.utc).date()
    sayim = dict(conn.execute(
        """SELECT f.tarih, COUNT(DISTINCT a.artist) FROM feedback f
             JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
            GROUP BY f.tarih""").fetchall())
    return [((bugun - timedelta(days=i)).isoformat(),
             int(sayim.get((bugun - timedelta(days=i)).isoformat(), 0)))
            for i in range(gun - 1, -1, -1)]


def eksen_isabeti(conn: sqlite3.Connection, calisma_id: str,
                  eksen_adlari: dict[int, str]) -> list[dict]:
    """Eksen başına zevk isabeti — SANATÇI düzeyinde, Wilson aralıklı.

    Satır düzeyinde sayılsaydı dört albümlük bir sanatçı dört karar sayılırdı
    ve eksenler albüm sayısına göre ağırlanırdı. Sanatçı başına tek karar.
    """
    from python.geri_bildirim import ASGARI_N, wilson

    kararlar: dict[int, dict[str, str]] = {}
    for eksen, artist, karar in conn.execute(
        """SELECT f.eksen, a.artist, f.karar FROM feedback f
             JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
            WHERE f.calisma_id = ?""", (calisma_id,)):
        kararlar.setdefault(int(eksen if eksen is not None else -1), {})[
            normalize_esleme(artist)] = karar
    sonuc = []
    for eksen, sanatcilar in kararlar.items():
        say = Counter(sanatcilar.values())
        n = say["begendim"] + say["tutmadi"]
        p, alt, ust = wilson(say["begendim"], n)
        sonuc.append({
            "eksen": eksen, "ad": eksen_adlari.get(eksen) or eksen_etiketi(eksen),
            "begendim": say["begendim"], "tutmadi": say["tutmadi"],
            "bilinen": say["zaten_biliyorum"], "n": n,
            "isabet": p if n else None, "alt": alt, "ust": ust,
            "yeterli": n >= ASGARI_N,
        })
    return sorted(sonuc, key=lambda s: (-s["n"], s["ad"]))


def liste_analizi(ogeler: list[dict], baglam: dict[str, list[str]]) -> dict:
    """Listenin kendi dökümü — yalnız ölçülmüş/sayılmış şeyler (K13).

    "Ortalama dinleyiciye göre" gibi bir kıyas YOK; elde öyle bir norm yok.
    """
    durum = Counter(o["durum"] for o in ogeler)
    onyil = Counter(t(f"{(o['year'] // 10) * 10}'ler", f"{(o['year'] // 10) * 10}s")
                    for o in ogeler if o.get("year"))
    eksen = Counter(o["eksen_ad"] for o in ogeler if o.get("eksen_ad"))
    strateji = Counter(strateji_adi(o.get("strateji") or "—") for o in ogeler)
    sanatcilar = {normalize_esleme(o["artist"]) for o in ogeler}
    baglam_say = Counter(e for a in sanatcilar for e in baglam.get(a, []))
    return {
        "toplam": len(ogeler), "sanatci": len(sanatcilar),
        "durum": {d: durum.get(d, 0) for d in DURUMLAR},
        "kutuphanede": sum(o["kutuphanede"] for o in ogeler),
        "onyil": sorted(onyil.items()),
        "eksen": eksen.most_common(),
        "strateji": strateji.most_common(),
        "baglam": baglam_say.most_common(8),
    }


# --------------------------------------------------------------------------- #
# Desteyi büyütmek
# --------------------------------------------------------------------------- #

def mevcut_derinlik(conn: sqlite3.Connection, calisma_id: str) -> int:
    """Eksen başına en çok kaç melez sanatçı üretilmiş — destenin derinliği."""
    satir = conn.execute(
        """SELECT MAX(n) FROM (SELECT COUNT(DISTINCT artist) n FROM adaylar
             WHERE calisma_id = ? AND strateji = 'melez' GROUP BY eksen)""",
        (calisma_id,)).fetchone()
    return int(satir[0] or 0)


def desteyi_buyut(conn: sqlite3.Connection, calisma_id: str) -> dict:
    """Ana stratejileri daha derin üret: +20 sıra, tavan 50 (ölçülmüş ufuk).

    Üç ana strateji de YEREL veriyle çalışıyor (npmi tablosu + CLAP gömüleri);
    ağa çıkmıyor. Ölçüldü (2026-09-23, seto): 10 → 30 derinlik, 8 eksen,
    6,7 sn; tekil sanatçı melez 80 → 227, ses 80 → 229.
    Bayat aday temizliği feedback'i olan satırları korur (`adaylar.py`).
    """
    from python.discover.adaylar import (
        adaylari_yaz, bayat_adaylari_temizle, eksen_uret,
    )

    simdiki = mevcut_derinlik(conn, calisma_id)
    hedef = min(max(simdiki, 10) + BUYUTME_ADIMI, BUYUTME_TAVANI)
    if simdiki >= BUYUTME_TAVANI:
        return {"durum": "tavan", "derinlik": simdiki}
    eksen_listesi = [r[0] for r in conn.execute(
        "SELECT kume_id FROM clusters WHERE calisma_id = ? AND stabil_mi = 1 "
        "ORDER BY kume_id", (calisma_id,))]
    once = conn.execute("SELECT COUNT(*) FROM adaylar WHERE calisma_id = ?",
                        (calisma_id,)).fetchone()[0]
    for eksen in eksen_listesi:
        adaylar = eksen_uret(conn, calisma_id, eksen, adet=hedef, stratejiler=ANA_SIRA)
        adaylari_yaz(conn, calisma_id, adaylar)
        bayat_adaylari_temizle(conn, calisma_id, adaylar,
                               tarih=date.today().isoformat())
    sonra = conn.execute("SELECT COUNT(*) FROM adaylar WHERE calisma_id = ?",
                         (calisma_id,)).fetchone()[0]
    return {"durum": "tamam", "derinlik": hedef, "yeni": int(sonra - once)}


# --------------------------------------------------------------------------- #
# Müzisyene göre deste — "Mario Duplantier gibi çalan davulcular" (2026-09-28)
# --------------------------------------------------------------------------- #

#: Bu benzerliğin altındaki adaylar desteye girmez; deste "bundan daha
#: benzeri yok" diyerek biter. Ölçü: standartlaştırılmış icra profillerinde
#: kosinüs (`muzisyen.muzisyene_benzeyen_adaylar`), −1…1. ÖLÇÜLMEDİ — başlangıç
#: değeri; kararlar biriktikçe beğeni oranına göre ayarlanacak (K19).
MUZISYEN_ESIGI = 0.5


def muzisyen_destesi(
    conn: sqlite3.Connection, profiller, kisi_anahtar: str, rol: str, *,
    adet: int = 8, haric: set[str] | frozenset[str] = frozenset(),
    esik: float = MUZISYEN_ESIGI,
) -> dict:
    """Seçilen müzisyen gibi çalan, sende olmayan albümler — deste biçiminde.

    Kart biçimi `deste` ile aynı; tek fark her kartın KENDİ çalışma kimliğini
    taşıması (`calisma_id`): stem profili olan aday eski bir çalışmadan da
    gelebilir ve karar o çalışmaya yazılmalı. `bitis`: 'esik' ise kalan
    adayların hepsi eşiğin altında.
    """
    from python.ceviri import rol_adi
    from python.muzisyen import muzisyene_benzeyen_adaylar

    sonuc, havuz = muzisyene_benzeyen_adaylar(conn, profiller, kisi_anahtar, rol, adet=10_000)
    kisi_adi = (str(profiller.loc[kisi_anahtar, "kisi_adi"])
                if "kisi_adi" in getattr(profiller, "columns", ()) and kisi_anahtar in profiller.index
                else kisi_anahtar)
    bos = {"kartlar": [], "kalan": 0, "toplam": 0, "havuz": havuz, "kisi_adi": kisi_adi,
           "bitis": "esik" if havuz else "profil_yok", "esik": esik}
    if sonuc.empty:
        return bos

    engelli = yargilanan_anahtarlar(conn) | set(kutuphane_adlari(conn))
    engelli |= {normalize_esleme(r[0]) for r in conn.execute(
        f"SELECT artist FROM adaylar WHERE aday_id IN ({','.join('?' * len(haric)) or 'NULL'})",
        tuple(haric))}
    uygun = sonuc[~sonuc["artist"].map(lambda a: normalize_esleme(str(a))).isin(engelli)]
    ustunde = uygun[uygun["benzerlik"] >= esik]
    secilen = ustunde.head(adet)

    adlar = kutuphane_adlari(conn)
    rol_ad = rol_adi(rol)
    kartlar = []
    for r in secilen.itertuples():
        satir = conn.execute(
            """SELECT aday_id, calisma_id, eksen, strateji, artist, title, year, birim,
                      parca_id, onizleme_parca, gerekce, skor, dayanak
                 FROM adaylar WHERE aday_id = ? ORDER BY calisma_id DESC LIMIT 1""",
            (r.aday_id,)).fetchone()
        if satir is None:
            continue
        s = _Satir(satir["aday_id"], int(satir["eksen"] if satir["eksen"] is not None else -1),
                   satir["strateji"], satir["artist"], satir["title"],
                   int(satir["year"]) if satir["year"] else None, satir["birim"] or "album",
                   int(satir["parca_id"]) if satir["parca_id"] else None,
                   satir["onizleme_parca"], satir["gerekce"] or "", float(satir["skor"] or 0),
                   satir["dayanak"])
        kart = _kart(conn, satir["calisma_id"], s, {}, {}, {}, {}, adlar)
        yuzde_ = round(float(r.benzerlik) * 100)
        kart.update(
            calisma_id=satir["calisma_id"],
            benzerlik=round(float(r.benzerlik), 3),
            eksen_ad=t(f"%{yuzde_} benzer", f"{yuzde_}% alike"),
            strateji_ad=t(f"{kisi_adi} gibi", f"like {kisi_adi}"),
            gerekce=t(
                f"{rol_ad.capitalize()} kanalı {kisi_adi} gibi çalıyor: ayrılmış kanaldan "
                f"ölçülen profil %{yuzde_} yakın. Ölçüm tek 30 sn klipten; dinleyip karar ver.",
                f"The {rol_ad} part plays like {kisi_adi}: the profile measured from the "
                f"separated stem is {yuzde_}% close. It comes from a single 30 s clip, "
                f"so have a listen and decide."),
        )
        kartlar.append(kart)
    kalan = len(ustunde) - len(secilen)
    return {"kartlar": kartlar, "kalan": max(0, kalan), "toplam": len(ustunde),
            "havuz": havuz, "kisi_adi": kisi_adi, "esik": esik,
            "bitis": "esik" if kalan <= 0 else None}
