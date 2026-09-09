"""Adayın, bir eksenin SESİNE ne kadar uzak olduğu.

`bilincli_uzaklik` stratejisi ölçüldü ve sınırı görüldü: kalabalık grafiğinde
iki adım gitmek, kütüphanenin niş olduğu eksende çok iyi çalışıyor (jazz-fusion
ekseni city pop getirdi) ama mainstream olduğu eksende çalışmıyor — hip-hop
ekseninden iki adım gidince yine Drake çıkıyor. Sebep basit: kalabalık grafiğinin
elinde "bu ikisi kulağa farklı geliyor" bilgisi YOK.

O bilgi burada var. Hem kütüphanenin hem adayların ayrılmış stem ölçümleri
`stem_profili`'nde duruyor (K12). Bu modül ikisini aynı ölçeğe koyup mesafeyi
hesaplıyor, böylece "iki adım ötede" olan aday ayrıca "kulağa da farklı geliyor"
diye süzülebiliyor.

## Ölçek: kütüphane sigması

Standartlaştırma KÜTÜPHANE dağılımıyla yapılıyor, aday havuzuyla değil. Sebep:
mesafenin birimi "bu kütüphanede bir standart sapma" olmalı. Aday havuzuyla
ölçeklenirse birim, o gün hangi adayların üretildiğine göre değişir ve iki
çalışma arasındaki sayılar kıyaslanamaz hale gelir.

## Eksik stem sorunu

Enstrümantal albümde vokal stem'i yok, aday klibinde bas ölçülememiş olabilir.
Eksik boyutu medyanla DOLDURMUYORUZ — doldurmak "bu albümün vokali ortalama"
demek olurdu, oysa vokali yok. Mesafe yalnız İKİ TARAFTA DA ölçülmüş boyutlarda
hesaplanır ve kaç boyuttan hesaplandığı `boyut` alanında döner; az boyuttan
çıkan mesafeye güvenilmemeli.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

#: Stem başına kullanılacak ölçütler. `muzisyen.ROL_SUTUNLARI`'ndan geliyor —
#: yani `olcut_denetimi`'nin artık-varyans elemesinden geçmiş küme. Elenmiş
#: sütunları buraya koymak mesafeyi aynı bilgiyi iki kez sayarak şişirirdi.
def _stem_sutunlari() -> dict[str, tuple[str, ...]]:
    from python.muzisyen import ROL_SUTUNLARI

    return {
        "drums": ROL_SUTUNLARI["drums"],
        "bass": ROL_SUTUNLARI["bass"],
        "other": ROL_SUTUNLARI["guitar"],
        "vocals": ROL_SUTUNLARI["vocals"],
    }


def kutuphane_olcegi(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    """Stem × ölçüt için kütüphanenin medyan ve standart sapması.

    Standart sapma sıfırsa 1'e çekilir: sabit bir sütun mesafeye katkı vermez,
    sıfıra bölünmez.
    """
    ham = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'album'", conn
    )
    olcek: dict[str, pd.DataFrame] = {}
    for stem, sutunlar in _stem_sutunlari().items():
        x = ham[ham["stem"] == stem]
        mevcut = [s for s in sutunlar if s in x.columns]
        if x.empty or not mevcut:
            continue
        sayisal = x[mevcut].astype(float)
        sapma = sayisal.std()
        sapma[sapma == 0] = 1.0
        olcek[stem] = pd.DataFrame({"medyan": sayisal.median(), "sapma": sapma})
    return olcek


def eksen_ses_merkezi(
    conn: sqlite3.Connection, calisma_id: str, eksen: int
) -> dict[str, pd.Series]:
    """Eksenin ses merkezi: üyesi albümlerin stem başına medyanı.

    Albüm eksene KESKİN atanıyor (en yüksek üyelik). Bulanık ağırlıklı medyan
    tanımlı ama kenar üyeler merkezi bulanıklaştırıyor; merkez "bu eksen nasıl
    seslenir" sorusunun cevabı olmalı, "eksene biraz benzeyen her şey" değil.
    """
    uyelik = pd.read_sql_query(
        "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id = ?",
        conn, params=(calisma_id,),
    )
    if uyelik.empty:
        return {}
    U = uyelik.pivot(index="album_id", columns="kume_id", values="uyelik").fillna(0.0)
    if eksen not in U.columns:
        return {}
    uyeler = set(U.index[U.idxmax(axis=1) == eksen])
    if len(uyeler) < 3:
        return {}

    ham = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'album'", conn
    )
    merkez: dict[str, pd.Series] = {}
    for stem, sutunlar in _stem_sutunlari().items():
        x = ham[(ham["stem"] == stem) & ham["album_id"].isin(uyeler)]
        mevcut = [s for s in sutunlar if s in x.columns]
        if len(x) < 3 or not mevcut:
            continue
        merkez[stem] = x[mevcut].astype(float).median()
    return merkez


def aday_uzakligi(
    aday_stemleri: pd.DataFrame,
    merkez: dict[str, pd.Series],
    olcek: dict[str, pd.DataFrame],
) -> tuple[float | None, int, dict[str, float]]:
    """Adayın eksen merkezine standartlaştırılmış uzaklığı.

    Dönen: (uzaklık, kaç boyuttan hesaplandı, stem başına uzaklık).

    Stem başına Öklid mesafesi alınıp BOYUT SAYISINA bölünüyor (kök ortalama
    kare). Ham Öklid kullanılsaydı çok stem'i ölçülmüş bir aday, yalnızca davulu
    ölçülmüş bir adaydan otomatik olarak "daha uzak" çıkardı — mesafe boyut
    sayısıyla büyür. Normalize edilince farklı kapsamalı adaylar kıyaslanabilir.
    """
    if aday_stemleri.empty or not merkez:
        return None, 0, {}

    stem_uzakliklari: dict[str, float] = {}
    toplam_kare, toplam_boyut = 0.0, 0
    for stem, m in merkez.items():
        if stem not in olcek:
            continue
        satir = aday_stemleri[aday_stemleri["stem"] == stem]
        if satir.empty:
            continue
        satir = satir.iloc[0]
        # Yalnız iki tarafta da ÖLÇÜLMÜŞ boyutlar. Eksik boyutu medyanla
        # doldurmak "vokali ortalama" demek olurdu; oysa vokali yok.
        boyutlar = [
            s for s in m.index
            if s in satir.index and pd.notna(satir[s]) and pd.notna(m[s])
            and s in olcek[stem].index
        ]
        if not boyutlar:
            continue
        fark = np.array(
            [(float(satir[s]) - float(m[s])) / float(olcek[stem].loc[s, "sapma"])
             for s in boyutlar]
        )
        kare = float((fark**2).sum())
        stem_uzakliklari[stem] = float(np.sqrt(kare / len(boyutlar)))
        toplam_kare += kare
        toplam_boyut += len(boyutlar)

    if toplam_boyut == 0:
        return None, 0, {}
    return float(np.sqrt(toplam_kare / toplam_boyut)), toplam_boyut, stem_uzakliklari


def eksen_uzakliklari(
    conn: sqlite3.Connection, calisma_id: str, eksen: int
) -> pd.DataFrame:
    """Bu eksenin tüm adayları için ses uzaklığı — en uzaktan en yakına.

    Referans olarak KÜTÜPHANENİN kendi dağılımı da veriliyor: adayın uzaklığını
    tek başına okumak zor ("2.1 sigma çok mu?"), ama kütüphanenin kendi
    albümlerinin o eksene uzaklık dağılımıyla kıyaslanınca anlam kazanıyor.
    """
    merkez = eksen_ses_merkezi(conn, calisma_id, eksen)
    olcek = kutuphane_olcegi(conn)
    if not merkez or not olcek:
        return pd.DataFrame()

    adaylar = pd.read_sql_query(
        """
        SELECT DISTINCT aday_id, artist, title, strateji
          FROM adaylar WHERE calisma_id = ? AND eksen = ?
        """,
        conn, params=(calisma_id, eksen),
    )
    if adaylar.empty:
        return pd.DataFrame()

    stemler = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'aday'", conn
    )
    satirlar = []
    for kayit in adaylar.itertuples():
        uzaklik, boyut, kirilim = aday_uzakligi(
            stemler[stemler["album_id"] == kayit.aday_id], merkez, olcek
        )
        if uzaklik is None:
            continue
        satirlar.append({
            "aday_id": kayit.aday_id,
            "artist": kayit.artist,
            "title": kayit.title,
            "strateji": kayit.strateji,
            "ses_uzakligi": round(uzaklik, 3),
            "boyut": boyut,
            **{f"uz_{k}": round(v, 3) for k, v in kirilim.items()},
        })
    return pd.DataFrame(satirlar).sort_values("ses_uzakligi", ascending=False)


def kutuphane_uzaklik_dagilimi(
    conn: sqlite3.Connection, calisma_id: str, eksen: int
) -> pd.Series:
    """Kütüphanenin KENDİ albümlerinin bu eksene uzaklığı — kıyas tabanı.

    Eksenin kendi üyeleri doğal olarak yakın, başka eksenlerin üyeleri uzak.
    Bir adayın "2.1 sigma uzak" olması ancak bu dağılıma göre anlam taşır.
    """
    merkez = eksen_ses_merkezi(conn, calisma_id, eksen)
    olcek = kutuphane_olcegi(conn)
    if not merkez or not olcek:
        return pd.Series(dtype=float)
    stemler = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'album'", conn
    )
    degerler = {}
    for album_id, grup in stemler.groupby("album_id"):
        uzaklik, boyut, _ = aday_uzakligi(grup, merkez, olcek)
        if uzaklik is not None and boyut >= 5:
            degerler[album_id] = uzaklik
    return pd.Series(degerler, dtype=float)
