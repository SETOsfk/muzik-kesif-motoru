"""Faz 2 — eksene özgü aday üretimi ve şablonlu gerekçe (K7).

Sistem karar vermez, kullanıcıya sorar: "hangi tarafını beslemek istiyorsun?"
Aday üretimi bu yüzden EKSEN başına yapılır, kütüphane geneli için değil. Bu bir
tercih değil, ölçülmüş bir zorunluluk: kütüphane genelinde toplanan komşuluk
sinyali AC/DC ve The Beatles veriyor; eksen bazında toplananı jazz-fusion ekseni
için Spyro Gyra ve Victor Wooten veriyor (bkz. karar günlüğü).

İki strateji:

**kredi_sicramasi** — ekseni AYIRT EDEN müzisyenlerin, kullanıcının duymadığı
projeleri. Projenin çekirdek tezi bu: "iyi davulcu dinleyen adam" bilgisi kredide
yatar. Discogs üzerinden yürür, çünkü MusicBrainz "bu müzisyenin çaldığı albümler"
sorgusunu vermiyor — `artist=` araması yalnızca ASIL SANATÇI olduğu kayıtları
döndürür, davulcu olarak çaldıklarını değil.

**sahne_komsulugu** — eksendeki sanatçıları dinleyenlerin dinlediği, kullanıcıda
olmayan sanatçılar (ListenBrainz).

Gerekçe K7'ye göre şablonla üretilir ve boşlukları sorgudan gelen GERÇEK sayılarla
dolar. Uydurma yok: her cümlenin arkasındaki sayı `dayanak` alanında saklanır.

Kullanım:
    python -m python.discover.adaylar --eksen 5
    python -m python.discover.adaylar --tum-eksenler --adet 10
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from collections import defaultdict
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from python.db import VARSAYILAN_DB, baglan
from python.enrich.rol_eslemesi import ENSTRUMAN_ROLLERI
from python.discover.listenbrainz import (
    benzer_sanatcilar,
    listenbrainz,
    sanatci_mbid_bul,
)
from python.metin import album_kimligi, normalize_esleme
from python.onbellek import AgYok, ApiIstemci, discogs, musicbrainz

#: Discogs sanatçı adlarındaki ayırt edici son ek: "Gojira (2)" → "Gojira".
_DISCOGS_SONEK = re.compile(r"\s*\(\d+\)\s*$")

#: Derleme / promo / video gibi öneriye uygun olmayan biçimler.
_ISTENMEYEN_BICIM = ("comp", "promo", "vhs", "dvd", "single", "sampler", "interview")

#: Discogs topluluk koleksiyonu eşiği. Oyun müziği, tren hattı açılış BGM'i ve
#: paket listeleri ("Fortitude + Magma") bu eşiğin altında kalıyor; gerçek albümler
#: yüzlerce/binlerce koleksiyonda (ölçüldü: Gojira Fortitude 4892, oyun müziği 2).
ASGARI_KOLEKSIYON = 25

#: Bir müzisyenden en fazla kaç aday. Olmazsa tek kişi listeyi dolduruyor:
#: Casiopea'nın klavyecisi Minoru Mukaiya tek başına 6 adayın 6'sını almıştı.
KISI_BASINA_AZAMI = 2

#: Başlıkta geçerse derleme/canlı sayılır. Discogs'un `format` alanı master
#: kayıtlarda boş geldiği için biçim süzgeci orada işlemiyor; başlık tek dayanak.
_DERLEME_IZLERI = (
    "best of", "greatest", "collection", "anthology", "compilation", "\u30d9\u30b9\u30c8",
    "live at", "live in", "live and best", "the very best", "essential",
    "singles", "b-sides", "rarities", "box set", "complete works",
)


def _temiz_ad(ad: str) -> str:
    return _DISCOGS_SONEK.sub("", (ad or "").strip())


@dataclass
class Aday:
    artist: str
    title: str
    year: int | None
    strateji: str
    eksen: int
    skor: float
    gerekce: str
    dayanak: dict = field(default_factory=dict)
    mbid: str | None = None
    discogs_id: str | None = None

    @property
    def aday_id(self) -> str:
        return album_kimligi(self.artist, self.title, self.year)


# --------------------------------------------------------------------------- #
# Ortak: eksenin kadrosu ve sanatçıları
# --------------------------------------------------------------------------- #

def eksen_muzisyenleri(
    conn: sqlite3.Connection,
    calisma_id: str,
    eksen: int,
    adet: int = 12,
    *,
    sadece_icraci: bool = True,
) -> pd.DataFrame:
    """Ekseni AYIRT EDEN müzisyenler (lift) — Discogs kimliğiyle birlikte.

    Sık geçen değil ayırt eden: kütüphanede çok albümü olan biri her eksende
    listenin başına çıkar ve o eksene özgü hiçbir şey söylemez.
    """
    uyelik = pd.read_sql_query(
        "SELECT album_id, uyelik FROM memberships WHERE calisma_id=? AND kume_id=?",
        conn, params=(calisma_id, eksen),
    ).set_index("album_id")["uyelik"]
    if uyelik.empty:
        return pd.DataFrame()

    kume_sayisi = conn.execute(
        "SELECT COUNT(*) FROM clusters WHERE calisma_id=?", (calisma_id,)
    ).fetchone()[0] or 1
    taban = 1.0 / kume_sayisi

    krediler = pd.read_sql_query(
        """SELECT album_id, person_name, person_id, role FROM credits
           WHERE person_id LIKE 'discogs:%'""",
        conn,
    )
    if krediler.empty:
        return pd.DataFrame()

    krediler["anahtar"] = krediler["person_name"].map(normalize_esleme)
    krediler = krediler[krediler["anahtar"] != ""]
    tekil = krediler.drop_duplicates(["anahtar", "album_id"])

    agirlik = tekil["album_id"].map(uyelik).fillna(0.0)
    tekil = tekil.assign(agirlik=agirlik.where(agirlik >= taban, 0.0))

    toplam_uyelik = float(uyelik[uyelik >= taban].sum()) or 1.0
    albüm_sayisi = float(len(uyelik)) or 1.0

    kume_payi = tekil.groupby("anahtar")["agirlik"].sum() / toplam_uyelik
    genel_payi = tekil.groupby("anahtar")["album_id"].nunique() / albüm_sayisi
    sahip_album = tekil.groupby("anahtar")["album_id"].nunique()

    cerceve = pd.DataFrame({
        "kume_payi": kume_payi,
        "genel_payi": genel_payi,
        "sahip_album": sahip_album,
    }).fillna(0.0)
    cerceve["lift"] = cerceve["kume_payi"] - cerceve["genel_payi"]
    cerceve["ad"] = krediler.groupby("anahtar")["person_name"].first()
    cerceve["discogs_id"] = (
        krediler.groupby("anahtar")["person_id"].first().str.replace("discogs:", "", regex=False)
    )
    cerceve["roller"] = (
        krediler.groupby("anahtar")["role"].apply(lambda r: sorted(set(r)))
    )
    # Kredi sıçraması ÇALAN kişiden gider. Mühendis/mix kredisi de bir bağdır ama
    # "bu albümü şu mix mühendisi mikslemiş" zayıf bir gerekçedir; projenin tezi
    # "kim çaldı". Üretim rolleri sahne komşuluğu stratejisine bırakılır.
    if sadece_icraci:
        cerceve = cerceve[
            cerceve["roller"].apply(lambda roller: bool(set(roller) & ENSTRUMAN_ROLLERI))
        ]
    return (
        cerceve[cerceve["kume_payi"] > 0]
        .sort_values("lift", ascending=False)
        .head(adet)
    )


def eksen_sanatcilari(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, adet: int = 8
) -> pd.DataFrame:
    """Eksene keskin atanmış albümlerin sanatçıları, üyelik ağırlıklı."""
    veri = pd.read_sql_query(
        """SELECT m.album_id, m.uyelik, a.artist
             FROM memberships m JOIN albums a USING (album_id)
            WHERE m.calisma_id = ?""",
        conn, params=(calisma_id,),
    )
    if veri.empty:
        return pd.DataFrame()
    tum = pd.read_sql_query(
        "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id=?",
        conn, params=(calisma_id,),
    ).pivot(index="album_id", columns="kume_id", values="uyelik")
    keskin = tum.idxmax(axis=1)
    sanatci = veri.drop_duplicates("album_id").set_index("album_id")["artist"]
    ait = keskin[keskin == eksen].index
    return (
        pd.DataFrame({"artist": sanatci.reindex(ait), "uyelik": tum.loc[ait, eksen]})
        .groupby("artist")
        .agg(albüm=("uyelik", "size"), uyelik=("uyelik", "mean"))
        .sort_values(["albüm", "uyelik"], ascending=False)
        .head(adet)
    )


def kutuphane_anahtarlari(conn: sqlite3.Connection) -> set[str]:
    """Sahip olunan albümlerin normalize anahtarları — aday elemek için."""
    return {
        f"{normalize_esleme(s['artist'])}|{normalize_esleme(s['title'])}"
        for s in conn.execute("SELECT artist, title FROM albums")
    }


# --------------------------------------------------------------------------- #
# Sıra kaynaşması — iki sinyali birleştirme
# --------------------------------------------------------------------------- #

#: RRF sabiti. Alan yazınında 60 standart; üst sıraların birbirine karşı
#: ezici üstünlük kurmasını engelliyor. 1/(k+sıra) eğrisi k büyüdükçe
#: düzleşir, yani k listelerin uzlaşmasına ne kadar güveneceğimizi ayarlar.
RRF_K = 60


def melez_sirala(
    siralamalar: list[list[str]], *, agirliklar: list[float] | None = None,
    k: int = RRF_K,
) -> list[str]:
    """Karşılıklı sıra kaynaşması (reciprocal rank fusion).

    skor(x) = Σ_i  a_i / (k + sıra_i(x))

    NEDEN SKOR TOPLAMI DEĞİL SIRA TOPLAMI. İki sinyalin ölçekleri
    kıyaslanamaz: npmi [-1, +1], hubness düzeltmeli CLAP kabaca [-0.35, 0].
    Ham toplam ölçeği büyük olanın kararı olurdu; z-skoru ise dağılımların
    normal olduğunu varsayardı ve ölçüldü, ikisi de değil. Sıra kaynaşması
    ölçekten bağımsız ve alan yazınında bu iş için standart.

    LİSTEDE OLMAMAK CEZALANDIRILIR ama sıfırlamaz: bir listede birinci, diğer
    listede hiç olmayan aday 1/(k+1) alır; iki listede de ellinci olan aday
    2/(k+50) alır ve ikincisi kazanır. İstenen tam olarak bu — projenin
    tekrar eden deseni burada da geçerli: KESİŞİM bir sönümleme çarpanı
    olarak değil, sıralama ölçütü olarak kullanılıyor.

    `agirliklar` sinyallerin gücü farklıysa: leave-one-artist-out ölçümünde
    çalma listesi sinyali rastgeleye göre 5,4 kat, CLAP 1,4 kat iyiydi.
    """
    if agirliklar is None:
        agirliklar = [1.0] * len(siralamalar)
    skor: dict[str, float] = defaultdict(float)
    for agirlik, siralama in zip(agirliklar, siralamalar):
        for sira, aday in enumerate(siralama, 1):
            skor[aday] += agirlik / (k + sira)
    return [a for a, _ in sorted(skor.items(), key=lambda x: -x[1])]


# --------------------------------------------------------------------------- #
# Strateji 1 — kredi sıçraması
# --------------------------------------------------------------------------- #

def kredi_sicramasi(
    conn: sqlite3.Connection,
    dc: ApiIstemci,
    calisma_id: str,
    eksen: int,
    *,
    kisi_adedi: int = 8,
    kisi_basina: int = 40,
) -> list[Aday]:
    muzisyenler = eksen_muzisyenleri(conn, calisma_id, eksen, adet=kisi_adedi)
    if muzisyenler.empty:
        return []

    sahip = kutuphane_anahtarlari(conn)
    kume_adi = _eksen_adi(conn, calisma_id, eksen)
    toplanan: dict[str, Aday] = {}
    kisi_adaylari: dict[str, list[str]] = {}

    for anahtar, kisi in muzisyenler.iterrows():
        try:
            govde = dc.get_json(
                f"artists/{kisi['discogs_id']}/releases",
                {"per_page": kisi_basina, "sort": "year", "sort_order": "desc"},
            )
        except AgYok:
            continue
        if not govde:
            continue

        # Kullanıcının bu kişiden sahip olduğu albümlerden örnek — gerekçede geçecek.
        ornekler = [
            f"{s['artist']} — {s['title']}"
            for s in conn.execute(
                """SELECT DISTINCT a.artist, a.title FROM credits c
                     JOIN albums a USING (album_id)
                    WHERE c.person_id = ? LIMIT 3""",
                (f"discogs:{kisi['discogs_id']}",),
            )
        ]
        icraci_rolleri = [r for r in kisi["roller"] if r in ENSTRUMAN_ROLLERI]
        roller = ", ".join((icraci_rolleri or kisi["roller"])[:3])

        for kayit in govde.get("releases", []):
            if kayit.get("role") not in ("Appearance", "Main"):
                continue
            if kayit.get("type") != "master":
                continue  # master = baskılar tekilleşmiş hâli
            sanatci = _temiz_ad(kayit.get("artist", ""))
            baslik = (kayit.get("title") or "").strip()
            if not sanatci or not baslik or sanatci.lower() == "various":
                continue
            bicim = str(kayit.get("format") or "").lower()
            if any(x in bicim for x in _ISTENMEYEN_BICIM):
                continue
            if any(x in baslik.lower() for x in _DERLEME_IZLERI):
                continue  # derleme/canlı: kullanıcı zaten sanatçıyı tanıyor
            # Çok sanatçılı derleme kaydı: "A = B*, C = D*, E" gibi adlar.
            if sanatci.count(",") >= 2:
                continue
            anahtar_aday = f"{normalize_esleme(sanatci)}|{normalize_esleme(baslik)}"
            if anahtar_aday in sahip:
                continue  # zaten kütüphanede

            koleksiyon = int(
                ((kayit.get("stats") or {}).get("community") or {}).get("in_collection", 0)
            )
            if koleksiyon < ASGARI_KOLEKSIYON:
                continue  # oyun müziği, promo paketi, kimsenin sahip olmadığı kayıt

            yil = kayit.get("year") or None
            # Skoru koleksiyon büyüklüğüyle logaritmik olarak ölçekle: aynı
            # müzisyenin albümleri arasında hangisinin daha yerleşik olduğunu
            # ayırt etmenin tek elimizdeki sinyali bu.
            skor = float(kisi["lift"]) * float(kisi["sahip_album"]) * math.log10(koleksiyon)
            gerekce = (
                f"{roller.capitalize()} olarak {kisi['ad']} var. "
                f"Kütüphanende onun çaldığı {int(kisi['sahip_album'])} albüm var"
                + (f" ({', '.join(ornekler[:2])})" if ornekler else "")
                + f" ve bu isim «{kume_adi}» ekseninde ayırt edici. "
                f"Bu albümü hiç dinlememişsin."
            )
            mevcut = toplanan.get(anahtar_aday)
            if mevcut and mevcut.skor >= skor:
                continue
            liste = kisi_adaylari.setdefault(anahtar, [])
            if anahtar_aday not in liste:
                liste.append(anahtar_aday)
            toplanan[anahtar_aday] = Aday(
                artist=sanatci,
                title=baslik,
                year=int(yil) if isinstance(yil, int) or str(yil).isdigit() else None,
                strateji="kredi_sicramasi",
                eksen=eksen,
                skor=round(skor, 4),
                gerekce=gerekce,
                dayanak={
                    "muzisyen": kisi["ad"],
                    "roller": kisi["roller"],
                    "eksende_lift": round(float(kisi["lift"]), 4),
                    "kutuphanedeki_album": int(kisi["sahip_album"]),
                    "ornek_albumler": ornekler,
                    "discogs_koleksiyon": koleksiyon,
                },
                discogs_id=str(kayit.get("id")),
            )

    # Kişi başına en iyi N aday, sonra kişiler arasında dönüşümlü sıralama.
    # Amaç eksenin KADROSUNU göstermek; tek bir müzisyenin diskografisini değil.
    sirali: list[Aday] = []
    kisi_listeleri = [
        sorted((toplanan[k] for k in anahtarlar), key=lambda a: -a.skor)[:KISI_BASINA_AZAMI]
        for anahtarlar in kisi_adaylari.values()
    ]
    kisi_listeleri.sort(key=lambda liste: -(liste[0].skor if liste else 0))
    for sira in range(KISI_BASINA_AZAMI):
        for liste in kisi_listeleri:
            if sira < len(liste):
                sirali.append(liste[sira])
    return sirali


# --------------------------------------------------------------------------- #
# Strateji 2 — sahne komşuluğu
# --------------------------------------------------------------------------- #

def sahne_komsulugu(
    conn: sqlite3.Connection,
    mb: ApiIstemci,
    lb: ApiIstemci,
    calisma_id: str,
    eksen: int,
    *,
    sanatci_adedi: int = 6,
    komsu_adedi: int = 15,
    album_adedi: int = 4,
) -> list[Aday]:
    sanatcilar = eksen_sanatcilari(conn, calisma_id, eksen, adet=sanatci_adedi)
    if sanatcilar.empty:
        return []

    sahip_sanatci = {
        normalize_esleme(s["artist"]) for s in conn.execute("SELECT DISTINCT artist FROM albums")
    }
    sahip = kutuphane_anahtarlari(conn)
    kume_adi = _eksen_adi(conn, calisma_id, eksen)

    # İsim eşleşmesi tek başına yetmiyor: ListenBrainz "Masayoshi Takanaka"yı
    # 高中正義 olarak döndürüyor ve kullanıcının kütüphanesinde romanize adı var.
    # Aynı sanatçı iki yazımda iki ayrı kişi sanılınca sahip olunan sanatçı
    # "keşif" diye önerildi (ölçüldü: ilk 5 adayın 4'ü). MBID tek doğru kimlik.
    sahip_mbid: set[str] = set()

    komsu_skor: dict[str, dict] = {}
    for ad, satir in sanatcilar.iterrows():
        try:
            mbid = sanatci_mbid_bul(mb, ad)
            if not mbid:
                continue
            sahip_mbid.add(mbid)
            komsular = benzer_sanatcilar(lb, mbid)[:komsu_adedi]
        except AgYok:
            continue
        en_buyuk = max((k.skor for k in komsular), default=0) or 1
        for komsu in komsular:
            anahtar = normalize_esleme(komsu.ad)
            if not anahtar or anahtar in sahip_sanatci:
                continue
            if komsu.mbid and komsu.mbid in sahip_mbid:
                continue  # aynı sanatçı, başka yazım (bkz. yukarıdaki not)
            kayit = komsu_skor.setdefault(
                anahtar,
                {"ad": komsu.ad, "mbid": komsu.mbid, "skor": 0.0, "kaynaklar": []},
            )
            kayit["skor"] += (komsu.skor / en_buyuk) * float(satir["albüm"])
            kayit["kaynaklar"].append(ad)

    # Tüm eksen sanatçıları çözüldükten sonra son bir süzme: ilk turlarda henüz
    # bilinmeyen MBID'ler yüzünden içeri sızmış olabilirler.
    for anahtar in [a for a, k in komsu_skor.items() if k["mbid"] in sahip_mbid]:
        komsu_skor.pop(anahtar, None)

    # Eksende BİRDEN FAZLA sanatçının işaret ettiği komşular önce: kesişim
    # popülerliği söndürüyor (ölçüldü — tek kaynaklı komşular mainstream çıkıyor).
    sirali = sorted(
        komsu_skor.values(),
        key=lambda k: (-len(set(k["kaynaklar"])), -k["skor"]),
    )

    adaylar: list[Aday] = []
    for kayit in sirali[:10]:
        if not kayit["mbid"]:
            continue
        try:
            # Okunabilir ad: MusicBrainz'de asıl ad Japonca olabiliyor
            # (高中正義). Latin yazımlı takma ad varsa onu göster, özgün adı
            # parantezde tut — kullanıcı hem okuyabilsin hem aratabilsin.
            kayit["gorunen_ad"] = _okunabilir_ad(mb, kayit["mbid"], kayit["ad"])
            govde = mb.get_json(
                "release-group",
                {"artist": kayit["mbid"], "type": "album", "fmt": "json", "limit": 25},
            )
        except AgYok:
            continue
        gruplar = gercek_albumler((govde or {}).get("release-groups", []))

        kaynak_sayisi = len(set(kayit["kaynaklar"]))
        for grup in gruplar[:album_adedi]:
            baslik = grup.get("title", "").strip()
            anahtar_aday = f"{normalize_esleme(kayit['ad'])}|{normalize_esleme(baslik)}"
            if not baslik or anahtar_aday in sahip:
                continue
            yil = (grup.get("first-release-date") or "")[:4]
            kaynak_adlari = sorted(set(kayit["kaynaklar"]))[:3]
            kimler = ", ".join(kaynak_adlari)
            isaret = "Bunları" if len(kaynak_adlari) > 1 else "Onu"
            gosterilecek = kayit.get("gorunen_ad") or kayit["ad"]
            gerekce = (
                f"«{kume_adi}» ekseninde {kimler} dinliyorsun. "
                f"{isaret} dinleyenler {gosterilecek}'i de dinliyor"
                + (f" ({kaynak_sayisi} ayrı sanatçından işaret geldi)." if kaynak_sayisi > 1
                   else " (tek sanatçıdan işaret — daha zayıf).")
            )
            adaylar.append(
                Aday(
                    artist=gosterilecek,
                    title=baslik,
                    year=int(yil) if yil.isdigit() else None,
                    strateji="sahne_komsulugu",
                    eksen=eksen,
                    skor=round(kayit["skor"] * kaynak_sayisi, 4),
                    gerekce=gerekce,
                    dayanak={
                        "kaynak_sanatcilar": sorted(set(kayit["kaynaklar"])),
                        "kaynak_sayisi": kaynak_sayisi,
                        "komsuluk_skoru": round(kayit["skor"], 4),
                        "ozgun_ad": kayit["ad"],
                    },
                    mbid=grup.get("id"),
                )
            )
    return sorted(adaylar, key=lambda a: -a.skor)


# --------------------------------------------------------------------------- #
# Strateji 3: bilinçli uzaklık
# --------------------------------------------------------------------------- #

def _ikinci_adim_havuzu(
    conn: sqlite3.Connection,
    mb: ApiIstemci,
    lb: ApiIstemci,
    calisma_id: str,
    eksen: int,
    *,
    sanatci_adedi: int = 5,
    komsu_adedi: int = 12,
    kopru_adedi: int = 8,
) -> dict[str, dict]:
    """Eksenden İKİ ADIM ötedeki sanatçı havuzu — albüm çekmeden, yalnız isim.

        eksen sanatçıların  →  1. adım komşular  →  2. adım komşular
                                  (köprüler)          (bu havuz)

    Havuzdan köprüler ve sahip olunanlar çıkarılır: geriye senin sahnene bir
    köprüyle bağlı ama DOĞRUDAN komşun olmayanlar kalır. Albüm çekme ayrı
    tutuldu çünkü havuz, eksen-özgüllüğü hesabı için tüm eksenlerde ayrı ayrı
    gerekiyor ve o aşamada albüme ihtiyaç yok.
    """
    sanatcilar = eksen_sanatcilari(conn, calisma_id, eksen, adet=sanatci_adedi)
    if sanatcilar.empty:
        return {}

    sahip_sanatci = {
        normalize_esleme(s["artist"]) for s in conn.execute("SELECT DISTINCT artist FROM albums")
    }

    birinci: dict[str, dict] = {}
    sahip_mbid: set[str] = set()
    for ad, _satir in sanatcilar.iterrows():
        try:
            mbid = sanatci_mbid_bul(mb, ad)
            if not mbid:
                continue
            sahip_mbid.add(mbid)
            for komsu in benzer_sanatcilar(lb, mbid)[:komsu_adedi]:
                if komsu.mbid:
                    birinci.setdefault(
                        komsu.mbid, {"ad": komsu.ad, "kaynaklar": set()}
                    )["kaynaklar"].add(ad)
        except AgYok:
            continue
    if not birinci:
        return {}

    kopruler = sorted(birinci.items(), key=lambda k: -len(k[1]["kaynaklar"]))[:kopru_adedi]

    havuz: dict[str, dict] = {}
    for kopru_mbid, kopru in kopruler:
        try:
            uzaklar = benzer_sanatcilar(lb, kopru_mbid)[:komsu_adedi]
        except AgYok:
            continue
        en_buyuk = max((u.skor for u in uzaklar), default=0) or 1
        for uzak in uzaklar:
            anahtar = normalize_esleme(uzak.ad)
            if not anahtar or anahtar in sahip_sanatci:
                continue
            if uzak.mbid and (uzak.mbid in birinci or uzak.mbid in sahip_mbid):
                continue  # bir adım ötede — bu stratejinin konusu değil
            kayit = havuz.setdefault(
                anahtar,
                {"ad": uzak.ad, "mbid": uzak.mbid, "skor": 0.0, "kopruler": set()},
            )
            kayit["skor"] += uzak.skor / en_buyuk
            kayit["kopruler"].add(kopru["ad"])
    return havuz


def eksen_frekansi(
    conn: sqlite3.Connection, mb: ApiIstemci, lb: ApiIstemci, calisma_id: str
) -> dict[str, int]:
    """Her sanatçı kaç ayrı eksenin iki-adım havuzunda görünüyor.

    Bu, popülerlik sönümlemesinin paydası. LB çağrıları önbellekli (K5), yani
    tüm eksenleri taramak ilk seferden sonra bedavaya yakın.
    """
    eksenler = [
        r[0] for r in conn.execute(
            "SELECT kume_id FROM clusters WHERE calisma_id = ? AND stabil_mi = 1",
            (calisma_id,),
        )
    ]
    frekans: dict[str, int] = {}
    for e in eksenler:
        for anahtar in _ikinci_adim_havuzu(conn, mb, lb, calisma_id, e):
            frekans[anahtar] = frekans.get(anahtar, 0) + 1
    frekans["__eksen_sayisi__"] = len(eksenler)
    return frekans


def bilincli_uzaklik(
    conn: sqlite3.Connection,
    mb: ApiIstemci,
    lb: ApiIstemci,
    calisma_id: str,
    eksen: int,
    *,
    frekans: dict[str, int] | None = None,
    album_adedi: int = 3,
    **havuz_ayari,
) -> list[Aday]:
    """Kalabalık grafiğinde İKİ ADIM ötesi — komşunun komşusu, senin komşun değil.

    Projenin çıkış noktası kullanıcının cümlesiydi: "hep yerel kütüphanemi
    dinliyorum, bu böyle olunca yeni müzikler keşfedemiyorum." Diğer iki strateji
    bu döngüyü kırmıyor — `kredi_sicramasi` zaten dinlediğin müzisyenin başka
    işine, `sahne_komsulugu` doğrudan komşuya gidiyor; ikisi de bir adım yakında.

    **İlk sürüm ölçüldü ve BAŞARISIZDI.** Sıralama ölçütü "kaç ayrı köprü bu
    sanatçıya işaret ediyor" idi. Sonuç doğrudan mainstream'e düştü: Green Day,
    The Offspring, ve en fenası — Coldplay, Meshuggah/Slipknot/Gojira/Opeth
    kümesinde aday olarak çıktı. Sebebi yapısal: popüler sanatçıya çok köprü
    işaret eder, tam da popüler olduğu için. Köprü çeşitliliği bir keşif sinyali
    değil, popülerlik vekiliymiş.

    **İkinci deneme de yetmedi.** Eksen-özgüllüğü (TF-IDF) ÇARPAN olarak eklendi:
    `köprü_sayısı × skor × ln(1 + eksen/df)`. Ölçüldü — dokuz eksende eşik beşe
    çıkıyor ve yalnız Bob Dylan eleniyordu; Muse (df=3) ve The Offspring (df=4)
    listenin başında kalmaya devam etti. Sebep yapısal: skor zaten popülerlik
    vekili olan `köprü_sayısı` ile ÇARPILIYOR, zayıf bir IDF bunu çeviremiyor.

    **Çalışan çözüm: özgüllük ÇARPAN değil, BİRİNCİL SIRALAMA ölçütü.**
    Sıralama `(df artan, sonra köprü×skor azalan)`. Ölçüm bunu net söylüyor —
    metal ekseninde df=1 adaylar Motörhead, Anthrax, Children of Bodom, Dark
    Tranquillity, Arch Enemy, Soilwork; aynı eksende çarpımsal puanlamanın
    getirdikleri Green Day ve AC/DC idi.

    Köprü sayısı ile özgüllük GERİLİMLİ: çok köprüden işaret alan sanatçı, tam
    da popüler olduğu için birden çok eksende de görünüyor. df=1 adayların
    neredeyse hepsi tek köprülü. Müzikal sinyali taşıyan taraf özgüllük.

    Bu, `sahne_komsulugu`'ndaki kesişim ve `kume_kadrosu`'ndaki lift ölçütüyle
    aynı aile — bu projede popülerlik yanlılığı üçüncü kez aynı yolla çözülüyor
    ve üçünde de sıralama ölçütü olarak, sönümleme çarpanı olarak değil.
    """
    havuz = _ikinci_adim_havuzu(conn, mb, lb, calisma_id, eksen, **havuz_ayari)
    if not havuz:
        return []
    if frekans is None:
        frekans = eksen_frekansi(conn, mb, lb, calisma_id)

    sahip = kutuphane_anahtarlari(conn)
    kume_adi = _eksen_adi(conn, calisma_id, eksen)
    eksen_sayisi = max(1, frekans.get("__eksen_sayisi__", 1))

    for anahtar, kayit in havuz.items():
        df = max(1, frekans.get(anahtar, 1))
        kayit["df"] = df
        kayit["idf"] = math.log(1 + eksen_sayisi / df)
        kayit["destek"] = len(kayit["kopruler"]) * kayit["skor"]

    # Eksenlerin üçte biri ya da fazlasında görünen = küresel hub, elenir.
    # Sönümlemek yetmiyor (bkz. docstring): Coldplay'i "biraz daha az önerelim"
    # demek yanlış cevap, hiç önermemek doğru cevap.
    esik = max(2, (eksen_sayisi + 2) // 3)
    sirali = sorted(
        (k for k in havuz.values() if k["df"] < esik),
        key=lambda k: (k["df"], -k["destek"]),
    )

    adaylar: list[Aday] = []
    gorulen: set[str] = set()
    for kayit in sirali[:10]:
        if not kayit["mbid"]:
            continue
        try:
            kayit["gorunen_ad"] = _okunabilir_ad(mb, kayit["mbid"], kayit["ad"])
            govde = mb.get_json(
                "release-group",
                {"artist": kayit["mbid"], "type": "album", "fmt": "json", "limit": 25},
            )
        except AgYok:
            continue
        gruplar = gercek_albumler((govde or {}).get("release-groups", []))

        kopru_sayisi = len(kayit["kopruler"])
        for grup in gruplar[:album_adedi]:
            baslik = (grup.get("title") or "").strip()
            anahtar_aday = f"{normalize_esleme(kayit['ad'])}|{normalize_esleme(baslik)}"
            # Aynı başlık iki release-group olarak gelebiliyor (AC/DC "High
            # Voltage" — Avustralya ve uluslararası sürüm). Kullanıcıya aynı
            # albümü iki kez göstermenin anlamı yok.
            if not baslik or anahtar_aday in sahip or anahtar_aday in gorulen:
                continue
            gorulen.add(anahtar_aday)
            yil = (grup.get("first-release-date") or "")[:4]
            koprular = sorted(kayit["kopruler"])[:2]
            gosterilecek = kayit.get("gorunen_ad") or kayit["ad"]
            ozgul = (
                f"Yalnız bu eksende çıkıyor — sana özgü."
                if kayit["df"] == 1
                else f"{kayit['df']}/{eksen_sayisi} eksende çıkıyor."
            )
            gerekce = (
                f"«{kume_adi}» ekseninden İKİ ADIM ötede. Seninkileri dinleyenler "
                f"{' ve '.join(koprular)} dinliyor; onları dinleyenler de "
                f"{gosterilecek} dinliyor. {gosterilecek} senin hiçbir eksenine "
                f"DOĞRUDAN komşu değil ({kopru_sayisi} köprü). {ozgul}"
            )
            adaylar.append(
                Aday(
                    artist=gosterilecek,
                    title=baslik,
                    year=int(yil) if yil.isdigit() else None,
                    strateji="bilincli_uzaklik",
                    eksen=eksen,
                    skor=round(kayit["destek"] * kayit["idf"], 4),
                    gerekce=gerekce,
                    dayanak={
                        "kopruler": sorted(kayit["kopruler"]),
                        "kopru_sayisi": kopru_sayisi,
                        "adim": 2,
                        "eksen_frekansi": kayit["df"],
                        "eksen_sayisi": eksen_sayisi,
                        "idf": round(kayit["idf"], 4),
                        "komsuluk_skoru": round(kayit["skor"], 4),
                        "ozgun_ad": kayit["ad"],
                    },
                    mbid=grup.get("id"),
                )
            )
    # Sıralama ölçütü BURADA da özgüllük olmalı. Bir kez `-skor` ile sıralandı
    # ve `sirali` içindeki df-öncelikli düzeni sessizce geri aldı: metal
    # ekseninde AC/DC (df=2) Children of Bodom'un (df=1) üstüne çıkmıştı.
    return sorted(adaylar, key=lambda a: (a.dayanak["eksen_frekansi"], -a.skor))


# --------------------------------------------------------------------------- #
# Strateji 4: liste birlikteliği — PARÇA düzeyinde
# --------------------------------------------------------------------------- #

def liste_birlikteligi(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, *,
    sanatci_adedi: int = 8, adet: int = 12,
) -> list[Aday]:
    """Çalma listesi birlikteliğinden PARÇA adayları (`python/discover/calma_listesi.py`).

    Diğer üç strateji albüm öneriyor; bu parça öneriyor ve önizlemesi hazır
    geliyor — hasat sırasında Deezer'ın 30 sn klibi kaydedilmişti. Kullanıcının
    isteği buydu: "bolca şarkı bul".

    Neden bu strateji diğerlerinden iyi çalışıyor: aday havuzu 116 sanatçıdan
    10.360'a çıktı (482 liste, 45.899 parça). Diğer stratejiler eksen başına
    6 tohum × 15 komşu ile sınırlıydı.

    Sıralama normalize PMI (bkz. `calma_listesi.birliktelik`). Ham birliktelik
    ünlüyü öne çıkarırdı; ölçüldü — 22 listelik ilk örneklemde Van Halen ↔
    Madonna/Haddaway çıkıyordu (80'ler parti listeleri). 482 listede npmi
    popülerliği de nadirliği de söndürüp müzikal komşuyu getiriyor:
    The Ocean ↔ Pineapple Thief/Devin Townsend, Vega ↔ TNK (Türkçe rock),
    Adam Nitti ↔ Nathan East (iki füzyon basçısı).
    """
    from python.discover.calma_listesi import aday_parcalar

    sanatcilar = eksen_sanatcilari(conn, calisma_id, eksen, adet=sanatci_adedi)
    if sanatcilar.empty:
        return []
    kume_adi = _eksen_adi(conn, calisma_id, eksen)
    parcalar = aday_parcalar(conn, list(sanatcilar.index), adet=adet)

    adaylar: list[Aday] = []
    for p in parcalar:
        kaynak = ", ".join(k for k in p["kaynaklar"] if k)[:80]
        gerekce = (
            f"«{kume_adi}» ekseninden {kaynak} ile AYNI çalma listelerinde "
            f"geçiyor ({p['birlikte']} listede birlikte). Bu bir tür etiketi "
            f"değil, insanların ikisini yan yana koyması. Popülerlik "
            f"sönümlenmiş (bağ gücü {p['pmi']:+.2f}, −1 ile +1 arası) — ünlü "
            f"olduğu için değil, tam da bu sanatçılarla birlikte göründüğü için."
        )
        adaylar.append(
            Aday(
                artist=p["sanatci"], title=p["parca"], year=None,
                strateji="liste_birlikteligi", eksen=eksen,
                skor=round(p["pmi"], 4), gerekce=gerekce,
                dayanak={
                    "pmi": round(p["pmi"], 4),
                    "birlikte_liste": p["birlikte"],
                    "kaynak_sanatcilar": p["kaynaklar"],
                    "birim": "parca",
                    "onizleme": p["onizleme"],
                    "parca_id": p.get("parca_id"),
                },
            )
        )
    return adaylar


# --------------------------------------------------------------------------- #
# Strateji 5: ses benzerliği (CLAP)
# --------------------------------------------------------------------------- #

def ses_benzerligi(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, *, adet: int = 12
) -> list[Aday]:
    """CLAP gömü uzayında eksenin albümlerine en yakın, sende OLMAYAN kayıtlar.

    Projenin baştan beri eksik olan parçası: İÇERİK TEMELLİ öneri. Kredi
    grafiği "kim çalmış", kalabalık "kim dinliyor" diyordu; bu "kulağa nasıl
    geliyor" diyor — ve elle tasarlanmış sekiz eksenle değil, 630 bin ses-metin
    çiftiyle eğitilmiş bir gömüyle.

    **Sıfır-atışlı ETİKETLEME denendi ve yetmedi** (`etiket_clap.py`): istem
    yanlılığı yüzünden "türk rock" Eminem'e de A-Ha'ya da yapışıyordu. Aynı
    gömüler ALAN İÇİ benzerlikte çok iyi çalışıyor, çünkü orada ne istem
    yanlılığı var ne alan kayması.

    **AÇIK HAVUZ (2026-09-01).** Önceki sürüm `benzer_adaylar`'ı çağırıyordu ve
    o yalnızca `stem_profili`'ndeki 125 aday albümü yeniden sıralıyordu —
    kapalı havuz. `python/degerlendirme.py` bunu görünür kıldı: gizlenen
    sanatçı o tabloda olmadığı için sınamada yapısal olarak bulunamıyordu.
    Şimdi çalma listesi parçalarının tamamında aranıyor (3.000+ gömü, arka
    planda büyüyor) — ses kümeleri sayfasında Jiro Inagaki'yi bulan havuz.

    Gerekçe kendiliğinden geliyor ve doğrulanabilir: hangi albümüne benzediği
    yazılıyor, kullanıcı ikisini arka arkaya dinleyip yargılayabiliyor.
    """
    from python.etiket_clap import acik_havuz_adaylari

    kume_adi = _eksen_adi(conn, calisma_id, eksen)
    kayitlar = acik_havuz_adaylari(conn, calisma_id, eksen, adet=adet)

    adaylar: list[Aday] = []
    for kayit in kayitlar:
        parca_mi = kayit["tur"] == "parca"
        gerekce = (
            f"Kulağa senin «{kayit['benzedigi']}» albümüne benziyor — bu "
            f"tür etiketi ya da kadro bağı değil, SESİN kendisi. Ölçüm "
            f"CLAP gömü uzayında; skor, adayın kütüphanenin geneline "
            f"benzerliği çıkarılarak hesaplandı, yani «her şeye benzeyen» "
            f"kayıtlar öne çıkmıyor. «{kume_adi}» ekseni için."
        )
        adaylar.append(
            Aday(
                artist=kayit["sanatci"], title=kayit["ad"] or "—", year=None,
                strateji="ses_benzerligi", eksen=eksen,
                skor=round(kayit["skor"], 4), gerekce=gerekce,
                dayanak={
                    "benzedigi": kayit["benzedigi"],
                    "clap_skor": round(kayit["skor"], 4),
                    "yontem": "CLAP gömü, hubness düzeltmeli, açık havuz",
                    "birim": "parca" if parca_mi else "album",
                    # URL değil KİMLİK saklanıyor: Deezer imzalı URL'leri
                    # kısa ömürlü, saklanmış hâli 403 dönüyor.
                    "parca_id": kayit["parca_id"],
                },
            )
        )
    return adaylar


# --------------------------------------------------------------------------- #
# Strateji 6: melez (liste birlikteliği + ses benzerliği)
# --------------------------------------------------------------------------- #

#: Kaynaşmada çalma listesi sinyalinin ses sinyaline ağırlık oranı. Süpürme
#: ile seçildi (`python/degerlendirme.py`, 147 sanatçı, 2026-09-02):
#:
#:     ağırlık  tavan  @5    @10   @50   MRR    medyan
#:     1:1       123   0.02  0.05  0.12  0.022     356
#:     2:1       123   0.03  0.04  0.16  0.025     288   ← seçilen
#:     3:1       123   0.02  0.04  0.16  0.022     262
#:     5:1       123   0.01  0.05  0.14  0.025     238
#:     npmi tek  109   0.01  0.03  0.14  0.024     159
MELEZ_AGIRLIK = (2.0, 1.0)


def melez(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, *, adet: int = 12
) -> list[Aday]:
    """İki sinyalin sıra kaynaşması: liste komşuluğu + kulağa benzerlik.

    Ölçüm bunu işaret etti (`python/degerlendirme.py`, leave-one-artist-out,
    147 sanatçı). İki sinyal FARKLI sorular cevaplıyor:

    - Çalma listesi birlikteliği örtük ortak filtreleme: listeyi yapan insan
      "bunları seven aynı kişi" bilgisini taşıyor. Rastgeleye göre 5,4 kat.
    - CLAP yalnız tınıyı kodluyor: "sende olana BENZEYEN". Rastgeleye göre
      1,4 kat — ama tamamen farklı bir havuzu görüyor.

    Bu yüzden birleşimin asıl kazancı sıralama değil ERİŞİM: tek başına çalma
    listesi 147 sanatçının 109'una ulaşabiliyordu, melez 123'üne. Yani 14
    sanatçı yalnız ses tarafından erişilebilir durumda. recall@50 de 0,14'ten
    0,16'ya çıkıyor.

    Kaynaşma skor toplamı DEĞİL sıra toplamı; gerekçesi `melez_sirala`'da.
    """
    liste = liste_birlikteligi(conn, calisma_id, eksen, adet=adet * 4)
    ses = ses_benzerligi(conn, calisma_id, eksen, adet=adet * 4)
    if not liste and not ses:
        return []

    # Kaynaşma SANATÇI düzeyinde: iki strateji farklı parçalar öneriyor, aynı
    # sanatçının iki ayrı parçası tek bir aday gibi yarışmalı.
    def sanatci_sirasi(adaylar: list[Aday]) -> list[str]:
        gorulen, sira = set(), []
        for a in adaylar:
            anahtar = normalize_esleme(a.artist)
            if anahtar not in gorulen:
                gorulen.add(anahtar)
                sira.append(anahtar)
        return sira

    kazanan = melez_sirala(
        [sanatci_sirasi(liste), sanatci_sirasi(ses)],
        agirliklar=list(MELEZ_AGIRLIK),
    )[:adet]

    # Her sanatçı için en iyi kaynağı seç; iki listede de varsa ikisinin de
    # gerekçesi yazılır — kullanıcının gördüğü şey tam olarak kararın sebebi.
    en_iyi_liste = {normalize_esleme(a.artist): a for a in reversed(liste)}
    en_iyi_ses = {normalize_esleme(a.artist): a for a in reversed(ses)}

    kume_adi = _eksen_adi(conn, calisma_id, eksen)
    adaylar: list[Aday] = []
    for basamak, anahtar in enumerate(kazanan, 1):
        l, s = en_iyi_liste.get(anahtar), en_iyi_ses.get(anahtar)
        kaynak = l or s
        if kaynak is None:
            continue
        if l and s:
            gerekce = (
                f"İKİ SİNYAL DE işaret ediyor. Çalma listelerinde «{kume_adi}» "
                f"sanatçılarının yanında duruyor (bağ gücü "
                f"{l.dayanak.get('pmi', 0):+.2f}) VE kulağa senin "
                f"«{s.dayanak.get('benzedigi', '?')}» albümüne benziyor. "
                f"Tek başına hiçbir sinyal bu kadarını söylemiyordu; ölçümde "
                f"birleşim, ikisinden de fazla sanatçıya ulaşıyor."
            )
        elif l:
            gerekce = l.gerekce
        else:
            gerekce = s.gerekce

        dayanak = dict(kaynak.dayanak)
        dayanak["melez_basamak"] = basamak
        dayanak["kaynaklar"] = [
            ad for ad, var in (("liste_birlikteligi", l), ("ses_benzerligi", s)) if var
        ]
        adaylar.append(
            Aday(
                artist=kaynak.artist, title=kaynak.title, year=kaynak.year,
                strateji="melez", eksen=eksen,
                # Skor sıralamayı korumalı: kaynaşma skoru ölçek taşımıyor,
                # basamağın tersi hem sıralamayı hem okunabilirliği veriyor.
                skor=round(1.0 / basamak, 4),
                gerekce=gerekce, dayanak=dayanak,
            )
        )
    return adaylar


# --------------------------------------------------------------------------- #
# Yürütme
# --------------------------------------------------------------------------- #

#: Stüdyo albümü SAYILMAYAN ikincil türler. MusicBrainz'de canlı kayıt da
#: `primary-type=Album` döner; ayırt eden `secondary-types`. Süzülmezse öneri
#: listesine bootleg konser kayıtları doluyor — ölçüldü: The Killers için ilk
#: üç adayın ikisi "2004-11-12: Manchester" gibi tarih başlıklı bootleg'di.
YOK_SAYILAN_TURLER = {"Live", "Compilation", "Demo", "Remix", "DJ-mix",
                      "Mixtape/Street", "Interview", "Audiobook", "Soundtrack"}


def gercek_albumler(gruplar: list[dict]) -> list[dict]:
    """Yalnız stüdyo albümleri, eskiden yeniye.

    İki strateji de (sahne komşuluğu, bilinçli uzaklık) aynı MusicBrainz
    sorgusunu kullanıyor ve ikisi de aynı hatayı yapıyordu.
    """
    temiz = [
        g for g in gruplar
        if g.get("primary-type") == "Album"
        and not (set(g.get("secondary-types") or []) & YOK_SAYILAN_TURLER)
    ]
    temiz.sort(key=lambda g: g.get("first-release-date") or "9999")
    return temiz


def _latin_mi(metin: str) -> bool:
    harfler = [k for k in metin if k.isalpha()]
    return bool(harfler) and all(ord(k) < 0x0250 for k in harfler)


def _okunabilir_ad(mb: ApiIstemci, mbid: str, ozgun: str) -> str:
    """Latin yazımlı ad; yoksa özgün ad."""
    if _latin_mi(ozgun):
        return ozgun
    try:
        govde = mb.get_json(f"artist/{mbid}", {"inc": "aliases", "fmt": "json"})
    except AgYok:
        return ozgun
    adaylar = [(govde or {}).get("sort-name", "")]
    adaylar += [t.get("name", "") for t in ((govde or {}).get("aliases") or [])]
    for varyant in adaylar:
        if varyant and _latin_mi(varyant):
            # "Takanaka, Masayoshi" → "Masayoshi Takanaka"
            if ", " in varyant:
                soyad, _, ad = varyant.partition(", ")
                varyant = f"{ad} {soyad}".strip()
            return f"{varyant} ({ozgun})"
    return ozgun


def _eksen_adi(conn: sqlite3.Connection, calisma_id: str, eksen: int) -> str:
    satir = conn.execute(
        "SELECT kullanici_adi FROM clusters WHERE calisma_id=? AND kume_id=?",
        (calisma_id, eksen),
    ).fetchone()
    ad = satir["kullanici_adi"] if satir else None
    return ad or f"küme {eksen}"


def adaylari_yaz(conn: sqlite3.Connection, calisma_id: str, adaylar: list[Aday]) -> int:
    """Adayları yaz; ÜRETİMİN SAHİBİ OLMADIĞI sütunlara dokunma.

    Eskiden `INSERT OR REPLACE` kullanılıyordu ve satırın TAMAMINI değiştiriyordu.
    `onizleme_url` sütun listesinde olmadığı için her yeniden üretim, sonradan
    iTunes/Deezer'dan bulunmuş 30 sn kliplerini NULL'a çeviriyordu — ölçüldü,
    bir yeniden üretimden sonra 253 satırın 253'ünde önizleme silinmişti.

    Doğrusu `ON CONFLICT ... DO UPDATE SET`: yalnız üretimin ürettiği alanlar
    güncellenir, sonraki aşamaların doldurduğu alanlar yerinde kalır. Aynı
    ayrım `profil_yaz`da da var.
    """
    bugun = date.today().isoformat()
    with conn:
        conn.executemany(
            """INSERT INTO adaylar
               (aday_id, calisma_id, eksen, strateji, artist, title, year, mbid,
                discogs_id, skor, gerekce, dayanak, uretim_tarihi, birim,
                onizleme_url, parca_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,COALESCE(?, NULL),?)
               ON CONFLICT(calisma_id, eksen, strateji, aday_id) DO UPDATE SET
                 artist=excluded.artist, title=excluded.title, year=excluded.year,
                 mbid=excluded.mbid, discogs_id=excluded.discogs_id,
                 skor=excluded.skor, gerekce=excluded.gerekce,
                 dayanak=excluded.dayanak, uretim_tarihi=excluded.uretim_tarihi,
                 birim=excluded.birim,
                 parca_id=COALESCE(excluded.parca_id, adaylar.parca_id),
                 -- Parça adayının önizlemesi hasattan HAZIR geliyor; albüm
                 -- adaylarında bu alanı sonraki aşama dolduruyor ve ezilmemeli.
                 onizleme_url=COALESCE(excluded.onizleme_url, adaylar.onizleme_url)""",
            [
                (a.aday_id, calisma_id, a.eksen, a.strateji, a.artist, a.title,
                 a.year, a.mbid, a.discogs_id, a.skor, a.gerekce,
                 json.dumps(a.dayanak, ensure_ascii=False), bugun,
                 a.dayanak.get("birim", "album"), a.dayanak.get("onizleme"),
                 a.dayanak.get("parca_id"))
                for a in adaylar
            ],
        )
    return len(adaylar)


def bayat_adaylari_temizle(
    conn: sqlite3.Connection, calisma_id: str, adaylar: list[Aday], *, tarih: str
) -> int:
    """Bu turda ÜRETİLMEYEN eski adayları sil.

    Gerekçe: strateji düzeltilince eski çıktı ortada kalıyor. Canlı kayıt
    süzgeci eklendikten sonra "Rage Against the Machine — Live & Rare" listede
    durmaya devam etti; kullanıcı düzeltilmiş bir sistemin düzeltilmemiş
    çıktısını görüyordu.

    Kullanıcının KARAR VERDİĞİ adaylar silinmez — beğendiği/tutmadığı bir albümün
    kaydını kaybetmek geri bildirim geçmişini boşa çıkarırdı.
    """
    if not adaylar:
        return 0
    kombinasyonlar = {(a.eksen, a.strateji) for a in adaylar}
    yeni = {(a.eksen, a.strateji, a.aday_id) for a in adaylar}
    silinecek = []
    for eksen, strateji in kombinasyonlar:
        mevcut = conn.execute(
            """SELECT aday_id FROM adaylar
                WHERE calisma_id = ? AND eksen = ? AND strateji = ?
                  AND aday_id NOT IN (SELECT aday_id FROM feedback
                                       WHERE calisma_id = ?)""",
            (calisma_id, eksen, strateji, calisma_id),
        ).fetchall()
        for (aday_id,) in mevcut:
            if (eksen, strateji, aday_id) not in yeni:
                silinecek.append((calisma_id, eksen, strateji, aday_id))
    if silinecek:
        with conn:
            conn.executemany(
                "DELETE FROM adaylar WHERE calisma_id=? AND eksen=? "
                "AND strateji=? AND aday_id=?",
                silinecek,
            )
    return len(silinecek)


def eksen_uret(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, *, adet: int = 10,
    frekans: dict[str, int] | None = None,
    stratejiler: tuple[str, ...] | None = None,
) -> list[Aday]:
    """Bir eksen için üç stratejinin adayları.

    `stratejiler` verilirse yalnız o stratejiler çalışır. Bayat aday temizliği
    zaten (eksen, strateji) çiftine göre kapsamlı, yani tek strateji yeniden
    üretmek diğerlerinin çıktısını silmez.

    `frekans` dışarıdan verilmeli: `bilincli_uzaklik`'ın popülerlik sönümlemesi
    TÜM eksenlerin havuzunu gerektiriyor ve her eksende yeniden hesaplanırsa
    tarama eksen sayısı kadar tekrarlanır. Önbellek bunu ucuzlatıyor ama bedava
    yapmıyor; çağıran bir kez hesaplayıp geçsin.
    """
    istenen = set(stratejiler) if stratejiler else None
    ister = lambda ad: istenen is None or ad in istenen  # noqa: E731

    adaylar: list[Aday] = []
    # Ağ isteyen stratejiler yalnız istendiklerinde kurulur; tek strateji
    # yeniden üretilirken MusicBrainz/Discogs'a hiç dokunulmaması için.
    if ister("kredi_sicramasi"):
        dc = discogs()
        if dc is not None:
            adaylar += kredi_sicramasi(conn, dc, calisma_id, eksen)[:adet]
        else:
            print("NOT: DISCOGS_TOKEN yok, kredi sıçraması atlanıyor.",
                  file=sys.stderr)
    if ister("sahne_komsulugu"):
        mb, lb = musicbrainz(), listenbrainz()
        adaylar += sahne_komsulugu(conn, mb, lb, calisma_id, eksen)[:adet]
    if ister("bilincli_uzaklik"):
        mb, lb = musicbrainz(), listenbrainz()
        if frekans is None:
            frekans = eksen_frekansi(conn, mb, lb, calisma_id)
        adaylar += bilincli_uzaklik(
            conn, mb, lb, calisma_id, eksen, frekans=frekans)[:adet]
    if ister("liste_birlikteligi"):
        adaylar += liste_birlikteligi(conn, calisma_id, eksen, adet=adet)
    if ister("ses_benzerligi"):
        adaylar += ses_benzerligi(conn, calisma_id, eksen, adet=adet)
    if ister("melez"):
        adaylar += melez(conn, calisma_id, eksen, adet=adet)
    return adaylar


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Faz 2 aday üretimi.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--calisma", help="calisma_id (varsayılan: en yenisi)")
    ayristirici.add_argument("--eksen", type=int, help="tek bir eksen")
    ayristirici.add_argument("--tum-eksenler", action="store_true")
    ayristirici.add_argument("--adet", type=int, default=10, help="strateji başına aday")
    ayristirici.add_argument("--strateji", action="append",
                             help="yalnız bu strateji (birden çok kez verilebilir)")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        calisma_id = args.calisma or conn.execute(
            "SELECT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 1"
        ).fetchone()[0]

        if args.tum_eksenler:
            eksenler = [
                s["kume_id"] for s in conn.execute(
                    "SELECT kume_id FROM clusters WHERE calisma_id=? AND stabil_mi=1 "
                    "ORDER BY kume_id", (calisma_id,)
                )
            ]
        elif args.eksen is not None:
            eksenler = [args.eksen]
        else:
            ayristirici.error("--eksen ya da --tum-eksenler verilmeli")

        toplam = 0
        secilen = tuple(args.strateji) if args.strateji else None
        # Popülerlik sönümlemesinin paydası bir kez hesaplanır (bkz. eksen_uret)
        # ve AĞ ister — yalnız ona ihtiyaç duyan strateji çalışacaksa kurulur.
        ortak_frekans = None
        if secilen is None or "bilincli_uzaklik" in secilen:
            ortak_frekans = eksen_frekansi(
                conn, musicbrainz(), listenbrainz(), calisma_id
            )
        for eksen in eksenler:
            adaylar = eksen_uret(
                conn, calisma_id, eksen, adet=args.adet, frekans=ortak_frekans,
                stratejiler=secilen,
            )
            toplam += adaylari_yaz(conn, calisma_id, adaylar)
            silinen = bayat_adaylari_temizle(
                conn, calisma_id, adaylar, tarih=date.today().isoformat()
            )
            if silinen:
                print(f"  ({silinen} bayat aday silindi)", file=sys.stderr)
            ad = _eksen_adi(conn, calisma_id, eksen)
            print(f"\n=== «{ad}» (eksen {eksen}) — {len(adaylar)} aday ===")
            for aday in adaylar[:8]:
                yil = f" ({aday.year})" if aday.year else ""
                print(f"  [{aday.strateji:<16}] {aday.artist} — {aday.title}{yil}")
                print(f"      {aday.gerekce}")
    finally:
        conn.close()

    print(f"\nToplam {toplam} aday yazıldı (calisma_id={calisma_id}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
