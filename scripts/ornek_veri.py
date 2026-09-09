"""Yapısı bilinen sentetik kütüphane üret — kümelemeyi doğrulamak için.

Gerçek kütüphaneyle test etmenin sorunu, doğru cevabı bilmemek: FCM 5 küme
bulduğunda bunun iyi mi kötü mü olduğunu söyleyemezsin. Burada eksenler önceden
kurulur (hangi albüm hangi sahneye ait, kim kiminle çalmış), sonra kümelemenin
o yapıyı geri bulup bulmadığına bakılır.

Sahneler kullanıcının gerçek dinleme profilinden (CLAUDE.md) türetildi. İsimler
uydurmadır — gerçek müzisyen adı kullanmak, sentetik veriyi gerçek sanılabilir
hale getirirdi.

İki albüm bilinçli olarak iki sahneye birden ait (ortak kadro): bulanık üyeliğin
işe yaradığı yer orası, keskin kümeleme o bilgiyi kaybeder (K3).

Kullanım:
    python scripts/ornek_veri.py --db data/db/ornek.sqlite
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.db import baglan
from python.metin import album_kimligi

TOHUM = 20260811

# --------------------------------------------------------------------------- #
# Sahneler: (ad, sanatçılar, kadro havuzu, label, ülke, yıl aralığı, etiketler,
#            tempo ortalaması, dinamik aralık ortalaması, ritmik karmaşıklık)
# --------------------------------------------------------------------------- #
SAHNELER = [
    {
        "ad": "teknik-prog-metal",
        "sanatcilar": ["Kavis", "Ardıç Kolektif", "Yedinci Kat", "Nadir Açı"],
        "kadro": [
            "Deniz Arun", "Mert Sağlam", "Kaan Uçar", "Bora Efe", "Selin Kaya",
            "Emre Tan", "Onur Bilge",
        ],
        "label": "Kuzey Kayıt",
        "ulke": "TR",
        "yillar": (2004, 2019),
        "etiketler": {"progressive metal": 0.5, "technical death metal": 0.3, "metal": 0.2},
        "ses": (168.0, 9.0, 0.82),
    },
    {
        "ad": "jazz-fusion",
        "sanatcilar": ["Üçlü Devinim", "Gece Seyri", "Mavi Oda"],
        "kadro": [
            "Levent Uz", "Ayşe Demirsoy", "Tarık Öz", "Bora Efe", "Cem Aksoy",
            "Nil Erdem",
        ],
        "label": "Blue Line",
        "ulke": "US",
        "yillar": (1972, 1984),
        "etiketler": {"jazz fusion": 0.5, "jazz": 0.3, "progressive rock": 0.2},
        "ses": (132.0, 15.0, 0.74),
    },
    {
        "ad": "turk-rock",
        "sanatcilar": ["Sekiz Sokak", "Hasat", "Gölge Bandı", "Kırık Cam"],
        "kadro": [
            "Serkan Yıldız", "Pınar Ateş", "Umut Kılıç", "Selin Kaya", "Doruk Han",
        ],
        "label": "Anadolu Plak",
        "ulke": "TR",
        "yillar": (1996, 2012),
        "etiketler": {"alternative rock": 0.4, "rock": 0.35, "anatolian rock": 0.25},
        "ses": (124.0, 11.0, 0.55),
    },
    {
        "ad": "hip-hop",
        "sanatcilar": ["Beton Kat", "Alt Geçit", "Yankı Odası"],
        "kadro": ["Volkan Er", "Ceyda Naz", "Tarık Öz", "Barış Gün"],
        "label": "Dip Nota",
        "ulke": "TR",
        "yillar": (2008, 2021),
        "etiketler": {"hip hop": 0.55, "boom bap": 0.25, "rap": 0.2},
        "ses": (92.0, 7.0, 0.41),
    },
]

# Kadroda bilinçli örtüşmeler:
#   Bora Efe    → prog metal + jazz-fusion  (davulcu ekseni)
#   Selin Kaya  → prog metal + türk rock    (gitar ekseni)
#   Tarık Öz    → jazz-fusion + hip-hop     (bas / sample ekseni)

ROLLER = ["drums", "bass", "guitar", "keyboards", "vocals", "producer", "engineer"]


def uret(conn, albums_hedef: int = 60) -> dict[str, int]:
    rastgele = random.Random(TOHUM)
    sayac = {"album": 0, "kredi": 0, "etiket": 0, "ses": 0, "dinleme": 0}
    albom_basina = max(1, albums_hedef // sum(len(s["sanatcilar"]) for s in SAHNELER))

    with conn:
        for sahne in SAHNELER:
            for sanatci in sahne["sanatcilar"]:
                for sira in range(albom_basina):
                    yil = rastgele.randint(*sahne["yillar"])
                    baslik = f"{sahne['ad'].split('-')[0].title()} {sira + 1}"
                    baslik = f"{baslik} / {sanatci.split()[0]}"
                    album_id = album_kimligi(sanatci, baslik, yil)

                    conn.execute(
                        """INSERT OR REPLACE INTO albums
                           (album_id, mbid, artist, title, year, country, label,
                            path, track_count, eklenme_tarihi)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (album_id, None, sanatci, baslik, yil, sahne["ulke"],
                         sahne["label"], f"/sentetik/{album_id}", 9, "2026-08-11"),
                    )
                    sayac["album"] += 1

                    # Kadro: sahnenin havuzundan 4–6 kişi, biri mutlaka örtüşen isim.
                    kadro = rastgele.sample(sahne["kadro"], rastgele.randint(4, min(6, len(sahne["kadro"]))))
                    for kisi in kadro:
                        rol = rastgele.choice(ROLLER)
                        conn.execute(
                            """INSERT OR IGNORE INTO credits
                               (album_id, person_id, person_name, role, kaynak)
                               VALUES (?,?,?,?,?)""",
                            (album_id, None, kisi, rol, "sentetik"),
                        )
                        sayac["kredi"] += 1

                    for etiket, agirlik in sahne["etiketler"].items():
                        sapma = rastgele.uniform(-0.05, 0.05)
                        conn.execute(
                            "INSERT OR REPLACE INTO tags (album_id, tag, agirlik) VALUES (?,?,?)",
                            (album_id, etiket, round(max(0.01, agirlik + sapma), 4)),
                        )
                        sayac["etiket"] += 1

                    tempo, dinamik, ritim = sahne["ses"]
                    conn.execute(
                        """INSERT OR REPLACE INTO audio_features
                           (album_id, tempo_medyan, tempo_iqr, dinamik_aralik,
                            ritmik_karmasiklik, spektral_merkez)
                           VALUES (?,?,?,?,?,?)""",
                        (
                            album_id,
                            round(rastgele.gauss(tempo, 12), 2),
                            round(abs(rastgele.gauss(14, 5)), 2),
                            round(rastgele.gauss(dinamik, 2), 2),
                            round(min(0.99, max(0.05, rastgele.gauss(ritim, 0.06))), 4),
                            round(rastgele.gauss(2200 + tempo * 3, 300), 1),
                        ),
                    )
                    sayac["ses"] += 1

                    # Dinleme geçmişi: her albüm için birkaç gün.
                    for _ in range(rastgele.randint(0, 6)):
                        gun = f"2026-{rastgele.randint(1, 8):02d}-{rastgele.randint(1, 28):02d}"
                        conn.execute(
                            """INSERT OR IGNORE INTO plays
                               (album_id, tarih, track, adet, kaynak)
                               VALUES (?,?,?,?,?)""",
                            (album_id, gun, f"parça {rastgele.randint(1, 9)}",
                             rastgele.randint(1, 3), "sentetik"),
                        )
                        sayac["dinleme"] += 1

    return sayac


