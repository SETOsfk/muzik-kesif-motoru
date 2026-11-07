"""İnsan çifti kıyası — gerçek açık veriyle, kütüphaneden bağımsız (2026-11-07).

Forumda doğrulanmış «X'i seven Y'yi dener» çiftlerinin (`docs/arastirma/
insan-ciftleri.csv`) tohum sanatçıları için:

1. Deezer çalma listesi hasadı — üretimdeki yöntemle (`calma_listesi.hasat`):
   listeler tohumların ADIYLA aranır, öneri sanatçısı aranmaz.
2. Deezer «benzer sanatçılar», ListenBrainz komşuları, MusicBrainz kadrosu
   (`discover/komsuluk.py`).

Sonra her yol ve birleşimler insan önerilerine karşı ölçülür
(`degerlendirme.cift_sinamasi`, kütüphane = tohumlar). Gerçek `data/`'ya
dokunmaz: `--kok` zorunlu (CLAUDE.md, değişmez kısıtlar).

    python scripts/insan_cifti_kiyasi.py --kok <klasör> [--cevrimdisi] [--json sonuç.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python import degerlendirme as D  # noqa: E402
from python.db import baglan  # noqa: E402
from python.discover import calma_listesi as L  # noqa: E402
from python.discover import komsuluk as K  # noqa: E402
from python.discover.listenbrainz import listenbrainz  # noqa: E402
from python.metin import normalize_esleme  # noqa: E402
from python.onbellek import musicbrainz  # noqa: E402

KOK = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ay = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ay.add_argument("--kok", type=Path, required=True,
                    help="kıyas veritabanı ve önbellek klasörü (data/ DEĞİL)")
    ay.add_argument("--ciftler", type=Path, default=KOK / "docs/arastirma/insan-ciftleri.csv")
    ay.add_argument("--cevrimdisi", action="store_true", help="yalnız önbellekten")
    ay.add_argument("--json", type=Path, help="sonuçları JSON olarak yaz")
    args = ay.parse_args(argv)

    kok = args.kok.resolve()
    if (KOK / "data").resolve() in [kok, *kok.parents]:
        ay.error("--kok gerçek data/ klasörünün içinde olamaz")
    kok.mkdir(parents=True, exist_ok=True)
    onbellek = kok / "onbellek"
    ciftler = D.ciftleri_oku(args.ciftler)
    tohumlar = sorted({t for c in ciftler for t in c["tohumlar"]})
    print(f"{len(ciftler)} doğrulanmış çift · {len(tohumlar)} tohum sanatçı", file=sys.stderr)

    conn = baglan(kok / "kiyas.sqlite")
    with conn:
        for t in tohumlar:
            conn.execute("INSERT OR IGNORE INTO albums (album_id, artist, title) VALUES (?,?,?)",
                         (f"tohum:{normalize_esleme(t)}", t, "—"))
    dz = L.deezer_listesi(onbellek_kok=onbellek, cevrimdisi=args.cevrimdisi)
    print("1/2 çalma listesi hasadı (Deezer)…", file=sys.stderr)
    sayac = L.hasat(conn, dz)
    print(f"   {sayac}", file=sys.stderr)

    print("2/2 komşuluklar (Deezer benzerleri, ListenBrainz, MusicBrainz kadrosu)…",
          file=sys.stderr)
    mb = musicbrainz(onbellek_kok=onbellek, cevrimdisi=args.cevrimdisi)
    lb = listenbrainz(onbellek_kok=onbellek, cevrimdisi=args.cevrimdisi)
    dis = K.komsular_topla(tohumlar, dz=dz, mb=mb, lb=lb, ilerleme=lambda i, n, ad, say: print(
        f"   {i}/{n} {ad}: " + " · ".join(f"{y} {k}" for y, k in say.items()), file=sys.stderr))
    (kok / "komsular.json").write_text(json.dumps(dis, ensure_ascii=False, indent=1))

    sonuc = D.cift_sinamasi(conn, ciftler, dis_komsular=dis, kutuphane_haric=False)
    print(D.cift_raporu(sonuc))
    if args.json:
        args.json.write_text(json.dumps(
            {k: v for k, v in sonuc.items()}, ensure_ascii=False, indent=1, default=str))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
