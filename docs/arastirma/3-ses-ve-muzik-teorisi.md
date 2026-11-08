# 3 — Ses, akustik ve müzik teorisi: benzerlik ve tercih için öznitelikler

Tarih: 2026-10-20 · Kapsam: tını benzerliği tarihi, hubness, armoni / ritim / dinamik
öznitelikleri, Essentia yüksek düzey betimleyicileri, önceden eğitilmiş gömüler,
gömü birleştirme, müzik tercihi psikolojisi. Sonra bunların bu projeye (30 sn
önizleme, CPU/M1, 0 TL, LLM yok) uygulanması.

---

## 0. Yöntem notu: neyi doğruladım, neyi doğrulayamadım

- Bu oturumda 37 web araması yapıldı. Ardından **arama bütçesi bitti**: sınır,
  oturumdaki bütün ajanların paylaştığı 200 arama. Birincil kaynakların çoğu bu
  ortamdan **erişilemiyor**: arxiv.org, archives.ismir.net, jmlr.org,
  ncbi.nlm.nih.gov, huggingface.co ve essentia.upf.edu DNS ya da vekil
  sunucu (proxy) tarafından reddedildi. GitHub erişilebilir. Bu yüzden lisans ve
  arayüz bilgilerini GitHub README'lerinden ve kaynak koddan doğruladım.
  Makale bulgularını ise arama sonuçlarındaki özetlerden ve abstract'lardan aldım.
- Kaynakçada her girdi işaretli:
  - **[D]** bu oturumda bir kaynak üzerinden doğrulandı (özet, README ya da kaynak kod);
  - **[B]** bu oturumda doğrulanamayan, alan bilgisine dayanan kaynak. Künye
    büyük olasılıkla doğru ama sayı ya da ayrıntı aktarmadan önce kontrol edilmeli.
- Projenin kodunu okudum: `python/etiket_clap.py`, `python/ses_kume.py`,
  `python/enrich/icra_profili.py`, `python/enrich/ses_ozellikleri.py`. Önerileri
  mevcut yapıya göre yazdım. Repoda hiçbir dosya değiştirilmedi.

---

## 1. Önce: kodda bulunan üç somut sorun (en ucuz, en yüksek getirili düzeltmeler)

### 1.1 CLAP gömüsü deterministik değil ve 30 sn'nin yalnız 10 sn'sini görüyor
`etiket_clap.klip_gomusu` ve `gomu_cikar`, 30 sn'lik sesi doğrudan
`ClapProcessor`'a veriyor. Hugging Face `ClapFeatureExtractor` kaynak kodunu
doğruladım [D, transformers `feature_extraction_clap.py`]:

- `max_length_s=10` (48 kHz'te 480 000 örnek). Daha uzun girdi kırpılıyor.
- `truncation="rand_trunc"` ise kırpma yeri **rastgele**:
  `idx = np.random.randint(0, overflow + 1)`.
- `truncation="fusion"` (varsayılan) ise ön, orta ve arka parçalar `np.random.choice` ile seçiliyor.
- `frequency_max = 14000` Hz.

Sonuç olarak aynı klip iki kez gömüldüğünde farklı vektör çıkabilir ve
klibin üçte ikisi atılıyor. Bu, K2'nin "sonuç tekrarlanabilir olmak zorundadır"
ilkesine aykırı. Model 10 sn'lik pencereyle eğitildiği için, Haken'in akustik
bir anına denk gelme riski de üç kat büyük.

**Düzeltme:** klibi deterministik pencerelere böl, her pencereyi ayrı göm,
ortalamayı al ve L2 ile normalize et. Örnek pencereler: 0–10, 10–20, 20–30 sn;
daha iyisi %50 örtüşmeyle 0–10, 5–15, …, 20–30. Maliyet klip başına üç–beş kat
CLAP çağrısı demek; ölçülmüş hızla (~1 sn/klip) 3–5 sn eder. Pencere vektörleri
de saklanabilir, böylece aşağıdaki küme–küme benzerliği (§13.3) kullanılabilir.
Sınama: aynı klibi iki kez göm; kosinüs 1.0000 olmalı.

### 1.2 Kütüphane ve aday aynı boru hattından geçmiyor
- Kütüphane albümleri (`gomu_cikar`): Demucs'un dört stem'i toplanıyor.
  Stem'ler **22.05 kHz**'te (`icra_profili.CALISMA_ORNEKLEME`), sonra 48 kHz'e
  yükseltiliyor. Bant 11.025 kHz'te kesik, Demucs'un yeniden sentez izlerini
  de taşıyor.
- Adaylar ve yeni kullanıcı albümleri (`onizleme_gomusu`, `aktarim.gomule`):
  ham MP3/AAC önizleme doğrudan 48 kHz'e çevriliyor. Bant ~16 kHz'e kadar dolu,
  CLAP 14 kHz'e kadar görüyor.

Bu, K11'in "kaynaklar karışmamalı" uyarısının gömü uzayındaki karşılığı.
11–14 kHz bandı ve Demucs izleri, sistematik bir **kaynak yönü** oluşturabilir.
Benzerlik o zaman kısmen "hangi boru hattından geçti" sorusunu ölçer.

**Düzeltme:** iki tarafı tek yoldan geçir. En basiti her şeyi ham önizlemeden
gömmek. Stem toplamı kullanılacaksa adaylar da aynı yoldan geçmeli.

**Ölçüm:** 50 kütüphane klibini iki yoldan da göm. Yollar arası kosinüsün
dağılımına bak. Ayrıca ilk birkaç temel bileşenin (PC) `yol` değişkeniyle
korelasyonunu ölç. K19 gizleme sınamasıyla iki yolu da karşılaştır.

### 1.3 "Hubness düzeltmesi" aslında global merkezleme
Kodda `S = A_aday·A_uyeᵀ − taban_aday − taban_uyeᵀ` hesaplanıyor. Burada
`taban_aday = A_aday · m` ve `m` kütüphane vektörlerinin ortalaması. Cebirle:

```
S(a,u) = a·u − a·m − u·m = (a − m)·(u − m) − ‖m‖²
```

Yani bu, kütüphane ortalamasıyla **merkezlenmiş iç çarpım**. Tek fark, yeniden
normalize edilmemiş olması (kosinüs değil). `‖m‖²` sabit olduğu için sıralamayı
etkilemez. Literatürdeki adı "global centering" (Suzuki vd. 2013 [B]).

Feldbauer ve Flexer'in karşılaştırmalı çalışması ölçeklemenin (yerel ölçekleme ve
Mutual Proximity) hubness'ı tutarlı biçimde azalttığını ve k-NN doğruluğunu
artırdığını buluyor. Merkezlemenin sonuçları ise karışık [D: OFAI TR 2016-05
özeti; KAIS 2019]. Yani projenin "beşinci kez aynı çözümü" doğru ailede ama ailenin
en zayıf üyesi. Yükseltme önerisi §3.4'te.

---

## 2. Tını benzerliğinin tarihi ve "cam tavan"

**Ana çizgi:**
- Logan ve Salomon (2001): MFCC + k-means + Earth Mover's Distance [B].
- Aucouturier ve Pachet (2002): her parçaya MFCC üzerinde GMM, Monte Carlo ile
  KL yaklaşımı [D, ISMIR 2002 metni listede].
- Mandel ve Ellis (2005): tek Gauss + kapalı biçimli KL [B].
- Pampalk (2006): tını (G1C) ile fluctuation patterns birleşimi [D: Pampalk'ın
  2006 birleşik modeli].
- Pohle vd. (2009) ve Seyerlehner vd. (2010): blok düzeyi öznitelikler; MIREX
  Ses Müzik Benzerliği (AMS) yarışmalarının galipleri [D/B].

