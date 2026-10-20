# Öneri algoritmaları: ilk makaleden 2026'ya ve bizim kurgumuza uygulanışı

Araştırma notu 1 — 2026-10-20. Kapsam: işbirlikçi filtrelemenin (CF) ana aileleri, her birinin
fikri, formülü, kazandığı veri rejimi, maliyeti ve önemli hiperparametreleri; ardından bunların
**482 çalma listesi × ~10.360 sanatçı** ve **eksen başına ağırlıklı kütüphane sanatçısı kümesi**
kurgusuna uygulanması.

---

## 0. Yöntem notu (okumadan önce)

- **Kaynak erişimi.** 30 web araması yapıldı (başarılı). WebFetch bu oturumda hiçbir alan adını
  çözemedi (DNS hatası), arXiv'e doğrudan `curl` da ajan vekili tarafından reddedildi. Bu yüzden
  makalelerin **tam metni okunamadı**. Doğrulama arama sonuç özetleri (özet, yayın yeri, temel
  bulgu) düzeyinde. Oturumun ortak arama bütçesi (200) de sonunda doldu. Pixie, Konstas ve
  Jeunen gibi birkaç kaynak bu yüzden aranamadı.
- **İşaretleme.** **†** işaretli her iddia bu oturumda birincil kaynaktan doğrulanamadı; önceki
  bilgime dayanıyor. Bunları uygulamadan önce makalenin kendisinden teyit edin. İşaretsiz
  iddialar en az bir arama özetiyle doğrulandı.
- **Depo bağlamı.** Öneriler `python/discover/calma_listesi.py`, `python/degerlendirme.py` ve
  `python/discover/adaylar.py` okunarak yazıldı. Koda dokunulmadı.

---

## 1. Yönetici özeti: sıralı öneriler

1. **Algoritma kıyasından önce ölçümü düzeltin (hasat sızıntısı).** `calma_listesi.tohum_sanatci`
   her listenin hangi kütüphane sanatçısı aranırken bulunduğunu tutuyor. Leave-one-artist-out
   (LOAO) bir sanatçıyı gizlerken **onun adıyla bulunmuş listeleri tutuyor**. Gerçek kullanımda
   tanımadığınız bir sanatçı için hiç arama yapılmaz. Bu yüzden tavan (132/147) ve recall@50 ≈
   0,15 şişmiş olabilir. Şişme her yöntemde eşit de değildir: popüler/yüksek dereceli adayı seven
   yöntemler daha çok kazanır. Ayrıntı: §6.1.
2. **NPMI + MAX yerine RP3β / genelleştirilmiş ItemKNN ailesi.** Matematik olarak RP3β ikili
   veride şuna indirgeniyor:
   `W_ij = Σ_p x_pi x_pj · n_p^(−α) / (d_i^α · d_j^β)`. Projenin elle denediği her düğme bu tek
   ailenin noktaları: liste ağırlığı (eşit/log/ters → α), aday popülerlik cezası (PMI'da örtük
   b=1 → β) ve tohum normalizasyonu. Tohumlar arası birleştirmede MAX yerine üyelik ağırlıklı
   **toplam** önerilir, Aiolli'nin yerellik üssü q ile (q→∞ MAX'a yaklaşır). Maliyet milisaniye,
   gerekçesi şablona (K7) doğrudan dökülüyor. Bkz. §5.2.
3. **EASE, Woodbury özdeşliğiyle.** Kullanıcı sayısı m=482 ≪ n=10.360 olduğu için
   `(XᵀX+λI)⁻¹` 10k×10k ters almadan, 482×482 ters ile hesaplanır. EASE'in kapalı formu böylece
   milisaniyelik bir iş olur. Hem güçlü bir kıyas çizgisi verir, hem de büyük listelerin çift
   sayımını "açıklayıp giderme" yeteneği var. Bkz. §5.3.
4. **Heterojen grafikte kişiselleştirilmiş PageRank (RWR).** Düğümler sanatçı, liste ve müzisyen
   (krediler). Kenarlar ListenBrainz ve CLAP karşılıklı-kNN. Yeniden başlama vektörü eksen
   üyelikleri, sonunda derece düzeltmesi (β). RRF'nin yerine tek, ayrıştırılabilir bir skor
   verebilir. Ancak kıyas ölçülerek yapılmalı. Bkz. §5.4.
5. **İçeriği (CLAP) ve yan bilgiyi (krediler) aynı makineye sokun.** Seçenekler: CLAP
   komşuluklarını ve müzisyen kadrolarını "sözde liste" satırları olarak X'e eklemek
   (collective / side-information EASE ve kNN), ya da CLAP'tan CF benzerliğine kapalı formlu
   ridge eşlemesi (CFeCBF benzeri) kurmak. İkincisi listelerde hiç geçmeyen soğuk adaylar için.
   Bkz. §5.5.
6. **Füzyon.** RRF (k=60) sağlam bir varsayılan. Ağırlıklar ayarlama yarısında öğrenilmeli,
   sınama yarısında raporlanmalı. Bkz. §5.6.
7. **Yatırım yapılmayacaklar.** iALS/BPR/SLIM (veri rejimi), NCF, GNN, ardışık modeller,
   two-tower, difüzyon ve LLM. Gerekçe: K2, veri boyutu ve 2019–2026 tekrarlanabilirlik
   çalışmaları. Bu çalışmalar basit komşuluk/grafik/doğrusal modellerin bu yöntemleri
   defalarca geçtiğini gösteriyor. İstisna: GF-CF eğitimsiz ve ucuz bir ek kıyas çizgisi
   olarak denenebilir.

---

## 2. Kurgumuzun biçimsel tanımı

Gösterim (bütün raporda):

- `X ∈ {0,1}^{m×n}`: m = 482 liste (CF'nin "kullanıcısı"), n ≈ 10.360 sanatçı (CF'nin "öğesi").
  `x_pi = 1` ⇔ i sanatçısı p listesinde.
- `d_i = Σ_p x_pi`: sanatçının liste görünürlüğü (öğe derecesi). `n_p = Σ_i x_pi`: liste boyu
  (kullanıcı derecesi).
- `c_ij = Σ_p w_p x_pi x_pj`: (ağırlıklı) birliktelik. `w_p` liste ağırlığı.
- `q^(k) ∈ ℝ^n_{≥0}`: k eksenine ait sorgu vektörü. Bugün keskin küme
  (`degerlendirme.eksen_haritasi`). Önerilen hâli `q_i^(k) = Σ_{a ∈ albüm(i)} u_ak^τ`. Bu,
  K3'ün "üyelik dereceleri öneri ağırlığıdır" sözünü tutar. τ ∈ {1, 2, 3} keskinleştirme,
  ya da `u_ak ≥ 1/c + δ` eşiği. Keskin atamanın kaçındığı "her albüm her eksene biraz girer"
  sorunu bununla kontrol altına alınır.
- Görev: `{j : q_j = 0, j ∉ kütüphane}` üzerinde sıralama.

