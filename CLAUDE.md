# Müzik Keşif Motoru — Proje Anayasası

Bu dosya projenin kalıcı bağlamıdır. Her oturumun başında oku, sonunda gerekiyorsa güncelle.

## Amaç

Kişisel FLAC kütüphanesi ve dinleme geçmişinden hareketle, kullanıcının zevk eksenlerini
çıkaran ve o eksenleri bilinçli olarak besleyen albüm önerileri üreten bir sistem.

Sıradan bir öneri motorundan farkı: **neden** önerdiğini ve albümde **neye dikkat edilmesi
gerektiğini** açıklar. Öneri, kullanıcının seçtiği eksene göre yapılır — sistem karar vermez,
kullanıcıya "hangi tarafını beslemek istiyorsun?" diye sorar.

## Çözülmesi gereken asıl problem

Tür etiketleri yetersiz. "İyi davulcu dinleyen adam" bilgisi tür etiketinde değil,
**kredilerde** yatar. Bu yüzden sistemin çekirdeği kredi grafiğidir (kim çalmış, kim
prodüktör, hangi label, hangi sahne).

## Mimari kararlar

### K1 — Uygulama, sohbet botu değil
Deterministik kısım (metadata alımı, kredi zenginleştirme, kümeleme, aday üretimi,
önbellek) tamamen koddur. Sohbet arayüzü birincil arayüz DEĞİLDİR.
Gerekçe: önizleme çalma, kalıcı profil, tekrarlanabilir kümeleme, önbellek ekonomisi.

### K2 — Sistem LLM'e bağımlı DEĞİLDİR (bütçe: 0 TL)
Projenin geliştirme ve çalıştırma maliyeti sıfır olmak zorundadır. Faz 1 ve Faz 2'de
hiçbir LLM çağrısı yoktur. Kullanılan tüm veri kaynakları ücretsizdir
(MusicBrainz, Discogs token, Reddit ücretsiz katman, iTunes Search).

LLM'in değer kattığı tek nokta Faz 3'teki "neye dikkat et" sentezidir ve bu bile
zorunlu değildir. Bu yüzden LLM çekirdeğe gömülmez, arkasına arayüz konur:

```
ozetle(metinler, mod) -> str
  mod="cikarimsal"  (VARSAYILAN, 0 TL) en çok oy almış yorumları filtreleyip ham gösterir
  mod="yerel"       Ollama, M1 Mac'te 7-8B model — elektrik dışında maliyet yok
  mod="api"         Anthropic API — opsiyonel, kullanıcı isterse
```

Varsayılan `cikarimsal`. Sistem hiçbir kod yolunda LLM'in varlığını varsaymaz.

**Elenen kullanımlar:**
- Küme isimlendirme önerisi — gereksiz, isimleri kullanıcı verir.
- "Neden bu albüm" gerekçesi — LLM'e gerek yok. Sebep kredi grafiğinde yapısal olarak
  duruyor ve şablonla üretilir; sayısal dayanağı olduğu için modelin yazacağından
  daha güvenilir. Bkz. K7.

Kümeleme ve aday üretimi her koşulda istatistikseldir; sonuç tekrarlanabilir olmak zorundadır.

### K3 — Bulanık kümeleme (FCM)
Bir albüm aynı anda birden fazla eksene ait olabilir. Keskin kümeleme bilgi kaybettirir.
Üyelik dereceleri (u_ij) doğrudan öneri motorunun eksen ağırlıkları olarak kullanılır.

Uygulama detayları:
- Yüksek boyutta FCM üyelikleri 1/c'ye yakınsar → önce boyut indirgeme (UMAP/PCA)
- Bulanıklık parametresi m = 1.3–1.6 (m=2 kullanma)
- Küme sayısı: Xie-Beni + partition entropy, ARTI bootstrap stabilite kontrolü (Jaccard)
- Kullanıcıya sadece stabil kümeler isimlendirme için sunulur

### K4 — Temsilci albüm seçimi
En yüksek üyelikli 5 albümü almak yanlış: aynı sanatçının 5 albümü çıkar, küme kimliği
anlaşılmaz. Üst üyelikten başlayıp aralarında maksimum çeşitlilik olanları seç
(max-min mesafe).

