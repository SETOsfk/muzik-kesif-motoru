"""«Sayılarla sen» — kütüphanenin istatistiksel portresi.

«Sen» sayfası düz cümle kurar; bu sayfa aynı veriyi SAYI ve GRAFİKLE
gösterir ve her sayının arkasındaki yöntemi adıyla söyler (bulanık kümeleme,
bootstrap, Shannon çeşitliliği, Wilson aralığı). Hepsi mutlak ya da kullanıcının
kendi verisine göre; "ortalama dinleyici" normu yok (K13).

Burada yalnız sayı ve ham ad döner; cümle ve dil şablonda kurulur (K22).
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter

import numpy as np

#: Bir albüm en yüksek üyeliği bu değerin üstündeyse o tarza «net» aittir.
NET_UYELIK = 0.6
#: İki tarzın ikisinde de en az bu kadar üyelik → köprü albüm.
KOPRU_UYELIK = 0.3
#: Tempo histogramının kutu genişliği (vuruş/dakika).
TEMPO_KUTU = 10
#: Ses ölçümleri kaynaklar arası kıyaslanamaz (K11); tek kaynak seçilir.
KAYNAK_SIRASI = ("yerel", "onizleme", "acousticbrainz")


def _tablo_var(conn: sqlite3.Connection, ad: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {ad} LIMIT 1")
        return True
    except sqlite3.Error:
        return False


# --------------------------------------------------------------------------- #
# Zaman
# --------------------------------------------------------------------------- #

def zaman(conn: sqlite3.Connection) -> dict | None:
    """On yıllara göre albüm sayısı (boş on yıllar da sıfırla)."""
    yillar = [int(r[0]) for r in conn.execute("SELECT year FROM albums WHERE year > 1900")]
    if len(yillar) < 3:
        return None
    say = Counter(y // 10 * 10 for y in yillar)
    onyillar = list(range(min(say), max(say) + 10, 10))
    return {
        "onyillar": [(o, say.get(o, 0)) for o in onyillar],
        "medyan_yil": int(np.median(yillar)),
        "en_eski": min(yillar), "en_yeni": max(yillar), "n": len(yillar),
    }


# --------------------------------------------------------------------------- #
# Tarzlar: bulanık üyelik
# --------------------------------------------------------------------------- #

def saglik(uyum: float, stabil: bool) -> str:
    """Bir tarzın durumu, üç kelimeyle.

    - «saglam»: bootstrap'ta her seferinde aynı albümleri topluyor VE üyeleri
      ona net ait (ortalama en yüksek üyelik ≥ NET_UYELIK).
    - «karisik»: sağlam ama üyeleri başka tarzlarla paylaşılıyor — öneriler
      daha dağınık gelir. Kullanıcının «emin değilim» dediği öneriler çoğu
      zaman buradan çıkar.
    - «oynak»: yeniden örneklemede dağılıyor; tarz verinin bir tesadüfü olabilir.
    """
    if not stabil:
        return "oynak"
    return "saglam" if uyum >= NET_UYELIK else "karisik"


def tarzlar(conn: sqlite3.Connection, calisma_id: str | None) -> dict | None:
    """Tarz büyüklükleri, netlik, köprüler, sağlamlık ve ayrışma."""
    if not calisma_id:
        return None
    satirlar = conn.execute(
        """SELECT m.album_id, m.kume_id, m.uyelik, a.artist, a.title
             FROM memberships m JOIN albums a USING (album_id)
            WHERE m.calisma_id = ?""", (calisma_id,)).fetchall()
    if not satirlar:
        return None
    albumler: dict[str, dict] = {}
    for r in satirlar:
        a = albumler.setdefault(r[0], {"artist": r[3], "title": r[4], "u": {}})
        a["u"][int(r[1])] = float(r[2])
    kumeler = {int(r[0]): {"ad": r[1] or "", "stabilite": r[2], "stabil": bool(r[3])}
               for r in conn.execute(
                   "SELECT kume_id, kullanici_adi, stabilite, stabil_mi FROM clusters "
                   "WHERE calisma_id = ?", (calisma_id,))}

    boyut: Counter = Counter()
    net_say: Counter = Counter()
    uyum_top: Counter = Counter()
    ciftler: Counter = Counter()
    en_yuksekler = []
    kopruler = []
    for a in albumler.values():
        sirali = sorted(a["u"].items(), key=lambda kv: -kv[1])
        k, u = sirali[0]
        boyut[k] += 1
        uyum_top[k] += u
        en_yuksekler.append(u)
        if u >= NET_UYELIK:
            net_say[k] += 1
        if len(sirali) > 1 and sirali[1][1] >= KOPRU_UYELIK:
            kopruler.append({"artist": a["artist"], "title": a["title"],
                             "kume1": k, "u1": u, "kume2": sirali[1][0], "u2": sirali[1][1]})
            ciftler[tuple(sorted((k, sirali[1][0])))] += 1
    kopruler.sort(key=lambda k: -k["u2"])
    n = len(albumler)
    c = max(2, len({k for a in albumler.values() for k in a["u"]}))
    liste = []
    for k in sorted(boyut, key=lambda k: -boyut[k]):
        bilgi = kumeler.get(k, {})
        uyum = uyum_top[k] / boyut[k]
        liste.append({"kume": k, "ad": bilgi.get("ad", ""), "album": boyut[k],
                      "pay": boyut[k] / n, "net": net_say[k], "arada": boyut[k] - net_say[k],
                      "uyum": uyum, "stabilite": bilgi.get("stabilite"),
                      "stabil": bilgi.get("stabil", False),
                      "saglik": saglik(uyum, bilgi.get("stabil", False))})
    net = sum(net_say.values())
    # Ayrışma: ortalama en yüksek üyeliğin 1/c (tam bulanık) ile 1 (tam keskin)
    # arasındaki yeri. Bezdek'in bölüntü katsayısının okunur, ölçeklenmiş akrabası.
    ort = float(np.mean(en_yuksekler))
    return {
        "n": n, "kume_sayisi": len(liste), "liste": liste,
        "net": net, "arada": n - net, "net_pay": net / n,
        "kopru_sayisi": len(kopruler), "kopruler": kopruler[:5],
        "ciftler": [(a, b, say) for (a, b), say in ciftler.most_common(6)],
        "stabil_sayisi": sum(1 for k in liste if k["stabil"]),
        "saglam_sayisi": sum(1 for k in liste if k["saglik"] == "saglam"),
        "ayrisma": max(0.0, (ort - 1 / c) / (1 - 1 / c)),
    }


# --------------------------------------------------------------------------- #
# Çeşitlilik
# --------------------------------------------------------------------------- #

def cesitlilik(conn: sqlite3.Connection) -> dict | None:
    """Sanatçı dağılımı: ilk 10'un payı, tek albümlüler, Shannon çeşitliliği.

    «Etkin sanatçı sayısı» = exp(H), Hill sayısı (q=1). Kütüphane, her biri
    EŞİT sayıda albümle temsil edilen kaç sanatçıya denk? Sanatçı sayısıyla
    kıyaslanınca dağılımın ne kadar dengeli olduğunu tek sayıyla söyler.
    """
    sayilar = [int(r[1]) for r in conn.execute(
        "SELECT artist, COUNT(*) FROM albums GROUP BY artist")]
    if len(sayilar) < 2:
        return None
    toplam = sum(sayilar)
    p = np.array(sayilar, dtype=float) / toplam
    entropi = float(-(p * np.log(p)).sum())
    ilk = conn.execute(
        "SELECT artist, COUNT(*) n FROM albums GROUP BY artist ORDER BY n DESC, artist LIMIT 10"
    ).fetchall()
    return {
        "sanatci": len(sayilar), "album": toplam,
        "etkin": math.exp(entropi),
        "denge": math.exp(entropi) / len(sayilar),
        "ilk10_pay": sum(int(r[1]) for r in ilk) / toplam,
        "tek_albumlu": sum(1 for s in sayilar if s == 1),
        "ilk": [(r[0], int(r[1])) for r in ilk],
    }


# --------------------------------------------------------------------------- #
# Ses
# --------------------------------------------------------------------------- #

def ses(conn: sqlite3.Connection) -> dict | None:
    """Tempo dağılımı ve dinamik aralık — TEK kaynaktan (K11)."""
    if not _tablo_var(conn, "audio_features"):
        return None
    mevcut = {r[0]: r[1] for r in conn.execute(
        """SELECT f.kaynak, COUNT(*) FROM audio_features f
             JOIN albums a USING (album_id)
            WHERE f.tempo_medyan > 0 GROUP BY f.kaynak""")}
    kaynak = next((k for k in KAYNAK_SIRASI if mevcut.get(k, 0) >= 10), None)
    if kaynak is None:
        return None
    satirlar = conn.execute(
        """SELECT a.artist, a.title, f.tempo_medyan, f.dinamik_aralik
             FROM audio_features f JOIN albums a USING (album_id)
            WHERE f.kaynak = ? AND f.tempo_medyan > 0""", (kaynak,)).fetchall()
    tempolar = np.array([float(r[2]) for r in satirlar])
    alt = int(tempolar.min() // TEMPO_KUTU * TEMPO_KUTU)
    ust = int(tempolar.max() // TEMPO_KUTU * TEMPO_KUTU)
    kutular = [(b, int(((tempolar >= b) & (tempolar < b + TEMPO_KUTU)).sum()))
               for b in range(alt, ust + TEMPO_KUTU, TEMPO_KUTU)]
    en_hizli = max(satirlar, key=lambda r: r[2])
    en_agir = min(satirlar, key=lambda r: r[2])
    dinamik = [float(r[3]) for r in satirlar if r[3] is not None]
    return {
        "kaynak": kaynak, "n": len(satirlar), "kutular": kutular,
        "tempo_medyan": float(np.median(tempolar)),
        "tempo_q1": float(np.percentile(tempolar, 25)),
        "tempo_q3": float(np.percentile(tempolar, 75)),
        "en_hizli": (en_hizli[0], en_hizli[1], float(en_hizli[2])),
        "en_agir": (en_agir[0], en_agir[1], float(en_agir[2])),
        "dinamik_medyan": float(np.median(dinamik)) if dinamik else None,
    }


# --------------------------------------------------------------------------- #
# Keşif karnesi
# --------------------------------------------------------------------------- #

def kesif(conn: sqlite3.Connection) -> dict | None:
    """Sanatçı düzeyinde kararlar; genel beğeni oranı ve kaynak başına aralık."""
    from python.geri_bildirim import (
        ASGARI_N, kararlar, sanatci_duzeyi, strateji_isabeti, wilson,
    )
    veri = sanatci_duzeyi(kararlar(conn))
    if veri.empty:
        return None
    from python.metin import normalize_esleme
    tekil = veri.assign(_a=veri["artist"].map(lambda a: normalize_esleme(str(a)))) \
        .sort_values("tarih").drop_duplicates("_a", keep="last")
    begendim = int((tekil["karar"] == "begendim").sum())
    tutmadi = int((tekil["karar"] == "tutmadi").sum())
    bilinen = int((tekil["karar"] == "zaten_biliyorum").sum())
    oran, alt, ust = wilson(begendim, begendim + tutmadi)
    isabet = strateji_isabeti(veri)
    kaynaklar = []
    if not isabet.empty:
        for _, r in isabet.iterrows():
            if r["zevk_n"] >= ASGARI_N:
                kaynaklar.append({"strateji": r["strateji"], "n": int(r["zevk_n"]),
                                  "begendim": int(r["begendim"]),
                                  "oran": float(r["zevk_isabeti"]),
                                  "alt": float(r["zevk_alt"]), "ust": float(r["zevk_ust"])})
    return {
        "sanatci": len(tekil), "begendim": begendim, "tutmadi": tutmadi,
        "bilinen": bilinen, "yeni_pay": 1 - bilinen / len(tekil),
        "oran": oran if begendim + tutmadi else None, "alt": alt, "ust": ust,
        "kaynaklar": sorted(kaynaklar, key=lambda k: -k["oran"]),
        "asgari_n": ASGARI_N,
    }


def hepsi(conn: sqlite3.Connection, calisma_id: str | None) -> dict:
    return {
        "album": conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0],
        "zaman": zaman(conn), "tarzlar": tarzlar(conn, calisma_id),
        "cesitlilik": cesitlilik(conn), "ses": ses(conn), "kesif": kesif(conn),
    }
