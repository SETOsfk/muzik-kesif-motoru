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
import contextlib
import json
import os
import re
import sqlite3
import sys
import threading
import time
from contextvars import ContextVar
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from python.db import baglan, baglan_kullanici, baglan_ortak
from python.hesap import (
    CEREZ_ADI,
    OTURUM_GUN,
    deneme_kaydet,
    denemeleri_sifirla,
    kilitli_mi,
    giris_dogrula,
    kullanici_bul,
    kullanici_olustur,
    kullanici_sayisi,
    oturum_ac,
    oturum_coz,
    oturum_kapat,
)
from python import kesif
from python.dil import (
    AKTIF_DIL, DIL_CEREZI, DILLER, dil as etkin_dil, istekten_dil, sayi as dil_sayi, t, yuzde,
)
from web.yer_tutucu import yer_tutucu_svg

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
ACIK_YOLLAR = ("/giris", "/uyelik", "/cikis", "/statik", "/saglik", "/sw.js", "/dil",
               "/gizlilik")

#: Hesap tavanı. Varsayılan 5: Spotify Development Mode uygulaması en fazla
#: beş yetkili hesap taşıyor (Şubat 2026). Listeyle başlama yolu (2026-09-28)
#: Spotify istemediği için yayında yükseltilebilir (`KESIF_AZAMI_KULLANICI`);
#: Spotify'ın kendi beş kişilik sınırı o zaman da panelde geçerli kalır.
AZAMI_KULLANICI = int(os.environ.get("KESIF_AZAMI_KULLANICI", "5"))

#: Aynı anda en çok kaç aktarım süreci. Her süreç CLAP (torch) yüklüyor,
#: ~2 GB bellek; küçük bir sunucuda iki üç eşzamanlı aktarım belleği bitirir.
AZAMI_ES_ZAMANLI_AKTARIM = int(os.environ.get("KESIF_ES_ZAMANLI_AKTARIM", "2"))

#: Uygulama https ardında mı sunuluyor? Açıksa oturum çerezi `secure` alır
#: (yalnız şifreli bağlantıda gönderilir) ve `X-Forwarded-For` okunur.
#: VARSAYILAN KAPALI: yerelde http kullanılıyor ve `secure` çerez hiç
#: gönderilmezdi — giriş sessizce çalışmaz hâle gelirdi.
HTTPS_ARKASINDA = os.environ.get("KESIF_HTTPS", "").lower() in ("1", "true", "evet")

#: `X-Forwarded-For` ancak GÜVENİLİR bir vekil arkasındayken anlamlı; aksi
#: hâlde istemci onu uydurup hız sınırını atlar.
GUVENILIR_VEKIL = HTTPS_ARKASINDA

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


# Sarmalayıcılar `lru_cache` nesnesi DEĞİL, dolayısıyla `cache_clear`
# taşımıyorlar. Çağrı yerleri (karar verme, küme adlandırma) önbelleği
# temizliyordu ve sarmalama sonrası AttributeError ile 500 veriyordu —
# kullanıcı "geri bildirimin kaydedilemedi" uyarısı alıyordu. İç işlevin
# temizleyicisini dışa bağlamak, çağrı yerlerini değiştirmeden çözüyor.
_calismalar.cache_clear = _calismalar_onbellek.cache_clear


def _son_calisma() -> str | None:
    calismalar = _calismalar()
    return calismalar[0]["calisma_id"] if calismalar else None


@lru_cache(maxsize=64)
def _eksen_adlari_onbellek(kullanici_id: int | None,
                           calisma_id: str) -> dict[int, str]:
    conn = _baglanti()
    try:
        # YALNIZ ham ad önbelleğe girer. Yedek ad ("Eksen 3"/"Axis 3") dile
        # bağlı ve gösterimde kuruluyor; önbellekte dursaydı ilk istek hangi
        # dildeyse herkes onu görürdü (K20'deki önbellek sınıfının dil hâli).
        return {
            int(r["kume_id"]): r["kullanici_adi"]
            for r in conn.execute(
                "SELECT kume_id, kullanici_adi FROM clusters WHERE calisma_id = ?",
                (calisma_id,),
            )
        }
    finally:
        conn.close()


def _eksen_adlari(calisma_id: str) -> dict[int, str]:
    return {k: ad or kesif.eksen_etiketi(k)
            for k, ad in _eksen_adlari_onbellek(AKTIF_KULLANICI.get(), calisma_id).items()}


_eksen_adlari.cache_clear = _eksen_adlari_onbellek.cache_clear


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

        # Yalnız SAYILAR önbelleğe girer; etiketler dile göre gösterimde.
        return (
            ("album", say("SELECT COUNT(*) FROM albums")),
            ("muzisyen", say("SELECT COUNT(DISTINCT person_name) FROM credits")),
            ("stem", say("SELECT COUNT(DISTINCT album_id) FROM stem_profili WHERE tur='album'")),
            ("aday", say("SELECT COUNT(DISTINCT aday_id) FROM adaylar")),
            ("karar", say("SELECT COUNT(*) FROM feedback")),
        )
    finally:
        conn.close()


_BORU_ETIKET = {
    "album": ("albüm", "albums"), "muzisyen": ("müzisyen", "musicians"),
    "stem": ("ses ölçümü", "audio scans"), "aday": ("aday", "candidates"),
    "karar": ("karar", "decisions"),
}


def _boru_hatti() -> list[dict]:
    return [{"ad": t(*_BORU_ETIKET[k]), "deger": n}
            for k, n in _boru_hatti_onbellek(AKTIF_KULLANICI.get())]


_boru_hatti.cache_clear = _boru_hatti_onbellek.cache_clear


# --------------------------------------------------------------------------- #
# Süreli önbellek — pahalı, yalnız boru hattı koşunca değişen hesaplar
# --------------------------------------------------------------------------- #
#
# ÖLÇÜLDÜ (2026-09-23, seto'nun verisi): /oneriler 1,7–3,4 sn. Dağılım:
# müzisyen profilleri aday başına yeniden hesaplanıyordu (40 × 0,11 sn),
# çalma listesi bağlamı 2,1 sn, CLAP havuzu her istekte ~2.600 dosya okuması
# (0,45 sn), kütüphane uzaklık dağılımı 1,1 sn. Hiçbiri kararla değişmiyor.
#
# `lru_cache` yetmiyor: aktarım AYRI SÜREÇTE yazıyor ve komut satırından
# koşulan boru hattı sunucuya haber vermiyor. Süre dolumu, sunucu yeniden
# başlatılmadan bayatlığın bir üst sınırı olmasını sağlıyor; bilinen yazma
# yolları (aktarım bitişi, desteyi büyütme) ayrıca açıkça boşaltıyor.
#
# K20: İLK ARGÜMAN HER ZAMAN KULLANICI KİMLİĞİ. Anahtarsız önbellek
# kullanıcılar arası veri sızdırır — bu projede dört kez yaşandı.

class _Sureli:
    def __init__(self, fn, saniye: float):
        self.fn, self.saniye = fn, saniye
        self._veri: dict[tuple, tuple[float, object]] = {}
        self._kilit = threading.Lock()
        self.__name__ = fn.__name__
        self.__doc__ = fn.__doc__

    def __call__(self, *anahtar):
        simdi = time.monotonic()
        with self._kilit:
            kayit = self._veri.get(anahtar)
        if kayit and simdi - kayit[0] < self.saniye:
            return kayit[1]
        deger = self.fn(*anahtar)
        with self._kilit:
            self._veri[anahtar] = (simdi, deger)
        return deger

    def cache_clear(self) -> None:
        with self._kilit:
            self._veri.clear()


_SURELILER: list[_Sureli] = []


def _sureli(saniye: float):
    def sar(fn):
        s = _Sureli(fn, saniye)
        _SURELILER.append(s)
        return s
    return sar


def _onbellekleri_bosalt() -> None:
    """Kullanıcı verisini etkileyen bir yazmadan sonra her şeyi boşalt."""
    for s in _SURELILER:
        s.cache_clear()
    _calismalar.cache_clear()
    _boru_hatti.cache_clear()
    _eksen_adlari.cache_clear()
    _icra_eslesmesi_onbellek.cache_clear()


def _baglantiyla(islev, *arg, **kw):
    conn = _baglanti()
    try:
        return islev(conn, *arg, **kw)
    finally:
        conn.close()


@_sureli(1200)
def _icra_profilleri_onbellek(kullanici_id: int | None, rol: str):
    from python.muzisyen import icra_profilleri
    return _baglantiyla(icra_profilleri, rol)


@_sureli(1800)
def _baglam_onbellek(kullanici_id: int | None) -> dict:
    try:
        from python.etiket import sanatci_baglami
        return _baglantiyla(sanatci_baglami)
    except Exception:
        return {}


@_sureli(1800)
def _olcum_onbellek(kullanici_id: int | None) -> dict:
    try:
        from python.etiket import aday_olcum_etiketleri
        return _baglantiyla(aday_olcum_etiketleri)
    except Exception:
        return {}


@_sureli(1200)
def _havuz_onbellek(kullanici_id: int | None):
    """CLAP havuzu (adaylar + liste parçaları). Adaylar değişince (desteyi
    büyütme) açıkça boşaltılıyor; bkz. `api_buyut`."""
    from python.ses_kume import havuz_gomuleri
    try:
        return _baglantiyla(havuz_gomuleri)
    except Exception:
        return None


@_sureli(1200)
def _taban_onbellek(kullanici_id: int | None, calisma_id: str, eksen: int):
    """Kütüphanenin kendi albümlerinin bu eksene uzaklığı: iç/dış medyan."""
    from python.discover.ses_uzakligi import kutuphane_uzaklik_dagilimi

    conn = _baglanti()
    try:
        dagilim = kutuphane_uzaklik_dagilimi(conn, calisma_id, eksen)
        if dagilim.empty:
            return None
        uyelik = pd.read_sql_query(
            "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id = ?",
            conn, params=(calisma_id,))
        U = uyelik.pivot(index="album_id", columns="kume_id", values="uyelik").fillna(0.0)
        keskin = U.idxmax(axis=1)
        ic = dagilim[dagilim.index.map(keskin) == eksen]
        dis = dagilim[dagilim.index.map(keskin) != eksen]
        if len(ic) >= 3 and len(dis) >= 3:
            return {"ic": float(ic.median()), "dis": float(dis.median())}
        return None
    except Exception:
        return None
    finally:
        conn.close()


