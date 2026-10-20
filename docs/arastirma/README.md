# Araştırma — öneri sistemleri, müzik önerisi, ses, dinleyici sesi, açık veri, değerlendirme

2026-10-20. Altı paralel araştırma ajanı. Bu belge onların **sentezi** ve
motorun (`python/motor.py`) hangi bulguya dayandığının haritası. Ayrıntı ve
tam kaynak listeleri bu klasördeki altı raporda.

| Rapor | Konu | Kaynak |
|---|---|---|
| [1-oneri-algoritmalari.md](1-oneri-algoritmalari.md) | Tapestry 1992 → 2026: CF, MF, BPR, SLIM, P3α/RP3β, EASE, sinir ağları, GNN, LLM | 72 |
| [2-muzik-onerisi.md](2-muzik-onerisi.md) | Uzun kuyruk, RecSys Challenge 2018, popülerlik/dil yanlılığı, çeşitlilik, bandit | ~60 |
| [3-ses-ve-muzik-teorisi.md](3-ses-ve-muzik-teorisi.md) | Tını benzerliği, hubness, ritim/armoni öznitelikleri, gömü modelleri, müzik psikolojisi | ~70 |
| [4-dinleyici-sesi.md](4-dinleyici-sesi.md) | Reddit, HN, Spotify topluluğu, forumlar, müzik basını | ~90 URL |
| [5-acik-veri-kaynaklari.md](5-acik-veri-kaynaklari.md) | 35 ücretsiz kaynak: lisans, ToS, sınır, uygunluk | 35 |
| [6-degerlendirme-ve-siralama.md](6-degerlendirme-ve-siralama.md) | Çevrimdışı değerlendirme, küçük veride sıralayıcı öğrenme, istatistiksel test | ~50 |
| [7-algoritma-dogrulama.md](7-algoritma-dogrulama.md) | **Tam metin:** RP3β, EASE/EDLAE + Woodbury, Aiolli, Dacrema ayarı, GF-CF, Pixie, kalibrasyon | sayfa künyeli |
| [8-muzik-dogrulama.md](8-muzik-dogrulama.md) | **Tam metin:** Lesota, Kowald, vl6, Zamani, Anderson, BaRT, Tamm & Aljanaki, Sandler 2026 | sayfa künyeli |
| [10-kaynak-dogrulama.md](10-kaynak-dogrulama.md) | **Asıl koşul metinleri** + kapsama ölçümü (Wikidata, MusicBrainz, ListenBrainz, Deezer) | ham sayfalar |

## Yöntemin sınırları — okumadan önce

- **"Tüm makaleler, tüm yorumlar" okunmadı; okunamaz.** Alan on binlerce makale.
  Yapılan: her alt alanın kurucu ve en çok atıf alan işleri, tekrarlanabilirlik
  çalışmaları ve 2023–2026 yenileri, toplam ~210 web araması.
- **İlk dalgada tam metin yoktu.** WebFetch hiçbir alan adını çözemedi ve ağ
  politikası arXiv/ISMIR'e çıkışı kapatıyordu; 1–6 arama özetlerinden.
  Raporlar her iddiayı işaretliyor († / [B] / [H] = önceki bilgiden).
  Ağ açıldıktan sonra **ikinci dalga (7, 8, 10) makaleleri ve koşul metinlerini
  tam okudu** ve ilk dalgayı düzeltti (aşağıda). Topluluk iplerinin tam
  okuması (9) ayrı.
- **Reddit ve forumlar yalnız OKUNDU.** Motor bunlardan veri çekmiyor: Reddit API
  başvurusu reddedildi, onaysız uç nokta kullanılmaz (K10). Okumanın ürünü
  tasarım ilkeleri ve sınama için insan eliyle kurulmuş "X'i seven Y'yi dener" çiftleri.

## On bulgu ve motordaki karşılıkları

