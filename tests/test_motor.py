"""Motor (2026-10-20): RP3β, EASE (Woodbury), koşullu logit, eşli kıyas, sızıntı.

Hepsi yapay veriyle ve ağsız. Gerçek `data/` okunmaz: gömü klasörleri geçici
dizine, Deezer arama önbelleği boş bir sahteye yönlendiriliyor.
"""

import numpy as np
import pytest

import python.motor as M
from python.db import baglan


def _grafik(listeler, basliklar=None):
    conn = baglan(":memory:")
    with conn:
        for lid, uyeler in listeler.items():
            conn.execute("INSERT INTO calma_listesi (liste_id, baslik) VALUES (?,?)",
                         (lid, (basliklar or {}).get(lid, f"liste {lid}")))
            for sira, ad in enumerate(uyeler):
                conn.execute("INSERT INTO liste_parca (liste_id, sira, sanatci, sanatci_anahtar,"
                             " parca, parca_id) VALUES (?,?,?,?,?,?)",
                             (lid, sira, ad, ad.lower(), f"{ad} {sira}", lid * 100 + sira))
    return conn


def test_rp3_komsuyu_bulur_ve_beta_populerligi_cezalandirir():
    # a ile b üç listede (b her yerde), a ile c bir listede ve c yalnız orada.
    conn = _grafik({1: ["a", "b", "c"], 2: ["a", "b"], 3: ["a", "b"],
                    4: ["b", "d"], 5: ["b", "e"], 6: ["x", "y"]})
    G = M.grafik_kur(conn, baglam_agirligi=1.0)
    skor, katki, ortak = M.rp3(G, {"a": 1.0}, alfa=1.0, beta=0.0)
    s = dict(zip(G.anahtar, skor))
    assert s["b"] > s["c"] > 0 and s["x"] == 0 and s["y"] == 0
    assert ortak[0, G.sira["b"]] == 3 and ortak[0, G.sira["c"]] == 1
    # β = 1: b'nin 5 listelik popülerliği cezalanır, c öne geçer.
    skor_b, _, _ = M.rp3(G, {"a": 1.0}, alfa=1.0, beta=1.0)
    s_b = dict(zip(G.anahtar, skor_b))
    assert s_b["c"] > s_b["b"]
    # α = 0 sıfır geçişleri bağlı saymamalı (0**0 tuzağı).
    skor0, _, _ = M.rp3(G, {"a": 1.0}, alfa=0.0, beta=0.0)
    assert dict(zip(G.anahtar, skor0))["x"] == 0


def test_rp3_satir_maskesi_listeyi_cikarir():
    conn = _grafik({1: ["a", "c"], 2: ["a", "b"]})
    G = M.grafik_kur(conn, baglam_agirligi=1.0)
    skor, _, _ = M.rp3(G, {"a": 1.0}, satir=G.satir_maskesi({1}))
    assert dict(zip(G.anahtar, skor))["c"] == 0


def test_ease_woodbury_dogrudan_cozumle_ayni():
    rng = np.random.default_rng(3)
    listeler = {i: [f"s{j}" for j in range(12) if rng.random() < 0.35] or ["s0", "s1"]
                for i in range(1, 9)}
    conn = _grafik(listeler)
    G = M.grafik_kur(conn, baglam_agirligi=1.0)
    lam = 2.0
    X = G.B.astype("float64")
    P = np.linalg.inv(X.T @ X + lam * np.eye(X.shape[1]))
    Bm = np.eye(X.shape[1]) - P / np.diag(P)
    q = np.zeros(X.shape[1])
    tohum = {G.anahtar[0]: 1.0, G.anahtar[3]: 1.0}
    for a in tohum:
        q[G.sira[a]] = 1.0
    beklenen = q @ Bm
    skor = M.ease(G, tohum, lam=lam)
    tohum_disi = [j for j in range(X.shape[1]) if q[j] == 0 and X[:, j].any()]
    assert np.allclose(skor[tohum_disi], beklenen[tohum_disi], atol=1e-8)