Bu, literatürde **yeni kullanıcı katlamalı (fold-in) öğe tabanlı top-N önerisi** ya da
**tohum kümesinden çalma listesi tamamlama** problemidir (RecSys Challenge 2018'in görevi).
Rejimin üç ayırt edici özelliği her şeyi belirliyor:

1. **m ≪ n.** 482 satır, 10k sütun. Gram matrisi `G = XᵀX`'in rankı ≤ 482. Gizil faktör
   modellerinin öğrenebileceği yapı çok sınırlı ve sanatçıların çoğunun derecesi 1–2 (uzun
   kuyruk).
2. **Tek gerçek kullanıcı, ağırlıklı tohum kümesi.** "Kullanıcı-kullanıcı" benzerliği yok.
   Doğal aile, kullanıcıdan bağımsız (user-free) öğe-öğe modelleri: ItemKNN, P3α/RP3β, EASE,
   SLIM, GF-CF. Bunlar yeni bir sorgu vektörünü yeniden eğitim olmadan puanlar (`s = qW`).
3. **Kartopu örneklemi.** Listeler kütüphane sanatçılarının adı aranarak toplandı
   (`LISTE_ADEDI = 6`). Veri kütüphanenin çevresinde yoğun, uzakta seyrek. Bu hem popülerlik
   yanlılığını hem değerlendirme sızıntısını (§6.1) doğuruyor.

---

## 3. Tarihçe: aile aile

Her aile için: **fikir · formül · kazandığı rejim · maliyet · önemli hiperparametreler.**

### 3.1 Tapestry (1992): "işbirlikçi filtreleme" adının doğuşu

- **Fikir.** Xerox PARC'ta e-posta ve haber filtreleme sistemi. Kullanıcılar belgelere not
  (annotation) düşer, filtreler bu notlar üzerinde çalışır ("X'in beğendiği belgeleri göster").
  Notlar belgeden sonra geldiği için filtreler tüm veritabanı üzerinde tekrar tekrar koşar.
  Otomatik öneri yoktu. Kullanıcı kimin görüşüne güveneceğini kendisi sorguluyordu.
- **Önemi.** Terimi tanıttı ve "insanların yargısı bir sinyaldir" fikrini koydu. Bizim K10
  (kalabalık katmanı) ve K16 (listeler insan eliyle verilmiş bir "bunu dinleyen şunu da dinliyor"
  işareti) tam bu soydan geliyor.
- Goldberg, Nichols, Oki, Terry, *CACM* 35(12):61–70, 1992.

### 3.2 GroupLens (1994): kullanıcı tabanlı kNN

- **Fikir.** Netnews için puan sunucuları ("Better Bit Bureaus"). Geçmişte anlaşan kullanıcıların
  gelecekte de anlaşacağı varsayımıyla tahmin yapılır. Açık mimari ve takma adla gizlilik vardı.
- **Formül (klasik user-kNN).**
  `r̂_ui = r̄_u + Σ_v sim(u,v)(r_vi − r̄_v) / Σ_v |sim(u,v)|`, burada `sim` Pearson korelasyonu.
- **Rejim.** Az öğe, çok kullanıcı, açık puanlar.
- **Bizde.** Tek kullanıcı olduğu için doğrudan uygulanmaz. Ama "liste-kNN" (sorguya en benzer
  listeleri bulup onların sanatçılarını oylamak) user-kNN'in bizdeki karşılığıdır. Ludewig &
  Jannach'ın oturum tabanlı kNN'i (§3.10) bunun güncel ve güçlü bir sürümü.
- Resnick ve ark., *CSCW* 1994, 175–186.

### 3.3 Öğe tabanlı CF: Sarwar (2001), Amazon (2003), Aiolli (2013)

- **Fikir.** Kullanıcılar yerine öğeler arası benzerlik önceden hesaplanır. Öneri, kullanıcının
  öğelerine benzeyenlerin ağırlıklı toplamıdır. Öğe-öğe ilişkisi kullanıcı-kullanıcıdan daha
  durağan, seyreklikte daha sağlam ve ölçeklenebilir.
- **Formül.**
  `s_uj = Σ_{i ∈ I(u)} sim(i,j)`. Kosinüs için `sim(i,j) = c_ij / √(d_i d_j)`. Genelde her
  i için yalnız en yakın K komşu tutulur (topK).
- **Sarwar ve ark. (WWW 2001).** Kosinüs, düzeltilmiş kosinüs ve korelasyon kıyaslandı. Öğe
  tabanlı yöntemler kullanıcı tabanlıdan belirgin iyi çıktı. 2016'da WWW "Test of Time" ödülü
  aldı.
- **Linden, Smith, York (IEEE Internet Computing 2003).** Amazon'un öğeden öğeye CF'si. Çevrimiçi
  hesaplama müşteri ve katalog sayısıyla büyümüyor, benzerlik çevrimdışı hesaplanıyor.
- **Büzülme (shrinkage) †.** Koren (KDD 2008, "Factorization meets the neighborhood") ve
  Bell & Koren (2007) benzerliği destekle büzer:
  `s̃_ij = n_ij/(n_ij + h) · s_ij`. Netflix'te h ≈ 100 kullanıldı. **Projenin
  `KANIT_BUZULMESI` çarpanı `n/(n+k)` tam olarak bu.** Bizim destek sayılarımız 1–20 aralığında
  olduğu için k = 1 Netflix'in 100'ünün ölçeklenmiş karşılığı. Ölçülen 4× recall@10 kazancı
  literatürle tutarlı.
- **Asimetrik kosinüs (Aiolli 2013, Million Song Dataset yarışması birincisi).**
  `S_ij = |U_i ∩ U_j| / (|U_i|^α · |U_j|^(1−α))`, skor `s_uj = Σ_{i∈I(u)} S_ij^q`.
  - α=½ kosinüstür. α koşullu olasılıklar `P(j|i)` ile `P(i|j)` arasında ara değer verir.
  - q ("yerellik") büyük benzerlikleri öne çıkaran bir üs. q → ∞ en güçlü tek bağa, yani
    **MAX'a** yakınsar. q = 1 düz toplamdır.
  - Doğrulanan değerler: öğe tabanlıda en iyisi α = 0,15, q = 3. Kullanıcı tabanlı sıralayıcı
    q = 5 ile tarandı. Kazanan birleşim (öğe α=0,15/q=3 + kullanıcı α=0,3/q=5)
    mAP@500 ≈ 0,179 verdi, kalibrasyonla 0,181. α=0 iken öğe tabanlı mAP q=1→3 aralığında
    0,122 → 0,171'e çıkıyor.
  - **Bizim için anlamı:** bugünkü MAX birleştirmesi q=∞ ucudur. Literatürün en iyisi
    q = 3–5 aralığında.
- **Rejim.** Seyrek, ikili (implicit), çok öğeli veri. Bugün de en güçlü sade kıyas çizgileri
  arasında (§3.8).
- **Maliyet.** `XᵀX` seyrek çarpım. Bizde yalnız tohum satırları gerektiği için `q·(XᵀX)`
  iki seyrek matris-vektör çarpımı: milisaniye.
- **Hiperparametreler.** Benzerlik türü, topK, büzülme h, α, q, kullanıcı (liste) ağırlıklandırma
  (TF-IDF/BM25). Ferrari Dacrema ve ark.'nın ayarlama uzayı †: topK 5–1000, shrink 0–1000,
  benzerlik ∈ {cosine, jaccard, asymmetric, dice, tversky}, asimetrik α 0–2, özellik
  ağırlıklandırma ∈ {none, TF-IDF, BM25}.

### 3.4 Netflix Ödülü ve matris ayrıştırma (2006–2009)

- **Fikir.** Kullanıcı ve öğeyi aynı düşük boyutlu uzaya gömmek:
  `r̂_ui = μ + b_u + b_i + p_uᵀ q_i`, en küçük kareler ve L2 düzenlileştirme ile, SGD ya da
  ALS kullanarak. Zamansal etkiler, örtük geri bildirim (SVD++) ve güven düzeyleri eklenebilir.
- **Bulgu.** Netflix Ödülü bağlamında MF klasik komşuluk yöntemlerini puan tahmininde geçti.
  Kazanan çözüm yüzlerce modelin harmanıydı. Komşuluk modelleri o harmanda da vardı.
- **Rejim.** Çok kullanıcı (480k), az öğe (18k), açık puan, RMSE hedefi.
- **Bizde.** Açık puan yok, kullanıcı sayısı 482. Dolaylı önemi büyük: aşağıdaki iALS ve
  BPR'nin atası.
- Koren, Bell, Volinsky, *IEEE Computer* 42(8):30–37, 2009.

### 3.5 Örtük geri bildirim için ALS: Hu, Koren, Volinsky (ICDM 2008)

- **Fikir.** Gözlenmemiş her (u,i) çifti "zayıf negatif", gözlenen çift "güvenle pozitif"
  sayılır. Tercih `p_ui = 1[r_ui > 0]`, güven `c_ui = 1 + α r_ui` (†: logaritmik varyant
  `1 + α log(1 + r/ε)`). Kayıp:
  `Σ_{u,i} c_ui (p_ui − x_uᵀ y_i)² + λ(Σ‖x_u‖² + Σ‖y_i‖²)`.
  Tüm matris üzerinde, ALS ile verimli çözülür (`YᵀY` önceden hesaplanır).
- **Hiperparametreler.** Boyut d, λ, α. Orijinal TV verisinde α ≈ 40 †.
- **iALS yeniden (Rendle, Krichene, Zhang, Koren, RecSys 2022).** iALS'in "zayıf" görüldüğü dört
  kıyas setinde iyi ayarlanınca rekabetçi olduğu gösterildi. Önerilen ayar sırası:
  - gözlenmemiş ağırlığı α₀ ve düzenlileştirme λ için önce log ızgara, sonra ince arama;
  - frekansla ölçeklenmiş düzenlileştirme (ν üssü). İyi λ değerleri ν seçimine göre farklı
    bölgelerde;
  - boyut d kapasiteyi belirler, maliyet d³ ile büyür.
- **Rejim.** Büyük, seyrek, sayım içeren örtük veri.
- **Bizde.** X ikili olduğu için güven ağırlığı anlamını yitiriyor. m = 482'de d ≤ 64 ile
  derecesi 1 olan sanatçının gömüsü tek listeden belirlenir. Uzun kuyruk düşük rank tarafından
  sıkıştırılır, ki kullanıcının istediğinin ("hiç duymadığım") tersi. Yeni sorgu için katlama
  kapalı formdur: `x_q = (YᵀC_qY + λI)⁻¹ YᵀC_q p_q`. **Öncelik düşük.** Kıyas için denenirse
  d ∈ {16, 32, 64}, α₀ ∈ 10^[−3, 0], λ log ızgara, ν = 1.

### 3.6 BPR (Rendle ve ark., UAI 2009)

- **Fikir.** Puan tahmini yerine sıralama. Her kullanıcı için gözlenen öğe gözlenmeyenden üstte
  olmalı. Sonsal tahminci:
  `max Σ_{(u,i,j)} ln σ(x̂_ui − x̂_uj) − λ‖Θ‖²`. Önyükleme (bootstrap) örneklemeli SGD ile
  eğitilir. MF'ye ve uyarlanabilir kNN'e uygulanabilir.
- **Rejim.** Örtük veri, AUC benzeri hedef. Sonraki "pairwise" ailesinin ve negatif örnekleme
  literatürünün kökü.
- **Bizde.** Örneklemeli SGD, küçük veri ve çok hiperparametre (öğrenme oranı, epok, negatif
  örnekleme) yüzünden kapalı formlu rakiplerine göre kötü bir yatırım. Atla.

### 3.7 Seyrek doğrusal modeller: SLIM (2011), FISM (2013)

- **SLIM (Ning & Karypis, ICDM 2011).** Öğe-öğe ağırlık matrisi W doğrudan öğrenilir:
  `min_W ½‖X − XW‖²_F + β/2 ‖W‖²_F + λ‖W‖₁`, kısıtlar `W ≥ 0`, `diag(W) = 0`. Her sütun için
  ayrı bir elastic-net problemi çözülür. Hem hız hem kalitede dönemin en iyilerini geçti.
  2020'de ICDM 10-yıl en yüksek etki ödülü aldı. Hiperparametreler †: l1_ratio 10^[−5, 0],
  alpha 10^[−3, 0], topK 5–1000.
- **FISM (Kabbur, Ning, Karypis, KDD 2013).** Benzerlik matrisini iki düşük boyutlu matrisin
  çarpımı olarak ayrıştırır (`S = PQᵀ`). Tahmin edilen değeri kendi tahmininden dışlar.
  **Seyreklik arttıkça** SLIM'e göre kazancı büyür.
- **Bizde.** SLIM: 10k elastic-net, her biri 482 satır × 10k sütunluk tasarım; numpy'da
  dakikalar–saatler sürer. EASE (§3.9) SLIM'i genelde geçer ve kapalı formdur. **SLIM atlanır.**
  FISM'in çok seyrek rejimdeki avantajı ilginç ama SGD eğitimi, ayarlama ve K2/K8 sadeliği
  açısından RP3β/EASE'e göre kötü bir takas.

### 3.8 Rastgele yürüyüşler: P3, P3α (2014), RP3β (2015/2017)

- **P3 / P3α (Cooper, Lee, Radzik, Siantos, WWW 2014 companion).** Kullanıcı→öğe→kullanıcı→öğe
  üç adımlı yürüyüşün dağılımı. Kesin hesap (matris cebiri) ile benzetim kıyaslandı. P3 önceki
  yürüyüş yöntemlerini (Fouss ve ark., Gori & Pucci) geçti, P3α (geçiş olasılıklarının α
  kuvveti) P3'ü de geçti. Veri: MovieLens.
  - Formül: `p_ui = Σ_j Σ_v P_uj^α P_jv^α P_vi^α`, burada `P_uj = x_uj/n_u` ve `P_jv = x_vj/d_j`.
- **RP3β (Christoffel, Paudel, Newell, Bernstein, RecSys 2015; dergi sürümü Paudel ve ark.,
  ACM TiiS 2017, doi 10.1145/2955101).** P3α skoru adayın derecesinin β kuvvetine bölünür:
  `W_ij ← W_ij / d_j^β`. Doğru sonuç verirken listenin üstüne çok sayıda uzun kuyruk öğesi
  taşır. Örnekleme tabanlı yaklaşık sürümler örnek sayısı arttıkça kesin sonuca yakınsar.
- **Kanıt.** Ferrari Dacrema ve ark. (RecSys 2019; TOIS 2021): tekrar üretilebilen 7 (sonra
  12) sinir ağı yönteminin 6'sı (sonra 11'i) en yakın komşu veya grafik tabanlı basit yöntemlerle
  geçildi. RP3β bu "basit" grubun düzenli üyesi. Sanayi kanıtı: bir ilan platformunda (2023)
  RP3β laboratuvarda SLIM ve ALS'e karşı güçlü çıktı, çevrimiçi A/B'de ALS'ten büyük artış verdi.
