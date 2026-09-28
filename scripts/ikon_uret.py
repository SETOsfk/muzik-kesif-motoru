"""İKİ AY ikonu üret — macOS uygulaması ve PWA için (2026-09-28).

Tema değişti (Neon → Çizim → İKİ AY), ikon Neon'da kalmıştı. Yeni kimlik:
gece mavisi zemin, büyük sarı ay, sağ üstte küçük adaçayı ay, duvarda ayın
önünde oturan bir kedi — `web/statik/cizim/iki-ay.svg` ile aynı sahne ve
`web/statik/stil.css` tokenlarıyla aynı renkler.

Çıktılar:
  web/statik/ikon-{180,192,512}.png   PWA / iOS (tam dolu kare; işletim sistemi maskeler)
  data/ikon/ikon-1024-mac.png         macOS (Big Sur ızgarası: yuvarlatılmış kare, kenar payı)

Kullanım: .venv/bin/python scripts/ikon_uret.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

KOK = Path(__file__).resolve().parents[1]
GECE = (39, 48, 90)          # --gece
DUVAR = (28, 35, 69)
AY = (229, 182, 74)          # --ay
AY_2 = (169, 191, 174)       # --ay-2
KEDI = (20, 24, 46)
OLCEK = 4          # süper örnekleme: 4 kat büyük çiz, küçült — kenarlar pürüzsüz


def ikon(boyut: int = 1024, *, mac: bool = False) -> Image.Image:
    S = boyut * OLCEK

    # macOS Big Sur ızgarası: 1024'lük tuvalde ~824'lük yuvarlatılmış kare.
    pay = int(S * 0.098) if mac else 0
    yaricap = int(S * 0.18) if mac else 0
    govde = (pay, pay, S - pay, S - pay)
    maske = Image.new("L", (S, S), 0)
    ImageDraw.Draw(maske).rounded_rectangle(govde, radius=yaricap, fill=255)

    # Maskelenebilir ikon: sahne ortadaki %80'lik güvenli dairenin içinde.
    zemin = Image.new("RGBA", (S, S), GECE + (255,))
    c = ImageDraw.Draw(zemin)
    def daire(x, y, r, renk):
        c.ellipse((S * (x - r), S * (y - r), S * (x + r), S * (y + r)), fill=renk)
    daire(.50, .47, .25, AY)
    daire(.76, .25, .06, AY_2)
    c.rectangle((0, S * .69, S, S), fill=DUVAR)
    # Kedi: ayın önünde, duvarda oturuyor.
    c.ellipse((S * .435, S * .54, S * .565, S * .72), fill=KEDI)
    daire(.50, .50, .055, KEDI)
    c.polygon([(S * .455, S * .48), (S * .46, S * .405), (S * .495, S * .46)], fill=KEDI)
    c.polygon([(S * .545, S * .48), (S * .54, S * .405), (S * .505, S * .46)], fill=KEDI)
    c.arc((S * .52, S * .60, S * .64, S * .72), start=270, end=90, fill=KEDI, width=int(S * .018))

    if mac:
        # Hafif iç kenar ışığı — Big Sur ikonlarının derinlik hissi.
        kenar = Image.new("L", (S, S), 0)
        ImageDraw.Draw(kenar).rounded_rectangle(govde, radius=yaricap, outline=255, width=OLCEK * 3)
        isik_kenar = Image.new("RGBA", (S, S), (255, 255, 255, 0))
        isik_kenar.putalpha(kenar.point(lambda v: int(v * .10)))
        zemin = Image.alpha_composite(zemin, isik_kenar)
        zemin.putalpha(ImageChops.multiply(zemin.getchannel("A"), maske))
        # Gölge: kare tuvalin altında yumuşak.
        golge = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        golge.putalpha(maske.filter(ImageFilter.GaussianBlur(S * .02)).point(lambda v: int(v * .45)))
        golge = golge.transform((S, S), Image.AFFINE, (1, 0, 0, 0, 1, -int(S * .012)))
        zemin = Image.alpha_composite(golge, zemin)

    return zemin.resize((boyut, boyut), Image.LANCZOS)


def main() -> int:
    statik = KOK / "web" / "statik"
    for b in (180, 192, 512):
        ikon(b).convert("RGB").save(statik / f"ikon-{b}.png", optimize=True)
    hedef = KOK / "data" / "ikon"
    hedef.mkdir(parents=True, exist_ok=True)
    ikon(1024, mac=True).save(hedef / "ikon-1024-mac.png", optimize=True)
    print(f"PWA ikonları: {statik}  ·  macOS: {hedef / 'ikon-1024-mac.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