**Havuz kümenin KENDİ üyelerinden kurulur** (2026-08-11 düzeltmesi). Yüzdelik tüm
kütüphaneden hesaplanırsa max-min çeşitlilik kümenin kenarını seçiyor: ölçüldü, ilk
temsilcinin üyeliği 0.98 iken diğer dördününki 0.22 idi — yani kümeye zar zor ait
albümler temsilci oluyordu. Düzeltmeden sonra 0.68.

### K5 — Her şey önbelleklenir
Discogs/MusicBrainz/Reddit çağrıları pahalı ve rate-limitli. Aynı sorgu iki kez yapılmaz.
Önbellek `data/cache/` altında, kalıcı veri `data/db/` altında SQLite.

### K6 — Artımlı çalışma
Kütüphane büyüdükçe sıfırdan başlanmaz. Her aşama "hangi kayıtlar yeni?" sorusunu
cevaplayabilmeli.

### K7 — "Neden bu albüm" şablonla üretilir
Öneri gerekçesi, aday üretiminde kullanılan yolun kendisidir. Kredi grafiğinden
gelen bir öneri kendi açıklamasını taşır:

> Davulda Marco Minnemann var. Kütüphanende onun çaldığı 4 albüm var ve üçü en çok
> dinlediğin %10'da. Bu albümü hiç dinlememişsin.

Her aday üretim stratejisinin (kredi sıçraması, sahne komşuluğu, bilinçli uzaklık)
kendi şablonu vardır ve şablonun boşlukları sorgudan gelen gerçek sayılarla dolar.
Uydurma yok, doğrulanabilir.

### K9 — Label kullanılmaz (kullanıcı kararı, 2026-08-11)
Plak şirketi sahne bloğundan çıkarıldı. Gerekçe: aynı label'dan çıkan iki albümün
ortak yanı dağıtım anlaşmasıdır, müzikal yakınlık değil. `albums.label` alanı
veritabanında durmaya devam ediyor (bilgi olarak), matrise girmiyor.

### K10 — Söylem/kalabalık katmanı projenin ayırt edici parçasıdır
Kullanıcının ifadesiyle: "bizi diğer uygulamalardan ayıran kısım bu tarz
forumlardan da öneri çekebiliyor olmamız." Kredi grafiğinin söyleyemediği şeyleri
(bkz. "benzer kalibrede davulcu" sorusu) yalnızca bu katman söyleyebilir.

**Reddit kapısı kapalı:** API başvurusu 2026-08-11'de reddedildi ("not in compliance
with Responsible Builder Policy"). Onaysız/belgelenmemiş uç nokta kullanmak
RateYourMusic için zaten reddedilen kategoriye girer — yapılmaz.

**Yerine ListenBrainz:** anahtarsız `labs.api.listenbrainz.org/similar-artists`
"bunu dinleyen şunu da dinliyor" veriyor (test edildi: Rush → Led Zeppelin, Pink
Floyd, Queen, Black Sabbath, Van Halen). Bu, forum metninin yerine geçmez ama aynı
işlevi görür: kalabalığın bilgisi. Metin gerekirse Wikipedia/Wikidata açık ve
lisanslıdır.

### K11 — Sende olmayan parçanın ses profili AcousticBrainz'den gelir
Öneri motorunun aday albümü kullanıcının diskinde olmadığı için librosa çalışamaz.
İki yol test edildi ve ikisi de işe yarıyor:
1. **AcousticBrainz** — kayıt MBID'siyle hazır analiz (BPM, dinamik, spektral,
   yüksek düzey sınıflandırıcılar). Örneklemde %92 kapsama. 2022'de donduruldu,
   yani 2022 sonrası yeni çıkanlar eksik.
2. **30 sn önizleme** — iTunes/Deezer'dan çekilip `parca_analiz(--sure 30)` ile
   analiz edilir. Kapsama boşluğunu kapatır ve zaten çalınacak dosyadır.

Kullanıcının önerdiği "kullanıcılar arası bulut havuzu" ELENDİ: sunucu, başka
kullanıcılar ve gizlilik yönetimi gerektiriyor; bu proje tek kişilik ve 0 TL (K2).

**Kaynaklar karışmamalı:** `audio_features.kaynak` sütunu (yerel / acousticbrainz /
onizleme). Önizlemeler AAC'ye sıkıştırılmış ve seviye normalize edilmiş olduğu için
`dinamik_aralik` kaynaklar arası kıyaslanamaz — karşılaştırma kaynak içinde
standartlaştırılır.