#: Gerçekten iki sahneye birden ait albümler. Ortak kadro tek başına yetmiyor —
#: etiket, label ve ses de karışmazsa küme ayrımı bunları yine bir tarafa çekiyor.
#: Bulanık üyeliğin keskin kümelemeden farkı tam olarak burada görünür (K3).
MELEZLER = [
    ("Kavis", "Ortak Yol", 2011, 0, 1),   # prog metal × jazz-fusion
    ("Gece Seyri", "Ara Bölge", 1981, 1, 3),  # jazz-fusion × hip-hop
    ("Hasat", "İki Nehir", 2003, 2, 0),   # türk rock × prog metal
    ("Alt Geçit", "Köprü", 2014, 3, 2),   # hip-hop × türk rock
]


def melezleri_ekle(conn, rastgele: random.Random) -> int:
    """İki sahnenin ortasında duran albümler üret."""
    eklenen = 0
    with conn:
        for sanatci, baslik, yil, a, b in MELEZLER:
            sahne_a, sahne_b = SAHNELER[a], SAHNELER[b]
            album_id = album_kimligi(sanatci, baslik, yil)
            conn.execute(
                """INSERT OR REPLACE INTO albums
                   (album_id, mbid, artist, title, year, country, label,
                    path, track_count, eklenme_tarihi)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (album_id, None, sanatci, baslik, yil, sahne_a["ulke"],
                 sahne_a["label"], f"/sentetik/{album_id}", 9, "2026-08-11"),
            )

            # Kadro yarı yarıya iki havuzdan.
            for havuz in (sahne_a["kadro"], sahne_b["kadro"]):
                for kisi in rastgele.sample(havuz, 3):
                    conn.execute(
                        """INSERT OR IGNORE INTO credits
                           (album_id, person_id, person_name, role, kaynak)
                           VALUES (?,?,?,?,?)""",
                        (album_id, None, kisi, rastgele.choice(ROLLER), "sentetik"),
                    )

            # Etiketler iki sahneden yarışır.
            for sahne in (sahne_a, sahne_b):
                for etiket, agirlik in sahne["etiketler"].items():
                    conn.execute(
                        "INSERT OR REPLACE INTO tags (album_id, tag, agirlik) VALUES (?,?,?)",
                        (album_id, etiket, round(agirlik / 2, 4)),
                    )

            # Ses öznitelikleri tam ortada.
            ort = [(x + y) / 2 for x, y in zip(sahne_a["ses"], sahne_b["ses"])]
            conn.execute(
                """INSERT OR REPLACE INTO audio_features
                   (album_id, tempo_medyan, tempo_iqr, dinamik_aralik,
                    ritmik_karmasiklik, spektral_merkez)
                   VALUES (?,?,?,?,?,?)""",
                (album_id, round(ort[0], 2), 14.0, round(ort[1], 2),
                 round(ort[2], 4), round(2200 + ort[0] * 3, 1)),
            )
            eklenen += 1
    return eklenen


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Sentetik örnek kütüphane üret.")
    ayristirici.add_argument("--db", type=Path, default=Path("data/db/ornek.sqlite"))
    ayristirici.add_argument("--albums", type=int, default=60)
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        sayac = uret(conn, args.albums)
        sayac["melez"] = melezleri_ekle(conn, random.Random(TOHUM + 1))
        sayac["album"] += sayac["melez"]
    finally:
        conn.close()

    print(f"Sentetik kütüphane: {args.db}")
    for ad, adet in sayac.items():
        print(f"  {ad:<8}: {adet}")
    print(f"Beklenen yapı: {len(SAHNELER)} sahne — " + ", ".join(s["ad"] for s in SAHNELER))
    print("Örtüşen kadro: Bora Efe (metal+fusion), Selin Kaya (metal+rock), Tarık Öz (fusion+hip-hop)")
    print(f"Melez albüm (iki sahnenin ortasında): {len(MELEZLER)} — " +
          ", ".join(f"{s[0]} / {s[1]}" for s in MELEZLER))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
