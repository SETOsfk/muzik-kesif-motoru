"""Aynı kişinin farklı yazımlarını birleştir — MusicBrainz alias verisiyle.

## Sorun

Profil anahtarı `normalize_esleme(person_name)`. Bu, kaynaklar arası ikilemeyi
(aynı kişi hem `discogs:424418` hem MusicBrainz UUID'siyle geliyor) ve tipografik
farkları (`O'Brien` / `O'Brien`) zaten çözüyor — ölçüldü, bölünen kimlik 0/4541.

Çözemediği tek sınıf: adın KENDİSİ farklıysa.

    神保彰            ↔  Akira Jimbo        (Japonca ad / romanize ad)
    Bob Siebenberg   ↔  Bob C. Benberg     (sahne adı / doğum adı)

Bunlar isimden çözülemez; ortak token yok. Sonuç öneri listesinde görünüyordu:
bir aday için "en yakın davulcular" listesinde aynı kişi iki kez, iki farklı
puanla çıkıyordu (神保彰 +0.887, Akira Jimbo +0.769) — çünkü profilleri
bölünmüş, her biri albümlerinin yarısından hesaplanmış.

## Çözüm ve GÜVENLİK KISITI

MusicBrainz her sanatçı için alias listesi tutuyor. Ama alias listesini olduğu
gibi almak tehlikeli: geniş, bazen yanlış, bazen grup adlarını içeriyor.

**Kritik kısıt: yalnız İKİ TARAFI DA kendi kredilerimde var olan adlar
birleştirilir.** Kütüphanede olmayan bir alias için eşleme YAZILMAZ. Böylece
MusicBrainz'in bilmediğimiz bir kişiye dair iddiası veritabanına sızmıyor;
yalnızca "bu iki ad bende ayrı ayrı duruyordu, MusicBrainz aynı kişi diyor"
durumunda birleşme oluyor.

İkinci kısıt: yalnız `type=Person`. Grup aliasları kişi grafiğini bozar.

## Kanonik ad seçimi

Birleşen adlardan hangisi kalacak? Kütüphanede EN ÇOK KREDİSİ olan. Gerekçe:
mevcut profillerin ve kullanıcının alışkanlığının çoğu o adla kurulmuş; azınlık
yazımı ona katılırsa daha az şey değişir. Eşitlikte Latin yazımlı olan tercih
edilir — kullanıcı okuyabilsin.

Kullanım:
    python -m python.enrich.kisi_birlestir            # enstrüman rolleri, ≥2 albüm
    python -m python.enrich.kisi_birlestir --tum      # tüm MB kimlikli kişiler
"""

from __future__ import annotations

import argparse
import sqlite3
import unicodedata
import sys
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.enrich.rol_eslemesi import ENSTRUMAN_ROLLERI
from python.metin import normalize_esleme
from python.onbellek import AgYok, ApiIstemci, musicbrainz


def _latin_mi(metin: str) -> bool:
    """Ad Latin yazımlı mı? Kanonik seçiminde eşitlik bozucu.

    NOKTALAMA LATİN SAYILIR. Önceki sürüm yalnız `ord(k) < 0x250` bakıyordu ve
    MusicBrainz'in tipografik noktalamasına takılıyordu: «Brendan O'Brien»
    (U+2019), «Jean‐Marie Horvat» (U+2010), «Mark "Exit" Goodchild» Latin
    sayılmıyordu — ölçüldü, 57 addan 49'u yanlış sınıflanmıştı. Sonuç
    kozmetikti ama yanlıştı: kredi sayısı eşit olduğunda gösterilecek ad
    Japonca yazım olabiliyordu.
    """
    return all(
        ord(k) < 0x250 or unicodedata.category(k).startswith(("P", "S"))
        for k in metin if not k.isspace()
    )


def hedef_kisiler(
    conn: sqlite3.Connection, *, tum: bool = False, asgari_album: int = 1
) -> list[tuple[str, str]]:
    """Alias'ı sorulacak (person_id, person_name) çiftleri.

    Yalnız ENSTRÜMAN rollerinde geçenler — tüm MB kimliklerini taramak 1743
    istek, bu küme 1065 ve arayüzde görünenlerin tamamını kapsıyor.

    **`asgari_album` VARSAYILANI 1, ve bu önemli.** İlk sürümde 2 idi ve tam da
    düzeltmeye çalıştığı vakayı eliyordu: bölünme tanımı gereği kişinin
    albümlerini İKİYE AYIRIYOR, her yarı eşiğin altında kalabiliyor. Ölçüldü —
    神保彰 MusicBrainz kimliğiyle tek albümde geçtiği için hedef kümeye
    girmemişti, oysa alias verisi doğru cevabı (`akira jimbo`) taşıyordu.
    Eşik, çözmeye çalıştığı sorunun kendisini gizliyordu.
    """
    if tum:
        sorgu = """
            SELECT person_id, MIN(person_name)
              FROM credits
             WHERE person_id NOT LIKE 'discogs:%' AND person_id IS NOT NULL
             GROUP BY person_id
        """
        parametre: tuple = ()
    else:
        yer = ",".join("?" * len(ENSTRUMAN_ROLLERI))
        sorgu = f"""
            SELECT person_id, MIN(person_name)
              FROM credits
             WHERE person_id NOT LIKE 'discogs:%' AND person_id IS NOT NULL
               AND role IN ({yer})
             GROUP BY person_id
            HAVING COUNT(DISTINCT album_id) >= ?
        """
        parametre = (*sorted(ENSTRUMAN_ROLLERI), asgari_album)
    return [(r[0], r[1]) for r in conn.execute(sorgu, parametre)]