### K12 — İcra karakteri MİKSTEN değil, AYRILMIŞ STEM'DEN ölçülür
"Benzer kalibrede davulcu" sorusunun cevabı tüm mikse bakan özniteliklerde YOK.
İki ölçüt tasarlanıp ölçülerek ELENDİ:

1. **Tempogram entropisi** — sekiz sanatçıda 0.878–0.891. Eminem'le Meshuggah aynı.
2. **HPSS + senkop fazı** — Françoise Hardy (0.682) Meshuggah'tan (0.600) yüksek
   çıktı. HPSS yoğun mikste davulu ayıramıyor, onset dedektörü gitar atağını da
   davul sanıyor.

**Çalışan yol: Demucs ile davul stem'ini ayırmak.** Aynı sekiz sanatçıda sonuç
müzikal olarak doğru:

| | nota/vuruş | ızgara-ent | tekme | trampet | zil |
|---|---|---|---|---|---|
| Meshuggah | 2.88 | 0.992 | 21% | **17%** | **62%** |
| Eminem | 1.51 | **0.755** | 39% | 45% | 17% |
| TOOL | 1.96 | 0.901 | **41%** | 37% | 22% |
| Casiopea | 2.73 | 0.989 | 17% | 32% | **52%** |

Haake'nin ride ağırlıklı/trampet cimri stili, Carey'nin tom-tekme ağırlığı ve
Eminem'in programlanmış beat'i (ızgara entropisi 0.755 — makine ızgaraya kilitli,
insan yayılır) doğrudan ölçülüyor.

**Dört enstrümana genellendi (2026-08-16).** Kullanıcının isteği: "sadece davul
için gitmiyorsun değil mi? gitarist ve vocalleri de ekliyorsun." Demucs zaten tek
geçişte dört kaynak üretiyor — davulu alıp diğer üçünü çöpe atmak bedava veriyi
atmaktı. Artık dördü de `stem_profili`'ne yazılıyor.

Ölçüt kümesi role göre değişir (`python/muzisyen.py:ROL_SUTUNLARI`); davulda perde
aranmaz, vokalde tekme payı aranmaz:

| Rol | Stem | Ayırt eden ölçütler |
|---|---|---|
| drums, percussion | `drums` | nota/vuruş, ızgara entropisi, tekme/trampet/zil payı |
| bass | `bass` | perde medyanı, perde aralığı, sustain, parlaklık |
| guitar, keyboards, piano, organ, synthesizer, saxophone | `other` | parlaklık, düzlük (distorsiyon), sustain, perde aralığı |
| vocals, backing_vocals | `vocals` | perde medyanı, perde aralığı, vibrato hızı |

**Bilinen sınır:** Demucs gitarla klavyeyi ayırmaz, ikisi de `other`. Bu roller
aynı ölçütleri paylaşır ve profil enstrümana değil o albümün melodik katmanına
aittir. Ayrı bir gitar modeli yok (htdemucs_6s piyano+gitar ekliyor ama kalitesi
dört-kaynak modelinin altında). Sınır gizlenmiyor, arayüzde yazılı.

**Perde takibinde `pyin` değil `yin`:** pyin'in Viterbi kod çözücüsü albüm başına
43 sn CPU götürüyordu, yin ~7 sn. Fark, perdesiz kareleri ayıklamak için RMS
maskesi eklenerek kapatıldı — pyin'in voicing olasılığı zaten bunu yapıyordu.

**Ölçüt kümesi ELLE SEÇİLMEDİ (2026-08-16).** `python/enrich/olcut_denetimi.py`
her özniteliği diğerlerine regresyon edip artık varyans payına bakıyor; 0.30'un
altı "başkasının kopyası" sayılıp geriye doğru ADIMSAL elemeyle atılıyor
(n≈270). Eleme sırayla yapılmalı: ilk turda `zil_payi` de elenecek görünüyordu,
oysa artıklığını `parlaklik` ile paylaşıyordu ve o zaten eleniyordu — parlaklık
gidince zil_payi eşiğin üstüne döndü. Sonuç: davulda `parlaklik` ve `nota_vurus`
(0.296, sınırda) elendi; diğer üç stem'de yalnız `zcr`. `harmonik_pay` dördünde
de ayakta — gitarda parlaklığın yerini aldı.

