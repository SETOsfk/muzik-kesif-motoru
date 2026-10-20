# Müzik önerisi literatürü: tam metin doğrulaması

Hazırlanma: 2026-10-20 · Önceki rapor: `2-muzik-onerisi.md` (özet/arama özetine dayanıyordu,
**[B]** işaretli maddeler bellekten). Bu raporda kaynakların **tam metni** okundu; sayılar,
formüller ve eşikler sayfa ya da bölüm numarasıyla verildi. Kod yazılmadı.

İşaretler:
- **[TM]**: tam metinden doğrulandı (sayfa/bölüm verildi).
- **[Ö]**: yalnız özet (abstract) düzeyinde okundu.
- **[P]**: projenin kendi ölçümü (`CLAUDE.md`, `docs/karar-gunlugu.md`, önceki rapor §3.0).
- **[Biz]**: literatürde yok, bu raporun önerisi; ölçülmeden üretime girmez (K19).

---

## 0. Ne okundu, nereden

| # | Kaynak | Erişim | Durum |
|---|---|---|---|
| 1 | Lesota ve ark. 2022, ISMIR, «Traces of globalization…» | Zenodo 7316652 (ISMIR bildiri PDF'i, s. 291–297) | [TM] |
| 1b | Lesota ve ark. 2024, RecSys LBR, «Oh, Behave! Country representation dynamics…» | arXiv 2408.11565 | [TM] |
| 2 | Kowald, Schedl, Lex 2020, ECIR, «The unfairness of popularity bias in music recommendation» | arXiv 1912.04696v2 | [TM] |
| 2b | Lesota ve ark. 2021, RecSys LBR, «Analyzing item popularity bias… genders» | arXiv 2108.06973 | [TM] |
| 3 | Volkovs ve ark. 2018, vl6, «Two-stage model for automatic playlist continuation at scale» | cs.toronto.edu/~mvolkovs/recsys2018_challenge.pdf | [TM] |
| 4 | Zamani, Schedl, Lamere, Chen 2019, ACM TIST | arXiv 1810.01520v2 | [TM] |
| 5 | Anderson ve ark. 2020, WWW, «Algorithmic effects on the diversity of consumption on Spotify» | cs.toronto.edu/~ashton/pubs/alg-effects-spotify-www2020.pdf | [TM] |
| 6 | McInerney ve ark. 2018, RecSys, «Explore, exploit, and explain» (BaRT) | jamesmc.com/s/BartRecSys.pdf (yazarın sayfası; ACM sürümü kapalı) | [TM] |
| 7a | Tamm & Aljanaki 2024, RecSys LBR | arXiv 2409.08987 | [TM] |
| 7b | Tamm & Aljanaki 2026, ACM TORS (doi 10.1145/3808222) | arXiv 2604.23077 | [TM] |
| 7c | Li, Lou, Huang, Sheng, Yao 2026, «From classification to recommendation…» | arXiv 2608.06928v2 | [TM] |
| 7d | Sandler 2026, «Nearest but not dearest: shared curator-feedback infrastructure…» (Feed.fm) | arXiv 2609.30568 | [TM] — **yeni bulundu, doğrudan ilgili** |
| 8 | Pichl, Zangerle, Specht 2015 (ICDMW) ve 2017 (ICMR) | Pichl doktora tezi 2018 (Innsbruck DBIS; iki makale tezin 6. bölümünde) | [TM, tez üzerinden] |
| 9 | Schedl, Zamani, Chen, Deldjoo, Elahi 2018, IJMIR | arXiv 1710.03208v2 | [TM] |
| 10 | Dil/kültür denetimi taraması (arXiv API) | Bkz. §10 | karışık |

Okunamayan: Pichl & Zangerle 2021 (MTAP), Moradi ve ark. 2024 tam metni (yalnız özet),
LEACE/INLP tam metni (yalnız özet). arXiv'de dil yanlılığını çalma listesi birlikteliğinde
doğrudan denetleyen bir çalışma **bulunamadı** (§10).

---

## 1. Önceki rapordaki iddiaların hükmü

| Önceki iddia (2-muzik-onerisi.md) | Hüküm | Doğrusu / ek |
|---|---|---|
| Lesota 2022: «ItemKNN birçok ülkenin kullanıcısına yerli müzik öneriyor, NeuMF ABD baskınlığını hızlandırıyor» | **Doğru, ama ölçülen şey dil değil ülke** | Sanatçı ülkesi MusicBrainz'den. ItemKNN'in yerli payı tükettiğinden belirgin fazla önerdiği dört ülkeden biri **Türkiye** (JP, TR, IT, FI). §2.1 |
| Kowald 2020: «LowMS grup belirgin biçimde en kötü öneriyi alıyor» | **Doğru, ama ölçüt MAE** | Puan tahmini (Surprise), sıralama değil. ΔGAP gruplar arasında fark **göstermedi** (MostPopular dışında). ItemKNN çalışmaya alınmadı. §2.2 |
| Lesota 2021: medyan, momentler, KL, Kendall τ | **Doğru** | Uygulanabilir ayrıntı: ondalık dilimler kümülatif popülerliğe göre (her dilim toplamın ~%10'u). Makalede metin ile tablo arasında bir tutarsızlık var. §2.3 |
| Volkovs 2018: «1. aşamada MF ve CNN 20 bin aday üretiyor» | **Düzeltme** | Yalnız WRMF 20 bin aday çekiyor; CNN, item-item ve user-user yalnız bu adayları skorluyor. §3 |
| Volkovs 2018 öznitelikleri [B] | **Kısmen doğrulandı** | En büyük kazanç liste–parça çiftli öznitelik grubundan. Liste «homojenliği» en önemli liste özniteliklerinden. Liste uzunluğu ve popülerlik doğru; «ortalama/en büyük/en küçük» ayrımı metinde yok. §3 |
| Zamani 2019: «başlıklar etkili kullanılamadı» | **Doğru, bir nüansla** | vl6'nın başlık-SVD soğuk başlangıç modeli popülerliğe göre RPREC'i 0,0395'ten 0,1106'ya çıkardı. Başlık soğuk başlangıçta işe yarıyor, tohum varken zarar verebiliyor. §4 |
| Anderson 2020: GS-skoru tanımı, 40 boyutlu word2vec, deney sonucu | **Doğru** | Eksik: «etkinliğe göre düzeltilmiş GS» (etkinlik kovası içinde yüzdelik sıra). Sayılar: §5 |
| McInerney 2018 [B]: FM ödül, ε-açgözlü, karşı-olgusal | **Doğrulandı** | Keşif «koşullu»: öğe ve açıklama ayrı ayrı keşfedilir. «Popüler olduğu için» açıklaması en zayıf. §6 |
| Tamm 2026: «MuQ ve MuQ-MuLan hem sıcak hem soğukta en üstte; soğuk testte HitRate@20 MuQ-MuLan 0,2502, MuQ 0,1726» | **Yanlış atıf** | Bu sayılar **KNN** soğuk tablosundan (Tablo 9). O tabloda MuQ **sonuncu**, MERT birinci (0,2829). MuQ yalnız eğitilen modellerde üstte. Eğitimsiz benzerlikte (projenin kullanımı) MuQ zayıf. §7 |
| Li 2026: «müziğe özgü CLAP en güçlü uzay, 18 ayarın 13'ünde» | **Doğru, ama dar** | Yalnız 6 kodlayıcı karşılaştırıldı (Wav2Vec2, HuBERT, Music2Vec, MERT, CLAP-G, CLAP-Music); MuQ, MusiCNN, MusicFM **yok**. Veri ~5 bin parçalık iki alt küme. §7 |
| Pichl 2015/2017: «bağlam sözcükleri word2vec benzerliğiyle kümeleniyor» | **Yanlış** | WordNet lemmatizasyonu, eşanlamlı/üst-kavram genişletmesi, tf-idf ve k-means. Sanatçı/albüm/**tür** adlı listeler bağlamsız sayılıp atılıyor. 23 durum kümesi. §8 |
| Schedl 2018: üç zorluk ve üç yön | **Doğru** | §3.3 kültürü açıkça «aynı dili konuşmak» düzeyinde de tanımlıyor. §9 |

---

## 2. Yerellik ve popülerlik yanlılığı

### 2.1 Lesota, Parada-Cabaleiro, Brandl, Lex, Rekabsaz, Schedl (2022), ISMIR, s. 291–297 [TM]

**Veri (§2.4, s. 293, Tablo 1):** LFM-2b'nin 2018–2019 dilimi. Bir kez dinlenmiş olaylar
atılıyor. Sanatçı ülkesi **MusicBrainz**'den alınıyor, ülkesi bulunamayan sanatçı atılıyor.
Sonuç: ~14,64 milyon etkileşim, ~13 bin kullanıcı (143 ülke), ~637 bin parça, ~45 bin
sanatçı (155 ülke). Ayrıntılı analiz ≥100 kullanıcı ve ≥1000 parçası olan 20 ülkede.
**Türkiye:** 115 kullanıcı, 286 sanatçı, 1.478 parça.

**Ölçütler (§2.1–2.2, s. 292):**
- Tüketim tarafı: `IC_{cu→ca} = |I_{ca,cu}| / |I_{cu}|`, yani cu ülkesindeki kullanıcıların
  tüm dinlemelerinde ca ülkesi sanatçılarının payı. Üç durum: yerel (ca=cu), ABD, diğer.
- İhracat tarafı: `IC_{cu←ca} = |I_{ca,cu}| / |I_{ca}|`, yani ca ülkesi müziğinin
  dinlemelerinin ne kadarının cu'dan geldiği.

**Öneri deneyi (§2.3, s. 292–293):** ItemKNN (Deshpande & Karypis 2004) ve NeuMF. Her biri
~100 bin parçalık 3 rastgele alt örneklemde eğitiliyor (5-çekirdek: parça ≥5, kullanıcı ≥5
etkileşim). Her kullanıcıya **ilk 10** öneri veriliyor ve IC aynı biçimde hesaplanıyor.

**Bulgular:**
- Ortalama tüketimin %39,6'sı ABD sanatçılarından. ABD kullanıcılarında yerli pay %60'ın
  üstünde (s. 294).
- **İhracat matrisi (Şekil 4, s. 296):** Türk müziğinin dinlemelerinin **%54,5'i Türk
  kullanıcılardan** geliyor (Brezilya %79,6, Polonya %65,7, Rusya %55,9). Türkiye «ABD
  etkisi düşük, yerelde tüketilen» kümede: PL, TR, RU (s. 295).
- **ItemKNN (Şekil 3a, s. 295):** «JP, TR, IT ve FI'deki dinleyicilere, kendi dinlemelerinde
  ayırdıkları paydan **belirgin biçimde daha büyük** bir yerli pay öneriliyor.» Aynı dört
  ülkede ABD payı tüketimin altında kalıyor. ItemKNN ortalamada daha az kayma yapıyor.
- **NeuMF (Şekil 3b):** ABD dışındaki her ülkeye tükettiğinden fazla ABD müziği öneriyor.

**Projeye anlamı:** Sezen Aksu vakası literatürde **Türkiye için adıyla raporlanmış** bir
etki. Ancak (i) makale ülkeyi ölçüyor, dili değil; (ii) etki şekilden okunuyor, ülke
başına sayı tabloda yok; (iii) mekanizma birlikteliğe dayalı komşuluk, yani NPMI ailesi.

### 2.1b Lesota, Geiger, Walder, Kowald, Schedl (2024), RecSys LBR [TM]

Geri besleme döngüsü benzetimi: 100 yineleme. Her yinelemede kullanıcı başına ilk 10
öneriden biri, `p(t|R) = e^{α·rank_t} / Σ_j e^{α·j}` olasılığıyla (α = −0,1) profile
ekleniyor ve model yeniden eğitiliyor (§2, s. 2). Veri: LFM-2b, ~2,29 milyon etkileşim,
~100 bin parça, ~12 bin kullanıcı. Bu örneklemde Türkiye yok.

**Ülke kalibrasyonu ölçütü (Denklem 1, s. 2):**
```
JSD(H_u, H*_u) = ½ Σ_c H_u(c)·log2(2H_u(c)/(H_u(c)+H*_u(c)))
               + ½ Σ_c H*_u(c)·log2(2H*_u(c)/(H_u(c)+H*_u(c)))
c ∈ {yerel, ABD, diğer}  ·  kullanıcı başına hesaplanır, grupta ortalanır
```
Popülerlik için de aynı ölçüt, `c ∈ {HighPop, MidPop, LowPop}`.

**Bulgular (Tablo 2, s. 3; §4.1):**
- 100. yinelemede önerilerdeki yerli pay değişimi: Pop −%47,5, NeuMF −%39,7, MultiVAE
  −%21,2, BPR −%6,6, LightGCN −%3,5, ItemKNN +%0,4. Başlangıçtaki yerli tüketim payı 0,18.
- Profil JSD'si: Pop 0,13, **ItemKNN 0,12** (eğitilen modeller içinde en yüksek), NeuMF
  0,10, MultiVAE 0,09, BPR ve LightGCN 0,08.
- **Ana ders:** ItemKNN **ortalama** yerli payı koruyor ama kullanıcı başına ülke
  dağılımını en çok bozuyor. Yazarların cümlesiyle «ortalama oranları koruyan modeller
  ülke-kalibre öneri vermiyor olabilir.» Ayrıca «en popülerlik-kalibre model (ItemKNN) en
  az ülke-kalibre olan.» (Özet ve §4.1.)

**Projeye anlamı:** Dil sızıntısını ortalama Türkçe payla ölçmek yanıltır. Ölçüt eksen
başına dağılım uyumu olmalı (§11-A).

### 2.2 Kowald, Schedl, Lex (2020), ECIR, LNCS 12036, s. 35–42 [TM, arXiv v2]

- **Veri (§2, s. 2–3):** LFM-1b'den 3.000 kullanıcı. «Ana akımlık» (mainstreaminess)
  puanına göre en düşük 1.000 (LowMS), medyan çevresindeki 1.000 (MedMS) ve en yüksek
  1.000 (HighMS). Bu puan, kullanıcının dinleme geçmişinin tüm Last.fm toplamıyla
  örtüşmesidir (Bauer & Schedl 2019). Toplam 1.755.361 kullanıcı–sanatçı etkileşimi,
  352.805 sanatçı.
- **Popülerlik tanımı (s. 3):** sanatçıyı dinleyen kullanıcıların oranı. «Popüler» = en çok
  dinleyicisi olan ilk %20. Kullanıcıların ~1/3'ünün profilinde en az %20 popüler olmayan
  sanatçı var. Profil boyu ile popüler sanatçı sayısı R = 0,965; profil boyu ile ortalama
  popülerlik **R = −0,372**: küçük profiller daha popüler dinliyor.
- **Yöntem (§3, s. 4):** Surprise kütüphanesi, **puan tahmini**. Dinleme sayısı [0, 1000]'e
  ölçekleniyor, ilk 10 öneriliyor, 80/20 bölme. Algoritmalar: Random, MostPopular,
  UserItemAvg, UserKNN, UserKNNAvg, NMF. **ItemKNN ve SVD++ hesap maliyeti yüzünden
  dışarıda.**
- **ΔGAP (s. 5):** `GAP(g)_p` = gruptaki kullanıcıların profil sanatçılarının ortalama
  popülerliği; `GAP(g)_r` = öneri listelerininki.
  `ΔGAP = (GAP(g)_r − GAP(g)_p) / GAP(g)_p`. 0 ise popülerlik açısından adil.
- **Bulgular:** Random ve NMF dışındaki tüm yöntemler her gruba fazla popüler öneriyor.
  **ΔGAP gruplar arasında belirgin fark göstermiyor** (yalnız MostPopular'da). Yazarlar bunu
  büyük katalogla açıklıyor. **MAE (Tablo 1, s. 6):** LowMS her algoritmada anlamlı
  biçimde en kötü (t-testi, p < 0,005). Örneğin UserKNN: LowMS 49,813, MedMS 42,527,
  HighMS 46,036. En iyi MedMS çıkıyor (kullanıcı başına ~715 sanatçıyla en büyük profiller).

**Projeye anlamı:** ΔGAP müzikte duyarsız. Lesota 2021'in dağılım ölçütleri tercih edilmeli.
«Bu kullanıcı LowMS» yorumu kalıyor; ama kanıt puan tahmini hatasından geliyor,
sıralamadan değil.

### 2.3 Lesota, Melchiorre, Rekabsaz, Brandl, Kowald, Lex, Schedl (2021), RecSys LBR [TM]

**Tanımlar (§3, s. 3–4):**
- Parça popülerliği `P(t) = Σ_u PC(t,u)` (toplam dinleme sayısı).
- Kullanıcının geçmiş dağılımı `H_u` ve öneri dağılımı `R_u`. Öneri listesi **geçmiş
  uzunluğuna kesiliyor**: `|T_top_rec(u)| = |T_hist(u)|`.
- `%ΔM_u = (M(R_u) − M(H_u)) / M(H_u) · 100`, M ∈ {ortalama, medyan, varyans, çarpıklık,
  basıklık}. Sistem değeri = kullanıcı değerlerinin **medyanı**.
- **KL ve Kendall τ için dilimleme (§3.2.2, s. 4):** 10 dilim, her dilimdeki parçaların
  **kümülatif popülerliği toplamın ~%10'u** olacak biçimde. Bu veri kümesinde en popüler
  dilim yalnız 161 parça (7 bin–47 bin dinleme). Her dilim bir sonrakinin ~yarısı kadar
  popüler. `KL(Ĥ_u ‖ R̂_u) = Σ_j Ĥ_u(b_j)·log(Ĥ_u(b_j)/R̂_u(b_j))`. Kendall τ dilim
  sayımlarının sırası üzerinden.
- Veri (§4.2, s. 5): LFM-2b-DemoBias, 19.972 kullanıcı, 99.831 parça (100 bin parça tekdüze
  rastgele örneklenmiş), kullanıcı tabanlı 60/20/20 bölme, 5 katlı çapraz doğrulama.

**Bulgular (Tablo 2, s. 6):**

| Alg. | %ΔOrt. | %ΔMedyan | KL | τ | NDCG@10 |
|---|---|---|---|---|---|
| ItemKNN | 9,6 | 4,6 | **0,175** | **0,423** | 0,301 |
| SLIM | 49,8 | 99,8 | 0,424 | 0,189 | **0,365** |
| BPR | −49,0 | −3,7 | 1,202 | 0,268 | 0,129 |
| ALS | 121,8 | 316,6 | 4,368 | 0,046 | 0,184 |
| VAE | 303,9 | 736,3 | 4,823 | −0,028 | 0,191 |
| POP | 432,5 | 975,2 | 6,023 | 0,057 | 0,045 |

ItemKNN popülerlik açısından en az yanlı, NDCG'de ikinci. Yazarlar daha az yanlılığın
doğruluk kaybı demek olmadığını söylüyor (s. 7). Yöntemlerin çoğu kadın kullanıcılara
daha popüler öneriyor.

**Dikkat:** Metin «SLIM KL 1,66» diyor, tablo 0,424 (s. 6). Makale içi tutarsızlık.

---

## 3. Volkovs, Rai, Cheng, Wu, Lu, Sanner (2018), vl6 [TM]

**1. aşama (§2.1, s. 2–3).** Aday üretimini **yalnız WRMF** yapıyor (rank 200, α = 100,
λ_U = λ_V = 0,001; `c_ij = 1 + α·R_ij`). Liste başına 20 bin aday, recall %90'ın üstünde;
ilk 1 bin aday tek başına ~%60 recall veriyor (s. 1). CNN (7 GLU bloğu, 900 çekirdek, 200
boyut), User-User ve Item-Item modelleri yalnız bu 20 bin adayı skorluyor.

**Komşuluk skorlarında popülerlik düzeltmesi (s. 3).** Verstrepen ve ark.'nı izleyerek:
```
s'_ij = s_ij · popularity_j^{−(1−β)}     β < 1 popüleri cezalandırır
β = 0,6 (User-User), β = 0,9 (Item-Item)
```
Yazarlar bunun iki komşuluk modelinin doğruluğunu da «belirgin biçimde» artırdığını
söylüyor.

**Karışım (Denklem 5, s. 3–4).** Skorlar önce z-standardize ediliyor (ortalama çıkar,
std'ye böl). Ağırlıklar {0, 0,1, …, 0,5} kümesinden açgözlü seçiliyor; küme aşırı
uyumu önlemek için bilerek küçük tutulmuş. Seçilen: WRMF 0,1, **CNN 0,4**, User 0,3,
Item 0,3. Tek başına en zayıf model (CNN) karışımda en büyük ağırlığı alıyor, çünkü
diğerlerinin taşımadığı sıra bilgisini taşıyor.

**2. aşama öznitelikleri (§2.2, s. 4), beş grup:**
1. 1. aşamadaki beş skor (dört model + karışım).
2. **Liste öznitelikleri:** ad, uzunluk, ortalama parça/sanatçı/albüm popülerliği ve
   **homojenlik** `(1/|V(i)|)·Σ_{j∈V(i)} U_i·V_j`. Yazarlara göre homojenlik bu grubun en
   önemli özniteliklerinden; bazı listeler tek tür, bazıları çok dağınık.
3. **Parça öznitelikleri:** sanatçı/albüm/başlık, süre, liste istatistikleri ve parça
   homojenliği `(1/|U(j)|)·Σ_{i∈U(j)} U_i·V_j`. Bu, parçanın benzer türden listelerde mi
   durduğunu ölçüyor; «etkili olduğu kanıtlandı».
4. **Liste–parça öznitelikleri:** hedef parça ile listedeki parçalar arasında ve hedef
   liste ile parçayı içeren listeler arasında benzerlikler (sanatçı/albüm örtüşmesi,
   ortalama gizil skor benzerliği, süre ve uzunluk farkı). **«1. aşamaya göre en büyük
   iyileşmeyi bu grup sağladı»**; yazarlar gelecekteki çabanın buraya gitmesini öneriyor.
5. Yaratıcı kulvar: Spotify ses API'sinden 12 öznitelik, «küçük ama tutarlı» kazanç.

**Eğitim:** liste başına 20 ilgili + 20 ilgisiz aday, ikili etiket. XGBoost, **çiftli
sıralama kaybı ikili çapraz entropiden iyi**, 150 ağaç, derinlik 10. 90 bin listelik ayrı
bir bölmeden 3,5 milyonun üstünde örnek (§2.4, s. 5).

**Soğuk başlangıç (§2.3, s. 4–5).** Liste adlarından bir matris (satırlar: listeler +
parçalar, sütunlar: adlar; parça satırı, onu içeren listelerin ad sayımları) kesik SVD ile
ayrıştırılıyor; liste ve parça aynı uzaya düşüyor.

**Doğrulama sonuçları (Tablo 1, s. 5; RPREC / NDCG / Clicks):**

| Model | RPREC | NDCG | Clicks |
|---|---|---|---|
| WRMF | 0,1641 | 0,3350 | 2,1230 |
| CNN | 0,1594 | 0,3230 | 2,1157 |
| Item-Item | 0,1772 | 0,3534 | 2,1649 |
| User-User | 0,1768 | 0,3550 | 1,6332 |
| Karışım | 0,1866 | 0,3728 | 1,4064 |
| 2. aşama | **0,1985** | **0,3846** | **1,1998** |
| Soğuk: Popüler | 0,0395 | 0,0815 | 17,27 |
| Soğuk: Ad-SVD | 0,1106 | 0,2083 | 7,96 |

Komşuluk modelleri gizil modellere eşit ya da daha iyi (s. 5). Test skoru: RPREC 0,2241,
NDCG 0,3946 (Tablo 3, s. 6).

**Projeye anlamı:**
- «Kaba geniş aday + ince yeniden sıralama» doğru; ama 2. aşamanın asıl gücü **çiftli
  öznitelikler** (aday ile kütüphane arasındaki örtüşme), model skorları değil.
- **Liste homojenliği** doğrudan bizim sorunumuza karşılık geliyor. Sezen Aksu bağını
  taşıyan 135 ve 250 sanatçılı «kişisel karışım» listeleri düşük homojenlikli listeler [P].
  Homojenliği ağırlık olarak kullanmak ucuz bir sızıntı süzgeci (§11-D).

---

## 4. Zamani, Schedl, Lamere, Chen (2019), ACM TIST [TM, arXiv v2]

- **Veri (Tablo 1, s. 3):** 1 milyon liste, 2.262.292 tekil parça, 295.860 sanatçı, 92.944
  tekil başlık, **17.381 tekil normalize başlık**, ortalama 66,35 parça.
- **Bulgular (§4, s. 6–8):**
  - «Şaşırtıcı biçimde, başlık da verildiğinde modeller daha kötü.» Tip 2 (başlık + ilk 5)
    ile Tip 3 (yalnız ilk 5) arasındaki tek fark başlık. Yazarların açıklaması:
    başlıklar seyrek, modeller eğitimdeki başlıklara aşırı uyuyor (s. 6).
  - Rastgele seçilmiş tohum parçalar ilk parçalardan çok daha iyi; bitişik parçalar aynı
    bilgiyi taşıyor (s. 6).
  - **«Bir parça bile fark eder»:** yalnız başlık (Tip 1) → başlık + ilk parça (Tip 10)
    büyük sıçrama (s. 7).
  - Az tohumda takımlar birbirine yakın; tohum ≥25 olunca fark açılıyor (s. 7).
  - Yaratıcı kulvar (dış veri) ana kulvardan **hafifçe kötü** (s. 7–8 ve §7).
- **Yaklaşımlar (§5, s. 9–10):** MF (WRMF, WARP kayıplı LightFM, BPR); basit komşuluk
  yöntemleriyle iyi sonuç alan takımlar (HAIR, Definitive Turtles); 2. aşamada çoğunlukla
  çiftli öğrenen-sıralama (XGBoost, GBDT, LambdaMART). **Bilgi erişimi ağırlıkları:**
  IDF (Definitive Turtles), TF-IDF (KAENEN), BM25 (Creamy Fireflies), relevance model
  (BachPropagate).
- **Ana bulgular (§7, s. 14):** çözümlerin çoğu bilinen yöntemleri birleştiriyor; başlık
  etkili kullanılamadı; **hiçbir çözüm başlıktan niyet çıkarmayı denemedi**.
- **Gelecek yönler (§9, s. 14–15):** başlıktan niyet çıkarma (öz-farkındalık, sosyal
  bağlılık, uyarılma/ruh hâli düzenleme); liste tutarlılığını ve çeşitliliğini (Creamy
  Fireflies'ın «sanatçı heterojenliği» ölçüsü gibi) **zayıf kısıt** olarak korumak;
  kullanıcı merkezli algılanan kalite ölçümü.

**Nüans:** Zamani «başlık işe yaramadı» diyor; ama vl6 başlığı **soğuk başlangıçta** başarıyla
kullandı (§3). Ders: başlık, kanıt yokken yararlı bir öncül; kanıt varken gürültü.

---

## 5. Anderson, Maystre, Mehrotra, Anderson, Lalmas (2020), WWW [TM]

**Gömü (§3.2, s. 3–4):** Spotify, 850 milyondan fazla (çoğunlukla kullanıcı yapımı) liste
üzerinde **word2vec CBOW** eğitiyor; çok kısa, çok uzun (tutarlı temaya sahip olamayacak
kadar) ve yakın zamanda güncellenmemiş listeler süzülüyor. Vektörler **40 boyutlu**, her gün
yeniden eğitiliyor. Benzerlik kosinüs.

**GS-skoru (§3.3, s. 4):**
```
μ_i = (1 / Σ_j w_j) · Σ_j w_j · s_j                     (dinleme sayısıyla ağırlıklı merkez)
GS(u_i) = (1 / Σ_j w_j) · Σ_j w_j · (s_j · μ_i) / (‖s_j‖·‖μ_i‖)
```
Yüksek GS uzman (odaklı), düşük GS genelci. Tür entropisiyle r = −0,77, tür Gini
katsayısıyla r = −0,60 (s. 4). Yüksek etkinlikte dağılım ~0,5 çevresinde kararlılaşıyor
(§4, s. 5).

**Etkinliğe göre düzeltilmiş GS (§5, s. 7):** kullanıcının GS'sinin, aynı etkinlik
kovasındaki kullanıcılar arasındaki **yüzdelik sırası**. Az dinleyen hafifçe daha «uzman»
göründüğü için gerekli.

**Bulgular:**
- Veri: 100 milyonun üstünde kullanıcı; Temmuz 2019'un ilk 28 gününde ~70 milyar dinleme;
  çalışma yalnız premium kullanıcılarla (§3, s. 3).
- Etkinlik denetlendiğinde genelciler 12 ayda **25 yüzde puana kadar daha az** ayrılıyor
  ve **35 yüzde puana kadar daha çok** ücretli aboneliğe geçiyor (s. 2, §4.3).
- Organik dinleme, algoritmik dinlemeden daha çeşitli. Zamanla genelcileşen kullanıcılar
  algoritmik dinlemeden organiğe kayıyor (§5).
- **Çevrimiçi deney (§6, Tablo 1, s. 10):** «All Out 50s–10s» listelerinde, bir hafta,
  540 bin ücretsiz kullanıcı. Sıralayıcılar: popülerlik, ilgililik (kullanıcı–parça kosinüsü),
  öğrenilmiş sinir ağı.

| Karşılaştırma | Kullanıcı | Dinleme | Atlama |
|---|---|---|---|
| İlgililik / popülerlik | Genelci | +%10,03 | +%4,71 |
| | Uzman | **+%25,66** | +%2,89 |
| Öğrenilmiş / ilgililik | Genelci | +%1,82 | +%0,90 |
| | Uzman | +%1,30 | **−%9,76** |

İlgililiğin kazancı uzmanlarda iki kattan fazla. Genelcilerde ilgililik daha çok atlama
getiriyor. Yazarlar «klasik modeller uzmanlarda çok daha iyi çalışıyor» diyor.

**Projeye anlamı:** Kullanıcı bütün kütüphanesiyle bir genelci; ama **eksen seçtirmek her
sorguyu bir uzman profiline çeviriyor** (K3, K21). Literatür bu tasarımı destekliyor:
ilgililik sıralaması uzman profilde en iyi çalışıyor. GS formülü, liste homojenliği
(§3) ile aynı hesap: tek fark ağırlık ve birim.

---

## 6. McInerney ve ark. (2018), RecSys, BaRT [TM]

**Problem (§3.1, s. 2–3):** öğeler J, kullanıcılar U, açıklamalar E. **Geçerlilik
fonksiyonu** `f: E × U → 2^J`, her açıklama ve kullanıcı için geçerli öğe kümesini veriyor
(«yakında tarihî roman okudun» yalnız ilgili öğeler için geçerli). Açıklamalar
**parametreli kurallar** (Tablo 1): «Arkadaşlarının sevdiği filmler», «P'ye benzer
sanatçıların listeleri» vb. Bir öğenin birden çok açıklaması olabilir.

**Ödül modeli (§3.2.1, s. 3–4):** lojistik regresyon tüm kullanıcılara aynı en iyi
(öğe, açıklama) çiftini verir; yazarlar bunu «denetlenmiş popülerlik» diye niteliyor.
Kişiselleştirme için 2. ve 3. dereceden **faktörizasyon makinesi**, bağlam vektörü öğe,
açıklama ve bağlamı birleştiriyor.

**Karşı-olgusal eğitim (§3.2.2, s. 4):** karşı-olgusal risk minimizasyonu (CRM):
```
(θ̂, v̂) ≈ argmax (1/N) Σ_n [Uniform(a_n) / π_c(a_n)] · log p_{θ,v}(r_n | a_n, x_n)
```
Toplama politikası π_c bilinmeli, yani her gösterimin olasılığı (eğilim skoru) loglanmalı.

**Keşif (§3.2.3, s. 5):** ε-açgözlü, ama **koşullu**: önce öğe, sonra öğeye koşullu
açıklama ayrı ayrı keşfediliyor. `π_c = π_c^öğe · π_c^açıklama`. Gerekçeler: ortak
keşif fazla keşifçi; çok sayıda eylem küçük eğilim skoru ve yüksek varyans getiriyor; raf
arayüzü bir açıklama altında birden çok öğe gösteriyor. Varyans için normalize önem
ağırlıklandırması ve eğilim skoru tavanı kullanılıyor.

**Bulgular (§4.1, s. 6):**
- H0₁ «akış, açıklamadan bağımsız»: χ² = 570,67, eşik 22,458 (sd = 6, %1). **Reddedildi.**
- H0₂ «aynı liste farklı açıklamayla aynı akışı alır»: küme 1 (haftanın günü, son
  dinlemelerinden esinle, tür sevgisi, popüler) χ² = 126,85, eşik 16,266, **reddedildi**;
  küme 2 (ruh hâli, odak) χ² = 0,112, reddedilemedi (yalnız 6 ortak liste).
- **«Popüler olduğu için» en zayıf; son dinlemelere ve türe dayalı açıklamalar en güçlü.**
- Çevrimiçi A/B: açıklamaları sabit sırayla göstermeye göre **%20'nin üstünde** akış oranı
  artışı (s. 6). Rastgele «güvenli» keşif: kullanıcı başına ~100 ilgili liste önceden
  seçilip sırası karıştırılmış.

**Projeye anlamı:** K7 şablonları BaRT'ın açıklama kuralları ve şablonun boşlukları
geçerlilik fonksiyonu. BaRT bulgusu, K22'deki «kanıtın gücünü söyle» ilkesini destekliyor:
popülerliğe dayanan gerekçe en az ikna eden gerekçe. Asıl uygulanabilir ders eğilim
skorunun loglanması (§11-G).

---

## 7. Ses gömüleri ve öneri

### 7.1 Tamm & Aljanaki (2024), RecSys LBR [TM]

- Veri: Music4All-Onion; eğitim 12 ay, test/doğrulama son ay (2020-02-20 sonrası), yalnız
  kullanıcı için yeni parçalar. Eğitim 17.053 kullanıcı, 56.193 parça, 5,1 milyon etkileşim
  (Tablo 2). Parça gömüsü zamanda ortalama. CLAP **yok**.
- **KNN (eğitimsiz, kullanıcı = profil ortalaması), HitRate@50 (Tablo 3):** MusicFM 0,009,
  MFCC 0,028, Music2Vec 0,033, MERT 0,049, EncodecMAE 0,054, Jukebox 0,057, **MusiCNN 0,089**.
- BERT4Rec ile: MusiCNN 0,385 (rastgele başlatmaya göre p < 0,05 anlamlı), MERT 0,360,
  EncodecMAE 0,349, rastgele 0,348.
- «MusiCNN tüm testlerde sürekli en iyi» (§3, s. 4). İçerik + işbirlikçi bilgi, ham
  KNN'den ~10 kat iyi.

### 7.2 Tamm & Aljanaki (2026), ACM TORS [TM]

Dokuz gömü (+MFCC), beş önerici, sıcak ve soğuk senaryo. Music4All-Onion (rock ve pop
ağırlıklı ana akım). Test ayı 2019-02; soğuk test o ay ilk kez görünen **589 parça**
arasından öneri (§3.1). **MuQ ve MuQ-MuLan eğitim verisine Music4All dahil** (öz-denetimli,
yazarlara göre sızıntı değil; Tablo 3, s. 9).

**Eğitimsiz KNN (projenin kullanım biçimine en yakın):**

| Sıcak, Tablo 4 (s. 13), HitRate@50 | | Soğuk, Tablo 9 (s. 18), HitRate@20 | |
|---|---|---|---|
| MusicFM | **0,0370** | MERT | **0,2829** |
| EncodecMAE | 0,0317 | MusiCNN | 0,2662 |
| MuQ-MuLan | 0,0289 | EncodecMAE | 0,2504 |
| MULE | 0,0282 | MuQ-MuLan | 0,2502 |
| MusiCNN | 0,0275 | Music2Vec | 0,2482 |
| Music2Vec | 0,0218 | MusicFM | 0,2453 |
| Jukebox | 0,0195 | MFCC | 0,2423 |
| MERT | 0,0171 | MULE | 0,2242 |
| **MuQ** | 0,0169 | Jukebox | 0,1832 |
| MFCC | 0,0147 | **MuQ** | **0,1726** |

**MuQ eğitimsiz benzerlikte iki senaryoda da sonlarda.** Sıcakta KNN değerleri 0,01–0,03;
eğitilen modellerde ~10 kat büyük (s. 12).

**Eğitilen modellerde en iyiler (Tablo 8, s. 16; Tablo 12, s. 21):**
- Sıcak, en iyi melez: **MusiCNN + BERT4Rec 0,4722**. Ama saf işbirlikçi **ELSA 0,5580**
  hiçbir melez tarafından geçilemiyor (s. 16).
- Tablo 12 (en iyi sıcak / soğuk): MusiCNN 0,472 / 0,569; EncodecMAE 0,445 / 0,620;
  MusicFM 0,443 / 0,673; MuQ 0,441 / 0,652; MULE 0,407 / 0,602; MERT 0,368 / 0,641;
  Jukebox 0,298 / **0,679**; MFCC 0,302 / 0,566.
- MuQ-MuLan Hibrit modelde iki senaryoda da en iyi; birleşik model için «güçlü aday»
  (§4.2.1).

**MIR başarısı öneriyi öngörüyor mu? (§4.3–4.4.3, s. 21–22):** «MIR görevlerindeki
performans doğrudan öneri performansına aktarılmıyor.» Soğuk öneri MIR'a sıcak öneriden
daha yakın. Örnek: MusiCNN etiketlemede orta, anahtar tespitinde en kötü (0,128), sıcak
öneride en iyi. Jukebox MIR'da güçlü, sıcakta en kötü, soğukta en iyi. MFCC soğukta
MusiCNN'e yakın.

### 7.3 Li, Lou, Huang, Sheng, Yao (2026), arXiv 2608.06928 [TM]

- Kodlayıcılar: Wav2Vec 2.0, HuBERT, Music2Vec, MERT, **CLAP-G** (genel ses, füzyon açık)
  ve **CLAP-Music** (HTSAT-base, füzyon kapalı), hepsi ℓ2-normalize (Tablo 1).
  **MuQ, MusiCNN, MusicFM yok.**
- Veri: LFM-1b'den 4.996 parçalık alt küme (7.987 kullanıcı) ve Music4All-Onion'dan 5.000
  parçalık alt küme (8.855 kullanıcı); birini-dışarıda-bırak (leave-one-out), K = 50.
- Bulgular (s. 4–5): CLAP-Music **18 ayarın 13'ünde** birinci, CLAP-G 10'unda ikinci.
  Müzikle ön eğitilmiş gömüler genel ses/konuşma gömülerini **54 karşılaştırmanın
  45'inde** geçiyor. **KNN gömü seçimine en duyarlı** önerici; SASRec etkileşimle uzayı
  yeniden biçimlendirip farkları kapatıyor.
- Sınır (yazarların): ~5 bin parçalık iki küçük veri; çevrimdışı ölçütler dinleyici
  memnuniyetini ölçmüyor.

### 7.4 Sandler (2026), arXiv 2609.30568, Feed.fm [TM] — doğrudan dil sızıntısı kanıtı

- Sistem: yalnız içerikle çalışan B2B müzik keşfi; **LAION-CLAP** (HTSAT-base, 512 boyut,
  müzikle ön eğitilmiş checkpoint), tam kosinüs araması, davranış sinyali yok (s. 2–3).
- **Kosinüsle en yakın komşuların %38,17'si küratörlerce reddediliyor** (1.200 öneri,
  458 kodlu ret). Retlerin %55,2'si ses hatası (tarz %36,7, tempo %11,4, ruh hâli %7,2);
  **%36,9'u bağlam hatası**: tatil %14,8, **yanlış dil %14,6**, müstehcen %3,1, popüler
  değil %1,7, çocuk %1,5, söz %0,7, dinî %0,4 (Tablo 1, s. 4).
- **Kosinüs dil hatasını göremiyor:** kabul edilenlerin ortalama kosinüsü 0,897,
  reddedilenlerin 0,881; kabul/ret AUC'u yalnız **0,644**. Yanlış dil retlerinin ortalaması
  0,879, ses retleriyle aynı bantta (s. 5). Makaledeki örnek: İspanyolca Latin-pop tohum,
  aynı prodüksiyonlu İngilizce bir parçayı ~0,85 kosinüsle getiriyor; küratör «yanlış dil»
  diye reddediyor (s. 1).
- **Çözüm, katmana göre yönlendirme:** bağlam retleri → aday üretiminde **kural tabanlı
  kısıt süzgeci** (dil etiketi denetimi; aynı gün devreye giriyor, «günlerce katalog işi»).
  Ses retleri → **yeniden ağırlıklandırma başı**: donmuş CLAP üzerinde tek doğrusal
  512×512 izdüşüm, birim matrisle başlatılıyor, birimden sapmaya ceza; üçlü kenar kaybı
  (margin 0,2), AdamW (lr 1e-4), birkaç yüz üçlü; «haftalarca model işi» (§3.3, s. 3).
- Sonuç: ret oranı %38,17 → %28,83 (−%24,5 göreli; McNemar χ² = 22,4, p = 2,2·10⁻⁶).
  Düşüşün 4,08 yüzde puanı süzgece uygun kategorilerden, 5,25'i diğerlerinden. **Uyarılar:**
  tek yazar, endüstri, kör olmayan değerlendirme (yazar kendisi belirtiyor).

**Projeye anlamı:** «CLAP, Türkçe kadın vokal tınısı üzerinden Sezen Aksu'yu buldu» [P]
gözlemi bu çalışmada da var: dil, kosinüs uzayında ayrışmıyor. Dil sorunu gömüyle değil,
**aday aşamasında meta veriyle** çözülüyor; ses sorunu ayrı bir katman.

### 7.5 Ses bölümünün sonucu

1. **Projenin eğitimsiz CLAP kullanımı literatürle uyumlu.** Eğitimsiz benzerlikte
   CLAP-Music, MERT ve Music2Vec'i geçiyor (7.3). MERT de Tamm 2026'nın soğuk KNN'inde
   birinci (7.2). CLAP ile MuQ ya da MusiCNN'i doğrudan karşılaştıran bir çalışma
   **yok**.
2. **MuQ'ya geçmek için kanıt yok, aleyhine kanıt var:** eğitimsiz KNN'de MuQ iki senaryoda
   da sonlarda (7.2). MuQ'nun üstünlüğü yalnız eğitilen önericilerde.
3. Sınanmaya değer tek ucuz aday **MusiCNN** (200 boyut, sıcak KNN'de orta, soğuk KNN'de
   ikinci, eğitilen sıcak modelde birinci). Lisansı ayrıca denetlenmeli; burada
   doğrulanmadı.
4. İçerik tek başına işbirlikçi sinyalden çok zayıf (sıcak KNN 0,037'ye karşı ELSA 0,558).
   Bu, projenin LOAO'daki «ses yolu 0,03» sonucuyla [P] tutarlı. Ama gerçek kararlarda
   ses yolu öndeydi [P]: çevrimdışı isabet «ses tercihi»ni ölçmüyor. Li 2026 ve Sandler
   2026 de bu sınırı açıkça yazıyor.

---

## 8. Pichl, Zangerle, Specht 2015 ve 2017 [TM, Pichl doktora tezi 2018 üzerinden]

Tezin 6. bölümü iki makalenin genişletilmiş hâli («ELFC-MR I: Situational Context»).

**Başlıktan bağlam çıkarma (§6.3, basılı s. 59–60):**
1. Başlıklar **WordNet ile lemmatize** ediliyor.
2. **Bağlam taşımayan listeler atılıyor**: çoğunlukla sanatçı, albüm ya da **tür** adını
   taşıyanlar. Tespit için AlchemyAPI varlık tanıma (IBM, ticari; yazarlara göre büyük
   ölçüde MusicBrainz'e dayanıyor).
3. Kalan kısa adlar WordNet **eşanlamlıları ve üst kavramlarıyla** genişletiliyor.
4. **tf-idf** matrisi, sonra **k-means**. k seçimi: 2 ≤ k ≤ √(n/2) aralığında (n = tekil
   liste sayısı; PDF metni bozuk, üst sınır bilinen √(n/2) kuralı olarak okundu) WCSS
   hesaplanıyor, birinci fark ΔWCSS alınıyor ve `ΔWCSS_k < ort(ΔWCSS) − σ(ΔWCSS)` koşulunu
   sağlayan **en büyük k** seçiliyor; Mann-Whitney U ile destekleniyor (p < 0,01).
5. Spotify veri kümesinde **23 durum kümesi** («summer», «summer feelings», «summer
   outside» aynı kümede). Bağlam genellikle zamansal, etkinlik ya da aktivite.

**Kullanım:** 2015'te bağlama göre ön süzme (pre-filtering): veri kümelere bölünüp CF
uygulanıyor. 2017'de küme kimliği faktörizasyon makinesine bağlam özniteliği olarak
veriliyor. Bu, ön süzmenin kullanıcı profilini bölme kusurunu gideriyor. FM tabanlı
yaklaşım ön süzmeli CF'den ortalama **%169,23 daha yüksek kesinlik** veriyor (PDF s. 84).
Değerlendirme ±1 etiketli, aşırı örneklemeyle dengelenmiş bir sınıflama; sayılar
sıralama ölçütleriyle kıyaslanamaz.

**Kültür bağlamı (tez §8):** kullanıcıların coğrafi konumundan «müzik-kültür kümeleri»
türetiliyor ve **doğruluğu artırmak için öznitelik** olarak kullanılıyor. Durum + ses +
kültür kümeleri birlikte en iyi; yalnız durum kümesi %19,53 daha düşük F1 (PDF s. 69).

**Projeye anlamı:**
- Pichl'in hattı İngilizceye bağlı (WordNet). Türkçe başlıklar için uygun değil; 482
  listede elle etiketleme daha ucuz ve doğrulanabilir (önceki rapor §3.1b).
- Pichl **tür adını taşıyan başlığı bağlamsız sayıyor**. Bizde tersi gerekiyor: tür adlı
  liste müzikal kanıt, «türkçe» ya da «karışık» adlı liste bağlam kanıtı.
- Literatür kültürü **ekleyerek** kullanıyor (doğruluk için). Bizim ihtiyacımız ise onu
  eksen sorusu için **denetlemek**. Bu ayrım önemli: Pichl'in sonucu, kültür sinyalinin
  güçlü olduğunu, yani sızıntının beklenen bir şey olduğunu gösteriyor.

---

## 9. Schedl, Zamani, Chen, Deldjoo, Elahi (2018), IJMIR 7(2):95–116 [TM]

**Müzik önerisinin özgüllükleri (§2.1, s. 2–3):** kısa öğe süresi (3–5 dk); on milyonlarca
öğelik katalog; ardışık tüketim; aynı öğeyi yeniden önermenin kabul görmesi; pasif dinleme
(atlanmayan şarkı yanlışlıkla olumlu sayılabilir); dinleme niyeti (Schäfer: öz-farkındalık,
sosyal bağlılık, uyarılma ve ruh hâli düzenleme); duygular; dinleme bağlamı.

**Üç büyük zorluk (§2.2–2.4):**
1. **Soğuk başlangıç** (yeni kullanıcı, yeni öğe, seyreklik). Çözümler: içerik tabanlı,
   melez, alanlar arası, aktif öğrenme (s. 3).
2. **Otomatik çalma listesi sürdürme** (§2.3).
3. **Değerlendirme:** doğruluk ötesi ölçütler (çeşitlilik, yenilik, serendipity, kapsama);
   bu ölçütlerin birden çok tanımı var, çünkü «şaşırtıcılık» gibi öğeler matematiksel
   olarak zor (§2.4).

**Gelecek yönleri (§3):** psikoloji temelli öneri (kişilik, duygu), duruma duyarlı öneri,
**kültüre duyarlı öneri (§3.3, s. 13)**. Bu son bölüm, kültürün yalnız sınırla değil
«ortak tarih, **aynı dili konuşmak**, inanç, kent/kır» düzeyinde tanımlanması gerektiğini
yazıyor. Türk makam müziği CompMusic projesinin beş geleneğinden biri olarak anılıyor.

---

## 10. Dil ve kültür etkisini denetleme: tarama sonucu

arXiv API'de «language bias», «cultural», «country/local» ve «playlist + language» ile
müzik önerisi aramaları yapıldı.

**Doğrudan bulunanlar:**
- **Ölçüm:** Lesota 2022 (yerli pay IC), Lesota 2024 (ülke dağılımı JSD'si). Bkz. §2.1.
- **Endüstri çözümü:** Sandler 2026, yanlış dil için aday aşamasında meta veri süzgeci.
  Bkz. §7.4.
- **Kültürü öznitelik yapmak:** Pichl tezi §8; Schedl, Bauer, Reisinger, Kowald, Lex (2020,
  arXiv 2009.09935) [Ö], ülke arketipleri ve geçitli (gating) VAE.
- **Gömü uzayında kültürel denge:** Moradi, Neophytou, Farnadi (2024, arXiv 2405.17607) [Ö],
  prototip tabanlı MF'de ilgisiz prototipleri süzme ve prototiplerin tekdüze dağılması
  için düzenlileştirme. Eğitilen modele özgü; projeye doğrudan aktarılmaz.
- **Popülerlik kalibrasyonu kullanıcı çalışması:** Lesota ve ark. (2026, arXiv 2608.05402)
  [Ö]. Kullanıcılar popülerlik bileşimindeki farkı algılıyor ama **kalibre listeyi açıkça
  tercih etmiyor**. JSD ile algılanan popülerlik arasındaki ilişki tanıdıklığa ve geçmiş
  verisinin eksiksizliğine bağlı. Hesaplanan ve kullanıcının yargıladığı popülerlik zayıf
  uyuşuyor. → Kalibrasyonu hedef değil **tanı** olarak kullanmak doğru.

**Komşu alanlardan aktarılabilir:**
- **Doğrusal kavram silme:** INLP (Ravfogel ve ark. 2020, arXiv 2004.07667) [Ö], LEACE
  (Belrose ve ark. 2023, arXiv 2306.03819) [Ö]. Bir özelliği (örneğin dil) doğrusal olarak
  tahmin edilemez kılacak biçimde gömüden siler; LEACE kapalı formlu ve gömüyü en az
  değiştiren çözüm.
- **Derece koruyan sıfır modeli:** Takeuchi (2026, arXiv 2604.26119) [TM, kısmen], çalma
  listesi birliktelik ağında topluluk sınır gücünü 100 «configuration model» benzetimine
  göre ölçüyor (§3.3, §4.3). Bu sıfır modeli popülerliği ve liste boyunu denetler, **dili
  denetlemez**.

**Bulunamayan:** çalma listesi birlikteliğinde dil/kültürü **koşullayarak** benzerlik
hesaplayan bir çalışma. Önceki raporun «eşleştirilmiş sıfır modeli» (dil × görünürlük
katmanı) önerisi literatürde bir karşılığı olmayan bir **[Biz]** önerisi. Değeri ancak
proje kendi ölçümüyle gösterebilir.

---

## 11. Uygulanabilir ayrıntılar (numpy + SQLite, 0 TL, LLM'siz)

Her madde K19'a göre bir kıyasla ölçülür. Kaynak gösterilmeyen ayrıntı **[Biz]**.

**A. Eksen başına dil dağılımı kalibrasyonu (Lesota 2024 Denklem 1).**
`c ∈ {tr, en, ja, enstrümantal, diğer}`. `H_k` = k ekseninin kütüphane sanatçılarında FCM
üyeliğiyle ağırlıklı dil dağılımı; `H*_k` = destenin ilk 50'sinin dağılımı. Log2 tabanlı
JSD [0, 1] aralığında. Raporlanacak: eksen başına JSD ve **ortalama Türkçe payı ayrıca**
(2024'ün dersi: ortalamanın korunması kalibrasyon demek değil). Dil etiketi K14'e uygun
kaynaktan: MusicBrainz sanatçı ülkesi (Lesota'nın kullandığı), yoksa «bilinmiyor».

**B. Popülerlik dağılımı (Lesota 2021 §3.2).** Görünürlük = sanatçının 482 listeden
kaçında geçtiği. 10 dilim, her dilim toplam görünürlüğün ~%10'u. Kütüphane (eksen) ile
deste arasında KL ve dilim sayımlarında Kendall τ. Lesota'da liste geçmiş boyuna
kesiliyordu; bizde deste 50, eksen üye sayısı farklı, bu yüzden oranlar karşılaştırılır.
Boş dilim için ε yumuşatması [Biz]. ΔGAP'i birincil ölçüt yapmayın; müzikte duyarsız
çıktı (Kowald 2020).

**C. Komşuluk skorunda popülerlik üssü (Volkovs §2.1).** `s' = s · pop^{−(1−β)}`;
Volkovs'ta β = 0,6 (kullanıcı tabanlı) ve 0,9 (öğe tabanlı). NPMI zaten popülerliği
normalize ediyor; bu düğme ham birliktelik ya da RP3β yolunda anlamlı. RP3β'da üs
doğrudan β, burada 1−β: aynı düğmenin iki yazımı, karıştırılmamalı.

**D. Liste homojenliği ağırlığı (Volkovs §2.2; Anderson GS §3.3).** Liste l için
`h_l = ort_{a∈l} cos(e_a, μ_l)`, burada `μ_l` listedeki sanatçı gömülerinin merkezi.
Gömü olarak CLAP (ses) ya da liste matrisinin PPMI-SVD'si kullanılabilir; CLAP gömüsü
olmayan sanatçılar atlanır. Anderson'daki gibi liste boyuna göre yüzdelik sıraya çevrilir
(büyük listeler doğal olarak daha dağınık). Ağırlık `w_l = yüzdelik(h_l)^γ`, γ ∈ {0; 0,5;
1}. Beklenti: 135 ve 250 sanatçılı kişisel karışımlar düşük ağırlık alır. Dikkat: dil
homojen ama tür dağınık bir «türkçe» listesi, gömü dili ayırmıyorsa (Sandler 2026)
**yüksek** homojenlik alabilir. Bu yüzden D, E'nin yerine geçmez.

**E. Sanatçının bağlam maruziyeti (vl6 ad-SVD fikrinin basit hâli).** Sanatçı a için
`m_a = (dil/karışık bağlamlı listelerdeki görünme sayısı) / (toplam görünme sayısı)`.
Eksen sorgusunda `m_a` yüksek ve tür bağlamlı listelerde desteği sıfır olan aday
«yalnız bağlam kanıtı» sayılır (önceki rapor §3.1b ile aynı kapı, burada tek sayı).

**F. Sızıntıyı aday aşamasında süzmek (Sandler 2026).** Ekseni kuran üyelerin Türkçe payı
p_k bir eşiğin altındaysa (örneğin %10 [Biz]), Türkçe adaylar listenin başına değil
sonuna itilir ya da kartta «bu bağ dil üzerinden» diye işaretlenir. Türk rock ekseninde
süzgeç devre dışı kalır. Sandler'in dersi: dil hatası gömüyle düzelmiyor, meta veri
kuralıyla bir günde düzeliyor.

**G. Tutmadı gerekçesini kodlamak ve eğilim skorunu loglamak (Sandler; BaRT §3.2.2).**
(i) «Tutmadı»ya isteğe bağlı tek dokunuşluk gerekçe: dil / ses / bağlam (tatil, çocuk vb.)
/ diğer. Dil ve bağlam retleri F'deki kurallara, ses retleri ilerideki bir doğrusal
yeniden ağırlıklandırmaya gider. (ii) Her kartın gösterim olasılığını loglamak:
Thompson'da kapalı form yok; aynı tohumla M = 1000 kez örnekleyip kaynağın seçilme oranı
eğilim skoru olarak yazılır. İleride kaynak payını karşı-olgusal değerlendirmek
(IPS: `Σ r_n · π_yeni(a_n)/π_c(a_n)`) ancak bu logla mümkün. Bugün yazılmazsa geçmiş
kararlar bu amaçla kullanılamaz.

**H. Eksen başına GS-skoru (Anderson §3.3).** `GS_k` = eksen üyelerinin eksen merkezine
ortalama kosinüsü (FCM üyeliğiyle ağırlıklı). İki kullanım: (i) uzman eksenlerde
(yüksek GS) ilgililik sıralaması; genelci eksenlerde (düşük GS) çeşitlilik ya da MMR
(Anderson'ın deneyi: ilgililik kazancı uzmanlarda iki kattan fazla). (ii) Destenin GS'si
eksen GS'sinden çok yüksekse deste tek tipleşmiş demektir.

**I. Ses omurgası kararı (Tamm 2026; Li 2026).** MuQ'ya geçilmez. İsteğe bağlı tek sınama:
CLAP ile MusiCNN (ya da MERT) arasında LOAO ve gerçek karar isabeti, **dil-içi** recall ile
birlikte. Benchmark sırası karar ölçütü değil (Tamm 2026 §4.4.3).

**J. Vokalsiz CLAP ya da kavram silme (Sandler; INLP/LEACE).** Önceki raporun vokalsiz
stem önerisi (§3.2) Sandler'in «dil kosinüste ayrışmıyor» bulgusuyla güçleniyor. Daha ucuz
alternatif [Biz]: etiketli kütüphane ve aday CLAP vektörlerinde Türkçe ile Türkçe olmayan
sınıf ortalamaları farkı yönünü izdüşümle silmek (`e' = e − (e·d̂)d̂`, d̂ birim fark
vektörü; INLP'nin tek adımlık, LEACE'in beyazlatmasız basit hâli). Risk: Türk rock
ekseninde dil tarzın parçası; silme yalnız ilgili eksenlerde uygulanır ve eksen başına
ölçülür.

**K. Derece koruyan permütasyon sıfır modeli (Takeuchi 2026; önceki rapor «curveball»).**
482 × 10.360 ikili matrisin satır ve sütun toplamlarını koruyan karıştırmalarla beklenen
birliktelik ve z-skoru. Bu, popülerliği ve liste boyunu denetler, dili denetlemez. Dil için
karıştırmanın **yalnız aynı dil bloğu içinde** yapılması gerekir [Biz]. O zaman z-skoru
«aynı dildeki rastgele bir sanatçıdan fazla mı» sorusunu cevaplar.

**L. Başlık: kanıt yokken öncül (vl6 §2.3; Zamani §4).** Başlık sinyal olarak değil iki
yerde kullanılır: (i) bağlam sınıflaması (E, F); (ii) kütüphanede kanıtı olmayan bir
eksen için soğuk başlangıç öncülü (örneğin «japanese fusion» başlıklı listeler). Tohum
sanatçılar varken başlığa ağırlık verilmez (Zamani: başlık eklenince sonuç kötüleşti).

---

## 12. Kaynaklar

- Lesota, O., Parada-Cabaleiro, E., Brandl, S., Lex, E., Rekabsaz, N., Schedl, M. (2022).
  Traces of globalization in online music consumption patterns and results of
  recommendation algorithms. ISMIR 2022, s. 291–297. https://zenodo.org/records/7316652
- Lesota, O., Geiger, J., Walder, M., Kowald, D., Schedl, M. (2024). Oh, Behave! Country
  representation dynamics created by feedback loops in music recommender systems.
  RecSys '24. doi 10.1145/3640457.3688187 · arXiv 2408.11565
- Kowald, D., Schedl, M., Lex, E. (2020). The unfairness of popularity bias in music
  recommendation: A reproducibility study. ECIR 2020, LNCS 12036, s. 35–42.
  arXiv 1912.04696
- Lesota, O., Melchiorre, A. B., Rekabsaz, N., Brandl, S., Kowald, D., Lex, E., Schedl, M.
  (2021). Analyzing item popularity bias of music recommender systems: Are different
  genders equally affected? RecSys '21, s. 601–606. arXiv 2108.06973
- Volkovs, M., Rai, H., Cheng, Z., Wu, G., Lu, Y., Sanner, S. (2018). Two-stage model for
  automatic playlist continuation at scale. RecSys Challenge '18.
  doi 10.1145/3267471.3267480 · https://www.cs.toronto.edu/~mvolkovs/recsys2018_challenge.pdf
- Zamani, H., Schedl, M., Lamere, P., Chen, C.-W. (2019). An analysis of approaches taken
  in the ACM RecSys Challenge 2018 for automatic music playlist continuation. ACM TIST
  10(5):57. arXiv 1810.01520
- Anderson, A., Maystre, L., Anderson, I., Mehrotra, R., Lalmas, M. (2020). Algorithmic
  effects on the diversity of consumption on Spotify. WWW '20.
  https://www.cs.toronto.edu/~ashton/pubs/alg-effects-spotify-www2020.pdf
- McInerney, J., Lacker, B., Hansen, S., Higley, K., Bouchard, H., Gruson, A., Mehrotra, R.
  (2018). Explore, exploit, and explain: Personalizing explainable recommendations with
  bandits. RecSys '18, s. 31–39. doi 10.1145/3240323.3240354 ·
  https://jamesmc.com/s/BartRecSys.pdf
- Tamm, Y.-M., Aljanaki, A. (2024). Comparative analysis of pretrained audio
  representations in music recommender systems. RecSys '24. arXiv 2409.08987
- Tamm, Y.-M., Aljanaki, A. (2026). Adopting state-of-the-art pretrained audio
  representations for music recommender systems. ACM TORS. doi 10.1145/3808222 ·
  arXiv 2604.23077
- Li, Q., Lou, H., Huang, C., Sheng, Q. Z., Yao, L. (2026). From classification to
  recommendation: Empirical analysis of audio embedding models application for
  content-based music recommendation. arXiv 2608.06928
- Sandler, M. (2026). Nearest but not dearest: Shared curator-feedback infrastructure for
  content-only search and recommendation. arXiv 2609.30568
- Pichl, M. (2018). Multi-context-aware recommender systems (doktora tezi, Univ.
  Innsbruck). https://dbis-informatik.uibk.ac.at/sites/default/files/2018-06/20180201_pichl_thesis_final.pdf
  · İçerdiği makaleler: Pichl, Zangerle, Specht (2015), ICDMW, s. 1360–1365; Pichl,
  Zangerle, Specht (2017), ICMR.
- Schedl, M., Zamani, H., Chen, C.-W., Deldjoo, Y., Elahi, M. (2018). Current challenges and
  visions in music recommender systems research. IJMIR 7(2):95–116. arXiv 1710.03208
- [Ö] Schedl, M., Bauer, C., Reisinger, W., Kowald, D., Lex, E. (2020). Listener modeling
  and context-aware music recommendation based on country archetypes. arXiv 2009.09935
- [Ö] Moradi, A., Neophytou, N., Farnadi, G. (2024). Advancing cultural inclusivity:
  Optimizing embedding spaces for balanced music recommendations. arXiv 2405.17607
- [Ö] Lesota, O. ve ark. (2026). Robustness and user-perceived value of popularity
  calibration in music recommendation: A user study. arXiv 2608.05402
- [Ö] Ravfogel, S., Elazar, Y., Gonen, H., Twiton, M. (2020). Null it out: Guarding
  protected attributes by iterative nullspace projection. arXiv 2004.07667
- [Ö] Belrose, N., Schneider-Joseph, D., Ravfogel, S., Cotterell, R. (2023). LEACE: Perfect
  linear concept erasure in closed form. arXiv 2306.03819
- [TM, kısmen] Takeuchi, M. (2026). Two-dimensional structural characterization of music
  genre communities in playlist co-occurrence networks. arXiv 2604.26119