def _yakinlik(conn, calisma_id: str) -> dict:
    from python.geri_bildirim import yakinlik_etkisi
    havuz = _havuz_onbellek(AKTIF_KULLANICI.get())
    return yakinlik_etkisi(conn, calisma_id, havuz=havuz)


def _liste_sayisi() -> int:
    if AKTIF_KULLANICI.get() is None:
        return 0
    return _baglantiyla(kesif.liste_sayisi)


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
        "liste_sayisi": _liste_sayisi(),
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
    """Giriş yapılmışsa Keşfet'e, yapılmamışsa ara katman girişe yollar.

    Keşfet günlük döngünün kendisi (kaydır, dinle, listeye at); Öneriler
    ayrıntılı inceleme için menüde duruyor.
    """
    return RedirectResponse("/kesfet")


#: Ana akıştaki yollar — leave-one-artist-out ile ölçüldü ve tuttular.
ANA_STRATEJILER = ("melez", "liste_birlikteligi", "ses_benzerligi")

#: Niş yollar: kredi/kalabalık grafiği. Ölçümde erişimleri çok dar çıktı
#: (147 gizlemenin tamamında 55–81 tekil sanatçı, 1 isabet) ama ölçüt onların
#: işini ölçmüyor — "müzisyen paylaşan başka kayıt" tanım gereği sahip
#: OLMADIĞIN şey. Bu yüzden silinmiyor, ana akıştan çıkarılıyor.
NIS_STRATEJILER = ("kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik")


def oneriler(istek):
    # SYNC: Starlette bunu iş parçacığı havuzunda koşturuyor. `async` iken
    # pandas hesabı olay döngüsünü kilitliyor, o sırada gelen her istek
    # (aynı kullanıcının önizleme çağrısı dahil) bekliyordu. Bağlam
    # değişkeni (AKTIF_KULLANICI) iş parçacığına kopyalanıyor (anyio).
    from python.discover.ses_uzakligi import eksen_uzakliklari
    from python.geri_bildirim import ETKI_TAVANI, bilinen_sanatcilar
    from python.metin import normalize_esleme

    kullanici_id = AKTIF_KULLANICI.get()

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    if not calisma_id:
        # Yeni kullanıcı komut satırı talimatıyla karşılaşmamalı: kütüphanesi
        # ya boş ya aktarılıyor, ikisinin de anlatıldığı yer /basla.
        return RedirectResponse("/basla", status_code=303)

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
        # "dinleyici tipi") ve ölçüm (adayın kendi stem'lerinden). İkisi de
        # pahalı ve karardan bağımsız — süreli önbellekten.
        baglam = _baglam_onbellek(kullanici_id)
        olcum_et = _olcum_onbellek(kullanici_id)
        try:
            from python.etiket import ACIKLAMALAR as etiket_aciklama
        except Exception:
            etiket_aciklama = {}

        if adaylar.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj=t("Henüz aday yok. Üretmek için: ",
                               "No candidates yet. To generate them: ")
                + "<code>python -m python.discover.adaylar --tum-eksenler</code>"))

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
        try:
            uzakliklar = eksen_uzakliklari(conn, calisma_id, secili)
            if not uzakliklar.empty:
                gorunum = gorunum.merge(
                    uzakliklar[["aday_id", "ses_uzakligi"]], on="aday_id", how="left"
                )
        except Exception:
            pass
        taban = _taban_onbellek(kullanici_id, calisma_id, secili)
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
        from python.gerekce import gerekce as gerekce_yaz
        eksen_adi_secili = _eksen_adlari(calisma_id).get(secili) or kesif.eksen_etiketi(secili)
        kutuphane_adlari = kesif.kutuphane_adlari(conn)

        # Medya (kapak + çalınabilir parça) tek sorguda. Keşfet destesinin
        # çözdüğü kapaklar burada da görünür; albüm adayının saklı önizlemesi
        # yoksa medyanın bulduğu parça çalınır.
        kimlikler = [str(k) for k in gorunum["aday_id"].unique()]
        medya: dict[str, sqlite3.Row] = {}
        for i in range(0, len(kimlikler), 500):
            dilim = kimlikler[i:i + 500]
            for r in conn.execute(
                f"SELECT aday_id, kapak, parca_id, parca_adi FROM medya "
                f"WHERE aday_id IN ({','.join('?' * len(dilim))})", dilim):
                medya[r["aday_id"]] = r

        gruplar = []
        for (sanatci, strateji), grup in gorunum.groupby(
            ["artist", "strateji"], sort=False
        ):
            grup = grup.sort_values("year", na_position="last")
            albumler = []
            for _, aday in grup.iterrows():
                uz = aday.get("ses_uzakligi")
                m = medya.get(aday["aday_id"])
                albumler.append({
                    "aday_id": aday["aday_id"], "title": aday["title"],
                    "year": int(aday["year"]) if pd.notna(aday["year"]) else None,
                    "onizleme": aday["onizleme_url"] if pd.notna(aday["onizleme_url"]) else None,
                    # Parça adayında SAKLANMIŞ URL kullanılmaz: Deezer kısa
                    # ömürlü imzalıyor. Kimlik varsa "dinle" düğmesi taze URL
                    # çeker (`/api/onizleme/{parca_id}`).
                    "parca_id": int(aday["parca_id"]) if pd.notna(
                        aday.get("parca_id")) else (
                        int(m["parca_id"]) if m and m["parca_id"] else None),
                    "parca": aday.get("onizleme_parca") if pd.notna(
                        aday.get("onizleme_parca")) else (m["parca_adi"] if m else None),
                    "kapak": m["kapak"] if m else None,
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
                # Gerekçe GÖSTERİMDE, etkin dilde ve kanıtın gücüyle kuruluyor
                # (`python/gerekce.py`); saklanan Türkçe metin yalnız yedek.
                "gerekce": gerekce_yaz(strateji, ilk.get("dayanak"),
                                       eksen=eksen_adi_secili, saklanan=ilk["gerekce"],
                                       adlar=kutuphane_adlari),
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
                "kapak": next((a["kapak"] for a in albumler if a["kapak"]), None)
                         or (ilk.get("kapak") if pd.notna(ilk.get("kapak")) else None),
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
        etki = _yakinlik(conn, calisma_id)
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
            etiket_aciklama_tr=etiket_aciklama,
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
            tablo, _ = adaya_benzeyen_icracilar(
                conn, aday_id, rol, adet=3,
                profiller=_icra_profilleri_onbellek(kullanici_id, rol))
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
        return JSONResponse({"hata": t("geçersiz karar", "invalid decision")}, status_code=400)

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
        # Liste, Keşfet'teki sağa kaydırmayla AYNI anlamı taşımalı: 👍 listeye
        # ekler; 👍 geri alınır ya da başka karara dönülürse yalnız hâlâ
        # 'yeni' olan satırlar çıkar (dinlenmiş/edinilmiş olan korunur).
        if karar == "begendim" and not geri_al:
            kesif.listeye_ekle(conn, calisma_id, kimlikler)
        elif "begendim" in mevcut:
            kesif.listeden_cikar_yeni(conn, kimlikler)
        liste = kesif.liste_sayisi(conn)
    finally:
        conn.close()
    _boru_hatti.cache_clear()
    return JSONResponse(
        {"karar": None if geri_al else karar, "adet": len(kimlikler), "liste": liste}
    )


async def profil(istek):
    from python.profil import (
        cesitlilik, eksen_adi, eksen_ozeti, enstruman_dengesi, harita,
        kume_ses_imzasi, odaklar, profil_cumleleri, stem_adi, stem_verisi,
    )
    from web import grafik

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    conn = _baglanti()
    try:
        veri = stem_verisi(conn)
        if veri.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj=t("Henüz enstrüman ölçümü yok. Çalıştırmak için: ",
                               "No instrument measurements yet. To run them: ")
                + "<code>python -m python.enrich.icra_profili --tum</code>"))

        # ODAK. Aynı ekran herkese aynı şeyi göstermemeli: biri gitara,
        # biri vokale bakmak ister, biri hiçbirine — düz bir profil ister.
        # Varsayılan «genel» ve enstrüman jargonu içermiyor.
        ODAKLAR = odaklar()
        odak = istek.query_params.get("odak", "genel")
        if odak not in ODAKLAR:
            odak = "genel"

        denge = enstruman_dengesi(veri)
        ozet = eksen_ozeti(veri, odak)
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
            [(stem_adi(r["stem"]), r["enerji_payi"]) for _, r in denge.iterrows()],
            basamak=3, renk=grafik.PALET["ikincil"])
        g_cesit = grafik.yatay_cubuk(
            [(r["eksen"], r["yayilim"]) for _, r in cesit.iterrows()],
            basamak=2, renk=grafik.PALET["mor"])

        # HARİTA ODAĞA GÖRE. Eskiden sabit bir "Davul haritası" vardı; vokale
        # bakan kullanıcı yine davul görüyordu.
        x_sutun, x_stem, y_sutun, y_stem, harita_aciklama = harita(odak)
        harita_basligi = t(f"{ODAKLAR[odak][0]} haritası", f"{ODAKLAR[odak][0]} map")

        if x_stem == y_stem:
            kaynak = veri[veri["stem"] == x_stem]
        else:  # farklı stem'lerden eksen: albüm bazında birleştir
            kaynak = veri[veri["stem"] == x_stem].merge(
                veri[veri["stem"] == y_stem][["album_id", y_sutun]],
                on="album_id", suffixes=("", "_y"))
        y_ad = y_sutun + "_y" if (x_stem != y_stem and y_sutun in
                                  veri.columns) else y_sutun
        davul = kaynak[kaynak[x_sutun].notna() & kaynak[y_ad].notna()].copy() \
            if x_sutun in kaynak.columns and y_ad in kaynak.columns else pd.DataFrame()
        g_davul = efsane = None
        if not davul.empty and not U.empty:
            keskin = U.idxmax(axis=1)
            davul["kume"] = davul["album_id"].map(keskin).map(adlar).fillna("—")
            g_davul = grafik.sacilim(
                [(float(r[x_sutun]), float(r[y_ad]), str(r["kume"]),
                  f"{r['artist']} — {r['title']}  ·  {r[x_sutun]:.2f} / "
                  f"{r[y_ad]:.2f}  ·  {r['kume']}")
                 for _, r in davul.iterrows()],
                # Eksen başlıkları ODAĞA göre. Eskiden sabit "tekme payı /
                # zil payı" yazıyordu; vokal haritasında bile.
                x_baslik=eksen_adi(x_sutun, x_stem), y_baslik=eksen_adi(y_sutun, y_stem))
            efsane = grafik.sacilim_efsanesi(sorted(davul["kume"].unique()))

        g_imza = None
        if not imza.empty:
            g_imza = grafik.isi_haritasi(
                sorted(imza["eksen"].unique()), sorted(imza["kume"].unique()),
                {(r["eksen"], r["kume"]): float(r["sapma"]) for _, r in imza.iterrows()},
                ipuclari={(r["eksen"], r["kume"]):
                          f"{r['kume']} · {r['eksen']}: {dil_sayi(r['medyan'], 3)} "
                          + t(f"(kütüphane {dil_sayi(r['genel_medyan'], 3)}, "
                              f"sapma {yuzde(r['sapma'])}, {r['albüm']} albüm)",
                              f"(library {dil_sayi(r['genel_medyan'], 3)}, "
                              f"deviation {yuzde(r['sapma'])}, {r['albüm']} albums)")
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
            odak=odak, odaklar=ODAKLAR, stem_adi=stem_adi,
            harita_basligi=harita_basligi, harita_aciklama=harita_aciklama,
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
        kararlar, ozet_cumleleri, sanatci_duzeyi, strateji_isabeti, uzaklik_tercihi,
    )
    from python.gerekce import strateji_adi
    from web import grafik

    calisma_id = istek.query_params.get("calisma") or _son_calisma()
    conn = _baglanti()
    try:
        # SANATÇI düzeyinde (bkz. `sanatci_duzeyi`) ve TÜM çalışmalar: kararlar
        # kümeleme çalışmasına değil kullanıcının zevkine ait.
        veri = sanatci_duzeyi(kararlar(conn))
        isabet = strateji_isabeti(veri) if not veri.empty else pd.DataFrame()
        if isabet.empty:
            return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
                istek, mesaj=t("Henüz geri bildirim yok. Keşfet'te kaydırdıkça ya da "
                               "Öneriler'de karar verdikçe bu ekran dolar.",
                               "No feedback yet. This page fills up as you swipe in "
                               "Discover or decide on Recommendations.")))

        kesif = grafik.aralik([
            (strateji_adi(r["strateji"]), r["kesif_orani"], r["kesif_alt"], r["kesif_ust"],
             t(f"{strateji_adi(r['strateji'])}: {r['toplam']} karar, "
               f"{r['zaten_biliyorum']} tanesi «zaten biliyorum»",
               f"{strateji_adi(r['strateji'])}: {r['toplam']} decisions, "
               f"{r['zaten_biliyorum']} \"already know it\""))
            for _, r in isabet.iterrows()])
        zevkli = isabet[isabet["zevk_n"] > 0]
        zevk = grafik.aralik([
            (strateji_adi(r["strateji"]), r["zevk_isabeti"], r["zevk_alt"], r["zevk_ust"],
             t(f"{strateji_adi(r['strateji'])}: {r['begendim']} beğendim / {r['tutmadi']} tutmadı",
               f"{strateji_adi(r['strateji'])}: {r['begendim']} liked / {r['tutmadi']} passed"))
            for _, r in zevkli.iterrows()]) if not zevkli.empty else None

        return SABLONLAR.TemplateResponse(istek, "ogrenme.html", _ortam(
            istek, cumleler=ozet_cumleleri(isabet), isabet=isabet,
            g_kesif=kesif, g_zevk=zevk,
            # Uzaklık eksen merkezine göre ve merkez ÇALIŞMAYA bağlı: yalnız
            # etkin çalışmanın kararları.
            uzaklik=uzaklik_tercihi(conn, sanatci_duzeyi(kararlar(conn, calisma_id)), calisma_id)
            if calisma_id else pd.DataFrame(),
            strateji_adi=strateji_adi,
            karar_sayisi=veri["aday_id"].nunique(), satir=len(veri),
        ))
    finally:
        conn.close()