**Adaylar da profilleniyor.** `stem_profili.tur = 'aday'`. Kredi grafiği
"kadroda ortak isim var" diyebiliyor ama "bu davulcu senin dinlediğin gibi
çalıyor" diyemiyordu; icra eşleşmesi bunu kapatıyor ve öneri kartında görünüyor.

**Bedel:** demucs + torch ≈ 2 GB, MPS'te klip başına ~12 sn. Bu yüzden ALBÜM
düzeyinde stem ölçülür, MÜZİSYEN düzeyine `credits` üzerinden medyanla çıkılır —
soru "bu icracı nasıl çalıyor", "bu albüm nasıl" değil.

**Kalite koruması:** vuruş başına 0.5 notadan az düşen klip atılır. Ölçüldü —
Ian Paice 0.18 çıkmıştı; klip sessiz bir pasaja denk gelmiş ve medyanı zehirliyordu.

### K8 — Tek dil: her şey Python
Kümeleme dahil tüm boru hattı Python. FCM, Xie-Beni, partition entropy ve bootstrap
Jaccard stabilitesi numpy ile açıkça yazıldı (`python/kumeleme/`), hazır paket
kullanılmadı.

Gerekçe: boru hattının geri kalanı (alım, zenginleştirme, Faz 2 aday üretimi, Faz 3
araştırma) zaten Python; kümeleme ortada tek başına duran bir R adası olacaktı.
İki çalışma zamanı = iki bağımlılık ağacı, dosya tabanlı köprü, iki kez kurulum.

Performans gerekçe DEĞİL: 2000 albüm × ~30 boyutta c taraması + 50 bootstrap iki
dilde de saniyeler sürer. Bu projenin pahalı yeri API zenginleştirmesiydi.

Bedeli kabul edildi: `fclust`/`fpc`'nin test edilmiş geçerlilik indeksleri ve
stabilite yordamı yerine kendi kodumuz. Karşılığında algoritmalar görünür ve
`tests/test_kumeleme.py` ile bilinen yapıyı geri bulmaları doğrulanıyor.

## Teknoloji yığını

| Katman | Araç | Gerekçe |
|---|---|---|
| Metadata & API istemcileri | Python (mutagen, requests + `python/onbellek.py`) | Tek önbellek/rate-limit katmanı |
| Ses analizi | Python (librosa) | Standart |
| Davul ayrıştırma | Python (demucs htdemucs, MPS) | K12 — davulcu karakteri yalnız stem'den ölçülebiliyor |
| Kümeleme | Python (numpy — FCM, Xie-Beni, PE, bootstrap Jaccard elde yazılı) | K8 — tek çalışma zamanı |
| Boyut indirgeme | Python (numpy SVD/PCA; `umap-learn` opsiyonel) | Aynı |
| Arayüz | Starlette + Jinja2 + elle SVG | K15 — Streamlit her etkileşimde betiği yeniden çalıştırıp çalan önizlemeyi kesiyordu |
| Kalıcılık | SQLite | Tek dosya, taşınabilir |
| Özetleme | Çıkarımsal (varsayılan) / Ollama / Anthropic API | K2 — takılıp çıkarılabilir, varsayılan 0 TL |

Tek dil, tek çalışma zamanı (K8). Ara çıktı `data/ozellikler.parquet`, kalıcı veri
SQLite. Aşamalar arası sınır dosya düzeyinde: her adım tek başına çalıştırılabilir.

### K15 — Arayüz: sunucuda çizilen HTML, Streamlit değil (2026-08-18)
Streamlit üç somut sorun çıkardı: (1) her etkileşim tüm betiği yeniden
çalıştırıyor ve ÇALAN ÖNİZLEMEYİ KESİYOR — oysa çekirdek eylem "dinle ve karar
ver"; (2) durum URL'de yok, bağlantı verilemiyor, geri tuşu çalışmıyor;
(3) görünüm ancak Streamlit'in CSS'ini geri döndürerek denetlenebiliyor.

Yerine Starlette + Jinja2 + uvicorn — üçü de zaten kuruluydu, **yeni bağımlılık
yok**. Grafikler elle SVG (`web/grafik.py`): Vega ~350 KB JS ve kendi tipografi
varsayımlarını getiriyordu, sunucuda PNG yakınlaştırınca bulanıklaşıyordu.

Taşıma yalnız görüntü katmanını ilgilendirdi; `python/` altındaki hesap modülleri
hiç değişmedi. Yan kazanç: görüntü katmanı artık test edilebilir.

