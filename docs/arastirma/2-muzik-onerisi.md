# Müzik önerisi araştırması: literatür ve Müzik Keşif Motoru'na uygulanışı

Hazırlanma: 2026-10-20 · Kapsam: müzik öneri sistemleri araştırması (2008–2026) ve projeye
aktarılabilecek teknikler. Kod yazılmadı; öneriler numpy + SQLite ile, LLM'siz, 0 TL koşuluna
göre süzüldü.

---

## 0. Yöntem notu: bu raporun kanıt düzeyi

- **Arama:** 34 web araması yapıldı (birincil kaynaklar: arXiv, ISMIR, ACM RecSys/TIST/TORS,
  WWW, NeurIPS, AAAI, Deezer Research, Spotify Research). Bu turun ortak arama bütçesi
  (200 arama, tüm alt ajanlarla paylaşılan) dolunca arama durdu. Bütçe yüzünden
  aranamayan birkaç kaynak aşağıda **[B]** ile işaretli.
- **Tam metin okunamadı:** `WebFetch` bu oturumda DNS hatası verdi; arXiv'e doğrudan erişim de
  vekil sunucu tarafından reddedildi. Bu yüzden kaynakların **özet, bildiri sayfası ve arama
  özetleri** okunabildi; tam metin okunamadı.
- **İşaretler:**
  - İşaretsiz iddialar bu oturumda bir kaynakta (özet/bildiri sayfası) görüldü.
  - **[B]**: bellekten; bu oturumda doğrulanamadı. Yöntemin özü güvenilir ama sayı, tablo ve
    ayrıntı birincil kaynaktan teyit edilmeli.
  - **[P]**: projenin kendi ölçümü (`docs/karar-gunlugu.md`, `CLAUDE.md`).
- **İstemdeki bir düzeltme:** Korzeniowski, Oramas ve Gouyon'un (2021) GNN ile sanatçı benzerliği
  makalesi **Deezer'ın değil, Pandora'nın** (SiriusXM) çalışması. Deezer'ın grafik çalışması
  Salha-Galvan ve ark. (2021, gravity-inspired graph autoencoder).

---

## 1. Yönetici özeti: projeye en çok kazandıracak 10 teknik

Sıralama **beklenen kazanç / maliyet** oranına göre. Maliyet, numpy ile yazma ve ölçme emeği
artı yeni veri gereksinimidir; kazanç, projenin bilinen kusurlarına (dil sızıntısı, düşük
tavan, vekil ölçüt ile gerçek tercih arasındaki uyumsuzluk) ne kadar dokunduğudur.

| # | Teknik | Neyi çözer | Maliyet | Beklenen kazanç | Ana kaynak |
|---|---|---|---|---|---|
| 1 | **Eşleştirilmiş sıfır modeliyle birliktelik** (dil ve popülerlik katmanında beklenenin üstü) + bağlamsız destek kapısı | Dil/ruh hâli sızıntısı (Sezen Aksu vakası) | Düşük | Yüksek | Lesota 2022; Pichl 2015/2017; Hao & Downie 2020; Zamani 2019 |
| 2 | **Bağımsız kanıtla çapraz onay:** vokalsiz stem üzerinden CLAP + kademeli melez | Melezin iki sinyalinin aynı şeyi (dil/vokal tınısını) taşıması | Düşük–orta | Yüksek | Burke 2002 [B]; van den Oord 2013; proje [P] |
| 3 | **RP3β / ProbS–HeatS rastgele yürüyüşü** (liste–sanatçı iki parçalı grafiği, kredi ve LB kenarlarıyla) | Düşük tavan (2. derece erişim) ve açık bir yenilik düğmesi | Düşük | Orta–yüksek | Zhou 2010 [B]; Christoffel 2015 [B]; Dacrema 2019 [B] |
| 4 | **Popülerliğe duyarlı ölçüm:** popülerlik-tabakalı recall, dil-içi gizleme sınaması, öneri/kütüphane popülerlik dağılımı | Vekil ölçütün popülerliği ve dil karışıklığını ödüllendirmesi | Düşük | Yüksek (karar kalitesi) | Steck 2011 [B]; Lesota 2021; Kowald 2020; Abdollahpouri 2019 |
| 5 | **Çalma listesi havuzunu tür/sahne sorgularıyla büyütmek** (sanatçı adıyla aramanın yanında) | 482 liste çok küçük; tohum-adı yanlılığı | Düşük–orta | Yüksek (tavan) | Zamani 2019 (ölçeğin önemi); Bonnin & Jannach 2014 [B] |
| 6 | **Bandit iyileştirmesi:** havuzlanmış (hiyerarşik) Beta önseli, «beğendi ∧ yeni» ödülü, takım-seçmeli harmanlama (team-draft interleaving) | n küçükken kaynak payını daha hızlı ve daha az gürültüyle öğrenmek | Düşük | Orta | McInerney 2018; Chapelle 2012 [B]; Radlinski 2008 [B] |
| 7 | **Küçük ikinci aşama yeniden sıralayıcı** (Bayesçi lojistik + Laplace, Thompson ile; gerçek kararlar + LOAO sözde-etiketleri) | Kaynak ağırlıklarını gerçek tercihten öğrenmek (vl6 dersi) | Orta | Orta–yüksek (n büyüdükçe) | Volkovs 2018; Zamani 2019; Chapelle & Li 2011 [B] |
| 8 | **EASE ve PPMI-SVD sanatçı gömüsü** (kapalı formlu madde–madde modelleri) | NPMI'ya güçlü, deterministik alternatif; 2. derece benzerlik | Düşük–orta | Orta | Steck 2019 [B]; Levy & Goldberg 2014/2015 [B]; Anderson 2020 |
| 9 | **Sesten kalabalığa köprü:** CLAP→PPMI-SVD ridge eşlemesi ve grafik üzerinde ses yumuşatma (SGC/APPNP tarzı, eğitimsiz) | Listede hiç görünmeyen adaylar; sesin kalabalıkla hizalanması | Orta | Orta | van den Oord 2013; Korzeniowski 2021/2022; Salha-Galvan 2021 |
| 10 | **Çeşitlilik ve kalibrasyon yeniden sıralaması:** MMR/DPP + kalibre popülerlik + GS-skoru tanısı | Destenin tek tipleşmesi, popülere kayma | Düşük | Düşük–orta | Carbonell & Goldstein 1998 [B]; Steck 2018; Abdollahpouri 2021 [B]; Anderson 2020 |

Bekleyebilecek, pahalı veya kazancı belirsiz olan iş: **ses omurgasını MuQ / MuQ-MuLan ile
değiştirmek** (Tamm & Aljanaki 2024/2026). Literatür çelişkili; ancak kendi ölçümümüzle karar
verilmeli (§3.11).

---

## 2. Literatür

### 2.1 Uzun kuyruk, keşif ve tanıdıklık–yenilik gerilimi (Celma)

- **Celma (2008 doktora tezi; 2010 kitabı *Music Recommendation and Discovery: The Long Tail,
  Long Fail, and Long Play in the Digital Music Space*, Springer).** Temel tez: müzik tüketimi
  az sayıda popüler sanatçıya yığılır. Standart önericiler kullanıcının zaten bildiği ya da
  popüler olanı önerir, bu da öneriyi etkisizleştirir. Celma yenilik (novelty) ile
  ilgililiği (relevance) iki ayrı eksen olarak koyar: tanıdık şarkı ilgilidir ama yeniliği
  düşüktür; keşfin hedefi «ilgili ama çok yeni» bölgesidir. «Long Fail» kavramı, kuyruktan
  önerilen ama kötü çıkan öğeleri anlatır: kuyruğa gitmek tek başına başarı sayılmaz.
  Tezdeki ağ analizi ve kullanıcı çalışması, işbirlikçi filtrelemenin popülere, içerik
  tabanlı yöntemlerin daha yeniye ama daha riskliye gittiğini gösterir [B: deneylerin
  ayrıntısı].
- **Projeye anlamı:** K17'deki «sahiplik = evet» ve K19'daki «hiç duymadığım sanatçı» ölçütü
  tam olarak Celma'nın ikinci ekseni. Projenin ölçtüğü uyumsuzluk da (liste yolu çevrimdışı
  en iyi, ama gerçek kararlarda ses yolu daha çok beğenildi, [P]) bu gerilimin yerel bir
  örneği: sahip olunanı geri bulmak tanıdıklığı ödüllendiriyor.

### 2.2 Anketler: güncel zorluklar

- **Schedl, Zamani, Chen, Deldjoo, Elahi (2018), «Current challenges and visions in music
  recommender systems research», *IJMIR* 7(2):95–116.** Akademi ve endüstrinin ortak
  zorluk listesi. Hatırlanan başlıklar [B]: soğuk başlangıç, otomatik çalma listesi
  sürdürme, değerlendirme (doğruluk ötesi ölçütler). Gelecek yönleri: psikoloji temelli,
  duruma duyarlı ve kültüre duyarlı öneri.
- **Schedl, Knees, McFee, Bogdanov (2022), «Music Recommendation Systems: Techniques, Use
  Cases, and Challenges», *Recommender Systems Handbook* (3. baskı), s. 927–971.** Kullanıcı
  merkezli bir sınıflama yapar: temel öneri, **lean-in keşif** ve **lean-back dinleme**.
  İçerik tabanlı filtreleme, ardışık öneri, psikoloji temelli yaklaşımlar ve
  adalet/açıklama/değerlendirme/arayüz zorluklarını kapsar.
  → **Proje lean-in keşif sistemidir.** Bu sınıfta kullanıcı kararı bilerek verir ve
  açıklama okur. Kaydırmalı deste (K21) bu kullanım için doğru arayüz.
- **Deldjoo, Schedl, Knees (2021 ön baskı; 2024 *Computer Science Review* 51), «Content-driven
  music recommendation: Evolution, state of the art, and challenges».** 55 çalışmayı tarar.
  **Soğan (onion) modeli** içeriği beş katmana ayırır: sinyal, gömülü metadata, uzman
  içeriği, kullanıcı üretimi içerik, türev içerik. Altı zorluk sayar: çeşitlilik/yenilik,
  şeffaflık/açıklama, bağlam duyarlılığı, dizi, ölçeklenebilirlik, soğuk başlangıç.
  Music4All-Onion (Moscati ve ark., CIKM 2022) bu katmanlara göre özellik veri setidir.
  → Projenin kaynakları soğana birebir oturuyor: sinyal (CLAP, stem), uzman (kredi grafiği),
  kullanıcı üretimi (çalma listeleri, ListenBrainz), türev (kümeler). Bu çerçeve, gerekçe
  metninde «kanıt hangi katmandan geliyor» demek için kullanılabilir.

### 2.3 ACM RecSys Challenge 2018 ve otomatik çalma listesi sürdürme