- **Hiperparametreler** (Ferrari Dacrema ayarlama uzayı †): topK 5–1000, α 0–2, β 0–2,
  satır normalizasyonu açık/kapalı.
- **Maliyet.** İki seyrek çarpım. Bizde tohum satırları yetiyor: milisaniye.
- **Bizde neden özel?** Bkz. §5.2. İkili X'te RP3β genelleştirilmiş ItemKNN'e indirgeniyor ve
  projenin elle ölçtüğü üç düğmeyi tek aileye topluyor.

### 3.9 Doğrusal otokodlayıcılar: EASE (2019) ve ardılları

- **Mult-VAE (Liang ve ark., WWW 2018) †.** Çok terimli olabilirlikli varyasyonel otokodlayıcı.
  Bir dönem en iyi kabul edildi. Dacrema'nın TOIS 2021 çalışmasında da güçlü bulunan nadir
  sinir ağı yöntemlerinden biri.
- **EASE^R (Steck, WWW 2019).** Gizli katmansız otokodlayıcı:
  `min_B ‖X − XB‖²_F + λ‖B‖²_F`, kısıt `diag(B) = 0`. Kapalı çözüm:
  `P̂ = (XᵀX + λI)⁻¹` ve `B̂ = I − P̂ · diagMat(1 ⊘ diag(P̂))`, yani `B_ij = −P_ij / P_jj`
  (i ≠ j). Yeterli istatistik Gram matrisi `G = XᵀX`. Tek hiperparametresi λ. Negatif
  ağırlıklara izin verir; SLIM'in `W ≥ 0` kısıtının kaldırılmasının kaliteyi artırdığını
  savunur. Bildirilen λ değerleri büyük veri setlerinde yüzlerden binlere †: ML-20M ≈ 500,
  Netflix ≈ 1000, MSD ≈ 200. Ferrari Dacrema'nın ayarlama uzayı † λ ∈ 10^[0, 7].
- **Ardıllar.**
  - EDLAE (Steck, NeurIPS 2020, "Autoencoders that don't overfit towards the identity") †:
    dropout'a eşdeğer **popülerlikle orantılı L2**, yani `Λ = λI + p/(1−p) · diagMat(diag(G))`.
  - "On the Regularization of Autoencoders" (Steck & Garcia, 2021).
  - "It's Enough: Relaxing Diagonal Constraints in Linear Autoencoders" (2023): `diag(B)=0`
    kısıtını gevşetiyor.
  - "Accurate and Diverse Recommendations via Propensity-Weighted Linear Autoencoders"
    (arXiv 2512.20896, Aralık 2025): başlığına göre popülerlik yanlılığını eğilim (propensity)
    ağırlığıyla düzeltip çeşitliliği artırıyor.
  - "Generalizing Linear Autoencoder Recommenders with Decoupled Expected Quadratic Loss"
    (arXiv 2603.07402, Mart 2026).
  - "On the Regularization Landscape for the Linear Recommendation Models" (arXiv 2609.11876,
    Eylül 2026).
  - Bu 2025–2026 makalelerinin yalnız varlığı ve başlığı doğrulandı, içerikleri okunamadı.
  - **Okuma:** 2026'da hâlâ en aktif "ucuz ve güçlü" hat doğrusal otokodlayıcılar.
- **Rejim.** Öğe sayısı orta (≤ ~50k), kullanıcı çok. O(n³) ters alma darboğaz.
- **Bizde.** m ≪ n olduğu için Woodbury ile ucuz (§5.3).

### 3.10 Tekrarlanabilirlik krizi (2019–2022): "gerçekten ilerliyor muyuz?"

- **Ferrari Dacrema, Cremonesi, Jannach (RecSys 2019).** Üst konferanslardaki 18 top-N
  algoritmasından yalnız 7'si makul çabayla üretilebildi. 6'sı komşuluk/grafik tabanlı basit
  sezgisellerle geçildi. TOIS 2021 genişletmesi: 12 üretilebilir yöntemin 11'i ya basit
  sezgisellerle ya doğrusal modellerle geçildi. Bazı makalelerde kıyas çizgileri hiç
  ayarlanmamış, varsayılan hiperparametrelerle bırakılmıştı.
- **Rendle, Krichene, Zhang, Anderson (RecSys 2020).** NCF'nin MLP benzerliği, iyi ayarlanmış
  nokta çarpımlı MF'ye kaybediyor. MLP'nin nokta çarpımını öğrenmesi pratikte kolay değil ve
  üretimde pahalı. Öneri: varsayılan nokta çarpımı.
- **Rendle ve ark. (RecSys 2022).** iALS iyi ayarlanınca rekabetçi (§3.5).
- **Rendle, Zhang, Koren (2019, "On the difficulty of evaluating baselines") †.** İyi ayarlanmış
  SGD-MF Netflix/ML-10M'de yıllarca "geçilmiş" sanılan sonuçları geçiyor.
- **Bizim için ders.** (1) Kıyas çizgisini en az önerilen yöntem kadar ayarla. (2) Ayarlamayı
  sınama setinde yapma (§6.2). (3) Karmaşıklık kanıt ister. K19 bu dersin proje içi hâli.

### 3.11 Ardışık / oturum tabanlı modeller (2016–2023)

- **GRU4Rec (Hidasi ve ark., ICLR 2016) †.** Oturumdaki tıklama dizisinden sonraki öğeyi GRU ile
  tahmin eder. Sıralama kayıpları BPR-max ve TOP1.
- **SASRec (Kang & McAuley, ICDM 2018) †.** Nedensel (tek yönlü) öz-dikkat, kaydırılmış dizi
  tahmini.
- **BERT4Rec (Sun ve ark., CIKM 2019) †.** Çift yönlü dikkat, maske tahmini görevi.
  - Petrov & Macdonald (RecSys 2022): varsayılan ayarlarla orijinal sonuçlar tekrar üretilemedi,
    ancak ~30 kat uzun eğitimle üretilebildi.
  - Klenitskiy & Vasilev (RecSys 2023): iki model de tam çapraz entropiyle eğitilince daha basit
    SASRec daha isabetli ve hızlı çıktı.
- **Oturum-kNN (Ludewig & Jannach, UMUAI 2018; RecSys 2017; Ludewig ve ark. 2019/2021).**
  Basit en yakın komşu sezgiselleri (SKNN, V-SKNN) çoğu yapılandırmada GRU4Rec'i geçti veya
  eşitledi. kNN+GRU4Rec birleşimi çoğu durumda en iyisiydi.
- **Bizde.** Kullanıcının sorgusu bir dizi değil, bir küme. Görev "sonraki parça" değil, sanatçı
  veya albüm keşfi. Ardışık model gereksiz. Ama Ludewig'in SKNN'i şunu söylüyor: "liste =
  oturum" kabul edilip sorguya en çok örtüşen listelerin oylaması yapılırsa bu, user-kNN'in
  bizdeki güçlü biçimidir. RP3β'ya ek bir kıyas çizgisi olarak düşünülebilir.

### 3.12 Grafik sinir ağları ve doğrusal grafik süzgeçleri (2019–2024)

- **NGCF (Wang ve ark., SIGIR 2019).** Kullanıcı-öğe grafiğinde yüksek mertebeli bağlantıyı
  mesaj geçirmeyle gömüye işler.
- **LightGCN (He ve ark., SIGIR 2020).** NGCF'deki özellik dönüşümü ve doğrusal olmayan
  etkinleştirmenin katkısı yok, çıkarılınca isabet arttı. Kalan şey yalnız komşu toplama:
  `E^(k+1) = Ã E^(k)`, `Ã = D^(−½) A D^(−½)`, son gömü katmanların ağırlıklı toplamı. Aynı
  düzenekte NGCF'ye göre ortalama ~%16 göreli iyileşme.
- **GF-CF (Shen ve ark., CIKM 2021).** Grafik sinyal işleme çerçevesi. Komşuluk yöntemleri, düşük
  ranklı MF, doğrusal otokodlayıcılar ve LightGCN farklı alçak geçiren süzgeçlerin özel
  durumları. GF-CF **kapalı formda, eğitimsiz** elde edilir. Amazon-book'ta LightGCN'e göre ~%70
  kazanç bildirildi. Formül †:
  `R̃ = D_U^(−½) R D_I^(−½)`, `P̃ = R̃ᵀR̃`,
  `s_u = r_u (P̃ + γ · D_I^(−½) Ū Ūᵀ D_I^(½))`. Burada Ū, R̃'nin ilk k sağ tekil vektörü
  ("ideal alçak geçiren" bileşen).
