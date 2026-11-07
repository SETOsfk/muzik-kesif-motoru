"""Kütüphane kıyası — sanatçı listesinden, gerçek açık veriyle (2026-11-07).

Kütüphanenin yalnız SANATÇI ADLARIYLA (FLAC klasör adları yeter) üretimdeki
gizleme sınamasını (`degerlendirme.calistir`, K19) koşar:

1. Deezer çalma listesi hasadı — üretimdeki yöntem (`calma_listesi.hasat`).
2. Dış komşuluklar — Deezer benzerleri, ListenBrainz, MusicBrainz kadrosu.
3. Eksenler MusicBrainz ETİKETLERİNDEN (küresel k-ortalamalar, kosinüs). Çalma
   listesinden kurulmaz: ölçülen yöntemle aynı veriden türeyen eksen sınamayı
   kendi cevabına yaslardı. Etiketi olmayan sanatçının ekseni tüm kütüphane.
4. Gizleme sınaması + motor (iç içe CV). Ses yolu YOK (gömüler kütüphane
   sahibinin makinesinde).

Kişisel veri: sanatçı listesi `--sanatcilar` dosyasından okunur, repoya girmez.
Gerçek `data/`'ya dokunmaz: `--kok` zorunlu.

    python scripts/kutuphane_kiyasi.py --kok <klasör> --sanatcilar adlar.txt \\
        [--onbellek <ortak önbellek>] [--es-adlar es.json] [--json sonuc.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python import degerlendirme as D  # noqa: E402
from python.db import baglan  # noqa: E402
from python.discover import calma_listesi as L  # noqa: E402
from python.discover import komsuluk as K  # noqa: E402
from python.discover.listenbrainz import listenbrainz  # noqa: E402
from python.metin import normalize_esleme  # noqa: E402
from python.onbellek import musicbrainz  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
CALISMA = "etiket-kume"


def etiketler(mb, ad: str) -> Counter:
    """MusicBrainz etiket + tür sayıları (iç kullanım; gösterilmez)."""
    mbid = K._mbid(mb, ad)
    if not mbid:
        return Counter()
    try:
        govde = mb.get_json(f"artist/{mbid}", {"inc": "tags+genres", "fmt": "json"})
    except Exception:
        return Counter()
    say = Counter()
    for alan in ("tags", "genres"):
        for e in (govde or {}).get(alan) or []:
            if e.get("name") and (e.get("count") or 0) > 0:
                say[e["name"].lower()] += int(e["count"])
    return say


def kume_kur(vektor: dict[str, Counter], *, k_araligi=range(5, 11), tohum: int = 0
             ) -> dict[str, int]:
    """Küresel k-ortalamalar, tf-idf etiket vektörleri; k kosinüs siluetiyle."""
    adlar = [a for a, v in vektor.items() if v]
    sozluk = sorted({e for a in adlar for e in vektor[a]
                     if sum(1 for b in adlar if e in vektor[b]) >= 2})
    if len(adlar) < 10 or not sozluk:
        return {}
    X = np.array([[np.log1p(vektor[a].get(e, 0)) for e in sozluk] for a in adlar])
    idf = np.log(len(adlar) / (1 + (X > 0).sum(axis=0)))
    X = X * idf
    X /= np.linalg.norm(X, axis=1, keepdims=True).clip(1e-9)
    en_iyi, en_iyi_s = None, -2.0
    for k in k_araligi:
        rng = np.random.default_rng(tohum)
        M = X[[int(rng.integers(len(X)))]]
        while len(M) < k:                         # k-ortalamalar++
            d = 1 - (X @ M.T).max(axis=1)
            M = np.vstack([M, X[int(rng.choice(len(X), p=d.clip(0) / d.clip(0).sum()))]])
        for _ in range(50):
            atama = (X @ M.T).argmax(axis=1)
            yeni = np.array([X[atama == j].sum(axis=0) if (atama == j).any() else M[j]
                             for j in range(k)])
            yeni /= np.linalg.norm(yeni, axis=1, keepdims=True).clip(1e-9)
            if np.allclose(yeni, M):
                break
            M = yeni
        S = X @ X.T
        sil = []
        for i in range(len(X)):
            ic = S[i, atama == atama[i]]
            a = 1 - (ic.sum() - 1) / max(len(ic) - 1, 1)
            b = min((1 - S[i, atama == j].mean()) for j in set(atama.tolist()) - {atama[i]}) \
                if len(set(atama.tolist())) > 1 else 0
            sil.append((b - a) / max(a, b, 1e-9))
        if np.mean(sil) > en_iyi_s:
            en_iyi, en_iyi_s = atama.copy(), float(np.mean(sil))
    print(f"   eksen: k={len(set(en_iyi.tolist()))}, kosinüs silueti {en_iyi_s:.3f}",
          file=sys.stderr)
    return dict(zip(adlar, en_iyi.tolist()))


def main(argv: list[str] | None = None) -> int:
    ay = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ay.add_argument("--kok", type=Path, required=True)
    ay.add_argument("--sanatcilar", type=Path, required=True,
                    help="satır başına bir sanatçı adı")
    ay.add_argument("--onbellek", type=Path, help="ortak önbellek (varsayılan: <kok>/onbellek)")
    ay.add_argument("--es-adlar", type=Path, help='{"Takanaka": "Masayoshi Takanaka"}')
    ay.add_argument("--cevrimdisi", action="store_true")
    ay.add_argument("--json", type=Path)
    args = ay.parse_args(argv)

    kok = args.kok.resolve()
    if (KOK / "data").resolve() in [kok, *kok.parents]:
        ay.error("--kok gerçek data/ klasörünün içinde olamaz")
    kok.mkdir(parents=True, exist_ok=True)
    onbellek = (args.onbellek or kok / "onbellek").resolve()
    es = json.loads(args.es_adlar.read_text()) if args.es_adlar else {}
    adlar = sorted({es.get(a.strip(), a.strip())
                    for a in args.sanatcilar.read_text(encoding="utf-8").splitlines()
                    if a.strip()})
    print(f"{len(adlar)} sanatçı", file=sys.stderr)

    conn = baglan(kok / "kutuphane.sqlite")
    with conn:
        for a in adlar:
            conn.execute("INSERT OR IGNORE INTO albums (album_id, artist, title) VALUES (?,?,?)",
                         (f"kut:{normalize_esleme(a)}", a, "—"))
    dz = L.deezer_listesi(onbellek_kok=onbellek, cevrimdisi=args.cevrimdisi)
    mb = musicbrainz(onbellek_kok=onbellek, cevrimdisi=args.cevrimdisi)
    lb = listenbrainz(onbellek_kok=onbellek, cevrimdisi=args.cevrimdisi)

    print("1/4 çalma listesi hasadı…", file=sys.stderr)
    print(f"   {L.hasat(conn, dz)}", file=sys.stderr)
    print("2/4 dış komşuluklar…", file=sys.stderr)
    dis = K.komsular_topla(adlar, dz=dz, mb=mb, lb=lb, ilerleme=lambda i, n, ad, say: print(
        f"   {i}/{n} {ad}: " + " · ".join(f"{y} {k}" for y, k in say.items()), file=sys.stderr))
    print("3/4 etiket eksenleri…", file=sys.stderr)
    atama = kume_kur({a: etiketler(mb, a) for a in adlar})
    with conn:
        conn.execute("DELETE FROM memberships WHERE calisma_id = ?", (CALISMA,))
        conn.execute("DELETE FROM clusters WHERE calisma_id = ?", (CALISMA,))
        for j in sorted(set(atama.values())):
            conn.execute("INSERT INTO clusters (kume_id, calisma_id, stabil_mi) VALUES (?,?,1)",
                         (j, CALISMA))
        for a, j in atama.items():
            conn.execute("INSERT INTO memberships (album_id, calisma_id, kume_id, uyelik) "
                         "VALUES (?,?,?,1.0)", (f"kut:{normalize_esleme(a)}", CALISMA, j))
    print("4/4 gizleme sınaması + motor…", file=sys.stderr)
    sonuc = D.calistir(conn, calisma=CALISMA if atama else None, olcut="npmi", buzulme=1.0,
                       melez_agirlik=(1.0, 2.0), motor=True, dis_komsular=dis)
    print(D.rapor(sonuc))
    print(D.motor_raporu(sonuc))
    # Üretimdeki adlarla: <kok>/kutuphane.motor.json ve .olcum.json (Ölçümler sayfası).
    from python import motor as M
    if "_motor_ayar" in sonuc:
        M.ayar_yaz(sonuc["_motor_ayar"], M.ayar_yolu(conn))
    olcum = D.olcum_ozeti(sonuc, kaynak="sanatçı listesi (ses yolu yok)")
    M.olcum_yolu(conn).write_text(json.dumps(olcum, ensure_ascii=False, indent=1))
    if args.json:
        args.json.write_text(json.dumps(
            {**olcum, "ayrinti": {ad: v["ayrinti"] for ad, v in sonuc.items()
                                  if not ad.startswith("_")}, "eksen": atama},
            ensure_ascii=False, indent=1, default=str))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
