"""Kümeleme ayarları — blok ağırlıkları, m, c aralığı, eşikler.

Kümeleme kararlarının tek yeri burası. Parametreyle oynarken başka dosyaya
dokunmak gerekmez; `calistir.py` her ayarı komut satırından da kabul eder.

Blok ağırlıkları, matriste zaten satır-L2 normalize edilmiş bloklara çarpan
olarak uygulanır — yani doğrudan karşılaştırılabilirler. Kredi bloğunun ağırlığı
en yüksek: projenin çekirdek tezi bu (CLAUDE.md, "çözülmesi gereken asıl problem").
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass(frozen=True)
class Ayar:
    # --- girdi / çıktı ---
    matris: Path = Path("data/ozellikler.parquet")
    db: Path = Path("data/db/kesif.sqlite")

    # --- blok ağırlıkları ---
    blok_agirliklari: dict[str, float] = field(
        default_factory=lambda: {
            "kredi": 1.0,   # çekirdek tez: kim ÇALMIŞ
            "etiket": 0.7,  # tür bağlamı
            "uretim": 0.5,  # kim üretmiş/mikslemiş — sahne sinyali, ama zayıf:
                            # mastering mühendisi müzikal yakınlık göstermez
            "sahne": 0.5,   # label / ülke / dönem
            "ses": 0.4,     # librosa özetleri
        }
    )

    # --- boyut indirgeme (K3: yüksek boyutta üyelikler 1/c'ye yakınsar) ---
    # Ölçüt açıklanan varyans DEĞİL, ayrışabilirlik. K3 boyut indirgemeyi
    # "üyelikler 1/c'ye yakınsıyor" diye istiyor; o halde hedef de bu çöküşü
    # engellemek olmalı. Gerçek kütüphanede ölçüldü (302 albüm, 1287 öznitelik):
    #   100 boyut → PE 1.00 (yapı yok)   30 boyut → PE 0.93
    #    10 boyut → PE 0.48               8 boyut → PE 0.28
    # Varyans hedeflemek burada tam ters çalışıyor: %80 varyans 80 bileşen
    # istiyor ve o boyutta mesafeler tamamen yoğunlaşıyor.
    yontem: str = "pca"            # "pca" | "umap"
    bilesen: int = 8               # sabit ve küçük; --bilesen ile değiştirilir
    asgari_bilesen: int = 2
    umap_komsu: int = 15
    umap_bilesen: int = 10

    # --- FCM ---
    m: float = 1.4                 # K3: 1.3–1.6 arası, m=2 kullanılmaz
    c_araligi: tuple[int, int] = (2, 12)
    yineleme: int = 300
    tolerans: float = 1e-6
    baslangic: int = 10            # rastgele başlangıç sayısı, en iyisi seçilir
    tohum: int = 20260811          # tekrarlanabilirlik (K1/K2: sonuç deterministik)

    # --- stabilite (K3: bootstrap Jaccard) ---
    bootstrap: int = 50
    tarama_bootstrap: int = 20   # c taramasında daha ucuz stabilite
    stabilite_esigi: float = 0.60

    # --- temsilciler (K4) ---
    temsilci_sayisi: int = 5
    temsilci_ust_dilim: float = 0.80  # üst %20 üyelik

    def __post_init__(self) -> None:
        # Yol alanları dizeyle de verilebilsin (dondurulmuş sınıf, setattr gerekli).
        for alan in ("matris", "db"):
            deger = getattr(self, alan)
            if not isinstance(deger, Path):
                object.__setattr__(self, alan, Path(deger))
        if isinstance(self.c_araligi, list):
            object.__setattr__(self, "c_araligi", tuple(self.c_araligi))

    def ile(self, **degisiklikler) -> "Ayar":
        """Tek bir alanı değiştirilmiş kopya (komut satırı geçersiz kılmaları için)."""
        return replace(self, **degisiklikler)


VARSAYILAN = Ayar()