Çalıştırma: `.venv/bin/python -m web.sunucu`

## Faz planı

### Faz 1 — Ayna (LLM YOK) — TAMAMLANDI
Kütüphaneyi oku → kredilerle zenginleştir → kümele → kullanıcıya kümeleri isimlendirt.
Çıktı: "sen busun" raporu. Öneri yok.
Bu faz bittiğinde uygulama iskeleti de kurulmuş olur.

### Faz 2 — Aday üretimi
Eksen seçimi + eksene özgü aday stratejileri:
- Kredi ekseni → kredi grafiğinde sıçrama (aynı müzisyenin dinlenmemiş projeleri)
- Sahne/coğrafya ekseni → label/dönem/sahne komşuluğu
- Çalma listesi birlikteliği → PMI ile popülerlik sönümlenmiş, PARÇA düzeyinde
  (`python/discover/calma_listesi.py`). Kullanıcı kaydı olmadan ortak
  filtremenin klasik vekili; havuzu 116 sanatçıdan 10.360'a çıkardı.
- "Yepyeni bir şey" → kümelere uzak ama komşuların sevdiği alanlar (bilinçli uzaklık)
  — YAZILDI. Kalabalık grafiğinde iki adım; sıralama ölçütü EKSEN-ÖZGÜLLÜĞÜ
  (kaç ayrı eksenin havuzunda görünüyor), köprü sayısı değil. Köprü sayısıyla
  sıralamak ölçüldü ve mainstream'e düşürdü — Coldplay metal kümesinde çıktı.

### Faz 3 — Gerekçe ve önizleme
Derin araştırma katmanı (Reddit API, incelemeler) + `ozetle()` (varsayılan çıkarımsal)
+ 30 sn önizleme (iTunes Search API — anahtar gerektirmez; alternatif Deezer açık API).
"Neden bu albüm" kısmı K7'ye göre şablonla üretilir, özetlemeden bağımsızdır.
Geri bildirim döngüsü: beğendim / tutmadı / zaten biliyorum — YAZILDI
(`python/geri_bildirim.py`). Eksen ağırlığı güncellenmiyor: kullanıcı ekseni
zaten kendi seçiyor. Bunun yerine İKİ AYRI oran ölçülüyor — zevk isabeti
(«zaten biliyorum» paydaya girmez) ve keşif oranı (girer). Küçük n'de Wilson
skor aralığı; dörtten az kararla strateji hakkında cümle kurulmuyor.
Somut etki: «zaten biliyorum» denen sanatçıların diğer albümleri öneri
listesinde geri plana iniyor.

## Veri kaynakları ve sınırları

| Kaynak | Kullanım | Sınır |
|---|---|---|
| MusicBrainz | Kanonik ID, temel krediler | Rate limit: 1 istek/sn, user-agent zorunlu |
| Discogs | Detaylı krediler, label, ülke | Token gerekli; metal/prog/jazz'da zengin, elektronikte zayıf |
| iTunes Search | 30 sn önizleme + katalog | Anahtarsız, ücretsiz — TEST EDİLDİ |
| Deezer | 30 sn önizleme (yedek) | Anahtarsız, ücretsiz — TEST EDİLDİ |
| AcousticBrainz | Sende OLMAYAN parçanın ses profili | Anahtarsız. Kayıt MBID'siyle. Yeni veri almıyor (2022'de donduruldu) ama arşiv okunabiliyor — örneklemde %92 kapsama |
| ListenBrainz | "Bunu dinleyen şunu da dinliyor" | Anahtarsız (labs uç noktası). Kalabalık sinyali |
| Deezer çalma listeleri | Ortak filtreleme vekili — 482 liste, 45.899 parça, 10.360 sanatçı | Anahtarsız, belgelenmiş uçlar (`search/playlist`, `playlist/{id}`). Sinyal müzikal benzerlik kadar BAĞLAM da taşıyor; PMI ile popülerlik sönümleniyor |
| Reddit | **ŞİMDİLİK KULLANILAMIYOR** | API başvurusu REDDEDİLDİ (2026-08-11). Onaysız uç nokta kullanılmaz — RateYourMusic ile aynı gerekçe |
| RateYourMusic | **KULLANILMAZ** | API yok, scraping ToS'a aykırı |
| Apple Music API | **KULLANILMAZ** | Ücretli geliştirici hesabı ($99/yıl) — K2'ye aykırı. iTunes Search zaten anahtarsız |
| Tidal | Beklemede | Kayıt/onay gerektiriyor (401 döndü) |
| Spotify | **KULLANILMAZ** | 2024 sonunda yeni uygulamalar için `preview_url` kapatıldı |
| CritiqueBrainz | CC lisanslı kullanıcı yorumları | Anahtarsız. Kapsama İNCE — 6 albümde 2 yorum (ölçüldü). Yardımcı sinyal, ana sinyal değil |

