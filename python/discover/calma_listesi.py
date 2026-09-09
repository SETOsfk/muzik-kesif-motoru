"""Çalma listesi hasadı — kullanıcı kaydı olmadan ortak filtreleme.

## Neden çalma listeleri

Sektörün ana silahı ortak filtreleme ve yakıtı çok kullanıcının dinleme kaydı.
Bizde tek kullanıcı var, o kaydın da geçmişi boş. Klasik vekil: **çalma
listeleri**. Bir listede iki sanatçının yan yana durması, birinin dinleyicisinin
diğerini de dinlediğine dair insan eliyle verilmiş bir işaret.

Kaynak Deezer'ın anahtarsız genel API'si (K2: 0 TL). Test edildi:
`search/playlist` liste buluyor, `playlist/{id}` 50 parçasını veriyor,
`artist/{id}/related` komşu veriyor. Hepsi anahtarsız ve belgelenmiş uçlar —
Reddit/RateYourMusic'te reddedilen "onaysız uç nokta" kategorisine GİRMİYOR.

## İki tuzak ve çözümleri

**1. Tek sanatçılık listeler.** Arama "meshuggah" için ilk sonuç «100%
Meshuggah» — editoryal bir derleme, içindeki 50 parçanın hepsi aynı gruptan.
Birliktelik sinyali sıfır. `_karisik_mi()` bunları eliyor: bir sanatçı listenin
yarısından fazlasını kaplıyorsa liste atılır.

**2. Popülerlik.** Ham birliktelik sayısı ünlü sanatçıyı öne çıkarır — herkesin
listesinde Metallica vardır. Bu projede popülerlik yanlılığı üç kez aynı yolla
çözüldü (kesişim sayısı, lift, eksen-özgüllüğü) ve burada da aynı aile:
**PMI** (noktasal karşılıklı bilgi). "Bu ikisi birlikte, tek başlarına
görülme sıklıklarının gerektirdiğinden NE KADAR fazla görünüyor" sorusu.

    PMI(a,b) = log( P(a,b) / (P(a) · P(b)) )

Metallica her listede olduğu için P(b) büyük ve payda onu söndürüyor; niş bir
grupla kurulan birliktelik ise yüksek PMI veriyor.

## Ne saklanıyor

Listelerin PARÇALARI saklanıyor, yalnız sanatçı adları değil. Kullanıcının
isteği buydu ("bolca şarkı bul") ve öneriyi albüm düzeyinden parça düzeyine
indirmenin tek yolu bu. Ayrıca liste BAŞLIKLARI da saklanıyor: «GYMeshuggah»,
«CHUG» gibi başlıklar kalabalığın kendi kelime dağarcığı ve bir sonraki
adımda (çok boyutlu etiketleme) etiket kaynağı olacaklar.

Kullanım:
    python -m python.discover.calma_listesi --hasat --limit 20
    python -m python.discover.calma_listesi --hasat --tum
    python -m python.discover.calma_listesi --birliktelik
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from math import log
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.metin import normalize_esleme
from python.onbellek import AgYok, ApiIstemci

#: Bir sanatçı için kaç liste taranacak. Arama sonuçları alâkaya göre sıralı;
#: ilk beşten sonrası hızla gürültüye dönüyor.
LISTE_ADEDI = 6

#: Bir listede tek sanatçının kaplayabileceği en yüksek pay. Üstündekiler
#: derleme sayılıp atılır — birliktelik sinyali taşımıyorlar.
TEK_SANATCI_ESIGI = 0.5

#: Birliktelik için bir listenin en az bu kadar parçası olmalı.
#: Kanıt gücü büzülmesi: skor *= n/(n+k). Süpürülerek seçildi
#: (`python/degerlendirme.py`, bkz. `birliktelik` gövdesindeki tablo).
KANIT_BUZULMESI = 1.0

ASGARI_PARCA = 8


def deezer_listesi(**kwargs) -> ApiIstemci:
    return ApiIstemci(
        servis="deezer_liste",
        temel_url="https://api.deezer.com",
        istek_araligi=0.35,
        basliklar={"User-Agent": "muzik-kesif-motoru/0.1 (kisisel)"},
        **kwargs,
    )


def liste_ara(istemci: ApiIstemci, sanatci: str, adet: int = LISTE_ADEDI) -> list[dict]:
    try:
        govde = istemci.get_json(
            "search/playlist", {"q": sanatci, "limit": adet * 2}
        )
    except (AgYok, Exception):
        return []
    listeler = [
        p for p in (govde or {}).get("data", [])
        if p.get("nb_tracks", 0) >= ASGARI_PARCA
    ]
    return listeler[:adet]


def liste_parcalari(istemci: ApiIstemci, liste_id: int) -> list[dict]:
    try:
        govde = istemci.get_json(f"playlist/{liste_id}", {})
    except (AgYok, Exception):
        return []
    return ((govde or {}).get("tracks") or {}).get("data", [])


def _karisik_mi(parcalar: list[dict]) -> bool:
    """Tek sanatçının hakim olduğu derleme mi?

    Ölçüldü: "meshuggah" aramasının ilk sonucu «100% Meshuggah», 50 parçanın
    50'si aynı gruptan. Böyle bir liste birliktelik hakkında hiçbir şey
    söylemiyor ama en alâkalı sonuç olduğu için her aramada başa geliyor.
    """
    if len(parcalar) < ASGARI_PARCA:
        return False
    sayac = Counter(
        normalize_esleme((p.get("artist") or {}).get("name", "")) for p in parcalar
    )
    en_cok = sayac.most_common(1)[0][1] if sayac else 0
    return en_cok / len(parcalar) <= TEK_SANATCI_ESIGI


def hasat(
    conn: sqlite3.Connection, istemci: ApiIstemci, *, limit: int | None = None
) -> dict[str, int]:
    """Kütüphanedeki sanatçılar için liste ara, parçalarını sakla."""
    sanatcilar = [
        r[0] for r in conn.execute(
            "SELECT DISTINCT artist FROM albums WHERE artist IS NOT NULL "
            "ORDER BY artist"
        )
    ]
    if limit:
        sanatcilar = sanatcilar[:limit]

    gorulen = {
        r[0] for r in conn.execute("SELECT liste_id FROM calma_listesi")
    }
    sayac = {"sanatci": 0, "liste": 0, "atlanan": 0, "parca": 0}

    for sira, sanatci in enumerate(sanatcilar, 1):
        sayac["sanatci"] += 1
        for liste in liste_ara(istemci, sanatci):
            liste_id = liste.get("id")
            if not liste_id or liste_id in gorulen:
                continue
            gorulen.add(liste_id)
            parcalar = liste_parcalari(istemci, liste_id)
            if not _karisik_mi(parcalar):
                sayac["atlanan"] += 1
                continue

            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO calma_listesi "
                    "(liste_id, baslik, parca_sayisi, takipci, kaynak, tohum_sanatci) "
                    "VALUES (?,?,?,?,'deezer',?)",
                    (liste_id, liste.get("title"), len(parcalar),
                     liste.get("fans", 0), sanatci),
                )
                conn.executemany(
                    "INSERT OR IGNORE INTO liste_parca "
                    "(liste_id, sira, sanatci, sanatci_anahtar, parca, onizleme) "
                    "VALUES (?,?,?,?,?,?)",
                    [
                        (liste_id, i,
                         (p.get("artist") or {}).get("name", ""),
                         normalize_esleme((p.get("artist") or {}).get("name", "")),
                         p.get("title", ""), p.get("preview"))
                        for i, p in enumerate(parcalar)
                        if (p.get("artist") or {}).get("name")
                    ],
                )
            sayac["liste"] += 1
            sayac["parca"] += len(parcalar)

        if sira % 10 == 0:
            print(f"  {sira}/{len(sanatcilar)} sanatçı · {sayac['liste']} liste · "
                  f"{sayac['parca']} parça", file=sys.stderr)
    return sayac


def birliktelik(
    conn: sqlite3.Connection, *, asgari_liste: int = 2, olcut: str = "npmi",
    buzulme: float = KANIT_BUZULMESI,
) -> list[tuple[str, str, int, float]]:
    """Kütüphane sanatçısı × dışarıdaki sanatçı için normalize edilmiş PMI.

    Dönen: (kütüphane_anahtarı, aday_anahtarı, birlikte_görülme, skor)

    `asgari_liste`: tek bir listede bir kez yan yana gelmek tesadüf olabilir.
    İki ayrı liste, iki ayrı insanın aynı bağı kurması demek.

    NEDEN NPMI (2026-09-01, ölçüldü)
    Ham PMI'nın bilinen nadir-öğe yanlılığı var: iki listede geçip ikisinde de
    tohumla yan yana olan bir sanatçı, yüz listede geçip elli kez yan yana
    gelenden yüksek skor alır. Sıralamanın başı bu yüzden ultra-nadir
    kayıtlarla doluyordu.

    `python.degerlendirme` ile leave-one-artist-out ölçümü (147 sanatçı):

        ölçüt   recall@10  recall@50    MRR   medyan sıra
        pmi          0.00       0.07  0.006          249
        npmi         0.03       0.14  0.024          159

    Bu, projede popülerlik/nadirlik yanlılığının altıncı kez ölçülüp
    düzeltilmesi. Öncekiler gibi burada da düzeltme bir sönümleme çarpanı
    değil, ölçütün kendisinin değişmesi.

    KANIT GÜCÜ (2026-09-02, ölçüldü). npmi'nin tavanı +1 ve İKİ liste onu
    doldurmaya yetiyor: «2 listede birlikte» ile «16 listede birlikte» aynı
    skoru alabiliyordu. `n/(n+k)` çarpanı az kanıtı sıfıra doğru büzüyor, çok
    kanıtta 1'e yaklaşıp etkisiz kalıyor. Süpürüldü (147 sanatçı, npmi):

        k   @10   @50    MRR   görünürlük
        0  0.03  0.14  0.024        2
        1  0.13  0.27  0.063        7   ← seçilen
        2  0.18  0.27  0.093       16
        4  0.18  0.27  0.099       20
        8  0.17  0.27  0.095       22

    Kazanç büyük: recall@50 iki katına, recall@10 dört katına çıkıyor. Ve
    dikkat çeken şey ne olduğu — YENİ BİR SİNYAL DEĞİL, var olan en güçlü
    sinyalin doğru okunması.

    NEDEN k=1, k=4 DEĞİL. Sağdaki sütun önerilerin medyan çalma listesi
    görünürlüğü, yani POPÜLERLİK vekili; kütüphanenin kendi medyanı 6.
    k büyüdükçe erişim ölçütü doyuyor (recall@50 zaten 0,27) ama popülerlik
    tırmanmaya devam ediyor. k=4, fazladan 0,05 recall@10 için popülerliği
    üçe katlıyor.

    Bu, projenin merkezindeki gerilim: gizleme sınaması "SAHİP OLDUĞUN
    sanatçıyı bulabildin mi" diye soruyor, sahip olduklarınsa popülere kayıyor
    — dolayısıyla ölçütü kovalamak kullanıcının asıl istediğinden ("hiç
    duymadığım sanatçı") uzaklaştırabiliyor. Tek sayıya bakılsaydı k=4
    seçilirdi ve yanlış olurdu.

    `olcut="pmi"` ham PMI'ya döner — kıyas ve tekrarlanabilirlik için duruyor.
    """
    sahip = {
        normalize_esleme(r[0]) for r in conn.execute(
            "SELECT DISTINCT artist FROM albums"
        ) if r[0]
    }
    listeler: dict[int, set[str]] = defaultdict(set)
    for liste_id, anahtar in conn.execute(
        "SELECT liste_id, sanatci_anahtar FROM liste_parca WHERE sanatci_anahtar != ''"
    ):
        listeler[liste_id].add(anahtar)

    toplam = len(listeler)
    if toplam < 5:
        return []

    gorulme = Counter()
    for uyeler in listeler.values():
        gorulme.update(uyeler)

    birlikte: Counter = Counter()
    for uyeler in listeler.values():
        icerdeki = uyeler & sahip
        disaridaki = uyeler - sahip
        for a in icerdeki:
            for b in disaridaki:
                birlikte[(a, b)] += 1

    sonuc = []
    for (a, b), adet in birlikte.items():
        if adet < asgari_liste:
            continue
        # PMI: birlikte görülme, tek tek görülme sıklıklarının gerektirdiğinden
        # ne kadar fazla. Popüler `b` için payda büyür ve skor söner.
        p_ab = adet / toplam
        p_a, p_b = gorulme[a] / toplam, gorulme[b] / toplam
        if p_a <= 0 or p_b <= 0:
            continue
        deger = log(p_ab / (p_a * p_b))
        if olcut == "npmi":
            # -log(p_ab)'ye bölüp [-1, 1]'e sıkıştır: nadirlik primi söner,
            # geriye bağın gücü kalır.
            payda = -log(p_ab)
            deger = deger / payda if payda > 0 else 0.0
        if buzulme > 0:
            deger *= adet / (adet + buzulme)
        sonuc.append((a, b, adet, deger))
    return sorted(sonuc, key=lambda x: -x[3])


def birliktelik_yaz(conn: sqlite3.Connection, satirlar) -> int:
    with conn:
        conn.execute("DELETE FROM liste_birlikteligi")
        conn.executemany(
            "INSERT INTO liste_birlikteligi "
            "(kutuphane_anahtar, aday_anahtar, birlikte, pmi) VALUES (?,?,?,?)",
            [(a, b, adet, round(pmi, 4)) for a, b, adet, pmi in satirlar],
        )
    return len(satirlar)


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--hasat", action="store_true")
    ayristirici.add_argument("--birliktelik", action="store_true")
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--tum", action="store_true")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        if args.hasat:
            sayac = hasat(conn, deezer_listesi(),
                          limit=None if args.tum else (args.limit or 15))
            print(f"\nsanatçı {sayac['sanatci']} · liste {sayac['liste']} · "
                  f"parça {sayac['parca']} · atlanan (tek sanatçılık) {sayac['atlanan']}")
        if args.birliktelik or not args.hasat:
            satirlar = birliktelik(conn)
            print(f"\n{birliktelik_yaz(conn, satirlar)} birliktelik yazıldı")
            for a, b, adet, pmi in satirlar[:20]:
                print(f"  {a[:26]:<28} ↔ {b[:26]:<28} {adet} liste  bağ {pmi:+.2f}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------- #
# Strateji 4: liste birlikteliği (PARÇA düzeyinde aday)
# --------------------------------------------------------------------------- #

def aday_parcalar(
    conn: sqlite3.Connection, eksen_sanatcilari: list[str], *,
    kisi_basi: int = 3, adet: int = 40,
) -> list[dict]:
    """Eksenin sanatçılarına PMI ile bağlı, kütüphanede OLMAYAN parçalar.

    Diğer üç strateji albüm öneriyor ve önizlemesini sonradan arıyor. Bu
    strateji parça öneriyor ve önizlemesi zaten elinde — çalma listesinden
    geldiği için Deezer'ın 30 sn klibi hasat sırasında kaydedilmişti.

    Sıralama ölçütü normalize PMI, ham birliktelik değil. Bu projede
    popülerlik yanlılığı aynı aileden bir ölçütle çözülüyor (kesişim, lift,
    eksen-özgüllüğü, PMI, şimdi npmi — sonuncusu `python.degerlendirme` ile
    ölçüldü: recall@50 0.07 → 0.14).
    """
    if not eksen_sanatcilari:
        return []

    anahtarlar = [normalize_esleme(a) for a in eksen_sanatcilari]
    yer = ",".join("?" * len(anahtarlar))
    komsular = conn.execute(
        f"""SELECT aday_anahtar, MAX(pmi) pmi, SUM(birlikte) birlikte,
                   GROUP_CONCAT(DISTINCT kutuphane_anahtar) kaynaklar
              FROM liste_birlikteligi
             WHERE kutuphane_anahtar IN ({yer})
             GROUP BY aday_anahtar ORDER BY pmi DESC LIMIT ?""",
        (*anahtarlar, adet * 3),
    ).fetchall()
    if not komsular:
        return []

    sahip_parca = {
        (normalize_esleme(r[0]), normalize_esleme(r[1] or ""))
        for r in conn.execute("SELECT artist, title FROM albums")
    }
    sahip_sanatci = {a for a, _ in sahip_parca}

    sonuc: list[dict] = []
    for komsu in komsular:
        anahtar = komsu["aday_anahtar"]
        if anahtar in sahip_sanatci:
            continue
        # `parca_id` şart, `onizleme` değil: saklanmış URL kısa ömürlü
        # (ölçüldü, saatler sonra 10 URL'nin 10'u 403). Kalıcı olan kimlik.
        parcalar = conn.execute(
            """SELECT sanatci, parca, onizleme, parca_id, COUNT(*) gecis
                 FROM liste_parca WHERE sanatci_anahtar = ? AND parca_id IS NOT NULL
                GROUP BY parca ORDER BY gecis DESC, sira LIMIT ?""",
            (anahtar, kisi_basi),
        ).fetchall()
        for p in parcalar:
            sonuc.append({
                "sanatci": p["sanatci"], "parca": p["parca"],
                "onizleme": p["onizleme"], "parca_id": p["parca_id"],
                "pmi": float(komsu["pmi"]),
                "birlikte": int(komsu["birlikte"]),
                "kaynaklar": (komsu["kaynaklar"] or "").split(",")[:3],
            })
        if len({s["sanatci"] for s in sonuc}) >= adet:
            break
    return sonuc