def test_baglam_listesi():
    assert M.baglam_listesi_mi("türkçe")
    assert M.baglam_listesi_mi("Evening Chill")
    assert not M.baglam_listesi_mi("Türk Rock")
    assert not M.baglam_listesi_mi("japanese fusion")
    conn = _grafik({1: ["a", "b"], 2: ["a", "c"]}, {1: "türkçe", 2: "prog metal"})
    G = M.grafik_kur(conn, baglam_agirligi=0.5)
    assert G.w.tolist() == [0.5, 1.0]


def test_logit_bilgili_ozniteligi_ogrenir_ve_buyuk_lambda_onculdur():
    rng = np.random.default_rng(0)
    d = len(M.OZNITELIKLER)
    ornekler = []
    for _ in range(80):
        F = rng.random((30, d))
        pos = int(np.argmax(F[:, 0] * 3 + rng.normal(0, 0.3, 30)))   # rr_rp3 bilgili
        ornekler.append((F, pos))
    theta = M.logit_egit(ornekler, lam=0.1)
    assert theta[0] > 2 and abs(theta[0]) > np.abs(theta[1:]).max()
    assert np.allclose(M.logit_egit(ornekler, lam=1e9), M.oncul(), atol=1e-4)


def test_eslesmis_kiyas():
    ayni = M.eslesmis_kiyas([0.5, 0.2, 0.0], [0.5, 0.2, 0.0])
    assert ayni["fark"] == 0 and ayni["p"] == 1.0
    a = [1.0] * 30 + [0.5] * 10
    b = [0.1] * 30 + [0.5] * 10
    k = M.eslesmis_kiyas(a, b)
    assert k["fark"] > 0 and k["p"] < 0.01 and k["alt"] > 0


def test_sizinti_ve_motor_uctan_uca(tmp_path, monkeypatch):
    """Gizlenen 'h' yalnız kendi adıyla bulunmuş listede kütüphaneyle yan yana:
    düzeltmeyle o katmanda erişilemez olmalı; motor koşmalı ve ayar üretmeli."""
    import python.degerlendirme as D
    import python.etiket_clap as C
    import python.discover.calma_listesi as L

    (tmp_path / "clap").mkdir()
    (tmp_path / "clap_parca").mkdir()
    monkeypatch.setattr(C, "GOMU_KLASOR", tmp_path / "clap")
    monkeypatch.setattr(D, "GOMU_KLASOR", tmp_path / "clap")
    monkeypatch.setattr(C, "PARCA_GOMU", tmp_path / "clap_parca")
    monkeypatch.setattr(D, "PARCA_GOMU", tmp_path / "clap_parca")
    monkeypatch.setattr(L, "liste_ara", lambda istemci, ad, adet=6: [])

    conn = baglan(":memory:")
    kutuphane = ["k1", "k2", "k3", "k4", "h"]
    listeler = {
        # 'h' aramasıyla bulunan: h ↔ k1 bağı yalnız burada.
        10: ("h", ["h", "k1", "z1"]),
        11: ("h", ["h", "k1", "z2"]),
        20: ("k1", ["k1", "k2", "y1"]), 21: ("k2", ["k2", "k3", "y1"]),
        22: ("k3", ["k3", "k4", "y2"]), 23: ("k4", ["k4", "k1", "y2"]),
        24: ("k1", ["k1", "k3", "y3"]), 25: ("k2", ["k2", "k4", "y3"]),
    }
    with conn:
        for ad in kutuphane:
            conn.execute("INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)",
                         (f"alb_{ad}", ad, f"{ad} albümü"))
        for lid, (tohum, uyeler) in listeler.items():
            conn.execute("INSERT INTO calma_listesi (liste_id, baslik, tohum_sanatci) "
                         "VALUES (?,?,?)", (lid, f"liste {lid}", tohum))
            for sira, ad in enumerate(uyeler):
                conn.execute("INSERT INTO liste_parca (liste_id, sira, sanatci, "
                             "sanatci_anahtar, parca) VALUES (?,?,?,?,?)",
                             (lid, sira, ad, ad, f"{ad} {sira}"))

    assert D.sizinti_listeleri(conn)["h"] == {10, 11}
    eski = D.calistir(conn, sizinti=False, olcut="npmi", buzulme=1.0)
    yeni = D.calistir(conn, sizinti=True, olcut="npmi", buzulme=1.0, motor=True)
    h = sorted(D.kutuphane(conn)).index("h")
    assert eski["liste_birlikteligi"]["siralar"][h] is not None
    assert yeni["liste_birlikteligi"]["siralar"][h] is None, "sızan liste katmanda kalmış"
    for yol in ("rp3", "ease", "motor"):
        assert len(yeni[yol]["siralar"]) == len(kutuphane)
        assert yeni[yol]["siralar"][h] is None
    ayar = yeni["_motor_ayar"]
    assert len(ayar["theta"]) == len(M.OZNITELIKLER) and ayar["sorgu"] == len(kutuphane)
    assert "motor − melez" in ayar["kiyas"]
    assert "Motor — iç içe CV" in D.motor_raporu(yeni)


