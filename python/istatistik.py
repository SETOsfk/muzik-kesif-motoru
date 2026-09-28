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
import pandas as pd

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
        "pano": pano(conn, calisma_id),
    }


# --------------------------------------------------------------------------- #
# Pano: tarz başına ayrıntı ve tarz haritası
# --------------------------------------------------------------------------- #

#: Renkli gösterilen en çok tarz. Fazlası «diğer» gri: dokuzuncu bir renk
#: üretmek ayrışmayan bir ton demek (kategorik palet 8 renkte doğrulandı).
RENKLI_TARZ = 8


def tarz_haritasi(U: np.ndarray) -> np.ndarray:
    """Tarzların 2B konumu — birlikte-üyelikten klasik MDS.

    Benzerlik S_ik = kosinüs(u_·i, u_·k): iki tarz aynı albümlerde birlikte
    yüksek üyelik alıyorsa yakın. Uzaklık √(2 − 2S). Konum, albüm uzayından
    değil tarzların birbirine KARIŞMASINDAN geliyor; eksenlerin anlamı yok,
    yalnız yakınlık okunur.
    """
    c = U.shape[1]
    if c < 2:
        return np.zeros((c, 2))
    norm = np.linalg.norm(U, axis=0)
    S = (U.T @ U) / np.maximum(np.outer(norm, norm), 1e-12)
    D2 = np.clip(2 - 2 * S, 0, None)
    J = np.eye(c) - 1.0 / c
    B = -0.5 * J @ D2 @ J
    deger, vektor = np.linalg.eigh(B)
    sira = np.argsort(deger)[::-1][:2]
    X = vektor[:, sira] * np.sqrt(np.clip(deger[sira], 0, None))
    if X.shape[1] < 2:
        X = np.hstack([X, np.zeros((c, 2 - X.shape[1]))])
    # İşaret belirsizliğini sabitle: tekrarlanabilir yerleşim (K2).
    for k in range(2):
        if X[np.argmax(np.abs(X[:, k])), k] < 0:
            X[:, k] *= -1
    return X


def pano(conn: sqlite3.Connection, calisma_id: str | None) -> dict | None:
    """Etkileşimli pano için tarz başına her şey — tek geçişte."""
    if not calisma_id:
        return None
    uy = pd.read_sql_query(
        """SELECT m.album_id, m.kume_id, m.uyelik, a.artist, a.year
             FROM memberships m JOIN albums a USING (album_id)
            WHERE m.calisma_id = ?""", conn, params=(calisma_id,))
    if uy.empty:
        return None
    U_df = uy.pivot_table(index="album_id", columns="kume_id", values="uyelik", fill_value=0.0)
    bilgi = uy.drop_duplicates("album_id").set_index("album_id")[["artist", "year"]]
    keskin = U_df.idxmax(axis=1)
    boyut = keskin.value_counts()
    sira = list(boyut.index)                       # büyükten küçüğe: renk sırası
    renk_sirasi = {int(k): (i if i < RENKLI_TARZ else None) for i, k in enumerate(sira)}

    X = tarz_haritasi(U_df.to_numpy())
    konum = {int(k): X[i] for i, k in enumerate(U_df.columns)}
    xs, ys = X[:, 0], X[:, 1]
    olcek = lambda v, lo, hi: 0.5 if hi - lo < 1e-9 else (v - lo) / (hi - lo)  # noqa: E731

    tempo = {}
    try:
        tempo = dict(conn.execute(
            "SELECT album_id, tempo_medyan FROM audio_features WHERE kaynak = 'yerel' "
            "AND tempo_medyan > 0").fetchall())
    except sqlite3.Error:
        pass

    onyillar = sorted({int(y) // 10 * 10 for y in bilgi["year"].dropna() if y and y > 1900})
    tarzlar = []
    for k in sira:
        k = int(k)
        uyeler = keskin[keskin == k].index
        sanatci = bilgi.loc[uyeler, "artist"].value_counts()
        yillar = [int(y) // 10 * 10 for y in bilgi.loc[uyeler, "year"].dropna() if y and y > 1900]
        t = [float(tempo[a]) for a in uyeler if a in tempo]
        tarzlar.append({
            "kume": k, "renk": renk_sirasi[k], "album": int(boyut[k]),
            "x": olcek(konum[k][0], xs.min(), xs.max()),
            "y": olcek(konum[k][1], ys.min(), ys.max()),
            "sanatcilar": [(a, int(n)) for a, n in sanatci.head(5).items()],
            "onyil": {o: yillar.count(o) for o in onyillar},
            "tempo": (float(np.median(t)), float(np.percentile(t, 25)), float(np.percentile(t, 75)))
                     if len(t) >= 3 else None,
            "uyum": float(U_df.loc[uyeler, k].mean()),
        })
    tum_tempo = [float(v) for v in tempo.values()]
    return {"tarzlar": tarzlar, "onyillar": onyillar,
            "tempo_alan": (min(tum_tempo), max(tum_tempo)) if len(tum_tempo) >= 3 else None,
            "sanatci_tarzi": {a: int(keskin[g.index].mode().iloc[0])
                              for a, g in bilgi.groupby("artist")}}