**Cam tavan (Aucouturier ve Pachet 2004):** Çok sayıda parametre ve
algoritma varyantı denendi. Mevcut algoritmalara göre R-precision'da yaklaşık
%15 kazanç sağlandı. Ama çoğu varyant fark yaratmadı. Simülasyonlar
**~%65 R-precision'da bir "cam tavan"** gösteriyor ve aynı yaklaşımın
varyasyonlarıyla aşılamayacağı öngörülüyor [D]. Aynı yazarlar hub olgusunu
da ilk fark edenler arasında: bazı parçalar "her şeye benziyor", çünkü GMM'ler
homojenleşiyor (Karydis vd. 2010'un aktarımıyla [D]). Aucouturier ve Pachet
(2008) bunu ölçekten bağımsız bir yanlış pozitif dağılımı olarak formüle etti
[B, Pattern Recognition].

**Bu projeye dersleri:**
1. Daha iyi bir tını temsili, benzerliğin tavanını ancak sınırlı biçimde
   yükseltir. CLAP, MFCC-GMM'den çok daha güçlü ama yine "kulağa nasıl geliyor"
   ekseninde. Kullanıcının asıl ayrımları başka eksenlerde: tek ölçü, armonik dil,
   icra yoğunluğu. Bunlar zaten K12'nin stem yolundan geliyor. Sonraki yatırım
   tınıya değil, **ritim ve armoni görünümlerine** yapılmalı.
2. İnsan değerlendiriciler arası uyum da bir tavan koyar. MIREX AMS
   yargılarında değerlendiriciler arası uyum sınırlı. Flexer (2014) bunun
   algoritmalara bir üst sınır çizdiğini gösterdi [B]. Bu, K19'un "mutlak düzey
   değil, yöntemler arası kıyas güvenilir" ilkesini destekliyor.

---

## 3. Hubness: kuram, MIR bulguları ve uygulama

### 3.1 Olgu
Yüksek boyutta bazı noktalar (hub'lar) çok sayıda noktanın k-en-yakın
komşusu olur. Komşuluk ilişkisi asimetrikleşir. Hiç kimsenin komşusu olmayan
"yetimler" (anti-hub) da ortaya çıkar. Ölçüt: N_k'nın (k-oluşum sayısı)
çarpıklığı S_k (Radovanović vd. 2010 [B]; Schnitzer vd. 2012 [D]).

### 3.2 MIR bulguları
- **Schnitzer, Flexer, Schedl, Widmer (2011, ISMIR):** Mutual Proximity
  (MP), standart içerik tabanlı benzerlikte hub sayısını düşürdü ve k-NN tür
  sınıflandırmasını iyileştirdi [D].
- **Schnitzer vd. (2012, JMLR 13:2871–2902):** yerel ölçekleme ve önerilen
  global yöntem (MP) incelendi. Global yöntemin yaklaşıklaması büyük veride
  kolay, olasılıksal bir yorumu var. Çok sayıda veri setinde hubness'ı güçlü
  biçimde azaltıp sınıflandırma doğruluğunu artırdılar [D].
- **Flexer, Schnitzer, Schlüter (2012, ISMIR, en iyi makale ödülü):** MIREX AMS
  sonuçlarında hubness'ın meta-analizi [D].
- **Flexer, Schnitzer, Gasser, Pohle (2010, ISMIR):** hub sorunu 250 000+
  şarkılık koleksiyonlarda da var ve koleksiyon büyüdükçe artıyor. **Farklı
  benzerlik yönlerini birleştirmek hubness'ı azaltıyor** ve benzerlik kalitesi
  korunuyor [D]. Bu bulgu §10'daki füzyon önerisine doğrudan dayanak.
- **Feldbauer ve Flexer (2019, KAIS, DOI 10.1007/s10115-018-1205-y):** bütün
  denetimsiz hubness azaltma ailelerinin büyük ölçekli karşılaştırması.
  Aileler: yerel/global ölçekleme, ortak komşu yaklaşımları, global/yerel
  merkezleme, yoğunluk gradyanı düzleştirme (DisSim) [D]. Yazarların önceki
  raporu: ölçekleme tutarlı biçimde iyi, merkezleme karışık [D].
- **Gömülerde hubness (2023–2025):** Sentence-BERT uzaylarında hubness azaltma
  semantik aramayı iyileştiriyor (arXiv 2311.18364 [D başlık]). Çapraz kipli
  aramada (CLAP dahil) sorgu/galeri bankası normalizasyonu ve Sinkhorn
  yöntemleri var (arXiv 2310.11612, 2508.02538 [D başlık]). CLAP'in kip
  boşluğu (modality gap) merkezlemeyle yalnız kısmen kapanıyor
  [D, ikincil özet].

### 3.3 Formüller (numpy ile birkaç satır)
`d_xy`, x ile y arasındaki uzaklık (ör. 1 − kosinüs) olsun.

- **Yerel ölçekleme (LS):** `LS(x,y) = 1 − exp(−d_xy² / (σ_x σ_y))`.
  `σ_x`, x'in k'inci en yakın komşusuna uzaklığı (Zelnik-Manor ve Perona 2004 [B]).
- **NICDM:** `d_xy / sqrt(μ_x μ_y)`. `μ_x`, x'in k en yakın komşusuna ortalama uzaklığı [B].
- **Mutual Proximity, Gauss yaklaşımı:**
  `MP(x,y) = (1 − Φ((d_xy − μ_x)/σ_x)) · (1 − Φ((d_xy − μ_y)/σ_y))`.
  Yeni uzaklık `1 − MP`. `μ_x` ve `σ_x`, x'in bütün referans kümesine uzaklıklarının
  ortalaması ve standart sapması.
- **Mutual Proximity, empirik:**
  `MP(x,y) = |{j : d_xj > d_xy ve d_yj > d_xy}| / (n − 2)`.
- **CSLS** (Conneau vd. 2018 [B]): `2·cos(x,y) − r_k(x) − r_k(y)`. `r_k`, k en
  yakın komşuya ortalama kosinüs. Projedeki düzeltmenin k-NN'li hâli bu:
  ortalama bütün kütüphane yerine en yakın k komşu üzerinden alınıyor.

### 3.4 Bu projeye öneri (sırayla dene, her adımı K19 ile ölç)
1. **Merkezle ve yeniden normalize et.** Ortalama `m`'yi kütüphane ile aday
   havuzunun birleşiminden al (daha nötr), ya da yalnız kütüphaneden ("kütüphane
   içinde ayırt edici olan"). Sonra kosinüs kullan. Mevcut hâli bundan
   yalnız normalizasyon kadar farklı.
2. **"All-but-the-top"** (Mu ve Viswanath 2018 [B]): merkezledikten sonra en
   baskın D bileşeni at (D ≈ d/100, 512 boyutta 3–5). Önizleme gömülerinde ilk
   bileşenler çoğunlukla ses yüksekliği, kodek, kayıt dönemi ya da boru hattı
   gibi müzik dışı yönleri taşır. **Önce ölç:** ilk 10 PC'nin `kaynak`, `yol`,
   çıkış yılı ve LUFS ile korelasyonu. Yalnız karıştırıcı (confound) olanları at.
3. **Mutual Proximity (Gauss) ya da LS (k=10).** Aday sıralamasında `μ` ve `σ`,
   adayın bütün kütüphaneye, kütüphane albümünün de bütün aday havuzuna
   uzaklıklarından hesaplanır. 10 000 × 302 matriste MP milisaniyeler sürer.
4. **Raporla:** S_k (k=10) önce ve sonra; en büyük 10 hub'ın N_k değeri;
   yetim oranı; K19 recall'u (iki payda). Uyarı: MP yalnız komşu sıralamasını
   düzeltir, mutlak benzerlik ölçeğini değiştirir. Arayüzde gösterilen sayılar
   (ör. "benzerlik 0.83") bu yüzden yeniden tanımlanmalı. Yüzdelik göstermek en dürüstü.

---

## 4. Armonik öznitelikler

### 4.1 Kroma ve türevleri
- **Kroma** (librosa `chroma_cqt`, `chroma_cens`; Müller ve Ewert'in Chroma
  Toolbox'ı [B]): 12 perde sınıfında enerji. CENS, nicemlenmiş ve yumuşatılmış
  hâli; tını ve dinamiğe dayanıklı.
- **Tonnetz / tonal merkez** (Harte, Sandler, Gasser 2006 [B];
  `librosa.feature.tonnetz`): kromayı beşliler, küçük üçlüler ve büyük üçlüler
  çemberlerine yansıtan 6 boyutlu vektör. Ardışık tonal merkezler arası
  Öklid uzaklığı **HCDF** (harmonik değişim fonksiyonu) verir. Tepe sayısı
  dakikadaki akor değişimini, yani armonik ritmi yaklaşık olarak ölçer.
- **TIV — Tonal Interval Vector** (Bernardes vd. 2016; TIV.lib, Ramires vd. 2020,
  DAFx [D]): L1-normalize kromanın ağırlıklı DFT'si, 6 karmaşık katsayı.
  Büyüklüklerin anlamı [D]: ‖T(2)‖ ikilik, ‖T(3)‖ üçlülük, ‖T(5)‖ **diatoniklik**,
  ‖T(6)‖ tam-ton karakteri. TIV.lib ayrıca harmonik değişim, aralıksal
  dissonans, kromatiklik ve tonalite hesaplıyor. Python'da, transkripsiyonsuz,
  çok sesli ses üzerinde çalışıyor [D]. Almeida, Bernardes, Weiß (ISMIR 2022)
  TIV özniteliklerini klasik müzikte dönem ve besteci sınıflandırmasında kullandı [D].

### 4.2 Tonal karmaşıklık (Weiß ve Müller)
Kromadan istatistiksel ölçüler türetiliyor. Bunlar orkestrasyon ve tınıdan
büyük ölçüde bağımsız biçimde tonal karmaşıklığı betimliyor [D, ICASSP 2015].

- **İnce ölçek** (akor ve dizi düzeyi) ile **kaba ölçek** (modülasyon düzeyi)
  ayrı karmaşıklıklar veriyor. Hesap farklı zaman çözünürlüklerinde yapılıyor
  (CENS benzeri yumuşatma) [D].
- Beethoven sonatlarında gelişme bölümlerinin karmaşıklığı daha yüksek çıktı
  (CIM 2014) [D]. Ölçüt, müzikolojik olarak beklenen yönde davranıyor.
- Formül [B, ayrıntı doğrulanmalı]: kroma beşliler çemberi sırasına dizilir
  (C, G, D, …). Her perde sınıfı `2πk/12` açısında birim vektör alınır.
  Ağırlıklı bileşke `r = |Σ c_k e^{i2πk/12}|` (c L1-normalize) hesaplanır.
  Karmaşıklık `Γ = sqrt(1 − r)`. Yanında **kroma entropisi**
  (`−Σ c log c / log 12`) ve **düzlük** (geometrik/aritmetik ortalama) gelir.
- Öncülü Streich'in (2007) tonal karmaşıklık ölçütü: kısa pencereyi uzun
  pencereyle kıyaslar [D, Weiß ve Müller 2011 aktarımı].

### 4.3 Tonalite, mod, tonalite netliği
- Krumhansl–Schmuckler korelasyonu: 24 döndürülmüş profil, en yüksek korelasyon
  tonaliteyi verir. Birinci ile ikinci korelasyonun farkı **belirsizlik**,
  en yüksek korelasyon **netlik** ölçüsü olur.
- Essentia `Key` algoritmasının profilleri [D, kaynak kod]:
  - `krumhansl`: pop için genelde iyi;
  - `temperley`: klasik, özellikle minör;
  - `shaath`: pop ve elektronik;
  - `edma`: EDM'den otomatik çıkarılmış, genelde shaath'tan iyi;
  - `bgate` ve `braw`: BeatPort;
  - `diatonic`: tonal-işlevsel olmayan müzik için.

  Atıflar: Gómez 2006; Temperley 1999; Faraldo vd. 2016 ve 2017 [D].
- Uyarı: metal riffleri sıklıkla **güç akoru** (kök + beşli, üçlüsüz) ve
  frig/lokriyen gibi modal dizilerle çalınır. Majör/minör ikiliği bu müzikte
  anlamsızlaşır. Modu raporlamak yerine **netlik** ve **diatoniklik**
  daha güvenilir sinyal.

### 4.4 Akor sözlüğü karmaşıklığı ve armonik "sürpriz"
- Akor tanıma araçları:
  - Chordino / NNLS kroma (Mauch ve Dixon 2010 [B]);
  - BTC (Park vd. 2019, ISMIR [B]): geniş sözlük, 7'li, 9'lu ve çevrimler;
  - madmom'un derin kroma tanıyıcısı (Korzeniowski ve Widmer 2016 [B]):
    yalnız majör/minör, füzyon için **yetersiz**.
- 30 sn'den türetilebilecekler: vuruş başına akor değişim hızı, farklı akor
  sayısı, 7'li/genişletilmiş akor payı, kök hareketi dağılımı (beşli /
  kromatik / üçlü). Casiopea tipi füzyonu metalden bu ayırır: yüksek değişim
  hızı, maj7/9/11/13 ve ii–V hareketleri.
- **Akor dizisi karmaşıklığı:** Di Giorgi vd. (2017, IEEE/ACM TASLP) veriye
  dayalı bir model önerdi [B]. Cheung vd. (2019, Current Biology), akor
  dizilerinde beklenmedikliğin hazzı belirsizlikle **etkileşerek**
  yordadığını gösterdi (eyer biçimli yüzey) [B]. Gold vd. (2019, J. Neurosci.)
  benzer bir ters-U buldu [B]. Uygulama fikri: kütüphanenin **tam FLAC'larından**
  çıkarılan akor dizileriyle bir bigram/trigram modeli kur. Adayın akor
  dizisinin bu modele göre ortalama şaşırtıcılığı (surprisal), "senin
  armonik alışkanlığına göre ne kadar yeni" sorusunu cevaplar. Sonraki faz işi.

### 4.5 Gerilim (Lerdahl; Herremans ve Chew)
- Lerdahl'ın *Tonal Pitch Space* kuramı (2001) ve Lerdahl ve Krumhansl (2007)
  tonal gerilim modeli [B] sembolik girdi ister, sesten doğrudan çalışmaz.
- Herremans ve Chew (TENOR 2016) spiral dizi üzerinde üç ölçüt tanımladı [D]:
  - bulut çapı: notaların tonal uzayda saçılımı;
  - bulut momentumu: perde kümelerinin spiral dizide hareketi;
  - gerilme gerinimi: yerel bağlamın globalden uzaklığı.

  `partitura` kütüphanesi bulut çapını ve gerilme gerinimini uyguluyor [D].
  Ses için önce nota transkripsiyonu gerekir (Basic Pitch, §12-7). Not olayları
  gürültülü olduğundan bu ölçütler 30 sn'de **düşük öncelikli**.

### 4.6 Türk rock'a özgü: mikrotonal içerik
Anadolu rock'ta ve makam etkili repertuvarda bağlama ve koma aralıkları
12-TET kromaya sığmaz, kroma "bulanıklaşır". Öneri: üç bin/yarım ton
çözünürlükte, yani 36 binlik kroma (`chroma_cqt(bins_per_octave=36)`).
Akort tahmininden sonra 12-TET merkezleri dışında kalan enerji payı bir
**mikroton payı** ölçüsü verir. Perde-frekans histogramı yaklaşımı Türk
makam müziği bilgi erişiminde yerleşik (Bozkurt 2008, JNMR; Gedik ve Bozkurt
2010, Signal Processing [B]). Bu bir **hipotez**: distorsiyonlu gitar ve
perde bükme (bend) de benzer enerji üretir. Önce bilinen çapalarla ölçülmeli
(ör. kütüphanedeki bağlamalı ve bağlamasız Türk rock albümleri).

---

## 5. Ritim ve ölçü öznitelikleri

### 5.1 Önceki iki ölçüt neden başarısız oldu (kuramsal açıklama)
- **Tempogram entropisi** periyodiklik belirsizliğini ölçer. Eminem de
  Meshuggah da ızgaraya kilitli ve tek, güçlü bir periyot taşıyor. Fark
  periyotta değil, **ölçüye göre örüntü** ve **döngü uzunluğunda**.
- **HPSS + senkop fazı**, ölçü başı (downbeat) bilinmeden ve kaynaklar ayrılmadan
  hesaplandı. Mevcut `izgara_entropi` de ilk vuruşu ölçü başı ve ölçüyü 4/4
  varsayıyor: `faz = (onset − vurus[0]) mod 4·ara` [kod]. Tek ölçüde
  (7/8, 5/4) ve ölçü değişiminde bu faz histogramı anlamını yitirir.

Doğru yapı üç adımlı: (1) gerçek vuruş ve ölçü başı, (2) stem bazlı onset,
(3) ölçüye hizalı metrik profil. Buradan senkop, döngü ve polimetre ölçüleri çıkar.

### 5.2 Vuruş, ölçü başı ve ölçü kestirimi
- **madmom** (Böck, Krebs, Widmer 2016, ISMIR) [D]: RNN ile DBN ortak vuruş ve
  ölçü başı takibi. `beats_per_bar` bir liste alabiliyor, ör. [3, 4, 5, 7] [D].
  Bilinen sorunlar [D, GitHub tartışmaları]: listeye 6 eklenince 4/4 rock
  parçaları zaman zaman 6 vuruş/ölçü etiketleniyor; tempo sınırları her zaman
  tutmuyor.
- **Holzapfel, Krebs, Srinivasamurthy (2014, ISMIR), "Tracking the 'odd'":**
  Bayesçi model 9/8 ve 7/8 gibi tek ölçülerde vuruş ve ölçü başını belirgin
  biçimde daha iyi izliyor [D]. Krebs vd. (2013) ritmik örüntü modeli [B].
- **Beat This!** (Foscarin, Schlüter, Widmer 2024, ISMIR) [D]: DBN son-işlemesi
  yok, bu yüzden ölçü ve tempo varsayımı dayatmıyor. Eğitim verisinde ölçü
  değişimli parçalar, solo enstrüman ve klasik müzik var. F1'de önceki en
  iyiyi aşıyor. Ama süreklilik metriklerinde daha kötü ve **zor, az temsil
  edilen türlerde hâlâ başarısız olabiliyor** [D]. Kod ve ağırlıklar
  **MIT** lisanslı. CPU'da çalışıyor (`--gpu=-1`). Vuruş ve ölçü başı veriyor.
  İsteğe bağlı `dbn=True` madmom ister [D, GitHub README]. Apple Silicon için
  üçüncü taraf bir MLX portu var [D].
- Derin öğrenmeyle ölçü sınıflandırma: Meter2800 veri setinde ResNet18 en iyi
  çıktı (EURASIP 2024) [D]. Hint müziğinde CNN ve DBN birleşimi (Holzapfel ve
  Grill 2016) [D].

**Bu projeye:** `librosa.beat.beat_track` sabit tempo varsayan dinamik
programlama yapıyor ve ölçü başı vermiyor. Yerine **Beat This!** (mix
üzerinde, MIT, CPU) kullanılmalı. 30 sn'de 120 BPM 4/4 için ~15 ölçü düşer.
Ölçü dağılımı çıkarılabilir ama gürültülü olur. İlk 2–3 sn'deki vuruşlar
atılmalı, çünkü takipçinin kilitlenmesi zaman alıyor.

### 5.3 Ölçüye hizalı öznitelikler (önerilen yeni ölçüt ailesi)
Girdi: ölçü başları, ölçü içi vuruşlar ve Demucs `drums` stem'inden tekme,
trampet ve zil onsetleri. Bant ayrımı zaten `icra_profili`'nde var. Her vuruş
4'e (onaltılık) ve ayrıca 3'e (triole/swing) bölünür, her ölçü ikili bir örüntüye dönüşür.

1. **Ölçü uzunluğu dağılımı:** ölçü başına vuruş sayısının histogramı (3, 4,
   5, 6, 7, …). Ölçü düzensizliği = modal uzunluktan sapan ölçü payı.
   Tek ölçü göstergesi = 5 ve 7'lik ölçülerin payı.
2. **Senkop:**
   - **Longuet-Higgins ve Lee (1984):** metrik ağırlıklar hiyerarşiktir. Daha
     yavaş düzeyin ağırlığı daha yüksektir. Bir sus ya da bağlı nota, kendisinden
     önceki onsetten yüksek ağırlıklı konuma düşerse senkop sayılır [D, ikincil
     tanım]. Smith ve Honing (2006) modeli dinleyici karmaşıklık yargılarıyla
     sınadı [D]. 4/4 için 16 adımlık ağırlıklar:
     0,−4,−3,−4,−2,−4,−3,−4,−1,−4,−3,−4,−2,−4,−3,−4.
   - **WNBD** (Gómez, Melvin, Rappaport, Toussaint 2005, Bridges) [D]:
     ağırlıklı nota–vuruş uzaklığı; önceki ölçütlerin bazı kusurlarını gideriyor.
   - Tekme ve trampet için **ayrı ayrı** hesaplanmalı. Hip-hop'ta tekme
     senkoplu ama trampet 2 ve 4'te sabit. Meshuggah'da tekme gitarla
     uyumlu (unison) ve ölçüyle çapraz.
3. **Döngü tekrar skoru** (hip-hop ayırıcısı): vuruş eşzamanlı mel ya da onset
   özniteliklerinin 1, 2 ve 4 ölçü gecikmedeki korelasyonunun en büyüğü.
   Programlanmış ya da örneklenmiş döngüde ~1, canlı davulda belirgin biçimde
   düşük olması beklenir. Bu bir **hipotez**, ama mevcut ölçümle uyumlu: Eminem
   ızgara entropisi 0.755, "makine ızgaraya kilitli". Ölçü-ölçü Hamming
   uzaklığı da **varyasyon/fill oranı** verir; canlı davulcunun imzasıdır.
4. **Riff periyodu / polimetre endeksi** (Meshuggah ayırıcısı, hipotez):
   tekme onsetlerinin (ya da bas nota onsetlerinin) onaltılık ızgaradaki öz
   korelasyonundan baskın periyot P bulunur. P, ölçü uzunluğunun (16 ya da 12)
   katı ya da böleni değilse, örneğin 23/16'lık riff 4/4 zil ızgarası üstünde
   dönüyorsa, polimetre vardır. Endeks: ölçü katı olmayan gecikmelerdeki öz
   korelasyon tepesi ile ölçü katı gecikmelerdeki tepenin oranı. Ölçü başı
   takipçisi zili izleyip "4/4" diyecek. Bu yüzden tek ölçü dağılımı Meshuggah'ı
   yakalamaz, riff periyodu yakalar.
5. **Metrik profil vektörü:** 16 ya da 12 binlik onset histogramı, enstrüman
   başına, ölçü başına hizalı. Bu, mevcut `izgara_entropi`'nin doğru hizalanmış
   hâli. Entropisi ve tepe konumları ayrı öznitelikler olur.

### 5.4 Tempodan bağımsız ritim betimleyicileri (orta öncelik)
- **Fluctuation Patterns** (Pampalk; Pampalk, Rauber, Merkl 2002) [D]: bant
  başına ses yüksekliği modülasyonu. ~3 sn'lik segmentlerde 0–10 Hz modülasyon
  spektrumu alınır, algısal dalgalanma gücüyle ağırlıklandırılır ve
  yumuşatılır [D].
- **Pohle vd. (2009, ISMIR):** fluctuation pattern'i revize ettiler, Ballroom
  verisinde ritim benzerliğinde sınadılar. Tını bileşeni eklemek sonucu
  iyileştirdi. Tek bir parametre setiyle hem ritim hem genel benzerlik
  yakalanıyor [D].
- Tempo değişmezliği için ölçek dönüşümü (Holzapfel ve Stylianou 2011, TASLP)
  ya da log-periyot ekseninde kayma-değişmez karşılaştırma kullanılır [B].
- Değer: CLAP bunun bir kısmını zaten taşıyor. Ama "ritim görünümü" ayrı bir
  eksen istendiğinde yorumlanabilir ve ucuz (numpy FFT).

### 5.5 Groove ve haz: senkopun ters-U'su
Witek vd. (2014, PLoS ONE): funk davul kesitlerinde senkop ile hareket etme
isteği ve haz arasında **ters-U** ilişkisi var. Orta düzey senkop en yüksek hazzı
veriyor. Entropi zayıf bir yordayıcı [D]. Sioros vd. (2014, Frontiers): orta
senkop sentetik örneklerde groove'u artırıyor [D]. Bu, "senkop ne kadar fazlaysa
o kadar iyi" sıralamasının yanlış olacağı anlamına gelir (§11.4).

---

## 6. Dinamik: EBU R128, LRA, PLR, tepe faktörü ve normalize önizleme

- **ITU-R BS.1770 ve EBU R128** [B, standart metinleri bu oturumda açılamadı]:
  - entegre ses yüksekliği (LUFS);
  - kısa süreli (3 sn) ve anlık (400 ms) ses yüksekliği;
  - gerçek tepe;
  - **LRA** (EBU Tech 3342): kapılı kısa süreli ses yüksekliği dağılımının
    10. ile 95. yüzdelikleri arasındaki fark. Bilinen tanım: −70 LUFS mutlak
    kapı ve −20 LU göreli kapı; doğrulanmalı.
- **pyloudnorm** (Steinmetz ve Reiss 2021, AES 150) [D]: BS.1770-4 uyguluyor,
  `loudness_range()` ile EBU Tech 3342'yi izlemeye çalışıyor. **MIT** lisanslı.
- **Normalize önizleme sorunu:**
  - Entegre LUFS bilgisizdir; bütün önizlemeler aynı hedefe çekilmiş.
  - Normalizasyon **yalnız kazanç** ise klip içi ölçüler korunur: LRA, tepe
    faktörü ve PLR (gerçek tepe − entegre ses yüksekliği).
  - Yükseltme bir **sınırlayıcıyla** yapıldıysa PLR ve tepe faktörü bozulur.
  - Bunu tahmin etmek yerine **ölçmek** gerekir (§13.4 kalibrasyon deneyi).
- **Makro ile mikro dinamik ayrımı:** Deruty ve Tardieu (2014, JAES) ana akım
  müzikte dinamik işlemenin zaman içindeki seyrini inceledi [B]. "Ses
  yüksekliği savaşı" makro dinamiği (LRA) ve mikro dinamiği (tepe/RMS, PLR)
  farklı etkiliyor. Yani ikisi ayrı ölçüt olmalı. Mevcut `dinamik_aralik`
  (RMS'in 95./5. yüzdeliği) LRA'ya yakın bir makro ölçü.
- **Stem başına tepe faktörü:** davul stem'inin geçici (transient) korunması,
  mastering sıkıştırmasının bir vekilidir. Mevcut kodun yorumu önemli: karışık
  pasajda tepe/RMS "aranjman yoğunluğunu" ölçüyordu. O yüzden yalnız `drums`
  stem'inde ve onset anlarında ölçülmeli.
- **Değer:** orta-düşük. Dinamik daha çok **prodüksiyon dönemi ve türü**
  kodluyor (füzyon yüksek PLR, modern metal düşük). Bu bir zevk ekseni olabilir,
  ama karıştırıcı da olabilir. K13 gereği çapa ile sun, norm uydurma.

---

## 7. Yapı (30 sn'de sınırlı)

Tam parça yapısı (verse/chorus) 30 sn'de görülemez. Klip içi iki ölçü yine de anlamlı:

- **Yenilik eğrisi** (Foote 2000 [B]): öz-benzerlik matrisinde damalı çekirdekle
  bölüm sınırı tepeleri. 30 sn'deki **bölüm değişimi sayısı** prog'da yüksek,
  döngü tabanlı müzikte düşük olmalı.
- **Tekrarlılık:** öz-benzerlik matrisinin köşegen dışı ortalaması. §5.3'teki
  döngü skoruyla aynı aileden.

Önizleme seçimi de bir tuzak. Hangi 30 sn'nin seçildiği servis politikasıdır;
nakarat da olabilir, ortadan bir kesit de. Kütüphane FLAC'ları üzerinde çapraz
korelasyonla ölçülebilir (§13.4).

---

## 8. Essentia yüksek düzey betimleyicileri ve geçerlilikleri

- **AcousticBrainz yüksek düzey betimleyicileri**: tür, ruh hâli, enstrüman.
  Sinyal betimleyicileri üzerinde eğitilmiş SVM'lerle çıkarılıyor [D].
- **Liem ve Mostert (2020, ISMIR), "Can't Trust the Feeling?":** laboratuvarda
  doğrulanmış betimleyiciler gerçek kullanımda **beklenmedik davranıyor**.
  Bu, **yapı geçerliliği** sorusu doğuruyor. Yöntem: betimleyiciler arası anlamsal
  fazlalık ve aynı kayıt için birden çok gönderim. Sonuç: değerler mutlak
  doğru sayılmamalı [D].
- **Sturm'ün "at" (horse) eleştirisi** (Sturm 2014 IEEE TMM [B]; "The 'Horse'
  Inside", arXiv 1606.03044 [D]): yüksek doğruluklar, müzikle ilgisiz bir
  karıştırıcıyı öğrenmekten gelebilir.
- **Yeni Essentia modelleri:**
  - Discogs-EffNet: 400 Discogs stiliyle eğitilmiş EfficientNet-B0, 1280 boyutlu
    gömü [D];
  - MAEST: Discogs ile eğitilmiş ses transformer'ı [D];
  - üzerlerinde küçük MLP başlıklar. Örnek: **approachability** ve
    **engagement** (2 sınıf, 3 sınıf, regresyon). Engagement-3c: kurum içi
    22 211 örnekte test normalize doğruluk **0.65** [D].
  - Lisans: modeller **CC BY-NC-SA 4.0** (ticari lisans ayrıca) [D]. Essentia
    kütüphanesinin kendisi AGPLv3 [B].
- **Bu projeye:**
  - Semantik etiketleri (tür, ruh hâli, approachability) **kullanıcıya gerçek
    gibi sunma**. K13 ve K14'ün ruhu bunu gerektiriyor.
  - Gömü olarak Discogs-EffNet değerli: stil düzeyinde ince ayrım yapıyor
    ve "Fusion", "Prog Rock" gibi stilleri kapsıyor.
  - "Engagement" gibi skorlar ancak zayıf bir yardımcı sinyal olabilir;
    önce kullanıcının kararlarıyla korelasyonu ölçülmeli.
  - Essentia'nın **label** tabanlı karşıtsal gömüsü (`discogs_label_embeddings`
    [D]) K9'un gerekçesiyle çelişir; kullanılmamalı. Artist ya da track tabanlı
    varyantlar tercih edilmeli. Bunların varlığı yalnız dosya adlarından
    çıkarıldı, doğrulanmalı.

---

## 9. Önceden eğitilmiş gömüler: karşılaştırma

### 9.1 Kanıt tabanı
- **MARBLE** (Yuan vd. 2023, NeurIPS D&B) [D]: dört düzeyli görev taksonomisi
  (akustik, icra, nota, yüksek düzey betimleme). Yayınlanan sürümde 12 veri
  setinde 18 görev var. Büyük ölçekli önceden eğitilmiş müzik dil modelleri
  görevlerin çoğunda en iyi.
- **MARBLE v2** (2025-06-04) [D, GitHub]: CLaMP3, DaSheng, MERT, MuQ,
  MuQ-MuLan, MusicFM, Qwen2-Audio ve Qwen2.5-Omni kodlayıcıları. Görevler:
  GTZAN tür, GiantSteps tonalite, EMO, MTG-Jamendo, MTT, akor, vuruş.
  README'de skor tablosu yok; model başına sayıları doğrulayamadım.
- **Öneri sistemi bağlamı** (benzerliğe en yakın kanıt):
  - Tamm ve Aljanaki (2024, arXiv 2409.08987) [D]: MusicFM, Music2Vec, MERT,
    EncodecMAE, Jukebox ve MusiCNN; KNN, sığ ağ ve BERT4Rec ile. **En iyi
    MIR modeli en iyi öneri modeli değil.** EncodecMAE, MERT ve MusiCNN iyi.
    MusiCNN'in tür, enstrüman ve duygu etiketleriyle denetimli eğitimi öneriye yarıyor.
  - "Adopting SOTA pretrained audio representations for MRS" (2026, arXiv
    2604.23077) [D, sonuç bölümü özeti; yazarlar doğrulanmadı]: 10 donuk
    gömü. Sıcak başlangıçta MusiCNN, EncodecMAE, MuQ-MuLan ve MuQ önde. Soğuk
    başlangıçta Jukebox, MusicFM, MuQ-MuLan, MERT ve MuQ önde. **MuQ ve
    MuQ-MuLan her görevde tutarlı.** Kaynaklar arasında küçük çelişki var;
    tablo doğrulanmalı.
  - **Soğuk başlangıç bu projenin durumu:** aday sanatçının etkileşim verisi yok.
- **Algısal benzerlik:** Vohra ve Akama (2026, arXiv 2601.19109) [D, abstract]:
  CLAP ve MuQ-MuLan ince ayarsız olarak görev-özel metrik öğrenme modelleriyle
  karşılaştırılabilir algısal uyum gösteriyor. İkincil bir özete göre ABX
  uyumu: LAION-CLAP %71.9, MuQ-MuLan %72.4 (Inst-Sim-ABX, Slakh2100) [D, ikincil;
  doğrulanmalı]. Asıl katkıları şu: **Demucs stem benzerliklerinin dinleyici
  yargılarına uydurulan doğrusal birleşimi**, enstrüman başına yorumlanabilir
  ağırlıklar veriyor. Bu, K12 ve K7 ile doğrudan örtüşüyor.
- **Ayrıştırılmış benzerlik:**
  - MERIT (Roy, Liang, Herremans 2026, arXiv 2605.27346) [D]: donuk MERT
    üzerinde üç hafif projeksiyon başlığı (melodi, ritim, tını). Eğitim
    üçlüleri koşullu üretim ve stem'lerle tek faktör değiştirilerek kuruluyor.
    Her başlık kendi boyutuna duyarlı, diğerlerinde şansa yakın. Erken aşamada
    (repo ~26 yıldız). İzleme listesine alınmalı; kullanıcının "hangi eksen?"
    tasarımına birebir uyuyor.
  - Lee vd. (2020, ICASSP) koşullu ve ayrıştırılmış çok boyutlu metrik öğrenme
    yaptı [B]. Aynı fikrin öncülü.

### 9.2 Model tablosu (CPU/M1, lisans, giriş)

| Model | Eğitim | Giriş | Lisans (kod / ağırlık) | CPU/M1 | Bu projede rolü |
|---|---|---|---|---|---|
| LAION-CLAP `music_audioset_epoch_15_esc_90.14` | karşıtsal ses–metin, müzik ağırlıklı | 48 kHz, 10 sn, füzyonsuz, HTSAT-base | repo CC0-1.0 [D] | evet | **birincil**, metinle sorgulanabilir |
| LAION-CLAP `630k` / HF `clap-htsat-unfused` (şu an kullanılan) | genel ses | 48 kHz, 10 sn | CC0 [D] | evet | mevcut; müzik checkpoint'iyle A/B yapılmalı |
| MuQ (`MuQ-large-msd-iter`) | SSL, Mel-RVQ | **24 kHz** zorunlu | kod MIT / ağırlık **CC BY-NC 4.0** [D] | ~300M param; örnekler CUDA, CPU ölçülmeli | akustik/armonik ikinci görünüm |
| MuQ-MuLan | MuQ + metin karşıtsal | 24 kHz | MIT / CC BY-NC 4.0 [D] | ~700M param, ağır | CLAP alternatifi |
| MERT-v1-95M / 330M | SSL (RVQ-VAE + CQT öğretmen) | 24 kHz [D] | kod Apache-2.0 [D] / ağırlık CC BY-NC 4.0 [B] | 95M CPU'da makul olmalı, ölçülmeli | MERIT ve CLaMP3 tabanı |
| OMAR-RQ (MTG, 2025) | çok öznitelikli maskeli token | 16 / 24 kHz | kod **AGPL-3.0** / ağırlık CC BY-NC-SA 4.0 [D] | **CPU varsayılan** [D] | multifeature varyantı perde, akor, vuruşta en iyi [D] |
| Discogs-EffNet (Essentia) | denetimli, 400 Discogs stili | 16 kHz | CC BY-NC-SA 4.0 [D] | çok hafif | stil düzeyinde ince ayrım |
| MAEST | denetimli transformer | 16 kHz | CC BY-NC-SA 4.0 [D] | orta | aynı |
| MusiCNN | denetimli etiketleme (MTT/MSD) | 16 kHz [B] | ISC [D] | çok hafif | öneri çalışmalarında iyi [D] |
| OpenL3 (music) | ses–görüntü karşılıklılığı | 48 kHz [B] | kod MIT / ağırlık CC BY 4.0 [D] | hafif | eski, düşük öncelik |
| PANNs | AudioSet denetimli | 32 kHz [B] | MIT [B] | hafif | genel ses, müzik stili için zayıf |
| Music2Latent | tutarlılık otokodlayıcısı | 44.1 kHz, ~10 Hz, 64 kanal | CC BY-NC 4.0 [D] | ? | üretim latent'i; benzerlik için değil |
| CLaMP 3 | çok kipli (nota, MIDI, ses, metin) | MERT-95M öznitelikleri [D] | MIT [D] | GPU varsayımı | düşük öncelik |
| MERIT (2026) | MERT + 3 ayrıştırılmış başlık | 24 kHz | ? | MERT kadar | **izleme listesi** |

**Lisans notu:** NC (ticari olmayan) ağırlıklar bu projede (kişisel, ≤5
kullanıcı, 0 TL) kullanılabilir. Ama `docs/karar-gunlugu.md`'ye yazılmalı ve
proje bir gün ticarileşirse çıkarılmalı. SA (ShareAlike) gömülerden türeyen
veriyi de bağlayabilir. Bir üçüncü taraf projesi bu yorumu yapıyor [D];
hukuki kesinliği yok.

**HF `larger_clap_music` hatası:** proje bu modeli transformers 5.15'te bozuk
buldu (sabit gömü). Aynı müzik checkpoint'i resmî `laion_clap` paketiyle
`amodel='HTSAT-base', enable_fusion=False` olarak yüklenebilir [D, README].
README'deki sıfır atış GTZAN sonuçları (istem: "This audio is a <genre> song."):

| Checkpoint | GTZAN |
|---|---|
| `music_audioset` | **%71** |
| `music_speech` | %69 |
| `music_speech_audioset` | %51 |

[D] Bu checkpoint'ler "geçici sürüm" olarak işaretli [D]. Bu sayılar tür
sınıflandırması, benzerlik değil; seçim K19 ile ölçülmeli. Not: `laion_clap`
da 10 sn'den uzun girdide rastgele kırpar. §1.1'deki deterministik pencereler
orada da gerekir [B, kod doğrulanmadı].

---

## 10. Gömüleri ve görünümleri birleştirme

1. **Erken füzyon (birleştirme, concatenation):** her blok önce merkezlenmeli,
   beyazlatılmalı ya da standartlaştırılmalı. Sonra blok başına eşit toplam
   varyansa ölçeklenmeli. Yoksa en büyük boyutlu blok (1280 > 512) baskın olur.
   302 albüm ve 512 boyutta kovaryans tekildir. Beyazlatma için ya aday havuzunu
   (10 000+ parça) dahil et, ya Ledoit–Wolf büzülmesi kullan (numpy ile birkaç
   satır), ya da PCA ile 64–128 bileşene indirip özdeğerlere taban (ε) koy.
   Kısmi beyazlatma (Σ^(−1/2) yerine Σ^(−1/4)) gürültü boyutlarını aşırı büyütmez.
   Cümle gömülerinde beyazlatma ve PCA aramayı iyileştiriyor (Su vd. 2021 [B]).
   Müzik için ölçülmeli.
2. **Geç füzyon (benzerlik düzeyinde):** her görünümün benzerliğini sorgu
   başına z-skora ya da yüzdeliğe çevir. Pohle ve Seyerlehner'in MIREX
   sistemleri buna "uzaklık uzayı normalizasyonu" diyordu [B]. Sonra ağırlıklı
   topla. Ağırlıklar K19 gizleme sınamasıyla, tercihen eksen başına seçilir.
   Alternatif **Reciprocal Rank Fusion**: `Σ_v w_v / (60 + sıra_v)` (Cormack
   vd. 2009 [B]). Ölçek farklarına duyarsız ve parametresi az.
3. **Füzyonu hiç yapmamak da bir seçenek:** K1 ve K3 gereği kullanıcı ekseni
   seçiyor. "Ritim görünümü", "armoni görünümü" ve "ses (CLAP) görünümü" ayrı
   aday kaynakları olarak desteye girebilir. Thompson örneklemesi (K21) payları
   gerçek kararlardan öğrenir. Bu, mevcut mimariye en uygun yol.
4. **Füzyonun hubness yararı:** farklı yönleri birleştirmek hubness'ı azaltıyor
   (Flexer vd. 2010 [D]). Bir hub'ın bütün görünümlerde hub olması daha az olası.
5. **Öğrenilmiş birleşim:** McFee ve Lanckriet (2011, JMLR) çok kipli benzerliği
   çoklu çekirdekle öğrendi [B]. Vohra ve Akama (2026) dinleyici yargılarından
   stem ağırlıklarını doğrusal programlamayla öğrendi [D]. Bu projede "dinleyici
   yargısı" kaydırma kararlarıdır (beğendim/tutmadı). Ancak n büyüyünce
   kullanılabilir.

---

## 11. Müzik tercihi psikolojisi

### 11.1 Boyutlar
- **Rentfrow ve Gosling (2003, JPSP)** [B]: dört boyut. Reflective & Complex
  (caz, klasik), Intense & Rebellious (rock, metal), Upbeat & Conventional,
  Energetic & Rhythmic (hip-hop dahil). Bu kullanıcı ilk ikisinde ve
  sonuncusunda yüksek.
- **MUSIC modeli** (Rentfrow, Goldberg, Levitin 2011, JPSP) [D]: Mellow,
  Unpretentious, Sophisticated, Intense, Contemporary. Faktörler **türden
  bağımsız** ve büyük ölçüde duygusal/duyuşsal tepkilere dayanıyor. Replikasyon
  "The Song Remains the Same" (Rentfrow vd. 2012, Music Perception): tercih
  türden çok sonik ve psikolojik özniteliklerle açıklanıyor [D]. Kültürler
  arası destek kısmi (Hırvatistan evet, Malezya kısmi) [D].
- **Greenberg vd. (2016, Social Psychological and Personality Science,
  "The Song Is You")** [D]: 26 tür ve alt türden 102 parça üzerinde 38 algılanan
  öznitelik üç boyuta indirgendi. **Uyarılmışlık** (enerji, yoğunluk),
  **değerlik** (hüzünlü–mutlu), **derinlik** (entelektüellik, sofistikelik).
  N = 9 454'te kişilik demografinin ötesinde tercihi yordadı. Deneyime açıklık
  derinlikle, heyecan arayan dışadönüklük uyarılmışlıkla ilişkili [D].
  (Not: makale PLOS ONE'da değil, SPPS'te.)
- **Gold-MSI** (Müllensiefen, Gingras, Musil, Stewart 2014, PLoS ONE)
  [D]: genel nüfusta müzikal sofistikeliği ölçen öz-bildirim aracı.
  N = 147 636. Psikometrik nitelikleri iyi. CC BY lisanslı ve açık materyal.

### 11.2 Karmaşıklık ve beğeni
- **Berlyne'in ters-U'su:** Chmiel ve Schubert (2017, Psychology of Music)
  57 çalışmayı gözden geçirdi; %87.7'si parçalı ters-U ile uyumlu [D].
- **Uzmanlık şekli değiştiriyor:** Orr ve Ohlsson (2005), profesyonel caz ve
  bluegrass müzisyenlerinde **ters-U kanıtı bulamadı** [D]. Uzmanda ilişki
  başka biçimde olabilir.
- **Tanışıklık:** tekrar dinleme karmaşıklıktan bağımsız olarak beğeniyi
  artırıyor (Madison ve Schiölde 2017, Frontiers in Neuroscience) [D].
- **Senkop ve groove:** ters-U (Witek vd. 2014) [D]. Ritmik ve armonik
  karmaşıklığın groove'da etkileşimi için Matthews vd. 2019 (PLoS ONE) [B].
- **Armonik beklenti:** belirsizlik × sürpriz (Cheung vd. 2019; Gold vd. 2019) [B].

### 11.3 Bu kullanıcı için neden önemli
Kullanıcının "enstrümantal derinlik ve icra kalitesi" önceliği, Greenberg'in
**derinlik** boyutuna ve MUSIC'in **Sophisticated** ile **Intense** faktörlerine
denk düşüyor. Ama bu boyutlar **dinleyici algısıyla** tanımlandı, akustik
karşılıkları kurulmadı. Hangi ses ölçütünün bu kullanıcının "derinlik"
algısına karşılık geldiği **kendi kararlarıyla ölçülmeli**, literatürden
varsayılmamalı (K13 ilkesi).

### 11.4 Tasarım sonuçları
1. **"Daha karmaşık = daha iyi" sıralaması yapma.** Her öznitelik için
   kullanıcının **tercih bölgesini** kendi kütüphanesinden (eksen başına) çekirdek
   yoğunluk tahminiyle (KDE) çıkar. Aday skoru öznitelik değeri değil, o
   bölgedeki yoğunluk olsun. "Bilinçli uzaklık" stratejisi bölgenin hemen
   dışını, Berlyne'in "optimal yenilik" kenarını hedefleyebilir.
2. **Öznitelik ilgililiği eksene bağlı.** Hip-hop ekseninde armonik karmaşıklık
   anlamsız. Füzyon ekseninde döngü skoru anlamsız. Eksen üyelerini
   kütüphanenin geri kalanından ayıran öznitelikler seçilmeli (Fisher skoru ya
   da L1 lojistik). Aday yalnız onlarla puanlanmalı. Bu öznitelikler K7
   şablonuna sayı da verir: "Akor değişim hızı dakikada 38. Füzyon ekseninde
   kütüphanendeki albümlerin medyanı 35."
3. **Gold-MSI isteğe bağlı sunulabilir** (≤5 kullanıcı, ücretsiz, CC BY).
   Yüksek sofistikelik, karmaşıklık eksenlerinin ağırlığını artırmak için
   değil, **tercih bölgesinin genişliğini** yorumlamak için kullanılır. Düşük öncelik.

---

## 12. UYGULAMA: eklenecek öznitelikler ve modeller (sıralı)

Sıralama ölçütü: (beklenen değer × kullanıcı eksenlerine uygunluk) / maliyet.
Her madde K19 gizleme sınamasıyla ölçülmeden üretime girmemeli.

### 12-1. CLAP boru hattını deterministik ve tek tip yap
- **Neyi yakalar:** aynı "ses görünümü", ama tekrarlanabilir ve klibin tamamıyla.
- **30 sn'den:** 3 ya da 5 deterministik 10 sn pencere. Her biri gömülür,
  ortalaması alınıp normalize edilir. Pencere vektörleri saklanır. Kütüphane
  ve aday aynı yoldan geçer (§1.1–1.2).
- **Değer:** yüksek. Doğruluk hatasını kapatıyor, K2'yi sağlıyor, veriyi üç
  katına çıkarıyor. Maliyet klip başına +2–4 sn CPU.
- **Tuzak:** pencere ortalaması, sessiz bir giriş penceresiyle sulanabilir.
  RMS'i çok düşük pencereler dışlanmalı (Ian Paice dersi).

### 12-2. Hubness: merkezle, normalize et, (karıştırıcı PC'leri at), Mutual Proximity
- **Neyi yakalar:** "evrensel komşu" etkisini kaldırır; komşuluğu simetrikleştirir.
- **Hesap:** §3.4. numpy ile on satır.
- **Değer:** yüksek. Literatürde tutarlı kazanç var [D]. Mevcut çözüm ailenin
  zayıf üyesi.
- **Tuzak:** MP mutlak skoru değiştirir, arayüzdeki sayıların anlamı değişir.
  Referans kümenin seçimi (yalnız kütüphane mi, havuz mu) sonucu etkiler;
  ikisi de ölçülmeli.

### 12-3. Sanatçı başına çoklu klip ve küme–küme benzerliği
- **Neyi yakalar:** tek klibin pasaj şansını (akustik an, sessiz giriş)
  ortalamayla giderir.
- **Hesap:** sanatçı ya da albüm başına 3–5 parça. Benzerlik: pencere ve klip
  vektörleri arası çiftlerin en iyi k'sının ortalaması (k=3), ya da ortalama
  bağlantı. Kodda "çok sesli kural" zaten başlamış; aynı ilke gömü
  düzeyine taşınır.
- **Değer:** yüksek. Maliyet doğrusal; önizleme indirme ve CLAP süresi artar.
- **Tuzak:** popüler parçalar (önizlemesi olanlar) sanatçının en erişilebilir
  yüzüdür. Seçim yanlılığı var; derin albüm parçası da istenmeli.

### 12-4. Ölçüye hizalı ritim ailesi (Beat This! + drums stem)
- **Neyi yakalar:** tek ölçü (5, 7), ölçü değişimi, tekme ve trampet senkopu
  (LHL, WNBD), döngü tekrar skoru (programlanmış beat), varyasyon/fill oranı,
  riff periyodu ve polimetre endeksi (Meshuggah). Eminem ile Meshuggah'ı
  ayıramayan iki eski ölçütün kuramsal eksiğini kapatıyor (§5.1).
- **30 sn'den:** Beat This! mix üzerinde çalışır (MIT, CPU). İlk 2–3 sn
  atılır. Mevcut `drums` stem'inin bant ayrımlı onsetleri onaltılık ya da
  triole ızgarasına nicemlenir. Ölçü başına örüntü çıkar. Öznitelikler §5.3'teki gibi.
- **Değer:** yüksek. Teknik/prog metal ve hip-hop eksenlerinin asıl ayırıcısı.
  Yorumlanabilir; K7 şablonu için doğal ("7/8 ölçü payı %40").
- **Tuzaklar:**
  - 30 sn = 10–20 ölçü, dağılımlar gürültülü. Çoklu klip (12-3) şart.
  - Ölçü başı takipçileri az temsil edilen türlerde ve tek ölçüde hata yapıyor [D].
    Önce **çapa listesiyle doğruluk ölç**: kütüphanede ölçüsü bilinen
    parçalar (Rush "Tom Sawyer" 7/8 ara bölümü, TOOL "Schism" ölçü değişimleri,
    Dream Theater vb.). Doğruluk düşükse yalnız güvenli öznitelikleri
    (senkop, döngü) tut.
  - MP3/AAC ön yankısı (pre-echo) zil onsetlerini bulanıklaştırır. FLAC ile
    önizleme arasında kalibre et (§13.4).

### 12-5. Armoni ailesi (other + bass stem kroması)
- **Neyi yakalar:** tonal karmaşıklık (ince ve kaba ölçek), diatoniklik ve
  kromatiklik (TIV), tonalite netliği, armonik değişim hızı (HCDF), Türk rock
  için mikroton payı. Füzyon ve gitar virtüözü eksenlerinin ayırıcısı.
- **30 sn'den:** `other` + `bass` stem'leri toplanır. Davul kromayı kirletir,
  vokal melodi ekler. Sonra `chroma_cqt` (22.05 kHz), vuruş eşzamanlı medyan
  (`librosa.util.sync`, 12-4'teki vuruşlarla) ve L1 normalizasyonu.
  Öznitelikler:
  - Weiß ve Müller'in beşliler çemberi saçılımı, entropi ve düzlük, iki ölçekte
    (vuruş ve klip), ayrıca ikisinin farkı;
  - TIV.lib ile ‖T5‖, ‖T1‖ ve dissonans;
  - tonnetz ile HCDF tepe sayısı/dk;
  - K–S netliği (Essentia profilleri ya da numpy);
  - 36 bin kromadan mikroton payı.
- **Değer:** orta-yüksek. Ucuz (numpy) ve yorumlanabilir.
- **Tuzaklar:**
  - Distorsiyonlu gitarın intermodülasyon ürünleri kromayı düzleştirir;
    prog metalde "karmaşıklık" yapay olarak yükselir. Distorsiyon ölçüsüne
    karşı kısmi korelasyonla denetle. Bu, `olcut_denetimi` adımsal elemesinin
    tam işi.
  - Güç akorlarında mod belirsizdir.
  - Demucs `other` gitarı ve klavyeyi birlikte taşır (K12 sınırı).

### 12-6. Akor sözlüğü (geniş sözlüklü tanıyıcı)
- **Neyi yakalar:** akor değişim hızı, farklı akor sayısı, 7'li/genişletilmiş
  pay, kök hareketi. Füzyon (Casiopea) ile metalin en net ayrımı.
- **30 sn'den:** BTC (geniş sözlük) ya da Chordino. Lisans ve kurulum
  doğrulanmalı. madmom yalnız majör/minör tanıdığı için yetersiz.
- **Değer:** orta. 30 sn'de 10–20 akor düşer; çoklu klip gerekir.
- **Tuzak:** distorsiyonda tanıma güvenilmez; metal klipleri için "N" (akor
  yok) payı yüksek çıkar. Bu payın kendisi de bilgi taşır.

### 12-7. Nota transkripsiyonu ile icra ölçütleri (Basic Pitch → other / bass / vocals)
- **Neyi yakalar:** saniye başına nota, ardışık aralık entropisi, kromatik aralık
  payı, perde aralığı, **hızlı koşu endeksi** (IOI < 100 ms ve en az 6 notalık
  aynı yönlü dizi: sweep ya da shred), legato. "Gitar virtüözü" ekseni için
  bugünkü stem ölçütlerinin (parlaklık, sustain) yakalayamadığı doğrudan icra
  sinyali.
- **30 sn'den:** Basic Pitch (Bittner vd. 2022, ICASSP; Apache-2.0 [B])
  stem üzerinde. Hafif ve CPU'da hızlı [B].
- **Değer:** orta-yüksek, ama doğruluğu belirsiz. Distorsiyonlu gitarda
  transkripsiyon hatası beklenir.
- **Tuzak:** çok sesli `other` stem'inde (gitar + klavye) nota olayları
  karışır. Önce bilinen çapalarla doğrula (Plini, Animals As Leaders, Takanaka).

### 12-8. İkinci bir öğrenilmiş gömü (akustik/armonik görünüm)
- **Aday sırası:**
  1. MuQ. Öneri soğuk başlangıcında tutarlı [D], 24 kHz, NC.
  2. MERT-v1-95M. Daha hafif, MERIT'in tabanı.
  3. Discogs-EffNet. Stil düzeyinde, çok hafif, NC-SA.
  4. OMAR-RQ multifeature. Perde, akor ve vuruşta güçlü, AGPL kod.
- **30 sn'den:** MERT/MuQ için ara katman (ör. 95M'de 6–8) zaman ortalaması
  ve standart sapması; katman seçimi K19 ile yapılır. Discogs-EffNet için
  pencere ortalaması.
- **Değer:** orta. CLAP'in "anlamsal" uzayına karşı daha akustik bir görünüm
  verir ve füzyonda hubness'ı azaltır [D].
- **Tuzak:** CPU süresi ölçülmeli (MuQ ~300M param). Lisans NC ve karar
  günlüğüne yazılmalı. 24 kHz'e yeniden örnekleme şart; yanlış örnekleme
  hızının "her şey hip hop" hatası projede zaten bir kez yaşandı.

### 12-9. Müzik CLAP checkpoint'i (A/B)
- **Ne:** `laion_clap` ile `music_audioset_epoch_15_esc_90.14.pt`; sıfır atış
  GTZAN %71 [D]. Mevcut model genel ses checkpoint'i.
- **Değer:** orta; ölçülmeli. Etiket sözlüğü (`etiket_clap`) için de muhtemel kazanç.
- **Tuzak:** "geçici sürüm" uyarısı [D]. Sabit gömü hatası için mevcut duman
  testi korunmalı (beyaz gürültü ile sinüs arası kosinüs).

### 12-10. Dinamik ailesi (LRA, PLR, drums stem tepe faktörü)
- **30 sn'den:** pyloudnorm (`integrated_loudness`, `loudness_range`), gerçek
  tepe için 4× aşırı örnekleme. Kenar sönmelerine (fade) karşı ilk ve son 1 sn
  atılır. Tepe faktörü drums stem'inde, onset anlarında.
- **Değer:** orta-düşük. Daha çok prodüksiyon dönemini kodlar.
- **Tuzak:** normalizasyon sınırlayıcı içeriyorsa PLR bozulur. Önce §13.4
  ölçülmeli. Kaynak içinde standartlaştırma (K11) sürer.

### 12-11. Tempodan bağımsız modülasyon spektrumu (FP/OP)
- **Değer:** düşük-orta, CLAP'le örtüşür. Ucuz ve yorumlanabilir bir "ritim
  dokusu" görünümü olarak eklenebilir.

### 12-12. Yapmayın ya da şimdilik ertelenin
- Essentia/AcousticBrainz semantik etiketlerini gerçek gibi sunmak
  (Liem ve Mostert 2020 [D]).
- `discogs_label_embeddings` (K9).
- Music2Latent ile benzerlik (üretim latent'i).
- Lerdahl gerilimi (sembolik girdi ister).

---

## 13. Ses benzerliğini sağlamlaştırma reçetesi

### 13.1 Kaynak ve kodek eşitliği
Urbano vd. (2014, ISMIR): MFCC ve kroma kodek, bit hızı ve örnekleme hızına
duyarlı. **Eğitim ve test aynı kodlamada olunca** sonuç en iyi, bit hızıyla
doğruluk arasında net korelasyon yok [D, poster özeti]. Uygulama:

- **Öncelikli yol:** kütüphane tarafını da önizlemeden ölçmek. Proje bunu zaten
  yapıyor (stem profili önizleme URL'sinden).
- FLAC kullanılacaksa önce aynı kodeğe ve bit hızına dönüştür (ffmpeg ile).
  Bit hızını tahmin etme, `ffprobe` ile ölç.
- Spektral öznitelikleri 11 kHz altıyla sınırla (22.05 kHz analiz zaten öyle).
  CLAP yolunda iki tarafı eşitle (§1.2).

### 13.2 Hubness azaltma
§3.4. Ayrıca füzyon (§10) hubness'ı kendiliğinden azaltır.

### 13.3 Çoklu klip ve çoklu pencere
- Sanatçı = klip ve pencere vektörlerinden bir küme.
- Benzerlik = en iyi k çift ortalaması ya da ortalama bağlantı.
- Belirsizlik: klipler üzerinde bootstrap ile güven aralığı. Aralığı genişse
  karta "zayıf kanıt" yazılır; K22'nin "kanıtın gücünü söyle" ilkesi.

### 13.4 Kalibrasyon deneyi: FLAC ile önizlemenin aynı 30 saniyesi (önerilen ilk ölçüm)
Kullanıcının 302 albümü için hem FLAC hem önizleme var. Bu, literatürde
bulunması zor bir **eşli örneklem**. Adımlar:

1. Önizlemenin FLAC içindeki yerini, onset zarflarının çapraz korelasyonuyla
   bul. Bu, servisin hangi 30 sn'yi seçtiğini de ortaya koyar.
2. Aynı 30 sn'de her ölçütü iki kaynaktan hesapla.
3. Ölçüt başına Spearman ρ, ICC ve Bland–Altman yanlılığı.
4. **Kaynaklar arası kıyasta yalnız ICC ≥ ~0.7 olan ölçütleri kullan.**
   Diğerleri yalnız kaynak içinde standartlaştırılır (K11'in genellemesi).
5. Aynı deney entegre LUFS dağılımıyla normalizasyon hedefini ve PLR
   kaybıyla sınırlayıcı kullanımını gösterir.

### 13.5 Karıştırıcı denetimi
İlk temel bileşenleri ve her yeni ölçütü şu değişkenlere karşı denetle:
`kaynak`, `yol`, çıkış yılı, LUFS, parlaklık. Proje bunu `olcut_denetimi`'nin
artık varyans eleme mantığıyla zaten yapıyor; aynı denetim gömü PC'lerine
de uygulanmalı.

---

## 14. Ölçüm planı (K19 ile)

| Değişiklik | Kıyas | Rapor |
|---|---|---|
| 12-1 deterministik pencere | mevcut rastgele kırpma | tekrar kosinüsü; recall (iki payda); tavan |
| 1.2 tek boru hattı | stem toplamı ve ham karışık | yol PC korelasyonu; recall |
| 12-2 MP / LS | mevcut merkezleme | S_k, hub ve yetim oranı; recall |
| 12-3 çoklu klip | tek klip | recall; skorun bootstrap güven aralığı |
| 12-4 ve 12-5 yeni ölçütler | CLAP tek başına | eksen başına recall; çapa doğruluğu (ölçü) |
| 12-8 ve 12-9 ikinci gömü / müzik CLAP | mevcut CLAP | recall; S_k; CPU süresi |

---

## 15. Kaynakça

**İşaretler:** [D] bu oturumda doğrulandı · [B] bu oturumda doğrulanamadı.

### Tını benzerliği ve tarih
- Aucouturier, J.-J., Pachet, F. (2002). *Music similarity measures: What's the use?* ISMIR. https://archives.ismir.net/ismir2002/paper/000020.pdf [D listede]
- Aucouturier, J.-J., Pachet, F. (2004). *Improving timbre similarity: How high is the sky?* Journal of Negative Results in Speech and Audio Sciences 1(1). https://www.francoispachet.fr/wp-content/uploads/2021/01/aucouturier-04b.pdf [D]
- Aucouturier, J.-J., Pachet, F. (2008). *A scale-free distribution of false positives for a large class of audio similarity measures.* Pattern Recognition 41(1). https://doi.org/10.1016/j.patcog.2007.04.012 [B]
- Karydis, I. vd. (2010). *Looking through the "glass ceiling": A conceptual framework for the problems of spectral similarity.* ISMIR. https://cir.di.ionio.gr/karydis/my_papers/ [D]
- Logan, B., Salomon, A. (2001). *A music similarity function based on signal analysis.* IEEE ICME. [B]
- Mandel, M., Ellis, D. (2005). *Song-level features and support vector machines for music classification.* ISMIR. [B]
- Pampalk, E., Rauber, A., Merkl, D. (2002). *Content-based organization and visualization of music archives.* ACM Multimedia. https://ofai.at/papers/oefai-tr-2002-30.pdf [D]
- Pampalk, E. (2006). *Computational Models of Music Similarity and their Application in MIR.* Doktora tezi, TU Wien. https://www.ofai.at/~elias.pampalk/publications.html [D listede]
- Pohle, T., Schnitzer, D., Schedl, M., Knees, P., Widmer, G. (2009). *On rhythm and general music similarity.* ISMIR. https://research.jku.at/en/activities/on-rhythm-and-general-music-similarity/ [D]
- Seyerlehner, K., Widmer, G., Pohle, T. (2010). *Fusing block-level features for music similarity estimation.* DAFx. [B]
- Flexer, A. (2014). *On inter-rater agreement in audio music similarity.* ISMIR. [B]
- Lee, J., Bryan, N. J., Salamon, J., Jin, Z., Nam, J. (2020). *Disentangled multidimensional metric learning for music similarity.* ICASSP. [B]

### Hubness
- Radovanović, M., Nanopoulos, A., Ivanović, M. (2010). *Hubs in space: Popular nearest neighbors in high-dimensional data.* JMLR 11. [B]
- Schnitzer, D., Flexer, A., Schedl, M., Widmer, G. (2011). *Using mutual proximity to improve content-based audio similarity.* ISMIR. https://archives.ismir.net/ismir2011/paper/000051.pdf [D]
- Schnitzer, D., Flexer, A., Schedl, M., Widmer, G. (2012). *Local and global scaling reduce hubs in space.* JMLR 13:2871–2902. https://jmlr.org/papers/v13/schnitzer12a.html [D]
- Flexer, A., Schnitzer, D., Gasser, M., Pohle, T. (2010). *Combining features reduces hubness in audio similarity.* ISMIR, 171–176. https://research.jku.at/en/publications/combining-features-reduces-hubness-in-audio-similarity/ [D]
- Flexer, A., Schnitzer, D., Schlüter, J. (2012). *A MIREX meta-analysis of hubness in audio music similarity.* ISMIR (en iyi makale). https://ir.webis.de/anthology/2012.ismir_conference-2012.30 [D]
- Feldbauer, R., Flexer, A. (2019). *A comprehensive empirical comparison of hubness reduction in high-dimensional spaces.* Knowledge and Information Systems. https://doi.org/10.1007/s10115-018-1205-y [D]; teknik rapor: https://ofai.at/papers/oefai-tr-2016-05.pdf [D]
- Feldbauer, R., Rattei, T., Flexer, A. (2020). *scikit-hubness.* JOSS. https://github.com/VarIr/scikit-hubness (BSD-3) [D]
- Suzuki, I., Hara, K., Shimbo, M., Saerens, M., Fukumizu, K. (2013). *Centering similarity measures to reduce hubs.* EMNLP. [B]
- Zelnik-Manor, L., Perona, P. (2004). *Self-tuning spectral clustering.* NeurIPS. [B]
- Conneau, A. vd. (2018). *Word translation without parallel data* (CSLS). ICLR. [B]
- Mu, J., Viswanath, P. (2018). *All-but-the-top: Simple and effective postprocessing for word representations.* ICLR. [B]
- Su, J. vd. (2021). *Whitening sentence representations for better semantics and faster retrieval.* arXiv:2103.15316. [B]
- (2023) *Hubness reduction improves Sentence-BERT semantic spaces.* arXiv:2311.18364. [D başlık]
- (2023) *Balance Act: Mitigating hubness in cross-modal retrieval with query and gallery banks.* arXiv:2310.11612. [D başlık]

### Armoni
- Harte, C., Sandler, M., Gasser, M. (2006). *Detecting harmonic change in musical audio.* ACM AMCMM. [B]
- Müller, M., Ewert, S. (2011). *Chroma Toolbox.* ISMIR. [B]
- Weiß, C., Müller, M. (2014). *Quantifying and visualizing tonal complexity.* CIM. https://www.audiolabs-erlangen.com/content/05_fau/professor/00_mueller/03_publications/2014_WeissMueller_TonalComplexity_CIM.pdf [D]
- Weiß, C., Müller, M. (2015). *Tonal complexity features for style classification of classical music.* ICASSP. https://www.audiolabs-erlangen.com/content/05_fau/professor/00_mueller/03_publications/2015_WeissMueller_TonalComplexity_ICASSP.pdf [D]
- Streich, S. (2007). *Music Complexity: A Multi-faceted Description of Audio Content.* Doktora tezi, UPF. [B]
- Bernardes, G. vd. (2016). *A multi-level tonal interval space for modelling pitch relatedness and musical consonance.* JNMR 45(4). https://repositorio.inesctec.pt/handle/123456789/3897 [D]
- Ramires, A., Bernardes, G., Davies, M. E. P., Serra, X. (2020). *TIV.lib: An open-source library for the tonal description of musical audio.* DAFx. https://arxiv.org/abs/2008.11529 [D]
- Almeida, F., Bernardes, G., Weiß, C. (2022). *Mid-level harmonic audio features for musical style classification.* ISMIR. https://archives.ismir.net/ismir2022/paper/000024.pdf [D]
- Herremans, D., Chew, E. (2016). *Tension ribbons: Quantifying and visualising tonal tension.* TENOR. https://www.dorienherremans.com/sites/default/files/paper_tenor_dh_preprint_small.pdf [D]
- Lerdahl, F. (2001). *Tonal Pitch Space.* Oxford UP; Lerdahl, F., Krumhansl, C. (2007). *Modeling tonal tension.* Music Perception 24(4). [B]
- Gómez, E. (2006). *Tonal description of polyphonic audio for music content processing.* INFORMS J. Computing 18(3). [D, Essentia kaynak kodunda atıf]
- Temperley, D. (1999). *What's key for key?* Music Perception 17(1). [D, aynı]
- Faraldo, Á., Gómez, E., Jordà, S., Herrera, P. (2016). *Key estimation in electronic dance music.* ECIR. [D, aynı]
- Essentia `Key` kaynak kodu (profil listesi). https://github.com/MTG/essentia/blob/master/src/algorithms/tonal/key.cpp [D]
- Mauch, M., Dixon, S. (2010). *Approximate note transcription for the improved identification of difficult chords.* ISMIR. [B]
- Park, J. vd. (2019). *A bi-directional transformer for musical chord recognition.* ISMIR. [B]
- Korzeniowski, F., Widmer, G. (2016). *Feature learning for chord recognition: The deep chroma extractor.* ISMIR. [B]
- Di Giorgi, B., Dixon, S., Zanoni, M., Sarti, A. (2017). *A data-driven model of tonal chord sequence complexity.* IEEE/ACM TASLP 25(11). [B]
- Cheung, V. K. M. vd. (2019). *Uncertainty and surprise jointly predict musical pleasure...* Current Biology 29(23). [B]
- Gold, B. P. vd. (2019). *Predictability and uncertainty in the pleasure of music.* J. Neuroscience 39(47). [B]
- Bozkurt, B. (2008). *An automatic pitch analysis method for Turkish maqam music.* JNMR 37(1). [B]
- Gedik, A. C., Bozkurt, B. (2010). *Pitch-frequency histogram-based music information retrieval for Turkish music.* Signal Processing 90(4). [B]
- Bittner, R. vd. (2022). *A lightweight instrument-agnostic model for polyphonic note transcription and multipitch estimation* (Basic Pitch). ICASSP. [B]

### Ritim ve ölçü
- Longuet-Higgins, H. C., Lee, C. S. (1984). *The rhythmic interpretation of monophonic music.* Music Perception 1(4). [D, ikincil tanım]
- Gómez, F., Melvin, A., Rappaport, D., Toussaint, G. (2005). *Mathematical measures of syncopation.* Bridges. https://archive.bridgesmathart.org/2005/bridges2005-73.html [D]
- Smith, L. M., Honing, H. (2006). *Evaluating and extending computational models of rhythmic syncopation in music.* ICMC. https://www.mcg.uva.nl/mcg-2023/papers/smith-honing-2006.pdf [D]
- Witek, M. A. G. vd. (2014). *Syncopation, body-movement and pleasure in groove music.* PLoS ONE 9(4): e94446. https://doi.org/10.1371/journal.pone.0094446 [D]
- Sioros, G., Miron, M., Davies, M., Gouyon, F., Madison, G. (2014). *Syncopation creates the sensation of groove in synthesized music examples.* Frontiers in Psychology 5:1036. https://doi.org/10.3389/fpsyg.2014.01036 [D]
- Holzapfel, A., Krebs, F., Srinivasamurthy, A. (2014). *Tracking the "odd": Meter inference in a culturally diverse music corpus.* ISMIR. https://archives.ismir.net/ismir2014/paper/000265.pdf [D]
- Holzapfel, A., Grill, T. (2016). *Bayesian meter tracking on learned signal representations.* ISMIR. https://archives.ismir.net/ismir2016/paper/000132.pdf [D, konu]
- Böck, S., Krebs, F., Widmer, G. (2016). *Joint beat and downbeat tracking with recurrent neural networks.* ISMIR; madmom belgeleri: https://madmom.readthedocs.io/en/v0.16/modules/features/downbeats.html [D]
- Foscarin, F., Schlüter, J., Widmer, G. (2024). *Beat this! Accurate beat tracking without DBN postprocessing.* ISMIR. https://arxiv.org/abs/2407.21658 ; kod (MIT): https://github.com/CPJKU/beat_this [D]
- (2024) Zaman işareti tespiti, Meter2800, ResNet18. EURASIP J. Audio, Speech, and Music Processing. https://doi.org/10.1186/s13636-024-00346-6 [D]
- Holzapfel, A., Stylianou, Y. (2011). *Scale transform in rhythmic similarity of music.* IEEE TASLP 19(1). [B]
- Grosche, P., Müller, M. (2011). *Extracting predominant local pulse information from music recordings.* IEEE TASLP 19(6). [B]
- Foote, J. (2000). *Automatic audio segmentation using a measure of audio novelty.* IEEE ICME. [B]

### Dinamik ve kodek
- ITU-R BS.1770-4/5; EBU R 128; EBU Tech 3341, 3342 (LRA). https://tech.ebu.ch/publications/r128 [B]
- Steinmetz, C. J., Reiss, J. D. (2021). *pyloudnorm: A simple yet flexible loudness meter in Python.* AES 150. https://github.com/csteinmetz1/pyloudnorm (MIT) [D]
- Deruty, E., Tardieu, D. (2014). *About dynamic processing in mainstream music.* JAES 62(1/2). [B]
- Urbano, J., Bogdanov, D., Herrera, P., Gómez, E., Serra, X. (2014). *What is the effect of audio quality on the robustness of MFCCs and chroma features?* ISMIR. https://archives.ismir.net/ismir2014/paper/000326.pdf [D]

### Essentia ve geçerlilik
- Liem, C. C. S., Mostert, C. (2020). *Can't trust the feeling? How open data reveals unexpected behavior of high-level music descriptors.* ISMIR. https://program.ismir2020.net/poster_2-10.html [D]
- Sturm, B. L. (2016). *The "horse" inside: Seeking causes behind the behaviours of music content analysis systems.* arXiv:1606.03044 [D]; Sturm (2014) IEEE TMM 16(6) [B]
- Alonso-Jiménez, P., Bogdanov, D., Pons, J., Serra, X. (2020). *TensorFlow audio models in Essentia.* ICASSP. [D, atıf önerisi]
- Alonso-Jiménez, P., Serra, X., Bogdanov, D. (2022). *Music representation learning based on editorial metadata from Discogs.* ISMIR. [D]
- MAEST model kartı (CC BY-NC-SA 4.0). https://huggingface.co/mtg-upf/discogs-maest-30s-pw-73e-ts [D]
- MTG approachability/engagement. https://replicate.com/mtg/music-approachability-engagement [D]
- Alonso-Jiménez, P., Ramoneda, P., Araz, R. O., Poltronieri, A., Bogdanov, D. (2025). *OMAR-RQ.* ACM MM Open Source; arXiv:2507.03482; https://github.com/MTG/omar-rq [D]

### Gömüler
- Yuan, R. vd. (2023). *MARBLE: Music audio representation benchmark for universal evaluation.* NeurIPS D&B. https://proceedings.neurips.cc/paper_files/paper/2023/hash/7cbeec46f979618beafb4f46d8f39f36-Abstract.html ; v2: https://github.com/a43992899/MARBLE [D]
- Li, Y. vd. (2024). *MERT: Acoustic music understanding model with large-scale self-supervised training.* ICLR. https://arxiv.org/abs/2306.00107 ; kod (Apache-2.0): https://github.com/yizhilll/MERT [D]
- Zhu, H. vd. (2025). *MuQ: Self-supervised music representation learning with Mel residual vector quantization.* arXiv:2501.01108; https://github.com/tencent-ailab/MuQ (kod MIT, ağırlık CC BY-NC 4.0, 24 kHz) [D]
- Wu, Y. vd. (2023). *Large-scale contrastive language-audio pretraining with feature fusion and keyword-to-caption augmentation* (LAION-CLAP). ICASSP. https://github.com/LAION-AI/CLAP (CC0, müzik checkpoint'leri ve GTZAN sonuçları) [D]
- Elizalde, B. vd. (2023). *CLAP: Learning audio concepts from natural language supervision.* ICASSP. https://arxiv.org/abs/2206.04769 [D]
- HF transformers `ClapFeatureExtractor` kaynak kodu (rand_trunc/fusion rastgeleliği, 10 sn, 14 kHz). https://github.com/huggingface/transformers/blob/main/src/transformers/models/clap/feature_extraction_clap.py [D]
- Pons, J., Serra, X. (2019). *musicnn: Pre-trained convolutional neural networks for music audio tagging.* ISMIR LBD; https://github.com/jordipons/musicnn (ISC) [D]
- Cramer, J., Wu, H.-H., Salamon, J., Bello, J. P. (2019). *Look, listen and learn more: Design choices for deep audio embeddings.* ICASSP; https://github.com/marl/openl3 (MIT / CC BY 4.0) [D]
- Kong, Q. vd. (2020). *PANNs: Large-scale pretrained audio neural networks for audio pattern recognition.* IEEE/ACM TASLP 28. [B]
- Pasini, M., Lattner, S., Fazekas, G. (2024). *Music2Latent.* ISMIR; https://github.com/SonyCSLParis/music2latent (CC BY-NC 4.0) [D]
- Wu, S. vd. (2025). *CLaMP 3.* ACL; https://github.com/sanderwood/clamp3 (MIT) [D]
- Won, M., Hung, Y.-N., Le, D. (2024). *A foundation model for music informatics* (MusicFM). ICASSP. [B]
- Tamm, Y.-M., Aljanaki, A. (2024). *Comparative analysis of pretrained audio representations in music recommender systems.* arXiv:2409.08987 [D]
- (2026). *Adopting state-of-the-art pretrained audio representations for music recommender systems.* arXiv:2604.23077 [D başlık ve sonuç]
- (2026). *From classification to recommendation: Empirical analysis of audio embedding models...* arXiv:2608.06928 [D başlık; sonuçlar okunamadı]
- Vohra, A., Akama, T. (2026). *Interpretable and perceptually-aligned music similarity with pretrained embeddings.* arXiv:2601.19109 [D abstract]
- Roy, A., Liang, J., Herremans, D. (2026). *MERIT: Learning disentangled music representations for audio similarity.* arXiv:2605.27346; https://dorienherremans.com/content/what-if-music-similarity-wasnt-single-number [D]
- (2024). *Artist similarity with audio embeddings* (OLGA tarzı). arXiv:2409.09026 [D başlık]
- Rouard, S., Massa, F., Défossez, A. (2023). *Hybrid transformers for music source separation.* ICASSP. [B]

### Füzyon
- McFee, B., Lanckriet, G. (2011). *Learning multi-modal similarity.* JMLR 12. [B]
- Cormack, G. V., Clarke, C. L. A., Büttcher, S. (2009). *Reciprocal rank fusion outperforms Condorcet and individual rank learning methods.* SIGIR. [B]

### Müzik psikolojisi
- Rentfrow, P. J., Gosling, S. D. (2003). *The do re mi's of everyday life.* JPSP 84(6). [B]
- Rentfrow, P. J., Goldberg, L. R., Levitin, D. J. (2011). *The structure of musical preferences: A five-factor model.* JPSP 100(6). [D]
- Rentfrow, P. J. vd. (2012). *The song remains the same: A replication and extension of the MUSIC model.* Music Perception 30(2). https://www.gsb.stanford.edu/index%2Ephp/node/428616 [D]
- Greenberg, D. M., Kosinski, M., Stillwell, D. J., Monteiro, B. L., Levitin, D. J., Rentfrow, P. J. (2016). *The song is you: Preferences for musical attribute dimensions reflect personality.* Social Psychological and Personality Science 7(6). https://doi.org/10.1177/1948550616641473 [D; yazar listesi doğrulanmalı]
- Müllensiefen, D., Gingras, B., Musil, J., Stewart, L. (2014). *The musicality of non-musicians: An index for assessing musical sophistication in the general population.* PLoS ONE 9(2): e89642. https://doi.org/10.1371/journal.pone.0089642 [D]
- Chmiel, A., Schubert, E. (2017). *Back to the inverted-U for music preference: A review of the literature.* Psychology of Music 45(6). https://researchers.westernsydney.edu.au/en/publications/back-to-the-inverted-u-for-music-preference-a-review-of-the-liter/ [D]
- Orr, M. G., Ohlsson, S. (2005). *Relationship between complexity and liking as a function of expertise.* Music Perception 22(4). https://www.gwern.net/doc/psychology/novelty/2005-orr.pdf [D]
- Madison, G., Schiölde, G. (2017). *Repeated listening increases the liking for music regardless of its complexity.* Frontiers in Neuroscience 11:147. https://doi.org/10.3389/fnins.2017.00147 [D]
- Matthews, T. E. vd. (2019). *The sensation of groove is affected by the interaction of rhythmic and harmonic complexity.* PLoS ONE 14(1). [B]
- Berlyne, D. E. (1971). *Aesthetics and Psychobiology.* Appleton-Century-Crofts. [B]