@_sureli(1200)
def _muzisyen_verisi_onbellek(kullanici_id: int | None):
    from python.muzisyen import muzisyen_verisi
    return _baglantiyla(muzisyen_verisi, None)


def _olcu_cubuklari(kendi, profiller, sutunlar) -> list[dict]:
    """Her ölçüt için kişinin değeri, kütüphanenin p5–p95 aralığında konumu.

    Ham sayı ("zil payı 0,41") tek başına bir şey söylemiyor; kütüphanedeki
    müzisyenlerin arasında NEREDE durduğu söylüyor (K13: norm uydurulmuyor,
    referans bu kütüphanenin kendisi).
    """
    from python.sozluk import terim

    cubuklar = []
    for s in sutunlar:
        if s not in kendi.index or kendi[s] != kendi[s] or s not in profiller.columns:
            continue
        seri = profiller[s].astype(float).dropna()
        if len(seri) < 5:
            continue
        alt, ust, med = seri.quantile(0.05), seri.quantile(0.95), seri.median()
        aralik = max(ust - alt, 1e-9)
        konum = lambda x: max(0.0, min(1.0, (float(x) - alt) / aralik))  # noqa: E731
        tanim = terim(s) or {}
        cubuklar.append({
            "sutun": s, "ad": tanim.get("ad") or s.replace("_", " "),
            "ipucu": tanim.get("kisa", ""), "deger": float(kendi[s]),
            "konum": konum(kendi[s]), "medyan": konum(med),
        })
    return cubuklar


def muzisyenler(istek):
    """Müzisyenler — rol çipleri, kişi listesi, seçilen kişinin icra profili,
    benzer icracılar ve "bu müzisyen gibi çalan, sende olmayan albümler".

    SYNC: müzisyen verisi pandas ağırlıklı; iş parçacığında koşar.
    """
    from python.enrich.icra_profili import ROL_STEM
    from python.muzisyen import (
        ROL_SUTUNLARI, benzer_icracilar, enstruman_rolleri, muzisyene_benzeyen_adaylar,
        rol_listesi,
    )

    kullanici_id = AKTIF_KULLANICI.get()
    veri = _muzisyen_verisi_onbellek(kullanici_id)
    if veri.profil.empty:
        return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
            istek, mesaj=t("Henüz kredi verisi yok. Çalıştırmak için: ",
                           "No credit data yet. To fetch it: ")
            + "<code>python -m python.enrich.krediler</code>"))

    # Yalnız enstrüman kanalı olan roller: akordeon ya da banjo için ayrılmış
    # bir kanal yok ve profil çıkamıyordu (çip tıklanınca boş sayfa). Ana
    # enstrümanlar önde.
    ONCELIK = ("drums", "bass", "guitar", "keyboards", "piano", "vocals",
               "synthesizer", "saxophone", "organ", "percussion", "backing_vocals")
    roller = sorted((r for r in enstruman_rolleri(veri) if r in ROL_STEM),
                    key=lambda r: ONCELIK.index(r) if r in ONCELIK else len(ONCELIK))
    if not roller:
        return SABLONLAR.TemplateResponse(istek, "bos.html", _ortam(
            istek, mesaj=t("Enstrüman kredisi yok.", "No instrument credits yet.")))
    rol = istek.query_params.get("rol")
    if rol not in roller:
        rol = "drums" if "drums" in roller else roller[0]
    liste = rol_listesi(veri, rol, adet=300)
    secim = istek.query_params.get("kisi")
    if secim not in liste.index and len(liste):
        secim = liste.index[0]

    profiller = _icra_profilleri_onbellek(kullanici_id, rol)
    try:
        agirlik = min(1.0, max(0.0, float(istek.query_params.get("agirlik", 0.7))))
    except ValueError:
        agirlik = 0.7
    sutunlar = [c for c in ROL_SUTUNLARI.get(rol, ())][:6]
    benzer, temel, kendi, cubuklar = pd.DataFrame(), "", None, []
    adaylar, havuz = pd.DataFrame(), 0
    if secim is not None and not profiller.empty and secim in profiller.index:
        kendi = profiller.loc[secim]
        benzer, temel = benzer_icracilar(
            veri, profiller, secim, rol=rol, adet=6, icra_agirligi=agirlik)
        cubuklar = _olcu_cubuklari(kendi, profiller, sutunlar)
        conn = _baglanti()
        try:
            adaylar, havuz = muzisyene_benzeyen_adaylar(conn, profiller, secim, rol, adet=6)
            if not adaylar.empty:
                kapak = {r[0]: r[1] for r in conn.execute(
                    f"SELECT aday_id, kapak FROM medya WHERE aday_id IN "
                    f"({','.join('?' * len(adaylar))})", list(adaylar["aday_id"]))}
                adaylar["kapak"] = adaylar["aday_id"].map(kapak)
        finally:
            conn.close()

    albumleri = veri.albumleri[veri.albumleri["kisi"] == secim] if secim else pd.DataFrame()
    return SABLONLAR.TemplateResponse(istek, "muzisyenler.html", _ortam(
        istek, roller=roller, rol=rol, stem=ROL_STEM.get(rol),
        liste=liste.head(80), secim=secim,
        kisi_adi=veri.profil.loc[secim, "kisi"] if secim in veri.profil.index else "",
        profil=veri.profil.loc[secim] if secim in veri.profil.index else None,
        kendi=kendi, cubuklar=cubuklar, sutunlar=sutunlar,
        benzer=benzer, temel=temel, agirlik=agirlik,
        adaylar=adaylar, havuz=havuz,
        albumleri=albumleri.groupby(["artist", "title", "year"])["role"]
        .apply(lambda r: ", ".join(sorted(set(r)))).reset_index()
        if not albumleri.empty else pd.DataFrame(),
    ))


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
            adaylar, hata = [], t("önbellekte yok, «ağdan ara»yı aç", "not in the cache; turn on \"search online\"")
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
    """Elle MBID kararı. Değer `mbid_coz`dan geçer — barkod çözülür, bozuk
    biçim REDDEDİLİR (bozuk MBID her kredi turunu düşürüyordu, bkz. orada)."""
    from python.enrich.mbid_eslestir import mbid_coz
    from python.onbellek import musicbrainz

    veri = await istek.json()
    album_id, mbid = veri.get("album_id"), veri.get("mbid")
    if mbid != "__yok__":
        mbid = mbid_coz(musicbrainz(), str(mbid or ""))
        if mbid is None:
            return JSONResponse({"hata": t("MBID ya da çözülebilir bir barkod değil", "not an MBID or a resolvable barcode")},
                                status_code=400)
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
    from python.sozluk import _kaynak

    gruplar = {
        t("Ölçümler: ayrılmış kanallardan", "Measurements: from separated stems"): [
            "stem", "izgara_entropi", "tekme_payi", "trampet_payi", "zil_payi",
            "nota_vurus", "harmonik_pay", "perde_medyan", "perde_araligi",
            "vibrato_hizi", "sustain_orani", "parlaklik", "dinamik_db",
            "enerji_payi",
        ],
        t("Kümeleme ve profil", "Clustering and profile"): [
            "eksen", "uyelik", "stabilite", "ses_uzakligi", "icra_profili",
            "yayilim",
        ],
        t("Öneri kaynakları", "Recommendation sources"): [
            "kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik",
            "liste_birlikteligi", "pmi",
        ],
        t("Ölçüm ve geri bildirim", "Evaluation and feedback"): [
            "loao", "tavan", "yuzdelik", "melez", "kesif_orani", "zevk_isabeti", "wilson"],
    }
    return SABLONLAR.TemplateResponse(istek, "sozluk.html", _ortam(
        istek, gruplar=gruplar, sozluk=_kaynak()))


