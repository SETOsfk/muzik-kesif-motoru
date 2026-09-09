# Faz 1 — Görev Listesi

Sırayla ilerlenir. Her madde bittiğinde işaretlenir.

## 1. Alım
- [x] `python/ingest/kutuphane_tara.py` — FLAC klasörünü gez, mutagen ile metadata oku,
      `albums` tablosunu doldur. Artımlı: dosya değişiklik zamanına göre atla.
- [x] `python/ingest/dinleme_logu.py` — Symfonium/ListenBrainz/Last.fm dışa aktarımını
      `plays` tablosuna aktar. Albüm eşlemesi bulanık (sanatçı+albüm normalize edilmiş).

Ortak altyapı: `python/db.py` (şema), `python/metin.py` (normalizasyon + album_id).
Testler: `tests/test_alim.py` — `python tests/test_alim.py`.

## 2. Zenginleştirme
- [x] `python/enrich/mbid_eslestir.py` — her albümü MusicBrainz release-group'a bağla.
      Eşleşmeyen albümleri raporla, elle düzeltme için CSV çıkar.
- [x] `python/enrich/rol_eslemesi.py` — Discogs rol varyantlarını normalize eden sözlük.
- [x] `python/enrich/krediler.py` — Discogs + MusicBrainz'den kredi çek, `credits` doldur.
      Rate limit'e saygı, tam önbellek, kaldığı yerden devam edebilme.
- [x] `python/enrich/etiketler.py` — tür/alt tür etiketleri.
- [x] `python/enrich/ses_ozellikleri.py` — librosa, albüm başına özet. Yavaş, ayrı çalışır.

Ortak altyapı: `python/onbellek.py` — önbellekli + rate-limitli HTTP (K5).
Testler: `tests/test_zenginlestirme.py` (ağa çıkmaz).

Discogs canlı doğrulandı (token `.env`'de, kullanıcı `setosfk`): 3 örnek albümde
46 kredi + label/ülke. Sözlük iki turda 20 rol öğrendi, bilinmeyen rol kalmadı.

Açık kalan:
- `ses_ozellikleri.py` çalıştırılmadı — librosa kurulu değil ve örnek kütüphanedeki
  FLAC'ler sentetik (ses çerçevesi yok). Albüm özeti (medyan/IQR) testli, librosa
  çağrıları değil. Gerçek kütüphanede ilk kez çalıştırılırken `--limit 5` ile denenmeli.
- `bilinmeyen_roller.csv` her kredi turundan sonra gözden geçirilip sözlüğe işlenmeli;
  akış bunun için var.

## 3. Öznitelik matrisi
- [x] `python/enrich/matris_kur.py` — dört bloğu birleştir, blok içi normalize et,
      `data/ozellikler.parquet` yaz.

Blok içi normalizasyon: kredi/sahne/etiket satır bazında L2, ses sütun bazında
robust z (medyan/IQR). Blok **ağırlıkları** burada uygulanmaz — `python/kumeleme/ayar.py`'ye ait.
Yan çıktı: `data/ozellikler_sozluk.csv` (sütun → blok, ham ad, kapsam).
Testler: `tests/test_matris.py` (pandas gerektirir, `.venv/bin/python` ile).

## 4. Kümeleme (Python — bkz. K8, dil kararı 2026-08-11'de değişti)
- [x] `python/kumeleme/ayar.py` — blok ağırlıkları, m parametresi, c aralığı.
- [x] `python/kumeleme/boyut_indirgeme.py` — PCA (varsayılan) veya UMAP, bileşen kararı
      açıklanan varyansla.
- [x] `python/kumeleme/fcm.py` — FCM, c için Xie-Beni + partition entropy taraması.
- [x] `python/kumeleme/stabilite.py` — bootstrap Jaccard, stabil küme filtresi (eşik 0.6).
- [x] `python/kumeleme/temsilciler.py` — küme başına 5 temsilci: üst %20 üyelikten
      max-min çeşitlilik + küme profili + örtüşen albümler.
- [x] `python/kumeleme/calistir.py` — boru hattı, `memberships`/`clusters`/`temsilciler`
      tablolarını `calisma_id` ile versiyonlayarak yazar.

Testler: `tests/test_kumeleme.py` (24 test). Yöntem: yapısı bilinen sentetik veri
üretilip kümelemenin onu geri bulması beklenir.

## 5. Arayüz
- [x] `app/app.py` — Streamlit: her stabil küme için 5 temsilci albüm, kümenin kadrosu,
      kümeyi ayırt eden öznitelikler; kullanıcıdan isim alıp `clusters.kullanici_adi`
      alanına yazar.
- [x] "Sen busun" özet ekranı: küme boyutları, üyelik dağılımı, örtüşen albümler.
- [x] Kararsız kümeler ayrı sekmede, neden isimlendirmeye açılmadıklarıyla birlikte.

## Faz 1 bitiş ölçütü
Kullanıcı kendi kütüphanesinin kümelerini isimlendirebiliyor ve kümeler ona anlamlı
geliyor. Öneri motoruna geçiş için gereken tek şart bu.

**Gerçek kütüphanede çalıştırıldı (2026-08-11):** 302 albüm, 3032 parça, 9290 kredi,
2265 etiket. 244 albüm MusicBrainz'e bağlandı (%81). Kümeleme 6 stabil küme buldu
(Jaccard 0.69–0.90): hard rock/70'ler, pop-rock/UK, prog-metal, grunge/90'lar,
hip-hop+jazz, 2020'ler/Fransa. İsimlendirme ekranı açık ve çalışıyor.

Ölçütün son adımı SENDE: kümelere isim verip anlamlı gelip gelmediğine karar vermen.

**Mekanizma sentetik veriyle de doğrulanmıştı** — sentetik kütüphanede (60 albüm,
4 kurulu sahne) kümeleme c=4'ü seçti, dördü de stabil çıktı (Jaccard 0.99–1.00) ve
melez albümler bulanık üyelikte doğru işaretlendi. Arayüzden verilen isim
veritabanına yazıldı.

Ölçütün asıl sınavı gerçek kütüphanede: kümeler SANA anlamlı gelmeli. Sentetik veri
kodun doğru çalıştığını gösterir, kümelerin anlamlı olduğunu gösteremez.

## Sıradaki
Faz 2 — aday üretimi. Faz 1 bitiş ölçütü gerçek kütüphanende karşılanmadan başlanmaz
(CLAUDE.md: "Faz atlanmaz").

---

## Not — bütçe
Faz 1'de hiçbir ücretli servis kullanılmaz. Discogs token ve Reddit uygulaması ücretsiz
katmandan alınır; MusicBrainz ve iTunes Search zaten açıktır. Faz 3'e gelmeden LLM
konusuna dönülmez (bkz. CLAUDE.md K2).