- **Ardıllar †.** BSPM (Choi ve ark., SIGIR 2023, ısı denklemi/bulanıklaştır-keskinleştir) ve
  Turbo-CF (Park ve ark., SIGIR 2024, eğitimsiz polinom süzgeçleri) aynı "eğitimsiz doğrusal
  süzgeç" hattında.
- **Bizde.** LightGCN'in 482 listede öğreneceği şey çok adımlı yumuşatılmış öğe-öğe
  ilişkisinden ibaret. RP3β ve GF-CF bunu eğitimsiz yapıyor. Not: GF-CF'nin `P̃`'si kullanıcı
  tarafında `n_p^(−½)` ve öğe tarafında `d^(−½)` normalizasyonuyla RP3β ailesinin bir noktası.
  Tekil vektörler için 482×10k SVD saniyeler sürer. **GF-CF eklemesi ucuz bir kıyas çizgisi.**

### 3.13 İki kuleli (two-tower) erişim (2016–2025)

- **Covington ve ark. (RecSys 2016, YouTube DNN) †.** Aday üretimi + sıralama iki aşaması,
  örneklemeli softmax.
- **Yi ve ark. (RecSys 2019).** Kullanıcı ve öğe kuleleri, parti içi negatifler. Kuvvet yasası
  dağılımında parti içi negatif örnekleme yanlılık doğurur. Akan veriden öğe frekansı kestirilip
  logit'ten `log Q` çıkarılır (logQ düzeltmesi). 2025'te "Correcting the LogQ Correction"
  (arXiv 2507.09331) bu düzeltmenin kendisini yeniden ele aldı.
- **Rejim.** Milyonlarca öğe ve kullanıcı, zengin özellikler, ANN ile sunum.
- **Bizde.** Kullanıcı kulesi yok, ki gerekmiyor da: tohum kümesinin CLAP gömülerinin ortalaması
  zaten bir "kullanıcı kulesi" ve CLAP önceden eğitilmiş bir "öğe kulesi" (ses yolu bunu
  yapıyor). Eğitecek veri yok. **Atla.**

### 3.14 Difüzyon tabanlı öneri (2023–2025)

- **DiffRec (Wang ve ark., SIGIR 2023).** Kullanıcının etkileşim vektörü gürültülendirilip
  adım adım geri kazanılır. L-DiffRec öğeleri kümeleyip gizil uzayda difüzyon yapar, T-DiffRec
  zaman damgasıyla yeniden ağırlıklandırır. Araştırmalar: Lin ve ark. 2024 (arXiv 2409.05033),
  Wei & Fang 2025 (arXiv 2501.10548).
- **Eleştiri (arXiv 2505.09364, 2025).** SIGIR 2023–2024'ten dört difüzyon önericisi, DiffRec
  dahil, **daha basit mevcut modellerce tutarlı biçimde geçildi**. Olasılıksal üretici doğa ile
  top-n değerlendirmenin deterministik gereği arasında kavramsal bir uyumsuzluk da vurgulandı.
- **Bizde.** Atla.

### 3.15 Üretici erişim ve LLM tabanlı öneri (2023–2026)

- **TIGER (Rajput ve ark., NeurIPS 2023).** İçerik gömüleri RQ-VAE ile hiyerarşik "anlamsal
  kimliklere" (semantic ID) nicelenir. Transformer bir sonraki öğenin kimliğini kod çözerek
  üretir.
- **HSTU (Zhai ve ark., ICML 2024, "Actions Speak Louder than Words…") †.** Meta'nın üretici
  önerici mimarisi. Kullanıcı geçmişi öğe ve eylemlerin iç içe dizisi olarak modellenir;
  ölçekleme yasaları ve üretimde trilyon parametre iddiası †. NVIDIA'nın 2024–2025 notları
  HSTU ile anlamsal kimlikleri üretici önerinin iki ana yaklaşımı sayıyor.
