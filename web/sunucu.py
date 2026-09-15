"""Web arayüzü — Starlette + Jinja2, sunucuda çizilen sayfalar.

## Streamlit neden bırakıldı

Biçimsel bir tercih değildi. Üç somut sorun:

1. **Her etkileşim tüm betiği yeniden çalıştırıyor.** Bir aday için 👍'ye
   basınca sayfa baştan kuruluyor ve çalan 30 saniyelik önizleme sıfırlanıyor —
   oysa bu uygulamanın çekirdek eylemi "dinle ve karar ver".
2. **Durum URL'de yok.** Bir eksene ya da müzisyene bağlantı verilemiyor,
   tarayıcı geri tuşu çalışmıyor, sekme yenilenince seçim kayboluyor.
3. **Görünüm denetlenemiyor.** Bileşen aralıkları, tablo başlıkları ve grafik
   tipografisi ancak CSS'i geri döndürerek düzeltilebiliyordu; `app/tema.py`
   giderek Streamlit'e karşı yazılmış bir yama listesine dönüşüyordu.

Buradaki karşılık: sunucuda çizilen HTML, URL'de duran durum, elle yazılmış
CSS ve SVG. Yeni bağımlılık YOK — starlette, jinja2 ve uvicorn zaten kuruluydu
(Streamlit'in kendi bağımlılıkları). K8 (tek dil) ve K2 (0 TL) korunuyor.

**Hesap katmanı hiç değişmedi.** `python/` altındaki modüller zaten DataFrame
döndüren saf fonksiyonlardı; Streamlit yalnızca görüntü katmanıydı. Bu dosya
onların yerine geçmiyor, önlerine yeni bir görüntü koyuyor.

Çalıştırma:
    .venv/bin/python -m web.sunucu
    .venv/bin/python -m web.sunucu --port 8800 --db data/db/kesif.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

import pandas as pd
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from python.db import baglan, baglan_kullanici, baglan_ortak
from python.hesap import (
    CEREZ_ADI,
    OTURUM_GUN,
    giris_dogrula,
    kullanici_bul,
    kullanici_olustur,
    kullanici_sayisi,
    oturum_ac,
    oturum_coz,
    oturum_kapat,
)

KOK = Path(__file__).resolve().parent
# Starlette 1.3 imzası: TemplateResponse(request, ad, bağlam). Eski
# (ad, bağlam) çağrısı sessizce şablon adı yerine sözlük alıp
# "cannot use 'tuple' as a dict key" gibi anlaşılmaz bir hatayla düşüyor.
SABLONLAR = Jinja2Templates(directory=str(KOK / "sablonlar"))

#: Modül düzeyinde tutuluyor: Starlette'te uygulama nesnesi bir kez kurulup
#: birçok istek görüyor, her istekte argüman taşımak gereksiz.
DB_YOLU = "data/db/kesif.sqlite"

#: İSTEK BAŞINA AKTİF KULLANICI. `_baglanti()` on ayrı yerden ARGÜMANSIZ
#: çağrılıyor; imzasını değiştirmek her çağrı yerine istek nesnesi taşımak
#: demekti. Bağlam değişkeni bunu çözüyor ve Starlette'in görev bağlamında
#: doğru çalışıyor: her istek kendi kopyasını görür, eşzamanlı istekler
#: birbirinin kullanıcısını okuyamaz.
AKTIF_KULLANICI: ContextVar[int | None] = ContextVar("aktif_kullanici",
                                                    default=None)

#: Oturum gerektirmeyen yollar. Geri kalan her şey girişe yönlendirilir.
ACIK_YOLLAR = ("/giris", "/uyelik", "/cikis", "/statik", "/saglik", "/sw.js")

#: Spotify Development Mode uygulaması en fazla beş yetkili hesap taşıyor
#: (Şubat 2026). Panele eklenmeyen hesap Spotify tarafında zaten giriş
#: yapamaz; sınırı burada da uygulamak anlaşılır bir mesaj vermeyi sağlıyor.
AZAMI_KULLANICI = 5


def _baglanti() -> sqlite3.Connection:
    """İstek başına yeni bağlantı — AKTİF KULLANICININ veritabanı.

    SQLite bağlantıları iş parçacıkları arasında paylaşılmaz; Starlette
    eşzamanlı istek görebildiği için tek bir küresel bağlantı yanlış olurdu.
    Açılış maliyeti mikrosaniyeler.

    Kullanıcı bağlam değişkeninden geliyor (ara katman yerleştiriyor). Böyle
    olması, bu işlevi çağıran on ayrı yerin hiç değişmemesini sağlıyor:
    `albums` aktif kullanıcının dosyasından, `liste_parca` ortaktan gelir —
    ayrımı SQLite'ın ad çözümlemesi yapar (bkz. python/db.py).
    """
    kullanici_id = AKTIF_KULLANICI.get()
    if kullanici_id is None:
        # Oturum yokken de bazı sayfalar (giriş ekranı) şablon bağlamı için
        # bağlantı isteyebilir; ortak veritabanı yeterli ve kütüphane boştur.
        return baglan_ortak()
    return baglan_kullanici(kullanici_id)


def _oturum_baglantisi() -> sqlite3.Connection:
    """Kimlik doğrulama için ortak veritabanı — kullanıcı henüz bilinmiyor."""
    return baglan_ortak()


# --------------------------------------------------------------------------- #
# Ortak veri
# --------------------------------------------------------------------------- #

# ÖNBELLEK ANAHTARINA KULLANICI GİRMEK ZORUNDA (2026-09-15).
# Bu işlevler kullanıcıya ÖZEL veri okuyor. Çok kiracılıktan önce tek
# kullanıcı vardı ve anahtarsız `lru_cache` doğruydu; şimdi aynı kod A
# kullanıcısının küme adlarını ve sayaçlarını B'ye servis eder. Ölçüldü:
# sunucu ilk isteği oturumsuz karşılayınca boş sonuç önbelleğe giriyor ve
# ondan sonra HERKES "hiç kümeleme çalışması yok" görüyor.
#
# Çözüm, çağrı yerlerini değiştirmeden sarmalamak: önbellekli iç işlev
# kullanıcıyı parametre olarak alır, dış kabuk bağlam değişkeninden okur.

@lru_cache(maxsize=32)
def _calismalar_onbellek(kullanici_id: int | None) -> tuple[dict, ...]:
    conn = _baglanti()
    try:
        return tuple(
            dict(r) for r in conn.execute(
                """
                SELECT calisma_id, COUNT(*) kume, SUM(stabil_mi) stabil,
                       ROUND(AVG(stabilite), 3) ort
                  FROM clusters GROUP BY calisma_id ORDER BY calisma_id DESC
                """
            )
        )
    finally:
        conn.close()


def _calismalar() -> list[dict]:
    return list(_calismalar_onbellek(AKTIF_KULLANICI.get()))


def _son_calisma() -> str | None:
    calismalar = _calismalar()
    return calismalar[0]["calisma_id"] if calismalar else None


@lru_cache(maxsize=64)
def _eksen_adlari_onbellek(kullanici_id: int | None,
                           calisma_id: str) -> dict[int, str]:
    conn = _baglanti()
    try:
        return {
            int(r["kume_id"]): (r["kullanici_adi"] or f"Küme {r['kume_id']}")
            for r in conn.execute(
                "SELECT kume_id, kullanici_adi FROM clusters WHERE calisma_id = ?",
                (calisma_id,),
            )
        }
    finally:
        conn.close()


def _eksen_adlari(calisma_id: str) -> dict[int, str]:
    return _eksen_adlari_onbellek(AKTIF_KULLANICI.get(), calisma_id)


@lru_cache(maxsize=32)
def _boru_hatti_onbellek(kullanici_id: int | None) -> tuple[dict, ...]:
    """Üst şeritteki sayaçlar — hangi aşama beslenmiş."""
    conn = _baglanti()
    try:
        def say(sorgu: str) -> int:
            try:
                return int(conn.execute(sorgu).fetchone()[0])
            except sqlite3.Error:
                return 0

        return (
            {"ad": "albüm", "deger": say("SELECT COUNT(*) FROM albums"),
             "alt": "kütüphanende"},
            {"ad": "müzisyen", "deger": say(
                "SELECT COUNT(DISTINCT person_name) FROM credits"),
             "alt": "kredi grafiğinde"},
            {"ad": "ses ölçümü", "deger": say(
                "SELECT COUNT(DISTINCT album_id) FROM stem_profili WHERE tur='album'"),
             "alt": "ayrılmış stem"},
            {"ad": "aday", "deger": say(
                "SELECT COUNT(DISTINCT aday_id) FROM adaylar"), "alt": "üretilmiş öneri"},
            {"ad": "kararın", "deger": say("SELECT COUNT(*) FROM feedback"),
             "alt": "geri bildirim"},
        )
    finally:
        conn.close()


def _boru_hatti() -> list[dict]:
    return list(_boru_hatti_onbellek(AKTIF_KULLANICI.get()))


def _ortam(istek, **fazladan) -> dict:
    """Her şablona giden ortak bağlam."""
    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    ortam = {
        "request": istek,
        "calismalar": _calismalar(),
        "calisma_id": calisma_id,
        "eksen_adlari": _eksen_adlari(calisma_id) if calisma_id else {},
        "boru": _boru_hatti(),
        "yol": istek.url.path,
    }
    ortam.update(fazladan)
    return ortam


def _sayi(deger, basamak: int = 2) -> str:
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        return "—"
    return f"{deger:.{basamak}f}"


# --------------------------------------------------------------------------- #
# Sayfalar
# --------------------------------------------------------------------------- #

async def anasayfa(istek):
    """Giriş yapılmışsa önerilere, yapılmamışsa ara katman girişe yollar."""
    return RedirectResponse("/oneriler")


#: Ana akıştaki yollar — leave-one-artist-out ile ölçüldü ve tuttular.
ANA_STRATEJILER = ("melez", "liste_birlikteligi", "ses_benzerligi")

#: Niş yollar: kredi/kalabalık grafiği. Ölçümde erişimleri çok dar çıktı
#: (147 gizlemenin tamamında 55–81 tekil sanatçı, 1 isabet) ama ölçüt onların
#: işini ölçmüyor — "müzisyen paylaşan başka kayıt" tanım gereği sahip
#: OLMADIĞIN şey. Bu yüzden silinmiyor, ana akıştan çıkarılıyor.
NIS_STRATEJILER = ("kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik")


async def oneriler(istek):
    from python.discover.ses_uzakligi import (
        eksen_uzakliklari, kutuphane_uzaklik_dagilimi,
    )
    from python.geri_bildirim import (
        ETKI_TAVANI, bilinen_sanatcilar, yakinlik_etkisi,
    )
    from python.metin import normalize_esleme

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    if not calisma_id:
        return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(istek, mesaj=(
            "Hiç kümeleme çalışması yok. Önce <code>python -m python.enrich.matris_kur"
            "</code> ve <code>python -m python.kumeleme.calistir</code>.")))

    conn = _baglanti()
    try:
        adaylar = pd.read_sql_query(
            "SELECT * FROM adaylar WHERE calisma_id = ?", conn, params=(calisma_id,)
        )
        kararlar = {
            r[0]: r[1] for r in conn.execute(
                "SELECT aday_id, karar FROM feedback WHERE calisma_id = ?",
                (calisma_id,),
            )
        }
        bilinenler = bilinen_sanatcilar(conn)
        # Etiketler kartta gösterilecek: bağlam (çalma listesi başlıklarından,
        # "dinleyici tipi") ve ölçüm (adayın kendi stem'lerinden).
        try:
            from python.etiket import (
                ACIKLAMALAR, aday_olcum_etiketleri, sanatci_baglami,
            )
            baglam = sanatci_baglami(conn)
            olcum_et = aday_olcum_etiketleri(conn)
            etiket_aciklama = ACIKLAMALAR
        except Exception:
            baglam, olcum_et, etiket_aciklama = {}, {}, {}

        if adaylar.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj="Henüz aday yok. "
                "<code>python -m python.discover.adaylar --tum-eksenler</code>"))

        eksenler = sorted(adaylar["eksen"].unique())
        secili = int(istek.query_params.get("eksen", eksenler[0]))
        stratejiler = sorted(adaylar["strateji"].unique())
        ana = [st for st in stratejiler if st in ANA_STRATEJILER]
        nis = [st for st in stratejiler if st in NIS_STRATEJILER]
        # VARSAYILAN «melez»: ölçülmüş en iyi tek liste (leave-one-artist-out,
        # 2026-09-02 — tavan 123/147, tek başına çalma listesi 109'du).
        # Kullanıcı sayfayı açtığında karar vermek zorunda kalmadan en iyi
        # sonucu görsün; diğerleri "nereden" menüsünde duruyor.
        #
        # "hepsi" seçildiğinde NİŞ stratejiler girmiyor: ölçümde üçü birlikte
        # 147 gizlemenin tamamında 55–81 sanatçı görebildi ve 1'ini bulabildi.
        # Ana listede yer kaplamaları kullanıcının işini zorlaştırırdı; ama
        # ölçüt onların işini (kadro bağı) tam ölçmediği için silinmiyorlar,
        # menüden açıkça seçilebiliyorlar.
        secili_strateji = istek.query_params.getlist("strateji") or (
            ["melez"] if "melez" in stratejiler else ana or stratejiler)
        sirala = istek.query_params.get("sirala", "skor")
        gizle = istek.query_params.get("gizle", "1") == "1"
        geri_at = istek.query_params.get("bilinen", "1") == "1"

        gorunum = adaylar[
            (adaylar.eksen == secili) & (adaylar.strateji.isin(secili_strateji))
        ].copy()
        if gizle:
            gorunum = gorunum[~gorunum.aday_id.isin(kararlar)]

        # Ses uzaklığı + kütüphanenin kendi dağılımı (kıyas tabanı olmadan
        # "1.24 uzak mı?" sorusunun cevabı yok).
        taban = None
        try:
            uzakliklar = eksen_uzakliklari(conn, calisma_id, secili)
            if not uzakliklar.empty:
                gorunum = gorunum.merge(
                    uzakliklar[["aday_id", "ses_uzakligi"]], on="aday_id", how="left"
                )
            dagilim = kutuphane_uzaklik_dagilimi(conn, calisma_id, secili)
            if not dagilim.empty:
                uyelik = pd.read_sql_query(
                    "SELECT album_id, kume_id, uyelik FROM memberships "
                    "WHERE calisma_id = ?", conn, params=(calisma_id,),
                )
                U = uyelik.pivot(index="album_id", columns="kume_id",
                                 values="uyelik").fillna(0.0)
                keskin = U.idxmax(axis=1)
                ic = dagilim[dagilim.index.map(keskin) == secili]
                dis = dagilim[dagilim.index.map(keskin) != secili]
                if len(ic) >= 3 and len(dis) >= 3:
                    taban = {"ic": float(ic.median()), "dis": float(dis.median())}
        except Exception:
            pass
        if "ses_uzakligi" not in gorunum.columns:
            gorunum["ses_uzakligi"] = float("nan")

        gorunum["bilinen"] = gorunum["artist"].map(
            lambda a: normalize_esleme(str(a)) in bilinenler
        )
        if sirala == "uzaklik":
            gorunum = gorunum.sort_values(
                "ses_uzakligi", ascending=False, na_position="last")
        else:
            gorunum = gorunum.sort_values("skor", ascending=False)
        if geri_at:
            gorunum = gorunum.sort_values("bilinen", kind="stable")

        # SANATÇI DÜZEYİNDE GRUPLAMA.
        #
        # Ölçüldü: aday listesinde sanatçı başına ~2,2 albüm var ve sıralama
        # skora göre olduğu için aynı sanatçının albümleri arka arkaya
        # geliyordu — bir eksende ilk ON sıra ÜÇ sanatçıdan ibaretti
        # (RATM ×4, NIN ×4, Nirvana ×2). Kullanıcı on kart kaydırıp üç fikir
        # görüyordu.
        #
        # Gerekçe zaten sanatçı düzeyinde ("bunu dinleyenler şunu da dinliyor");
        # albüm düzeyinde tekrarlamak bilgi eklemiyordu. Artık bir sanatçı =
        # bir kart, albümleri kartın içinde.
        gruplar = []
        for (sanatci, strateji), grup in gorunum.groupby(
            ["artist", "strateji"], sort=False
        ):
            grup = grup.sort_values("year", na_position="last")
            albumler = []
            for _, aday in grup.iterrows():
                uz = aday.get("ses_uzakligi")
                albumler.append({
                    "aday_id": aday["aday_id"], "title": aday["title"],
                    "year": int(aday["year"]) if pd.notna(aday["year"]) else None,
                    "onizleme": aday["onizleme_url"] if pd.notna(aday["onizleme_url"]) else None,
                    # Parça adayında SAKLANMIŞ URL kullanılmaz: Deezer kısa
                    # ömürlü imzalıyor. Kimlik varsa "dinle" düğmesi taze URL
                    # çeker (`/api/onizleme/{parca_id}`).
                    "parca_id": int(aday["parca_id"]) if pd.notna(
                        aday.get("parca_id")) else None,
                    "parca": aday.get("onizleme_parca") if pd.notna(
                        aday.get("onizleme_parca")) else None,
                    "uzaklik": float(uz) if pd.notna(uz) else None,
                    "karar": kararlar.get(aday["aday_id"]),
                    "dayanak": _dayanak_metni(aday["dayanak"]),
                })

            ilk = grup.iloc[0]
            uzakliklar = [a["uzaklik"] for a in albumler if a["uzaklik"] is not None]
            ortalama_uz = sum(uzakliklar) / len(uzakliklar) if uzakliklar else None
            nitel = renk = None
            if ortalama_uz is not None and taban:
                if ortalama_uz > taban["dis"]:
                    nitel, renk = "gerçekten uzak", "mor"
                elif ortalama_uz < taban["ic"]:
                    nitel, renk = "eksenin içinde", "turuncu"
                else:
                    nitel, renk = "tanıdık ama farklı", "mavi"

            gruplar.append({
                "sanatci": sanatci, "strateji": strateji,
                "skor": float(grup["skor"].max()),
                "gerekce": ilk["gerekce"],
                "albumler": albumler,
                "aday_kimlikleri": [a["aday_id"] for a in albumler],
                "kararlar": {a["karar"] for a in albumler if a["karar"]},
                "uzaklik": ortalama_uz, "uzaklik_nitel": nitel, "uzaklik_renk": renk,
                "bilinen": bool(ilk["bilinen"]),
                # Aday albüm de olabilir parça da: çalma listesi stratejisi
                # PARÇA öneriyor ve önizlemesi hazır geliyor.
                "birim": (ilk.get("birim") or "album"),
                "baglam": baglam.get(normalize_esleme(str(sanatci)), []),
                "olcum_etiket": sorted({
                    e for a in albumler
                    for e in olcum_et.get(a["aday_id"], ())
                })[:4],
                "kapak": ilk.get("kapak") if pd.notna(ilk.get("kapak")) else None,
                # İcra eşleşmesi sanatçı düzeyinde bir kez: aynı sanatçının dört
                # albümü için dört kez hesaplamak hem yavaş hem gereksiz.
                "icra": _icra_eslesmesi_onbellek(albumler[0]["aday_id"],
                                             AKTIF_KULLANICI.get()),
            })

        # GERİ BİLDİRİM DÖNGÜSÜ. Kararlar artık yalnız kaydedilmiyor,
        # sıralamayı da kaydırıyor: beğendiğine benzeyen yukarı, tutmadığına
        # benzeyen aşağı. Etki, gösterilen skorların KENDİ standart sapması
        # cinsinden sınırlı (ETKI_TAVANI = 0,5 σ) — ham skor ölçeği stratejiye
        # göre değiştiği için mutlak bir sayı eklemek anlamsız olurdu.
        #
        # Tavan bilerek düşük: n=2 beğendim, n=3 tutmadı. Kararlar sıralamayı
        # DEVİRMİYOR, kaydırıyor. Ölçülebilir hâle gelince süpürülecek (K19).
        etki = yakinlik_etkisi(conn, calisma_id)
        if etki:
            skorlar = [g["skor"] for g in gruplar]
            ortalama = sum(skorlar) / len(skorlar) if skorlar else 0.0
            sigma = (
                (sum((x - ortalama) ** 2 for x in skorlar) / len(skorlar)) ** 0.5
                if len(skorlar) > 1 else 0.0
            )
            for g in gruplar:
                pay, gerekce = etki.get(normalize_esleme(g["sanatci"]), (0.0, ""))
                g["geri_bildirim"] = gerekce if pay else ""
                g["geri_bildirim_yon"] = "arti" if pay > 0 else "eksi"
                g["skor_ayarli"] = g["skor"] + ETKI_TAVANI * pay * sigma
        else:
            for g in gruplar:
                g["geri_bildirim"] = ""
                g["skor_ayarli"] = g["skor"]

        if sirala == "uzaklik":
            gruplar.sort(key=lambda g: (g["uzaklik"] is None,
                                        -(g["uzaklik"] or 0)))
        else:
            gruplar.sort(key=lambda g: -g["skor_ayarli"])
        if geri_at:
            gruplar.sort(key=lambda g: g["bilinen"])
        gruplar = gruplar[:30]

        return SABLONLAR.TemplateResponse(istek, "oneriler.html", _ortam(
            istek, gruplar=gruplar, eksenler=eksenler, secili=secili,
            stratejiler=stratejiler, secili_strateji=list(secili_strateji),
            ana_stratejiler=ana, nis_stratejiler=nis,
            nis_secili=[st for st in secili_strateji if st in NIS_STRATEJILER],
            sirala=sirala, gizle=gizle, geri_at=geri_at, taban=taban,
            toplam=len(gorunum), sanatci_sayisi=len(gruplar),
            etiket_aciklama=etiket_aciklama,
            bilinenler=sorted(bilinenler)[:5],
            geri_bildirim_etkin=bool(etki),
        ))
    finally:
        conn.close()


def _dayanak_metni(ham) -> str:
    try:
        return json.dumps(json.loads(ham or "{}"), ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(ham or "")


@lru_cache(maxsize=512)
def _icra_eslesmesi_onbellek(aday_id: str, kullanici_id: int | None = None) -> tuple:
    """Adayın stem'ine en yakın kütüphane icracıları, rol rol.

    Önbellekli: dört rol × kosinüs hesabı, kırk kartlık bir sayfada dört yüz
    hesap eder. Sonuç yalnız veritabanı değişince değişiyor.
    """
    from python.muzisyen import adaya_benzeyen_icracilar

    conn = _baglanti()
    try:
        sonuc = []
        for rol in ("drums", "bass", "guitar", "vocals"):
            tablo, _ = adaya_benzeyen_icracilar(conn, aday_id, rol, adet=3)
            if not tablo.empty:
                sonuc.append((rol, tuple(
                    (str(s["kisi_adi"]), float(s["benzerlik"]))
                    for _, s in tablo.iterrows()
                )))
        return tuple(sonuc)
    except Exception:
        return ()
    finally:
        conn.close()


def _icra_eslesmesi(conn, aday_id: str):
    return _icra_eslesmesi_onbellek(aday_id)


async def karar_ver(istek):
    """Geri bildirim — sayfa yenilenmeden, sanatçının tüm albümlerine.

    Kart sanatçı düzeyinde olduğu için karar da öyle: bir grubu "zaten
    biliyorum" demek, o gruptan listelenen dört albümü de bilmek demektir.
    Veritabanında yine albüm başına satır duruyor — şema değişmedi, yalnız
    tek istekte hepsi yazılıyor.
    """
    veri = await istek.json()
    karar = veri.get("karar")
    kimlikler = veri.get("aday_kimlikleri") or (
        [veri["aday_id"]] if veri.get("aday_id") else []
    )
    calisma_id = veri.get("calisma_id") or _son_calisma()
    if not kimlikler or karar not in ("begendim", "tutmadi", "zaten_biliyorum"):
        return JSONResponse({"hata": "geçersiz karar"}, status_code=400)

    conn = _baglanti()
    try:
        # Aynı karara ikinci kez basmak GERİ ALIR. Grupta karar karışıksa
        # (bazısı işaretli bazısı değil) geri alma değil, hepsini işaretleme
        # doğru olan — kullanıcı grubu bütün olarak görüyor.
        mevcut = {
            r[0] for r in conn.execute(
                f"SELECT karar FROM feedback WHERE calisma_id = ? AND aday_id IN "
                f"({','.join('?' * len(kimlikler))})",
                (calisma_id, *kimlikler),
            )
        }
        geri_al = mevcut == {karar}
        with conn:
            if geri_al:
                conn.execute(
                    f"DELETE FROM feedback WHERE calisma_id = ? AND aday_id IN "
                    f"({','.join('?' * len(kimlikler))})",
                    (calisma_id, *kimlikler),
                )
            else:
                for aday_id in kimlikler:
                    eksen = conn.execute(
                        "SELECT eksen FROM adaylar WHERE aday_id = ? "
                        "AND calisma_id = ? LIMIT 1", (aday_id, calisma_id),
                    ).fetchone()
                    conn.execute(
                        "INSERT OR REPLACE INTO feedback "
                        "(aday_id, calisma_id, eksen, karar, tarih) "
                        "VALUES (?,?,?,?,date('now'))",
                        (aday_id, calisma_id, eksen[0] if eksen else 0, karar),
                    )
    finally:
        conn.close()
    _boru_hatti.cache_clear()
    return JSONResponse(
        {"karar": None if geri_al else karar, "adet": len(kimlikler)}
    )


async def profil(istek):
    from python.profil import (
        cesitlilik, eksen_ozeti, enstruman_dengesi, kume_ses_imzasi,
        profil_cumleleri, stem_verisi,
    )
    from web import grafik

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    conn = _baglanti()
    try:
        veri = stem_verisi(conn)
        if veri.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj="Stem ölçümü yok. "
                "<code>python -m python.enrich.icra_profili --tum</code>"))

        denge = enstruman_dengesi(veri)
        ozet = eksen_ozeti(veri)
        cesit = cesitlilik(ozet)

        uyelik = pd.read_sql_query(
            "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id = ?",
            conn, params=(calisma_id,),
        )
        U = (uyelik.pivot(index="album_id", columns="kume_id", values="uyelik")
             .fillna(0.0) if not uyelik.empty else pd.DataFrame())
        adlar = _eksen_adlari(calisma_id) if calisma_id else {}
        imza = kume_ses_imzasi(conn, veri, U, adlar) if not U.empty else pd.DataFrame()

        # --- grafikler ---
        g_denge = grafik.yatay_cubuk(
            [(r["stem"], r["enerji_payi"]) for _, r in denge.iterrows()],
            basamak=3, renk=grafik.PALET["ikincil"])
        g_cesit = grafik.yatay_cubuk(
            [(r["eksen"], r["yayilim"]) for _, r in cesit.iterrows()],
            basamak=2, renk=grafik.PALET["mor"])

        davul = veri[(veri["stem"] == "drums") & veri["zil_payi"].notna()].copy()
        g_davul = efsane = None
        if not davul.empty and not U.empty:
            keskin = U.idxmax(axis=1)
            davul["kume"] = davul["album_id"].map(keskin).map(adlar).fillna("—")
            g_davul = grafik.sacilim(
                [(float(r["tekme_payi"]), float(r["zil_payi"]), str(r["kume"]),
                  f"{r['artist']} — {r['title']}  ·  tekme {r['tekme_payi']:.2f} / "
                  f"zil {r['zil_payi']:.2f}  ·  {r['kume']}")
                 for _, r in davul.iterrows()],
                x_baslik="tekme payı", y_baslik="zil payı")
            efsane = grafik.sacilim_efsanesi(sorted(davul["kume"].unique()))

        g_imza = None
        if not imza.empty:
            g_imza = grafik.isi_haritasi(
                sorted(imza["eksen"].unique()), sorted(imza["kume"].unique()),
                {(r["eksen"], r["kume"]): float(r["sapma"]) for _, r in imza.iterrows()},
                ipuclari={(r["eksen"], r["kume"]):
                          f"{r['kume']} · {r['eksen']}: {r['medyan']:.3f} "
                          f"(kütüphane {r['genel_medyan']:.3f}, "
                          f"sapma {r['sapma']:+.0%}, {r['albüm']} albüm)"
                          for _, r in imza.iterrows()})

        secili_eksen = istek.query_params.get("uc") or (
            ozet.iloc[0]["eksen"] if not ozet.empty else None)
        uc_satiri = ozet[ozet["eksen"] == secili_eksen]
        uclar = None
        if not uc_satiri.empty:
            s = uc_satiri.iloc[0]
            uclar = {
                "eksen": s["eksen"],
                "dusuk_anlam": s["dusuk_anlam"], "yuksek_anlam": s["yuksek_anlam"],
                "en_dusuk": s["en_dusuk"], "en_dusuk_deger": float(s["en_dusuk_deger"]),
                "en_yuksek": s["en_yuksek"], "en_yuksek_deger": float(s["en_yuksek_deger"]),
                "dusuk_klip": _klip_bul(veri, s["stem"], s["en_dusuk"]),
                "yuksek_klip": _klip_bul(veri, s["stem"], s["en_yuksek"]),
            }

        return SABLONLAR.TemplateResponse(istek, "profil.html", _ortam(
            istek, cumleler=profil_cumleleri(ozet, denge), denge=denge,
            g_denge=g_denge, g_cesit=g_cesit, g_davul=g_davul, efsane=efsane,
            g_imza=g_imza, ozet=ozet, uclar=uclar,
            eksen_listesi=list(ozet["eksen"]), albom_sayisi=veri["album_id"].nunique(),
        ))
    finally:
        conn.close()


def _klip_bul(veri: pd.DataFrame, stem: str, etiket: str):
    eslesen = veri[(veri["stem"] == stem)
                   & ((veri["artist"] + " — " + veri["title"]) == etiket)]
    if eslesen.empty:
        return None
    url = eslesen.iloc[0]["onizleme_url"]
    return url if pd.notna(url) else None


async def ogrenme(istek):
    from python.geri_bildirim import (
        kararlar, ozet_cumleleri, strateji_isabeti, uzaklik_tercihi,
    )
    from web import grafik

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    conn = _baglanti()
    try:
        veri = kararlar(conn, calisma_id)
        isabet = strateji_isabeti(veri) if not veri.empty else pd.DataFrame()
        if isabet.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj="Henüz geri bildirim yok. Öneriler sayfasında "
                "👍 / 👎 / 😐 düğmelerini kullandıkça bu ekran dolar."))

        kesif = grafik.aralik([
            (r["strateji"], r["kesif_orani"], r["kesif_alt"], r["kesif_ust"],
             f"{r['strateji']}: {r['toplam']} karar, "
             f"{r['zaten_biliyorum']}'i «zaten biliyorum»")
            for _, r in isabet.iterrows()])
        zevkli = isabet[isabet["zevk_n"] > 0]
        zevk = grafik.aralik([
            (r["strateji"], r["zevk_isabeti"], r["zevk_alt"], r["zevk_ust"],
             f"{r['strateji']}: {r['begendim']} beğendim / {r['tutmadi']} tutmadı")
            for _, r in zevkli.iterrows()]) if not zevkli.empty else None

        return SABLONLAR.TemplateResponse(istek, "ogrenme.html", _ortam(
            istek, cumleler=ozet_cumleleri(isabet), isabet=isabet,
            g_kesif=kesif, g_zevk=zevk,
            uzaklik=uzaklik_tercihi(conn, veri, calisma_id),
            karar_sayisi=veri["aday_id"].nunique(), satir=len(veri),
        ))
    finally:
        conn.close()


async def muzisyenler(istek):
    from python.enrich.icra_profili import ROL_STEM
    from python.muzisyen import (
        ROL_SUTUNLARI, benzer_icracilar, enstruman_rolleri, icra_profilleri,
        muzisyen_verisi, rol_listesi,
    )

    conn = _baglanti()
    try:
        veri = muzisyen_verisi(conn, None)
        if veri.profil.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj="Kredi verisi yok. "
                "<code>python -m python.enrich.krediler</code>"))

        roller = enstruman_rolleri(veri)
        rol = istek.query_params.get("rol") or ("drums" if "drums" in roller else roller[0])
        liste = rol_listesi(veri, rol, adet=300)
        secim = istek.query_params.get("kisi") or (liste.index[0] if len(liste) else None)
        if secim not in liste.index and len(liste):
            secim = liste.index[0]

        profiller = icra_profilleri(conn, rol)
        agirlik = float(istek.query_params.get("agirlik", 0.7))
        benzer, temel = (pd.DataFrame(), "")
        kendi = None
        if secim is not None and not profiller.empty and secim in profiller.index:
            kendi = profiller.loc[secim]
            benzer, temel = benzer_icracilar(
                veri, profiller, secim, rol=rol, adet=6, icra_agirligi=agirlik)

        albumleri = veri.albumleri[veri.albumleri["kisi"] == secim] if secim else pd.DataFrame()
        return SABLONLAR.TemplateResponse(istek, "muzisyenler.html", _ortam(
            istek, roller=roller, rol=rol, stem=ROL_STEM.get(rol),
            liste=liste.head(60), secim=secim,
            kisi_adi=veri.profil.loc[secim, "kisi"] if secim in veri.profil.index else "",
            profil=veri.profil.loc[secim] if secim in veri.profil.index else None,
            kendi=kendi, sutunlar=[s for s in ROL_SUTUNLARI.get(rol, ())][:6],
            benzer=benzer, temel=temel, agirlik=agirlik,
            albumleri=albumleri.groupby(["artist", "title", "year"])["role"]
            .apply(lambda r: ", ".join(sorted(set(r)))).reset_index()
            if not albumleri.empty else pd.DataFrame(),
        ))
    finally:
        conn.close()


async def kumeler(istek):
    from python.kumeleme.temsilciler import ortusen_albumler

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    conn = _baglanti()
    try:
        kumeler_df = pd.read_sql_query(
            "SELECT * FROM clusters WHERE calisma_id = ? ORDER BY kume_id",
            conn, params=(calisma_id,))
        temsilciler = pd.read_sql_query(
            """SELECT t.kume_id, t.sira, t.uyelik, a.artist, a.title, a.year
                 FROM temsilciler t JOIN albums a USING (album_id)
                WHERE t.calisma_id = ? ORDER BY t.kume_id, t.sira""",
            conn, params=(calisma_id,))
        uyelik = pd.read_sql_query(
            "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id = ?",
            conn, params=(calisma_id,))
        U = uyelik.pivot(index="album_id", columns="kume_id",
                         values="uyelik").fillna(0.0)
        albumler = pd.read_sql_query(
            "SELECT album_id, artist, title, year FROM albums", conn
        ).set_index("album_id")

        ortusen = []
        if not U.empty:
            for kayit in ortusen_albumler(U.to_numpy(), esik=0.25, adet=20).itertuples():
                albom = albumler.loc[U.index[kayit.satir]]
                adlar = _eksen_adlari(calisma_id)
                ortusen.append({
                    "artist": albom["artist"], "title": albom["title"],
                    "a": adlar.get(int(kayit.kume_a), kayit.kume_a),
                    "ua": round(kayit.uyelik_a, 2),
                    "b": adlar.get(int(kayit.kume_b), kayit.kume_b),
                    "ub": round(kayit.uyelik_b, 2),
                })

        keskin = U.idxmax(axis=1) if not U.empty else pd.Series(dtype=int)
        boyut = keskin.value_counts().to_dict() if len(keskin) else {}
        return SABLONLAR.TemplateResponse(istek, "kumeler.html", _ortam(
            istek, kumeler=kumeler_df, temsilciler=temsilciler,
            boyut=boyut, ortusen=ortusen,
        ))
    finally:
        conn.close()


async def kume_adlandir(istek):
    veri = await istek.json()
    conn = _baglanti()
    try:
        with conn:
            conn.execute(
                "UPDATE clusters SET kullanici_adi = ? "
                "WHERE calisma_id = ? AND kume_id = ?",
                ((veri.get("ad") or "").strip() or None,
                 veri.get("calisma_id"), int(veri.get("kume_id"))),
            )
    finally:
        conn.close()
    _eksen_adlari.cache_clear()
    return JSONResponse({"tamam": True})


async def veri_seti(istek):
    conn = _baglanti()
    try:
        albumler = pd.read_sql_query(
            """
            SELECT a.artist, a.title, a.year, a.country,
                   a.mbid IS NOT NULL AS mbid_var,
                   (SELECT COUNT(*) FROM credits c WHERE c.album_id=a.album_id) kredi,
                   (SELECT COUNT(*) FROM tags t WHERE t.album_id=a.album_id) etiket,
                   (SELECT COUNT(*) FROM stem_profili s
                     WHERE s.album_id=a.album_id AND s.tur='album') stem
              FROM albums a ORDER BY a.artist, a.year
            """, conn)
        arama = (istek.query_params.get("ara") or "").strip().lower()
        if arama:
            maske = (albumler["artist"].str.lower().str.contains(arama, na=False)
                     | albumler["title"].str.lower().str.contains(arama, na=False))
            albumler = albumler[maske]
        return SABLONLAR.TemplateResponse(istek, "veri_seti.html", _ortam(
            istek, albumler=albumler.head(400), toplam=len(albumler), arama=arama))
    finally:
        conn.close()


async def eslestirme(istek):
    """Elle MusicBrainz eşleştirme — kalan 55 albüm için.

    Otomatikleştirilmiyor: yanlış release-group'a bağlamak, o albüme başka bir
    kaydın kredilerini yazmak demek ve kredi grafiği bu projenin çekirdeği.
    Karar kullanıcının, ekran yalnız adayları getiriyor.
    """
    from python.enrich.mbid_eslestir import album_ara
    from python.onbellek import AgYok, musicbrainz

    canli = istek.query_params.get("canli") == "1"
    sayfa = max(1, int(istek.query_params.get("sayfa", 1)))
    boy = 6

    conn = _baglanti()
    try:
        bekleyen = pd.read_sql_query(
            """SELECT album_id, artist, title, year, track_count FROM albums
                WHERE mbid IS NULL AND mbid_yok = 0 ORDER BY artist, year""", conn)
        say = lambda q: int(conn.execute(q).fetchone()[0])  # noqa: E731
        toplam, bagli = say("SELECT COUNT(*) FROM albums"), say(
            "SELECT COUNT(*) FROM albums WHERE mbid IS NOT NULL")
        yok = say("SELECT COUNT(*) FROM albums WHERE mbid_yok = 1")
    finally:
        conn.close()

    dilim = bekleyen.iloc[(sayfa - 1) * boy: sayfa * boy]
    istemci = musicbrainz(cevrimdisi=not canli)
    satirlar = []
    for _, albom in dilim.iterrows():
        try:
            adaylar, hata = album_ara(istemci, albom["artist"], albom["title"]), None
        except AgYok:
            adaylar, hata = [], "önbellekte yok — «ağdan ara»yı aç"
        except Exception as h:
            adaylar, hata = [], str(h)
        satirlar.append({
            "album_id": albom["album_id"], "artist": albom["artist"],
            "title": albom["title"],
            "year": int(albom["year"]) if pd.notna(albom["year"]) else None,
            "parca": int(albom["track_count"]) if pd.notna(albom["track_count"]) else 0,
            "hata": hata,
            # `album_ara` sözlük değil `Aday` dataclass'ı döndürüyor.
            "adaylar": [{
                "mbid": a.mbid, "baslik": a.title, "sanatci": a.artist,
                "yil": a.yil, "tur": a.tur or "", "skor": a.skor,
            } for a in (adaylar or [])[:6]],
        })

    return SABLONLAR.TemplateResponse(istek, "eslestirme.html", _ortam(
        istek, satirlar=satirlar, bekleyen=len(bekleyen), toplam=toplam,
        bagli=bagli, yok=yok, canli=canli, sayfa=sayfa,
        son_sayfa=max(1, (len(bekleyen) - 1) // boy + 1)))


async def eslestir_kaydet(istek):
    veri = await istek.json()
    album_id, mbid = veri.get("album_id"), veri.get("mbid")
    conn = _baglanti()
    try:
        with conn:
            if mbid == "__yok__":
                conn.execute("UPDATE albums SET mbid_yok = 1 WHERE album_id = ?",
                             (album_id,))
            else:
                conn.execute("UPDATE albums SET mbid = ? WHERE album_id = ?",
                             (mbid, album_id))
    finally:
        conn.close()
    _boru_hatti.cache_clear()
    return JSONResponse({"tamam": True})


async def sozluk_sayfasi(istek):
    """Terimler sözlüğü — ekrandaki her sayının ne olduğu.

    Ayrı bir sayfa olmasının sebebi: ipuçları (`title=`) yalnız fareyle
    üstüne gelince görünüyor ve nasıl ölçüldüğü gibi uzun açıklamayı
    taşıyamıyor. Burada hepsi bir arada, aranabilir.
    """
    from python.sozluk import SOZLUK

    gruplar = {
        "Ölçümler — ayrılmış stem'den": [
            "stem", "izgara_entropi", "tekme_payi", "trampet_payi", "zil_payi",
            "nota_vurus", "harmonik_pay", "perde_medyan", "perde_araligi",
            "vibrato_hizi", "sustain_orani", "parlaklik", "dinamik_db",
            "enerji_payi",
        ],
        "Kümeleme ve profil": [
            "eksen", "uyelik", "stabilite", "ses_uzakligi", "icra_profili",
            "yayilim",
        ],
        "Aday üretme stratejileri": [
            "kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik",
            "liste_birlikteligi", "pmi",
        ],
        "Geri bildirim": ["kesif_orani", "zevk_isabeti", "wilson"],
    }
    return SABLONLAR.TemplateResponse(istek, "sozluk.html", _ortam(
        istek, gruplar=gruplar, sozluk=SOZLUK))


async def etiketler(istek):
    """Çok boyutlu etiketler ve tarifler."""
    from python.etiket import ACIKLAMALAR, tarifler

    conn = _baglanti()
    try:
        etiket = pd.read_sql_query(
            """SELECT e.eksen, e.etiket, e.kaynak, COUNT(*) albüm
                 FROM album_etiket e GROUP BY e.eksen, e.etiket
                ORDER BY albüm DESC""", conn)
        if etiket.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj="Etiket yok. <code>python -m python.etiket</code>"))

        secili = istek.query_params.get("etiket")
        albumler = pd.DataFrame()
        if secili:
            albumler = pd.read_sql_query(
                """SELECT a.artist, a.title, a.year FROM album_etiket e
                     JOIN albums a USING (album_id)
                    WHERE e.etiket = ? ORDER BY a.artist, a.year""",
                conn, params=(secili,))

        return SABLONLAR.TemplateResponse(istek, "etiketler.html", _ortam(
            istek, tarif=tarifler(conn), etiket=etiket, aciklamalar=ACIKLAMALAR,
            secili=secili, albumler=albumler,
            toplam=int(etiket["albüm"].sum())))
    finally:
        conn.close()


async def ses_kumeleri(istek):
    """Sesten keşfedilmiş türler — «bu sese benzeyen ama bende olmayan».

    Kullanıcının isteği buydu: "j-fusion önerisi istediğimde elimde olmayan
    bir öneri gelsin." Tür etiketi kullanılmıyor; kümeler CLAP gömüsünden,
    yani sesin kendisinden çıkıyor.
    """
    from python.ses_kume import kume_adi, kumeye_yakinlar

    conn = _baglanti()
    try:
        kumeler = pd.read_sql_query("SELECT * FROM ses_kumesi", conn)
        if kumeler.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj="Ses kümesi yok. Önce "
                "<code>python -m python.etiket_clap --gomu</code> sonra "
                "<code>python -m python.ses_kume</code>"))

        albumler = {
            r[0]: (r[1], r[2]) for r in conn.execute(
                "SELECT album_id, artist, title FROM albums")
        }
        kullanici_adlari = {
            r[0]: r[1] for r in conn.execute("SELECT kume, ad FROM ses_kume_adi")
        }
        liste = []
        for kume, grup in kumeler.groupby("kume"):
            liste.append({
                "kume": int(kume), "ad": kume_adi(conn, grup),
                "kullanici_adi": kullanici_adlari.get(int(kume)),
                "sayi": len(grup),
                "uyeler": [
                    f"{albumler.get(a, ('?', ''))[0]} — {albumler.get(a, ('', '?'))[1]}"
                    for a in grup.nsmallest(6, "merkez_uzakligi")["album_id"]
                ],
            })

        secili = istek.query_params.get("kume")
        oneriler_ = []
        if secili is not None and secili.isdigit():
            grup = kumeler[kumeler["kume"] == int(secili)]
            if not grup.empty:
                oneriler_ = kumeye_yakinlar(conn, grup, adet=25)
        secili_no = int(secili) if (secili and secili.isdigit()) else None
        return SABLONLAR.TemplateResponse(istek, "ses_kumeleri.html", _ortam(
            istek, kumeler=liste, secili=secili_no, oneriler=oneriler_,
            secili_ad=kullanici_adlari.get(secili_no)))
    finally:
        conn.close()


async def taze_onizleme(istek):
    """Bir Deezer parçasının TAZE önizleme URL'si.

    Saklanan URL'ler kullanılamıyor: Deezer onları kısa ömürlü imzalıyor —
    ölçüldü, hasattan saatler sonra 10 URL'nin 10'u da 403 döndü. Kalıcı olan
    parça kimliği; çalma anında taze URL alınıyor.

    Yönlendirme değil JSON dönüyor: tarayıcı `<audio src>`'yi kendisi
    ayarlasın, böylece bir kez alınan URL sayfa açık kaldığı sürece çalışır.

    `yenile=True` ŞART ve bu satır bir hatanın düzeltmesi (2026-09-02). K5
    gereği her dış çağrı önbellekleniyor; önbellekli çağrı da URL'nin ESKİ
    hâlini döndürüyordu. Yani "taze önizleme" ucu taze değildi: ölçüldü,
    dönen URL'nin imzası 1.053 saniye önce dolmuştu ve ses dosyası 403
    veriyordu. Önbellek burada tam olarak çözmesi gereken şeyi bozuyor.

    Genel kural: KISA ÖMÜRLÜ İMZALI URL ÖNBELLEKLENMEZ. Bu uçtaki maliyet
    çalma başına bir istek ve `istek_araligi` ile zaten sınırlı.
    """
    parca_id = istek.path_params["parca_id"]
    from python.discover.calma_listesi import deezer_listesi

    try:
        bilgi = deezer_listesi().get_json(f"track/{parca_id}", {}, yenile=True)
        url = (bilgi or {}).get("preview")
    except Exception:
        url = None
    if not url:
        return JSONResponse({"hata": "önizleme yok"}, status_code=404)
    return JSONResponse({"url": url})


async def ses_kume_adlandir(istek):
    veri = await istek.json()
    conn = _baglanti()
    try:
        with conn:
            conn.execute(
                "INSERT INTO ses_kume_adi (kume, ad) VALUES (?,?) "
                "ON CONFLICT(kume) DO UPDATE SET ad = excluded.ad",
                (int(veri.get("kume")), (veri.get("ad") or "").strip() or None),
            )
    finally:
        conn.close()
    return JSONResponse({"tamam": True})

# --------------------------------------------------------------------------- #
# Oturum — ara katman ve giriş yolları
# --------------------------------------------------------------------------- #

class OturumAraKatmani(BaseHTTPMiddleware):
    """Çerezden oturumu çöz, kullanıcıyı bağlam değişkenine koy.

    Ara katman olmasının sebebi: yetki denetimi her rotada tekrarlanırsa bir
    gün biri unutulur ve o sayfa sessizce herkese açık kalır. Tek kapı, açık
    yollar listesi (`ACIK_YOLLAR`) ve geri kalan her şey kapalı.
    """

    async def dispatch(self, istek, sonraki):
        jeton = istek.cookies.get(CEREZ_ADI)
        conn = _oturum_baglantisi()
        try:
            kullanici_id = oturum_coz(conn, jeton)
        finally:
            conn.close()

        belirtec = AKTIF_KULLANICI.set(kullanici_id)
        try:
            yol = istek.url.path
            acik = any(yol == a or yol.startswith(a + "/") for a in ACIK_YOLLAR)
            if kullanici_id is None and not acik:
                return RedirectResponse("/giris", status_code=303)
            return await sonraki(istek)
        finally:
            AKTIF_KULLANICI.reset(belirtec)


def _cerez_koy(yanit, jeton: str):
    """Oturum çerezi. `httponly` betiklerden okunmasını engeller; `samesite`
    başka sitelerin bu uygulamaya kimlikli istek attırmasını (CSRF) zorlaştırır.
    `secure` YOK çünkü uygulama yerelde http üzerinden çalışıyor; https'e
    taşınırsa eklenmeli."""
    yanit.set_cookie(CEREZ_ADI, jeton, max_age=OTURUM_GUN * 86400,
                     httponly=True, samesite="lax", path="/")
    return yanit


async def giris(istek):
    if AKTIF_KULLANICI.get() is not None:
        return RedirectResponse("/oneriler", status_code=303)
    conn = _oturum_baglantisi()
    try:
        ilk_kurulum = kullanici_sayisi(conn) == 0
    finally:
        conn.close()
    return SABLONLAR.TemplateResponse(istek, "giris.html", {
        "request": istek, "hata": istek.query_params.get("hata"),
        "ilk_kurulum": ilk_kurulum, "yol": "/giris",
        "spotify_hazir": _spotify_hazir(),
    })


async def giris_gonder(istek):
    veri = await istek.form()
    eposta = (veri.get("eposta") or "").strip().lower()
    parola = veri.get("parola") or ""
    conn = _oturum_baglantisi()
    try:
        kullanici_id = giris_dogrula(conn, eposta, parola)
        if kullanici_id is None:
            # Tek mesaj: "kullanıcı yok" ile "parola yanlış" ayrımı hangi
            # e-postaların kayıtlı olduğunu ele verir.
            return RedirectResponse("/giris?hata=1", status_code=303)
        jeton = oturum_ac(conn, kullanici_id)
    finally:
        conn.close()
    return _cerez_koy(RedirectResponse("/oneriler", status_code=303), jeton)


async def uyelik(istek):
    if AKTIF_KULLANICI.get() is not None:
        return RedirectResponse("/oneriler", status_code=303)
    return SABLONLAR.TemplateResponse(istek, "uyelik.html", {
        "request": istek, "hata": istek.query_params.get("hata"),
        "yol": "/uyelik",
    })


async def uyelik_gonder(istek):
    veri = await istek.form()
    ad = (veri.get("ad") or "").strip()
    eposta = (veri.get("eposta") or "").strip().lower()
    parola = veri.get("parola") or ""
    if not ad or not eposta or len(parola) < 8:
        return RedirectResponse("/uyelik?hata=eksik", status_code=303)

    conn = _oturum_baglantisi()
    try:
        # BEŞ KULLANICI SINIRI. Spotify Development Mode uygulaması en fazla
        # beş yetkili hesap taşıyabiliyor (Şubat 2026 kuralı) ve panele elle
        # eklenmeyen hesap zaten giriş yapamaz. Sınırı burada da uygulamak,
        # kullanıcının Spotify tarafında anlaşılmaz bir hatayla karşılaşması
        # yerine anlaşılır bir mesaj görmesini sağlıyor.
        if kullanici_sayisi(conn) >= AZAMI_KULLANICI:
            return RedirectResponse("/uyelik?hata=dolu", status_code=303)
        if kullanici_bul(conn, eposta=eposta) is not None:
            return RedirectResponse("/uyelik?hata=kayitli", status_code=303)
        kullanici_id = kullanici_olustur(conn, ad, eposta=eposta, parola=parola)
        jeton = oturum_ac(conn, kullanici_id)
    finally:
        conn.close()
    # Yeni hesabın kütüphanesi boş; doğrudan karşılama akışına.
    return _cerez_koy(RedirectResponse("/basla", status_code=303), jeton)


async def cikis(istek):
    jeton = istek.cookies.get(CEREZ_ADI)
    conn = _oturum_baglantisi()
    try:
        oturum_kapat(conn, jeton)
    finally:
        conn.close()
    yanit = RedirectResponse("/giris", status_code=303)
    yanit.delete_cookie(CEREZ_ADI, path="/")
    return yanit


async def saglik(istek):
    return JSONResponse({"durum": "ayakta"})


async def servis_calisani(istek):
    from starlette.responses import FileResponse
    return FileResponse(KOK / "statik" / "sw.js",
                        media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})


def _spotify_hazir() -> bool:
    """Spotify düğmesi ancak yapılandırılmışsa gösterilir.

    Yapılandırılmadan gösterilirse kullanıcı tıklar ve hata görür; düğmenin
    varlığı bir söz veriyor, tutulamayacak söz verilmemeli.
    """
    from python.onbellek import _env
    return bool(_env("SPOTIFY_CLIENT_ID") and _env("SPOTIFY_CLIENT_SECRET"))


async def basla(istek):
    """Karşılama — hesabı yeni açılmış, kütüphanesi boş kullanıcı için.

    Boş bir öneri sayfasına düşmek "uygulama bozuk" hissi veriyor. Burada ne
    olduğu ve sıradaki adımın ne olduğu yazılı.
    """
    conn = _baglanti()
    try:
        albom = conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
        kullanici = conn.execute(
            "SELECT ad, spotify_id FROM kullanici WHERE kullanici_id = ?",
            (AKTIF_KULLANICI.get(),)).fetchone()
    finally:
        conn.close()
    if albom:
        return RedirectResponse("/oneriler", status_code=303)
    return SABLONLAR.TemplateResponse(istek, "basla.html", {
        "request": istek, "yol": "/basla",
        "ad": kullanici["ad"] if kullanici else "",
        "spotify_bagli": bool(kullanici and kullanici["spotify_id"]),
        "spotify_hazir": _spotify_hazir(),
    })

ROTALAR = [
    Route("/", anasayfa),
    Route("/oneriler", oneriler),
    Route("/profil", profil),
    Route("/ogrenme", ogrenme),
    Route("/muzisyenler", muzisyenler),
    Route("/kumeler", kumeler),
    Route("/veri", veri_seti),
    Route("/eslestirme", eslestirme),
    Route("/etiketler", etiketler),
    Route("/ses-kumeleri", ses_kumeleri),
    Route("/api/onizleme/{parca_id}", taze_onizleme),
    Route("/api/ses-kume-adi", ses_kume_adlandir, methods=["POST"]),
    Route("/basla", basla),
    Route("/giris", giris),
    Route("/giris", giris_gonder, methods=["POST"]),
    Route("/uyelik", uyelik),
    Route("/uyelik", uyelik_gonder, methods=["POST"]),
    Route("/cikis", cikis, methods=["GET", "POST"]),
    Route("/saglik", saglik),
    # Servis çalışanının KAPSAMI bulunduğu dizinle sınırlı. `/statik/sw.js`
    # yalnız `/statik/*` isteklerini görebilirdi; uygulamanın tamamını
    # kapsaması için kökten sunuluyor.
    Route("/sw.js", servis_calisani),
    Route("/sozluk", sozluk_sayfasi),
    Route("/api/eslestir", eslestir_kaydet, methods=["POST"]),
    Route("/api/karar", karar_ver, methods=["POST"]),
    Route("/api/kume-adi", kume_adlandir, methods=["POST"]),
    Mount("/statik", StaticFiles(directory=str(KOK / "statik")), name="statik"),
]

uygulama = Starlette(
    routes=ROTALAR,
    middleware=[Middleware(OturumAraKatmani)],
)

SABLONLAR.env.filters["sayi"] = _sayi


def main(argv: list[str] | None = None) -> int:
    global DB_YOLU
    import uvicorn

    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", default=DB_YOLU)
    ayristirici.add_argument("--port", type=int, default=8800)
    ayristirici.add_argument("--host", default="127.0.0.1")
    args = ayristirici.parse_args(argv)

    DB_YOLU = args.db
    print(f"  http://{args.host}:{args.port}")
    uvicorn.run(uygulama, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
