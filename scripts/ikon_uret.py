"""Neon ikonu üret — macOS uygulaması ve PWA için (2026-09-23).

Eski ikon (turuncu kulaklık) v2 temasındandı. Neon kimliği: gece mavisi zemin,
başlıktaki ◈ işareti macenta→turuncu geçişle, camgöbeği HUD köşeleri —
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
ZEMIN = (5, 6, 12)
MACENTA = (255, 43, 214)
TURUNCU = (255, 122, 69)
CAMGOBEGI = (34, 236, 255)
OLCEK = 4          # süper örnekleme: 4 kat büyük çiz, küçült — kenarlar pürüzsüz


def _gecis(boyut: int) -> Image.Image:
    """Sol üstten sağ alta macenta → turuncu."""
    g = Image.new("RGB", (boyut, boyut))
    px = g.load()
    for y in range(boyut):
        for x in range(boyut):
            t = (x + y) / (2 * (boyut - 1))
            px[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(MACENTA, TURUNCU))
    return g


def _elmas(ciz: ImageDraw.ImageDraw, m: float, r: float, kalinlik: float | None = None,
           dolgu=255) -> None:
    nokta = [(m, m - r), (m + r, m), (m, m + r), (m - r, m)]
    if kalinlik is None:
        ciz.polygon(nokta, fill=dolgu)
    else:
        ciz.line(nokta + [nokta[0]], fill=dolgu, width=int(kalinlik), joint="curve")


def ikon(boyut: int = 1024, *, mac: bool = False) -> Image.Image:
    S = boyut * OLCEK
    tuval = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # macOS Big Sur ızgarası: 1024'lük tuvalde ~824'lük yuvarlatılmış kare.
    pay = int(S * 0.098) if mac else 0
    yaricap = int(S * 0.18) if mac else 0
    govde = (pay, pay, S - pay, S - pay)
    maske = Image.new("L", (S, S), 0)
    ImageDraw.Draw(maske).rounded_rectangle(govde, radius=yaricap, fill=255)

    zemin = Image.new("RGBA", (S, S), ZEMIN + (255,))
    # İki ışık lekesi (stil.css `--zemin-desen` ile aynı yerleşim).
    isik = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ci = ImageDraw.Draw(isik)
    ci.ellipse((int(S * .45), int(-S * .25), int(S * 1.25), int(S * .55)), fill=MACENTA + (70,))
    ci.ellipse((int(-S * .35), int(S * .55), int(S * .45), int(S * 1.3)), fill=CAMGOBEGI + (48,))
    isik = isik.filter(ImageFilter.GaussianBlur(S * .12))
    zemin = Image.alpha_composite(zemin, isik)
    # 44 px ızgaranın ikon ölçeğindeki karşılığı: seyrek, çok soluk.
    iz = ImageDraw.Draw(zemin)
    adim = S // 10
    for i in range(adim, S, adim):
        iz.line((i, 0, i, S), fill=CAMGOBEGI + (8,), width=OLCEK)
        iz.line((0, i, S, i), fill=CAMGOBEGI + (8,), width=OLCEK)

    m = S / 2
    r_dis = S * (0.30 if mac else 0.33)
    # ◈: dış elmas çerçeve + iç dolu elmas, ikisi de geçişle boyanıyor.
    # Çerçeve çizgiyle değil İKİ DOLU ELMASIN FARKIYLA: çizgi birleşimi tepe
    # köşesinde çentik bırakıyordu (ilk sürümde görüldü).
    kal = S * 0.045
    dis, ici = Image.new("L", (S, S), 0), Image.new("L", (S, S), 0)
    _elmas(ImageDraw.Draw(dis), m, r_dis + kal / 2)
    _elmas(ImageDraw.Draw(ici), m, r_dis - kal / 2 * 1.414)
    sekil = ImageChops.subtract(dis, ici)
    _elmas(ImageDraw.Draw(sekil), m, r_dis * 0.46)
    renk = _gecis(S).convert("RGBA")
    # Neon parıltısı: şeklin bulanık kopyası macenta olarak arkaya.
    parilti = Image.new("RGBA", (S, S), MACENTA + (0,))
    parilti.putalpha(sekil.filter(ImageFilter.GaussianBlur(S * 0.035)).point(lambda v: int(v * .85)))
    zemin = Image.alpha_composite(zemin, parilti)
    renkli = renk.copy()
    renkli.putalpha(sekil)
    zemin = Image.alpha_composite(zemin, renkli)

    # HUD köşeleri (sol üst, sağ alt) — camgöbeği, hafif parıltılı.
    hud = Image.new("L", (S, S), 0)
    ch = ImageDraw.Draw(hud)
    ic = pay + int(S * 0.085)
    boy, kal = int(S * 0.13), int(S * 0.022)
    ch.line((ic, ic + boy, ic, ic, ic + boy, ic), fill=255, width=kal, joint="curve")
    d = S - ic
    ch.line((d, d - boy, d, d, d - boy, d), fill=255, width=kal, joint="curve")
    hud_parilti = Image.new("RGBA", (S, S), CAMGOBEGI + (0,))
    hud_parilti.putalpha(hud.filter(ImageFilter.GaussianBlur(S * 0.012)))
    zemin = Image.alpha_composite(zemin, hud_parilti)
    hud_renk = Image.new("RGBA", (S, S), CAMGOBEGI + (0,))
    hud_renk.putalpha(hud)
    zemin = Image.alpha_composite(zemin, hud_renk)

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