def tarzlar_sayfasi(istek):
    """Tarzlarını adlandır, sonra birini besle — sistemin çekirdek adımı."""
    calisma_id = _calisma_sec(istek)
    if not calisma_id:
        return RedirectResponse("/basla", status_code=303)
    conn = _baglanti()
    try:
        kumeler = conn.execute(
            "SELECT kume_id, kullanici_adi FROM clusters WHERE calisma_id = ? AND stabil_mi = 1 "
            "ORDER BY kume_id", (calisma_id,)).fetchall()
        boyut = dict(conn.execute(
            """SELECT kume_id, COUNT(*) FROM (
                 SELECT album_id, kume_id, MAX(uyelik) FROM memberships
                  WHERE calisma_id = ? GROUP BY album_id) GROUP BY kume_id""",
            (calisma_id,)).fetchall())
        tarzlar = []
        for k in kumeler:
            albumler = [dict(r) for r in conn.execute(
                """SELECT a.artist, a.title FROM temsilciler t JOIN albums a USING (album_id)
                    WHERE t.calisma_id = ? AND t.kume_id = ? ORDER BY t.sira LIMIT 5""",
                (calisma_id, k["kume_id"]))]
            # Ad önerisi: temsilcilerin en sık MusicBrainz etiketi. Yalnız ipucu;
            # ad kullanıcının (sistem küme adı UYDURMAZ, K2).
            oneri = conn.execute(
                """SELECT tag FROM tags WHERE album_id IN (
                     SELECT album_id FROM temsilciler WHERE calisma_id = ? AND kume_id = ?)
                   GROUP BY tag ORDER BY COUNT(*) DESC LIMIT 1""",
                (calisma_id, k["kume_id"])).fetchone()
            tarzlar.append({"kume_id": k["kume_id"], "ad": k["kullanici_adi"],
                            "album": boyut.get(k["kume_id"], 0), "albumler": albumler,
                            "oneri": oneri[0] if oneri else ""})
    finally:
        conn.close()
    tarzlar.sort(key=lambda k: -k["album"])
    return SABLONLAR.TemplateResponse(istek, "tarzlar.html", _ortam(
        istek, tarzlar=tarzlar, ilk=istek.query_params.get("ilk") == "1",
        bos_var=any(not k["ad"] for k in tarzlar)))


async def tarz_otomatik(istek):
    """Adı boş tarzlara ilgili ad öner (kullanıcının verdiği adlara dokunmaz)."""
    from python.tarz_adi import bos_olanlari_adlandir

    veri = await istek.form()
    calisma_id = _calisma_sec(istek, {"calisma_id": veri.get("calisma_id")})
    if calisma_id:
        conn = _baglanti()
        try:
            bos_olanlari_adlandir(conn, calisma_id)
        finally:
            conn.close()
        _eksen_adlari.cache_clear()
    return RedirectResponse(f"/tarzlar?calisma={calisma_id or ''}", status_code=303)


def sen_sayfasi(istek):
    """«Sen»: düz dille portre (bkz. python/sen.py)."""
    from python.sen import eksen_adi, onyil_adi, ozet_cumlesi, portre

    calisma_id = _calisma_sec(istek)
    conn = _baglanti()
    try:
        p = portre(conn, calisma_id)
    finally:
        conn.close()
    if not p["album"]:
        return RedirectResponse("/basla", status_code=303)
    etiketler = [{"ad": eksen_adi(e), "adres": f"/kesfet?eksen={e['kume']}"}
                 for e in p["eksenler"][:3]]
    etiketler += [{"ad": x["etiket"], "adres": f"/etiketler?etiket={x['etiket']}"}
                  for x in p["turler"][:3]]
    if p["donem"]:
        etiketler.append({"ad": onyil_adi(p["donem"]["onyil"]), "adres": "#donem"})
    gorulen: set[str] = set()
    etiketler = [e for e in etiketler
                 if not (e["ad"].casefold() in gorulen or gorulen.add(e["ad"].casefold()))]
    return SABLONLAR.TemplateResponse(istek, "sen.html", _ortam(
        istek, p=p, ozet=ozet_cumlesi(p), etiketler=etiketler,
        eksen_adi=eksen_adi, onyil_adi=onyil_adi))


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
                istek, mesaj=t("Henüz etiket yok. Üretmek için: ", "No tags yet. To build them: ")
                + "<code>python -m python.etiket</code>"))

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
                istek, mesaj=t("Henüz ses kümesi yok. Önce ", "No sound clusters yet. First run ")
                + "<code>python -m python.etiket_clap --gomu</code>" + t(", sonra ", ", then ")
                + "<code>python -m python.ses_kume</code>"))

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
        return JSONResponse({"hata": t("önizleme yok", "no preview")}, status_code=404)
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
        yol = istek.url.path
        # Statik dosya ve servis çalışanı kimlik istemiyor; oturum çözmek
        # (paylaşılan veritabanında bir sorgu) her ikon ve CSS isteğinde boşa
        # gidiyordu.
        if yol.startswith("/statik/") or yol == "/sw.js":
            return _guvenlik_basliklari(await sonraki(istek))

        jeton = istek.cookies.get(CEREZ_ADI)
        conn = _oturum_baglantisi()
        try:
            kullanici_id = oturum_coz(conn, jeton)
        finally:
            conn.close()

        # Dil: çerez, yoksa tarayıcının tercihi (bkz. python/dil.py). Bağlam
        # değişkeninde — kullanıcı gibi — ki cümle üreten `python/` işlevleri
        # imza değiştirmeden iki dilde konuşsun.
        dil_belirtec = AKTIF_DIL.set(istekten_dil(
            istek.cookies.get(DIL_CEREZI), istek.headers.get("accept-language")))
        belirtec = AKTIF_KULLANICI.set(kullanici_id)
        try:
            acik = any(yol == a or yol.startswith(a + "/") for a in ACIK_YOLLAR)
            if kullanici_id is None and not acik:
                if yol.startswith("/api/"):
                    # Fetch çağrısı yönlendirmeyi izleyip giriş sayfasının
                    # HTML'ini JSON diye okumaya çalışıyordu; açık bir 401
                    # istemcinin "oturum düştü" diyebilmesini sağlıyor.
                    return _guvenlik_basliklari(
                        JSONResponse({"hata": t("oturum yok", "not signed in")}, status_code=401))
                return RedirectResponse("/giris", status_code=303)
            yanit = await sonraki(istek)
            yanit.headers.setdefault("Content-Language", etkin_dil())
            yanit.headers.setdefault("Vary", "Cookie, Accept-Language")
            return _guvenlik_basliklari(yanit)
        finally:
            AKTIF_KULLANICI.reset(belirtec)
            AKTIF_DIL.reset(dil_belirtec)


#: İçerik güvenliği. Betik ve stil yalnız kendi kökenimizden (satır içi
#: `onchange="this.form.submit()"` kalıpları için 'unsafe-inline' — dış betik
#: yine yasak). Görsel ve ses yalnız kullandığımız CDN'lerden: Deezer
#: (dzcdn.net), iTunes (apple.com / mzstatic.com), Cover Art Archive.
#: `frame-ancestors 'none'`: uygulama başka bir sayfaya çerçevelenemez.
ICERIK_POLITIKASI = "; ".join((
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https://*.dzcdn.net https://*.mzstatic.com "
    "https://coverartarchive.org https://*.archive.org",
    "media-src 'self' https://*.dzcdn.net https://*.apple.com https://*.mzstatic.com",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self' https://accounts.spotify.com",
))


def _guvenlik_basliklari(yanit):
    b = yanit.headers
    b.setdefault("X-Content-Type-Options", "nosniff")
    b.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    b.setdefault("X-Frame-Options", "DENY")
    b.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if "text/html" in b.get("content-type", ""):
        b.setdefault("Content-Security-Policy", ICERIK_POLITIKASI)
    return yanit


