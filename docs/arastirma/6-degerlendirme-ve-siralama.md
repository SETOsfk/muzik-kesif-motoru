# 6 — Çok az veriyle güçlü bir sıralayıcı kurmak ve doğrulamak

*Araştırma raporu · 2026-10-20 · Müzik Keşif Motoru (K2, K8, K19, K21 bağlamında)*

**Yöntem notu.** Bu oturumda 36 web araması yapıldı (RecSys, SIGIR, KDD, CIKM, WWW,
ICML/NeurIPS, JMLR, arXiv). `WebFetch` bu ortamda hiçbir alan adına ulaşamadı (DNS
hatası). Bu yüzden doğrulanan şey birincil metnin kendisi değil; arama motorunun
döndürdüğü özet, künye ve ikincil alıntılar oldu. Paylaşılan arama bütçesi (oturum başına
200) dolunca birkaç klasik kaynak arka plan bilgisinden yazıldı. Kaynakçada
**[D]** bu oturumda aramayla doğrulandı, **[B]** arka plan bilgisi, bu oturumda
doğrulanmadı demek. Ayrıca kod tabanı **okundu ama değiştirilmedi**:
`python/degerlendirme.py`, `python/discover/calma_listesi.py`, `python/discover/adaylar.py`,
`python/kesif.py`, `python/geri_bildirim.py`. Kod okuması bir sızıntı bulgusu
çıkardı (§1.3, S1). Bu bulgu raporun en acil sonucudur.

---

## 0. Yönetici özeti — tek sayfalık tarif

1. **Önce sızıntıyı kapat.** Çalma listeleri, kütüphanedeki **her sanatçının adıyla**
   Deezer'da aranarak toplanmış (`calma_listesi.hasat` → `liste_ara(istemci, sanatci)`,
   `calma_listesi.tohum_sanatci` sütunu). Gizleme sınamasında (LOAO) gizlenen sanatçının
   *kendi adıyla bulunmuş* listeler korpusta kalıyor. Bu durum hem tavanı hem PMI
   sıralamasını yapay olarak şişiriyor. Çevrimdışı ölçümün liste yolunu, gerçek
   kararların ise ses yolunu öne çıkarması kısmen bu sızıntıdan geliyor olabilir. Bu bir
   **hipotez** ve tek bir yeniden koşuyla sınanabilir (§1.3).
2. **Sıralayıcı: koşullu logit.** Model McFadden tipi, *eşleştirilmiş vaka-kontrol*
   biçiminde kurulur: her LOAO sorgusu bir tabaka, gizlenen sanatçı "vaka", havuzdaki
   diğer adaylar "kontrol". Özellikler şunlar: kaynak başına sıra dönüşümü, ham skorlar,
   kanıt sayısı, yokluk göstergeleri, popülerlik ve destekleyen kaynak sayısı. L2 önselinin
   ortalaması **mevcut RRF 1:2'ye eşdeğer ağırlıklara** konur. Böylece model "RRF'den ancak
   veri gerektirdiği kadar sapar". Kestirim numpy ile Newton yöntemiyle yapılır; 5–15
   yineleme yeter.
3. **İç içe LOAO.** Dış döngü 147 sanatçının her birini sırayla gizler. İç döngü kalan 146
   sorguda sanatçıya göre gruplanmış 10-kat çalışır. λ, iç **koşullu log-olabilirlikle**
   ve 1-SE kuralıyla seçilir. Eski motorun ağırlıkları da aynı iç döngüde seçilir; adil
   kıyas için ikisinin ayar bütçesi eşit olmalı (Ferrari Dacrema 2019 dersi).
4. **"Yeni eskisini yener" testi.** Birincil ölçüt **önceden** karar günlüğüne yazılır:
   MRR, 147 sorgunun tamamında, erişilemeyen sanatçıya RR=0. Test, RR farkları üzerinde
   eşleştirilmiş **işaret çevirme permütasyonu** (tohumlu, B=100.000), etki aralığı
   **eşleştirilmiş BCa bootstrap** ile verilir. İkincil ölçütler Holm düzeltmesiyle
   sınanır: recall@10 ve @50 için **kesin McNemar**, yüzdelik sıra için permütasyon.
   **Koruma ölçütü** bir eşdeğersizlik sınamasıdır: ilk-10'un medyan liste görünürlüğü
   (veya ARP@10) belirlenen eşikten fazla artmamalı. Wilcoxon kullanılmaz (Urbano 2019,
   2026).
5. **Çevrimiçi güncelleme.** Çevrimdışı modelin sonsalı **ölçek ve yön ayrıştırılarak**
   aktarılır: η = β₀ + β_eksen + γ·(θ̂_offᵀx) + δᵀx, öncesel olarak γ~N(1, 0.5²) ve
   δ~N(0, τ²I). Kestirim Laplace yaklaşımıyla yapılır. Thompson örneklemesi kaynak
   düzeyinden **model düzeyine** taşınır: deste başına bir θ̃ çekilir. «Zaten biliyorum»
   ayrı bir görev olarak modellenir ve kart değeri **P(bilinmiyor)·P(beğenir | bilinmiyor)**
   olur. Gösterim olasılıkları günlüğe yazılır ve bir ε keşif tabanı tutulur; ileride IPS
   bunlar olmadan yapılamaz.
6. **Deste yeniden sıralayıcısı.** Açgözlü bir amaç kullanılır: MMR (CLAP kosinüs) ile
   Steck kalibrasyonunun (eksen dağılımı üzerinde KL) toplamı. Sert kısıtlar şunlar:
   sanatçı başına tek kart ve her beşinci kart ε-keşif yuvası. RNG
   `SeedSequence([kullanıcı, karar_sayısı, deste_no])` ile kurulur. Python'un `hash()`
   işlevi süreç başına tuzlandığı için **kullanılmaz**.
7. **Çevrimiçi kıyas.** A/B yerine **takım seçmeli serpiştirme** (team-draft interleaving)
   kullanılır. %65'lik bir tercihi %80 güçle görmek yaklaşık 85, %60'lık tercihi
   görmek yaklaşık 194 bağsız kredili karşılaştırma ister (§5.3). Günde 10 kararla bu
   1–3 hafta eder.

---

## 1. Çevrimdışı değerlendirme metodolojisi

### 1.1 Bir-dışarıda-bırak (LOO) ailesi ve LOAO'nun yeri

| Varyant | Gizlenen | Ölçtüğü soru | Bizdeki karşılığı |
|---|---|---|---|
| Son etkileşimi dışarıda bırak | kullanıcının son öğesi | "sıradaki ne" | Yok (zaman damgalı dinleme yok, `plays` boş) |
| Öğeyi dışarıda bırak | tek albüm | aynı sanatçının diğer albümü kütüphanede kalır, kolay | **Kaçınılan şey** (K19) |
| **Grubu dışarıda bırak (LOAO)** | bir sanatçının tüm albümleri | "hiç sahip olmadığım sanatçıyı bulabiliyor muyum" | Şu anki sınama |
| Zamansal | belli bir tarihten sonra eklenenler | geçmişten geleceği tahmin | Önerilen ek sınama (§1.4) |

LOAO istatistiksel olarak **gruplanmış çapraz doğrulamadır**. Grup sanatçıdır, çünkü aynı
sanatçının albümleri birbirinden bağımsız değildir. Bu seçim K19'un mantığıyla tutarlı.

**Ölçütün ayrıştırılması.** Her sorgu için recall@k iki olasılığın çarpımıdır:

  recall@k = P(gizlenen havuzda) × P(sıra ≤ k | havuzda)

Birinci çarpan **kapsama** (tavan), ikincisi **sıralama** kalitesidir. Öğrenilmiş bir
sıralayıcı yalnızca ikinci çarpanı değiştirebilir. Kod iki paydayı zaten raporluyor
(`recall@k` ve `recall@k_eris`). Bu çarpım kimliği raporda açıkça yazılırsa "yanlış işe
yatırım" riski azalır.

**Yüzdelik sıra.** `ozet()` içindeki `medyan_yuzdelik` yalnız *bulunan* sanatçılarda
hesaplanıyor, yani havuzda olmaya koşullu. Hu, Koren ve Volinsky'nin (2008) beklenen
yüzdelik sırasına [B] benzer **koşulsuz** bir sürüm de raporlanmalı: erişilemeyen
sanatçıya yüzdelik 1,0 atanır. Rastgele bir sıralama koşullu sürümde 0,50, koşulsuz
sürümde ise 0,50·tavan + (1−tavan) değerini verir.

### 1.2 Örneklenmiş ölçüt tuzakları (Krichene ve Rendle 2020)

Krichene ve Rendle (KDD 2020, en iyi makale) şunu gösterdi: 100 rastgele negatife karşı
sıralama gibi **örneklenmiş** ölçütler, tam ölçütlerle **tutarsızdır**. Yöntemler arasındaki
göreli sıralamayı koruyamaz, tersine bile çevirebilir. Örneklem çok küçüldükçe her ölçüt
AUC'ye çöker. Yazarların önerisi örneklemeden kaçınmak. Mutlaka örneklenecekse yanlılık
veya ortalama karesel hata ölçütüne göre düzeltme yapılabilir. Rendle'ın (2019) ön
baskısı aynı sonucu daha önce vermişti [D].