### K14 — Dış kaynak iddiası, kendi verimizde karşılığı yoksa yazılmaz
MusicBrainz alias verisiyle aynı kişinin farklı yazımları birleştiriliyor
(`kisi_eslesme`). Ama alias listesi geniş ve bazen yanlış. Kural: bir eşleme
ancak İKİ TARAFI DA kendi kredilerimizde varsa yazılır. "Bu iki ad bende ayrı
ayrı duruyordu, MusicBrainz aynı kişi diyor" durumu birleşir; "MusicBrainz
tanımadığım bir adı da bu kişiye bağlıyor" durumu birleşmez.

Aynı ilke `rol_eslemesi` ve MBID eşleştirmesinde de geçerli: dış kaynak bizim
verimizi zenginleştirir, yerine geçmez.

## Çalışma kuralları

- Her yeni mimari karar `docs/karar-gunlugu.md` dosyasına eklenir (tarih + gerekçe).
- Şema değişikliği `docs/veri-sozlesmesi.md` dosyasına yansıtılır.
- `data/` altındaki hiçbir şey git'e girmez.
- Yeni bir API kaynağı eklenmeden önce rate limit ve ToS durumu bu dosyaya not edilir.
- Faz atlanmaz. Faz 1 bitmeden Faz 2 kodu yazılmaz.

### K13 — Profil ekranı uydurma norm kullanmaz
"Kütüphanene göre sen böyle birisin" demek bir referans gerektirir. Elimizde
"ortalama dinleyici" verisi YOK ve uydurulmuyor. Konum yalnız iki şeye göre
veriliyor: (a) bu kütüphanede gerçekten ölçülmüş uçlar (`profil.CAPALAR`),
(b) kullanıcının kendi isimlendirdiği kümeler. Çapası olmayan eksende konum
cümlesi kurulmaz.

Ölçüm albüm başına tek 30 sn klipten geldiği için her uç değerin yanında o klip
ÇALINABİLİR duruyor — sayıyı doğrulanabilir kılmanın tek dürüst yolu bu.

### K16 — Kullanıcı kaydı yoksa vekil: çalma listeleri
Sektörün ana silahı ortak filtreleme ve yakıtı çok kullanıcının dinleme kaydı.
Bizde tek kullanıcı var, `plays` boş. Klasik vekil çalma listeleri: bir listede
iki sanatçının yan yana durması, insan eliyle verilmiş bir "bunu dinleyen şunu
da dinliyor" işareti.

İKİ TUZAK, ikisi de ölçüldü:
- Tek sanatçılık derlemeler («100% Meshuggah») her aramada başa geliyor ve
  sıfır sinyal taşıyor → bir sanatçı listenin yarısından fazlasını kaplıyorsa
  liste atılır.
- Ham birliktelik popüleri öne çıkarıyor. 22 listelik ilk örneklemde Van Halen
  ↔ Madonna/Haddaway çıktı — 80'ler PARTİ listeleri, sinyal "ikisi de 80'ler".
  → PMI. 482 listede sonuç müzikal olarak doğru.

**Çalma listesi sinyali müzikal benzerlik kadar BAĞLAM da taşır** (spor, chill,
parti). Bu bir kusur değil ayrı bir bilgi; liste başlıkları saklanıyor ve
"dinleyici tipi" etiketlerinin kaynağı olacak.

### K17 — Sahiplik zaten tercih sinyalidir
Kullanıcının düzeltmesi (2026-08-18): "sahip olduğumu seviyorum, bu yüzden
kümeliyoruz." Kütüphane kürasyonla kurulmuş; 302 albümün her biri bir "evet".
`plays` tablosunun boş olması TEMEL BİR EKSİK DEĞİL, bir zenginleştirme
fırsatı. Sistem sahiplikle çalışacak şekilde kurulur; dinleme geçmişi gelirse
gerekçeler zenginleşir, gelmezse hiçbir şey bozulmaz.