def _cerez_koy(yanit, jeton: str):
    """Oturum çerezi. `httponly` betiklerden okunmasını engeller; `samesite`
    başka sitelerin bu uygulamaya kimlikli istek attırmasını (CSRF) zorlaştırır.
    `secure` bayrağı `HTTPS_ARKASINDA` (ortam: KESIF_HTTPS) ile açılıyor;
    yerelde http olduğu için varsayılanı kapalı, açık olsaydı çerez hiç
    gönderilmez ve giriş sessizce çalışmazdı."""
    yanit.set_cookie(CEREZ_ADI, jeton, max_age=OTURUM_GUN * 86400,
                     httponly=True, samesite="lax", path="/",
                     secure=HTTPS_ARKASINDA)
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


def _istemci_ip(istek) -> str:
    """İstemci adresi. Ters vekil arkasındaysa X-Forwarded-For'un İLK girdisi.

    Zincirin sonraki girdileri istemci tarafından uydurulabilir; yalnız en
    soldaki, bizim vekilimizin gördüğü adrestir — ve o da ancak GÜVENDİĞİMİZ
    bir vekil arkasındaysak anlamlı. Doğrudan açık bir sunucuda bu başlık hiç
    okunmamalı; `GUVENILIR_VEKIL` onu denetliyor.
    """
    if GUVENILIR_VEKIL:
        iletilen = istek.headers.get("x-forwarded-for", "")
        if iletilen:
            return iletilen.split(",")[0].strip()
    return istek.client.host if istek.client else "?"


async def giris_gonder(istek):
    veri = await istek.form()
    eposta = (veri.get("eposta") or "").strip().lower()
    parola = veri.get("parola") or ""

    # HEM IP HEM HESAP sayılıyor: yalnız IP sayılırsa dağıtık deneme kaçar,
    # yalnız hesap sayılırsa saldırgan hesapları sırayla deneyip her birinde
    # sınırın altında kalır.
    ip = _istemci_ip(istek)
    # Yerel tünel (Tailscale Funnel) ardında her istek 127.0.0.1'den gelir ve
    # iletilen adres başlığı gelmeyebilir: IP sayacı o zaman BÜTÜN kullanıcıları
    # tek kişi sayıp herkesi kilitlerdi. Döngü adresinde yalnız hesap sayılır.
    yerel = ip in ("127.0.0.1", "::1", "localhost")
    anahtarlar = ([] if yerel else [f"ip:{ip}"]) + [f"hesap:{eposta}"]
    for anahtar in anahtarlar:
        kalan = kilitli_mi(anahtar)
        if kalan:
            return RedirectResponse(f"/giris?hata=kilit&sn={kalan}",
                                    status_code=303)

    conn = _oturum_baglantisi()
    try:
        kullanici_id = giris_dogrula(conn, eposta, parola)
        if kullanici_id is None:
            for anahtar in anahtarlar:
                deneme_kaydet(anahtar)
            # Tek mesaj: "kullanıcı yok" ile "parola yanlış" ayrımı hangi
            # e-postaların kayıtlı olduğunu ele verir.
            return RedirectResponse("/giris?hata=1", status_code=303)
        for anahtar in anahtarlar:
            denemeleri_sifirla(anahtar)
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


async def gizlilik(istek):
    """Ne saklanıyor, ne dışarı gidiyor, nasıl silinir — oturumsuz da açık.

    İletişim adresi `KESIF_ILETISIM` ortam değişkeninden; yayını yapan kişinin
    adresi koda gömülmez.
    """
    return SABLONLAR.TemplateResponse(istek, "gizlilik.html", {
        "request": istek, "yol": "/gizlilik",
        "giris_var": AKTIF_KULLANICI.get() is not None,
        "iletisim": os.environ.get("KESIF_ILETISIM", "").strip(),
    })


async def hesap_sil_istek(istek):
    """Hesabı ve kişisel veriyi sil (bkz. `hesap.hesap_sil`).

    Onay kutusu şart; çapraz site POST'u `samesite=lax` çerez zaten taşımaz.
    """
    from python.hesap import hesap_sil

    veri = await istek.form()
    if veri.get("onay") != "evet":
        return RedirectResponse("/gizlilik", status_code=303)
    kullanici_id = AKTIF_KULLANICI.get()
    conn = _oturum_baglantisi()
    try:
        hesap_sil(conn, kullanici_id)
    finally:
        conn.close()
    _onbellekleri_bosalt()
    yanit = RedirectResponse("/giris?hata=silindi", status_code=303)
    yanit.delete_cookie(CEREZ_ADI, path="/")
    return yanit


async def dil_degistir(istek):
    """Dili değiştir ve geldiğin sayfaya dön. Seçim çerezde, bir yıl.

    Dönüş adresi YALNIZ yerel bir yol olabilir ("/..." ama "//..." değil):
    aksi hâlde bu uç, başka bir siteye yönlendiren açık bir kapı olurdu.
    """
    kod = istek.path_params["kod"]
    if kod not in DILLER:
        kod = "tr"
    geri = istek.query_params.get("geri") or "/"
    if not geri.startswith("/") or geri.startswith("//"):
        geri = "/"
    yanit = RedirectResponse(geri, status_code=303)
    yanit.set_cookie(DIL_CEREZI, kod, max_age=365 * 86400, samesite="lax",
                     path="/", secure=HTTPS_ARKASINDA)
    return yanit


async def saglik(istek):
    """Canlılık denetimi — süreç ayakta VE paylaşılan veritabanı okunuyor.

    Yalnız "ayakta" dönmek, veritabanı kilitli ya da diski dolmuşken de
    "sağlıklı" demekti; launchd/izleyici bunu göremezdi.
    """
    try:
        conn = _oturum_baglantisi()
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as hata:
        return JSONResponse({"durum": "veritabani", "hata": str(hata)}, status_code=503)
    from python import __version__
    return JSONResponse({"durum": "ayakta", "surum": __version__})


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
    from python.spotify import yapilandirildi_mi
    return yapilandirildi_mi()


async def spotify_baslat(istek):
    """Kullanıcıyı Spotify'ın yetki sayfasına gönder."""
    from python.spotify import SpotifyHatasi, yetki_baslat
    try:
        url, _ = yetki_baslat()
    except SpotifyHatasi:
        return RedirectResponse("/giris?hata=spotify_yok", status_code=303)
    # 303 değil 302: Spotify'a giden bu yönlendirme bir form sonucu değil.
    return RedirectResponse(url, status_code=302)


def _spotify_aktarimini_baslat(kullanici_id: int) -> None:
    """Spotify bağlanan ve henüz önerisi olmayan kullanıcı için aktarımı
    KENDİLİĞİNDEN başlat. Spotify geçmişi elimizdeyken kullanıcıya sanatçı
    listesi sormanın ya da ayrıca "aktar" düğmesine bastırmanın anlamı yok
    (kullanıcı geri bildirimi, 2026-09-28)."""
    conn = baglan_kullanici(kullanici_id)
    try:
        aday = conn.execute("SELECT COUNT(*) FROM adaylar").fetchone()[0]
    finally:
        conn.close()
    if not aday:
        _aktarim_baslat(kullanici_id)


async def spotify_donus(istek):
    """Spotify'dan dönüş — hesabı bul, bağla ya da aç, oturumu başlat.

    Dört durum var ve sıralamaları önemli:

    1. **Zaten girişli** → Spotify kimliğini bu hesaba bağla (`/basla`'daki
       "Spotify hesabını bağla" düğmesi buraya düşüyor).
    2. **Bu Spotify kimliği kayıtlı** → o hesaba gir.
    3. **E-posta kayıtlı** → hesapları ikizlemek yerine Spotify'ı ona bağla.
       Varsayım: Spotify e-postayı doğrulamış oluyor. Doğrulanmamış bir
       e-posta ile hesap ele geçirilebilirdi; beş kullanıcılık kişisel bir
       uygulamada bu kabul edilen risk, açık uçlu bir serviste olmazdı.
    4. **Hiçbiri** → yeni hesap (beş kullanıcı sınırına takılmıyorsa).
    """
    from python.hesap import spotify_bagla
    from requests import RequestException

    from python.spotify import SpotifyHatasi, ben, durum_gecerli_mi, jeton_al

    if istek.query_params.get("error"):
        # Kullanıcı "Agree" yerine "Cancel" dedi — hata değil, karar.
        return RedirectResponse("/giris?hata=spotify_iptal", status_code=303)

    if not durum_gecerli_mi(istek.query_params.get("state")):
        # CSRF ya da çok beklemiş sekme. İkisini ayırmıyoruz: saldırgana
        # hangisine takıldığını söylemenin faydası yok.
        return RedirectResponse("/giris?hata=spotify_durum", status_code=303)

    kod = istek.query_params.get("code")
    if not kod:
        return RedirectResponse("/giris?hata=spotify", status_code=303)

    try:
        jetonlar = jeton_al(kod)
        kimlik = ben(jetonlar["access_token"])
    except (SpotifyHatasi, KeyError, RequestException) as hata:
        # Gövde kullanıcıya GÖSTERİLMİYOR: jeton taşımasa da istemciye
        # sunucu içi ayrıntı sızdırmanın faydası yok.
        print(f"[spotify] {type(hata).__name__}: {hata}")
        return RedirectResponse("/giris?hata=spotify", status_code=303)

    if not kimlik["spotify_id"]:
        return RedirectResponse("/giris?hata=spotify", status_code=303)

    yenile = jetonlar.get("refresh_token")
    mevcut = AKTIF_KULLANICI.get()
    conn = _oturum_baglantisi()
    try:
        if mevcut is not None:                                  # 1
            baskasinda = kullanici_bul(conn, spotify_id=kimlik["spotify_id"])
            if baskasinda is not None and baskasinda["kullanici_id"] != mevcut:
                return RedirectResponse("/basla?hata=spotify_baskasinda",
                                        status_code=303)
            spotify_bagla(conn, mevcut, kimlik["spotify_id"], yenile)
            _spotify_aktarimini_baslat(mevcut)
            return RedirectResponse("/basla?spotify=bagli", status_code=303)

        kullanici = kullanici_bul(conn, spotify_id=kimlik["spotify_id"])   # 2
        if kullanici is None and kimlik["eposta"]:                        # 3
            kullanici = kullanici_bul(conn, eposta=kimlik["eposta"])
            if kullanici is not None:
                spotify_bagla(conn, kullanici["kullanici_id"],
                              kimlik["spotify_id"], yenile)

        if kullanici is not None:
            kullanici_id = kullanici["kullanici_id"]
            if yenile:
                spotify_bagla(conn, kullanici_id, kimlik["spotify_id"], yenile)
            hedef = "/kesfet"
        else:                                                              # 4
            if kullanici_sayisi(conn) >= AZAMI_KULLANICI:
                return RedirectResponse("/giris?hata=dolu", status_code=303)
            kullanici_id = kullanici_olustur(
                conn, kimlik["ad"], eposta=kimlik["eposta"],
                spotify_id=kimlik["spotify_id"], spotify_yenile=yenile)
            hedef = "/basla"
        jeton = oturum_ac(conn, kullanici_id)
    finally:
        conn.close()
    _spotify_aktarimini_baslat(kullanici_id)
    return _cerez_koy(RedirectResponse(hedef, status_code=303), jeton)


