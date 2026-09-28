"""Spaces yedeği — ağsız, sahte API ile.

Korunan üç şey: yalnız değişen gönderilir; SQLite anlık kopyayla gönderilir;
yerelde silinen (hesap silme) depodan da silinir.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class _SahteApi:
    def __init__(self):
        self.commitler = []

    def create_commit(self, *, repo_id, repo_type, operations, commit_message):
        assert repo_type == "dataset"
        kayit = []
        for o in operations:
            if type(o).__name__ == "CommitOperationAdd":
                kayit.append(("ekle", o.path_in_repo, Path(o.path_or_fileobj).read_bytes()))
            else:
                kayit.append(("sil", o.path_in_repo, None))
        self.commitler.append(kayit)


def _kur(kok: Path):
    (kok / "data/db/kullanici").mkdir(parents=True)
    (kok / "data/cache/clap").mkdir(parents=True)
    conn = sqlite3.connect(kok / "data/db/ortak.sqlite")
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    sqlite3.connect(kok / "data/db/kullanici/2.sqlite").close()
    (kok / "data/cache/clap/a.npy").write_bytes(b"gomu")
    (kok / "data/cache/stemler").mkdir()
    (kok / "data/cache/stemler/x.npy").write_bytes(b"buyuk")  # yedeğe girmemeli


def test_yalniz_degisen_gider_silinen_silinir(tmp_path):
    from python.hf_yedek import Yedekci

    _kur(tmp_path)
    api = _SahteApi()
    y = Yedekci("u/kesif-veri", kok=tmp_path, api=api)

    assert y.tur() == (3, 0)
    yollar = sorted(k[1] for k in api.commitler[0])
    assert yollar == ["data/cache/clap/a.npy", "data/db/kullanici/2.sqlite",
                      "data/db/ortak.sqlite"]
    # SQLite anlık kopyası gerçekten okunabilir bir veritabanı.
    kopya = tmp_path / "kopya.sqlite"
    kopya.write_bytes(next(k[2] for k in api.commitler[0] if k[1].endswith("ortak.sqlite")))
    assert sqlite3.connect(kopya).execute("SELECT x FROM t").fetchone() == (1,)

    assert y.tur() == (0, 0) and len(api.commitler) == 1   # değişiklik yok → commit yok

    (tmp_path / "data/db/kullanici/2.sqlite").unlink()      # hesap silindi
    assert y.tur() == (0, 1)
    assert api.commitler[-1] == [("sil", "data/db/kullanici/2.sqlite", None)]


def test_disk_doluysa_geri_yukleme_yapmaz(tmp_path):
    from python.hf_yedek import geri_yukle

    _kur(tmp_path)
    assert geri_yukle("u/kesif-veri", kok=tmp_path) == 0   # ağa çıkmadan döner


def test_degiskenler_yoksa_kapali(monkeypatch, tmp_path):
    import python.hf_yedek as H

    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("KESIF_YEDEK_DEPO", raising=False)
    assert not H.etkin()
    H.acilis(tmp_path)          # yerelde hiçbir şey yapmaz
    assert H._YEDEKCI is None