def test_uretim_motor_stratejisi_ve_gerekce(tmp_path, monkeypatch):
    """Eksen üyelikleriyle üretimdeki `adaylar.motor`: sahip olunmayan sanatçı
    önerir, parça kimliği taşır, gerekçe ortak liste sayısını söyler."""
    import python.etiket_clap as C
    from python.discover import adaylar as A
    from python.dil import AKTIF_DIL
    from python.gerekce import gerekce

    monkeypatch.setattr(C, "GOMU_KLASOR", tmp_path / "clap")
    monkeypatch.setattr(C, "PARCA_GOMU", tmp_path / "clap_parca")
    monkeypatch.setattr(M, "AYAR_DOSYASI", tmp_path / "yok.json")
    M._GRAFIK.clear()
    conn = _grafik({1: ["Meshuggah", "Vildhjarta"], 2: ["Meshuggah", "Vildhjarta"],
                    3: ["Gojira", "Vildhjarta"], 4: ["Gojira", "Car Bomb"],
                    5: ["Duman", "Sezen Aksu"]})
    cal = "c1"
    with conn:
        for i, (ad, eksen) in enumerate((("Meshuggah", 0), ("Gojira", 0), ("Duman", 1))):
            conn.execute("INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)",
                         (f"a{i}", ad, f"{ad} albümü"))
            conn.execute("INSERT INTO clusters (kume_id, calisma_id, kullanici_adi, stabil_mi)"
                         " VALUES (?,?,?,1) ON CONFLICT DO NOTHING", (eksen, cal, "metal"))
            for k in (0, 1):
                conn.execute("INSERT INTO memberships (album_id, calisma_id, kume_id, uyelik)"
                             " VALUES (?,?,?,?)", (f"a{i}", cal, k, 0.9 if k == eksen else 0.1))
    adaylar = A.motor(conn, cal, 0, adet=5)
    adlar = [a.artist for a in adaylar]
    assert adlar[0] == "Vildhjarta" and "Sezen Aksu" not in adlar
    assert not {"Meshuggah", "Gojira"} & set(adlar)
    ilk = adaylar[0]
    assert ilk.dayanak["parca_id"]
    assert tuple(ilk.dayanak["tohumlar"][0]) == ("Meshuggah", 2)
    belirtec = AKTIF_DIL.set("tr")
    try:
        metin = gerekce("motor", ilk.dayanak, eksen="metal")
    finally:
        AKTIF_DIL.reset(belirtec)
    assert "Meshuggah (2)" in metin


def test_clap_pencereleri_sabit():
    """Rastgele kesim yerine sabit 10 sn pencereler (K2: aynı klip aynı gömü)."""
    from python.etiket_clap import CLAP_ORNEKLEME as sr, pencereler

    y = np.arange(30 * sr, dtype="float32")
    p = pencereler(y)
    assert [len(x) for x in p] == [10 * sr] * 3 and p[1][0] == 10 * sr
    assert len(pencereler(y[: 25 * sr])) == 2
    assert len(pencereler(y[: 5 * sr])) == 1
