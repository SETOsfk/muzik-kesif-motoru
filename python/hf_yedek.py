"""Hugging Face Spaces'te kalıcı veri: özel bir veri deposuna yedek.

## Neden

Ücretsiz Space'in diski geçici: her yeniden başlatmada (güncelleme, 48 saat
uyku) `data/` sıfırlanır. Her 👍/👎 SQLite'a yazıldığı için bu, kullanıcıların
kararlarını ve hesaplarını kaybetmek demekti (karar günlüğü 2026-09-15).

Çözüm: veri, kullanıcının Hugging Face hesabındaki ÖZEL bir veri deposunda
(`KESIF_YEDEK_DEPO`, ör. `setosfk/kesif-veri`) durur.

- Açılışta disk boşsa depodan geri yüklenir (`geri_yukle`).
- Çalışırken `ARALIK_SN`de bir yalnız DEĞİŞEN dosyalar gönderilir; SQLite
  dosyası yazılırken kopyalanmasın diye `backup` API'siyle anlık kopya alınır.
- Yerelde silinen dosya depodan da silinir: hesap silme (`hesap.hesap_sil`)
  yedekten de düşmeli, yoksa bir sonraki açılışta hesap geri gelirdi.

Kötü durumda kaybolan: son yedekten sonraki birkaç dakikanın kararları.

Yalnız `HF_TOKEN` ve `KESIF_YEDEK_DEPO` ikisi de tanımlıysa çalışır; yerelde
hiçbir şey yapmaz.

İlk yükleme (Mac'te, bir kez):
    HF_TOKEN=... python -m python.hf_yedek yukle --depo KULLANICI/kesif-veri
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
import threading
import time
from pathlib import Path

DEPO_DEGISKENI = "KESIF_YEDEK_DEPO"
JETON_DEGISKENI = "HF_TOKEN"
ARALIK_SN = int(os.environ.get("KESIF_YEDEK_ARALIK", "300"))

#: Sunmak için gereken veri (ölçüldü 2026-09-15: ~47 MB). Stem önbelleği ve
#: FMA çevrimdışı hattın malı; yedeğe girmez.
KALIPLAR = (
    "data/db/ortak.sqlite",
    "data/db/kullanici/*.sqlite",
    "data/cache/clap/*.npy",
    "data/cache/clap_parca/*.npy",
)

Imza = dict[str, tuple[int, int]]  # göreli yol → (mtime_ns, boyut)


def etkin() -> bool:
    return bool(os.environ.get(DEPO_DEGISKENI) and os.environ.get(JETON_DEGISKENI))


def imza_al(kok: Path) -> Imza:
    imza: Imza = {}
    for kalip in KALIPLAR:
        for yol in kok.glob(kalip):
            if yol.is_file():
                d = yol.stat()
                imza[yol.relative_to(kok).as_posix()] = (d.st_mtime_ns, d.st_size)
    return imza


def degisiklikler(onceki: Imza, simdiki: Imza) -> tuple[list[str], list[str]]:
    """(gönderilecek, silinecek) — değişmeyen dosyaya dokunulmaz."""
    gonder = sorted(y for y, i in simdiki.items() if onceki.get(y) != i)
    sil = sorted(set(onceki) - set(simdiki))
    return gonder, sil


def _anlik_kopya(kaynak: Path, hedef: Path) -> None:
    """SQLite'ın tutarlı kopyası — yazma sürerken düz kopya bozuk gelebilir."""
    k = sqlite3.connect(kaynak)
    h = sqlite3.connect(hedef)
    try:
        k.backup(h)
    finally:
        h.close()
        k.close()


class Yedekci:
    def __init__(self, depo: str, *, kok: Path = Path("."), api=None):
        if api is None:
            from huggingface_hub import HfApi
            api = HfApi(token=os.environ.get(JETON_DEGISKENI))
        self.depo, self.kok, self.api = depo, kok, api
        self.imza: Imza = {}
        self._kilit = threading.Lock()

    def tur(self) -> tuple[int, int]:
        """Değişenleri gönder, silinenleri sil. (gönderilen, silinen) döner."""
        from huggingface_hub import CommitOperationAdd, CommitOperationDelete

        with self._kilit:
            simdiki = imza_al(self.kok)
            gonder, sil = degisiklikler(self.imza, simdiki)
            if not gonder and not sil:
                return 0, 0
            with tempfile.TemporaryDirectory() as gecici:
                islemler = []
                for sira, goreli in enumerate(gonder):
                    yol = self.kok / goreli
                    if yol.suffix == ".sqlite":
                        kopya = Path(gecici) / f"{sira}.sqlite"
                        _anlik_kopya(yol, kopya)
                        yol = kopya
                    islemler.append(CommitOperationAdd(goreli, str(yol)))
                islemler += [CommitOperationDelete(goreli) for goreli in sil]
                self.api.create_commit(
                    repo_id=self.depo, repo_type="dataset", operations=islemler,
                    commit_message=f"yedek: {len(gonder)} dosya, {len(sil)} silme")
            self.imza = simdiki
            return len(gonder), len(sil)


def geri_yukle(depo: str, *, kok: Path = Path(".")) -> int:
    """Disk boşsa veriyi depodan indir. İndirilen dosya sayısı."""
    if (kok / "data/db/ortak.sqlite").exists():
        return 0
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=depo, repo_type="dataset", local_dir=str(kok),
                      allow_patterns=["data/**"], token=os.environ.get(JETON_DEGISKENI))
    return len(imza_al(kok))


_YEDEKCI: Yedekci | None = None


def acilis(kok: Path = Path(".")) -> None:
    """Sunucu açılışı: geri yükle, sonra arka planda düzenli yedekle."""
    global _YEDEKCI
    if not etkin():
        return
    depo = os.environ[DEPO_DEGISKENI]
    try:
        n = geri_yukle(depo, kok=kok)
        print(f"[yedek] {depo}: {n} dosya geri yüklendi", file=sys.stderr)
    except Exception as hata:  # noqa: BLE001 — boş depo ya da ağ: boş başla
        print(f"[yedek] geri yükleme yapılamadı: {hata}", file=sys.stderr)
    _YEDEKCI = Yedekci(depo, kok=kok)
    _YEDEKCI.imza = imza_al(kok)  # geri yüklenenleri yeniden gönderme

    def _dongu():
        while True:
            time.sleep(ARALIK_SN)
            try:
                _YEDEKCI.tur()
            except Exception as hata:  # noqa: BLE001 — bir sonraki turda yeniden
                print(f"[yedek] {type(hata).__name__}: {hata}", file=sys.stderr)

    threading.Thread(target=_dongu, name="yedek", daemon=True).start()


def kapanis() -> None:
    if _YEDEKCI is not None:
        try:
            _YEDEKCI.tur()
        except Exception as hata:  # noqa: BLE001
            print(f"[yedek] kapanışta: {hata}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Veriyi Hugging Face veri deposuna yükle")
    a.add_argument("komut", choices=["yukle"])
    a.add_argument("--depo", required=True, help="KULLANICI/kesif-veri")
    args = a.parse_args(argv)
    if not os.environ.get(JETON_DEGISKENI):
        print(f"{JETON_DEGISKENI} tanımlı değil", file=sys.stderr)
        return 1
    from huggingface_hub import HfApi

    HfApi(token=os.environ[JETON_DEGISKENI]).create_repo(
        args.depo, repo_type="dataset", private=True, exist_ok=True)
    gonderilen, _ = Yedekci(args.depo).tur()
    print(f"{args.depo} (özel): {gonderilen} dosya yüklendi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