- **Görev ve veri:** Spotify Million Playlist Dataset (1M liste, ~2M parça). Değerlendirme
  R-precision, NDCG ve «tıklama». Ana kulvarda en iyi skorlar R-precision 0,2241 ve NDCG
  0,3946 (Zamani ve ark. 2019).
- **Zamani, Schedl, Lamere, Chen (2019), «An analysis of approaches taken in the ACM RecSys
  Challenge 2018 for automatic music playlist continuation», *ACM TIST* 10(5):57.** Bulgular:
  - Üst sıradaki çözümlerin çoğu **bilinen yöntemleri birleştirdi**: matris ayrışımı,
    komşuluk tabanlı işbirlikçi filtreleme, basit bilgi erişimi ve sıralamayı öğrenme
    (learning-to-rank). Birçok takım **iki aşamalı mimari** kullandı.
  - Tohum parça sayısı yeterliyse ve parçalar sırayla değil rastgele seçilmişse modeller
    en iyi sonucu verdi. Az tohumda yöntemler arasındaki fark kapandı.
  - **Çalma listesi başlıkları etkili kullanılamadı.** Yazarlar sebebi başlıkların seyrekliği
    ve verinin ölçeği olarak görüyor. Hiçbir çözüm başlıktan **kullanıcı niyetini**
    çıkarmaya çalışmadı. → Bizim için önemli: başlık güçlü ama gürültülü bir bağlam
    sinyali; sinyal olarak değil **bağlam ayıklayıcısı** olarak kullanılmalı (§3.1).
- **Volkovs, Rai, Cheng, Wu, Lu, Sanner (2018), «Two-stage model for automatic playlist
  continuation at scale» (takım vl6, Layer 6 AI): ana ve yaratıcı kulvarda birinci.**
  - 1. aşama: işbirlikçi filtreleme (ağırlıklı MF) ve derin öğrenme (CNN) modelleri 2,2M
    parçalık uzayı liste başına **20 bin adaya** indiriyor; bu aşamanın recall'u %90'ın
    üstünde.
  - 2. aşama: adaylara CNN gömü modeli, **kullanıcı-kullanıcı ve madde-madde komşuluk**
    modellerinden ek skorlar ekleniyor. Tüm model skorları, bunların doğrusal karışımı
    (blend) ve çıkarılmış liste-parça öznitelikleri **XGBoost** ile (150 ağaç, derinlik 10)
    çiftli olarak skorlanıyor. **Sıralama kaybı, ikili çapraz entropiden iyi çıkıyor.**
  - Öznitelik listesinin ve önem sırasının ayrıntısı tam metinde; okunamadı. Hatırlanan
    öznitelikler [B]: liste uzunluğu, sanatçı/albüm çeşitliliği, aday parçanın popülerliği,
    adayın listedeki parçalara benzerliğinin ortalama/en büyük/en küçük değerleri,
    sanatçı/albüm eşleşme sayıları.
- **Avito takımı (3. sıra, ana kulvar), «A hybrid two-stage recommender system for automatic
  playlist continuation».** Aday seçimi işbirlikçi filtrelemeyle, son tahmin gradyan
  güçlendirmeyle yapıldı.
- **Creamy Fireflies (4. sıra, ana kulvar; Politecnico di Milano [B]), «Artist-driven layering
  and user's behaviour impact on recommendations in a playlist continuation scenario»
  (arXiv 2010.06233).** İşbirlikçi ve içerik tabanlı teknikleri birleştiren melez sistem.
  Hem listelerin yapısından hem alan bilgisinden (sanatçı katmanı) yararlanıyor.
- **Klasik temel çizgiler:** Bonnin & Jannach (2014, *ACM CSUR* 47(2):26) bir çalma listesi
  üretimi anketi ve deneyleri yayımladı [B: içerik]. Bonnin & Jannach (ISMIR 2013), parça
  popülerliği ve sanatçı bilgisine dayanan basit bir temel çizgi önerdi. Jannach, Kamehkhosh
  ve Bonnin (UMAP 2016) sanatçı birlikteliğini benzerlik olarak kullanan «Collocated Artists
  – Greatest Hits» (CAGH) yöntemini ve **kNN (aynı parçaları içeren başka listeler) güçlü bir
  temel çizgidir** bulgusunu raporladı.
- **Projeye ders:** (i) Kazanan desen *kaba geniş aday + ince yeniden sıralama*. Proje zaten
  kaynak başına aday üretiyor, ikinci aşama ise eksik. (ii) Basit komşuluk yöntemleri güçlü,
  NPMI bu ailenin içinde; ama 2. derece (rastgele yürüyüş) ve kapalı formlu (EASE) üyeleri
  denenmedi. (iii) Başlık, sinyal olarak değil niyet/bağlam ayıklayıcısı olarak kullanılmalı.

### 2.4 İçerik tabanlı öneri, soğuk başlangıç ve ses gömüleri

- **van den Oord, Dieleman, Schrauwen (2013), «Deep content-based music recommendation»,
  NeurIPS 26.** İşbirlikçi filtrelemenin gizil faktörleri **sesten tahmin edilir**; kullanım
  verisi olmayan (yeni/popüler olmayan) şarkılarda soğuk başlangıç böyle aşılır. Derin
  CNN'ler kelime-torbası temel çizgisini belirgin biçimde geçti. Ses ile kullanıcı tercihi
  arasında «büyük anlamsal boşluk» olmasına rağmen tahmin edilen faktörler anlamlı öneri
  üretti. → **Projedeki karşılığı:** CLAP gömüsünden çalma listesi gömüsüne doğrusal bir
  eşleme (§3.9).
- **Pons & Serra (2019), «musicnn: Pre-trained convolutional neural networks for music audio
  tagging», ISMIR.** Müzikal motivasyonlu, önceden eğitilmiş etiketleyiciler; MTT'de
  ROC-AUC 90,69 / PR-AUC 38,44. 200 boyutlu, küçük ve hızlı.
- **MERT (Li ve ark., ICLR 2024).** RVQ-VAE akustik öğretmeni ve CQT müzikal öğretmeniyle
  MLM tarzı öz-denetimli ön eğitim, 95M–330M parametre. **MARBLE** (Yuan ve ark. 2023)
  benchmark'ında 14 görevde güçlü.
- **MuQ (Zhu ve ark., arXiv 2501.01108, 2025; Tencent AI Lab).** Mel-RVQ belirteçlerini
  tahmin eden öz-denetimli model. Yalnız 0,9 bin saat açık veriyle önceki modelleri geçiyor.
  **MuQ-MuLan:** CLIP tarzı müzik–metin ortak gömüsü, MTT'de sıfır-atış etiketlemede en iyi.
  Kod MIT lisanslı, PyPI'da `muq` paketi var. Ağırlıkların lisansı ayrıca denetlenmeli
  [B: hatırladığım kadarıyla ticari olmayan kullanım].
- **Tamm & Aljanaki (2024), «Comparative analysis of pretrained audio representations in
  music recommender systems», RecSys 2024 (arXiv 2409.08987).** MusicFM, Music2Vec, MERT,
  EncodecMAE, Jukebox ve MusiCNN'i öneri modellerinde karşılaştırdı. **MusiCNN tutarlı olarak
  en iyisi.** Yazarlar bunu denetimli otomatik etiketleme eğitimine bağlıyor; ardından MERT
  ve EncodecMAE geliyor.
- **Tamm & Aljanaki (2026), «Adopting state-of-the-art pretrained audio representations for
  music recommender systems», ACM (doi 10.1145/3808222; arXiv 2604.23077).** Dokuz omurgayı
  (MULE, MuQ, MuQ-MuLan dahil) beş öneri yaklaşımıyla, sıcak ve soğuk senaryoda sınıyor.
  **MuQ ve MuQ-MuLan hem sıcak hem soğukta en üstte.** MuQ-MuLan melez önericide iki
  senaryoda da en iyi; soğuk testte HitRate@20 0,2502, MuQ'da 0,1726. Önemli bulgu:
  **standart MIR görevlerindeki başarı öneri başarısını öngörmüyor.**
- **«From classification to recommendation: Empirical analysis of audio embedding models
  application for content-based music recommendation» (arXiv 2608.06928, 2026).** Uyarlama
  yapılmadan (eğitimsiz benzerlik) kullanıldığında **hizalama tabanlı (metin–ses karşıtlıklı)
  modeller** daha iyi. Müziğe özgü CLAP benzerlik araması için en güçlü anlamsal uzay;
  arama özetine göre 18 ayarın 13'ünde en iyi. Yeterli etkileşim verisi varsa (SASRec)
  omurga seçimi daha az önemli. Müzik verisiyle ön eğitilmiş gömüler genel ses/konuşma
  gömülerinden iyi.
- **CLAP gömüleriyle grafik tabanlı sanatçı ilişkisi tahmini (RecSys 2024 çalıştayı, arXiv
  2409.09026):** CLAP gömüleri grafik tabanlı çerçevelerde umut verici bulundu.
- **Projeye anlamı:** Eğitimsiz benzerlik kullanan bir sistem için CLAP seçimi literatürle
  uyumlu. Model değişikliği kararı benchmark'tan değil projenin kendi LOAO ve karar
  ölçümünden çıkmalı (2026 bulgusu tam olarak bunu söylüyor). Projenin özgün katkısı olan
  stem tabanlı icra profili için doğrudan bir karşılık literatürde bulunamadı. Bu bir boşluk:
  icracı düzeyinde ses profili, bilinen öneri çalışmalarında yok.

### 2.5 Popülerlik yanlılığı

- **Abdollahpouri, Mansoury, Burke, Mobasher (2019), «The unfairness of popularity bias in
  recommendation» (arXiv 1907.13286).** Kullanıcı açısından popülerlik yanlılığı:
  niş zevkli kullanıcılar beklentilerinden daha popüler öneri alır. Devamı olan «The
  connection between popularity bias, calibration, and fairness in recommendation»
  (2019/2020), popülerlik yanlılığından ne kadar etkilenen bir grubun önerilerinin o kadar
  **kalibrasyonsuz** olduğunu gösterir. «Addressing the multistakeholder impact of popularity
  bias in recommendation through calibration» (arXiv 2007.12230, 2020) kalibrasyonla düzeltme
  önerir; müzik ve film verisinde mevcut yöntemleri geçer ve sağlayıcı adaletini de iyileştirir.
  «Calibrated Popularity» (CP) yeniden sıralaması ve «user popularity deviation» ölçütü
  UMAP 2021 makalesinde (Abdollahpouri ve ark., «User-centered evaluation of popularity bias
  in recommender systems») [B].