def kutuphane_anahtarlari(conn: sqlite3.Connection) -> dict[str, int]:
    """Kredilerdeki her profil anahtarı → kaç albümde geçtiği.

    Hem güvenlik kısıtının ("bu ad bende var mı?") hem kanonik seçiminin
    ("hangisi daha çok geçiyor?") dayanağı.
    """
    sayac: dict[str, int] = {}
    for ad, adet in conn.execute(
        "SELECT person_name, COUNT(DISTINCT album_id) FROM credits GROUP BY person_name"
    ):
        anahtar = normalize_esleme(ad or "")
        if anahtar:
            sayac[anahtar] = sayac.get(anahtar, 0) + int(adet)
    return sayac


def aliaslari_getir(mb: ApiIstemci, mbid: str) -> tuple[list[str], str | None]:
    """Sanatçının bilinen tüm adları + türü (Person / Group / None)."""
    try:
        govde = mb.get_json(f"artist/{mbid}", {"inc": "aliases", "fmt": "json"})
    except AgYok:
        return [], None
    if not govde:
        return [], None
    adlar = [govde.get("name"), govde.get("sort-name")]
    adlar += [a.get("name") for a in (govde.get("aliases") or [])]
    adlar += [a.get("sort-name") for a in (govde.get("aliases") or [])]
    return [a for a in adlar if a], govde.get("type")


def eslesmeleri_kur(
    conn: sqlite3.Connection, mb: ApiIstemci, *, tum: bool = False,
    ilerleme: bool = True,
) -> dict[str, str]:
    """Alias → kanonik anahtar eşlemesi üret.

    Yalnız iki tarafı da kütüphanede var olan adlar birleşir (bkz. modül
    başlığı). Kanonik: kredisi en çok olan yazım, eşitlikte Latin yazımlı.
    """
    kisiler = hedef_kisiler(conn, tum=tum)
    kutuphane = kutuphane_anahtarlari(conn)
    eslesme: dict[str, str] = {}

    for sira, (mbid, ad) in enumerate(kisiler, 1):
        if ilerleme and sira % 25 == 0:
            print(f"  {sira}/{len(kisiler)}", file=sys.stderr)
        adlar, tur = aliaslari_getir(mb, mbid)
        if not adlar or (tur and tur != "Person"):
            continue  # grup aliasları kişi grafiğini bozar

        # Yalnız KÜTÜPHANEDE gerçekten duran yazımlar. MusicBrainz'in
        # bilmediğimiz bir kişiye dair iddiası veritabanına sızmamalı.
        varyantlar = {
            k for k in (normalize_esleme(a) for a in adlar) if k and k in kutuphane
        }
        if len(varyantlar) < 2:
            continue  # birleştirilecek bir şey yok

        okunur = {normalize_esleme(a): a for a in adlar}
        kanonik = max(
            varyantlar,
            key=lambda k: (kutuphane.get(k, 0), _latin_mi(okunur.get(k, k))),
        )
        for varyant in varyantlar:
            if varyant != kanonik:
                eslesme[varyant] = kanonik
    return eslesme


def eslesmeleri_yaz(conn: sqlite3.Connection, eslesme: dict[str, str]) -> int:
    with conn:
        conn.executemany(
            "INSERT INTO kisi_eslesme (anahtar, kanonik, kaynak) "
            "VALUES (?,?,'musicbrainz') "
            "ON CONFLICT(anahtar) DO UPDATE SET kanonik=excluded.kanonik",
            [(a, k) for a, k in eslesme.items()],
        )
    return len(eslesme)


def eslesmeleri_oku(conn: sqlite3.Connection) -> dict[str, str]:
    """Kayıtlı eşlemeler. Tablo yoksa boş — çağıran kırılmamalı."""
    try:
        return {r[0]: r[1] for r in conn.execute(
            "SELECT anahtar, kanonik FROM kisi_eslesme"
        )}
    except sqlite3.Error:
        return {}


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--tum", action="store_true",
                             help="enstrüman rolleriyle sınırlama, hepsini tara")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        eslesme = eslesmeleri_kur(conn, musicbrainz(), tum=args.tum)
        yazilan = eslesmeleri_yaz(conn, eslesme)
        print(f"\n{yazilan} eşleme yazıldı")
        for anahtar, kanonik in sorted(eslesme.items())[:25]:
            print(f"  {anahtar}  →  {kanonik}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