def _aktarim_bitti_mi(kullanici_id: int | None) -> dict | None:
    """Aktarım durumu; bittiyse kullanıcı önbelleklerini boşalt.

    Aktarım AYRI BİR SÜREÇTE yazıyor, dolayısıyla sunucunun `lru_cache`'leri
    yeni çalışmayı görmez: aktarım sürerken bir kez "çalışma yok" önbelleğe
    girer ve sunucu yeniden başlayana kadar öyle kalırdı.
    """
    from python.aktarim import durum_oku

    if kullanici_id is None:
        return None
    durum = durum_oku(kullanici_id)
    if durum and durum.get("durum") == "bitti":
        _onbellekleri_bosalt()
    return durum


async def basla(istek):
    """Karşılama — kütüphanesi boş ya da aktarılmakta olan kullanıcı için.

    Boş bir öneri sayfasına düşmek "uygulama bozuk" hissi veriyor. Burada ne
    olduğu ve sıradaki adımın ne olduğu yazılı.

    Yönlendirme ölçütü ALBÜM değil ADAY: aktarım albümleri ilk dakikada
    yazıyor ama öneri ancak son aşamada çıkıyor. Albüm sayısına bakılsaydı
    kullanıcı yarım bir hattın boş öneri sayfasına atılırdı.
    """
    return _basla_yaniti(istek, hata=istek.query_params.get("hata"))


