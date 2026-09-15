"""SQLite bağlantısı ve şema kurulumu.

Şema `docs/veri-sozlesmesi.md` ile birebir aynıdır. Buraya sütun eklemeden önce
o dosya güncellenir — tersi değil.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

VARSAYILAN_DB = Path("data/db/kesif.sqlite")

SEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS albums (
        album_id        TEXT PRIMARY KEY,
        mbid            TEXT,
        artist          TEXT NOT NULL,
        title           TEXT NOT NULL,
        year            INTEGER,
        country         TEXT,
        label           TEXT,
        path            TEXT,
        track_count     INTEGER,
        eklenme_tarihi  TEXT,
        -- Kullanıcı "bu albümün MusicBrainz karşılığı yok" dediğinde 1.
        -- Eşleştirme ekranında bir daha sorulmaz; boş mbid ile karıştırılmaz.
        mbid_yok        INTEGER NOT NULL DEFAULT 0
    )
    """,
    # Artımlı alımın belleği: hangi dosya ne zamandan beri hangi albüme ait.
    # Etiket okuma pahalı; mtime + boyut değişmemişse dosyaya hiç dokunulmaz.
    """
    CREATE TABLE IF NOT EXISTS dosyalar (
        yol       TEXT PRIMARY KEY,
        album_id  TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        mtime     REAL NOT NULL,
        boyut     INTEGER NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_dosyalar_album ON dosyalar(album_id)",
    """
    CREATE TABLE IF NOT EXISTS credits (
        album_id     TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        person_id    TEXT,
        person_name  TEXT NOT NULL,
        role         TEXT NOT NULL,
        kaynak       TEXT NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_credits_tekil
        ON credits(album_id, COALESCE(person_id, ''), person_name, role, kaynak)
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
        album_id  TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        tag       TEXT NOT NULL,
        agirlik   REAL,
        PRIMARY KEY (album_id, tag)
    )
    """,
    # kaynak PK'nın parçası: aynı albümün hem yerel (librosa) hem AcousticBrainz
    # profili yan yana durabilsin. İkisi AYNI ŞEYİ ÖLÇMÜYOR — kıyaslama kaynak
    # içinde standartlaştırılarak yapılır (K11).
    """
    CREATE TABLE IF NOT EXISTS audio_features (
        album_id            TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        kaynak              TEXT NOT NULL DEFAULT 'yerel',
        tempo_medyan        REAL,
        tempo_iqr           REAL,
        dinamik_aralik      REAL,
        nabiz_netligi       REAL,
        vurus_degiskenligi  REAL,
        spektral_merkez     REAL,
        onset_hizi          REAL,   -- yalnızca AcousticBrainz
        dans_edilebilirlik  REAL,   -- yalnızca AcousticBrainz
        akor_degisim_hizi   REAL,   -- yalnızca AcousticBrainz
        parca_sayisi        INTEGER,
        PRIMARY KEY (album_id, kaynak)
    )
    """,
    # kaynak sütunu: aynı gün iki farklı dışa aktarımdan (Last.fm + ListenBrainz)
    # gelen dinlemeler birbirini ezmesin, her kaynak kendi içinde idempotent olsun.
    """
    CREATE TABLE IF NOT EXISTS plays (
        album_id  TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        tarih     TEXT NOT NULL,
        track     TEXT,
        adet      INTEGER NOT NULL DEFAULT 1,
        kaynak    TEXT NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_plays_tekil
        ON plays(kaynak, album_id, tarih, COALESCE(track, ''))
    """,
    """
    CREATE TABLE IF NOT EXISTS memberships (
        album_id    TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        kume_id     INTEGER NOT NULL,
        uyelik      REAL NOT NULL,
        calisma_id  TEXT NOT NULL,
        PRIMARY KEY (calisma_id, kume_id, album_id)
    )
    """,
    # Temsilciler kümeleme anında seçilir ve saklanır: arayüz, çalışmanın verdiği
    # kararı göstermeli: yeniden hesaplarsa (farklı ağırlık/tohum) başka albümler
    # çıkabilir ve kullanıcı isimlendirdiği kümeyi bir daha tanıyamaz.
    """
    CREATE TABLE IF NOT EXISTS temsilciler (
        calisma_id  TEXT NOT NULL,
        kume_id     INTEGER NOT NULL,
        album_id    TEXT NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
        sira        INTEGER NOT NULL,
        uyelik      REAL NOT NULL,
        PRIMARY KEY (calisma_id, kume_id, album_id)
    )
    """,
    # Davul (ve ileride başka enstrüman) stem profili. Müzisyen düzeyinde,
    # albüm düzeyinde DEĞİL: soru "bu davulcu nasıl çalıyor", "bu albüm nasıl"
    # değil. Kaynak 30 sn önizleme; tek kaynak olması karşılaştırmayı geçerli
    # kılıyor (K11).
    """
    CREATE TABLE IF NOT EXISTS davul_profili (
        kisi_anahtar    TEXT NOT NULL,
        rol             TEXT NOT NULL,
        kisi_adi        TEXT NOT NULL,
        nota_vurus      REAL,   -- vuruş başına nota: tempodan bağımsız yoğunluk
        izgara_entropi  REAL,   -- 16'lık ızgara entropisi: makine düşük, insan yüksek
        tekme_payi      REAL,   -- <120 Hz
        trampet_payi    REAL,   -- 120–2000 Hz
        zil_payi        REAL,   -- >6000 Hz
        dinamik_db      REAL,
        tempo           REAL,
        klip_sayisi     INTEGER,
        -- Tanı alanları: "bu kişi gerçekten davulcu mu" sorusunu KULLANICI
        -- yargılasın diye. Otomatik eşik denendi ve bırakıldı: %25 kredi payı
        -- Bruce Swedien'i (11 rollü mühendis) eliyor ama Matt Cameron'ı da
        -- eliyor (Soundgarden'da şarkı da yazdığı için payı %22). İyi veriyi
        -- atmaktansa kanıtı göstermek doğru.
        rol_sayisi      INTEGER,  -- kişinin toplam farklı rol sayısı
        rol_kredi_payi  REAL,     -- bu roldeki kredi / tüm kredileri
        ornek_onizleme  TEXT,   -- kullanıcının DUYABİLMESİ için
        PRIMARY KEY (kisi_anahtar, rol)
    )
    """,
    # Albüm × stem icra profili. Demucs tek geçişte dört stem üretiyor, o yüzden
    # ölçüm birimi ALBÜM: bir klip bir kez ayrışır, davul/bas/gitar/vokal profili
    # birlikte çıkar. Müzisyen profili bundan türetilir (kredilere göre medyan).
    # Enstrümana özgü sütunlar ilgisiz stem'de NULL kalır — davulda perde,
    # vokalde tekme payı aranmaz.
    """
    CREATE TABLE IF NOT EXISTS stem_profili (
        album_id        TEXT NOT NULL,  -- albums.album_id VEYA adaylar.aday_id
        tur             TEXT NOT NULL DEFAULT 'album',  -- album / aday
        stem            TEXT NOT NULL,   -- drums / bass / other / vocals
        onizleme_url    TEXT,
        -- ortak
        nota_vurus      REAL,   -- vuruş başına nota: tempodan bağımsız yoğunluk
        tempo           REAL,
        enerji_payi     REAL,   -- stem'in mikste kapladığı yer
        dinamik_db      REAL,
        sustain_orani   REAL,   -- uzun nota mı staccato mu
        parlaklik       REAL,   -- spektral merkez
        harmonik_pay    REAL,   -- HPSS harmonik enerji payı: distorsiyon düşürür
        zcr             REAL,   -- sıfır geçiş oranı
        -- yalnız davul
        izgara_entropi  REAL,   -- makine düşük, insan yüksek
        tekme_payi      REAL,
        trampet_payi    REAL,
        zil_payi        REAL,
        -- yalnız perdeli stem'ler (bas / gitar-klavye / vokal)
        perde_medyan    REAL,   -- yarım ton, C1 referanslı
        perde_araligi   REAL,
        vibrato_hizi    REAL,
        PRIMARY KEY (album_id, stem)
    )
    """,
    # Faz 2: üretilen aday albümler. Kütüphanede OLMAYAN albümler burada durur;
    # `albums` tablosu yalnızca kullanıcının sahip olduklarıdır.
    """
    CREATE TABLE IF NOT EXISTS adaylar (
        aday_id       TEXT NOT NULL,
        calisma_id    TEXT NOT NULL,
        eksen         INTEGER,
        strateji      TEXT NOT NULL,
        artist        TEXT NOT NULL,
        title         TEXT NOT NULL,
        year          INTEGER,
        mbid          TEXT,
        discogs_id    TEXT,
        skor          REAL NOT NULL,
        gerekce       TEXT NOT NULL,
        dayanak       TEXT,
        onizleme_url  TEXT,
        uretim_tarihi TEXT,
        PRIMARY KEY (calisma_id, eksen, strateji, aday_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_adaylar_skor ON adaylar(calisma_id, skor DESC)",
    # Faz 3 geri bildirim döngüsü; şema şimdiden dursun ki aday ekranı yazarken
    # tablo eksikliğinden dolayı yeniden göç gerekmesin.
    """
    CREATE TABLE IF NOT EXISTS feedback (
        aday_id    TEXT NOT NULL,
        eksen      INTEGER,
        karar      TEXT NOT NULL,
        tarih      TEXT NOT NULL,
        calisma_id TEXT,
        PRIMARY KEY (aday_id, calisma_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clusters (
        kume_id        INTEGER NOT NULL,
        calisma_id     TEXT NOT NULL,
        kullanici_adi  TEXT,
        stabilite      REAL,
        stabil_mi      INTEGER,
        PRIMARY KEY (calisma_id, kume_id)
    )
    """,
    # Aynı kişinin farklı yazımları. Profil anahtarı `normalize_esleme(ad)`
    # olduğu için kaynak ikilemesi ve tipografik fark zaten birleşiyor;
    # burası ADIN KENDİSİ farklı olan durumu çözer (神保彰 ↔ Akira Jimbo,
    # Bob Siebenberg ↔ Bob C. Benberg). Kaynak MusicBrainz alias verisi, ama
    # yalnız İKİ TARAFI DA kredilerde var olan adlar yazılır — bkz.
    # `python/enrich/kisi_birlestir.py`.
    """
    CREATE TABLE IF NOT EXISTS kisi_eslesme (
        anahtar   TEXT PRIMARY KEY,   -- normalize_esleme(varyant ad)
        kanonik   TEXT NOT NULL,      -- normalize_esleme(kalacak ad)
        kaynak    TEXT                -- musicbrainz / elle
    )
    """,
    # Çok boyutlu etiketleme (MTG-Jamendo'nun üç eksenli yapısı: tür /
    # enstrüman / doku). 12 kaba küme yerine okunabilir tarifler üretmek için;
    # Netflix'in ~76 bin kategorisi de kümelemeyle değil etiket kombinasyonuyla
    # üretilmişti.
    """
    CREATE TABLE IF NOT EXISTS album_etiket (
        album_id  TEXT NOT NULL,
        eksen     TEXT NOT NULL,   -- tur / enstruman / doku
        etiket    TEXT NOT NULL,
        kaynak    TEXT,            -- olcum / musicbrainz / yil / ulke
        PRIMARY KEY (album_id, etiket)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_album_etiket_etiket ON album_etiket(etiket)",
    # Ses kümeleri: türü etiketten değil CLAP gömüsünden keşfeden kümeleme.
    # `memberships` ile AYNI ŞEY DEĞİL — o kredi/etiket/sahne matrisinden
    # geliyor, bu yalnız sesten. Ölçüldü: uyumları ARI 0.073, yani iki ayrı
    # bakış.
    """
    CREATE TABLE IF NOT EXISTS ses_kumesi (
        album_id         TEXT PRIMARY KEY,
        kume             INTEGER NOT NULL,
        merkez_uzakligi  REAL
    )
    """,
    # Ses kümesine kullanıcının verdiği ad. Küme numarası kümeleme yeniden
    # koşunca değişebilir; bu tabloyu silmek gerekir. Şimdilik tek çalışma
    # var, versiyonlama gerekmiyor.
    """
    CREATE TABLE IF NOT EXISTS ses_kume_adi (
        kume  INTEGER PRIMARY KEY,
        ad    TEXT
    )
    """,
    # Çalma listesi hasadı: kullanıcı kaydı olmadan ortak filtreleme vekili.
    # Bir listede iki sanatçının yan yana durması, insan eliyle verilmiş bir
    # "bunu dinleyen şunu da dinliyor" işareti. Kaynak Deezer'ın anahtarsız
    # genel API'si.
    """
    CREATE TABLE IF NOT EXISTS calma_listesi (
        liste_id       INTEGER PRIMARY KEY,
        baslik         TEXT,
        parca_sayisi   INTEGER,
        takipci        INTEGER,
        kaynak         TEXT,
        tohum_sanatci  TEXT   -- hangi kütüphane sanatçısını ararken bulundu
    )
    """,
    # Listelerin PARÇALARI saklanıyor, yalnız sanatçı adları değil: öneriyi
    # albüm düzeyinden parça düzeyine indirmenin tek yolu bu.
    """
    CREATE TABLE IF NOT EXISTS liste_parca (
        liste_id         INTEGER NOT NULL REFERENCES calma_listesi(liste_id)
                         ON DELETE CASCADE,
        sira             INTEGER NOT NULL,
        sanatci          TEXT NOT NULL,
        sanatci_anahtar  TEXT NOT NULL,   -- normalize_esleme(sanatci)
        parca            TEXT,
        onizleme         TEXT,            -- Deezer 30 sn
        PRIMARY KEY (liste_id, sira)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_liste_parca_sanatci ON liste_parca(sanatci_anahtar)",
    # PMI ile popülerlik sönümlenmiş birliktelik. Ham sayı ünlü sanatçıyı öne
    # çıkarırdı — herkesin listesinde Metallica var.
    """
    CREATE TABLE IF NOT EXISTS liste_birlikteligi (
        kutuphane_anahtar  TEXT NOT NULL,
        aday_anahtar       TEXT NOT NULL,
        birlikte           INTEGER NOT NULL,
        pmi                REAL NOT NULL,
        PRIMARY KEY (kutuphane_anahtar, aday_anahtar)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS kullanici (
        kullanici_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        eposta          TEXT UNIQUE,        -- e-posta ile üyelikte
        ad              TEXT NOT NULL,      -- gösterilecek ad
        spotify_id      TEXT UNIQUE,        -- Spotify ile bağlanmışsa
        spotify_yenile  TEXT,               -- refresh token (yerelde kalır)
        parola_ozeti    TEXT,               -- e-posta ile üyelikte (scrypt)
        olusturma       TEXT NOT NULL,
        son_giris       TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS oturum (
        jeton         TEXT PRIMARY KEY,     -- rastgele, çerezde taşınır
        kullanici_id  INTEGER NOT NULL,
        olusturma     TEXT NOT NULL,
        son_gorulme   TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_oturum_kullanici ON oturum(kullanici_id)
    """,
)


# --------------------------------------------------------------------------- #
# Çok kiracılık — kullanıcı veritabanı + paylaşımlı veritabanı
# --------------------------------------------------------------------------- #
#
# NEDEN İKİ DOSYA, TEK DOSYA + `kullanici_id` SÜTUNU DEĞİL
# Kütüphaneyi okuyan 145, paylaşımlı tabloları okuyan 117 sorgu yeri var
# (ölçüldü). Her birine kullanıcı süzgeci eklemek yüzlerce dokunuş ve yüzlerce
# hata fırsatı demekti.
#
# SQLite'ın ad çözümlemesi bunu bedavaya çözüyor: NİTELİKSİZ bir tablo adı
# önce `main`de, bulunamazsa ATTACH edilmiş veritabanlarında aranır. Bir tablo
# ikisinden yalnız BİRİNDE varsa, mevcut sorguların tamamı hiç değişmeden
# doğru yere gider. Ölçüldü: okuma, yazma ve iki veritabanı arası JOIN çalışıyor.
#
# BEDELİ: veritabanları arası yabancı anahtar YOK. Ölçüldü ve sessizce
# yok sayılmıyor, gürültülü patlıyor ("no such table: ortak.albums"). Bu
# yüzden paylaşımlı tablolardaki `REFERENCES albums(...)` kısıtları
# otomatik sökülüyor (`_fk_sok`). Kaybedilen CASCADE semantik olarak zaten
# YANLIŞ olurdu: bir kullanıcının albümü silindiğinde o albümün kredileri
# silinmemeli, başka kullanıcı ona sahip olabilir.

#: Paylaşımlı veritabanına giden tablolar. Ölçüt: kayıt ALBÜMÜ ya da KİŞİYİ
#: tarif ediyorsa paylaşımlı (bir kez hesaplanır, herkes yararlanır);
#: KULLANICININ tercihini/kütüphanesini tarif ediyorsa kullanıcıya özel.
ORTAK_TABLOLAR: frozenset[str] = frozenset({
    "credits",          # albüm → kim çalmış
    "tags",             # albüm → tür etiketi (MusicBrainz)
    "audio_features",   # albüm → ses ölçümü
    "stem_profili",     # albüm → ayrılmış stem ölçümü
    "davul_profili",    # kişi → icra karakteri
    "kisi_eslesme",     # takma ad → kanonik ad
    "calma_listesi",    # havuz
    "liste_parca",      # havuz
    "kullanici",        # hesaplar
    "oturum",           # oturum jetonları
})

#: Kullanıcıya özel kalanlar (belge amaçlı; kod `ORTAK_TABLOLAR` dışını kullanır):
#: albums, dosyalar, plays, memberships, temsilciler, clusters, adaylar,
#: feedback, album_etiket, ses_kumesi, ses_kume_adi, liste_birlikteligi.
#:
#: `liste_birlikteligi` ve `album_etiket` paylaşımlı DEĞİL çünkü ikisi de
#: kütüphaneye görelidir: PMI "kütüphane sanatçısı × dışarıdaki" bağıdır,
#: etiket eşikleri kütüphanenin kendi dağılımının kuyruğundan gelir.

VARSAYILAN_ORTAK = Path("data/db/ortak.sqlite")
KULLANICI_KOK = Path("data/db/kullanici")

_TABLO_ADI = re.compile(r"CREATE TABLE(?: IF NOT EXISTS)? (\w+)", re.IGNORECASE)
#: İndeks de bir tabloya aittir ve o tablonun veritabanında oluşturulmalı.
#: Sınıflandırılmazsa her iki tarafa da yazılmaya çalışılır ve olmayan tabloda
#: patlar ("no such table: main.credits").
#: UNIQUE ve çok satıra yayılan "ON tablo" biçimleri de yakalanmalı:
#: `ix_credits_tekil` ile `ix_plays_tekil` böyle yazılmış ve ilk sürümde
#: sınıflandırılamayıp iki tarafa da yazılmaya çalışıldı.
_INDEKS_TABLOSU = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+\w+\s+ON\s+(\w+)",
    re.IGNORECASE | re.DOTALL,
)
_FK = re.compile(r"\s+REFERENCES albums\(album_id\)(?:\s+ON DELETE CASCADE)?", re.IGNORECASE)


def _tablo_adi(ddl: str) -> str | None:
    """DDL'in ait olduğu tablo — CREATE TABLE ya da CREATE INDEX ... ON."""
    eslesme = _TABLO_ADI.search(ddl) or _INDEKS_TABLOSU.search(ddl)
    return eslesme.group(1) if eslesme else None


def _fk_sok(ddl: str) -> str:
    """`albums`a giden yabancı anahtarı söker — veritabanları arası FK çalışmaz."""
    return _FK.sub("", ddl)


#: Oluşturulan nesnenin adını `ortak.` ile niteler. Dizi değiştirmeyle
#: yapılırsa `CREATE UNIQUE INDEX` gibi biçimler kaçar ve indeks main'de
#: oluşturulmaya çalışılıp "no such table: main.credits" verir (ölçüldü).
_NITELE = re.compile(
    r"(CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)(?:\s+IF\s+NOT\s+EXISTS)?\s+)(\w+)",
    re.IGNORECASE,
)


def _ortak_nitele(ddl: str) -> str:
    """`CREATE TABLE x` → `CREATE TABLE ortak.x` (indeksler ve UNIQUE dahil)."""
    return _NITELE.sub(r"\1ortak.\2", ddl, count=1)


def _sema_bolumu(ortak: bool) -> tuple[str, ...]:
    """SEMA'yı hedef veritabanına göre süz. Tek şema kaynağı korunur."""
    secilen = []
    for ddl in SEMA:
        ad = _tablo_adi(ddl)
        if ad is None:
            secilen.append(ddl)          # indeksler; ait oldukları yerde çalışır
        elif (ad in ORTAK_TABLOLAR) == ortak:
            secilen.append(_fk_sok(ddl) if ortak else ddl)
    return tuple(secilen)


def kullanici_db(kullanici_id: int | str) -> Path:
    return KULLANICI_KOK / f"{kullanici_id}.sqlite"


def baglan_kullanici(
    kullanici_id: int | str, *, ortak_yolu: Path | str | None = None,
    sema: bool = True,
) -> sqlite3.Connection:
    """Kullanıcının veritabanını aç, paylaşımlı olanı `ortak` adıyla ekle.

    Dönen bağlantıda mevcut sorguların tamamı DEĞİŞMEDEN çalışır: `albums`
    kullanıcıdan, `liste_parca` ortaktan gelir; niteliksiz adları SQLite
    kendisi çözer.
    """
    kul_yolu = kullanici_db(kullanici_id)
    kul_yolu.parent.mkdir(parents=True, exist_ok=True)
    # Modül genelini ÇAĞRI ANINDA oku, varsayılan argüman olarak DEĞİL:
    # varsayılan argüman tanımlama anında bağlanır ve testler yolu
    # yönlendiremez — ilk sürümde test gerçek ortak veritabanına yazdı.
    ortak_yolu = Path(ortak_yolu if ortak_yolu is not None else VARSAYILAN_ORTAK)
    ortak_yolu.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(kul_yolu)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("ATTACH DATABASE ? AS ortak", (str(ortak_yolu),))
    # FK'ler ancak TEK veritabanı içinde çalışır; ATTACH'li bağlantıda açık
    # bırakmak paylaşımlı tablolara yazarken patlıyor (ölçüldü).
    conn.execute("PRAGMA foreign_keys = OFF")
    if sema:
        with conn:
            for ddl in _sema_bolumu(ortak=False):
                conn.execute(ddl)
            for ddl in _sema_bolumu(ortak=True):
                conn.execute(_ortak_nitele(ddl))
            _gocleri_uygula(conn)
    return conn

def baglan(db_yolu: Path | str = VARSAYILAN_DB, *, sema: bool = True) -> sqlite3.Connection:
    """Veritabanını aç (yoksa oluştur) ve şemayı garanti et."""
    db_yolu = Path(db_yolu)
    if str(db_yolu) != ":memory:":
        db_yolu.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_yolu)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    if sema:
        sema_kur(conn)
    return conn


# Var olan veritabanlarına sonradan eklenen sütunlar. Şema dosyası tek doğru
# kaynak; burası yalnızca eski dosyaları oraya taşır.
GOC: tuple[tuple[str, str, str], ...] = (
    ("albums", "mbid_yok", "ALTER TABLE albums ADD COLUMN mbid_yok INTEGER NOT NULL DEFAULT 0"),
    ("davul_profili", "rol_sayisi", "ALTER TABLE davul_profili ADD COLUMN rol_sayisi INTEGER"),
    ("davul_profili", "rol_kredi_payi", "ALTER TABLE davul_profili ADD COLUMN rol_kredi_payi REAL"),
    # tepe_orani, elenen `duzluk`un yerine geldi (2026-08-16). Spektral düzlük
    # Demucs çıktısında 0.000-0.012'ye sıkışıp hiçbir şey ayırmıyordu.
    ("stem_profili", "harmonik_pay", "ALTER TABLE stem_profili ADD COLUMN harmonik_pay REAL"),
    ("stem_profili", "zcr", "ALTER TABLE stem_profili ADD COLUMN zcr REAL"),
    # Önizlemenin HANGİ parça olduğu. Öneri kartı artık sanatçı düzeyinde
    # gruplanıyor ve altında albümler listeleniyor; "hangi şarkıyı dinliyorum"
    # sorusunun cevabı olmadan o liste okunmuyordu.
    ("adaylar", "onizleme_parca", "ALTER TABLE adaylar ADD COLUMN onizleme_parca TEXT"),
    ("adaylar", "kapak", "ALTER TABLE adaylar ADD COLUMN kapak TEXT"),
    # Aday artık albüm olmak zorunda değil: çalma listesi hasadı PARÇA düzeyinde
    # aday üretiyor ve önizlemesi hazır geliyor. 'album' | 'parca'.
    ("adaylar", "birim", "ALTER TABLE adaylar ADD COLUMN birim TEXT NOT NULL DEFAULT 'album'"),
    # CLAP etiketleri olasılık taşıyor; yüzdelik kesiminden gelenler taşımıyor.
    ("album_etiket", "skor", "ALTER TABLE album_etiket ADD COLUMN skor REAL"),
    # Deezer önizleme URL'leri KISA ÖMÜRLÜ imzalı: ölçüldü, hasattan saatler
    # sonra 10 URL'nin 10'u da 403 döndü. Kalıcı olan şey parça kimliği;
    # taze URL gerektiğinde `track/{id}` ile alınır.
    ("liste_parca", "parca_id", "ALTER TABLE liste_parca ADD COLUMN parca_id INTEGER"),
    # Parça adaylarının önizlemesi SAKLANAMAZ: Deezer kısa ömürlü imzalıyor
    # (ölçüldü, saatler sonra 10 URL'nin 10'u 403). Kalıcı olan kimlik;
    # taze URL çalma anında `/api/onizleme/{parca_id}` ile alınıyor.
    ("adaylar", "parca_id", "ALTER TABLE adaylar ADD COLUMN parca_id INTEGER"),
)


def _stem_profili_gocu(conn: sqlite3.Connection) -> None:
    """stem_profili'ni albums'a bağlı olmaktan çıkar.

    İcra profili artık SAHİP OLUNMAYAN albümler için de üretiliyor: öneri
    "bu albümün davulcusu Duplantier kalibresinde" diyebilsin diye adayların da
    stem'i ölçülüyor. Adaylar `adaylar` tablosunda, `albums`ta değil — yabancı
    anahtar bu satırları reddediyordu.

    Kimlik uzayı ortak: `aday_id` de `album_id` de `album_kimligi()` ile aynı
    şekilde türetiliyor. Yani bir aday sonradan kütüphaneye girerse kimliği
    değişmez ve ölçülmüş profili olduğu yerde kalır — yeniden ayrıştırma yok.
    `tur` sütunu sorguların hangisinden bahsettiğini açık tutar.

    ADD COLUMN ile yapılamaz: yabancı anahtar kısıtı kaldırılıyor, bu da SQLite'ta
    tablo yeniden kurmayı gerektirir. Mevcut satırlar `tur='album'` olarak taşınır.
    """
    tablolar = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('stem_profili', 'stem_profili_eski')"
        )
    }
    if "stem_profili" not in tablolar and "stem_profili_eski" not in tablolar:
        return

    # Yarıda kalmış göçü tamamla. Bu bir kez gerçekten oldu: yeni şemada olmayan
    # bir sütun (elenen `duzluk`) yüzünden INSERT patladı, eski tablo adı
    # değişmiş hâlde kaldı ve yeni tablo boş kuruldu. Sonraki çağrı "tur var,
    # göç bitmiş" deyip erken dönüyordu — 289 albümlük ölçüm görünmez oluyordu.
    if "stem_profili_eski" in tablolar:
        for ddl in SEMA:
            if "stem_profili" in ddl:
                conn.execute(ddl)
        eski = {r[1] for r in conn.execute("PRAGMA table_info(stem_profili_eski)")}
        yeni = {r[1] for r in conn.execute("PRAGMA table_info(stem_profili)")}
        ortak = ", ".join(sorted(eski & yeni - {"tur"}))
        conn.execute(
            f"INSERT OR IGNORE INTO stem_profili ({ortak}, tur) "
            f"SELECT {ortak}, 'album' FROM stem_profili_eski"
        )
        conn.execute("DROP TABLE stem_profili_eski")
        return

    sutunlar = {s[1] for s in conn.execute("PRAGMA table_info(stem_profili)")}
    if "tur" in sutunlar:
        return
    conn.execute("ALTER TABLE stem_profili RENAME TO stem_profili_eski")
    for ddl in SEMA:
        if "stem_profili" in ddl:
            conn.execute(ddl)
    # Yalnız İKİ tabloda da olan sütunlar taşınır. Eski tabloda elenen ölçütler
    # duruyor (`duzluk`, `tepe_orani`); onları taşımak elenmiş bir ölçütü geri
    # getirmek olurdu. Kesişim almak aynı zamanda ileride eklenecek sütunlarda
    # da bu göçün kırılmamasını sağlar.
    yeni = {r[1] for r in conn.execute("PRAGMA table_info(stem_profili)")}
    ortak = ", ".join(sorted(sutunlar & yeni - {"tur"}))
    conn.execute(
        f"INSERT INTO stem_profili ({ortak}, tur) SELECT {ortak}, 'album' "
        "FROM stem_profili_eski"
    )
    conn.execute("DROP TABLE stem_profili_eski")