Asıl iş bundan sonra basit: "şu eksende BENDE OLMAYAN bir şey ver."

### K18 — Tür etiketi zorunlu değil: ses kendi türünü söyler
"Müzik genrelerine takılı kalmayalım, gerekirse tüm müzikleri analiz edip yeni
genreler keşfedelim." `python/ses_kume.py` CLAP gömüsünü kümeleyip türü SESTEN
çıkarıyor — hiçbir etiket, kredi ya da metadata kullanmadan.

Bu, `memberships`'in yerine geçmiyor; onunla uyumu ARI 0.073, yani başka bir
şey görüyor. İkisi yan yana duruyor: biri "kim çalmış", diğeri "kulağa nasıl
geliyor".

Küme adları UYDURULMUYOR, merkeze en yakın sanatçılarla anlatılıyor
("Casiopea · Takanaka · Plini gibi").

## Kullanıcı bağlamı

**Projenin çıkış noktası (kullanıcının kendi ifadesi):** "Ben hep DAP'tan yerel
kütüphanemi dinliyorum, ancak bu böyle olunca yeni müzikler keşfedemiyorum."

**Ve işin özeti, yine kendi ifadesiyle:** "j-fusion önerisi istediğimde elimde
olmayan bir öneri gelsin. bu kadar basit."
Sistem bu kapalı döngüyü kırmak için var. Kullanıcı bunu kendisi için yapıyor;
akademik bir teslim değil, günlük kullanacağı bir alet.

Çalışma tarzı: **düzenli ve ayrıntı seven**. Kaba/özet çıktı yerine ince taneli,
gerekçeli çıktı bekler. "6 küme" gibi kaba bölmeler yetmez; ayrımın nerede
olduğunu görmek ister. Emin olunmayan yerde sorulmasını ister; gerektiğinde
hocasına danışıp geri bildirim getirebilir.

İstatistik yüksek lisans öğrencisi; R ve Python'da rahat, kümeleme metodolojisine hakim.
Kümeleme tercihlerinde teknik gerekçe bekler, basitleştirilmiş açıklama istemez.
Dinleme profili: teknik/prog metal, jazz-fusion, gitar virtüözleri, Türk rock, hip-hop.
Enstrümantal derinlik ve performans kalitesi önceliklidir — bu, kredi ekseninin neden
merkezde olduğunu açıklar.

### K19 — Her değişiklik ölçülür: leave-one-artist-out (2026-09-01)
"Öneri iyi mi?" sorusu kulakla cevaplanmaz. `python/degerlendirme.py` her
erişim yoluna sayı verir; bundan sonraki hiçbir yöntem değişikliği ölçülmeden
üretime girmez.

Sınama: kütüphanedeki bir sanatçının TÜM albümleri gizlenir, motor onu geri
getirebiliyor mu diye bakılır. Albüm değil sanatçı gizlenir — çünkü kullanıcının
ölçütü "hiç duymadığım sanatçı" ve albüm gizlemek sanatçıyı kütüphanede
bırakacağı için tam olarak kaçınılan şeyi ("zaten biliyorum") ölçerdi.

Raporlanması ZORUNLU olanlar:
- **tavan** — gizlenen sanatçı ilgili havuzda var mı? Erişilemeyen sanatçı
  sıralama hatası değil, kapsama boşluğudur; karıştırılırsa yanlış işe
  yatırım yapılır.
- **iki payda** — recall(tüm gizlenenler) ve recall(havuzda olanlar).
- **kıyas** — tek bir sayı anlamsız; her ölçüm bir alternatifle birlikte.

Sayının sınırı da yazılır: gerçek etiket yalnızca sahip olunan 147 sanatçı için
var, gizleneni geçen adayların çoğu da iyi öneri olabilir (missing-not-at-random).
Bu yüzden mutlak seviye değil, yöntemler arası KIYAS güvenilirdir.

Değerlendirme kodu üretim kodunu ÇAĞIRIR ama kopyalamaz; kopyalarsa üretimdeki
hatayı ölçemez. Kopyalanması gereken tek yer üretimin değerlendirmeyi imkânsız
kılan kısıtları (kütüphaneyi aday havuzundan çıkarmak gibi) ve o zaman sebebi
yazılır.