| # | Bulgu | Kaynak | Motorda |
|---|---|---|---|
| 1 | **Ölçümümüz sızdırıyordu.** Listeler her kütüphane sanatçısının ADIYLA aranarak toplandı; gizlenen sanatçının listeleri sınamada kalıyordu. Üretimde tanımadığın sanatçının adı aranmaz. Tavan ve liste yolunun sayıları şişikti. | iki ajan bağımsız (1, 6); kodda doğrulandı | `degerlendirme.sizinti_listeleri` — **varsayılan açık**; `--eski-protokol` eskiyi üretir |
| 2 | **İyi ayarlanmış basit doğrusal yöntemler sinir ağlarını geçiyor.** | Ferrari Dacrema 2019/2021; Rendle 2020; Ludewig & Jannach 2018 | Sinir ağı yok. RP3β + EASE |
| 3 | **Elle süpürdüğümüz düğmeler RP3β ailesinin noktaları** (liste boyutu ağırlığı = α, PMI'nın popülerlik cezası ≈ β, `MAX(pmi)` = Aiolli yerelliğinin γ→∞ ucu). | Cooper 2014; Christoffel 2015; Paudel 2017; Aiolli 2013 | `motor.rp3`, α·β·bağlam ızgarası |
| 4 | **EASE 482 satırda Woodbury ile ucuz:** 10k×10k yerine 482×482 ters alma. | Steck 2019 | `motor.ease`; doğrudan çözümle eşitliği test ediliyor |
| 5 | **Füzyon ağırlığı aynı sorgularda seçilmişti** → öğrenilmiş sıralayıcı, iç içe CV. Gizleme bir eşleşmiş vaka–kontrol düzeni: koşullu logit. | Varma & Simon 2006; Cawley & Talbot 2010; McFadden; Volkovs 2018 (vl6: aday üret + yeniden sırala) | `motor.logit_egit`, `degerlendirme.motor_olc` |
| 6 | **Sahiplik etiketleri popülere kayıyor.** PDA (popülerliği eğitimde kullan, öneride kapat) denendi: yapılı yapay veride motoru çökertti, çünkü ortak liste sayısı popülerlikle ilişkili. Çıkarıldı; popülerlik cezası RP3β'nın β'sında. | Steck 2011; Kowald 2020; Zhang 2021 (PDA) | `rp3(beta=…)`, «görünür» sütunu |
| 7 | **Ortak görülme yerel dili birbirine bağlar.** Sezen Aksu vakası tesadüf değil, ItemKNN'nin bilinen özelliği; liste ve ses sinyali İKİSİ DE dil taşıyabiliyor. | Lesota 2022 (ISMIR); dinleyici şikâyetlerinde 3. sırada | Bağlam listesi ağırlığı (`baglam_listesi_mi`), ızgarada seçiliyor |
| 8 | **"Yeni eskiyi geçti mi?" testi eşli olmalı;** Wilcoxon sıfır farklarda bozuluyor. | Smucker 2007; Urbano 2019 | `motor.eslesmis_kiyas`: işaret çevirmeli permütasyon + eşli bootstrap |
| 9 | **CLAP gömüsü tekrarlanabilir değildi:** HF işlemcisi 10 sn'den uzun girdiyi tohumsuz `np.random` ile kesiyor. Kütüphane ve havuz farklı boru hattından geçiyor (stem toplamı 22 kHz ↔ ham önizleme). | ses ajanı; transformers kaynak kodunda doğrulandı | `etiket_clap.pencereler`: sabit 0–10/10–20/20–30 sn; `--yeniden` |
| 10 | **Dinleyicinin ilk üç şikâyeti:** bildiğini önermek, aynı sanatçıyı tekrar getirmek, dili tarz sanmak. Güveni artıran: ortak müzisyen, sayısal ve çalınabilir kanıt. | rapor 4 | İlk ikisi zaten vardı (K21). Üçüncüsü bulgu 7. Kanıt motor kartında: ortak liste sayıları |

## İkinci dalganın düzeltmeleri (tam metinden)

- **RP3β** motordaki formül Dacrema 2019'un resmî koduyla aynı:
  `S_i· = d_i^−α (x_iᵀ diag(n^−α) X) ⊙ d^−β`. Kod varsayılanı α=1, β=0,6;
  ızgara α 0–2'ye genişletildi (Cooper 2014'ün en iyisi 1,9).
- **EASE/Woodbury** doğrudan tersle ≤1e-15 farkla aynı. m<n iken λ→0 sonlu:
  EASE listelerin gerdiği uzaya izdüşüme dönüşüyor.
- **Ses modeli değiştirme ŞİMDİLİK HAYIR.** Tamm & Aljanaki 2026'nın eğitimsiz
  KNN tablosunda MuQ SONUNCU, MERT birinci. Önceki raporun «MuQ en iyi» okuması
  eğitilmiş modellerden. CLAP ile MuQ'yu doğrudan kıyaslayan makale yok.
- **Dil sızıntısının yayımlanmış karşılığı var.** Lesota 2022: ItemKNN yerli
  payı kullanıcının gerçek dinlemesinden yüksek öneriyor; adı geçen dört ülkeden
  biri TR. Lesota 2024: ortalama yerli pay değil, kullanıcı başına ülke
  kalibrasyonu (JSD) bakılacak ölçü.
- **Sandler 2026 (LAION-CLAP, arXiv 2609.30568).** Küratörler en yakın kosinüs
  komşularının %38'ini reddetmiş; reddedilenlerin %14,6'sının sebebi yanlış dil.
  Kosinüs kabulle reddi zor ayırıyor (AUC 0,644). Çözüm: aday üretiminde dil
  süzgeci ve öğrenilmiş doğrusal yeniden ağırlıklandırma. Tek yazarlı, körlemesiz.
- **vl6:** komşu skorlarına `pop^−(1−β)` cezası; liste «homojenliği» en önemli
  özniteliklerden. 135–250 sanatçılı kişisel karışım listelerini kısmak için
  ucuz bir düğme.
- **PDA çıkarıldı:** yapılı yapay veride motoru çökertti (bulgu 6).

## Koşul metinleri — uyumluluk (rapor 10, asıl metinler okundu)