**Bize etkisi:**
- Şu an sıralama **tam havuzda** yapılıyor ve bu doğru.
- Eğitimde negatif örneklemek meşrudur (§4.1, McFadden'in alternatif örnekleme özelliği).
  **Değerlendirmede asla örneklenmez.**
- Havuz boyu değişirse recall@k kıyaslanamaz. Kod bunu zaten yazıyor (2.163'ten 4.183
  gömüye çıkıldığında recall@50 düştü ama yüzdelik iyileşti). Kaynakların havuz boyları
  da farklı olduğu için kaynaklar arası kıyas ya yüzdelikle ya da **aynı birleşik havuzu
  yeniden sıralayarak** yapılmalı. Öğrenilmiş sıralayıcı zaten birleşik havuzda çalışır.

### 1.3 Veri sızıntısı (Ji ve ark. 2023) ve projeye özgü denetim listesi

Ji, Sun, Zhang ve Li (TOIS 2023), çevrimdışı değerlendirmede "gelecekten" bilgi sızmasının
modellerin göreli sıralamasını değiştirdiğini gösterdi [D]. Genel ilke şu: **sınama anında
var olmaması gereken her bilgi**, özellik veya havuz kurulurken kullanılmamalı. Kod okumasından
çıkan denetim listesi:

**S1 — Hasat sızıntısı (yeni bulgu, kod okundu).** `calma_listesi.hasat()` kütüphanedeki
her sanatçı için `search/playlist?q=<sanatçı>` çağırıyor, ilk 6 karışık listeyi saklıyor
ve listeyi *ilk bulan* sanatçıyı `tohum_sanatci` sütununa yazıyor. `degerlendirme.pmi_tablosu`
ise **tüm** listeleri kullanıyor: "PMI kütüphaneden bağımsız" diye bir kez hesaplanıyor.
Bu varsayım yanlış, çünkü *korpusun kendisi* kütüphaneye bağlı. Sonuçları:

- (i) Gizlenen sanatçı a'nın havuzda olması, kısmen a'nın adıyla arama yapılmış
  olmasından kaynaklanıyor. Bu yüzden **tavan şişiyor**.
- (ii) "a gibi" aramaların döndürdüğü listeler a'nın eksen komşularıyla dolu. Bu yüzden
  a ile sorgu tohumları arasındaki PMI **şişiyor**.
- (iii) CLAP havuzu (`clap_parca`) aynı listelerin parçalarından kurulu. Ses yolunun
  tavanı da şişiyor, ama sıralaması benzerliğe dayandığı için daha az etkileniyor.
- (iv) Görünürlük/popülerlik değerleri de şişiyor.

Üretimde aday hiçbir zaman "kendi adıyla aranmış" olmaz. Bu sızıntının yönü, LOAO'nun
liste yolunu ses yoluna göre kayırması yönündedir. Bu, gözlenen offline–online gerilimle
tutarlıdır, ama gerilimin tek açıklaması olduğu **kanıtlanmış değildir**.

*Düzeltme.* Doğru karşı-olgusal soru şu: "a kütüphanede olmasaydı hangi listeler toplanırdı?"
Önbellekteki (K5) `search/playlist` yanıtlarından her liste l için tam tohum kümesi
S(l) yeniden kurulur. a katında l ancak S(l)∖{a} ≠ ∅ ise tutulur. Bu yeniden kurulum
yapılamıyorsa yaklaşık kural `tohum_sanatci ≠ a` olur. Yaklaşık kural muhafazakârdır:
a'nın ilk bulduğu ama başkalarının da bulduğu listeler gereksiz yere atılır. Kat başına
PMI tablosu ve CLAP havuzu bu filtreyle yeniden kurulur; ~600 listede bu ucuz bir iş.

*Hipotez sınaması.* Düzeltmeden önce ve sonra liste yolu ile ses yolunun tavanı ve MRR'ı
yan yana raporlanmalı. Liste yolu ses yoluna göre belirgin şekilde düşüyorsa gerilimin
büyük kısmı sızıntıdır.

**S2 — Eksen sızıntısı.** FCM kümeleri gizlenen albümler *dahil* kuruldu
(`eksen_haritasi` gizlemeden önce okunuyor) ve sorgu "gizlenenin ekseni" olarak seçiliyor.
Kullanıcının ekseni kendisinin seçmesi üründe meşru, yani hedef eksenin bilinmesi kabul
edilebilir. Ama eksenin *sınırları* gizlenenin albümleriyle şekillendi. 302 albümde etkinin
küçük olması beklenir. *Duyarlılık sınaması:* 20 rastgele sanatçı için kümeleme gizlemeli
yeniden koşulur, sorgu kümesinin Jaccard benzerliği ve sıra farkları raporlanır.

**S3 — Hiperparametre seçim yanlılığı.** RRF ağırlığı 1:2, `KANIT_BUZULMESI = 1.0`
("süpürülerek seçildi"), `ASGARI_BIRLIKTE`, liste ağırlık şeması ve ses kuralı aynı 147
sorguda seçildi. Bu durumda raporlanan melez sayıları **iyimserdir** (Varma ve Simon
2006; Cawley ve Talbot 2010; §1.9). RRF'nin k=60 değeri dışarıdan sabitlendiği için
(Cormack 2009) bu sorunu taşımıyor.

**S4 — Sabit tutulan yaklaşıklıklar.** `ag_frekans` (bilinçli uzaklık paydası) bir kez
hesaplanıyor ve bu durum kodda yazılı. Sınırlı ama belgeli bir yaklaşıklık.

**S5 — Ses yolu tabanı.** `SesErisimi` hubness tabanını kalan kütüphaneden alıyor. Bu
doğru ve sızıntı yok.

**Sızıntı için genel duman testi (y-permütasyonu).** Her sorguda hedef etiketi havuzdaki
rastgele bir adaya taşınır ve boru hattı (öğrenme dahil) çalıştırılır. Ortaya çıkan MRR,
rastgele beklentiye, yani H_M/M'ye eşit olmalı. Burada H_M harmonik sayı, M havuz boyu.
M=2.000 için beklenti ≈0,0041; M=10.000 için ≈0,0010. Belirgin şekilde üstündeyse boru
hattında bir yerde etiket bilgisi sızıyor demektir. Bu test Varma ve Simon'ın "null veri"
deneyinin bu bağlama uyarlanmış hâlidir.

### 1.4 Zamansal bölme

Spotify parça eklenme tarihleri ve FLAC dosya tarihleri bir zaman ekseni veriyor.
**Zamansal LOAO** şöyle kurulur: en son eklenen %20 sanatçı gizlenir, sorgu yalnız
öncekilerle yapılır. Bu kurgu ürünün gerçek kullanımına, yani "şimdiki kütüphaneden bir
sonraki edinimi tahmin etmeye" en yakın olanıdır ve popülerlik yanlılığını da farklı
biçimde örnekler. n≈30 ile ancak **ikincil kanıt** olur; ana karar ölçütü yapılmamalı.
Ji ve ark. (2023) ayrıca küresel zaman çizelgesinin göz ardı edilmesine karşı uyarıyor.
Bizdeki Deezer hasadı tek bir anlık görüntü, yani bir zamansal iddiada bulunmuyor.

### 1.5 "Gerçekten ilerliyor muyuz?" dersleri (Ferrari Dacrema, Cremonesi, Jannach 2019)

Yazarlar üst konferanslardan 18 sinirsel öneri yöntemini inceledi. İkincil kaynağa göre
yalnızca 7'si yeniden üretilebildi ve bunların 6'sı iyi ayarlanmış basit yöntemlere
yenildi [D, sayılar ikincil kaynaktan]. Bizim için dört kural çıkıyor:

1. **Güçlü, basit tabanlar** her raporda yer alır: (B0) rastgele, (B1) eksen içi
   popülerlik (liste görünürlüğü), (B2) her tek kaynak, (B3) RRF 1:1, (B4) RRF 1:2
   (şu anki).
2. **Eşit ayar bütçesi.** Tabanlar da aynı iç döngüde ayarlanır (§7.d).
3. **Tekrarlanabilirlik.** Tohum, kod sürümü ve veri anlık görüntüsü kimliği her rapora
   yazılır.
4. Ölçüt ve veri **sonradan** seçilmez; birincil ölçüt önceden kaydedilir.

Yeni model B1'i ve en iyi tek kaynağı geçemiyorsa çalışma orada durur.

### 1.6 Rastgele olmayan eksiklik (MNAR) ve popülerlik yanlılığı

- **Steck (KDD 2010)** eksik derecelendirmelerin bilgi taşıdığını, rastgele olmayan
  eksiklik altında top-k isabet oranına yakın bazı ölçütlerin hafif varsayımlarla
  yansız kestirilebildiğini gösterdi [D].
- **Steck (RecSys 2011)** popüler öğelere doğru seçim yanlılığı varsayarak kuyruğa doğru
  kademeli ayarlanabilen bir doğruluk ölçütü tanımladı. Bu ölçüt "neredeyse yansız"
  kestirim veriyor [D]. Kesin üs biçimini birincil metinde doğrulayamadım. Aşağıdaki
  formül genel biçimidir.
- **Cañamares ve Castells (SIGIR 2018, en iyi makale)** popülerliğin işe yaramasını
  derecelendirme, keşif ve alaka değişkenleri arasındaki bağımlılıklarla modelledi.
  Yanlılıktan arındırılmış, kitle kaynaklı bir veri setiyle gösterdi [D].
- **Bellogín, Castells ve Cantador (2017)** seyreklik ve popülerlik yanlılığının
  algoritmaların karşılaştırmasını "ciddi biçimde" değiştirdiğini buldu [D, ikincil].
- **Schnabel ve ark. (ICML 2016)** önerileri bir "tedavi" gibi ele aldı. Eğilim skorunun
  tersiyle ağırlıklandırma (IPS) ve kendi kendini normalleştiren sürümü SNIPS ile yansız
  değerlendirme ve öğrenme önerdi. SNIPS daha düşük varyanslı ama küçük bir yanlılık
  taşıyor [D].

**Bizdeki MNAR yapısı.** Kütüphane kürasyonla kuruldu ve gözlem sürecinin kendisi bu
kürasyon. Sahip olunan sanatçılar bulunabilir, satın alınabilir ve tanınmış sanatçılara
kayık. LOAO hedefleri bu yüzden popülere eğilimli ve popüler sinyal veren kaynak
ödüllendiriliyor. Kodun "belirsizlik ölçümü" yorumu bunu zaten ölçmüş: büzülme
recall@10'u altı katına çıkarırken önerilerin medyan görünürlüğünü 6'dan 8–9'a taşıdı.

**Popülerlik katmanlı recall (genel biçim):**

  recall_β@k = Σ_q w_q · 1[r_q ≤ k] / Σ_q w_q,  w_q ∝ pop(a_q)^(−β)

β=0 olağan recall'u verir; β=0,5 veya β=1 kuyruğa ağırlık verir. pop olarak liste
görünürlüğü kullanılır ve **S1 düzeltilmiş korpustan** hesaplanır. Daha az varsayımlı bir
alternatif, popülerlik tersillerine göre katmanlı raporlamadır (3 × n≈49). İkisi birlikte
verilir.

### 1.7 Küçük n'de istatistiksel anlamlılık

**Alanyazının durumu (tartışmalı):**

- **Smucker, Allan ve Carterette (CIKM 2007):** t-testi, bootstrap ve randomizasyon
  (permütasyon) testleri arasında pratikte fark yok. Wilcoxon ve işaret testi
  randomizasyon testiyle uyumsuz. 2009'daki devam çalışmasına göre konu (sorgu) sayısı
  10'a doğru azaldıkça testler arasındaki uyum azalıyor [D].
- **Urbano, Lima ve Hanjalic (SIGIR 2019):** TREC verisinden yapılmış, 500 milyonun
  üzerinde p-değerli bir simülasyon. Özet slaytlara göre ortalama farkı için **t-testi
  en sağlam**. Wilcoxon ve işaret testinden kaçınılmalı; ortalama dışı istatistikler için
  permütasyon testi düşünülmeli. İşaret testi en güçsüz çıktı [D, özet ve slayt].
- **Parapar ve ark. (2019/2020):** Wilcoxon ve işaret testi daha güçlü bulundu [D].
- **Urbano (arXiv, Nisan 2026), "Stop Using the Wilcoxon Test":** Wilcoxon'un simetri
  varsayımı IR ölçütlerinde ihlal ediliyor ve tip I hata oranı denetimden çıkıyor [D, özet].
- **Ihemelandu ve Ekstrand (2021, 2023, 2024):** RecSys'te istatistiksel çıkarım büyük
  ölçüde eksik. Büyük veride işaret testi ve Wilcoxon kullanılmamalı, etki büyüklüğüne
  bakılmalı. Çoklu karşılaştırmada Benjamini–Yekutieli düzeltmesi Bonferroni'den daha
  güçlü ve hatası düşük çıktı [D].
- **Carterette (TOIS 2012)** ve **Ferro ve ark. (SIGIR 2024)**: çevrimdışı deneylerde
  çoklu sınama düzeltmesi zorunlu [D, künye ve ikincil].

**Bizim veri yapımıza göre seçim:**

| Karşılaştırma | Veri | Test | Neden |
|---|---|---|---|
| MRR farkı (birincil) | sorgu başına RR_yeni − RR_eski (çok sayıda 0) | **eşleştirilmiş işaret çevirme permütasyonu**, t-testiyle çapraz kontrol | ortalama içindir; dağılım varsayımı yok; çok sayıda sıfır ve bağ Wilcoxon'u bozar |
| recall@k farkı | sorgu başına ikili (isabet/ıska) çiftler | **kesin McNemar** (uyumsuz çiftlerde Binom(n_d, ½)) | ikili eşleştirilmiş veri için doğru kesin test |
| Yüzdelik sıra farkı | sürekli, [0,1] | permütasyon (veya t) | ortalama |
| Kazanma oranı | sıra_yeni < sıra_eski olan, bağsız sorgular | işaret testi + Wilson aralığı | yorumu kolay bir etki büyüklüğü |

İşaret çevirme permütasyonunda istatistik T = (1/n)Σ d_q olarak alınır. Her yinelemede
d_q'ların işaretleri ±1 ile rastgele çevrilir. İki taraflı p-değeri şöyle hesaplanır:
p = (1 + #{|T*| ≥ |T|}) / (1 + B). Tam sayım 2¹⁴⁷ olasılık gerektirdiği için Monte Carlo
kullanılır: B = 100.000 yineleme, sabit tohum. Değeri sıfır olan d_q'lar istatistiğe
katkı vermez ama n'de kalır; bu doğru davranış.

**Güç hesabı** (α=0,05 iki taraflı, güç 0,80, normal yaklaşım):

| Senaryo | Tespit edilebilir en küçük etki / gereken n |
|---|---|
| RR farklarının ss'si 0,10 / 0,15 / 0,20 / 0,30, n=147 | MRR'da en küçük fark **0,023 / 0,035 / 0,046 / 0,069** |
| McNemar, uyumsuz çiftlerin %65 / %70 / %75 / %80'i yeni lehine | gereken uyumsuz sorgu sayısı **85 / 47 / 29 / 19** |

Anlamı şu: 147 sorguda recall@10 farkını görmek için *uyumsuz* sorgu sayısının en az
30–50 olması gerekir. İki motor sorguların çoğunda aynı sonucu veriyorsa McNemar'ın gücü
düşüktür. Bu yüzden birincil ölçüt **MRR** olmalı: her sıradaki bilgiyi kullanır.

**Bağımlılık.** Aynı eksendeki sorgular aynı tohumları paylaşır; bu yüzden tam bağımsız
değildirler. Duyarlılık analizi olarak **küme (eksen) bootstrap'ı** yapılır: 12 eksen
yeniden örneklenir, eksen içindeki sorgular birlikte alınır. Küme sayısı az olduğu için
kaba bir analiz ama dürüst bir üst sınır verir.

**Çoklu karşılaştırma.** Tek bir birincil ölçüt seçilir ve düzeltmesiz sınanır. Dört
ikincil ölçüt Holm ile sınanır (aile bazlı hata oranı 0,05). Yöntem varyantlarının
taranması, örneğin λ ızgarası, iç döngüde yapılır ve hipotez testi olarak sayılmaz.

### 1.8 recall@k ve MRR için güven aralıkları

- **Tek sistemin recall@k'sı.** Binom oranıdır. Wilson skor aralığı kullanılır; Brown,
  Cai ve DasGupta (2001) bunu küçük n için önerir [B]. `geri_bildirim.wilson` zaten var.
- **Tek sistemin MRR'ı.** RR dağılımı çok çarpık: çoğu 0, birkaç değer 1. Bu yüzden
  **BCa bootstrap** kullanılır (Efron, [B]), 10.000 yeniden örnek ve sabit tohumla.
  Sakai (2018), standart ve bootstrap aralıkların çoğu IR ölçütünde iyi kapsama verdiğini,
  ama başarım çok düşükken bozulduğunu bildiriyor [D, ikincil]. Bizim MRR'larımız tam o
  düşük bölgede.
- **Fark.** Eşleştirilmiş bootstrap kullanılır: aynı sorgu çifti birlikte yeniden örneklenir.

### 1.9 147 sorguda aşırı uymadan hiperparametre seçmek

- **Varma ve Simon (2006):** CV ile ayarlanmış bir sınıflayıcının CV hatasını raporlamak
  ciddi biçimde yanlıdır. Null veri setlerinin %38'inde SVM'nin tahmini hatası %30'un
  altına düştü, oysa bağımsız sınamada başarım şanstan iyi değildi. **İç içe CV**
  neredeyse yansız [D].
- **Cawley ve Talbot (JMLR 2010):** Model seçim ölçütünün **varyansı** yanlılığı kadar
  önemli. Yüksek varyanslı bir ölçüt seçim aşamasında aşırı uyuma yol açıyor ve bunun
  bedeli algoritmalar arasındaki farklar kadar büyük olabiliyor. Bayesçi kanıtı
  maksimize etmek de aynı riske açık [D].

**Uygulamaya dönük üç sonuç:**

1. Dış döngü 147 sanatçı üzerinde LOAO, iç döngü sanatçıya göre gruplanmış 10-kat.
2. İç seçim ölçütü olarak recall@10 gibi basamak biçimli, yüksek varyanslı bir ölçüt
   yerine **koşullu log-olabilirlik** kullanılır; bu ölçüt düzgün ve düşük varyanslı.
3. **1-SE kuralı** uygulanır [B: Hastie, Tibshirani ve Friedman]. En iyi değere bir
   standart hata yakınlıktaki en basit model seçilir; burada en basit model en büyük
   λ'dır, yani RRF önseline en yakın olan.

Izgara küçük tutulur: λ için 7 değer ve 2 özellik kümesi.

---

## 2. Doğruluğun ötesindeki ölçütler

Kaminskas ve Bridge (ACM TiiS 2016/17), çeşitlilik, beklenmediklik (serendipity), yenilik
ve kapsama hedeflerini derleyip yeniden sıralama yöntemlerinin bu hedefler arasındaki
ödünleşimlerini ölçtü [D]. Aşağıdaki tabloda **e_i** CLAP sanatçı merkezidir (birim
vektör), **pop(i)** liste görünürlüğüdür (i'yi içeren liste sayısı), **N_L** toplam
liste sayısıdır.

| Ölçüt | Tanım | Kaynak | Bizde |
|---|---|---|---|
| Yenilik (öz-bilgi) | nov(i) = −log₂(pop(i)/N_L), listede ortalama | Zhou ve ark. 2010 [B]; Vargas ve Castells 2011 çerçevesi [D] | Her raporda ilk-10'un ortalaması |
| EPC (beklenen popülerlik tümleyeni) | EPC@k = C·Σ_{n≤k} disc(n)·rel(i_n)·(1 − p(görülmüş \| i_n)) | Vargas ve Castells 2011 [D] (formül [B]) | Çevrimiçi: rel = beğendim, p(görülmüş) = P(biliyorum) |
| Liste içi çeşitlilik (ILD) | ILD = 2/(k(k−1))·Σ_{i<j}(1 − cos(e_i, e_j)) | Ziegler ve ark. 2005 (liste içi benzerlik) [D] | Deste ve ilk-10 için |
| Beklenmediklik | Önerinin bir **ilkel öneri sisteminin** (popülerlik) ilk-k'sında olmaması | Ge, Delgado-Battenfeld ve Jannach 2010 [D] | UNEXP = ilk-k ∖ B1'in ilk-k'sı |
| Serendipity | \|UNEXP ∩ YARARLI\| / k | Ge ve ark. 2010 [D] | LOAO'da "beklenmedik isabet": gizlenen bulundu **ve** B1'in ilk-k'sında değildi |
| Kapsama | Toplam çeşitlilik: tüm sorguların ilk-k listelerindeki tekil sanatçı sayısı; maruziyet Gini'si | Ge ve ark. 2010 [D]; Fleder ve Hosanagar 2009 [B] | 147 sorgu × ilk-10 |
| ARP | Önerilen öğelerin ortalama popülerliği | Abdollahpouri, Burke ve Mobasher 2019 [D] | Ortalama görünürlük |
| APLT / ACLT | Uzun kuyruk öğelerinin listedeki ortalama payı ve kapsanması | Abdollahpouri ve ark. 2019 [D] | Kuyruk: kümülatif görünürlüğün alt %80'i |
| Kalibrasyon hatası | C_KL(p‖q̃) = Σ_g p(g)·log(p(g)/q̃(g)) | Steck 2018 [D, ikincil] | g = eksen (FCM yumuşak üyelik) |

APLT'nin bilinen bir zaafı var: herkese aynı kuyruk öğeleri önerilse bile yüksek
çıkabiliyor. Abdollahpouri ve ark. bu yüzden ACLT'yi tanımladı. Biz de ikisini birlikte
raporlamalıyız.

**Raporlama kuralı:** her yöntem değişikliğinde doğruluk (MRR, recall) ile en az bir
yenilik/popülerlik ölçütü (ARP@10 veya yenilik@10) ve ILD@10 **yan yana** verilir. Kod
bunu medyan görünürlükle zaten kısmen yapıyor. Kullanıcının asıl ölçütü "hiç duymadığım
sanatçı" olduğu için popülerlik bir **koruma ölçütü**dür, süs değil.

---

## 3. Skor ve sıra füzyonu

- **CombSUM ve CombMNZ (Fox ve Shaw 1994, TREC-2):** CombSUM(d) = Σ_s ŝ_s(d).
  CombMNZ(d) = |{s : d ∈ R_s}| · CombSUM(d). İkisi de skorların önceden normalleştirilmesini
  gerektirir [D, ikincil].
- **Normalleştirme yöntemleri:** min–max ile [0,1] aralığına çekme (Lee 1997) [D, ikincil].
  Dağılım temelli normalleştirme (Montague ve Aslam 2001), standart tekniklerin aykırı
  değerlere bağımlılığını sorun olarak gösteriyor [D]. Condorcet-fuse (Montague ve Aslam
  2002) Borda'yı geçiyor [D].
- **RRF (Cormack, Clarke ve Büttcher, SIGIR 2009):** skor(d) = Σ_s 1/(k + r_s(d)).
  k=60 pilot bir çalışmada sabitlendi ve sonra hiç değiştirilmedi. TREC deneylerinde ve
  LETOR 3'te Condorcet'yi ve tek tek sistemleri geçti [D].
- **Bruch, Gai ve Ingber (TOIS 2023):** Ayarlanmış dışbükey birleşim (convex combination)
  hem alan içinde hem alan dışında RRF'yi geçiyor. RRF parametrelerine duyarlı. Dışbükey
  birleşim tek parametreli olduğu için **çok az eğitim örneğiyle** ayarlanabiliyor ve
  normalleştirme seçimine görece duyarsız [D].

**RRF ne zaman kazanır?**
- Etiketli veri yoksa.
- Skor ölçekleri kıyaslanamıyorsa ve dağılımlar ağır kuyrukluysa. Bizim npmi değerleri
  [−1, 1], hubness düzeltmeli CLAP değerleri kabaca [−0,35, 0] aralığında (`adaylar.py`'deki
  belgeye göre).
- Çok sayıda zayıf ve gürültülü sistem varsa.
- Skor büyüklüklerine güvenilemiyorsa.

**Öğrenilmiş füzyon ne zaman kazanır?**
- Az da olsa etiketli sorgu varsa. Bizde 147 sorgu var, sızıntı düzeltmesinden sonra
  ~100+ erişilebilir.
- Skorlar sıranın ötesinde bilgi taşıyorsa. Örnekler: npmi'nin kanıt sayısı, CLAP'te
  birinci ile ikinci aday arasındaki fark, kredi sıçramasının atlama sayısı.
- Bir kaynakta **yok olmak** kendi başına bilgi taşıyorsa. RRF yokluğu "katkı 0" diye
  işler; öğrenilmiş model yokluğun değerini ayrıca öğrenebilir.

**Önemli gözlem:** ağırlıklı RRF, f_s = 1/(k + r_s) özelliklerinde **doğrusal bir
modeldir**. Bu yüzden §4'teki öğrenilmiş sıralayıcı RRF'yi özel durum olarak içerir. Önsel
ortalamasını RRF ağırlıklarına koymak "RRF'ye doğru büzme" demektir ve hipotez doğrudan
sınanabilir hâle gelir: veri RRF'den sapmayı haklı çıkarıyor mu?

---

## 4. Çok az veriden sıralayıcı öğrenmek

### 4.1 Problemin kurgusu: LOAO, eşleştirilmiş bir vaka-kontrol tasarımıdır

Her sorgu q (gizlenen sanatçı a_q) bir aday kümesi C_q üretir. Bu küme, gizleme sonrası
tüm kaynak havuzlarının birleşimidir. C_q içinde **tek bir pozitif** vardır, o da a_q'dur
(havuzdaysa). Bu yapı epidemiyolojideki **1:M eşleştirilmiş vaka-kontrol** tasarımıyla
aynıdır. Ders kitabındaki kestirici **koşullu lojistik regresyon** (Breslow ve Day [B]),
ekonometrideki adı **koşullu logit** (McFadden 1974 [B]):

  P(seçilen = i | C_q) = exp(θᵀx_qi) / Σ_{j∈C_q} exp(θᵀx_qj)

  ℓ(θ) = Σ_q [ θᵀx_{q,a_q} − log Σ_{j∈C_q} exp(θᵀx_qj) ]

**Neden noktasal lojistik regresyon değil?**
- Koşullu olabilirlik sorguya özgü sabitleri (havuz boyu, eksen büyüklüğü, temel oran)
  **kendiliğinden yok eder**. Sorgu içinde sabit olan her özellik düşer; istatistikçinin
  "rahatsız edici parametreyi koşullayarak yok et" argümanı.
- Model, ListNet'in "ilk sıra olasılığı" kaybının birebir aynısıdır (Cao ve ark. 2007 [B]).
  Yani **listesel** bir sıralama kaybını en çok olabilirlikle kestiriyoruz.
- **Alternatif örnekleme:** McFadden (1978) [B], bağımsız alternatifler (IIA) varsayımı
  altında rastgele bir alternatif alt kümesiyle kestirimin tutarlı olduğunu gösterdi.
  Hız gerekirse eğitimde sorgu başına 500 negatif örneklenebilir. **Değerlendirmede
  örneklenmez** (§1.2).

**Erişilemeyen sorgular** (a_q ∉ C_q) olabilirliğe katkı vermez ve eğitimden çıkar.
Bunlar sıralama değil kapsama sorunudur; değerlendirmede ise RR=0 ile kalırlar.

### 4.2 Diğer seçenekler ve neden ikinci planda kalıyorlar

- **BPR (Rendle ve ark., UAI 2009):** σ(θᵀ(x_pos − x_neg)) üzerinde en büyük sonsal
  kestirim; örnekleme ve SGD ile [D]. Bizim kurguda bu, *özellik farkları* üzerinde bir
  lojistik regresyon demektir. Koşullu logit aynı bilgiyi örnekleme gürültüsü olmadan,
  Newton yöntemiyle ve kapalı biçimli bir Hessian'la kullanıyor.
- **RankSVM (Joachims 2002) [B]:** çiftsel menteşe kaybı. Olasılık çıktısı vermediği için
  §4.6'daki çevrimiçi aktarım için uygun değil.
- **LambdaMART (Burges 2010):** NDCG gibi düzgün olmayan ölçütleri ağaçlarla optimize
  ediyor ve Yahoo LTR 2010'da birinci oldu [D]. ~100 pozitifle **ağaç topluluklarının
  varyansı çok yüksek**; önerilmez. Ancak derinlik 1–2, güçlü büzülme ve iç içe CV ile bir
  "kontrol" olarak denenebilir.
- **Ölçütü doğrudan optimize eden koordinat yükselişi (Metzler ve Croft 2007) [B]:**
  az sayıda özellikte MRR'ı doğrudan maksimize ediyor. Ölçüt düzgün olmadığı için
  aşırı uyuma açık. Ancak çapraz kontrol olarak kullanılmalı.

### 4.3 Özellikler (x_qj)

Bütün özellikler **kat içinde** standartlaştırılır: ortalama ve ss yalnız eğitim katından
alınır.

| # | Özellik | Dönüşüm | Not |
|---|---|---|---|
| f1 | PMI sırası | 1/(60 + r_pmi), yoksa 0 | RRF ile aynı dil |
| m1 | PMI'da yok | gösterge | Yokluk bilgisi |
| f2 | npmi (büzülmüş, en büyük) | ham | Kanıtın büyüklüğü |
| f3 | Birliktelik kanıtı | log(1 + n_birlikte) | Büzülmenin yerini alabilir |
| f4 | CLAP sırası | 1/(60 + r_ses), yoksa 0 | |
| m2 | CLAP'te yok | gösterge | |
| f5 | Düzeltilmiş CLAP benzerliği (en büyük) | ham | |
| f6 | Kredi sıçraması | 1[h=1], 1[h=2] | Yoksa ikisi de 0 |
| f7 | ListenBrainz benzerliği | ham, yoksa 0 + gösterge | |
| f8 | Popülerlik | log(1 + görünürlük) | **"Uydururken var, puanlarken yok"** (§4.5) |
| f9 | Destekleyen kaynak sayısı | tamsayı | m'lerle doğrusal bağımlı; m'lerden biri atılır |

Kabaca kural şu: parametre başına 10–20 olay (EPV; Peduzzi 1996, Riley ve ark.'ın
eleştirisiyle birlikte [B]). ~100–120 erişilebilir sorgu için d ≤ 8–10 hedeflenir. Daha
fazlası ancak büzülmeyle taşınabilir. Etkileşimler en fazla bir tane tutulur (f1×f4,
"iki kaynak hemfikir").

### 4.4 Bayesçi lojistik ve bilgilendirici önseller

**Önsel.** θ ~ N(μ, Λ⁻¹), Λ = λ·I.
- **μ = μ_RRF**: standartlaştırılmış f1 ve f4 uzayında 1:2 RRF'yi yeniden üreten
  katsayılar, diğer katsayılar 0. Böylece λ → ∞ iken model tam olarak şu anki melez olur.
- **Gelman ve ark. (2008):** ikili olmayan girdiler yeniden ölçeklenir ve katsayılara
  bağımsız Student-t önseli konur. Önerilen varsayılan, ölçeği 2,5 olan Cauchy. Bu önsel
  **tam ayrışmada bile** kestirim verir. Çapraz doğrulamada Gauss ve Laplace önsellerini
  geçti [D].
- Bizde ayrışma riski gerçek: örneğin gizlenen sanatçı her zaman PMI havuzunda
  çıkıyorsa m1 göstergesi tam ayrışma yaratır ve en çok olabilirlik kestirimi sonsuza
  kaçar. Gauss önseli bu sorunu zaten çözer. Firth'in cezalı olabilirliği (1993) [B]
  bir alternatif.

**Kestirim (MAP, Newton) ve Laplace yaklaşımı.** Gradyan ve negatif Hessian kapalı
biçimdedir:

  g(θ) = Σ_q w_q (x_{q,a_q} − x̄_q) − Λ(θ − μ),  x̄_q = Σ_j p_qj·x_qj

  H(θ) = Σ_q w_q [ Σ_j p_qj·x_qj·x_qjᵀ − x̄_q·x̄_qᵀ ] + Λ   (pozitif tanımlı)

  θ ← θ + H⁻¹·g;  sonsal ≈ N(θ̂, H(θ̂)⁻¹)

Burada w_q sorgu ağırlığıdır (§4.5); varsayılan değeri 1.

**Laplace kanıtıyla λ seçimi** de mümkün:
log p(D|λ) ≈ ℓ(θ̂) − ½(θ̂−μ)ᵀΛ(θ̂−μ) + ½log|Λ| − ½log|H|. Ancak Cawley ve Talbot kanıt
maksimizasyonunun da seçim aşamasında aşırı uyduğunu söylüyor. Asıl yol iç içe CV
olmalı; kanıt yalnız çapraz kontrol için kullanılır.

### 4.5 Pozitif–etiketsiz öğrenme ve MNAR

**Elkan ve Noto (KDD 2008):** Etiketli örnekler pozitiflerin *rastgele* bir alt kümesiyse
(SCAR varsayımı), pozitif ve etiketsiz veriyle eğitilmiş bir sınıflayıcının olasılıkları
gerçek koşullu olasılıklardan **sabit bir çarpanla** farklıdır [D]. Bunun sıralama için
anlamı önemli: SCAR altında **sıralama korunur**. LOAO'daki "negatiflerin" bir kısmının
aslında beğenilecek sanatçılar olması (K19'un kabul ettiği MNAR) sinyali zayıflatır, ama
SCAR geçerliyse θ'nın yönünü bozmaz. Bekker ve Davis (2020) bu alanın taramasıdır [B].

**SCAR bizde ihlal ediliyor.** Sahip olunan sanatçılar, beğenilen ama sahip olunmayan
sanatçılardan daha popüler. Bu ihlal popülerlik katsayısını şişirir. Üç çare var:

1. **Sorgu ağırlığı:** w_q ∝ pop(a_q)^(−β), §1.6'daki popülerlik katmanlı recall'un
   eğitimdeki karşılığı. β önceden sabitlenir (ör. 0,5) ve sonuçlar β ∈ {0; 0,5; 1}
   için duyarlılık olarak verilir.
2. **"Uydururken var, puanlarken yok":** popülerlik (f8) uyum sırasında modele girer ki
   seçim etkisini "açıklasın"; puanlama sırasında katsayısı 0'a veya kullanıcının seçtiği
   bir değere çekilir. Karıştırıcıya göre ayarlayıp sonra müdahale etme mantığıdır. Zhang
   ve ark. (SIGIR 2021, PDA) aynı fikrin nedensel çerçevesi [B].
3. **Popülerlik katsayısını çevrimiçi kararlardan öğrenmek.** Çevrimiçi kararlarda
   sahiplik seçimi yok, deste kartlarını sistem seçiyor. Bu yüzden popülerliğin
   *beğeniye* etkisi orada tanımlanabilir (identified) hâldedir. Çevrimiçi modelde f8'in
   önseli **geniş** tutulur (§4.6).

### 4.6 Çevrimdışı sahte etiketlerle çevrimiçi açık kararları birleştirmek

İki farklı olabilirlik var:
- **Çevrimdışı (koşullu logit):** "hangi aday sahiplik seçimi?"
- **Çevrimiçi (Bernoulli):** "gösterilen kart beğenildi mi?"

Sonuçlar farklı ama "zevk" yönü ortak. Ölçekler de karşılaştırılamaz: |C| aday arasında
seçim logiti ile tek kart logiti aynı ölçekte değil. Bu yüzden **yön ve ölçek ayrıştırılarak**
kısmi havuzlama yapılır:

  η_t = β₀ + β_{eksen(t)} + γ·(θ̂_offᵀ x_t) + δᵀx_t

  β₀ ~ N(logit 0,3; 1,5²),  β_eksen ~ N(0, σ_e²) [eksenler arası kısmi havuzlama],
  γ ~ N(1; 0,5²),  δ ~ N(0, τ²I) (τ ≈ 0,3, popülerlik koordinatında τ_pop ≈ 1)

- γ şu soruyu yanıtlar: "çevrimdışı yön çevrimiçinde ne kadar geçerli?" γ ≈ 0 ise
  çevrimdışı sinyal yanıltıcıdır. Bu, offline–online gerilimi **doğrudan ölçen tek bir
  sayıdır**.
- δ, yönden sapmalara izin verir.

Bu yapı, güç önseli fikrinin (Ibrahim ve Chen 2000 [B]) ölçek uyumsuzluğuna dayanıklı bir
biçimidir. Güç önselinin klasik hâli p(θ | D_on) ∝ L_on(θ)·L_off(θ)^{a₀}·π₀(θ) ≈
L_on(θ)·N(θ; θ̂_off, (a₀·H_off)⁻¹) olarak yazılır. Kısmi havuzlamanın genel çerçevesi
Gelman ve Hill (2007) [B].

**«Zaten biliyorum» ayrı bir görevdir.**
- Zevk olabilirliğine girmez. Bu, projenin "zevk isabeti" tanımıyla tutarlı.
- Ayrı bir lojistik model kurulur: P(biliyor | x). Ağırlıklı olarak popülerlik ve kaynak
  özelliklerine dayanır.
- Kartın değeri, **beklenen yeni beğeni** olarak tanımlanır:

  değer_i = P(bilinmiyor | x_i) · P(beğenir | x_i, bilinmiyor)

Bu tanım "hiç duymadığım ve seveceğim" ölçütünün doğrudan matematiksel karşılığı.

**Seçim yanlılığı.** Çevrimiçi kartlar politikanın seçtiği kartlar ve seçim x'e (ve Thompson
çekilişinin rastgeleliğine) bağlı. **Gözlenen değişkenlere göre seçim** altında, doğru
belirlenmiş bir koşullu model P(y|x) için ağırlıklandırma gerekmez. IPS, *politika
değerini* kestirmek için gereklidir (§5.4). Model yanlış belirlenmişse bu bir ortak
değişken kayması (covariate shift; Shimodaira 2000 [B]) sorunudur. n=150'de önem
ağırlıklandırmanın varyansı kazancını yer; önerilmez.

---

## 5. Kaydırma geri bildiriminden çevrimiçi öğrenme

### 5.1 Mevcut Beta–Bernoulli Thompson örneklemesi (K21)

Russo ve ark. (2018) Thompson örneklemesinin standart başvuru kaynağı [D]. Şu anki
uygulamanın sınırları:

- **(i) Kol öğe değil, kaynak.** Aynı kaynak farklı eksenlerde farklı başarım gösterebilir;
  kaynak ile eksen karışıyor.
- **(ii) Durağanlık yok.** Kaynaklar iyileştikçe (S1 düzeltmesi, yeni özellikler) eski
  kararlar bayatlar.
- **(iii) Amaç uyumsuzluğu.** TS pişmanlığı (regret) en aza indirir. Asıl istenen "hangi
  kaynak daha iyi"yi **belirlemek**se, en iyi kolu belirlemeye yönelik "ilk iki" TS
  (top-two TS; Russo 2016 [B]) daha uygun.
- **(iv) Doğru yapılan:** «biliyorum» kararları paydadan çıkarılıyor.

**Küçük n'de ne söylenebilir?** Aşağıdaki sayılar *gerçek değil, örnektir*:

| Örnek | Wilson %95 aralığı |
|---|---|
| Ses yolu: 4/6 beğeni | [0,30, 0,90] |
| Liste yolu: 1/9 beğeni | [0,02, 0,44] |

Beta(5,3) ve Beta(2,9) sonsallarıyla P(θ_ses > θ_liste) ≈ 0,98. Bu "sesin daha iyi
olduğuna" dair güçlü bir *sonsal inanç* demektir. Ama bu inanç sanatçı/kaynak düzeyinde
bağımsızlık varsayımına ve tek bir kullanıcıya dayanıyor; genellenebilir bir sonuç değil.

**Gereken karar sayısı** (iki oran, α=0,05, güç 0,80):

| Beğeni oranları | Kol başına gereken karar | Günde 10 kararla |
|---|---|---|
| 0,45 ve 0,30 | ≈162 | 1 aydan fazla |
| 0,50 ve 0,30 | ≈93 | |
| 0,60 ve 0,30 | ≈42 | |
| 0,67 ve 0,11 (gözlenen fark gerçekse) | ≈11 | Zaten görünür olurdu |

### 5.2 Bağlamsal haydutlar (contextual bandits)

- **LinUCB (Li, Chu, Langford ve Schapire, WWW 2010):** sırt regresyonuyla bir üst güven
  sınırı hesaplar. Yahoo verisinde bağlamsız haydutlara göre %12,5 tıklama artışı sağladı
  ve **veri azken avantajı daha büyüktü** [D].
- **Doğrusal TS (Agrawal ve Goyal, ICML 2013):** Gauss önsel ve olabilirlikle,
  Õ(d^{3/2}√T) pişmanlık sınırı [D].
- **Lojistik TS için Laplace yaklaşımı:** Chapelle ve Li (NIPS 2011) reklam tıklamalarında
  sonsalı Gauss ile yaklaştırdı (ikincil kaynağa göre köşegen kovaryansla) ve TS'nin
  rekabetçi olduğunu gösterdi [D]. Russo ve ark. (2018, §5.3) genel Laplace formüllerini
  veriyor [D].

**Bize uyarlanması.** Kaynak seçimi yerine **aday düzeyinde** skor kullanılır. Her deste
kurulurken (tohumlu) bir φ̃ ~ N(φ̂, H⁻¹) çekilir. φ = (β₀, β_eksen, γ, δ) parametre
vektörüdür. Skorlar φ̃ ile hesaplanır. Kaynak TS'si bu yapının özel bir durumudur: özellik
olarak yalnız kaynak göstergeleri alınırsa ona indirgenir. d≈10 olduğu için tam kovaryans
kullanılır; köşegene gerek yok. Her karardan sonra sıcak başlangıçlı bir Newton adımı
O(d³) maliyetlidir, yani ihmal edilebilir. Çevrimdışı önsel olmadan 10 karar/gün yetersiz
kalırdı; önsel sayesinde yeterli.

### 5.3 Düello haydutları ve serpiştirme (interleaving)

- **Radlinski, Kurup ve Joachims (CIKM 2008):** arXiv arama motorunda denenen sekiz mutlak
  kullanım ölçütünün (tıklama sayısı, sorgu yeniden yazımı, terk etme…) hiçbiri, ele
  alınan örneklem büyüklüklerinde kaliteyi güvenilir biçimde yansıtmadı. Serpiştirmeye
  dayalı eşleştirilmiş karşılaştırmalar (dengeli ve **takım seçmeli**) ise doğru ve
  tutarlı çıktı [D].
- **Chapelle, Joachims, Radlinski ve Yue (TOIS 2012):** iki ticari arama motorunda büyük
  ölçekli doğrulama; serpiştirmenin istatistiksel verimliliği ve varyantları [D].
- Düello haydutları (Yue ve Joachims 2009) ile çoklu serpiştirme (multileaving; Schuth ve
  ark. 2014) bu yaklaşımın genellemeleridir [B].

**Desteye uyarlama (takım seçmeli serpiştirme):** A ve B iki sıralayıcı.
1. Her turda yazı–tura atılır ve önce kimin seçeceği belirlenir. İki taraf sırayla kendi
   sırasında henüz destede olmayan en üst kartı ekler. Her kart hangi takımdan geldiğini
   taşır.
2. «Beğendim» kararı kartın takımına +1 kredi yazar. «Tutmadı» kredi yazmaz. «Biliyorum»
   bağ sayılır.
3. **Oturum (deste) düzeyinde** kazanan belirlenir, çünkü aynı destedeki kartlar
   bağımsız değil. Kazananlar işaret testiyle sınanır.

**Güç hesabı** (bağsız oturum sayısı, α=0,05, güç 0,80):

| B lehine tercih payı | %55 | %60 | %65 | %70 | %75 |
|---|---|---|---|---|---|
| Gereken bağsız oturum | ≈783 | ≈194 | ≈85 | ≈47 | ≈29 |

**Erken durma (optional stopping) tuzağı.** p-değerine sürekli bakıp anlamlı çıktığı anda
durmak tip I hatayı şişirir. Çare: n önceden sabitlenir, ya da her zaman geçerli p-değeri
(Johari ve ark. 2017 [B]) veya önceden yazılmış bir Bayesçi karar eşiği kullanılır. Örnek
eşik: P(p_B > 0,5 | veri) > 0,95 **ve** n ≥ 30.

### 5.4 Politika dışı değerlendirme (OPE)

- **Yeniden oynatma (replay; Li, Chu, Langford ve Wang, WSDM 2011):** rastgele toplanmış
  günlüklerle bir politikayı yansız değerlendirir [D].
- **IPS ve SNIPS (Schnabel ve ark. 2016)** [D]. Çift sağlamlı (doubly robust) kestirici
  için Dudík, Langford ve Li (2011) [B].

**Ön koşul: gösterim olasılığı günlüğe yazılmalı.**
- Kaynak TS'sinde bu olasılık Monte Carlo ile hesaplanabilir: 1.000 Beta çekilişinde her
  kaynağın kazanma sıklığı.
- Model düzeyinde TS'de M çekilişte kartın desteye girme sıklığı kullanılır.
- Olasılığın **ε tabanı** olmadan, örneğin kartların %10'u ilk-200'den tekdüze seçilmezse,
  IPS ağırlıkları patlar.

150 kararla OPE ancak kaba bir sağlık kontrolüdür. Asıl kıyas aracı serpiştirmedir.

### 5.5 Günde ~10 kararla neler yapılabilir?

| Yöntem | Uygulanabilir mi? | Not |
|---|---|---|
| Beta–Bernoulli TS (kaynak) | Evet (mevcut) | Gözlenen fark büyükse ~11–40 karar/kol yeter |
| Laplace lojistik TS + çevrimdışı önsel | **Evet, önerilen** | d≈10; önsel sayesinde soğuk başlangıç yok |
| LinUCB | Evet ama gereksiz | TS zaten belirsizliği taşıyor |
| Takım seçmeli serpiştirme | **Evet, A/B'nin yerine** | 85–200 bağsız oturum, 1–3 hafta |
| Çoklu serpiştirme | Sınırlı | 3+ sıralayıcıda oturum başına kredi seyrekleşir |
| IPS / DR ile OPE | Yalnız kaba | ε tabanı ve olasılık günlüğü şart |
| Düello haydutu ile kol ayıklama | Hayır | Çok sayıda düello ister |

---

## 6. Deste için yeniden sıralama

- **MMR (Carbonell ve Goldstein, SIGIR 1998):** alaka ile yeniliği dengeler [D]:

  i* = argmax_{i ∈ R∖S} [ λ·rel(i) − (1−λ)·max_{j∈S} sim(i, j) ]

- **DPP:** Çekirdek L = Diag(q)·S·Diag(q), q_i = exp(α·r_i), S_ij = cos(e_i, e_j).
  En olası alt kümeyi bulmak NP-zor. Chen, Zhang ve Zhou (NeurIPS 2018) açgözlü
  yaklaşımı hızlandırdı: saf O(M⁵) yerine O(M³). Daha iyi bir alaka–çeşitlilik ödünleşimi
  ve çevrimiçi A/B doğrulaması da bildirdiler [D]. Wilhelm ve ark. (CIKM 2018) YouTube'da
  sıralama ile politika katmanı arasına bir DPP katmanı koydu [D, ikincil]. Bizde deste
  ≤50 kart ve havuz ≤2.000 olduğu için artımlı Cholesky'li saf açgözlü yöntem yeter.
- **xQuAD (Santos, Macdonald ve Ounis, WWW 2010; ailesi):**
  skor(i | S) = (1−λ)·P(i|q) + λ·Σ_a P(a|q)·P(i|a)·Π_{j∈S}(1 − P(j|a)) [D, ikincil].
  Abdollahpouri ve ark. (2019) "yönler" yerine popüler ve uzun kuyruk gruplarını koyup
  popülerlik yanlılığını yönetti [D]. Bizde yönler eksenlerdir; P(i|a), FCM'den gelen
  eksen üyeliği.
- **Kalibrasyon (Steck, RecSys 2018):**
  - p(g|u): kullanıcının profilindeki g dağılımı. Bizde kullanıcının seçtiği eksen
    karışımı veya kütüphanenin ortalama FCM üyeliği.
  - q(g|L): listedeki dağılım. q̃ = (1−α)q + αp, α ≈ 0,01; bu karışım KL'nin sonsuza
    kaçmasını önler.
  - Amaç: L* = argmax (1−λ)·Σ_{i∈L} s(i) − λ·C_KL(p, q̃(L)). Çözüm açgözlü.
  - Seymen ve ark. açgözlü çözümün miyop olduğunu söyleyip karışık tamsayılı programlama
    önerdi [D, ikincil]. 50 kartlık bir destede açgözlü yöntem yeterli.

**"Eksenler arası kalibrasyon"un iki anlamı var; ikisi de gerekli.**
1. **Dağılım kalibrasyonu** (Steck): destedeki eksen payları hedef dağılıma uysun.
2. **Olasılık kalibrasyonu**: farklı eksenlerden gelen skorlar aynı ölçekte olsun.
   Eksen sabitli tek bir model (§4.6, β_eksen) bunu yapısal olarak sağlar. Eksen başına
   Platt veya izotonik kalibrasyon ancak n büyüyünce, hiyerarşik büzmeyle yapılır.

**Tekrarlanabilirlik:**
- Açgözlü adımlar deterministik olmalı. Bağlar sabit bir anahtarla (sanatçı anahtarı)
  çözülür.
- Sıralamada `np.argsort(kind="stable")` kullanılır. Skorlar karşılaştırmadan önce
  1e-12'ye yuvarlanır.
- RNG `np.random.default_rng(np.random.SeedSequence([kullanici_id, karar_sayisi, deste_no]))`
  ile kurulur.
- Metin → tamsayı dönüşümünde `hashlib` kullanılır. Python'un `hash()` işlevi süreç
  başına tuzlanır (PYTHONHASHSEED); aynı girdi farklı süreçlerde farklı deste üretir.
- Mevcut "tohum = çalışma + karar sayısı" ilkesi (K21) bu yapıya oturur.

---

## 7. Bizim ortama uygulama — somut tarif

### (a) LOAO sahte etiketleriyle eğitilmiş öğrenilmiş füzyon sıralayıcısı (yalnız numpy)

**Adım 0: Sızıntı düzeltmesi ve birleşik havuz.** S1 filtresi her katta uygulanır.
C_q, gizleme sonrası PMI, CLAP, kredi ve ListenBrainz havuzlarının birleşimidir; aday
sanatçı anahtarına göre tekilleştirilir.

**Adım 1: Özellik matrisi.** Bütün sorguların adayları alt alta yığılır: X (N×d). Grup
başlangıç indisleri `bas` (G), grup boyları `boy` (G), pozitiflerin satır indisleri `poz`
(G') ve sorgu ağırlıkları `w` (G) tutulur. Ortalama ve ss yalnız eğitim katından alınır.

**Adım 2: Koşullu logit + RRF'ye doğru büzme (Newton).** Satırlar grup sırasına dizilir.

```text
fonksiyon kosullu_logit(X, bas, boy, poz, w, mu, lam, en_cok=50):
    θ ← mu
    wr ← tekrarla(w, boy)                         # satır ağırlığı
    döngü en_cok kez:
        s  ← X·θ
        s  ← s − tekrarla(grup_max(s, bas), boy)  # sayısal kararlılık
        e  ← exp(s);  Z ← grup_topla(e, bas);  p ← e / tekrarla(Z, boy)
        xb ← grup_topla(p[:,None]·X, bas)         # G×d, x̄_q
        g  ← Σ_q w_q·(X[poz_q] − xb_q) − lam·(θ − mu)
        H  ← (X·(wr·p)[:,None])ᵀ·X − (xb·w[:,None])ᵀ·xb + lam·I
        adım ← çöz(H, g);  θ ← θ + adım
        eğer max|adım| < 1e-8: dur
    döndür θ, H                                    # sonsal ≈ N(θ, H⁻¹)
```

numpy karşılıkları: `np.maximum.reduceat`, `np.add.reduceat`, `np.repeat`,
`np.linalg.solve`. Bu yapı yalnız *erişilebilir* sorgularla çalışır. Problem içbükey
olduğu için tek bir çözümü vardır.

**Adım 3: İç içe LOAO.**
```text
her dış sanatçı a için (147):
    E ← {q ≠ a}                                   # eğitim sorguları
    katlar ← sanatçıya göre gruplanmış 10 kat (tohum sabit, eksene göre tabakalı)
    her (λ, F) ∈ {0.1, 0.3, 1, 3, 10, 30, 100} × {F_min, F_tam} için:
        iç_skor[λ,F] ← katlar üzerinden ortalama dışarıda koşullu log-olabilirlik
    (λ*, F*) ← 1-SE kuralı: en iyiye 1 SE yakın en büyük λ, sonra küçük F
    θ_a ← kosullu_logit(E, λ*, F*)
    C_a'yı θ_a ile sırala → r_a (a erişilemiyorsa None)
    kaydet: r_a, θ_a, λ*, F*
```

Maliyet: 147 × 10 × 14 ≈ 20.600 küçük Newton uyumu. Her biri ~10 yineleme, N ≈
146 × |C| satır ve d ≤ 10. Sorgu başına 500 negatif örneklenirse (yalnız eğitimde)
dizüstü bilgisayarda birkaç dakika sürer.

**Adım 4: Çıktılar.**
- Dış döngüden gelen sıralar mevcut `ozet()`'e verilir.
- Bunlara eklenir: koşulsuz yüzdelik, recall_β (β=0,5), ARP@10, yenilik@10, ILD@10,
  beklenmedik isabet oranı ve popülerlik tersillerine göre katmanlar.
- **Katsayı kararlılığı:** 147 adet θ_a vektörünün medyanı ve çeyrekler arası aralığı.
  Bu bir jackknife görünümüdür. İşaret değiştiren katsayı varsa model kırılgandır.
- **λ* dağılımı:** neredeyse hep en büyük λ seçiliyorsa veri RRF'den sapmayı haklı
  çıkarmıyor demektir. Bu bir sonuçtur, başarısızlık değil.

**Adım 5: Duman testleri.**
- y-permütasyonu (§1.3): MRR ≈ H_M/M olmalı.
- λ → ∞ iken sonuç RRF 1:2 ile **birebir** aynı olmalı. Bu bir birim testidir.

### (b) Açık kararlardan güncelleme

1. **Veri.** Her kart için şunlar günlüğe yazılır: özellik vektörü x_t, model sürümü,
   çekiliş tohumu, gösterim olasılığı, karar ∈ {beğendim, tutmadı, biliyorum} ve zaman.
2. **Zevk modeli** (Bernoulli; beğendim=1, tutmadı=0; «biliyorum» dışarıda):
   η_t = β₀ + β_eksen + γ·(θ̂_offᵀx_t) + δᵀx_t. Önseller §4.6'daki gibi. Kestirim MAP-IRLS:

   φ ← φ + (ZᵀWZ + P₀)⁻¹·(Zᵀ(y − μ) − P₀(φ − m₀)),  W = diag(μ(1−μ))

   Burada Z, [1, eksen göstergeleri, θ̂_offᵀx, x] sütunlarından oluşan tasarım matrisi.
   Sonsal ≈ N(φ̂, (ZᵀWZ + P₀)⁻¹).
3. **Bilme modeli.** Tüm kartlarda P(biliyor | x) için ayrı bir lojistik. Popülerliğe
   geniş önsel, diğer katsayılara dar önsel.
4. **Sunum.** Deste başına (tohumlu) φ̃ ve ψ̃ çekilir. Kart değeri
   r_i = (1 − P_ψ̃(biliyor|x_i)) · σ(η_φ̃(x_i)).
5. **Güncelleme sıklığı.** Her karardan sonra sıcak başlangıçlı tek bir Newton adımı.
   Destenin tamamı yalnız deste sınırında yeniden çekilir; bu K21'in "aynı durum, aynı
   deste" ilkesini korur.
6. **Değerlendirme (sıralı, prequential).** Her karar, yalnız ondan önceki kararlarla
   uydurulmuş modelle tahmin edilir. Log-kayıp ve Brier skoru şu üç seçenekle
   karşılaştırılır: (i) yalnız çevrimdışı model (γ=1, δ=0), (ii) kaynak Beta-TS'sinin
   kaynak başına ortalaması, (iii) sabit oran. Fark, gün bloklarıyla yapılan bootstrap
   ile sınanır.
7. **Raporlanacak tek sayı: γ'nın sonsalı.** "Çevrimdışı ölçüm gerçek tercihi ne kadar
   öngörüyor?" sorusunun ölçülmüş cevabı budur. Sızıntı düzeltmesinden önce ve sonra
   eğitilmiş θ̂_off ile γ'yı kıyaslamak, S1 hipotezini çevrimiçi taraftan da sınar.

### (c) Deste yeniden sıralayıcısı (CLAP ile MMR + eksen kalibrasyonu)

**Girdiler.** Aday kümesi R içindeki her i için:
- r_i: beklenen yeni beğeni (b.4), havuz içinde sıra yüzdeliğine göre [0,1]'e çekilir
  ki terimler kıyaslanabilir olsun;
- e_i: CLAP sanatçı merkezi, hubness tabanı çıkarılmış ve birim normlu;
- a_i ∈ Δ^K: yumuşak eksen üyeliği;
- src_i: kaynak.

Hedef dağılım p şöyle seçilir: kullanıcı tek bir eksen seçtiyse ağırlığın çoğu o eksende,
kalan küçük pay eksen komşuluğuna orantılı dağıtılır. «Sen» destesinde p, kütüphanenin
ortalama FCM üyeliğidir.

**Açgözlü adım** (t = 1…N, S boş başlar):

  i* = argmax_{i∈R∖S} (1−λ₁−λ₂)·r_i − λ₁·max_{j∈S} cos(e_i, e_j)
       + λ₂·[C_KL(p, q̃(S)) − C_KL(p, q̃(S ∪ {i}))]

  q(S) = Σ_{j∈S} a_j / |S|,  q̃ = 0,99·q + 0,01·p

**Sert kısıtlar:**
- Sanatçı başına tek kart (K21).
- Aynı kaynaktan art arda en fazla 3 kart.
- Her 5. kart bir **ε-keşif yuvası**: R'nin ilk-200'ünden tekdüze seçim, gösterim
  olasılığı bilinen = 1/200. Bu yuva ileride IPS'yi mümkün kılar.

**Başlangıç ayarı ve λ seçimi.** Başlangıç değerleri λ₁=0,3, λ₂=0,2. Çevrimdışı tarafta
bir Pareto eğrisi çizilir: LOAO recall@50'deki düşüş ile ILD@50 ve C_KL'deki kazanç
karşılaştırılır. "Diz" noktası seçilir ve ardından çevrimiçi serpiştirmeyle doğrulanır
(§5.3). Bu iki parametre için ayrıca iç içe CV yapmaya gerek yok; ölçütleri doğruluk
olmadığı için seçim yanlılığı zaten küçük.

**Tekrarlanabilirlik.** §6'daki kurallar (tohum dizisi, kararlı sıralama, hashlib).

### (d) 147 sorguyla "yeni motor eskisini yener" kararı

**Ön kayıt.** Aşağıdakiler koşudan önce `docs/karar-gunlugu.md`'ye yazılır:
1. **Birincil ölçüt:** MRR, 147 sorgunun tamamında, erişilemeyen sanatçıya RR=0.
   Sızıntı düzeltmeli katlarda hesaplanır.
2. **Adil kıyas:** iki motor aynı katlarda, aynı birleşik havuzda ve **ikisi de iç içe
   ayarlanmış** olarak koşar. Eski motorun RRF ağırlığı iç döngüde {1:1, 1:2, 1:3, 2:1}
   içinden seçilir. Böylece eski motorun 147 sorguda seçilmiş 1:2 ağırlığının
   iyimserliği ortadan kalkar.
3. **Test:** d_q = RR_yeni,q − RR_eski,q. Eşleştirilmiş işaret çevirme permütasyonu
   uygulanır (B = 100.000, tohum = 20261020), iki taraflı α = 0,05. Çapraz kontrol olarak
   eşleştirilmiş t-testi yapılır. Etki büyüklüğü d̄ olarak verilir; %95 aralığı
   eşleştirilmiş BCa bootstrap ile (B = 10.000).
4. **İkincil ölçütler (Holm, aile bazlı 0,05):** recall@10 ve recall@50 için kesin
   McNemar; koşulsuz ortalama yüzdelik sıra için permütasyon; recall_β@10 (β=0,5) için
   permütasyon.
5. **Koruma ölçütleri (eşdeğersizlik, tek taraflı %95 bootstrap üst sınırı):**
   - ARP@10 artışı ≤ %10, veya ilk-10'un medyan liste görünürlüğü artışı ≤ 1;
   - ILD@10 düşüşü ≤ 0,02.
6. **Karar kuralı:**
   - Birincil p < 0,05, d̄'nin alt aralık sınırı > 0 ve koruma ölçütleri geçiyorsa
     **üretime adaydır**. Ardından çevrimiçi serpiştirmeyle onaylanır (§5.3; %60–65
     tercihi görmek için 85–194 bağsız oturum).
   - Birincil ölçüt anlamlı değil ama koruma ölçütleri yenilikte iyileşme gösteriyorsa
     karar "çevrimdışında eşdeğer, daha yenilikçi" olur ve doğrudan serpiştirmeye geçilir.
   - Koruma ölçütü ihlal ediliyorsa, birincil ölçüt ne derse desin **reddedilir**. Bu
     durumda kazanç popülerlikten gelmektedir ve kullanıcının ölçütüyle çelişir.
7. **Sağlamlık kontrolleri (karar ölçütü değil, raporlanır):** küme (eksen) bootstrap'ı,
   popülerlik tersilleri, tek üyeli eksenlerin dışlandığı koşu, S2 duyarlılığı ve
   zamansal LOAO.
8. **Güç notu:** RR farklarının ss'si ≈ 0,2 ise %80 güçle tespit edilebilecek en küçük
   MRR farkı ≈ 0,046. recall@10 farkını görmek için en az 30–50 uyumsuz sorgu gerekir.
   Daha küçük gerçek farkları 147 sorgu **göremez**. Bu durumda "fark yok" denmez;
   "çevrimdışı ölçüm bu büyüklükte bir farkı ayırt edemiyor" denir.

---

## 8. Riskler ve açık sorular

- **S1'in büyüklüğü bilinmiyor.** Düzeltmeden sonra liste yolunun tavanı belirgin
  düşebilir. Bu "motor kötüleşti" demek değil; "ölçüm dürüstleşti" demek. Önce ve sonraki
  sayılar karar günlüğüne birlikte yazılmalı.
- **Çevrimiçi n küçük ve tek kullanıcılı.** Kullanıcı sayısı 5'e çıkınca kullanıcıya
  özgü rastgele etkiler (β_kullanıcı) ve kullanıcılar arası kısmi havuzlama doğal bir
  genişleme olur. Ama önce tek kullanıcıda γ ölçülmeli.
- **«Beğendim» satın almak veya dinlemek demek değil.** K21'in "liste ≠ ölçüm" ayrımı
  korunmalı. Listeye ekleme sonradan bir *ikinci* sonuç olarak modellenebilir.
- **Kaynakça doğrulaması sınırlı.** WebFetch çalışmadığı için birincil metinlerden formül
  doğrulaması yapılamadı (Steck 2011'in üssü, Vargas–Castells EPC formülü, Chapelle–Li
  güncelleme kuralı). Uygulamadan önce ilgili bölümler birincil metinle karşılaştırılmalı.

---

## Kaynakça

**[D]** = bu oturumda web aramasıyla künyesi/özeti doğrulandı. **[B]** = arka plan bilgisi,
bu oturumda doğrulanmadı.

**Değerlendirme metodolojisi**
- [D] Krichene, W., Rendle, S. (2020). *On Sampled Metrics for Item Recommendation.* KDD 2020 (en iyi makale). https://research.google/pubs/on-sampled-metrics-for-item-recommendation/ · genişletilmiş özet IJCAI 2021: https://www.ijcai.org/proceedings/2021/0651.pdf
- [D] Rendle, S. (2019). *Evaluation Metrics for Item Recommendation under Sampling.* arXiv:1912.02263. https://arxiv.org/abs/1912.02263
- [D] Ferrari Dacrema, M., Cremonesi, P., Jannach, D. (2019). *Are We Really Making Much Progress? A Worrying Analysis of Recent Neural Recommendation Approaches.* RecSys 2019. https://arxiv.org/abs/1907.06902
- [D] Ji, Y., Sun, A., Zhang, J., Li, C. (2023). *A Critical Study on Data Leakage in Recommender System Offline Evaluation.* ACM TOIS 41(3). https://arxiv.org/abs/2010.11060
- [D] Cremonesi, P., Koren, Y., Turrin, R. (2010). *Performance of Recommender Algorithms on Top-N Recommendation Tasks.* RecSys 2010, 39–46.
- [D] Steck, H. (2010). *Training and Testing of Recommender Systems on Data Missing Not at Random.* KDD 2010, 713–722. https://dblp.org/rec/conf/kdd/Steck10.html
- [D] Steck, H. (2011). *Item Popularity and Recommendation Accuracy.* RecSys 2011, 125–132. https://doi.org/10.1145/2043932.2043957
- [D] Cañamares, R., Castells, P. (2018). *Should I Follow the Crowd? A Probabilistic Analysis of the Effectiveness of Popularity in Recommender Systems.* SIGIR 2018 (en iyi makale). https://doi.org/10.1145/3209978.3210014
- [D] Bellogín, A., Castells, P., Cantador, I. (2017). *Statistical Biases in Information Retrieval Metrics for Recommender Systems.* Information Retrieval Journal 20(6).
- [D] Schnabel, T., Swaminathan, A., Singh, A., Chandak, N., Joachims, T. (2016). *Recommendations as Treatments: Debiasing Learning and Evaluation.* ICML 2016. https://arxiv.org/abs/1602.05352
- [B] Hu, Y., Koren, Y., Volinsky, C. (2008). *Collaborative Filtering for Implicit Feedback Datasets.* ICDM 2008 (beklenen yüzdelik sıra).
- [B] Yang, L., Cui, Y., Xuan, Y., Wang, C., Belongie, S., Estrin, D. (2018). *Unbiased Offline Recommender Evaluation for Missing-Not-At-Random Implicit Feedback.* RecSys 2018.

**İstatistiksel çıkarım ve model seçimi**
- [D] Smucker, M. D., Allan, J., Carterette, B. (2007). *A Comparison of Statistical Significance Tests for Information Retrieval Evaluation.* CIKM 2007. https://doi.org/10.1145/1321440.1321528
- [D] Smucker, M. D., Allan, J., Carterette, B. (2009). *Agreement Among Statistical Significance Tests for Information Retrieval Evaluation at Varying Sample Sizes.* SIGIR 2009. https://ir.webis.de/anthology/2009.sigirconf_conference-2009.82
- [D] Urbano, J., Lima, H., Hanjalic, A. (2019). *Statistical Significance Testing in Information Retrieval: An Empirical Analysis of Type I, Type II and Type III Errors.* SIGIR 2019. https://arxiv.org/abs/1905.11096
- [D] Parapar, J., Losada, D. E., Presedo-Quindimil, M. A., Barreiro, Á. (2019/2020). *Using Score Distributions to Compare Statistical Significance Tests for Information Retrieval Evaluation.* JASIST. https://arxiv.org/abs/1901.10696
- [D] Urbano, J. (2026). *Stop Using the Wilcoxon Test: Myth, Misconception and Misuse in IR Research.* arXiv:2604.25349. https://arxiv.org/abs/2604.25349
- [D] Ihemelandu, N., Ekstrand, M. D. (2021). *Statistical Inference: The Missing Piece of RecSys Experiment Reliability Discourse.* Perspectives@RecSys 2021. https://arxiv.org/abs/2109.06424
- [D] Ihemelandu, N., Ekstrand, M. D. (2023). *Inference at Scale: Significance Testing for Large Search and Recommendation Experiments.* SIGIR 2023 (kısa). https://arxiv.org/abs/2305.02461
- [D] Ihemelandu, N., Ekstrand, M. D. (2024). *Multiple Testing for IR and Recommendation System Experiments.* ECIR 2024 (Advances in Information Retrieval).
- [D] Carterette, B. (2012). *Multiple Testing in Statistical Analysis of Systems-Based Information Retrieval Experiments.* ACM TOIS 30(1), 4:1–4:34. https://doi.org/10.1145/2094072.2094076
- [D] Ferro, N. ve ark. (2024). *Uncontextualized Significance Considered Dangerous.* SIGIR 2024 (yazar listesi ikincil kaynaktan, doğrulanmalı).
- [D] Sakai, T. (2018). *Laboratory Experiments in Information Retrieval: Sample Sizes, Effect Sizes, and Statistical Power.* Springer.
- [D] Varma, S., Simon, R. (2006). *Bias in Error Estimation when Using Cross-Validation for Model Selection.* BMC Bioinformatics 7:91. https://doi.org/10.1186/1471-2105-7-91
- [D] Cawley, G. C., Talbot, N. L. C. (2010). *On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation.* JMLR 11, 2079–2107. https://www.jmlr.org/papers/v11/cawley10a.html
- [B] Brown, L. D., Cai, T. T., DasGupta, A. (2001). *Interval Estimation for a Binomial Proportion.* Statistical Science 16(2).
- [B] Efron, B., Tibshirani, R. (1993). *An Introduction to the Bootstrap.* Chapman & Hall (BCa).
- [B] Holm, S. (1979). *A Simple Sequentially Rejective Multiple Test Procedure.* Scand. J. Statistics · Benjamini, Y., Yekutieli, D. (2001). Annals of Statistics.
- [B] Hastie, T., Tibshirani, R., Friedman, J. (2009). *The Elements of Statistical Learning*, 2. baskı (1-SE kuralı).
- [B] Peduzzi, P. ve ark. (1996), J. Clin. Epidemiol. (EPV) · Riley, R. D. ve ark. (2019/2020), BMJ / Stat. Med. (örneklem büyüklüğü eleştirisi).

**Doğruluğun ötesi**
- [D] Kaminskas, M., Bridge, D. (2016/2017). *Diversity, Serendipity, Novelty, and Coverage: A Survey and Empirical Analysis of Beyond-Accuracy Objectives in Recommender Systems.* ACM TiiS 7(1). https://doi.org/10.1145/2926720
- [D] Vargas, S., Castells, P. (2011). *Rank and Relevance in Novelty and Diversity Metrics for Recommender Systems.* RecSys 2011, 109–116.
- [D] Ziegler, C.-N., McNee, S. M., Konstan, J. A., Lausen, G. (2005). *Improving Recommendation Lists through Topic Diversification.* WWW 2005, 22–32. https://doi.org/10.1145/1060745.1060754
- [D] Ge, M., Delgado-Battenfeld, C., Jannach, D. (2010). *Beyond Accuracy: Evaluating Recommender Systems by Coverage and Serendipity.* RecSys 2010, 257–260. https://doi.org/10.1145/1864708.1864761
- [D] Abdollahpouri, H., Burke, R., Mobasher, B. (2019). *Managing Popularity Bias in Recommender Systems with Personalized Re-ranking.* FLAIRS 2019. https://arxiv.org/abs/1901.07555
- [D, ikincil] Steck, H. (2018). *Calibrated Recommendations.* RecSys 2018. Tarama: *Calibrated Recommendations: Survey and Future Directions* (2025), https://arxiv.org/abs/2507.02643
- [B] Zhou, T. ve ark. (2010). *Solving the Apparent Diversity–Accuracy Dilemma of Recommender Systems.* PNAS 107(10).
- [B] Fleder, D., Hosanagar, K. (2009). *Blockbuster Culture's Next Rise or Fall.* Management Science 55(5) (Gini).
- [B] Kaya, M., Bridge, D. (2019). *A Comparison of Calibrated and Intent-Aware Recommendations.* RecSys 2019.

**Füzyon**
- [D] Cormack, G. V., Clarke, C. L. A., Büttcher, S. (2009). *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.* SIGIR 2009, 758–759. https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- [D] Bruch, S., Gai, S., Ingber, A. (2023). *An Analysis of Fusion Functions for Hybrid Retrieval.* ACM TOIS. https://arxiv.org/abs/2210.11934
- [D, ikincil] Fox, E. A., Shaw, J. A. (1994). *Combination of Multiple Searches.* TREC-2, 243–252.
- [D, ikincil] Lee, J. H. (1997). *Analyses of Multiple Evidence Combination.* SIGIR 1997.
- [D] Montague, M., Aslam, J. A. (2001). *Relevance Score Normalization for Metasearch.* CIKM 2001. https://www.khoury.northeastern.edu/home/jaa/papers/MontagueAs01b.pdf
- [D] Montague, M., Aslam, J. A. (2002). *Condorcet Fusion for Improved Retrieval.* CIKM 2002. https://ir.webis.de/anthology/2002.cikm_conference-2002.69

**Sıralama öğrenme, Bayesçi yöntemler, PU**
- [D] Rendle, S., Freudenthaler, C., Gantner, Z., Schmidt-Thieme, L. (2009). *BPR: Bayesian Personalized Ranking from Implicit Feedback.* UAI 2009. https://arxiv.org/abs/1205.2618
- [D] Burges, C. J. C. (2010). *From RankNet to LambdaRank to LambdaMART: An Overview.* MSR-TR-2010-82. https://www.microsoft.com/en-us/research/?p=159784
- [D] Gelman, A., Jakulin, A., Pittau, M. G., Su, Y.-S. (2008). *A Weakly Informative Default Prior Distribution for Logistic and Other Regression Models.* Annals of Applied Statistics 2(4), 1360–1383. https://doi.org/10.1214/08-AOAS191
- [D] Elkan, C., Noto, K. (2008). *Learning Classifiers from Only Positive and Unlabeled Data.* KDD 2008, 213–220.
- [B] Bekker, J., Davis, J. (2020). *Learning from Positive and Unlabeled Data: A Survey.* Machine Learning 109.
- [B] McFadden, D. (1974). *Conditional Logit Analysis of Qualitative Choice Behavior.* Zarembka (ed.), Frontiers in Econometrics · McFadden, D. (1978). *Modelling the Choice of Residential Location* (alternatif örnekleme).
- [B] Breslow, N. E., Day, N. E. (1980). *Statistical Methods in Cancer Research, Vol. 1: The Analysis of Case-Control Studies.* IARC (koşullu lojistik).
- [B] Cao, Z., Qin, T., Liu, T.-Y., Tsai, M.-F., Li, H. (2007). *Learning to Rank: From Pairwise Approach to Listwise Approach.* ICML 2007 (ListNet).
- [B] Joachims, T. (2002). *Optimizing Search Engines Using Clickthrough Data.* KDD 2002 (RankSVM).
- [B] Metzler, D., Croft, W. B. (2007). *Linear Feature-Based Models for Information Retrieval.* Information Retrieval 10(3).
- [B] Firth, D. (1993). *Bias Reduction of Maximum Likelihood Estimates.* Biometrika 80(1).
- [B] Ibrahim, J. G., Chen, M.-H. (2000). *Power Prior Distributions for Regression Models.* Statistical Science 15(1).
- [B] Gelman, A., Hill, J. (2007). *Data Analysis Using Regression and Multilevel/Hierarchical Models.* Cambridge UP.
- [B] Zhang, Y. ve ark. (2021). *Causal Intervention for Leveraging Popularity Bias in Recommendation.* SIGIR 2021 (PDA).
- [B] Shimodaira, H. (2000). *Improving Predictive Inference under Covariate Shift by Weighting the Log-Likelihood Function.* JSPI 90(2).

**Haydutlar, serpiştirme, OPE**
- [D] Russo, D., Van Roy, B., Kazerouni, A., Osband, I., Wen, Z. (2018). *A Tutorial on Thompson Sampling.* Foundations and Trends in ML 11(1). https://arxiv.org/abs/1707.02038
- [D] Chapelle, O., Li, L. (2011). *An Empirical Evaluation of Thompson Sampling.* NIPS 2011. https://papers.nips.cc/paper/2011/hash/e53a0a2978c28872a4505bdb51db06dc-Abstract.html
- [D] Li, L., Chu, W., Langford, J., Schapire, R. E. (2010). *A Contextual-Bandit Approach to Personalized News Article Recommendation.* WWW 2010. https://arxiv.org/abs/1003.0146
- [D] Agrawal, S., Goyal, N. (2013). *Thompson Sampling for Contextual Bandits with Linear Payoffs.* ICML 2013. https://arxiv.org/abs/1209.3352
- [D] Li, L., Chu, W., Langford, J., Wang, X. (2011). *Unbiased Offline Evaluation of Contextual-Bandit-Based News Article Recommendation Algorithms.* WSDM 2011. https://arxiv.org/abs/1003.5956
- [D] Radlinski, F., Kurup, M., Joachims, T. (2008). *How Does Clickthrough Data Reflect Retrieval Quality?* CIKM 2008. https://cs.cornell.edu/~tj/publications/radlinski_etal_08b.pdf
- [D] Chapelle, O., Joachims, T., Radlinski, F., Yue, Y. (2012). *Large-Scale Validation and Analysis of Interleaved Search Evaluation.* ACM TOIS 30(1), 6:1–6:41. https://doi.org/10.1145/2094072.2094078
- [B] Yue, Y., Joachims, T. (2009). *Interactively Optimizing Information Retrieval Systems as a Dueling Bandits Problem.* ICML 2009.
- [B] Schuth, A. ve ark. (2014). *Multileaved Comparisons for Fast Online Evaluation.* CIKM 2014.
- [B] Dudík, M., Langford, J., Li, L. (2011). *Doubly Robust Policy Evaluation and Learning.* ICML 2011.
- [B] Russo, D. (2016). *Simple Bayesian Algorithms for Best Arm Identification.* COLT 2016 (top-two TS).
- [B] Johari, R., Koomen, P., Pekelis, L., Walsh, D. (2017). *Peeking at A/B Tests.* KDD 2017 (her zaman geçerli p-değerleri).

**Yeniden sıralama ve çeşitlilik**
- [D] Carbonell, J., Goldstein, J. (1998). *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries.* SIGIR 1998, 335–336. https://doi.org/10.1145/290941.291025
- [D] Chen, L., Zhang, G., Zhou, H. (2018). *Fast Greedy MAP Inference for Determinantal Point Process to Improve Recommendation Diversity.* NeurIPS 2018. https://arxiv.org/abs/1709.05135
- [D] Wilhelm, M., Ramanathan, A., Bonomo, A., Jain, S., Chi, E. H., Gillenwater, J. (2018). *Practical Diversified Recommendations on YouTube with Determinantal Point Processes.* CIKM 2018. https://doi.org/10.1145/3269206.3272018
- [D] Santos, R. L. T., Macdonald, C., Ounis, I. (2010). *Exploiting Query Reformulations for Web Search Result Diversification.* WWW 2010. https://doi.org/10.1145/1772690.1772780