- **LLM önericiler ve tekrarlanabilirlik (2025–2026).**
  - RecRankerEval (ECIR 2026): RecRanker'ın noktasal yönteminin olağandışı yüksek sonuçları
    sızıntıdan geliyordu (doğru cevap istemde).
  - XRec tekrarı (arXiv 2510.06275, 2025): XRec bazı ölçütlerde kıyas çizgilerini geçemedi.
  - Klagenfurt grubu (2026, "Reproducibility of LLM-based Recommender Systems Research:
    Worrying Observations…"): LLM'lerin rastlantısallığı ve karmaşıklığı tekrarlanabilirliği
    daha da kötüleştiriyor.
  - 2026 ön baskısı: soğuk başlangıçta LLM yeniden sıralayıcılar popülerlik sıralamasının
    gerisinde kaldı.
- **Bizde.** K2 (LLM yok, 0 TL) zaten dışlıyor. Literatür de bu kararı destekliyor: küçük ve
  orta veride bu ailelerin kanıtlanmış bir üstünlüğü yok.

### 3.16 Müziğe ve çalma listesine özgü hat

- **Bonnin & Jannach (ACM CSUR 2014, "Automated generation of music playlists: survey and
  experiments") †.** Liste devam ettirmede kNN tabanlı yöntemler ve sanatçı/popülerlik
  sezgiselleri şaşırtıcı derecede güçlü.
- **RecSys Challenge 2018 (Spotify MPD, 1M liste).** Ana yolda 113 takım ve 1.228 gönderim. En
  iyi R-precision 0,2241, NDCG 0,3946 (Zamani, Schedl, Lamere, Chen, ACM TIST 2019).
  - Birinci vl6 (Volkovs ve ark. 2018): iki aşamalı mimari. Hızlı aday erişimi (CF; anahtar
    sözcükleri işbirlikçi filtreleme, CNN, gradyan artırma) ve üst sırada isabet için yeniden
    sıralama.
  - Üçüncü Avito: CF ile aday seçimi + gradyan artırma.
  - 12. Latte: CF'lerin bileşimi.
  - **Ders:** en iyi sistemler bile aday üretiminde komşuluk/MF ailesine dayandı. Kazanç,
    yeniden sıralamada çok sinyalin birleşiminden geldi.
- **Deezer (Bendada ve ark., RecSys 2023, "A Scalable Framework for Automatic Playlist
  Continuation", arXiv 2304.09061) †.** Önce temsil et sonra birleştir: listenin temsili
  parça gömülerinin birleşimi.
- **Vall, Schedl ve ark. (UMUAI 2019) †.** Liste devam ettirmede ses/etiket özellikleriyle CF'yi
  birleştiren özellik-birleşimi melezleri. Soğuk parçalarda içerik şart.
- **van den Oord, Dieleman, Schrauwen (NeurIPS 2013) †.** Sesten (CNN) WMF gizil faktörlerini
  regresyonla tahmin et: içerikten CF uzayına eşleme fikrinin müzikteki klasiği.

---

## 4. Ailelerin özet tablosu

| Aile | Temsilci | Kazandığı rejim | Maliyet (bizde) | Önemli hiperparametre | Bizde öncelik |
|---|---|---|---|---|---|
| Öğe-kNN | Sarwar 2001, Aiolli 2013 | seyrek, ikili, çok öğe | ms | benzerlik, topK, h, α, q, liste ağırlığı | **yüksek** (var, genelleştir) |
| Rastgele yürüyüş | P3α 2014, RP3β 2015/17 | seyrek, uzun kuyruk istenen | ms | α, β, topK | **en yüksek** |
| Doğrusal otokodlayıcı | EASE 2019, EDLAE 2020 | n ≤ ~50k, çok kullanıcı | ms (Woodbury) | λ (+ popülerlik ölçekli λ) | **yüksek** |
| Eğitimsiz grafik süzgeci | GF-CF 2021 | GCN'in yaptığını eğitimsiz | sn (SVD) | γ, k | orta |
| Heterojen PPR | Konstas 2009 †, Pixie 2018 † | çok türlü ilişki, açıklama | ms | yeniden başlama, kenar türü ağırlıkları, β | **yüksek** |
| MF / iALS | Hu 2008, Rendle 2022 | büyük örtük veri | sn | d, α₀, λ, ν | düşük |
| BPR | Rendle 2009 | büyük örtük veri | dk | lr, epok, negatif | çok düşük |
| SLIM / FISM | 2011 / 2013 | orta n; FISM çok seyrek | dk–sa | l1, l2, topK / d | düşük |
| Ardışık | GRU4Rec, SASRec | uzun etkileşim dizileri | — | — | yok (görev uymuyor) |
| GNN | NGCF, LightGCN | büyük grafik | — | — | yok (GF-CF yeter) |
| İki kule | YouTube 2016/2019 | dev katalog, özellik | — | — | yok |
| Difüzyon / LLM | DiffRec, TIGER, HSTU | endüstriyel ölçek | — | — | yok (K2 + kanıt) |

---

## 5. Uygulama: 482 liste ve eksen başına ağırlıklı tohum kümesi

### 5.1 Bugünkü yöntemin literatürdeki yeri

Bugün liste yolu şunu yapıyor (`calma_listesi.birliktelik`, `degerlendirme.pmi_sirala`):

```
s_j = max_{i : q_i > 0}  NPMI(i, j) · c_ij / (c_ij + 1)       (c_ij ≥ 2 ise)
NPMI(i,j) = log( p_ij / (p_i p_j) ) / (−log p_ij)
```

Literatürle eşleşmesi:

- `log(p_ij/(p_i p_j)) = log(c_ij · N / (d_i d_j))`. Tek bir tohum içinde sıralama bakımından
  PMI, `c_ij / (d_i^a d_j^b)` biçimli bir benzerliğin **a = b = 1** ucuna denk düşer: adayın
  popülerliği tam üsle cezalandırılır. NPMI'nın paydası nadirlik primini sönümleyerek bunu biraz
  yumuşatır.
- `c/(c+1)` Koren tipi büzülme (§3.3).
- `MAX` birleştirmesi Aiolli'nin q → ∞ ucudur. Literatürdeki öğe-kNN tohumlar üzerinde **toplar**.
  Aiolli'nin MSD'de bulduğu en iyi q, toplam ile MAX arasında, 3–5 aralığında.
- Eksen üyelikleri (u_ij) kullanılmıyor, keskin küme kullanılıyor.

Yani bugünkü yöntem iyi tanımlanmış bir ailenin **tek bir köşesi**. Aşağıdaki öneri, köşeden
ailenin içine çıkıp onu ölçerek ayarlamaktır.

### 5.2 Öneri A: RP3β = genelleştirilmiş ItemKNN (en yüksek öncelik)

**İndirgeme.** X ikili olduğunda `x^α = x` olur. P3α'nın öğe-öğe matrisi
(`P_jv = x_vj/d_j`, `P_vi = x_vi/n_v`):

```
W_ij = Σ_p (x_pi / d_i)^α (x_pj / n_p)^α        (P3α)
     = (1 / d_i^α) · Σ_p x_pi x_pj · n_p^(−α)
RP3β:  W_ij ← W_ij / d_j^β
Skor:  s = q · W     (tohumlar üzerinde TOPLAM; isteğe bağlı topK ve satır normalizasyonu)
```

Bu, şu genel ailenin bir alt kümesi:

```
S_ij = c_ij^(ρ) / (d_i^a · d_j^b + h),   c_ij^(ρ) = Σ_p x_pi x_pj · n_p^(−ρ)
s_j  = Σ_i  q_i · S_ij^γ        (γ: Aiolli yerelliği; γ → ∞ ≈ MAX)
```

| Düğme | Anlamı | Projedeki karşılığı | Literatür |
|---|---|---|---|
| ρ | büyük listenin sesini kısma | `LISTE_AGIRLIGI`: eşit = 0, ters = 1 (log ≈ 0,1–0,2) | RP3β'da ρ = α; BM25/TF-IDF kullanıcı ağırlığı |
| a | çok listede geçen tohumun sesini kısma | yok (MAX bunu gizliyor) | RP3β'da a = α; asimetrik kosinüs α |
| b | adayın popülerlik cezası | PMI'da örtük b ≈ 1 | RP3β β |
| h | az kanıtı büzme | `KANIT_BUZULMESI` (çarpımsal biçim) | Koren shrink |
| γ | tek güçlü bağ ↔ çok zayıf bağ | MAX (γ = ∞) | Aiolli q |
| topK | her tohumun en çok kaç komşusu oy verir | `adet*3` limiti | topK |

**Neden en yüksek öncelik?**

1. Projede altı kez ayrı ayrı ölçülüp düzeltilen popülerlik/nadirlik yanlılığı tek düzlemde iki
   sürekli düğmeye (b ve ρ) iniyor. Karar günlüğündeki "recall ↔ görünürlük" gerilimi (k = 1 mi,
   k = 4 mü?) b üzerinde bir **Pareto eğrisi** olarak çizilebilir. Kullanıcı o eğri üzerinde
   nokta seçer: K13'ün "sistem karar vermez" ruhuna uygun.
2. Dacrema'nın tüm tekrarlanabilirlik çalışmalarında RP3β ve ItemKNN, ayarlanmış hâlleriyle en
   zor geçilen kıyas çizgileri.
3. K7 şablonu doğrudan çıkar: `s_j = Σ_i q_i S_ij^γ` toplamının terimleri "hangi tohumdan ne
   kadar" sorusunun tam cevabı. Örnek: "Rush ile 5 listede, Dream Theater ile 3 listede birlikte;
   skorun %60'ı Rush'tan."
4. Maliyet: tohum satırları için iki seyrek matris-vektör çarpımı, numpy/scipy ile milisaniye.
   Tam 10k×10k matris gerekmez. topK budaması da yalnız tohum satırlarında yapılır.

**Önerilen ızgara** (LOAO ayarlama yarısında; §6.2):

- α veya (ρ, a): {0, 0,25, 0,5, 0,75, 1}. Literatür aralığı 0–2 †. İkili ve küçük veride 0–1
  yeterli.
- β veya b: {0, 0,25, 0,5, 0,75, 1}. Literatür 0–2 †. Bizde b = 1 bugünkü PMI ucu; kullanıcı
  uzun kuyruk istediği için 0,5–1 arası ilgi bölgesi.
- h: {0, 0,5, 1, 2, 4}. Bugünkü k = 1 merkezde.
- γ: {1, 2, 3, 5, ∞}. Aiolli: öğe tabanlıda 3, kullanıcı tabanlıda 5.
- topK: {50, 100, 200, tümü}. Dacrema 5–1000 †.
- Asgari destek `c_ij ≥ 2`: hem açık hem kapalı. Bugünkü eşik kıyas adilliği için korunmalı.
- Tam ızgara ~5⁴×4 ≈ 2.500 yapılandırma, her biri 147 gizleme × ms. Toplam dakikalar. Seçim
  yanlılığını önlemek için §6.2 zorunlu.

**Beklenti (tahmin, ölçülmedi).** Tohum toplamı (γ = 2–3) ve ρ > 0, MAX + eşit ağırlığa göre
recall'u artırmalı. Birden çok eksen sanatçısına bağlanan aday "uzlaşmanın" ödülünü alır (projenin
destedeki `UZLASMA_AGIRLIGI` fikrinin liste yolu içindeki karşılığı). b'yi 1'den aşağı çekmek
recall'u artırıp görünürlüğü (popülerliği) yükseltir. İkisi birlikte raporlanmalı.

### 5.3 Öneri B: EASE'i Woodbury özdeşliğiyle kurmak

**Fizibilite sorusu: 10k öğede EASE mümkün mü?** Doğrudan yol: `G` 10.360² ≈ 1,07×10⁸ eleman.
float64 ~860 MB, float32 ~430 MB. Ters alma ~n³ ≈ 1,1×10¹² flop, M1'de dakikalar. Mümkün ama
gereksiz, çünkü **m = 482 ≪ n**. Woodbury özdeşliği:

```
P = (λ I_n + XᵀX)⁻¹ = (1/λ) · [ I_n − Xᵀ K⁻¹ X ],     K = λ I_m + X Xᵀ   (482 × 482)
diag(P)_j = (1/λ) · (1 − x_jᵀ K⁻¹ x_j)                (x_j: X'in j. sütunu, seyrek)
(qP)      = (1/λ) · (q − (q Xᵀ) K⁻¹ X)
EASE skoru (q_j = 0 olan aday j için):  s_j = − (qP)_j / P_jj
```

Maliyet: 482×482 ters alma (~10⁸ flop) + seyrek çarpımlar = **milisaniye**. Liste ağırlığı da
eklenebilir: `G = Xᵀ D_w X` için `K = λ D_w⁻¹ + X Xᵀ`, ya da X'in satırlarını `√w_p` ile
ölçeklemek.

**Rejime özgü dikkat noktaları.**

- `rank(G) ≤ 482` olduğundan λ'nın rolü büyük. Uç davranışlar:
  - λ → ∞: `P ≈ (1/λ)(I − G/λ)` olur, dolayısıyla `B_ij ≈ G_ij / (λ − G_jj) ≈ G_ij/λ`. EASE
    **ham birlikteliğe** döner, yani popülerlik yanlı ve normalizasyonsuz kNN.
  - λ küçük: regresyon gibi davranır. Aynı listede birlikte geçmekten gelen kanıtı "açıklayıp
    giderir" (explaining away), negatif ağırlıklar çıkar. Örneğin 250 sanatçılı «1. Çalma
    Listem» içindeki her çifti ayrı kanıt saymaz, çünkü o çiftler aynı satırdan geliyor.
  - Aradaki doğru nokta ölçülmeli.
- Steck'in büyük veri λ'ları (yüzler–binler) †, `diag(G)`'nin binlerle ölçüldüğü veriler için.
  Bizde `diag(G) = d_j` çoğunlukla 1–20. **Önerilen ızgara:** λ ∈ {0,1, 0,3, 1, 3, 10, 30, 100}.
  Ek olarak EDLAE tipi popülerlik ölçekli düzenlileştirme † `Λ = λI + κ·diagMat(d)`,
  κ ∈ {0, 0,25, 1, 4}. Bu, adayın popülerliği arttıkça ağırlığını daha çok büzer: β'nın EASE'teki
  karşılığı. Woodbury `Λ` köşegen olduğu sürece geçerli:
  `(Λ + XᵀX)⁻¹ = Λ⁻¹ − Λ⁻¹Xᵀ(I + XΛ⁻¹Xᵀ)⁻¹XΛ⁻¹`.
- Negatif ağırlıklar açıklama şablonuna (K7) zor girer ("şu sanatçı skoru düşürdü"). Gösterimde
  yalnız pozitif katkılar kullanılabilir, skor yine tam B ile hesaplanır.
- Bir uyarı: listeler kütüphane sanatçısı aranarak toplandığı için EASE "tohum sanatçı →
  listesindeki diğerleri" ilişkisini güçlü öğrenir. §6.1'deki düzeltme olmadan EASE'in
  değerlendirmesi özellikle şişebilir.

**Konumu.** RP3β'ya rakip ikinci kıyas çizgisi. İkisi aynı LOAO ile ölçülür, kazanan liste yolu
olur. Dacrema'nın 2021 bulgularında EASE ve RP3β çoğu veri setinde ilk üçteydi †.

### 5.4 Öneri C: heterojen grafikte kişiselleştirilmiş PageRank (RWR)

**Grafik.**

- Düğümler: sanatçılar A (kütüphane + aday), listeler P (482), müzisyenler M (kredilerden).
- Kenar türleri:
  - A–P: listede geçme, ağırlık 1 ya da `n_p^(−ρ)`.
  - A–M: kadroda çalma/prodüksiyon (rol türüne göre ağırlık).
  - A–A (LB): ListenBrainz benzer-sanatçı skoru.
  - A–A (K): CLAP karşılıklı-kNN (k = 10–20), hubness düzeltmesinden sonra. Karşılıklı kNN
    göbek (hub) sanatçıların yayılmasını kısıtlar.

**Geçiş.** Sanatçıdan çıkışta önce kenar türü seçilir (π_P, π_M, π_LB, π_K; o sanatçıda
bulunmayan türler için yeniden normalize edilir), sonra tür içinde ağırlıkla orantılı komşuya
gidilir. Listeden ve müzisyenden çıkış bağlı sanatçılara eşit ya da ağırlıklıdır. Bu "meta-yol
ağırlıklı" bir yürüyüş.

**Skor.**

```
s = (1 − c) · Σ_{t=0}^{T} c^t · r Tᵗ ,     r = q^(k) / ‖q^(k)‖₁   (eksen üyelikleri)
son düzeltme:  s_j ← s_j / d_j^β      (ya da durağan dağılımın β kuvvetine bölmek)
```

**Hiperparametreler.**

- Yeniden başlama 1 − c ∈ {0,15, 0,3, 0,5}. Klasik PageRank sönümü 0,85, yani yeniden başlama
  0,15. Öneri için daha yerel, 0,3–0,5 genelde daha iyi.
- Yürüyüş uzunluğu: T = 1 meta-adım (A→X→A, P3'ün karşılığı) ve T = 2. Cooper ve Christoffel'in
  ortak bulgusu kısa yürüyüşlerin uzun ve durağan yürüyüşlerden iyi olduğu. Uzun yürüyüş göbek
  düğümlere (popüler sanatçı, dev liste) akar.
- β ∈ {0,25, 0,5, 0,75}: PPR'nin yüksek dereceli düğümleri kayırması bilinen bir sorun ve RP3β
  düzeltmesi burada da geçerli.
- π simpleksi: kaba ızgara, örneğin π_P ∈ {0,4, 0,6, 0,8}, kalan kütle M/LB/K arasında.

**Pixie'den alınacak iki fikir (Eksombatchai ve ark., WWW 2018) †.**

1. Çok tohumlu sorguda her tohum için ayrı yürüyüş yapılır. Sonuçlar
   `V[j] = (Σ_seed √V_seed[j])²` ile birleştirilir: birden çok tohumdan ulaşılan adayı ödüllendiren
   ve toplam ile MAX arasında duran bir birleştirme. Aiolli'nin γ'sının kardeşi.
2. Tohum başına adım bütçesi tohumun derecesine göre ölçeklenir.

**Neden?**

- RRF bugün iki ayrı sıralamayı birleştiriyor. PPR tüm kanıt ailelerini (liste, kredi, kalabalık,
  ses) tek bir olasılık kütlesinde birleştirir. Destedeki "uzlaşma ödülü" (K21 (21)) burada
  yapısal olarak kendiliğinden ortaya çıkar: birden çok yoldan ulaşılan aday daha çok kütle alır.
- T = 1 iken skor tohum × kenar türü katkılarına tam ayrışır. K7 cümlesi kurulabilir: "Skorun
  %55'i ortak listelerden, %30'u ortak davulcudan (Gavin Harrison), %15'i ses komşuluğundan."
- Literatür: Konstas, Stathopoulos, Jose (SIGIR 2009) †, Last.fm'de kullanıcı–parça–etiket–
  arkadaşlık grafiğinde RWR. Bu, müzikte heterojen RWR'nin klasik örneği. Ayrıca "Recommender
  Systems with Random Walks: A Survey" (arXiv 1711.04101).

**Risk.** Daha çok hiperparametre, 147 gizlemelik küçük değerlendirme ve seçim yanlılığı. RP3β
(yalnız liste) ve RRF'ye karşı aynı protokolle kıyaslanmadan üretime girmemeli (K19).

### 5.5 Öneri D: içeriği (CLAP) ve yan bilgiyi (krediler) enjekte etmek

Literatürdeki melezleme yolları (Burke 2002'nin sınıflaması †: ağırlıklı, anahtarlamalı,
özellik-birleşimi, kaskad...) ve bizdeki somut karşılıkları:

1. **Skor/sıra füzyonu (bugün).** RRF: `Σ_r w_r/(k + rank_r)`, k = 60 (Cormack, Clarke,
   Büttcher, SIGIR 2009 †). Ölçek bağımsız ve sağlam. Bkz. §5.6.
2. **Sözde listeler (collective / side-information CF).** CLAP ve krediler X'e ek satır olarak
   eklenir:
   - her sanatçının CLAP karşılıklı-kNN kümesi bir "sözde liste" satırı olur;
   - her müzisyenin çaldığı sanatçılar bir satır olur (müzisyen = kadro listesi);
   - ListenBrainz komşulukları da satır olarak eklenebilir.
   - `X̃ = [X ; √μ_K F_K ; √μ_M F_M]`. Ardından **aynı** RP3β/EASE makinesi koşar. Jeunen,
     Van Balen, Goethals (RecSys 2020 LBR, "Closed-form models for collaborative filtering with
     side-information") † EASE'i bu biçimde (birleşik Gram matrisi) ve skor düzeyinde
     (`B = (1−w)B_X + wB_F`) genişletti. Kapalı form korunuyor.
   - Avantaj: tek hiperparametre μ ile tek, açıklanabilir model. Woodbury de satır sayısı
     ~482 + birkaç bin olduğu sürece ucuz.
3. **Grafik kenarı olarak içerik.** §5.4'teki A–A (K) kenarı. Aynı fikrin grafik hâli.
4. **İçerikten CF uzayına eşleme (soğuk aday).** Listede hiç geçmeyen ya da `d_j ≤ 1` olan
   aday için CF skoru yok, yalnız CLAP var.
   - CFeCBF (Deldjoo, Ferrari Dacrema ve ark., UMUAI 2019, "Movie genome") †: içerik
     özelliklerinin ağırlıkları, içerik benzerliği CF benzerliğini taklit edecek biçimde
     öğrenilir.
   - Bizde kapalı form: `S^CF_ij ≈ Σ_f w_f e_if e_jf` (Hadamard özellik `z_ij = e_i ⊙ e_j`
     üzerinde ridge). Eğitim çiftleri her iki sinyalde de bulunan sanatçılardan gelir, çözüm
     numpy'da tek `lstsq`. Sonuç: "liste kalabalığının duyduğu biçimde ağırlıklanmış" bir CLAP
     benzerliği.
   - Benzer fikirler: CB2CF (Barkan ve ark. 2019) †, DropoutNet (Volkovs ve ark., NeurIPS
     2017) †, van den Oord 2013 † (sesten gizil faktör regresyonu).
   - Bu, ses yolunun spektral çalışmadan sonra kötüleşmesine (karar günlüğü (17)) yönelik
     ölçülebilir bir aday düzeltme. Ses yolunu kalabalık sinyaline hizalıyor.
5. **Anahtarlamalı melez.** `d_j ≥ 2` ise liste/RP3β skoru, değilse içerik skoru (eşlenmiş
   CLAP). Basit, ölçülebilir ve kapsama tavanını yükseltir.
6. **Hubness.** CLAP gibi yüksek boyutlu gömülerde göbek (hub) sorunu iyi belgelenmiştir:
   Schnitzer, Flexer, Schedl, Widmer (JMLR 2012) †, karşılıklı yakınlık (mutual proximity) ve
   yerel ölçekleme. Proje bunu zaten düzeltiyor. Kenar/sözde liste kurarken karşılıklı kNN
   kullanmak aynı korumayı grafiğe taşır.

### 5.6 Füzyon: RRF'yi koruyun ama ağırlığı adil ölçün

- RRF ölçek bağımsız ve aykırı değere dayanıklı. Literatürde (Cormack 2009 †) k = 60 iyi bir
  varsayılan. k küçüldükçe üst sıralara ağırlık artar.
- Bugünkü 1:2 ağırlığı (liste:ses) LOAO'nun **tümünde** seçildiyse iyimser. 147 sanatçı ikiye
  bölünmeli: biri ağırlık seçimi, öteki rapor için, sonra yer değiştirilmeli (§6.2).
- Alternatif: sıra yüzdelikleriyle CombSUM, ya da 2–3 parametreli lojistik "öğrenilmiş füzyon"
  (girdi: her yolun sırası/yüzdeliği; hedef: gizlenen mi). RecSys Challenge 2018 birincilerinin
  yaptığının küçük ölçekli hâli: aday üretimi + ikinci aşama. Örnek 147 pozitif olduğundan
  parametre sayısı 3–5'i geçmemeli.
- PPR (§5.4) ya da sözde listeli tek model (§5.5-2) kazanırsa RRF gereksizleşebilir. Bunu da
  ölçüm söyler.

### 5.7 Eksen sorgusunu kurmak: üyelikler

- `q_i^(k) = Σ_{a∈albüm(i)} u_ak^τ`, τ ∈ {1, 2, 3}; ya da `u_ak ≥ 1/c + δ` eşiği. Keskin atama
  τ → ∞'ın özel hâli. Bu da ölçülebilir bir düğme ve K3'ün "üyelik = ağırlık" ilkesini liste
  yoluna taşır.
- **Eksene özgü skor (karşıtsal).** `s^(k) − ζ · s^(tüm kütüphane)`, ζ ∈ {0, 0,25, 0,5}.
  Kütüphanenin geneline zaten yakın olan (her eksende çıkan, çoğu zaman popüler) adayları geri
  iter. Projenin daha önce kullandığı "eksen-özgüllüğü" sıralama ölçütünün sürekli bir genellemesi.

---

## 6. Değerlendirme protokolü (algoritma kıyasının ön şartı)

### 6.1 Hasat sızıntısı

`hasat()` her kütüphane sanatçısının adıyla Deezer'da liste arıyor ve `tohum_sanatci` alanına
yazıyor. LOAO'da gizlenen sanatçı G için:

- G'nin adıyla bulunmuş ≤ 6 liste veride kalıyor. Bu listeler G'yi neredeyse kesinlikle içeriyor,
  çoğu zaman G'nin tarzındaki diğer kütüphane sanatçılarını da.
- Gerçek kullanımda tanımadığınız bir sanatçı için böyle bir arama yapılmaz. O ancak *başka*
  sanatçılar aranırken bulunan listelerde geçerse havuza girer.
- Sonuçlar:
  1. **Tavan şişer.** "147 sanatçının 132'si listelerde geçiyor" kısmen her birinin adıyla arama
     yapılmasının ürünü.
  2. **Recall şişer.**
  3. **Şişme yönteme göre farklıdır.** G'nin derecesi kendi aramasıyla yükseldiği için düşük b/β
     (popülerliğe az ceza) kullanan yöntemler daha çok kazanır. Yani RP3β'nın β'sı veya EASE'in
     λ'sı sızıntılı protokolde **yanlış yönde** ayarlanır.
- **Düzeltme:** gizleme sırasında `tohum_sanatci = G` olan listeleri (ve yalnız onların G'ye ait
  satırlarını değil, listenin tamamını) dışarıda bırakın. Sonra bugünkü 0,15'i yeniden ölçün.
  Yeni sayı daha düşük ama dürüst bir taban olacak, bütün kıyaslar bu taban üzerinden yapılmalı.
- Benzer bir gizli sızıntı CLAP aday havuzunda da var mı diye bakın: aday havuzunun ~3.000
  parçası nasıl seçildi, gizlenen sanatçıya dayanarak mı?

### 6.2 Ayarlama/sınama ayrımı ve belirsizlik

- Dacrema'nın ana eleştirilerinden biri hiperparametrelerin sınama verisinde seçilmesi. 147
  gizlemeyi rastgele (tohumlu, K2) iki yarıya bölün. A'da ayarlayın, B'de raporlayın, sonra
  yer değiştirin (2 katlı çapraz uydurma). İki sonucu da yazın.
- Karşılaştırmalar **eşli**: aynı gizlemelerde yöntem farkı. Sanatçı başına karşılıklı sıra
  farkının eşli bootstrap %95 aralığı, ya da işaret/Wilcoxon sınaması. n = 147'de recall@50
  farkı 0,03 (yaklaşık 4–5 sanatçı) gürültü içinde kalabilir. Karar günlüğü (17)'nin "farklar yön
  göstergesi" uyarısı doğru.
- Çok sayıda yapılandırma tarandığında "en iyinin" iyimserliği. Tek standart hata kuralı:
  en iyiye 1 SE yakın olan en basit/en popülerlik-cezalı yapılandırmayı seçin.

### 6.3 Popülerliğe göre katmanlı ölçüt

- Kullanıcının başarı ölçütü "hiç duymadığım sanatçı". Recall, popüler gizlenenleri bulmakla
  kolayca şişer (karar günlüğündeki k = 4 vakası).
- Steck (RecSys 2011, "Item popularity and recommendation accuracy") † popülerliğe göre katmanlı
  recall önerdi: isabetler `1/d_G^γ` ile ağırlıklanır, ya da gizlenenler görünürlük
  yarılarına/üçte birlerine bölünüp ayrı raporlanır.
- Projenin "medyan görünürlük" sütunu doğru yönde. Katmanlı recall onu bir isabet ölçütüne
  dönüştürür.
- MNAR uyarısı (Steck, KDD 2010 †): sahiplik rastgele eksik değil. Mutlak seviyeler yerine yöntem
  kıyasına güvenin. K19 zaten bunu söylüyor.

### 6.4 Örneklemeli ölçüt tuzağı

- Krichene & Rendle (KDD 2020, "On sampled metrics for item recommendation") † 100 rastgele
  negatife karşı sıralamanın yöntem sıralamasını tersine çevirebildiğini gösterdi.
- Proje tam sıralama kullanıyor (doğru). Bu korunmalı.

---

## 7. Somut deney planı (önerilen sıra)

| Adım | İş | Maliyet | Karar ölçütü |
|---|---|---|---|
| 0 | LOAO'ya hasat sızıntısı düzeltmesi (§6.1) + A/B yarıları (§6.2) + katmanlı recall (§6.3) | yarım gün | yeni taban sayıları |
| 1 | Liste yolunu genelleştirilmiş ItemKNN/RP3β ile değiştirmeden yanına koy; ızgara (§5.2) | ms/yapılandırma, dakikalar | B yarısında recall@50 ve katmanlı recall, eşli bootstrap |
| 2 | Toplam vs MAX (γ) ve üyelik ağırlıklı q (τ) (§5.2, §5.7) | aynı | aynı |
| 3 | EASE-Woodbury, λ × κ ızgarası (§5.3) | ms | RP3β ile eşli kıyas |
| 4 | GF-CF eğitimsiz süzgeç (§3.12) | sn | ek kıyas çizgisi |
| 5 | Sözde liste satırları: kredi + CLAP-kNN + LB (§5.5-2) | ms | liste-yalnız modele göre kazanç |
| 6 | Heterojen PPR (§5.4) | ms | RRF ve 5'e karşı |
| 7 | CLAP→CF ridge eşlemesi + anahtarlamalı melez (§5.5-4/5) | sn | ses yolunun ve kapsama tavanının değişimi |
| 8 | Füzyon ağırlıklarının A/B ile yeniden seçimi (§5.6) | dk | — |
| 9 | Gerçek kararlarla doğrulama: K21 Thompson payı, yeni yolun beğeni oranı (Wilson) | haftalar | ≥ 30 karar/kaynak |

Bu planın hiçbir adımı LLM, ücretli API ya da yeni ağır bağımlılık gerektirmiyor (numpy +
mevcut scipy yeter). K2 ve K8 ile uyumlu.

---

## 8. Kaynaklar

**Doğrulama durumu:** "D" = bu oturumda arama özetiyle doğrulandı (yayın yeri ve temel bulgu).
"†" = aranamadı veya ayrıntısı doğrulanamadı; önceki bilgiye dayanıyor. URL'ler arama
sonuçlarından ya da kanonik DOI/arXiv kimliğinden.

### Temeller

1. Goldberg, D., Nichols, D., Oki, B. M., Terry, D. (1992). Using collaborative filtering to
   weave an information tapestry. *CACM* 35(12):61–70. doi:10.1145/138859.138867. D.
   https://ftp.mirrorservice.org/sites/www.bitsavers.org/pdf/xerox/parc/techReports/CSL-92-10_Using_Collaborative_Filtering_to_Weave_an_Information_Tapestry.pdf
2. Resnick, P., Iacovou, N., Suchak, M., Bergstrom, P., Riedl, J. (1994). GroupLens: An open
   architecture for collaborative filtering of netnews. *CSCW '94*, 175–186. D.
   https://presnick.people.si.umich.edu/papers/cscw94/GroupLens.htm
3. Sarwar, B., Karypis, G., Konstan, J., Riedl, J. (2001). Item-based collaborative filtering
   recommendation algorithms. *WWW '01*, 285–295. doi:10.1145/371920.372071. D.
   https://archives.iw3c2.org/www10/cdrom/papers/519/sdm2.html
4. Linden, G., Smith, B., York, J. (2003). Amazon.com recommendations: Item-to-item
   collaborative filtering. *IEEE Internet Computing* 7(1):76–80. D.
   https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf
5. Koren, Y. (2008). Factorization meets the neighborhood: a multifaceted collaborative
   filtering model. *KDD '08*. † (shrink h ≈ 100). https://doi.org/10.1145/1401890.1401944

### Matris ayrıştırma ve örtük geri bildirim

6. Koren, Y., Bell, R., Volinsky, C. (2009). Matrix factorization techniques for recommender
   systems. *IEEE Computer* 42(8):30–37. doi:10.1109/MC.2009.263. D.
   https://gwern.net/doc/ai/tabular/2009-koren.pdf
7. Hu, Y., Koren, Y., Volinsky, C. (2008). Collaborative filtering for implicit feedback
   datasets. *ICDM '08*, 263–272. D (α ≈ 40 değeri †). https://doi.org/10.1109/ICDM.2008.22
8. Rendle, S., Freudenthaler, C., Gantner, Z., Schmidt-Thieme, L. (2009). BPR: Bayesian
   personalized ranking from implicit feedback. *UAI '09*, PMLR R7:460–469. D.
   https://arxiv.org/abs/1205.2618
9. Rendle, S., Krichene, W., Zhang, L., Koren, Y. (2022). Revisiting the performance of iALS on
   item recommendation benchmarks. *RecSys '22*, 427–435. D.
   https://arxiv.org/abs/2110.14037
10. Rendle, S., Krichene, W., Zhang, L., Anderson, J. (2020). Neural collaborative filtering vs.
    matrix factorization revisited. *RecSys '20*. D. https://arxiv.org/abs/2005.09683
11. Rendle, S., Zhang, L., Koren, Y. (2019). On the difficulty of evaluating baselines. †.
    https://arxiv.org/abs/1905.01395

### Doğrusal ve komşuluk modelleri

12. Ning, X., Karypis, G. (2011). SLIM: Sparse linear methods for top-N recommender systems.
    *ICDM '11*, 497–506. doi:10.1109/ICDM.2011.134. D.
    https://www-users.cse.umn.edu/~ningx005/slides/ICDM2011_slides.pdf
13. Kabbur, S., Ning, X., Karypis, G. (2013). FISM: Factored item similarity models for top-N
    recommender systems. *KDD '13*, 659–667. D.
    https://experts.umn.edu/en/publications/fism-factored-item-similarity-models-for-top-n-recommender-system/
14. Aiolli, F. (2013). Efficient top-N recommendation for very large scale binary rated datasets.
    *RecSys '13*. D (α = 0,15, q = 3). https://www.math.unipd.it/~aiolli/PAPERS/MSD_final.pdf
15. Aiolli, F. (2012). A preliminary study on a recommender system for the Million Songs Dataset
    challenge. D (q taraması). https://www.math.unipd.it/~aiolli/PAPERS/MSDaiolli.pdf
16. Polato, M., Aiolli, F. (2016). Exploiting sparsity to build efficient kernel based
    collaborative filtering for top-N item recommendation. D. https://arxiv.org/abs/1612.05729
17. Steck, H. (2019). Embarrassingly shallow autoencoders for sparse data. *WWW '19*. D (kapalı
    form; λ değerleri †). https://arxiv.org/abs/1905.03375
18. Steck, H. (2020). Autoencoders that don't overfit towards the identity. *NeurIPS '20*. † (URL doğrulanmadı).
19. Steck, H., Garcia Garcia, D. (2021). On the regularization of autoencoders. D (varlık).
    https://arxiv.org/abs/2110.11402
20. Moon, J. ve ark. (2023). It's enough: Relaxing diagonal constraints in linear autoencoders
    for recommendation. *SIGIR '23*. D (varlık; yazar ve yayın yeri †).
    https://arxiv.org/abs/2305.12922
21. (2025). Accurate and diverse recommendations via propensity-weighted linear autoencoders.
    D (varlık; yazarlar okunamadı). https://arxiv.org/abs/2512.20896
22. (2026). Generalizing linear autoencoder recommenders with decoupled expected quadratic loss.
    D (varlık). https://arxiv.org/abs/2603.07402
23. (2026). On the regularization landscape for the linear recommendation models. D (varlık).
    https://arxiv.org/abs/2609.11876

### Rastgele yürüyüşler ve grafikler

24. Cooper, C., Lee, S. H., Radzik, T., Siantos, Y. (2014). Random walks in recommender
    systems: exact computation and simulations. *WWW '14 Companion*.
    doi:10.1145/2567948.2579244. D.
    https://archives.iw3c2.org/www2014/proceedings/companion/p811.pdf
25. Christoffel, F., Paudel, B., Newell, C., Bernstein, A. (2015). Blockbusters and wallflowers:
    Accurate, diverse, and scalable recommendations with random walks. *RecSys '15*.
    doi:10.1145/2792838.2800180. D.
26. Paudel, B., Christoffel, F., Newell, C., Bernstein, A. (2017). Updatable, accurate, diverse,
    and scalable recommendations for interactive applications. *ACM TiiS* 7(1).
    doi:10.1145/2955101. D (DOI; yazar sırası †).
27. (2017). Recommender systems with random walks: A survey. D (varlık; yazarlar okunamadı).
    https://arxiv.org/abs/1711.04101
28. Eksombatchai, C. ve ark. (2018). Pixie: A system for recommending 3+ billion items to 200+
    million users in real-time. *WWW '18*. † (arama bütçesi bitti).
    https://arxiv.org/abs/1711.07601
29. Konstas, I., Stathopoulos, V., Jose, J. M. (2009). On social networks and collaborative
    recommendation. *SIGIR '09*. † (arama bütçesi bitti; URL doğrulanmadı).
30. Wang, X., He, X., Wang, M., Feng, F., Chua, T.-S. (2019). Neural graph collaborative
    filtering. *SIGIR '19*, 165–174. D. https://arxiv.org/abs/1905.08108
31. He, X. ve ark. (2020). LightGCN: Simplifying and powering graph convolution network for
    recommendation. *SIGIR '20*. D. https://arxiv.org/abs/2002.02126
32. Shen, Y. ve ark. (2021). How powerful is graph convolution for recommendation? *CIKM '21*.
    D (formül ayrıntısı †). https://arxiv.org/abs/2108.07567
33. (2023). LightGCN: Evaluated and enhanced. D (varlık; yazarlar okunamadı).
    https://arxiv.org/abs/2312.16183
34. Kwieciński, R. ve ark. (2023). Ilan platformlarında öneri modellerinin kıyası (RP3β, SLIM,
    ALS; çevrimiçi A/B). D (özet; başlık ve yazarlar †). https://arxiv.org/abs/2301.07946

### Tekrarlanabilirlik

35. Ferrari Dacrema, M., Cremonesi, P., Jannach, D. (2019). Are we really making much progress?
    A worrying analysis of recent neural recommendation approaches. *RecSys '19*. D.
    https://arxiv.org/abs/1907.06902 · kod:
    https://github.com/MaurizioFD/RecSys2019_DeepLearning_Evaluation
36. Ferrari Dacrema, M., Boglio, S., Cremonesi, P., Jannach, D. (2021). A troubling analysis of
    reproducibility and progress in recommender systems research. *ACM TOIS* 39(2):20.
    doi:10.1145/3434185. D (ayarlama uzayları †). https://arxiv.org/abs/1911.07698
37. Petrov, A., Macdonald, C. (2022). A systematic review and replicability study of BERT4Rec
    for sequential recommendation. *RecSys '22*. D. https://arxiv.org/abs/2207.07483
38. Klenitskiy, A., Vasilev, A. (2023). Turning dross into gold loss: Is BERT4Rec really better
    than SASRec? *RecSys '23*. D (özet).
39. (2025). Diffusion recommender reproducibility study (SIGIR 2023–2024 difüzyon modelleri). D.
    https://arxiv.org/abs/2505.09364
40. RecRankerEval (ECIR 2026). D.
    https://ecir2026.dryfta.com/programme/abstract-archive/abstract/public/137/recrankereval-a-reproducible-framework-for-deploying-andevaluating-llm-based-top-k-recommenders
41. (2025). Reproducibility study of "XRec: Large language models for explainable
    recommendation". D. https://arxiv.org/abs/2510.06275
42. Klagenfurt Üniversitesi (2026). Reproducibility of LLM-based recommender systems research:
    Worrying observations from an initial analysis. D (varlık). https://zenodo.org/records/19049779
43. Krichene, W., Rendle, S. (2020). On sampled metrics for item recommendation. *KDD '20*. †.
    https://doi.org/10.1145/3394486.3403226

### Ardışık, iki kule, difüzyon, üretici

44. Hidasi, B. ve ark. (2016). Session-based recommendations with recurrent neural networks.
    *ICLR '16*. †. https://arxiv.org/abs/1511.06939
45. Kang, W.-C., McAuley, J. (2018). Self-attentive sequential recommendation. *ICDM '18*. †.
    https://arxiv.org/abs/1808.09781
46. Sun, F. ve ark. (2019). BERT4Rec. *CIKM '19*. †. https://arxiv.org/abs/1904.06690
47. Ludewig, M., Jannach, D. (2018). Evaluation of session-based recommendation algorithms.
    *UMUAI* 28. D. https://arxiv.org/abs/1803.09587
48. Ludewig, M., Mauro, N., Latifi, S., Jannach, D. (2019/2021). Performance comparison of
    neural and non-neural approaches to session-based recommendation / *UMUAI*. D.
    https://link.springer.com/doi/10.1007/s11257-020-09277-1
49. Covington, P., Adams, J., Sargin, E. (2016). Deep neural networks for YouTube
    recommendations. *RecSys '16*. †. https://doi.org/10.1145/2959100.2959190
50. Yi, X. ve ark. (2019). Sampling-bias-corrected neural modeling for large corpus item
    recommendations. *RecSys '19*. D.
    https://research.google/pubs/sampling-bias-corrected-neural-modeling-for-large-corpus-item-recommendations/
51. (2025). Correcting the LogQ correction: Revisiting sampled softmax for large-scale
    retrieval. D. https://arxiv.org/abs/2507.09331
52. Wang, W., Xu, Y., Feng, F., Lin, X., He, X., Chua, T.-S. (2023). Diffusion recommender
    model. *SIGIR '23*. D. https://arxiv.org/abs/2304.04971
53. Lin, J. ve ark. (2024). A survey on diffusion models for recommender systems. D.
    https://arxiv.org/abs/2409.05033
54. Wei & Fang (2025). Diffusion models in recommendation systems: A survey. D.
    https://arxiv.org/abs/2501.10548
55. Rajput, S. ve ark. (2023). Recommender systems with generative retrieval (TIGER).
    *NeurIPS '23*. D. https://arxiv.org/abs/2305.05065
56. Zhai, J. ve ark. (2024). Actions speak louder than words: Trillion-parameter sequential
    transducers for generative recommendations (HSTU). *ICML '24*. † (yalnız NVIDIA özeti D).
    https://arxiv.org/abs/2402.17152

### Müzik ve çalma listesi

57. Zamani, H., Schedl, M., Lamere, P., Chen, C.-W. (2019). An analysis of approaches taken in
    the ACM RecSys Challenge 2018 for automatic music playlist continuation. *ACM TIST*
    10(5):57. doi:10.1145/3344257. D. https://arxiv.org/abs/1810.01520
58. Volkovs, M., Rai, H., Cheng, Z., Wu, G., Lu, Y., Sanner, S. (2018). Two-stage model for
    automatic playlist continuation at scale. *RecSys Challenge '18*. D.
    https://www.cs.toronto.edu/~mvolkovs/recsys2018_challenge.pdf
59. Takım "Latte" (2018). Automatic playlist continuation through a composition of collaborative
    filters. D (12. sıra; yazarlar okunamadı). https://arxiv.org/abs/1808.04288
60. Bendada, W. ve ark. (2023). A scalable framework for automatic playlist continuation on music
    streaming services. *SIGIR/RecSys '23*. D (varlık). https://arxiv.org/abs/2304.09061
61. Bonnin, G., Jannach, D. (2014). Automated generation of music playlists: Survey and
    experiments. *ACM CSUR* 47(2). †. https://doi.org/10.1145/2652481
62. Vall, A., Dorfer, M., Eghbal-zadeh, H., Schedl, M., Burjorjee, K., Widmer, G. (2019).
    Feature-combination hybrid recommender systems for automated music playlist continuation.
    *UMUAI* 29. † (URL doğrulanmadı).
63. van den Oord, A., Dieleman, S., Schrauwen, B. (2013). Deep content-based music
    recommendation. *NeurIPS '13*. † (URL doğrulanmadı).

### Melezleme, içerik ve değerlendirme

64. Jeunen, O., Van Balen, J., Goethals, B. (2020). Closed-form models for collaborative
    filtering with side-information. *RecSys '20 LBR*. † (URL doğrulanmadı; arama bütçesi bitti).
65. Deldjoo, Y., Ferrari Dacrema, M. ve ark. (2019). Movie genome: alleviating new item cold
    start in movie recommendation (CFeCBF). *UMUAI*. † (URL doğrulanmadı).
66. Barkan, O. ve ark. (2019). CB2CF: A neural multiview content-to-collaborative filtering
    model. † (yayın yeri ve URL doğrulanmadı).
67. Volkovs, M., Yu, G., Poutanen, T. (2017). DropoutNet: Addressing cold start in recommender
    systems. *NeurIPS '17*. † (URL doğrulanmadı).
68. Burke, R. (2002). Hybrid recommender systems: Survey and experiments. *UMUAI* 12. †.
    https://doi.org/10.1023/A:1021240730564
69. Schnitzer, D., Flexer, A., Schedl, M., Widmer, G. (2012). Local and global scaling reduce
    hubs in space. *JMLR* 13. †. https://jmlr.org/papers/v13/schnitzer12a.html
70. Cormack, G. V., Clarke, C. L. A., Büttcher, S. (2009). Reciprocal rank fusion outperforms
    Condorcet and individual rank learning methods. *SIGIR '09*. †.
    https://doi.org/10.1145/1571941.1572114
71. Steck, H. (2011). Item popularity and recommendation accuracy. *RecSys '11*. † (URL doğrulanmadı).
72. Steck, H. (2010). Training and testing of recommender systems on data missing not at random.
    *KDD '10*. †. https://doi.org/10.1145/1835804.1835895