- **Kowald, Schedl, Lex (2020), «The unfairness of popularity bias in music recommendation:
  A reproducibility study», ECIR (arXiv 1912.04696).** LFM-1b'den 3.000 kullanıcı, ana akıma
  yakınlığa göre üç grup. Müzikte de algoritmalar popülere yanlı ve **ana akımdan uzak (LowMS)
  grup belirgin biçimde en kötü öneriyi alıyor.** Film alanındaki grup ortalama popülerlik
  ölçütü müzikte farklı davranıyor; sebep sanatçı sayısının çok fazla olması.
  → **Bu proje kullanıcısı tam olarak LowMS:** teknik prog metal, Japon fusion, Türk rock.
- **Lesota ve ark. (2021), «Analyzing item popularity bias of music recommender systems: Are
  different genders equally affected?», RecSys LBR (arXiv 2108.06973).** Ortalama/medyan
  farkı yerine **profil ve öneri listesinin popülerlik dağılımlarını** karşılaştırır: medyan,
  momentler, KL ıraksaması, Kendall τ. Daha az popülerlik yanlısı algoritmaların NDCG'de
  mutlaka kötü olmadığını gösterir.
- **Lesota ve ark. (2022), «Traces of globalization in online music consumption patterns and
  results of recommendation algorithms», ISMIR.** Last.fm'de ABD müziği her ülkede güçlü.
  **ItemKNN birçok ülkenin kullanıcısına yerli müzik öneriyor, NeuMF ise ABD baskınlığını
  hızlandırıyor.** → **Bizim sızıntının literatürdeki adı bu:** birlikteliğe dayalı komşuluk
  yöntemleri ülke/dil sinyalini taşır. Sezen Aksu vakası bir hata değil, ItemKNN ailesinin
  bilinen bir özelliği. Dil yerellikle aynı şey olduğu için sinyal gerçek, ama eksen sorusuna
  ait değil.
- **Steck (2011), «Item popularity and recommendation accuracy», RecSys [B].** Rastgele
  eksik olmayan (MNAR) veride sıradan recall popüleri ödüllendirir. Önerdiği
  **popülerlik-tabakalı recall**, isabeti 1/pop^γ ile ağırlıklandırır. Ayrıca Steck (2010,
  KDD), «Training and testing of recommender systems on data missing not at random» [B].
  → Projenin `KANIT_BUZULMESI` k=1/k=4 ikilemi bu ölçütle resmîleştirilebilir (§3.4).

### 2.6 Çeşitlilik, serendipity, yenilik

- **Kaminskas & Bridge (2016), «Diversity, serendipity, novelty, and coverage: A survey and
  empirical analysis of beyond-accuracy objectives in recommender systems», *ACM TiiS*
  7(1) [B: künye].** Tanımlar: *yenilik* kullanıcının bilmediği öğe (popülerlikle
  bağlantılı); *beklenmedik olma* beklenenden sapan ilgili öğe; *serendipity* ilgililik ile
  şaşırtıcılığın birleşimi; *çeşitlilik* listedeki ortalama çiftli uzaklık; *kapsama*
  katalogdan ne kadarının önerildiği. Kaminskas & Bridge (2014, RecSys çalıştayı, «Measuring
  surprise in recommender systems») şaşkınlığı **kullanıcının bildiklerine en yakın
  benzerliğin tersi** olarak tanımlar. İçerik ya da birliktelik tabanlı (NPMI) iki uzaklık
  da kullanılır [B: NPMI ayrıntısı].
- **Anderson, Maystre, Anderson, Mehrotra, Lalmas (2020), «Algorithmic effects on the
  diversity of consumption on Spotify», WWW 2020.** 100M+ premium kullanıcı, ~70 milyar dinleme
  (Temmuz 2019). Çeşitlilik, çalma listelerinde word2vec ile eğitilmiş 40 boyutlu şarkı
  gömüsünde (850M liste) **genelci–uzman skoru (GS-skoru)** ile ölçülüyor: tüketilen
  vektörlerin ağırlık merkezine ortalama kosinüs benzerliği; yüksek değer odaklı, düşük
  değer çeşitli dinleme. Bulgular:
  1. Çeşitlilik uzun vadeli metriklerle (dönüşüm, elde tutma) ilişkili.
  2. **Algoritmik dinleme daha düşük çeşitlilikle ilişkili.**
  3. Kullanıcılar çeşitlendikçe algoritmik dinlemeden organik dinlemeye kayıyor.
  4. Rastgele deneyde öneriler **çeşitliliği düşük kullanıcılarda** daha iyi çalıştı.
  → 12 eksenli bu kullanıcı bir «genelci». Literatüre göre genelci kullanıcıya standart
  öneri en kötü hizmeti veriyor. Projenin eksen seçtirme kararı (kullanıcı hangi tarafını
  beslemek istediğini seçiyor) bu bulguya doğrudan bir cevap.
- **Zhou, Kuscsik, Liu, Medo, Wakeling, Zhang (2010), «Solving the apparent
  diversity-accuracy dilemma of recommender systems», *PNAS* 107(10):4511–4515 [B].** İki
  parçalı grafikte iki yayılım tanımlanır: **kütle yayılımı (ProbS)** doğruluğu,
  **ısı iletimi (HeatS)** yeniliği öne çıkarır. Tek bir λ parametresiyle melezlenir ve
  doğruluktan neredeyse ödün vermeden yenilik artırılabilir. → Projeye uygulanışı §3.3'te.
- **MMR (Carbonell & Goldstein 1998, SIGIR) [B]** ve **DPP (Chen, Zhang, Zhou 2018,
  «Fast greedy MAP inference for determinantal point process to improve recommendation
  diversity», NeurIPS) [B]:** ilgililik ile listedeki benzerliği dengeleyen yeniden sıralama.
  DPP'de çekirdek L = diag(r)·S·diag(r) olur ve açgözlü MAP artımlı Cholesky ile hızlı çözülür.

### 2.7 Kalibrasyon

- **Steck (2018), «Calibrated recommendations», RecSys.** Öneri listesi kullanıcının ilgi
  oranlarını yansıtmalı: 70 romantik ve 30 aksiyon izleyen birine 70/30 önerilmeli.
  Açgözlü yeniden sıralama hedefi şudur:
  `(1−λ)·Σ ilgililik − λ·KL(p ‖ q̃)`. Burada p kullanıcının tür dağılımı, q̃ listenin
  yumuşatılmış dağılımıdır (sıfır sorunu için yumuşatılır). Sonraki eleştiri: KL sınırsız;
  açgözlü çözüm optimumdan uzak kalabilir ve doğrusal programlama alternatifleri var.
- **Projeye anlamı:** Kullanıcı ekseni kendisi seçtiği için eksenler arası kalibrasyon
  gerekmiyor (K2/K3 ruhu). Ama **eksen içinde** iki kalibrasyon anlamlı: (i) popülerlik
  dağılımı (kütüphanenin baş/orta/kuyruk oranları, Abdollahpouri CP), (ii) dil/bölge
  dağılımı (eksenin kendi dil oranı; Türk rock ekseni Türkçe öneri alsın ama grunge ekseni
  eksenin dil oranından fazlasını almasın).

### 2.8 Keşif–sömürü, bandit ve açıklama

- **McInerney, Lacker, Hansen, Higley, Bouchard, Gruson, Mehrotra (2018), «Explore, exploit,
  and explain: Personalizing explainable recommendations with bandits», RecSys (s. 31–39).**
  Spotify'ın BaRT sistemi: öğe ile **açıklamayı birlikte** bir eylem olarak ele alan
  bağlamsal bandit. Açıklama eklemenin kullanıcı memnuniyetini ve önerinin ikna gücünü
  artırdığı biliniyor. Hatırlanan ayrıntılar [B]: ödül modeli faktörizasyon makinesi;
  ε-açgözlü keşif; karşı-olgusal (off-policy) değerlendirme; aynı öğe farklı açıklamayla
  farklı ödül getiriyor.
- **Thompson örneklemesi:** Chapelle & Li (2011), «An empirical evaluation of Thompson
  sampling», NeurIPS [B]. Lojistik ödülle Laplace yaklaşımlı Bayesçi lojistik regresyon
  kullanılır; arka dağılımdan örneklenerek seçilir. Projede Beta–Bernoulli hâli zaten var [P].
- **Harmanlama (interleaving):** Radlinski, Kurup, Joachims (2008, CIKM), takım-seçmeli
  harmanlama [B]. Chapelle, Joachims, Radlinski, Yue (2012, *ACM TOIS*), «Large-scale
  validation and analysis of interleaved search evaluation»: harmanlama, A/B testine göre
  aynı farkı çok daha az etkileşimle saptar [B].

### 2.9 Açıklama

- **Afchar, Melchiorre, Schedl, Hennequin, Epure, Moussallam (2022), «Explainability in music
  recommender systems», *AI Magazine* 43(2):190–208 (Deezer + JKU).** Gerçek sistemler
  doğruluğa optimize edilmiş, birden çok yapı taşını birleştiren karmaşık sistemler, bu da
  açıklamayı zorlaştırıyor. Açıklanabilirlik güveni ve affediciliği artırıyor. Açıklama
  kalitesi doğruluktan ayrı değerlendirilmeli; makale bunun gerekliliklerini ve
  stratejilerini tartışıyor.
- **Millecamp, Htun, Conati, Verbert (2019), «To explain or not to explain: The effects of
  personal characteristics when explaining music recommendations», IUI.** Spotify ses
  öznitelikleriyle (popülerlik, mutluluk, enerji, dans edilebilirlik) çubuk grafik
  açıklamaları kullanıldı. **Kişisel özellikler etkileşimi değiştiriyor;** bilişsel ihtiyacı
  düşük kullanıcılar açıklamadan en çok yararlanıyor. Melchiorre ve ark. (takip çalışması):
  müzikal sofistikasyonu düşük kullanıcılar sade açıklama istiyor.
- **Projeye anlamı:** K7 (şablonlu, sayısal dayanaklı gerekçe) literatürdeki «sadık
  açıklama» idealine birebir uyuyor. Açıklama, öneriyi üreten yolun kendisi. Afchar'ın
  işaret ettiği zorluk (çok bileşenli sistemde açıklamanın bozulması) projede melez yolda
  zaten görüldü: «iki sinyal de işaret ediyor» cümlesi iki sinyal bağımsız olmadığı için
  yanıltıcıydı [P]. Kural şu olmalı: **bağımsızlık iddiası, bağımsızlık ölçülmeden
  kurulmaz** (§3.2).

### 2.10 Grafik tabanlı sanatçı benzerliği ve bilgi grafikleri