def _basla_yaniti(istek, *, hata: str | None = None, liste_metni: str = "",
                  durum_kodu: int = 200):
    from python.aktarim import (
        ASAMA_ADI, ASAMALAR, ASGARI_ALBUM, LISTE_SANATCI_ALBUM, calisiyor_mu,
    )

    kullanici_id = AKTIF_KULLANICI.get()
    durum = _aktarim_bitti_mi(kullanici_id)
    calisiyor = calisiyor_mu(kullanici_id) if kullanici_id is not None else False
    conn = _baglanti()
    try:
        albom = conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
        aday = conn.execute("SELECT COUNT(*) FROM adaylar").fetchone()[0]
        kullanici = conn.execute(
            "SELECT ad, spotify_id FROM kullanici WHERE kullanici_id = ?",
            (kullanici_id,)).fetchone()
    finally:
        conn.close()
    # Keşfet çalışma (kümeleme) ister; yalnız aday sayısına bakılırsa aday
    # olup çalışması olmayan hesap /basla ↔ /kesfet arasında döngüye giriyordu.
    if aday and not calisiyor and _son_calisma():
        # Önce tarzlarını adlandırsın: sistemin çekirdek adımı. Hiç ad yoksa
        # oraya, varsa doğrudan desteye.
        conn = _baglanti()
        try:
            adli = conn.execute(
                "SELECT COUNT(*) FROM clusters WHERE calisma_id = ? "
                "AND COALESCE(kullanici_adi, '') != ''", (_son_calisma(),)).fetchone()[0]
        finally:
            conn.close()
        if adli:
            return RedirectResponse("/kesfet", status_code=303)
        # Hiç ad yok: ilgili adları öner ve yaz, sonra kullanıcı görsün/düzeltsin.
        from python.tarz_adi import bos_olanlari_adlandir
        conn = _baglanti()
        try:
            bos_olanlari_adlandir(conn, _son_calisma())
        finally:
            conn.close()
        _eksen_adlari.cache_clear()
        return RedirectResponse("/tarzlar?ilk=1", status_code=303)

    # Durum dosyası "çalışıyor" diyor ama süreç yok: öldürülmüş ya da çökmüş.
    if durum and durum.get("durum") == "calisiyor" and not calisiyor:
        durum = {**durum, "durum": "hata",
                 "hata": t("aktarım yarıda kesildi (süreç artık çalışmıyor)", "the import was cut short (the process is no longer running)")}
    asama = (durum or {}).get("asama")
    asamalar = [(a, ASAMA_ADI[a]) for a in ASAMALAR]
    if durum and durum.get("kaynak") == "liste":
        # Listeyle gelen kullanıcı Spotify aşamasını hiç görmemeli.
        asamalar = [(a, ad_) for a, ad_ in asamalar if a != "spotify"]
    sira = [a for a, _ in asamalar]
    return SABLONLAR.TemplateResponse(istek, "basla.html", {
        "request": istek, "yol": "/basla",
        "ad": kullanici["ad"] if kullanici else "",
        "spotify_bagli": bool(kullanici and kullanici["spotify_id"]),
        "spotify_hazir": _spotify_hazir(),
        "hata": hata,
        "bagli_yeni": istek.query_params.get("spotify") == "bagli",
        "albom": albom,
        "aktarim": durum,
        "calisiyor": calisiyor,
        "asamalar": asamalar,
        "asama_sira": sira.index(asama) if asama in sira else -1,
        "liste_metni": liste_metni,
        "asgari_sanatci": -(-ASGARI_ALBUM // LISTE_SANATCI_ALBUM),
    }, status_code=durum_kodu)


def _calisan_aktarim_sayisi() -> int:
    """Şu an yaşayan aktarım süreçleri (bütün kullanıcılar)."""
    import python.db as _db
    from python.aktarim import calisiyor_mu

    sayi = 0
    for yol in _db.KULLANICI_KOK.glob("*.aktarim.json"):
        kimlik = yol.name.split(".", 1)[0]
        if kimlik.isdigit() and calisiyor_mu(int(kimlik)):
            sayi += 1
    return sayi


def _aktarim_baslat(kullanici_id: int, ek: list[str] | None = None, *,
                   kaynak: str = "spotify") -> str | None:
    """Aktarımı AYRI SÜREÇTE başlat; başlatılamazsa hata kodu döner.

    Ayrı süreç çünkü CLAP (torch) ~2 GB bellek istiyor ve sunucuya yüklenirse
    her kullanıcının isteği o süreçle yarışır; ayrıca aktarım dakikalar
    sürer ve istek zaman aşımına uğrardı. İkinci tıklama ikinci süreç
    açmaz — `calisiyor_mu` süreç kimliğini denetliyor.
    """
    import subprocess

    import python.db as _db
    from python.aktarim import baslangic_yaz, calisiyor_mu

    if calisiyor_mu(kullanici_id):
        return None
    if _calisan_aktarim_sayisi() >= AZAMI_ES_ZAMANLI_AKTARIM:
        return "mesgul"
    _db.KULLANICI_KOK.mkdir(parents=True, exist_ok=True)
    gunluk = open(_db.KULLANICI_KOK / f"{kullanici_id}.aktarim.log", "ab")
    surec = subprocess.Popen(
        [sys.executable, "-m", "python.aktarim", "--kullanici", str(kullanici_id),
         *(ek or [])],
        cwd=str(KOK.parent), stdout=gunluk, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, start_new_session=True,
    )
    gunluk.close()
    baslangic_yaz(kullanici_id, surec.pid, kaynak)
    return None


async def aktar(istek):
    """Spotify aktarımını başlat (bkz. `_aktarim_baslat`)."""
    kullanici_id = AKTIF_KULLANICI.get()
    conn = _oturum_baglantisi()
    try:
        kayit = kullanici_bul(conn, kullanici_id=kullanici_id)
    finally:
        conn.close()
    if kayit is None or not kayit["spotify_yenile"]:
        return RedirectResponse("/basla?hata=spotify_yok", status_code=303)
    hata = _aktarim_baslat(kullanici_id)
    return RedirectResponse(f"/basla?hata={hata}" if hata else "/basla", status_code=303)


async def aktar_liste(istek):
    """Spotify'sız başlangıç: elle yazılmış sanatçı / albüm listesi.

    Liste kullanıcının dosyasına JSON olarak yazılır ve aynı hat `--json`
    ile başlar. Kümelemeye yetmeyecek kısa liste süreç açılmadan, metin
    korunarak geri çevrilir — kullanıcı yazdığını kaybetmesin.
    """
    import python.db as _db
    from python.aktarim import liste_ayristir, liste_yeterli_mi

    kullanici_id = AKTIF_KULLANICI.get()
    veri = await istek.form()
    metin = str(veri.get("liste") or "")[:20000]
    kayitlar, sanatcilar = liste_ayristir(metin)
    if not liste_yeterli_mi(kayitlar, sanatcilar):
        return _basla_yaniti(istek, hata="liste_kisa", liste_metni=metin,
                             durum_kodu=400)
    _db.KULLANICI_KOK.mkdir(parents=True, exist_ok=True)
    dosya = _db.KULLANICI_KOK / f"{kullanici_id}.liste.json"
    dosya.write_text(json.dumps(
        [{"sanatci": k["sanatci"], "album": k["album"], "kaynak": "liste"} for k in kayitlar]
        + [{"sanatci": s_} for s_ in sanatcilar], ensure_ascii=False), encoding="utf-8")
    hata = _aktarim_baslat(kullanici_id, ["--json", str(dosya.resolve())], kaynak="liste")
    if hata:
        return _basla_yaniti(istek, hata=hata, liste_metni=metin, durum_kodu=503)
    return RedirectResponse("/basla", status_code=303)


async def aktar_durum(istek):
    """İlerleme çubuğunun kaynağı. Günlük satırı DEĞİL yalnız özet döner."""
    from python.aktarim import calisiyor_mu

    kullanici_id = AKTIF_KULLANICI.get()
    durum = _aktarim_bitti_mi(kullanici_id) or {}
    return JSONResponse({
        "durum": durum.get("durum"), "asama": durum.get("asama"),
        "adim": durum.get("adim", 0), "toplam": durum.get("toplam", 0),
        "calisiyor": calisiyor_mu(kullanici_id), "hata": durum.get("hata"),
    })


# --------------------------------------------------------------------------- #
# Keşfet — kaydırmalı deste
# --------------------------------------------------------------------------- #

_KIMLIK = re.compile(r"^[0-9a-f]{8,40}$")


def _calisma_sec(istek, veri: dict | None = None) -> str | None:
    return ((veri or {}).get("calisma_id") or istek.query_params.get("calisma")
            or _son_calisma())


def kesfet_sayfa(istek):
    """Keşfet: kart kart dinle, kaydırarak karar ver.

    Sayfa kabuğu sunucuda çiziliyor (eksen çipleri, günlük özet); kartlar
    `/api/kesfet/deste`den parti parti geliyor. Böylece her kaydırma sayfa
    yenilemiyor ve çalan önizleme kesilmiyor — K15'in gerekçesi aynen.
    """
    calisma_id = _calisma_sec(istek)
    if not calisma_id:
        return RedirectResponse("/basla", status_code=303)
    conn = _baglanti()
    try:
        eksenler = kesif.eksenler(conn, calisma_id)
        gunluk = kesif.gunluk_ozet(conn)
        derinlik = kesif.mevcut_derinlik(conn, calisma_id)
    finally:
        conn.close()
    secili = istek.query_params.get("eksen")
    muzisyen = istek.query_params.get("muzisyen") or ""
    rol = istek.query_params.get("rol") or "drums"
    muzisyen_adi = ""
    if muzisyen:
        profiller = _icra_profilleri_onbellek(AKTIF_KULLANICI.get(), rol)
        if muzisyen in profiller.index and "kisi_adi" in profiller.columns:
            muzisyen_adi = str(profiller.loc[muzisyen, "kisi_adi"])
        else:
            muzisyen_adi = muzisyen
    return SABLONLAR.TemplateResponse(istek, "kesfet.html", _ortam(
        istek, eksenler=eksenler, gunluk=gunluk,
        muzisyen=muzisyen, muzisyen_adi=muzisyen_adi, rol=rol,
        secili_eksen=int(secili) if secili and secili.lstrip("-").isdigit() else None,
        kaynak=istek.query_params.get("kaynak") if istek.query_params.get("kaynak")
        in kesif.KAYNAKLAR else "ana",
        buyutulebilir=derinlik < kesif.BUYUTME_TAVANI and not muzisyen,
    ))


def api_deste(istek):
    """Sıradaki kart partisi. Her partide sıralama YENİDEN hesaplanır: az önce
    verilen kararlar `yakinlik_etkisi` ile bir sonraki partiye yansır."""
    q = istek.query_params
    calisma_id = _calisma_sec(istek)
    if not calisma_id:
        return JSONResponse({"kartlar": [], "kalan": 0, "toplam": 0})
    eksen = q.get("eksen")
    eksen = int(eksen) if eksen and eksen.lstrip("-").isdigit() else None
    try:
        adet = max(1, min(int(q.get("adet", 8)), 20))
    except ValueError:
        adet = 8
    haric = {k for k in (q.get("haric") or "").split(",") if _KIMLIK.match(k)}
    kullanici_id = AKTIF_KULLANICI.get()
    if q.get("muzisyen"):
        return _muzisyen_destesi_yaniti(q, calisma_id, adet, haric, kullanici_id)
    conn = _baglanti()
    try:
        sonuc = kesif.deste(
            conn, calisma_id, eksen=eksen, kaynak=q.get("kaynak", "ana"),
            adet=adet, haric=haric, etki=_yakinlik(conn, calisma_id),
            baglam=_baglam_onbellek(kullanici_id), olcum=_olcum_onbellek(kullanici_id),
            eksen_adlari=_eksen_adlari(calisma_id),
        )
    finally:
        conn.close()
    for kart in sonuc["kartlar"]:
        kart["yer_tutucu"] = str(yer_tutucu_svg(kart["artist"], kart["title"]))
    sonuc["calisma_id"] = calisma_id
    return JSONResponse(sonuc)


def _muzisyen_destesi_yaniti(q, calisma_id, adet, haric, kullanici_id):
    """«X gibi çalanlar» destesi (bkz. `kesif.muzisyen_destesi`)."""
    rol = q.get("rol") or "drums"
    profiller = _icra_profilleri_onbellek(kullanici_id, rol)
    conn = _baglanti()
    try:
        sonuc = kesif.muzisyen_destesi(conn, profiller, q["muzisyen"], rol,
                                       adet=adet, haric=haric)
    finally:
        conn.close()
    for kart in sonuc["kartlar"]:
        kart["yer_tutucu"] = str(yer_tutucu_svg(kart["artist"], kart["title"]))
    sonuc["calisma_id"] = calisma_id
    return JSONResponse(sonuc)


def api_medya(istek):
    """Kartın görseli + TAZE önizlemesi. İlk çağrıda Deezer'dan çözülür ve
    `medya` tablosuna yazılır; sonrakiler yalnız taze önizleme için bir çağrı."""
    from python.medya import medya_coz

    aday_id = istek.path_params["aday_id"]
    if not _KIMLIK.match(aday_id):
        return JSONResponse({"hata": t("geçersiz kimlik", "invalid id")}, status_code=400)
    conn = _baglanti()
    try:
        satir = conn.execute(
            "SELECT artist, title, MAX(parca_id) parca_id FROM adaylar "
            "WHERE aday_id = ? GROUP BY aday_id", (aday_id,)).fetchone()
        if satir is None:
            satir = conn.execute(
                "SELECT artist, title, parca_id FROM liste WHERE aday_id = ?",
                (aday_id,)).fetchone()
        if satir is None:
            return JSONResponse({"hata": "aday yok"}, status_code=404)
        sonuc = medya_coz(conn, {"aday_id": aday_id, **dict(satir)})
    finally:
        conn.close()
    return JSONResponse(sonuc)


async def api_kesfet_karar(istek):
    veri = await istek.json()
    karar, aday_id = veri.get("karar"), str(veri.get("aday_id") or "")
    if karar not in kesif.KARARLAR or not _KIMLIK.match(aday_id):
        return JSONResponse({"hata": t("geçersiz karar", "invalid decision")}, status_code=400)
    conn = _baglanti()
    try:
        sonuc = kesif.karar_kaydet(conn, _calisma_sec(istek, veri), aday_id, karar)
    except LookupError:
        return JSONResponse({"hata": t("aday bulunamadı", "pick not found")}, status_code=404)
    finally:
        conn.close()
    _boru_hatti.cache_clear()
    return JSONResponse(sonuc)


async def api_kesfet_geri_al(istek):
    veri = await istek.json()
    aday_id = str(veri.get("aday_id") or "")
    if not _KIMLIK.match(aday_id):
        return JSONResponse({"hata": t("geçersiz kimlik", "invalid id")}, status_code=400)
    conn = _baglanti()
    try:
        sonuc = kesif.karar_geri_al(conn, _calisma_sec(istek, veri), aday_id)
    finally:
        conn.close()
    _boru_hatti.cache_clear()
    return JSONResponse(sonuc)


#: Aynı kullanıcı için ikinci büyütme isteği birinciyi beklemez, reddedilir.
_BUYUYEN: set[int] = set()
_BUYUME_KILIDI = threading.Lock()


def api_buyut(istek):
    """Desteyi büyüt: ana stratejileri +20 sıra derine üret (tavan 50).

    Ayrı süreç DEĞİL (aktarımdan farklı): üç ana strateji yerel veriyle
    ~7 sn'de bitiyor (ölçüldü), torch yüklemiyor. İstek iş parçacığında
    bekler, istemci o sırada "kartlar hazırlanıyor" gösterir.
    """
    kullanici_id = AKTIF_KULLANICI.get()
    calisma_id = _calisma_sec(istek)
    if not calisma_id or kullanici_id is None:
        return JSONResponse({"durum": "yok"}, status_code=400)
    with _BUYUME_KILIDI:
        if kullanici_id in _BUYUYEN:
            return JSONResponse({"durum": "suruyor"}, status_code=409)
        _BUYUYEN.add(kullanici_id)
    try:
        conn = _baglanti()
        try:
            sonuc = kesif.desteyi_buyut(conn, calisma_id)
        finally:
            conn.close()
    except Exception as hata:          # üretim hatası kullanıcıya sade döner
        print(f"[buyut] {type(hata).__name__}: {hata}", file=sys.stderr)
        return JSONResponse({"durum": "hata"}, status_code=500)
    finally:
        with _BUYUME_KILIDI:
            _BUYUYEN.discard(kullanici_id)
    _onbellekleri_bosalt()      # CLAP havuzu ve sayaçlar yeni adayları görsün
    return JSONResponse(sonuc)


# --------------------------------------------------------------------------- #
# Listem
# --------------------------------------------------------------------------- #

def listem(istek):
    """Sağa kaydırılanlar: dinle, durumunu işaretle, nereden edineceğini gör,
    dışa aktar — ve listenin kendi dökümü."""
    durum = istek.query_params.get("durum")
    durum = durum if durum in kesif.DURUMLAR or durum == "kutuphanede" else None
    kullanici_id = AKTIF_KULLANICI.get()
    calisma_id = _son_calisma()
    conn = _baglanti()
    try:
        tumu = kesif.liste_ogeleri(conn)
        gunluk = kesif.gunluk_ozet(conn)
        etkinlik = kesif.etkinlik(conn, 21)
        isabet = (kesif.eksen_isabeti(conn, calisma_id, _eksen_adlari(calisma_id))
                  if calisma_id else [])
    finally:
        conn.close()
    if durum == "kutuphanede":
        ogeler = [o for o in tumu if o["kutuphanede"]]
    elif durum:
        ogeler = [o for o in tumu if o["durum"] == durum]
    else:
        ogeler = tumu
    analiz = kesif.liste_analizi(tumu, _baglam_onbellek(kullanici_id))
    en_cok = max([n for _, n in etkinlik] + [1])
    return SABLONLAR.TemplateResponse(istek, "listem.html", _ortam(
        istek, ogeler=ogeler, tumu_sayi=len(tumu), durum=durum, analiz=analiz,
        gunluk=gunluk, etkinlik=etkinlik, en_cok=en_cok, isabet=isabet,
        durumlar=kesif.DURUMLAR,
    ))


def listem_aktar(istek):
    bicim = istek.path_params["bicim"]
    if bicim not in ("csv", "txt", "json"):
        return JSONResponse({"hata": t("biçim csv, txt ya da json olmalı", "format must be csv, txt or json")}, status_code=404)
    durum = istek.query_params.get("durum")
    conn = _baglanti()
    try:
        ogeler = kesif.liste_ogeleri(conn, durum if durum in kesif.DURUMLAR else None)
    finally:
        conn.close()
    icerik, tur = kesif.disa_aktar(ogeler, bicim)
    ad = f"kesif-listem-{date.today().isoformat()}{'-' + durum if durum else ''}.{bicim}"
    return Response(icerik, media_type=tur,
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


async def api_liste_ekle(istek):
    """Bir adayı doğrudan listeye ekle (Müzisyenler sayfasındaki ♥).

    Destedeki sağa kaydırmayla AYNI kayıt: sanatçı düzeyinde «beğendim» +
    liste satırı. Adayın bulunduğu en yeni çalışma kullanılır.
    """
    veri = await istek.json()
    aday_id = str(veri.get("aday_id") or "")
    if not _KIMLIK.match(aday_id):
        return JSONResponse({"hata": t("geçersiz istek", "invalid request")}, status_code=400)
    conn = _baglanti()
    try:
        satir = conn.execute(
            "SELECT MAX(calisma_id) FROM adaylar WHERE aday_id = ?", (aday_id,)).fetchone()
        if not satir or not satir[0]:
            return JSONResponse({"hata": t("aday yok", "no such pick")}, status_code=404)
        sonuc = kesif.karar_kaydet(conn, satir[0], aday_id, "begendim")
    finally:
        conn.close()
    _boru_hatti.cache_clear()
    return JSONResponse(sonuc)


async def api_liste_durum(istek):
    veri = await istek.json()
    aday_id, durum = str(veri.get("aday_id") or ""), veri.get("durum")
    if not _KIMLIK.match(aday_id) or durum not in kesif.DURUMLAR:
        return JSONResponse({"hata": t("geçersiz istek", "invalid request")}, status_code=400)
    conn = _baglanti()
    try:
        tamam = kesif.durum_guncelle(conn, aday_id, durum)
    finally:
        conn.close()
    return JSONResponse({"tamam": tamam, "durum": durum},
                        status_code=200 if tamam else 404)


async def api_liste_sil(istek):
    veri = await istek.json()
    aday_id = str(veri.get("aday_id") or "")
    if not _KIMLIK.match(aday_id):
        return JSONResponse({"hata": t("geçersiz istek", "invalid request")}, status_code=400)
    conn = _baglanti()
    try:
        tamam = kesif.listeden_sil(conn, aday_id)
        sayi = kesif.liste_sayisi(conn)
    finally:
        conn.close()
    return JSONResponse({"tamam": tamam, "liste": sayi})


ROTALAR = [
    Route("/", anasayfa),
    Route("/kesfet", kesfet_sayfa),
    Route("/api/kesfet/deste", api_deste),
    Route("/api/kesfet/karar", api_kesfet_karar, methods=["POST"]),
    Route("/api/kesfet/geri-al", api_kesfet_geri_al, methods=["POST"]),
    Route("/api/kesfet/buyut", api_buyut, methods=["POST"]),
    Route("/api/medya/{aday_id}", api_medya),
    Route("/listem", listem),
    Route("/listem/disa-aktar/{bicim}", listem_aktar),
    Route("/api/liste/ekle", api_liste_ekle, methods=["POST"]),
    Route("/api/liste/durum", api_liste_durum, methods=["POST"]),
    Route("/api/liste/sil", api_liste_sil, methods=["POST"]),
    Route("/oneriler", oneriler),
    Route("/profil", profil),
    Route("/ogrenme", ogrenme),
    Route("/muzisyenler", muzisyenler),
    Route("/kumeler", kumeler),
    Route("/veri", veri_seti),
    Route("/eslestirme", eslestirme),
    Route("/etiketler", etiketler),
    Route("/sen", sen_sayfasi),
    Route("/tarzlar", tarzlar_sayfasi),
    Route("/tarzlar/otomatik", tarz_otomatik, methods=["POST"]),
    Route("/ses-kumeleri", ses_kumeleri),
    Route("/api/onizleme/{parca_id}", taze_onizleme),
    Route("/api/ses-kume-adi", ses_kume_adlandir, methods=["POST"]),
    Route("/basla", basla),
    Route("/api/aktar", aktar, methods=["POST"]),
    Route("/api/aktar/liste", aktar_liste, methods=["POST"]),
    Route("/api/aktar/durum", aktar_durum),
    Route("/giris", giris),
    Route("/giris", giris_gonder, methods=["POST"]),
    Route("/uyelik", uyelik),
    Route("/uyelik", uyelik_gonder, methods=["POST"]),
    Route("/cikis", cikis, methods=["GET", "POST"]),
    Route("/giris/spotify", spotify_baslat),
    Route("/giris/spotify/donus", spotify_donus),
    Route("/saglik", saglik),
    Route("/gizlilik", gizlilik),
    Route("/hesap/sil", hesap_sil_istek, methods=["POST"]),
    Route("/dil/{kod}", dil_degistir),
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

def _onbellekleri_isit() -> None:
    """Açılışta, arka planda: her kullanıcının pahalı önbelleklerini doldur.

    Ölçüldü (2026-09-23): soğuk sunucuda ilk deste partisi 1,9 sn, sıcakta
    0,14 sn; farkın tamamı bağlam etiketleri ve CLAP havuzunun ilk okunuşu.
    Kullanıcı sayfayı açmadan önce bu iş bitmiş olsun. Hata sessiz: ısıtma
    bir iyileştirme, uygulamanın çalışması ona bağlı değil.
    """
    try:
        conn = _oturum_baglantisi()
        try:
            kimlikler = [r[0] for r in conn.execute("SELECT kullanici_id FROM kullanici")]
        finally:
            conn.close()
        for kid in kimlikler:
            belirtec = AKTIF_KULLANICI.set(kid)
            try:
                _baglam_onbellek(kid)
                _olcum_onbellek(kid)
                _havuz_onbellek(kid)
            finally:
                AKTIF_KULLANICI.reset(belirtec)
    except Exception as hata:          # noqa: BLE001 — ısıtma asla çökertmemeli
        print(f"[isitma] {type(hata).__name__}: {hata}", file=sys.stderr)


@contextlib.asynccontextmanager
async def _yasam(uygulama_):
    import asyncio

    from python import hf_yedek

    # Hugging Face Spaces: disk geçici, veri özel veri deposundan gelir.
    # Geri yükleme ısıtmadan ÖNCE — ısıtma veritabanını okuyor.
    await asyncio.to_thread(hf_yedek.acilis)
    threading.Thread(target=_onbellekleri_isit, name="isitma", daemon=True).start()
    yield
    await asyncio.to_thread(hf_yedek.kapanis)


uygulama = Starlette(
    routes=ROTALAR,
    middleware=[Middleware(OturumAraKatmani)],
    lifespan=_yasam,
)



def _statik(yol: str) -> str:
    """`/statik/stil.css?v=<mtime>` — dosya değişince adres de değişir.

    Starlette statik dosyayı yalnız ETag/Last-Modified ile sunuyor; tarayıcı
    sezgisel tazelik süresince sunucuya hiç sormuyor ve servis çalışanının
    "önce ağ" isteği de aynı HTTP önbelleğinden geçiyor. Ölçüldü
    (2026-09-21): CSS düzeltmesinden sonra sayfa eski stil.css ile açıldı.
    Sürüm damgası her istekte stat ile okunuyor — mikrosaniye, ve sunucu
    yeniden başlatılmadan yapılan değişiklik de hemen yansıyor.
    """
    try:
        damga = int((KOK / "statik" / yol).stat().st_mtime)
    except OSError:
        damga = 0
    return f"/statik/{yol}?v={damga}"


from python import __version__ as _SURUM  # noqa: E402
SABLONLAR.env.globals["surum"] = _SURUM
SABLONLAR.env.globals["statik"] = _statik
SABLONLAR.env.globals["yer_tutucu"] = yer_tutucu_svg
SABLONLAR.env.globals["t"] = t
SABLONLAR.env.globals["dil"] = etkin_dil
SABLONLAR.env.filters["sayi"] = dil_sayi
SABLONLAR.env.filters["yuzde"] = yuzde
SABLONLAR.env.globals["yuzde"] = yuzde
from python.ceviri import etiket_aciklama, etiket_adi, rol_adi  # noqa: E402
from python.gerekce import strateji_adi  # noqa: E402
SABLONLAR.env.filters["etiket_adi"] = etiket_adi
SABLONLAR.env.filters["rol_adi"] = rol_adi
SABLONLAR.env.globals["etiket_aciklama"] = etiket_aciklama
SABLONLAR.env.globals["strateji_adi"] = strateji_adi


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