| Kaynak | Bulgu | Durum |
|---|---|---|
| ListenBrainz | «never make more than ONE call per second»; iletişimsiz UA engellenebilir | **Düzeltildi:** 0,6 → 1,05 sn, `onbellek.ajan()` |
| MusicBrainz / Wikidata | UA'da gerçek iletişim şart; yer tutucu e-posta kullanılıyordu | **Düzeltildi:** depo adresli varsayılan |
| Discogs API | Koşul: içerik 6 saatten eskiyse gösterilmez, gerekenden uzun saklanmaz. «Data provided by Discogs» atfı ister | **Çelişki — kullanıcı kararı.** Önerilen: CC0 aylık döküm |
| Last.fm | Yalnız ticari olmayan kullanım; toplam 100 MB saklama; herkese açık sayfa için yazılı onay | Eklenmedi; eklenmeden önce yazılı onay |
| Deezer | Ses verisinin yerel saklanması **kesin yasak**; içerik «aile içi özel kullanım» | **Çelişki — kullanıcı kararı:** `tur_sinif.py`, `icra_profili.py` Deezer önizlemesinden üretilen stem'leri diskte tutuyor |
| Setlist.fm | Yalnız kısa süreli önbellek | Kullanılmıyor |
| Wikidata kapsaması | Etki (P737) 15 sanatçının 1'inde; tür ve ülke 15/15 | Etki ekseni için yetersiz; ülke/kimlik eşleme için iyi |

## Uygulananlar (2026-10-20)

1. **Sınama sızıntısı düzeltildi.** Bundan önceki bütün K19 sayıları eski
   protokolle ölçüldü ve yeniden ölçülmeli. Liste yolunun düşmesi bekleniyor.
2. **Motor** (`python/motor.py`): RP3β ve EASE, bağlam ağırlığı, koşullu logit
   füzyonu (öncül = bugünkü melez).
   - Ölçüm: `python -m python.degerlendirme --motor --olcut npmi --buzulme 1 --melez-agirlik 1,2`.
   - Ayar: `python -m python.motor --egit`.
3. **Destede `motor` kaynağı.** Payını Thompson örneklemesi gerçek kararlardan
   belirliyor (K21); kötüyse kendiliğinden az kart alır.
4. **CLAP sabit pencereler.** Kütüphane ve havuz BİRLİKTE yeniden gömülmeli:
   `python -m python.etiket_clap --gomu --yeniden` ve
   `python -m python.etiket_clap --parca-gomu --yeniden`.

## Sıradakiler — kanıt sırasıyla, hepsi K19'dan geçecek

| Öncelik | İş | Neden | Kaynak |
|---|---|---|---|
| 1 | Gerçek veride `--motor` ölçümü | Motor ölçülmeden varsayılan sayılmaz | — |
| 2 | Ses benzerliğinde Mutual Proximity / yerel ölçekleme | Şimdiki "hubness düzeltmesi" cebirsel olarak ortalama merkezleme; MP tutarlı kazanç veriyor | Schnitzer 2012; Feldbauer & Flexer 2019 |
| 3 | Sanatçı başına 3–5 klip, en iyi k çiftin ortalaması | Tek klip bir pasajın tesadüfü | rapor 3 |
| 4 | Vokalsiz CLAP (davul + bas + other) | Sezen Aksu vakasında ses sinyali Türkçe kadın vokale eşleşti | rapor 2 |
| 5 | Dil/popülerlik eşleşmiş sıfır model | Başlık sözlüğü listelerin yalnız %17'sini yakalıyor; içerikten dil çıkar | Lesota 2022 |
| 6 | Deste içi MMR (CLAP) + eksen kalibrasyonu | Arka arkaya aynı tınıda kart gelmesin | Carbonell & Goldstein 1998; Steck 2018 |
| 7 | Kararlardan çevrimiçi güncelleme: η = β₀ + γ·(motor skoru) + δᵀx | γ'nın sonsalı "çevrimdışı ölçüm gerçek zevki ne kadar öngörüyor" sorusunun cevabı | rapor 6 |
| 8 | Ölçü/ritim (Beat This!) ve armoni (TIV, tonal karmaşıklık) | Prog/füzyon dinleyicisi benzerliği tür adıyla değil ölçü ve armoniyle tarif ediyor | rapor 3, 4 |
| 9 | MusicBrainz artist-rels, Discogs CC0 dökümü, Wikidata P737 | Kadro/etki grafiği; Discogs API'nin saklama maddesi K5 ile çelişebilir (doğrulanmadı) | rapor 5 |
| 10 | Team-draft interleaving | İki sıralayıcıyı az kararla kıyaslamak | Radlinski 2008; Chapelle 2012 |

**Yapılmayacaklar:** NCF, GNN, ardışık modeller, two-tower, difüzyon ve LLM
önericiler. 482 satırda düşük ranklı modeller (iALS, BPR, SLIM) uzun kuyruğu
sıkıştırıyor. Tekrarlanabilirlik çalışmalarında basit taban çizgilerine
kaybediyorlar. Ayrıca K2'ye aykırılar.