- **Korzeniowski, Oramas, Gouyon (2021), «Artist similarity with graph neural networks»,
  ISMIR 2021 (Pandora).** Üçlü kayıpla eğitilen GNN, sanatçı bağlantı grafiğini içerik
  öznitelikleriyle birleştiriyor. **OLGA** veri seti AllMusic benzerliklerini AcousticBrainz
  öznitelikleriyle eşliyor: 17.673 sanatçı. TISMIR 2022 genişletmesi («Artist similarity for
  everyone»): az bağlantısı olan sanatçılar için **bağlantı bırakma (connection dropout)**
  düzenlemesi.
- **Salha-Galvan, Hennequin, Chapus, Tran, Vazirgiannis (2021), «Cold start similar artists
  ranking with gravity-inspired graph autoencoders», RecSys 2021 (Deezer).** Yeni sanatçının
  benzerlerini sıralama, yönlü ve öznitelikli bir grafikte (her sanatçı en benzer k
  komşusuna bağlı) bağlantı tahmini olarak kuruluyor. «Kütleçekimi» mekanizması
  **asimetriyi** modelliyor: benzerlik okları popülere doğru akar [B: kütle yorumu]. Kod ve
  endüstriyel grafik açık.
- **Briand, Salha-Galvan, Bendada, Morlon, Tran (2021), «A semi-personalized system for user
  cold start recommendation on music streaming apps», KDD 2021 (Deezer).** Yeni kullanıcıyı
  heterojen kaynaklardan kurulan kullanıcı kümelerinden birine atayıp küme düzeyinde öneri
  veriyor. Üretimde çalışıyor; 100 bin anonim kullanıcılık veri açık.
  → `/basla` (sanatçı listesiyle başlama) akışının literatürdeki karşılığı.
- **Oramas, Ostuni, Di Noia, Serra, Di Sciascio (2016), «Sound and music recommendation with
  knowledge graphs», *ACM TIST* 8(2).** Metin ve etiketler varlık bağlamayla DBpedia/WordNet'e
  bağlanıp bilgi grafiği kuruluyor; yol tabanlı özniteliklerle melez öneri yapılıyor
  (işbirlikçi yöntemlere göre iyileşme). Yenilik ve uzun kuyruk kazancı ve yol tabanlı
  açıklanabilirlik [B].
  → Projenin kredi grafiği bir bilgi grafiği; «kredi sıçraması» ise yol tabanlı bir öneri.
  K7 şablonları, KG yollarından açıklama üretme literatürüyle aynı fikirde.

### 2.11 Bağlam ve çalma listesi başlıkları

- **Pichl, Zangerle, Specht (2015, ICDMW, «Towards a context-aware music recommendation
  approach: What is hidden in the playlist name?») [B: künye]; Pichl ve ark. (2017, ICMR,
  «Improving context-aware music recommender systems: Beyond the pre-filtering approach»)
  [B].** Liste adlarından bağlam çıkarılıyor: adlar lemmatize ediliyor, sanatçı/albüm/parça
  adları ayıklanıyor, kalan bağlam sözcükleri word2vec benzerliğiyle kümeleniyor. Kümeler
  faktörizasyon makinesine ek öznitelik olarak veriliyor. **Pichl & Zangerle (2021, MTAP):**
  kullanıcıları durumsal bağlam özniteliklerine, parçaları içerik özniteliklerine göre
  kümeleyen çok-bağlamlı kullanıcı modeli.
- **Hao & Downie (2020), «Using latent semantics of playlist titles and descriptions to
  enhance music recommendations», NLP4MusA.** 20.065 liste, word2vec parça vektörleriyle
  562 kümeye ayrılıyor. Başlık+açıklamadan küme üyeliğini Naive Bayes tahmin ediyor;
  soğuk başlangıç için öneriliyor.
- **Chung ve ark. (ISMIR 2017):** birlikte görülen şarkılar ve başlık sözcükleri üzerinden
  denetimsiz öğrenme.
- **Projeye anlamı:** Proje başlıkları zaten bağlam etiketi için kullanıyor. MTG-Jamendo'nun
  56 ruh/tema etiketinden türetilmiş kontrollü bir sözlük var; ama başlıkların yalnız %17'si
  sözlükten terim içeriyor [P]. Yani **başlık tek başına sızıntı süzgeci olamaz,** kapsaması
  çok düşük. Literatürdeki iki çözüm şunlar: (i) **başlığı değil liste İÇERİĞİNİ**
  kümelemek (Hao & Downie; listenin dil homojenliği ve tür dağınıklığı), (ii) başlık
  sözcüklerini parça birlikteliğiyle aynı uzaya gömmek (Chung). Bu proje için (i) ucuz ve
  deterministik (§3.1).

### 2.12 2023–2026: LLM dönemi ve aktarılabilir fikirler (motor LLM'siz kalır)

Bu bölüm arama bütçesi dolduğu için büyük ölçüde **[B]**.
- **Üretken erişim ve «anlamsal kimlikler» (semantic IDs):** Spotify'ın Text2Tracks
  çalışması (Palumbo ve ark. 2025, arXiv 2503.24193) [B]: metin isteminden parça kimliği
  üretiliyor; kimlikler gömülerin hiyerarşik nicemlenmesinden (RVQ/k-means) kuruluyor.
  2026 «From classification to recommendation» makalesi de CLAP'i anlamsal kimlik kurmak
  için en iyi uzay olarak anıyor. **LLM'siz aktarım:** CLAP gömüsünün hiyerarşik k-means
  kodları, «ses ailesi» açıklaması (örneğin «3.2.7 ailesi: Casiopea, Takanaka gibi») ve
  hızlı aday erişimi için deterministik bir dizin olur.
- **Sohbetli/çok kipli öneri:** TalkPlay (Doh ve ark. 2025) [B]. Proje K1 gereği sohbet
  botu değil; aktarılabilir fikir **eleştiri tabanlı öneri** (critiquing, Chen & Pu 2012)
  [B]: «daha az vokal», «daha teknik davul» gibi düğmeler. Bunlar CLAP metin kodlayıcısının
  (üretken LLM değil, yerel bir metin kodlayıcı; projede `etiket_clap.py` zaten kullanıyor)
  **yön vektörleriyle** yapılabilir: `q = μ_eksen + η·(t("instrumental") − t("vocals"))`.
