"""Web arayüzü testleri — SVG üretimi ve yönlendirmeler.

Streamlit'ten çıkarken görüntü katmanı test edilebilir hale geldi: Starlette'in
test istemcisi sunucuyu ayağa kaldırmadan istek atabiliyor. Streamlit'te bunun
karşılığı yoktu, ekranlar ancak elle açılarak denenebiliyordu.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web import grafik

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


# --------------------------------------------------------------------------- #
# SVG üretimi
# --------------------------------------------------------------------------- #

def test_xml_kacisi():
    """Sanatçı adlarında & ve < gerçekten geçiyor; kaçırılmazsa SVG bozulur."""
    cizim = grafik.yatay_cubuk([("AC/DC & <Guns>", 1.0)])
    assert "&amp;" in cizim.svg and "&lt;Guns&gt;" in cizim.svg
    assert "<Guns>" not in cizim.svg


def test_bos_veri_cokmez():
    for fn in (
        lambda: grafik.yatay_cubuk([]),
        lambda: grafik.aralik([]),
        lambda: grafik.sacilim([], x_baslik="x", y_baslik="y"),
        lambda: grafik.isi_haritasi([], [], {}),
    ):
        assert fn().svg.startswith("<svg"), "boş veride de geçerli SVG dönmeli"


def test_tek_noktali_sacilim_bolme_hatasi_vermez():
    """Tüm noktalar aynı yerdeyse (x1-x0)=0 olur — sıfıra bölme riski."""
    cizim = grafik.sacilim([(0.5, 0.5, "a", "tek")], x_baslik="x", y_baslik="y")
    assert "circle" in cizim.svg
    # Düz `"nan" in svg` YANLIŞ bir kontrol: `domiNANt-baseline` eşleşiyor.
    # Aranan şey, bir SAYI alanında NaN olması.
    import re
    assert not re.search(r'="[^"]*nan[^"]*"', cizim.svg, re.I) or \
        not re.search(r'(cx|cy|x|y|width|height)="nan"', cizim.svg, re.I), cizim.svg[:200]


def test_isi_haritasi_eksik_hucreyi_bos_birakir():
    """Ölçülmemiş küme×eksen kutusu renklendirilmemeli — sıfır sanılmasın."""
    cizim = grafik.isi_haritasi(
        ["e1", "e2"], ["k1"], {("e1", "k1"): 0.4})
    assert cizim.svg.count("<rect") == 2, "iki hücre olmalı"
    assert "opacity=\"0.35\"" in cizim.svg, "eksik hücre soluk çizilmeli"


def test_sapma_yonu_renk_degistirir():
    """İki yönlü ölçüde sıfırın iki yanı farklı renk almalı."""
    arti = grafik.isi_haritasi(["e"], ["k"], {("e", "k"): 0.5}).svg
    eksi = grafik.isi_haritasi(["e"], ["k"], {("e", "k"): -0.5}).svg
    assert grafik.PALET["ikincil"][1:] in arti
    assert grafik.PALET["vurgu"][1:] in eksi


def test_aralik_ipucu_tasir():
    cizim = grafik.aralik([("sahne", 0.2, 0.07, 0.46, "10 karardan 8'i bilinen")])
    assert "<title>10 karardan 8&#x27;i bilinen</title>" in cizim.svg


def test_kategorik_renk_dongusu():
    """12'den fazla grup varsa renkler başa döner ama çakışma sayısı azalsın."""
    assert len(grafik.KATEGORIK) >= 12


def test_nan_deger_cizilmez():
    cizim = grafik.yatay_cubuk([("a", float("nan"))])
    assert "—" in cizim.svg


# --------------------------------------------------------------------------- #
# Yönlendirmeler
# --------------------------------------------------------------------------- #

def test_tum_sayfalar_acilir():
    """Her sayfa 200 dönmeli — veritabanı boş olsa bile."""
    from starlette.testclient import TestClient

    from web.sunucu import uygulama

    istemci = TestClient(uygulama)
    for yol in ("/oneriler", "/profil", "/ogrenme", "/muzisyenler",
                "/kumeler", "/veri", "/eslestirme"):
        yanit = istemci.get(yol)
        assert yanit.status_code == 200, f"{yol} → {yanit.status_code}"


def test_kok_yonlendirir():
    from starlette.testclient import TestClient

    from web.sunucu import uygulama

    yanit = TestClient(uygulama).get("/", follow_redirects=False)
    assert yanit.status_code in (302, 307), yanit.status_code


def test_gecersiz_karar_reddedilir():
    from starlette.testclient import TestClient

    from web.sunucu import uygulama

    yanit = TestClient(uygulama).post(
        "/api/karar", json={"aday_id": "x", "karar": "sacmalik"})
    assert yanit.status_code == 400


def test_onizleme_onbellegi_atlar():
    """Kısa ömürlü imzalı URL önbellekten dönerse ÖLÜ döner.

    Gerçek hata (2026-09-02): `/api/onizleme` K5 gereği önbellekli çağrı
    yapıyordu, dolayısıyla "taze" URL aslında eskisiydi. Ölçüldü — dönen
    URL'nin imzası 1.053 saniye önce dolmuştu, ses dosyası 403 veriyordu.
    Deezer imzası 900 saniye yaşıyor; önbellek 15 dakikadan sonra her zaman
    ölü URL verir.

    Bu test uçtan `yenile=True` geçtiğini korur. Sessizce geri gelirse
    uygulamanın çekirdek eylemi ("dinle ve karar ver") çalışmaz.
    """
    from starlette.testclient import TestClient

    import python.discover.calma_listesi as CL
    from web.sunucu import uygulama

    cagrilar = []

    class SahteIstemci:
        def get_json(self, yol, params=None, *, yenile=False):
            cagrilar.append((yol, yenile))
            return {"preview": "https://ornek/taze.mp3"}

    eski = CL.deezer_listesi
    CL.deezer_listesi = lambda **k: SahteIstemci()
    try:
        yanit = TestClient(uygulama).get("/api/onizleme/123")
    finally:
        CL.deezer_listesi = eski

    assert yanit.status_code == 200, yanit.status_code
    assert yanit.json()["url"] == "https://ornek/taze.mp3"
    assert cagrilar == [("track/123", True)], (
        f"önbellek atlanmadı: {cagrilar}")


def test_hepsi_nis_stratejileri_almaz():
    """«Ana yolların hepsi» seçiliyken kadro grafiği stratejileri girmez.

    Ölçüldü (2026-09-02): kredi_sicramasi, sahne_komsulugu ve bilincli_uzaklik
    147 gizlemenin TAMAMINDA 55–81 tekil sanatçı görebiliyor ve 1'ini
    bulabiliyor. Ana listede yer kaplamaları kullanıcının işini zorlaştırır.
    Silinmiyorlar (ölçüt onların işini tam ölçmüyor) ama açıkça seçilmeleri
    gerekiyor. Bu ayrım sessizce geri gelirse ana liste yine kalabalıklaşır.
    """
    from web.sunucu import ANA_STRATEJILER, NIS_STRATEJILER

    assert not set(ANA_STRATEJILER) & set(NIS_STRATEJILER)
    assert "melez" in ANA_STRATEJILER
    for st in ("kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik"):
        assert st in NIS_STRATEJILER, st


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