def _audio_features_gocu(conn: sqlite3.Connection) -> None:
    """audio_features'ı (album_id) PK'dan (album_id, kaynak) PK'ya taşı.

    ADD COLUMN ile yapılamaz çünkü birincil anahtar değişiyor. Mevcut satırlar
    `kaynak='yerel'` olarak korunur — librosa taraması yeniden çalıştırılmasın.
    """
    sutunlar = {s[1] for s in conn.execute("PRAGMA table_info(audio_features)")}
    if not sutunlar or "kaynak" in sutunlar:
        return

    eski_ortak = [
        s for s in ("tempo_medyan", "tempo_iqr", "dinamik_aralik",
                    "nabiz_netligi", "vurus_degiskenligi", "spektral_merkez")
        if s in sutunlar
    ]
    conn.execute("ALTER TABLE audio_features RENAME TO audio_features_eski")
    for ddl in SEMA:
        if "CREATE TABLE IF NOT EXISTS audio_features" in ddl:
            conn.execute(ddl)
            break
    alanlar = ", ".join(eski_ortak)
    conn.execute(
        f"INSERT INTO audio_features (album_id, kaynak, {alanlar}) "
        f"SELECT album_id, 'yerel', {alanlar} FROM audio_features_eski"
    )
    conn.execute("DROP TABLE audio_features_eski")


def _gocleri_uygula(conn: sqlite3.Connection) -> None:
    """Eksik sütunları ekle. Tablo hangi veritabanındaysa oraya işler."""
    for tablo, sutun, ddl in GOC:
        try:
            mevcut = {s[1] for s in conn.execute(f"PRAGMA table_info({tablo})")}
        except sqlite3.Error:
            continue
        if not mevcut:
            # PRAGMA table_info niteliksiz adı çözemediyse ortak'ta ara.
            mevcut = {s[1] for s in conn.execute(f"PRAGMA ortak.table_info({tablo})")}
            if mevcut and sutun not in mevcut:
                conn.execute(ddl.replace(f"ALTER TABLE {tablo}",
                                         f"ALTER TABLE ortak.{tablo}"))
            continue
        if sutun not in mevcut:
            conn.execute(ddl)


def sema_kur(conn: sqlite3.Connection) -> None:
    with conn:
        _audio_features_gocu(conn)
        _stem_profili_gocu(conn)
        for ddl in SEMA:
            conn.execute(ddl)
        _gocleri_uygula(conn)