- **LLM önericilerin popülerlik yanlılığı:** 2024–2025'te birçok çalışma LLM tabanlı
  önericilerin popüler sanatçılara güçlü biçimde yığıldığını raporladı [B]. Bu, K2'nin
  (motor LLM'e bağımlı değil) bir keşif sistemi için yalnız maliyet değil, **kalite**
  kararı da olduğunu destekliyor.

---

## 3. Bizim duruma uygulama

### 3.0 Teşhis: neden çevrimdışı en iyi yol gerçek kararlarda en kötü?

Proje ölçümleri [P]:
- LOAO: liste yolu recall@50 ≈ 0,15–0,29 (ayara göre). Ses yolu tek başına 0,03.
- Gerçek kararlar: ses yolunda %67 [25–92] beğeni, liste yolunda %11 [3–38], melezde
  %25 [10–49].
- Liste yolundan gelen 12 kararda bağ gücünün beğeniyi ayırma AUC'u **0,30**. Yani bağ
  güçlendikçe beğeni AZALIYOR.

Literatürün açıklaması üç parçalı:
1. **MNAR ve popülerlik (Steck 2010/2011, Kowald 2020):** Gizleme sınaması «sahip olduğunu
   bulabildin mi» diye soruyor. Sahip olunanlar ortalamada popüler, bu yüzden ölçüt
   popülerliği ödüllendiriyor.
2. **Yerellik/dil (Lesota 2022):** Komşuluk yöntemleri yerli müziği yerli müziğe bağlıyor.
   Kullanıcı birden çok Türk rock sanatçısına sahip olduğu için LOAO'da dil sinyali «doğru»
   görünüyor: Duman gizlenince Şebnem Ferah Türkçe listeler üzerinden geri geliyor [P].
   Eksen sorusunda («grunge») ise aynı sinyal yanlış.
3. **Tanıdıklık–yenilik (Celma; Anderson 2020):** Güçlü birliktelik «tanıdık ve popüler
   komşu» demek. AUC 0,30 bununla tutarlı: en güçlü bağlar kullanıcının ya bildiği ya da
   ilgisini çekmeyen ana akım komşulara gidiyor.

**Sonuç:** Liste sinyali atılmamalı; tavanı en yüksek kaynak o. Ama (a) sıfır modeli dil ve
popülerliği kontrol edecek biçimde değişmeli, (b) değerlendirme bu iki karışıklığı ayıracak
biçimde tabakalanmalı, (c) son karar gerçek kararlardan öğrenilmeli.

Aşağıdaki gösterim boyunca:
`X ∈ {0,1}^{L×A}` liste × sanatçı ikili matrisi (L=482, A=10.360); `w ∈ ℝ^L` liste
ağırlıkları; `k_A = Xᵀw` sanatçı derecesi; `k_L = X·1` liste boyu; `q ∈ ℝ^A` eksenin sorgu
vektörü (kütüphane sanatçılarında FCM üyeliği `u_ik`, dışarıda 0).

---

### 3.1 [#1] Dil/ruh hâli sızıntısını önleme: bağlam farkında birliktelik

Üç katman; birbirini tamamlıyor, her biri ayrı ölçülebilir.

**(a) Eşleştirilmiş sıfır modeli: «aynı dil ve aynı popülerlikteki rastgele bir sanatçıdan
fazla mı?»**

En kritik adım bu, çünkü başlığa bağlı değil (başlıkların %83'ü sözlükte terim taşımıyor).
Sezen Aksu'yu Duman'a bağlayan şey «aynı dil». O hâlde sorulacak soru şu: Duman–Sezen Aksu
birlikteliği, Duman ile aynı dilde ve benzer görünürlükte rastgele bir sanatçının
birlikteliğinden fazla mı?

```
C = X_libᵀ · diag(w) · X                 # |kütüphane| × A ağırlıklı birliktelik (bir kez)
s(b) = (dil(b), görünürlük_ondalığı(b))  # katman
M[a, s] = ortalama_{b' ∈ s, b' ∉ kütüphane} C[a, b']
S[a, s] = std_{b' ∈ s} C[a, b']
z[a, b] = (C[a, b] − M[a, s(b)]) / (S[a, s(b)] + ε)
lift[a, b] = (C[a, b] + 1) / (M[a, s(b)] + 1)
```

Tamamen vektörel: katman sayısı en çok ~5 dil × 10 ondalık = 50 sütun. Tek bir `np.add.at`
ya da katman başına maske ortalamasıyla saniyenin altında biter. Sonra NPMI yerine (veya
yanında) `log lift` için NPMI'daki gibi `−log p_ab` normalizasyonu ve mevcut `n/(n+k)`
kanıt büzülmesi kullanılır.

- **Dil etiketi nereden?** Sırayla: (1) MusicBrainz sanatçı `area`/`country`. Önbellekli;
  1 istek/sn ile yalnız aday havuzunun üst kısmı için birkaç saat. (2) Bedava sezgisel:
  sanatçının `liste_parca.title` başlıklarında Türkçeye özgü harf payı (ç ğ ı İ ö ş ü) ve
  Türkçe işlev sözcükleri; Japonca için Unicode kana/kanji aralıkları. (3) Enstrümantal mı?
  CLAP sıfır-atış «instrumental» olasılığı ya da Demucs vokal stem enerjisi (projede var).
  Belirsiz olan «bilinmiyor» katmanına gider. Uydurma etiket yok (K14).
- **Daha ilkeli alternatif (isteğe bağlı):** satır/sütun toplamlarını ve dil bloklarını
  koruyan karıştırmalarla (curveball algoritması, Strona ve ark. 2014 [B]) permütasyon
  p-değeri. Ama eşleştirilmiş ortalama, istatistikçi kullanıcıya hem açıklanabilir hem
  yeterli.
- **Gerekçe metnine etkisi (K7):** «Duman'la 3 listede birlikte; Duman'ın aynı dildeki benzer
  popülerlikteki sanatçılarla ortalama birlikteliği 2,6 liste, yani bağ beklenenin ancak
  1,15 katı» gibi bir cümle dürüst bir **zayıf kanıt** beyanıdır.

**(b) Bağlamsız destek kapısı (projenin sıradaki iş #2'sinin ölçülebilir hâli)**

Her listeye bağlam sınıfı verilir, çoklu etiket olabilir: `tür`, `dil/ülke`, `ruh hâli`,
`etkinlik`, `dönem`, `kişisel/karışık`, `bilinmiyor`.
- **Başlıktan:** mevcut kontrollü sözlük, buna dil/ülke («türkçe», «turkish», «yerli»,
  «türk», «deutsch», «français»), etkinlik («gym», «spor», «koşu», «study», «ders»,
  «yolculuk», «road trip», «parti», «uyku»), dönem («80s», «90'lar», «nostalji») ve kişisel
  («1. çalma listem», «favoriler», «karışık», «mix», «liked») eklenir. Uyarı: «japanese
  fusion», «city pop» gibi başlıklar dil + tür karışığıdır ve `tür` sayılmalı. Sözlük bunu
  «tür terimi varsa tür» kuralıyla çözer.
- **İçerikten (başlıksız %83 için):** liste dil homojenliği yüksek (örneğin
  ≥%80 aynı dil) ama **tür dağınıklığı** da yüksekse liste `dil` bağlamı sayılır.
  Tür dağınıklığı için iki ucuz ölçüt var: (i) Deezer albüm `genre_id`'lerinin entropisi
  (belgelenmiş uç, anahtarsız; sanatçı başına bir albüm çağrısı, ~10 bin istek, 50 istek/5 sn
  sınırıyla yaklaşık 20 dakika, önbellekli). (ii) Listedeki CLAP gömülü parçaların GS-skoru
  (Anderson 2020 tanımı: merkeze ortalama kosinüs). Bu ikincisinin kapsaması düşük.
- **Kural:** `n⁰_ab` = yalnız `tür` ve `bilinmiyor` sınıfındaki listelerde birlikte görülme.
  `n⁰_ab = 0` olan çift «yalnız bağlam kanıtı» olarak işaretlenir. Ya düşürülür ya da
  sıralamada geri itilir ve kartta açıkça yazılır. Sezen Aksu vakasındaki 4 liste
  (135 ve 250 sanatçılı iki kişisel karışım, «türkçe», «Eksibirband») bu kuralla **sıfır
  bağlamsız destek** verir.
- **482 liste küçük:** başlıkların hepsi kullanıcı tarafından yaklaşık bir saatte elle
  etiketlenebilir. Bu bir «altın küme» olur; sözlük + içerik kuralının isabeti buna karşı
  ölçülür (K19). Hem ucuz hem doğrulanabilir.

**(c) Bağlam ağırlığı (yumuşak sürüm)**

`w_l = w_boyut(l) · w_bağlam(l)`. `w_bağlam`, `tür` ve `bilinmiyor` için 1, diğerleri için
ρ ∈ {0; 0,25; 0,5}. ρ süpürülür. Not: boyut ağırlığı (eşit/log/ters) tek başına sorunu
çözmedi [P]: «Karışıklık liste BOYUTU değil DİL». Bu yüzden (c) tek başına yetmez;
(a) ve (b) ile birlikte ölçülmeli.

**(d) Sızıntıyı ölçmek: iki yeni sınama**

1. **Dil-içi gizleme sınaması (koşullu recall):** Gizlenen sanatçının sırası yalnız **aynı
   dildeki** adaylar arasında hesaplanır. Bu, «yöntem doğru Türk sanatçısını Türk
   sanatçıları arasından seçebiliyor mu» sorusunu ölçer; dil sinyalinin kendisi
   ödüllendirilmez. Mevcut recall ile yan yana raporlanır (K19 «kıyas» şartı).
2. **Sızıntı kümesi:** Kullanıcının «tutmadı» dediği ve sebebi dil/tarz uyuşmazlığı olan
   çiftlerden (Sezen Aksu–grunge gibi) küçük bir negatif küme. Ölçüt: bu çiftlerin eksen
   destesinin ilk 50'sine girme oranı. Her yöntem değişikliğinde «sızıntı oranı ↓, dil-içi
   recall ≈» beklenir.

**Öngörülebilir başarısızlık:** Türk rock ekseninde dil gerçekten tarzın parçası. Eşleştirilmiş
sıfır modeli Türk rock sanatçılarını birbirine bağlayan **tarz** bağını da zayıflatabilir.
Bu yüzden z/lift NPMI'nın yerine değil **yanına** konur (RRF'de üçüncü bir sıra ya da kapı
olarak) ve eksen bazında ölçülür. Türk rock ekseni ile grunge ekseninde farklı ρ çıkması
beklenir.

---

### 3.2 [#2] Bağımsız kanıtla çapraz onay: vokalsiz CLAP + kademeli melez

**Sorun [P]:** Melez yolda iki sinyal bağımsız değildi. Sezen Aksu'yu liste tarafı «aynı dil»
diye, CLAP tarafı da «Türkçe kadın vokal tınısı» (en yakın: Şebnem Ferah) diye getirdi.
«İki sinyal de işaret ediyor» cümlesi bu yüzden yanıltıcıydı.

**Öneri:**
1. **CLAP'ı vokalsiz karışım üzerinden hesapla.** Demucs projede zaten dört stem üretiyor
   (K12) ve adaylar da profilleniyor. `drums + bass + other` toplamı «enstrümantal karışım»
   verir. Bu karışımın CLAP gömüsü dil ve vokal tınısını büyük ölçüde dışarıda bırakır;
   aranje, enstrümantasyon, prodüksiyon ve icra kalır. Bu, kullanıcının «enstrümantal derinlik
   ve icra kalitesi» önceliğiyle de örtüşüyor. Maliyet: ek bir CLAP geçişi; Demucs çıktısı
   saklanıyorsa ucuz, saklanmıyorsa aday başına ~12 sn yeniden ayrıştırma.
   **Ölçüm:** tam karışım CLAP'ı ile vokalsiz CLAP'ı karşılaştır: LOAO, dil-içi recall,
   sızıntı oranı ve ses yolunun gerçek karar isabeti.
2. **Kademeli melez (Burke 2002 sınıflamasında «cascade») [B]:** Liste yolu aday önerir,
   ses ve icra kapısı süzer. Kapı eşiği kütüphaneden gelir (K12'deki ölçek ilkesi):
   `t_k = eksen üyelerinin kendi eksenine benzerliğinin %10'luk dilimi`. Eksenler bulanık ve
   çok modlu olabileceği için merkez yerine **eksen üyelerine en yakın 3 benzerliğin
   ortalaması** kullanılmalı.
3. **Bağımsızlık beyanı ölçülmeden kurulmaz:** Gerekçe metninde «iki bağımsız sinyal» demek
   için iki sinyalin skorları arasındaki korelasyon **dil katmanı içinde** ölçülür. Örneğin
   Türkçe adaylar arasında NPMI ile CLAP benzerliğinin Spearman ρ'su. Yüksekse cümle
   «iki sinyal» der, «bağımsız» demez.
4. RRF (k=60) zaten var [P]. Yeni bir kaynak (z/lift, vokalsiz CLAP, RP3β) eklendiğinde de
   aynı kaynaşma kullanılır; ölçek sorunu yok.

Gerekçe: van den Oord (2013) ses ile tercih arasındaki «anlamsal boşluğu» vurgular. Bu
kullanıcı için boşluğun bir kısmı vokal/dil, bir kısmı icra. İcra kısmı tam da stem'lerin
ölçtüğü şey; bu kullanıcıda ses yolunun gerçek kararlarda kazanması bununla tutarlı.

---

### 3.3 [#3] RP3β ve ProbS–HeatS rastgele yürüyüşü

**Neden:** NPMI yalnız **1. derece** birlikteliği görür: bir sanatçı, kütüphane sanatçısıyla
aynı listede değilse görünmez. Tavan (havuzda olma) bu yüzden sınırlı (liste yolunda 109/147
[P]). Rastgele yürüyüş 2. dereceden ulaşır ve popülerlik için **açık bir düğme** taşır.
Dacrema ve ark. (2019, RecSys, «Are we really making much progress?») RP3β ve ItemKNN gibi
basit grafik/komşuluk yöntemlerinin birçok sinirsel yöntemi geçtiğini gösterdi [B].

**numpy tarifi (O(nnz), 482×10.360 matriste milisaniyeler):**
```
# Yürüyüş: eksen sanatçıları → listeler → sanatçılar
m  = X @ (q / k_A)            # liste kütlesi (L)      [sanatçı→liste geçişi]
m  = w * m / k_L               # liste→sanatçı geçişi (1/k_L: ProbS'un liste normalizasyonu)
s  = X.T @ m                   # sanatçı skoru (A)
s  = s / k_A**β                # RP3β: popülerlik cezası (β=0 → P3; β≈0.5–1 → kuyruk)
# P3α: geçiş olasılıklarını α üssüne yükselt (α>1 güçlü geçişleri sivriltir)
# 2. derece (kapsama): s'yi yeni q olarak bir tur daha yürü; yalnız yeni ulaşılanları ekle
```
**ProbS–HeatS melezi (Zhou 2010) [B]:**
`W_ba = 1/(k_b^{1−λ} · k_a^{λ}) · Σ_l X_lb X_la / k_l`, skor `s_b = Σ_a W_ba q_a`.
λ=1 saf ProbS (kütle yayılımı; doğruluk, popülere eğilim), λ=0 saf HeatS (ısı iletimi; kuyruk).
Tek λ ile tanıdıklık–yenilik ekseni açıkça ayarlanır.

**Bağlantı:** `1/k_l` normalizasyonu, projede denenmiş «ters» liste ağırlığının yürüyüşteki
karşılığı. Ayrı ölçüldüğünde fark çıkmadı [P]; ama yürüyüşte `k_A^β` cezasıyla **birlikte**
çalışıyor. Bu, ölçülmemiş bir bileşim.

**Heterojen grafik:** Aynı yürüyüş kredi grafiği (sanatçı–müzisyen–sanatçı) ve ListenBrainz
benzer-sanatçı kenarlarıyla genişletilebilir: `X` yerine blok matris `[X_liste; X_kredi;
X_LB]`, her blok kendi ağırlığıyla. Böylece «sahne komşuluğu», «kredi sıçraması» ve «liste»
tek bir yürüyüşte birleşir. Kart yine yolu yazabilir (K7): en çok kütle taşıyan ara düğüm
gerekçedir («Bu sanatçıya en çok Marco Minnemann üzerinden ulaşıldı»).

**Ölçüm:** LOAO recall@50, tavan, **görünürlük medyanı** (popülerlik vekili; kütüphane medyanı
6 [P]), dil-içi recall ve sızıntı oranı. β ve λ süpürülür. K19 gereği NPMI ile kıyaslanır.

---

### 3.4 [#4] Popülerliğe ve dile duyarlı değerlendirme

Projede k=1 ile k=4 arasındaki karar zaten bir popülerlik–erişim ödünleşimiydi ve elle
verildi [P]. Bunu resmîleştirmek ileride her kararı kolaylaştırır:
1. **Popülerlik-tabakalı recall (Steck 2011) [B]:**
   `R_γ = Σ_{isabet} pop(b)^{−γ} / Σ_{gizlenen} pop(b)^{−γ}`, γ ∈ {0; 0,5; 1}. γ=0 bugünkü
   recall. γ>0 kuyruktaki isabeti ödüllendirir. k=1/k=4 kararı tek bir tabloda görünür olur.
2. **Popülerlik dağılımı karşılaştırması (Lesota 2021):** destenin ilk 50'sinin görünürlük
   dağılımı ile kütüphanenin dağılımı arasında KL/JS ve medyan farkı. Abdollahpouri'nin
   ΔGAP'ı (grup ortalama popülerlik farkı) da raporlanabilir.
3. **Dil-içi recall** (§3.1d) ve **sızıntı oranı**.
4. **Yenilik:** ortalama öz-bilgi `−log₂ p(b)`, p(b) liste görünürlüğünden (Zhou 2010) [B].
5. **Gerçek kararlarla ayrışma:** her kaynak için Wilson aralıklı zevk isabeti ve keşif oranı
   (projede var [P]), artı **AUC(skor → beğeni)** kaynak içinde. AUC 0,30 gibi bir değer
   «skor tersine çalışıyor» der ve en güçlü uyarı sinyalidir.

Bu beş sayı K19'daki «tavan, iki payda, kıyas» şartına eklenir. Tek sayıya göre karar
verilmez.

---

### 3.5 [#5] Çalma listesi havuzunu büyütmek: tür ve sahne sorguları

482 liste, MPD'nin (1M) 2000'de biri. Zamani (2019) performansın tohum ve veri ölçeğiyle
arttığını gösteriyor. Havuz şu an **sanatçı adıyla** aranıyor (`tohum_sanatci`). Bu iki
yanlılık doğuruyor: (i) aramada başa gelen listeler adı taşıyan ya da sanatçının dil/ülke
listeleri oluyor; (ii) tohum sanatçının P(a)'sı şişiyor.

**Öneri:** Deezer `search/playlist` belgelenmiş ucuyla **tür/sahne sorguları:** «jazz
fusion», «japanese fusion», «city pop instrumental», «technical death metal», «djent»,
«progressive metal», «anadolu rock», «türkçe rock 90», «guitar virtuoso», «shred»,
«boom bap», «türkçe rap». Sorguları eksenlerin ayırt edici MusicBrainz etiketlerinden
(`tarz_adi.py` bunları zaten çıkarıyor) otomatik türetmek K2/K18 ile uyumlu. Hedef: 2–5 bin
liste. Mevcut süzgeçler (tek sanatçı payı > 0,5 olanı at, ≥8 parça) aynen uygulanır.
**Maliyet:** API ücretsiz, rate-limit içinde birkaç saat, önbellekli (K5). Ölçüm, tavan
artışı ve dil-içi recall üzerinden.

**Uyarı:** tür sorgusuyla gelen listeler de bağlam taşır («workout metal»). §3.1'deki
bağlam sınıflaması bu listelere de uygulanır. Kaynak sütunu (`kaynak = 'tür_sorgusu'`)
saklanır ki iki havuzun etkisi ayrı ölçülebilsin (K11'deki «kaynaklar karışmamalı» ilkesi).

---

### 3.6 [#6] Bandit: daha az kararla daha çok öğrenmek

Projede Beta(1+beğendi, 1+tutmadı) Thompson var [P]. Üç küçük iyileştirme:
1. **Havuzlanmış önsel (≤5 kullanıcı):** Kaynak s için tüm kullanıcıların kararlarından
   ortalama m_s ve yoğunlaşma κ (moment yöntemi ya da sabit κ≈10) hesaplanır. Kullanıcı u'nun
   önseli `Beta(κ·m_s, κ·(1−m_s))` olur. Yeni kullanıcı ilk desteden itibaren ortak bilgiyle
   başlar (Briand 2021'in yarı-kişisel soğuk başlangıç fikrinin bandit hâli). Kişisel veri
   sızmaz: yalnız kaynak düzeyinde toplam sayılar paylaşılır. K20'deki önbellek kuralına
   dikkat edilmeli: anahtar kullanıcı kimliğini içermeli ya da yalnız toplam tutulmalı.
2. **Ödülü kullanıcının hedefiyle tanımla:** Hedef «beğendiğim VE bilmediğim». İki Beta
   kullanılır: `θ_yeni ~ Beta(1+yeni, 1+biliyordum)` ve
   `θ_beğeni|yeni ~ Beta(1+beğendi, 1+tutmadı)`. Örneklenen `θ_yeni · θ_beğeni|yeni`
   sıralamaya girer. Bugünkü iki oran (zevk isabeti ve keşif oranı) böylece tek bir karar
   kuralında birleşir.
3. **Takım-seçmeli harmanlama (Radlinski 2008; Chapelle 2012) [B]:** İki sıralayıcıyı
   (örneğin NPMI ile z/lift, ya da tam karışım CLAP ile vokalsiz CLAP) aynı destede
   karşılaştırır. Her çift yuvada yazı-tura ile hangi sıralayıcının önce seçeceği belirlenir,
   her biri kendi en iyi gösterilmemiş sanatçısını koyar ve karar o «takıma» yazılır.
   Birkaç düzine kararla işaret testi (binom). Ayrı destelerle A/B'den çok daha az karar
   ister. Tohumlanır, tekrarlanabilir (K2).
4. (İsteğe bağlı) **Açıklama türü de kolun parçası (McInerney 2018):** Aynı aday «kredi»,
   «kalabalık» ya da «ses» gerekçesiyle gösterildiğinde beğeni değişiyor mu? n küçük olduğu
   için şimdilik yalnız kaydedilmeli (hangi gerekçe türü gösterildi), sınanmamalı.

---

### 3.7 [#7] Küçük ikinci aşama yeniden sıralayıcı (vl6 dersi, küçük n'ye uyarlanmış)

RecSys 2018'in ana dersi şuydu: geniş aday, sonra **öğrenilmiş** yeniden sıralama. Projede
kaynak içi sıralama ölçülmüş skorla, kaynaklar arası pay Thompson ile yapılıyor. Ama
özniteliklerin birleşimi gerçek tercihten öğrenilmiyor.

- **Öznitelikler (≤8, yorumlanabilir):** max NPMI; bağlamsız destek `n⁰`; z/lift (§3.1a);
  RP3β skoru; vokalsiz CLAP'ın eksene k-NN benzerliği; stem/icra eşleşmesi; kredi yolu
  uzunluğu/sayısı; LB skoru; log görünürlük; dil eşleşmesi göstergesi.
- **Model:** L2 düzenlemeli lojistik regresyon, numpy'de Newton–IRLS (10–20 iterasyon).
  Bayesçi sürümde Laplace yaklaşımı `Σ = (XᵀWX + λI)⁻¹` alınır ve Thompson ağırlık
  vektöründen örneklenir (Chapelle & Li 2011) [B]. Böylece keşif ve yeniden sıralama tek
  modelde birleşir.
- **Eğitim verisi:** (i) gerçek kararlar: beğendi=1, tutmadı=0; «biliyordum» ya ayrı bir
  modelde ya da dışarıda. (ii) LOAO sözde-etiketleri: gizlenen sanatçı=1, aynı eksen
  havuzunda ilk N'deki diğerleri=0. (ii) zayıf ve popülerliğe yanlı olduğu için örnek
  ağırlığı küçük tutulur (örneğin 0,2) ya da yalnız önsel (prior mean) olarak kullanılır.
- **Doğrulama:** sanatçıya göre gruplu çapraz doğrulama. Katsayılar bootstrap güven
  aralıklarıyla raporlanır; kullanıcı istatistikçi, katsayı tablosu kendi başına bir bulgu
  (örneğin «gerçek kararlarda log görünürlüğün katsayısı negatif»).
- **Ne zaman:** n≈150 sınırda. Öznitelik sayısı küçük ve düzenleme güçlü olmalı. Asıl
  değer, kaynak başına ≥30 karar hedefine ulaşıldığında (sıradaki iş #1) çıkar.
- **K7 uyumu:** Lojistik katsayı × öznitelik katkıları, kartta «bu öneride en çok ağırlık
  taşıyan kanıt» satırını sayıyla doldurur. Uydurma yok.

---

### 3.8 [#8] EASE ve PPMI-SVD: kapalı formlu, deterministik alternatifler

1. **EASE (Steck 2019, WWW, «Embarrassingly shallow autoencoders for sparse data») [B]:**
   ```
   A' = en az 2 listede görülen sanatçılar (~birkaç bin)
   G  = X_{A'}ᵀ diag(w) X_{A'} + λI
   P  = inv(G)
   B  = −P / diag(P)[None, :] ;  diag(B) = 0
   s  = q_{A'} @ B
   ```
   3 bin sanatçıda `inv` ~1 sn. Not: L=482 ≪ A' olduğu için G'nin rankı ≤ 482. λ baskın
   olacak ve model, düzenlenmiş bir birliktelik gibi davranacak. Kazanç belirsiz ama ölçmesi
   ucuz. Havuz büyürse (§3.5) EASE'in değeri artar.
2. **PPMI-SVD sanatçı gömüsü (Levy & Goldberg 2014, «Neural word embedding as implicit matrix
   factorization»; Levy, Goldberg, Dagan 2015, TACL) [B]:** word2vec (SGNS) örtük olarak
   kaydırılmış PMI matrisini ayrıştırır. Anderson 2020'nin Spotify gömüsü de liste üzerinde
   word2vec. Tarif: bağlam dağılımını yumuşat (`p_α(b) ∝ c_b^{0,75}`), `M = max(PMI, 0)`
   (A'×A'), kesik SVD (k=32–64), `E = U_k Σ_k^{1/2}`, kosinüs. Kazanç: **2. derece
   benzerlik** (aynı listede hiç görülmemiş ama aynı komşulara sahip sanatçılar) ve §3.9 için
   hedef uzay. GS-skoru (§3.10) bu uzayda tanımlanabilir.

---

### 3.9 [#9] Sesten kalabalığa köprü

1. **Doğrusal eşleme (van den Oord 2013'ün eğitimsiz, kapalı formlu hâli):**
   `W = (FᵀF + λI)⁻¹ FᵀZ`. F: hem CLAP gömüsü hem PPMI-SVD gömüsü olan sanatçıların
   (sanatçı düzeyinde ortalanmış, hubness düzeltilmiş) CLAP matrisi; Z: PPMI-SVD gömüsü.
   Listede hiç görünmeyen adayın kalabalık konumu `ẑ = f·W` ile tahmin edilir. LOAO'da
   gizlenen sanatçı yalnız sesiyle konumlandırılıp bulunabiliyor mu diye bakılır. Bu,
   «yalnız sesle erişilebilen 14 sanatçı» [P] için kalabalık açıklaması da üretir.
2. **Grafik üzerinde ses yumuşatma (Korzeniowski 2021'in eğitimsiz analoğu; SGC, Wu ve ark.
   2019; APPNP, Klicpera ve ark. 2019) [B]:**
   ```
   S = NPMI⁺ (bağlamsız) k-NN grafiği, Â = D^{-1/2}(S + I)D^{-1/2}
   H = Σ_{t=0..K} α(1−α)^t Â^t F      # kişiselleştirilmiş PageRank yayılımı, K=2–3
   ```
   Sonuç, sesi kalabalık komşularıyla harmanlanmış bir sanatçı gömüsü. Korzeniowski'nin
   bulgusu, grafik ile içeriğin birleşiminin ikisinden de iyi olduğu ve az bağlantılı
   sanatçıların içerikten yararlandığı yönünde (connection dropout). Dikkat: grafik
   bağlamsız (§3.1b) kurulmalı, yoksa dil sızıntısı sese de bulaşır.
3. **Asimetri (Salha-Galvan 2021):** Benzerlik okları popülere akar. LB benzer-sanatçı ve
   liste birlikteliği yönlü kullanılmalı: «a'yı dinleyenin b'yi dinlemesi» ≠ tersi.
   Koşullu olasılık `P(b|a)` yerine `P(a|b)` («b'nin listelerinde a ne sıklıkla var»)
   kuyruğa doğru bakar ve keşif için daha uygundur [B: kütle yorumu].

---

### 3.10 [#10] Çeşitlilik, kalibrasyon ve tanı

1. **MMR (desteye, eksen içinde):**
   `seç = argmax_b [ λ·ilgi(b) − (1−λ)·max_{s∈Seçilen} sim(b, s) ]`. sim, vokalsiz CLAP ve
   PPMI-SVD kosinüslerinin ortalaması. Sanatçı düzeyinde tekilleştirme zaten var [P]. MMR,
   aynı «ses ailesinden» beş sanatçının arka arkaya gelmesini önler. K4'teki max-min
   çeşitlilik fikrinin öneri tarafındaki karşılığı.
2. **DPP (Chen 2018) [B]:** 50'lik deste için artımlı Cholesky ile açgözlü MAP numpy'de
   basit. MMR'den daha ilkeli ama kazancı küçük olabilir; ancak MMR yetmezse.
3. **Kalibre popülerlik (Abdollahpouri 2021) [B]:** Görünürlük ondalıklarıyla baş/orta/kuyruk
   kovaları kurulur. Eksen kütüphanesinin kova dağılımı p, destenin dağılımı q olur.
   Açgözlü seçimde `(1−λ)·ilgi − λ·JS(p, q(S∪{b}))`. Eksen içinde dil kalibrasyonu da aynı
   kalıpla yapılır (§2.7).
4. **GS-skoru tanısı (Anderson 2020):** Kütüphanenin ve destenin GS-skoru aynı gömüde
   (PPMI-SVD ya da vokalsiz CLAP) hesaplanır. Deste kütüphaneden belirgin biçimde daha
   odaklıysa (yüksek GS) sistem kullanıcıyı daraltıyordur. Bu Spotify'ın ölçtüğü etkinin
   yerel karşılığı. «Sen» sayfasında K13 uyumlu bir gösterge olabilir: norm uydurmadan,
   yalnız kendi kütüphanesine göre.

---

### 3.11 Bekleyebilecek iş: ses omurgası

- Literatür çelişkili: 2024'te MusiCNN en iyiydi; 2026'da MuQ/MuQ-MuLan en iyi;
  eğitimsiz benzerlikte CLAP-Music en iyi. Ve **MIR benchmark'ı öneri başarısını öngörmüyor**
  (Tamm & Aljanaki 2026).
- Projenin kullanımı eğitimsiz benzerlik + hubness düzeltmesi; bu, CLAP'ın güçlü olduğu
  senaryo. Önce **vokalsiz CLAP** (§3.2) denenmeli: aynı model, farklı girdi, ucuz.
- MuQ-MuLan denemesi gerekirse: kütüphane + ~3 bin aday klibi, M1'de MPS ile birkaç saat.
  Ağırlık lisansı denetlenmeli. Karar yalnız LOAO + dil-içi recall + gerçek kararlarla
  (harmanlama, §3.6) verilir.

---

### 3.12 Yapılmaması gerekenler (literatür ve proje ölçümünden)

- **Ham birliktelikle sıralamak:** popülere düşer (Van Halen ↔ Madonna [P]; Zhou 2010).
- **Köprü sayısıyla «uzak» önermek:** ana akıma düşer (Coldplay metal kümesinde [P]); Anderson
  2020'deki genelci bulgusuyla tutarlı.
- **Başlığı ana sinyal yapmak:** RecSys 2018'de kimse başlıktan değer çıkaramadı (Zamani 2019);
  projede başlıkların yalnız %17'si sözlükte. Başlık bağlam ayıklayıcı olarak kullanılmalı.
- **Benchmark'a göre gömü seçmek:** MIR başarısı öneri başarısını öngörmüyor (Tamm &
  Aljanaki 2026).
- **Bağımsızlık ölçülmeden «iki bağımsız sinyal» demek** (Afchar 2022'nin sadakat ilkesi;
  Sezen Aksu vakası [P]).
- **LOAO'yu tek ölçüt yapmak:** MNAR ve dil karışıklığı yüzünden gerçek tercihle ters
  düşebiliyor (Steck 2011; proje AUC 0,30 [P]).

---

### 3.13 Önerilen sıra (uygulama planı, her adım K19 ile ölçülür)

1. Ölçüm altyapısı: dil etiketi (sezgisel + MB), dil-içi recall, sızıntı kümesi,
   popülerlik-tabakalı recall (§3.4). **Önce ölçüm, sonra karar.**
2. Eşleştirilmiş sıfır modeli + bağlamsız destek kapısı (§3.1). 482 başlığın elle
   etiketlenmesi kullanıcıya önerilir (yaklaşık bir saat; altın küme).
3. Vokalsiz CLAP + kademeli kapı (§3.2), harmanlamayla gerçek kararlarda sınanır (§3.6.3).
4. RP3β / ProbS–HeatS (§3.3) ve EASE / PPMI-SVD (§3.8) LOAO'da NPMI ile kıyaslanır.
5. Havuz genişletme (§3.5), tavan artışı ölçülür.
6. Bandit önseli + «beğendi ∧ yeni» ödülü (§3.6).
7. Kaynak başına ≥30 kararda ikinci aşama lojistik (§3.7).
8. Köprü ve çeşitlilik (§3.9, §3.10).

---

## 4. Kaynakça

Erişim: 2026-10-20. **[B]** = bellekten, bu oturumda doğrulanamadı.

**Uzun kuyruk ve anketler**
- Celma, Ò. (2008). *Music Recommendation and Discovery in the Long Tail*. Doktora tezi,
  Universitat Pompeu Fabra. https://mtg.upf.edu/node/1242
- Celma, Ò. (2010). *Music Recommendation and Discovery: The Long Tail, Long Fail, and Long
  Play in the Digital Music Space*. Springer. https://link.springer.com/doi/10.1007/978-3-642-13287-2
- Schedl, M., Zamani, H., Chen, C.-W., Deldjoo, Y., Elahi, M. (2018). Current challenges and
  visions in music recommender systems research. *IJMIR* 7(2):95–116.
  https://arxiv.org/abs/1710.03208
- Schedl, M., Knees, P., McFee, B., Bogdanov, D. (2022). Music Recommendation Systems:
  Techniques, Use Cases, and Challenges. *Recommender Systems Handbook* (3. baskı), 927–971.
  https://doi.org/10.1007/978-1-0716-2197-4_24
- Deldjoo, Y., Schedl, M., Knees, P. (2024; ön baskı 2021). Content-driven music
  recommendation: Evolution, state of the art, and challenges. *Computer Science Review* 51.
  https://arxiv.org/abs/2107.11803
- Moscati, M., Parada-Cabaleiro, E., Deldjoo, Y., Zangerle, E., Schedl, M. (2022).
  Music4All-Onion. CIKM 2022. https://hcai.test.cp.jku.at/publications/2022_onion/

**RecSys Challenge 2018 / çalma listesi sürdürme**
- Zamani, H., Schedl, M., Lamere, P., Chen, C.-W. (2019). An analysis of approaches taken in
  the ACM RecSys Challenge 2018 for automatic music playlist continuation. *ACM TIST* 10(5):57.
  https://arxiv.org/abs/1810.01520 · https://dl.acm.org/doi/10.1145/3344257
- Volkovs, M., Rai, H., Cheng, Z., Wu, G., Lu, Y., Sanner, S. (2018). Two-stage model for
  automatic playlist continuation at scale. RecSys Challenge 2018.
  https://www.cs.toronto.edu/~mvolkovs/recsys2018_challenge.pdf ·
  https://dl.acm.org/doi/abs/10.1145/3267471.3267480
- Avito takımı (2018). A hybrid two-stage recommender system for automatic playlist
  continuation. RecSys Challenge 2018. https://doi.org/10.1145/3267471.3267488
- Creamy Fireflies (2018/2020). Artist-driven layering and user's behaviour impact on
  recommendations in a playlist continuation scenario. https://arxiv.org/abs/2010.06233
- Bonnin, G., Jannach, D. (2014). Automated generation of music playlists: Survey and
  experiments. *ACM CSUR* 47(2):26. [B: içerik]
- Jannach, D., Kamehkhosh, I., Bonnin, G. (2016). UMAP 2016 (sonraki parça önerisi; CAGH,
  kNN temel çizgileri). https://web-ainf.aau.at/pub/jannach/files/Conference_UMAP2016.pdf

**İçerik / ses gömüleri**
- van den Oord, A., Dieleman, S., Schrauwen, B. (2013). Deep content-based music
  recommendation. NeurIPS 26. https://papers.nips.cc/paper/5004-deep-content-based-music-recommendation
- Pons, J., Serra, X. (2019). musicnn: Pre-trained convolutional neural networks for music
  audio tagging. https://arxiv.org/abs/1909.06654
- Li, Y. ve ark. (2024). MERT: Acoustic music understanding model with large-scale
  self-supervised training. ICLR 2024. https://iclr.cc/media/iclr-2024/Slides/17510.pdf
- Yuan, R. ve ark. (2023). MARBLE: Music audio representation benchmark for universal
  evaluation. https://arxiv.org/abs/2306.10548
- Zhu, H. ve ark. (2025). MuQ: Self-supervised music representation learning with Mel
  residual vector quantization. https://arxiv.org/abs/2501.01108
- Tamm, Y.-M., Aljanaki, A. (2024). Comparative analysis of pretrained audio representations
  in music recommender systems. RecSys 2024. https://arxiv.org/abs/2409.08987
- Tamm, Y.-M., Aljanaki, A. (2026). Adopting state-of-the-art pretrained audio
  representations for music recommender systems. ACM. https://doi.org/10.1145/3808222 ·
  https://arxiv.org/abs/2604.23077
- (2026). From classification to recommendation: Empirical analysis of audio embedding
  models application for content-based music recommendation. https://arxiv.org/abs/2608.06928
- (2024). CLAP gömüleriyle grafik tabanlı sanatçı ilişkisi tahmini (RecSys 2024 çalıştayı).
  https://arxiv.org/abs/2409.09026

**Popülerlik yanlılığı ve kalibrasyon**
- Abdollahpouri, H., Mansoury, M., Burke, R., Mobasher, B. (2019). The unfairness of
  popularity bias in recommendation. https://arxiv.org/abs/1907.13286
- Abdollahpouri, H. ve ark. (2019/2020). The connection between popularity bias,
  calibration, and fairness in recommendation. https://arxiv.org/abs/1910.05755
- Abdollahpouri, H. ve ark. (2020). Addressing the multistakeholder impact of popularity
  bias in recommendation through calibration. https://arxiv.org/abs/2007.12230
- Abdollahpouri, H. ve ark. (2021). User-centered evaluation of popularity bias in
  recommender systems. UMAP 2021. [B]
- Kowald, D., Schedl, M., Lex, E. (2020). The unfairness of popularity bias in music
  recommendation: A reproducibility study. ECIR 2020. https://arxiv.org/abs/1912.04696
- Lesota, O. ve ark. (2021). Analyzing item popularity bias of music recommender systems:
  Are different genders equally affected? RecSys 2021. https://arxiv.org/abs/2108.06973
- Lesota, O., Parada-Cabaleiro, E., Brandl, S., Lex, E., Rekabsaz, N., Schedl, M. (2022).
  Traces of globalization in online music consumption patterns and results of
  recommendation algorithms. ISMIR 2022. https://ismir2022program.ismir.net/poster_165.html ·
  https://zenodo.org/records/7316652
- Steck, H. (2018). Calibrated recommendations. RecSys 2018.
  https://www.slideshare.net/slideshow/calibrated-recommendations/118205343
- Steck, H. (2011). Item popularity and recommendation accuracy. RecSys 2011. [B]
- Steck, H. (2010). Training and testing of recommender systems on data missing not at
  random. KDD 2010. [B]
- Steck, H. (2019). Embarrassingly shallow autoencoders for sparse data. WWW 2019. [B]

**Çeşitlilik / yenilik / keşif**
- Anderson, A., Maystre, L., Anderson, I., Mehrotra, R., Lalmas, M. (2020). Algorithmic
  effects on the diversity of consumption on Spotify. WWW 2020.
  https://www.cs.utoronto.ca/~ashton/pubs/alg-effects-spotify-www2020.pdf
- Kaminskas, M., Bridge, D. (2016). Diversity, serendipity, novelty, and coverage. *ACM TiiS*
  7(1). [B: künye]
- Kaminskas, M., Bridge, D. (2014). Measuring surprise in recommender systems. RecSys 2014
  çalıştayı.
- Zhou, T., Kuscsik, Z., Liu, J.-G., Medo, M., Wakeling, J. R., Zhang, Y.-C. (2010). Solving
  the apparent diversity-accuracy dilemma of recommender systems. *PNAS* 107(10):4511–4515. [B]
- Carbonell, J., Goldstein, J. (1998). The use of MMR, diversity-based reranking. SIGIR. [B]
- Chen, L., Zhang, G., Zhou, H. (2018). Fast greedy MAP inference for determinantal point
  process to improve recommendation diversity. NeurIPS. [B]
- Christoffel, F., Paudel, B., Newell, C., Bernstein, A. (2015). Blockbusters and wallflowers:
  Accurate, diverse, and scalable recommendations with random walks. RecSys 2015. [B]
- Paudel, B., Christoffel, F., Newell, C., Bernstein, A. (2017). Updatable, accurate, diverse,
  and scalable recommendations for interactive applications. *ACM TiiS*. [B]
- Ferrari Dacrema, M., Cremonesi, P., Jannach, D. (2019). Are we really making much progress?
  A worrying analysis of recent neural recommendation approaches. RecSys 2019. [B]

**Bandit, harmanlama, açıklama**
- McInerney, J., Lacker, B., Hansen, S., Higley, K., Bouchard, H., Gruson, A., Mehrotra, R.
  (2018). Explore, exploit, and explain: Personalizing explainable recommendations with
  bandits. RecSys 2018, 31–39. https://patents.google.com/patent/US11301513 (ilgili patent)
- Chapelle, O., Li, L. (2011). An empirical evaluation of Thompson sampling. NeurIPS. [B]
- Radlinski, F., Kurup, M., Joachims, T. (2008). How does clickthrough data reflect retrieval
  quality? CIKM. [B]
- Chapelle, O., Joachims, T., Radlinski, F., Yue, Y. (2012). Large-scale validation and
  analysis of interleaved search evaluation. *ACM TOIS*. [B]
- Afchar, D., Melchiorre, A. B., Schedl, M., Hennequin, R., Epure, E. V., Moussallam, M.
  (2022). Explainability in music recommender systems. *AI Magazine* 43(2):190–208.
  https://ojs.aaai.org/index.php/aimagazine/article/view/21743
- Millecamp, M., Htun, N. N., Conati, C., Verbert, K. (2019). To explain or not to explain:
  The effects of personal characteristics when explaining music recommendations. IUI 2019.
  https://www.cs.ubc.ca/~conati/522/532b-2019/papers/MillecampIUI2019.pdf
- Burke, R. (2002). Hybrid recommender systems: Survey and experiments. *UMUAI*. [B]

**Grafikler, bilgi grafikleri, Deezer**
- Korzeniowski, F., Oramas, S., Gouyon, F. (2021). Artist similarity with graph neural
  networks. ISMIR 2021 (Pandora). https://arxiv.org/abs/2107.14541 · TISMIR 2022 genişletmesi:
  https://doaj.org/article/3d00d5df750046eaad6075feef48b784
- Salha-Galvan, G., Hennequin, R., Chapus, B., Tran, V.-A., Vazirgiannis, M. (2021). Cold
  start similar artists ranking with gravity-inspired graph autoencoders. RecSys 2021.
  https://arxiv.org/abs/2108.01053
- Briand, L., Salha-Galvan, G., Bendada, W., Morlon, M., Tran, V.-A. (2021). A
  semi-personalized system for user cold start recommendation on music streaming apps.
  KDD 2021. https://arxiv.org/abs/2106.03819
- Oramas, S., Ostuni, V. C., Di Noia, T., Serra, X., Di Sciascio, E. (2016). Sound and music
  recommendation with knowledge graphs. *ACM TIST* 8(2). https://mtg.upf.edu/biblio/author/905
- Wu, F. ve ark. (2019). Simplifying graph convolutional networks (SGC). ICML. [B]
- Klicpera, J., Bojchevski, A., Günnemann, S. (2019). Predict then propagate (APPNP).
  ICLR. [B]
- Levy, O., Goldberg, Y. (2014). Neural word embedding as implicit matrix factorization.
  NeurIPS. Levy, O., Goldberg, Y., Dagan, I. (2015). Improving distributional similarity
  with lessons learned from word embeddings. TACL. [B]
- Strona, G. ve ark. (2014). A fast and unbiased procedure to randomize ecological binary
  matrices with fixed row and column totals (curveball). *Nature Communications*. [B]

**Bağlam / başlıklar**
- Pichl, M., Zangerle, E., Specht, G. (2015). Towards a context-aware music recommendation
  approach: What is hidden in the playlist name? ICDMW. [B: künye] ·
  https://dbis-informatik.uibk.ac.at/node/465
- Pichl, M., Zangerle, E. (2021). User models for multi-context-aware music recommendation.
  *MTAP*. https://dbis.uibk.ac.at/sites/default/files/2021-08/mtap_zangerle_2021.pdf
- Hao, Y., Downie, J. S. (2020). Using latent semantics of playlist titles and descriptions
  to enhance music recommendations. NLP4MusA. https://aclanthology.org/2020.nlp4musa-1.4/
- Chung ve ark. (2017). ISMIR 2017 (çalma listesi başlıkları ve şarkı birlikteliği).
  https://archives.ismir.net/ismir2017/paper/000047.pdf [B: URL'nin bu makaleye ait olduğu doğrulanmadı]

**LLM dönemi (hepsi [B])**
- Palumbo, E. ve ark. (2025). Text2Tracks: Prompt-based music recommendation via generative
  retrieval. arXiv 2503.24193. [B]
- Doh, S. ve ark. (2025). TalkPlay: Multimodal music recommendation with large language
  models. arXiv 2502.13713. [B]
- Chen, L., Pu, P. (2012). Critiquing-based recommenders: Survey and emerging trends.
  *UMUAI*. [B]
