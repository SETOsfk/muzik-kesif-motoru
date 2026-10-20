# Algoritma doğrulaması: tam metinden formüller, hiperparametreler ve düzeltmeler

Araştırma notu 7 — 2026-10-20. Bu not, `1-oneri-algoritmalari.md` raporundaki iddiaları
(özellikle † işaretlileri) makalelerin **tam metninden** ve gerekirse resmî kıyas kodundan
doğruluyor. Her madde için: doğrulanan formül, önceki raporda doğru ve yanlış olanlar,
bizim veri boyutumuz için önerilen ızgara, sayfa/bölüm künyesi.

Kurgumuz: ikili `X ∈ {0,1}^{m×n}`, m = 482 liste, n ≈ 10.360 sanatçı. `d_j = Σ_p x_pj`
(sanatçı derecesi), `n_p = Σ_j x_pj` (liste boyu), `c_ij = Σ_p x_pi x_pj`. Sorgu
`q ∈ ℝ^n_{≥0}`: bir eksenin ağırlıklı kütüphane sanatçıları. Görev: `q_j = 0` olan
sahipsiz sanatçıları sıralamak. Gösterimde **i = tohum (kütüphane), j = aday**.

---

## 0. Erişim durumu (hangi iddia neye dayanıyor)

| Kaynak | Okunan | Durum |
|---|---|---|
| Steck 2019, EASE (arXiv 1905.03375) | tam metin | **D** |
| Steck 2020, EDLAE (NeurIPS, proceedings PDF + ek) | tam metin | **D** |
| Cooper ve ark. 2014, P3α (WWW'14 Companion, iw3c2 arşivi) | tam metin | **D** |
| Ferrari Dacrema ve ark. 2019 (arXiv 1907.06902) | tam metin | **D** |
| Ferrari Dacrema ve ark. 2021, TOIS (arXiv 1911.07698, Ek B Tablo 24) | tam metin | **D** |
| Dacrema kıyas kodu (`RP3betaRecommender.py`, `Compute_Similarity_Python.py`) | kaynak kod | **D** |
| Aiolli 2013 (RecSys'13) ve Aiolli 2012 ön çalışma | tam metin | **D** |
| Shen ve ark. 2021, GF-CF (arXiv 2108.07567) + resmî kod (`yshenaw/GF_CF`) | tam metin + kod | **D** |
| Eksombatchai ve ark. 2018, Pixie (arXiv 1711.07601) | tam metin | **D** |
| 2512.20896, 2603.07402, 2609.11876, 2305.12922, 2110.11402 | arXiv API özetleri; 2512.20896 tam metin | **D** (özet) |
| Rendle 2019, "Evaluation Metrics for Item Recommendation under Sampling" (arXiv 1912.02263) | tam metin | **D** (Krichene & Rendle 2020'nin öncülü) |
| **Paudel ve ark. TiiS 2016/17 (RP3β)** | **okunamadı** | ZORA deposu Anubis bot korumasıyla, ACM DL Cloudflare ile kapalı. Formül Dacrema 2019/2021 tanımından, resmî kıyas kodundan ve Kwieciński ve ark. 2023 (arXiv 2301.07946) yeniden ifadesinden. Künye S2/OpenAlex'ten doğrulandı. |
| **Christoffel ve ark. 2015, Blockbusters and Wallflowers** | **okunamadı** | Aynı engeller. Yalnız künye ve özet düzeyi. |
| **Steck 2018, Calibrated Recommendations** | **okunamadı** | ACM Cloudflare. Formül iki ikincil kaynaktan: Kaya & Bridge 2019 (RecSys, UCC deposu, §3.1) ve da Silva & Jannach 2025 derlemesi (arXiv 2507.02643, §3.1). İkisi birbiriyle tutarlı. |
| **Krichene & Rendle 2020 (KDD)** | **okunamadı** | ACM. Ana sonuç aynı çizginin öncül makalesinden (Rendle 2019). |

Atlatma yapılmadı: bot korumalı sayfalar için çözüm denenmedi. Wayback Machine vekilden
erişilemedi (429/bağlantı sıfırlandı).

Sayısal doğrulama betikleri (depoya değil, karalama alanına yazıldı):
- `/tmp/claude-0/-home-user-muzik-kesif-motoru/52bc46b8-24b6-56e9-8149-608600165b63/scratchpad/betik/woodbury_dogrula.py`:
  Woodbury'li EASE = doğrudan EASE, köşegen Λ dahil (fark ≤ 1e-15).
- `/tmp/claude-0/-home-user-muzik-kesif-motoru/52bc46b8-24b6-56e9-8149-608600165b63/scratchpad/betik/ease_limit.py`:
  m < n iken λ → 0 limitinin sonlu olduğu.

---

## 1. RP3β ve P3α (Cooper 2014; Christoffel 2015; Paudel 2016/17)

### 1.1 Doğrulanan tanım

**P3α (Cooper ve ark. 2014, §1 ve §4.3).** Ağırlıksız iki parçalı grafikte geçiş matrisi
`P = D⁻¹A`. `P_α`, P'nin her pozitif girdisinin α kuvveti alınarak elde edilir (Hadamard
kuvveti). Kullanıcı u için sıralama `P_α³(u, ·)`'ya göre yapılır. Özel durumlar:
`α = 0 → P_0 = A` ("#3-Paths", yol sayısı) ve `α = 1 → P³`. İkili veride:

```
P3α skoru:  p_uj = Σ_i Σ_p (x_ui/n_u)^α (x_pi/d_i)^α (x_pj/n_p)^α
           ∝ Σ_{i∈I(u)} W_ij                (u'nun (1/n_u)^α çarpanı sıralamayı değiştirmez)
W_ij = d_i^(−α) · Σ_p x_pi x_pj · n_p^(−α)
```

**RP3β.** P3α benzerliği adayın derecesinin β kuvvetine bölünür: `W_ij ← W_ij · d_j^(−β)`.
β = 0 iken P3α'dır (Dacrema 2019 §2; TOIS §3.2.3; Kwieciński ve ark. 2023 §2.3.3:
"((D⁻¹A)^∘α)³ ... divided by the popularity of the items raised to the power of β").

**Resmî kıyas uygulaması (Dacrema, `RP3betaRecommender.fit`).** Herkesin "RP3β" diye
kıyasladığı sürüm budur. İşlem sırası önemli:

```
Pui = satır-L1(X)            → x_pj / n_p
Piu = satır-L1(Xᵀ_ikili)     → x_pi / d_i
(α ≠ 1 ise) Pui ← Pui^∘α, Piu ← Piu^∘α
S = Piu · Pui                → S_ij = Σ_p (x_pi/d_i)^α (x_pj/n_p)^α
S_ij ← S_ij · d_j^(−β)       (topK seçiminden ÖNCE)
S_ii ← 0
her satır i (tohum) için en büyük topK girdi tutulur
normalize_similarity=True ise: her satır L1'e göre normalize edilir
skor: s = x_u · S            (ikili kullanıcı profili; bizde s = q · S)
varsayılanlar: alpha=1.0, beta=0.6, topK=100, normalize_similarity=True
```

### 1.2 Önceki raporla kıyas

- **Doğru:** §5.2'deki indirgeme
  `W_ij = (1/d_i^α) Σ_p x_pi x_pj n_p^(−α)`, `W_ij ← W_ij/d_j^β` ve §3.8'deki P3α formülü
  (P_uj = x_uj/n_u, P_jv = x_vj/d_j) kodla birebir tutuyor.
- **Eksik ve önemli: satır normalizasyonu tohum düğmesini yok ediyor.** Dacrema'nın
  `normalize_similarity=True` seçeneğinde her tohum satırı L1'e göre normalize ediliyor.
  `d_i^(−α)` satır boyunca sabit olduğu için bu çarpan **tamamen sadeleşiyor**. Yani §5.2
  tablosundaki "a = α (çok listede geçen tohumun sesini kısma)" düğmesi normalizasyon
  açıkken yoktur. Onun yerine "her tohum toplam 1 birim oy dağıtır" kuralı gelir. α o
  zaman yalnız liste boyu ağırlığını (`n_p^(−α)`) ayarlar. İki seçenek ayrı ayrı
  ölçülmeli: normalize açık (her tohum eşit oy) ve kapalı (popüler tohum az oy).
- **Düzeltme: α ızgarası [0, 1] ile sınırlanmamalı.** Cooper α'yı 0'dan 4'e 0,1 adımla
  taradı. Orta veride (ML-1M) en iyisi **α = 1,9** çıktı (Metric I %89,62 → %90,90).
  Dacrema'nın aralığı 0–2. Önceki rapor "ikili ve küçük veride 0–1 yeterli" diyordu, ama
  literatürün en iyi bölgesi 1'in üstünde olabiliyor. Bizim "250 sanatçılı dev liste"
  sorunumuz için α > 1 (uzun listeyi daha sert kısmak) tam ilgilenilen bölge.
- **topK yönü:** RP3β'da topK her TOHUM satırı için uygulanıyor ("her tohum en iyi K
  adayına oy verir"). Dacrema'nın ItemKNN'inde ise her ADAY sütunu için uygulanıyor
  (`Compute_Similarity_Python`: sütun = aday, en iyi K satır = tohum). Kıyasta bu fark
  bilinmeli. Bizim kurguda tohum satırı başına topK daha doğal.
- **Kısa yürüyüş bulgusu:** Cooper için doğrulandı. P³ ve P⁵ kıyaslandı, 3 adım en iyisi.
  s = 7, 9 yürüyüşlerin skoru azaldı (§5.3). P̂³ (benzetim) P³'e yakınsıyor: küçük veride
  20n adımda göreli fark 0,05, büyükte n adımdan azında. Christoffel 2015 tarafı
  doğrulanamadı.
- **Doğrulanamayan:** Paudel TiiS'teki orijinal RP3β'nın α içerip içermediği (yoksa
  P³'ün β ile yeniden sıralanması mı olduğu). Literatürdeki tüm kıyaslar Dacrema
  tanımını kullanıyor, bu yüzden pratikte önemi yok.
- **Raporlanmış en iyi değerler** (hepsi başka veride, yalnız yön göstergesi):

  | Kaynak | Veri | α | β |
  |---|---|---|---|
  | Cooper 2014 §4.3 | ML-1M | 1,9 (P3α) | — |
  | Paudel & Bernstein 2021 (arXiv 2102.09635), Tablo 8 | 8 veri | — | çoğunda 0,5, birinde 0,7 |
  | Kwieciński ve ark. 2023 (arXiv 2301.07946), hiperparametre eki | OLX Jobs, 185k ilan | 0,614 | 0,144 |
  | Dacrema kod varsayılanı | — | 1,0 | 0,6 |

### 1.3 Bizim veri için ızgara

- α ∈ {0; 0,25; 0,5; 0,75; 1; 1,25; 1,5; 2}
- β ∈ {0; 0,1; 0,2; 0,3; 0,4; 0,5; 0,6; 0,8; 1,0}
- topK (tohum satırı başına) ∈ {20, 50, 100, 200, tümü}
- normalize_similarity ∈ {açık, kapalı}
- Toplam 8 × 9 × 5 × 2 = 720 yapılandırma, her biri ms. Dacrema 35–50 noktalık Bayesçi
  arama yaptı. Bizde tam ızgara ucuz, ama seçim yanlılığı için A/B yarı ayrımı (rapor 1
  §6.2) şart.

### 1.4 Künye

Cooper, Lee, Radzik, Siantos, WWW'14 Companion, s. 811–816, §1, §4.3, §5.3–5.4.
Dacrema 2019 §2 "Baselines" (Denk. 3). TOIS 2021 §3.2.3. Kod:
`MaurizioFD/RecSys2019_DeepLearning_Evaluation/GraphBased/RP3betaRecommender.py`.
Paudel, Christoffel, Newell, Bernstein, ACM TiiS 7(1):1, doi:10.1145/2955101 (künye D,
metin †). Christoffel, Paudel, Newell, Bernstein, RecSys'15, doi:10.1145/2792838.2800180
(künye D, metin †).

---

## 2. EASE (Steck 2019), EDLAE (Steck 2020) ve m ≪ n için Woodbury

### 2.1 Doğrulanan formüller

```
Skor (Denk. 1):        S_uj = X_u· · B_·j
Amaç (Denk. 2–3):      min_B ‖X − XB‖²_F + λ‖B‖²_F   s.t. diag(B) = 0
Lagrange (§3.1):       B̂ = (XᵀX + λI)⁻¹ (XᵀX − diagMat(γ))
Denk. 4:               P̂ = (XᵀX + λI)⁻¹
Denk. 7:               B̂ = I − P̂ · diagMat(1 ⊘ diag(P̂))
Denk. 8:               B̂_ij = 0 (i = j);   B̂_ij = −P̂_ij / P̂_jj (aksi hâlde)
```

- Algoritma 1 (numpy): `G[diag] += λ; P = inv(G); B = P / (−diag(P)); B[diag] = 0`.
- Tek hiperparametre λ. **Raporlanan en iyi λ** (§5.2): ML-20M ≈ 500, Netflix ≈ 1.000,
  MSD ≈ 200. ML-10M'de (kullanıcı başına ≤ %30 eğitim, zayıf genelleme) λ = 3.000 (Tablo 2
  tartışması). SLIM'de tipik λ ~1.
- Öğrenilen ağırlıkların **~%60'ı negatif**, bütün veri setlerinde. Negatifleri sıfırlamak
  (EASE ≥ 0) isabeti SLIM düzeyine düşürüyor (Tablo 1).
- Steck'e göre ölçek dönüşümleri (merkezleme, korelasyon) sıralamayı standart hata
  düzeyinde değiştiriyor (§3.2 sonu).
- Dacrema TOIS Tablo 24: EASE `l2 norm` ∈ 10⁰–10⁷, log-uniform. **Doğrulandı.**

**EDLAE (Steck 2020).**
- Dropout ile gürültü giderme, L2'ye denk (Denk. 3–4):
  `Λ = (p/q) · dMat(diag(XᵀX))`, q = 1 − p. İkili X'te `Λ_jj = (p/(1−p)) · d_j`, yani
  **popülerlikle orantılı L2**.
- DLAE tam rank çözümü (Denk. 5): `B = I − (XᵀX + Λ)⁻¹Λ`. Bu çözümün köşegeni sıfır
  DEĞİL, dolayısıyla kimliğe aşırı uyumu tam engellemiyor.
- EDLAE tam vurgu (b = 0), tam rank (Denk. 7–9):
  `B̂ = I − C · dMat(1 ⊘ diag(C))`, `C = (XᵀX + Λ)⁻¹`.
  Yani **EASE'in λI yerine Λ ile yazılmış hâli.**
- Tablo 1 dipnotu (rank-1000 deneyleri): `Λ̃ = Λ + λI`, iki hiperparametre (p, λ).
  Önceki raporun yazdığı `Λ = λI + p/(1−p)·diagMat(diag(G))` bu Λ̃'dır. Kombinasyon
  olarak doğru, ama makalenin tam rank kapalı formu yalnız Λ ile verilmiş.
- En iyi p ve λ değerleri ana metinde yazmıyor (kod GitHub'da). Bu yüzden önceki raporda
  bunlar için sayı verilmemesi doğru.

### 2.2 Woodbury: geçerli mi, diag(P) nasıl ucuz hesaplanır? — EVET, geçerli

Herhangi bir köşegen ve pozitif Λ için (λI, EDLAE Λ ya da Λ̃) özdeşlik kesindir:

```
Li = Λ⁻¹ (köşegen)
P  = (XᵀX + Λ)⁻¹ = Li − Li Xᵀ K⁻¹ X Li,      K = I_m + X Li Xᵀ   (482 × 482)
Λ = λI özel hâli:  P = (1/λ)(I_n − Xᵀ (λI_m + XXᵀ)⁻¹ X)

K = L Lᵀ (Cholesky),  Y = L⁻¹ (X · diag(Li))         (m × n, yoğun ≈ 482×10.360 ≈ 40 MB float64)
diag(P)_j = Li_j − ‖Y_·j‖²
q P       = q⊙Li − Li ⊙ ( Xᵀ K⁻¹ X (q⊙Li) )
EASE skoru: s_j = q_j − (qP)_j / P_jj     →  aday (q_j = 0) için  s_j = −(qP)_j / P_jj
```

- **Sayısal doğrulama:** m = 60, n ≈ 400 rastgele ikili X ve dört (λ, κ) çifti için
  doğrudan `inv(XᵀX + Λ)` ile Woodbury skorları arasındaki en büyük fark 1,4e-16 ile
  1,0e-15 arasında. diag(P) birebir eşit (`woodbury_dogrula.py`).
- **Maliyet:** Cholesky O(m³) ≈ 10⁸ flop, Y için O(m²·n) ≈ 2,4×10⁹ flop. Her ikisi de
  saniyenin altında. Bunlar λ (ve κ) başına bir kez hesaplanır. Sorgu başına iş yalnız iki
  seyrek çarpım ve bir m×m çözüm: milisaniye.
- **Yeni bulgu (önceki raporda yok): m < n iken λ → 0 limiti sonludur.**
  `B(λ) → B₀ = I − Π · dMat(1 ⊘ diag Π)`, burada `Π = I − X⁺X`, yani X'in sıfır uzayına
  izdüşüm. Sayısal olarak: λ = 0,1 / 1e-3 / 1e-6 için `‖B(λ) − B₀‖_max` = 5,5e-3 /
  5,6e-5 / 5,7e-8 (`ease_limit.py`). Yorum: küçük λ'da EASE, sorgunun "listelerin
  gerdiği uzaya" düşmeyen artığını puanlar. Önceki raporun λ → ∞ yorumu
  (`B_ij ≈ G_ij/(λ − d_j)`, ham birlikteliğe dönüş) doğru. Küçük λ ucu "patlamaz" ama
  `Π_jj ≈ 0` olan sanatçılarda bölme kararsızlaşabilir. Pratikte λ > 0 tutulmalı.

### 2.3 Bizim veri için ızgara

Steck'in λ'larını ortalama dereceye oranlayalım (yaklaşık d̄ = nnz/n):
- ML-20M: d̄ ≈ 500, λ = 500, λ/d̄ ≈ 1
- Netflix: d̄ ≈ 3.200, λ = 1.000, λ/d̄ ≈ 0,3
- MSD: d̄ ≈ 830, λ = 200, λ/d̄ ≈ 0,25
- ML-10M %30: d̄ ≈ 280, λ = 3.000, λ/d̄ ≈ 10

Önerilen ızgara ölçekten bağımsız yazılsın:
- λ = c · d̄, c ∈ {0,03; 0,1; 0,3; 1; 3; 10; 30}. d̄ veriden hesaplanır; listelerde
  tahminen 2–5 aralığında.
- EDLAE: κ = p/(1−p) ∈ {0; 0,25; 0,5; 1; 2}, yani p ∈ {0; 0,2; 0,33; 0,5; 0,67}.
  Önceki raporun {0, 0,25, 1, 4} önerisi de makul. 4 (p = 0,8) üst uç.

### 2.4 Künye

Steck, WWW'19, arXiv 1905.03375v1: §2 Denk. 1; §3 Denk. 2–3; §3.1 Denk. 4–8; §3.3
Algoritma 1; §5.2 (λ değerleri, %60 negatif ağırlık); Tablo 1–2. Steck, NeurIPS 2020
"Autoencoders that don't overfit towards the Identity": §2 Denk. 1–2; §3 Denk. 3–5;
§4 Teorem (Denk. 6); §4.1.1 Denk. 7–9; §6 Tablo 1 (Λ̃ = Λ + λI). Dacrema TOIS Tablo 24
(s. 20:45).

---

## 3. Aiolli 2013: asimetrik kosinüs ve yerellik

### 3.1 Doğrulanan formül (§3.1, §3.2 Denk. 5, §3.3)

```
S_α(a, b) = P(a|b)^α · P(b|a)^(1−α) = |R(a) ∩ R(b)| / ( |R(a)|^α · |R(b)|^(1−α) ),   0 ≤ α ≤ 1

Öğe tabanlı:  w_ij = |U(i) ∩ U(j)| / ( |U(i)|^α · |U(j)|^(1−α) )
              h_ui = Σ_{j ∈ I(u)} f(w_ij),   f(w) = w^q   (q ∈ ℕ, "yerellik")
              ⇒  i = puanlanan ADAY, j = kullanıcının öğesi (TOHUM)
Kullanıcı tabanlı: w_uv = |I(u) ∩ I(v)| / ( |I(u)|^α · |I(v)|^(1−α) ),
              h_ui = Σ_{v ∈ U(i)} f(w_uv)
```

- α = 0 → `P(i|j) = c_ij/|U(j)|` (tohum koşullu), α = ½ → kosinüs, α = 1 → `P(j|i)`.
- q = 0: düz sayım. q büyüdükçe küçük benzerlikler sıfıra iner. q → ∞ iken
  `(Σ w^q)^{1/q} → max w`, yani sıralama MAX birleştirmesine yaklaşır.
- **Asimetrik tahmin (§4.1, Denk. 6):**
  `r̂_ui = x_uᵀy_i / (‖x_u‖^{2β} ‖y_i‖^{2(1−β)})`. Kullanıcı tabanlıda bu,
  `Σ_{v∈U(i)} w_uv / |U(i)|^{1−β}` olur: adayın popülerliğine (1−β) üssüyle bölme.
- **Kalibrasyon (§4.2):** her öğe için pozitif çiftlerdeki ortalama m_i ve en büyük M_i
  skor bulunur, skor parçalı doğrusal biçimde [0, 1]'e eşlenir, θ = 0,5.

### 3.2 Raporlanan sayılar (MSD, mAP@500, §5.3)

| Yapılandırma | mAP@500 |
|---|---|
| Popülerlik | 0,02262 |
| IS (öğe tabanlı) α = 0, q = 1 / 2 / 3 / 4 / 5 | 0,12224 / 0,16581 / **0,17144** / 0,17004 / 0,16830 |
| IS α = ½ (kosinüs), q = 1 … 5 | **0,16439** (q=1) → 0,14621 (q=5); azalıyor |
| US (kullanıcı tabanlı) α = 0, q = 1 … 7 | en iyisi q=5: 0,13400 |
| US α = ½, q = 1 … 7 | en iyisi q=6: 0,14487 |
| **IS α = 0,15, q = 3** (Şekil 1a) | **0,177322** |
| US α = 0,6, q = 5 (Şekil 1b) | 0,143551 |
| US α = 0,5, q = 4, β = 0,7 (Tablo 2) | 0,16229 |
| IS α = 0,15, q = 3, **kalibreli** | **0,181084** (en iyi tek sıralayıcı) |
| Stokastik birleşim IS(0,8) + US(0,2), US α = 0,3, q = 5 (Tablo 3) | 0,17896 (yarışmayı kazanan yapılandırma) |
| Doğrusal birleşim IS + US, en iyi (0,8 / 0,2) (Tablo 4) | 0,18092 |
| **ML-1M** (Tablo 5): IS α = 0,6, q = 1 / US α = 0,6, q = 6 / US β = 0,8 | 0,18146 / 0,18549 / 0,18984 |

### 3.3 Önceki raporla kıyas

- **YANLIŞ (yön ters): indisler yer değiştirmiş.** Önceki rapor
  `S_ij = |U_i ∩ U_j| / (|U_i|^α · |U_j|^(1−α))` ve `s_uj = Σ_{i∈I(u)} S_ij^q` yazmış.
  Burada i tohum, j aday olduğu için α TOHUMUN derecesine gidiyor. Aiolli'de α ADAYIN
  derecesine, 1−α tohumun derecesine gidiyor. α = 0,15 için doğru okuma:
  - aday derecesi üssü **b = 0,15** (çok hafif popülerlik cezası),
  - tohum derecesi üssü **a = 0,85**,
  - yani neredeyse koşullu olasılık `P(aday | tohum)`.

  Önceki raporun yazdığı biçimde α = 0,15 adayı 0,85 üssüyle cezalandırırdı, ki bu
  Aiolli'nin bulgusunun tersi. Dacrema'nın uygulaması Aiolli ile tutarlı: payda
  `‖x_aday‖^{2α} · ‖x_tohum‖^{2(1−α)}`, ikili veride `d_aday^α · d_tohum^(1−α)`.
- **Kısmen yanlış:** "kalibrasyonla 0,181" değeri birleşimin değil, kalibreli tek öğe
  tabanlı sıralayıcının (0,181084). Kazanan birleşim 0,17896 (stokastik, Tablo 3).
- **Doğru:** α = 0,15, q = 3 en iyi öğe tabanlı. α = 0 iken q = 1 → 3 aralığında
  0,122 → 0,171. q → ∞ ≈ MAX.
- **Eklenmesi gereken:** en iyi değerler veriye bağlı. ML-1M'de IS için q = 1 ve
  α = 0,6 en iyisi, kullanıcı tabanlı öğe tabanlıyı geçiyor. Yani "q = 3–5 literatürün
  en iyisi" genellenemez. MSD (müzik, uzun kuyruk, seyrek) bize daha yakın, ama
  ölçülmeli.
- **Bizim için yeni bir kıyas çizgisi:** "kullanıcı tabanlı" = **liste-kNN**. m = 482
  olduğu için çok ucuz:
  `w_p = ( Σ_i q_i x_pi / (|q|^{α'} · n_p^{1−α'}) )^{γ'}`, `s_j = Σ_p w_p x_pj / d_j^{1−β'}`.
  Aiolli'nin MSD bulgusu α' ≈ 0,5–0,6, γ' ≈ 4–6, β' ≈ 0,7.

### 3.4 Bizim veri için ızgara

Öğe tabanlı, Aiolli/Dacrema uyumlu:

```
S_ij = c_ij^(ρ) / ( d_i^(1−a) · d_j^(a) + h ),     i = tohum, j = aday
s_j  = Σ_i q_i · S_ij^γ
```

- a (Aiolli α) ∈ {0; 0,15; 0,3; 0,5; 0,75; 1}
- γ (Aiolli q) ∈ {1, 2, 3, 5, 8}
- h (ek, payda) ∈ {0; 0,5; 1; 2; 5}. Bkz. §4.2'deki ölçek uyarısı.
- ρ (liste boyu ağırlığı; `c^(ρ) = Σ_p x_pi x_pj n_p^(−ρ)`) ∈ {0; 0,5; 1}. Dacrema'daki
  TF-IDF/BM25 satır ağırlığının sürekli karşılığı.
- Liste-kNN: α' ∈ {0,3; 0,5; 0,7}, γ' ∈ {1, 3, 5, 7}, β' ∈ {0,5; 0,7; 1}.

### 3.5 Künye

Aiolli, "Efficient Top-N Recommendation for Very Large Scale Binary Rated Datasets",
RecSys'13, s. 273–280 (Dacrema TOIS kaynakçası [1]): §3.1–3.3, §4.1 Denk. 6, §4.2,
§5.3 Tablo 1–4 ve Şekil 1, §5.5 Tablo 5. Aiolli 2012 ön çalışma §2.2–2.3 aynı formülleri
veriyor.

---

## 4. Ferrari Dacrema ve ark.: kıyas çizgileri ve ayarlama uzayı

### 4.1 RecSys 2019 (arXiv 1907.06902, §2)

- **Kıyas çizgileri:** TopPopular, ItemKNN, UserKNN, ItemKNN-CBF, ItemKNN-CFCBF, P3α,
  RP3β.
- ItemKNN benzerliği (Denk. 1): `s_ij = r_i·r_j / (‖r_i‖‖r_j‖ + h)`. Puanlar isteğe bağlı
  TF-IDF ya da BM25 ile ağırlıklanıyor. Norm paydası açılıp kapatılabiliyor. **h (shrink)
  paydaya EKLENİYOR.**
- P3α (Denk. 3): `p_ui = (r_ui/N_u)^α`, `p_iu = (r_ui/N_i)^α`, `s_ij = Σ_v p_jv p_vi`.
- **Ayarlama:** Scikit-Optimize ile Bayesçi arama, algoritma başına 35 nokta (ilk 5
  rastgele). k ∈ 5–800, h ∈ 0–1000, α ve β ∈ 0–2 (gerçel).

### 4.2 TOIS 2021 (arXiv 1911.07698, §3.1–3.2 ve Ek B Tablo 24)

- Bayesçi arama, algoritma başına **50 nokta (ilk 15 rastgele)**. Erken durdurmalı epok
  seçimi. Sonra eğitim ve doğrulama birleşiminde yeniden uydurma.
- Kıyas listesi: TopPopular, UserKNN, ItemKNN (+ CBF ve CFCBF), P3α, RP3β, iALS, PureSVD,
  SLIM ElasticNet, EASE^R.
- Benzerlik türleri: Jaccard, Kosinüs, Asimetrik Kosinüs, Dice-Sørensen, Tversky.

| Algoritma | Hiperparametre | Aralık (dağılım) |
|---|---|---|
| KNN cosine | topK; shrink; normalize; feature weighting | 5–1000; 0–1000; {T, F}; {none, TF-IDF, BM25} |
| KNN dice / jaccard | topK; shrink; normalize | 5–1000; 0–1000; {T, F} |
| KNN asymmetric | topK; shrink; normalize; asymmetric alpha; feature weighting | 5–1000; 0–1000; **True (sabit)**; **0–2**; {none, TF-IDF, BM25} |
| KNN tversky | topK; shrink; normalize; tversky alpha; tversky beta | 5–1000; 0–1000; True; 0–2; 0–2 |
| P3alpha | topK; alpha; normalize similarity | 5–1000; 0–2; {T, F} |
| RP3beta | topK; alpha; beta; normalize similarity | 5–1000; 0–2; 0–2; {T, F} |
| SLIM ElasticNet | topK; l1 ratio; alpha | 5–1000; 10⁻⁵–1 (**log-uniform**); 10⁻³–1 (**uniform**) |
| PureSVD | faktör | 1–350 |
| iALS | faktör; epok; güven ölçekleme; alpha; epsilon; reg | 1–200; 1–500 (erken durdurma); {linear, log}; 10⁻³–50 (log); 10⁻³–10 (log); 10⁻⁵–10⁻² (log) |
| EASE^R | l2 norm | 10⁰–10⁷ (log-uniform) |

Tablo dipnotları: KNN'de "normalize" paydanın kullanılması demek. P3α/RP3β'da
"normalize similarity" benzerlik matrisinin satırlarına L1 normalizasyonu demek.

Koddan ek formüller (`Compute_Similarity_Python.py`):
- asymmetric: `W[tohum, aday] = c / (d_aday^α · d_tohum^(1−α) + h)`. Aiolli ile tutarlı.
- tversky: `W = c / (c + α(d_aday − c) + β(d_tohum − c) + h)`.
- jaccard: `c / (d_i + d_j − c + h)`. dice: `c / (d_i + d_j + h)`.

### 4.3 Önceki raporla kıyas

- **Doğru:** topK 5–1000, shrink 0–1000, benzerlik türleri, asimetrik α 0–2, TF-IDF/BM25,
  RP3β α/β 0–2, EASE 10⁰–10⁷.
- **Düzeltme (SLIM):** l1_ratio 10⁻⁵–1 log-uniform. alpha 10⁻³–1 **uniform** (önceki
  rapor ikisini de log ızgara gibi yazmıştı).
- **Düzeltme (shrink türü):** Dacrema'nın shrink'i **paydaya eklenen** sabit:
  `c/(‖·‖‖·‖ + h)`. Koren tipi çarpımsal büzülme `n_ij/(n_ij + h)` ise destek sayısına
  bağlı. Önceki rapor §3.3'te ikisini aynı şey gibi anıyor. Etkileri farklı: ek payda
  küçük dereceli ÇİFTLERİ (küçük paydayı) cezalandırır, çarpımsal büzülme az ORTAK
  GÖZLEMİ cezalandırır. Projedeki `KANIT_BUZULMESI = n/(n+k)` çarpımsal türdür. Dacrema
  shrink'i ayrı bir düğme olarak denenebilir.
- **Ölçek uyarısı:** h = 1000 Dacrema'nın verilerinde (d ~ yüzler–binler) anlamlı. Bizde
  `√(d_i d_j)` çoğunlukla 1–20 aralığında, bu yüzden h aralığı {0; 0,5; 1; 2; 5} gibi
  yeniden ölçeklenmeli.
- 2019 sürümü yalnız kosinüs ItemKNN içeriyor. Asimetrik ve Tversky ancak TOIS 2021'de
  geliyor.

---

## 5. GF-CF (Shen ve ark., CIKM 2021)

### 5.1 Doğrulanan formül

```
§2:   D_U = Diag(R·1),  D_I = Diag(1ᵀR),   R̃ = D_U^(−½) R D_I^(−½),   P̃ = R̃ᵀR̃
Denk. 6 (ideal alçak geçiren):   h(λ_i) = 1  (λ_i ≤ λ̄),  0 aksi hâlde
Denk. 22 (GF-CF):   s_u = r_u · ( R̃ᵀR̃ + α · D_I^(−½) Ū Ūᵀ D_I^(½) ),
                    Ū = R̃'nin ilk K tekil vektörü (öğe uzayında)
```

Resmî kod (`Table3&4/model.py`, `GF_CF`):
- `sparsesvd(norm_adj, 256)`, yani **K = 256**.
- `ret = U_2 + 0.3 * U_1`, yani **α = 0,3** (Gowalla, Yelp2018).
- **Amazon-book için `ret = U_2`:** yalnız doğrusal süzgeç, ideal alçak geçiren kısım
  KAPALI.

### 5.2 Önceki raporla kıyas

- **Doğru:** formülün yapısı (önceki rapor α yerine γ yazmış).
- **Doğru:** Amazon-book'ta ~%70 kazanç. recall@20 0,0710 ve LightGCN-64 0,0411, yani
  +%73 (Tablo 3; Tablo 4'te LightGCN-512'ye karşı bile 0,0710 / 0,0485). **Ama** resmî
  koda göre bu sayı yalnız doğrusal kısımdan (R̃ᵀR̃) geliyor.
- **Düzeltme:** "P̃, kullanıcı tarafında n_p^(−½) normalizasyonlu RP3β noktası" ifadesi
  eksik. R̃'nin girdisinde n_p^(−½) var, ama Gram matrisinde
  `P̃_ij = Σ_p x_pi x_pj / (n_p · √(d_i d_j))`. Yani ailede **ρ = 1, a = b = ½** noktası:
  liste boyuna tam ters ağırlık ve simetrik kosinüs.
- m = 482 iken R̃'nin rankı ≤ 482. K = 256 bizde rankın yarısından fazlası ve "alçak
  geçiren" anlamını yitirir.

### 5.3 Bizim veri için ızgara

- K ∈ {8, 16, 32, 64, 128}
- α ∈ {0; 0,1; 0,3; 1}. α = 0 = yalnız doğrusal süzgeç ve zaten RP3β ailesinin bir
  noktası.
- SVD tek seferlik, 482 × 10k matriste saniyeler sürer.

### 5.4 Künye

arXiv 2108.07567: §2 (R̃, Ã, P̃), Denk. 6, §4.3 Denk. 22, §5 Tablo 3–4. Kod:
`github.com/yshenaw/GF_CF`, `Table3&4/model.py` satır 255–290.

---

## 6. Kalibre öneriler (Steck 2018)

**Uyarı:** birincil metin okunamadı. Aşağısı iki bağımsız ikincil kaynağın uyuşan
ifadesi.

### 6.1 Formül

```
p(g|u) = Σ_{i∈H_u} w_ui · p(g|i) / Σ_{i∈H_u} w_ui          (hedef dağılım; deneylerde w_ui = 1)
q(g|u) = Σ_{i∈I}  w_r(i) · p(g|i) / Σ_{i∈I} w_r(i)         (liste dağılımı; deneylerde w_r(i) = 1)
p(g|i): öğenin türleri arasında eşit pay (Σ_g p(g|i) = 1)
q̃(g|u) = (1 − α) q(g|u) + α p(g|u),   α = 0,01
C_KL(p, q) = KL(p ‖ q̃) = Σ_g p(g|u) log( p(g|u) / q̃(g|u) )
I* = argmax_{I, |I| = N}  (1 − λ) · s(I) − λ · C_KL(p, q(I)),   s(I) = Σ_{i∈I} s(u, i),   0 ≤ λ ≤ 1
```

- **Açgözlü yeniden sıralama:** boş listeden başlanır, her adımda
  `f(i, I) = (1 − λ) s(u,i) + λ · [−(C_KL(p, q(I ∪ {i})) − C_KL(p, q(I)))]` en büyük
  olan aday eklenir. Steck'in "surrogate submodular" savıyla (1 − 1/e) yaklaşıklık
  garantisi.
- Aday havuzu tipik olarak temel sıralayıcının ilk 100'ü (derleme §3.1.2).
- λ genelde 0'dan 1'e 0,1 adımla taranıyor (derleme §3.1.6).

### 6.2 Önceki raporla kıyas ve bizdeki yeri

- Önceki raporda Steck 2018 yalnız adıyla geçiyordu. Formül ilk kez burada yazıldı.
- **Bizde g = eksen** olabilir: `p(k|sanatçı)` = FCM üyeliği. Ama ürün kullanıcıya TEK
  eksen seçtiriyor. Tek eksenli listede eksenler arası kalibrasyon anlamsızdır.
- Anlamlı olduğu iki yer:
  - (a) karma deste (K21), ya da "tüm kütüphane" modu: eksen payları kütüphanedeki
    paylara yaklaştırılır;
  - (b) eksen İÇİNDE alt tarzlara (CLAP ses kümeleri, K18) göre kalibrasyon: listenin
    tek bir alt tarza yığılmasını engeller.
- Izgara: λ ∈ {0; 0,2; 0,4; 0,6; 0,8}, α = 0,01 sabit, havuz = ilk 100 aday.

### 6.3 Künye

Steck, RecSys'18, s. 154–162, doi:10.1145/3240323.3240372 (metin †). Kaya & Bridge,
"A comparison of calibrated and intent-aware recommendations", RecSys'19, §3.1
Denk. 11–16 (UCC CORA deposu). da Silva & Jannach, "Calibrated Recommendations: Survey
and Future Directions", arXiv 2507.02643, §3.1.2–3.1.7 Denk. 1, 3–7.

---

## 7. Pixie: çok tohumlu birleştirme (Eksombatchai ve ark., WWW 2018)

### 7.1 Doğrulanan formüller (§3.1, Algoritma 2–3)

```
Denk. 1 (ölçek çarpanı):  s_q = |E(q)| · (C − log |E(q)|),   C = max_{p∈P} |E(p)|  (en büyük pin derecesi)
Denk. 2 (adım bütçesi):   N_q = w_q · N · s_q / Σ_{r∈Q} s_r
Denk. 3 (çoklu isabet):   V[p] = ( Σ_{q∈Q} √(V_q[p]) )²
Erken durma: n_p aday en az n_v kez ziyaret edilince yürüyüşler kesilir (çalışma süresi yarıya iner).
```

- Her tohum q için ayrı bir yürüyüş yapılır ve sayaç V_q tutulur.
- **w_q yalnız adım bütçesine giriyor** (Denk. 2). Birleştirme formülünde açıkça yer
  almıyor. Ama `V_q ≈ N_q · π_q`, bu yüzden ağırlık dolaylı olarak giriyor.
- **Belirlenimci (yürüyüşsüz) karşılığı:** `π_i` = i tohumunun normalize edilmiş skor
  vektörü (örneğin satır-L1 RP3β satırı) ise:
  `s_j = ( Σ_i √( ŵ_i · π_i(j) ) )²`, `ŵ_i = q_i · s_i / Σ_r s_r`.
- **Yazım uyarısı:** C en büyük derece olarak yazıldığında `C − log d ≈ C` olur ve s_q
  derecede neredeyse doğrusaldır. Oysa metin "alt doğrusal" diyor. Formül basıldığı gibi
  aktarıldı, ama muhtemelen `C = log max derece` kastedilmiş. Uygularken ikisi de denenmeli
  ya da bu çarpan atlanmalı.
- **Budama (§3.2):** konu dağılımı entropisi yüksek (dağınık) panolar grafikten atılıyor.
  Yüksek dereceli pinlerin derecesi |E(p)|^δ'ya indiriliyor (konu uyumu düşük kenarlar
  atılıyor). Budama "%58 daha ilgili öneri" veriyor.
  **Bizim için doğrudan ders:** dağınık "karışık" listeler (sanatçı/tarz entropisi
  yüksek) ya atılmalı ya düşük ağırlıklanmalı. Bu, `n_p^(−ρ)`'den farklı bir düğme:
  uzunluk değil, çeşitlilik.

### 7.2 Önceki raporla kıyas

- **Doğru:** `V[j] = (Σ_seed √V_seed[j])²` ve "tohum başına adım bütçesi dereceyle alt
  doğrusal ölçeklenir".
- **Kesinleştirilen:** s_q formülü (yukarıda) ve w_q'nun yalnız bütçeye girdiği.
- Kare kök birleştirmesi, γ < 1 kuvvet ortalamasının (Σ v^{½})² özel hâli. Aiolli'nin
  γ > 1'i ise büyük tekil bağları öne çıkarıyor. İkisi zıt yönler:
  - Pixie: çok tohumdan gelen uzlaşmayı ödüllendirir.
  - Aiolli: tek güçlü bağı ödüllendirir.

  Tek bir aile hâlinde ölçülebilir: `s_j = (Σ_i (q_i S_ij)^{1/τ})^τ`. τ = 2 Pixie,
  τ = 1 toplam, τ → 0'a yakın uç MAX.

### 7.3 Künye

arXiv 1711.07601: §3.1 (Algoritma 1–3, Denk. 1–3), §3.2 (budama, δ), §4.2 (erken durma).

---

## 8. 2025–2026 doğrusal otokodlayıcı makaleleri (arXiv API özetleri)

| arXiv | Künye | Ne öneriyor | Bize uygulanır mı |
|---|---|---|---|
| **2512.20896** | Onishi, Hayashi, Kamigaito, "Accurate and Diverse Recommendations via Propensity-Weighted Linear Autoencoders", **SIGIR-AP 2025** | Güç yasası tabanlı IPS popüler öğeleri aşırı cezalandırıyor. Yerine log-sigmoid eğilim: `p_j = 1/(1 + exp(−α₀ − β₀ log(N_j + 1)))`. α₀, p = 0,5 orta noktaya gelecek biçimde sabitleniyor (Denk. 10): `α₀ = −β₀ (log(min N + 1) + log(max N + 1))/2`. Ağırlık `w_j = 1/p_j`. Kapalı form (Denk. 12–13): `B_w = B̂ · diag(w)`, yani yalnız **aday sütununu w_j ile çarpmak**. β₀ ∈ {0,1 … 0,9}. Coverage@100 ML-20M'de +%280, Netflix'te ~+%150; isabet korunuyor. | **Evet, doğrudan.** Her öğe-öğe modeline (EASE, RP3β, ItemKNN) skor sonrası `s_j ← s_j · w_j` olarak eklenir. `d_j^(−β)`'nın sınırlı, popülerler arasında yumuşak alternatifi. Tek düğme β₀. LOAO'da β ile kıyaslanmalı. |
| **2603.07402** | Guo, Li, Zhou, Zhou, Jin, "Generalizing Linear Autoencoder Recommenders with Decoupled Expected Quadratic Loss", **ICLR 2026** | EDLAE'yi DEQL kaybına genelliyor. Steck'in yalnız b = 0 için verdiği kapalı formu b > 0 aralığına taşıyor. Hesaplanabilirlik için Miller'ın matris tersi teoremi kullanılıyor. b > 0 çözümleri, b = 0 EDLAE'yi geçiyor. | Kuramsal olarak evet, ama ek hiperparametre (a, b, p). Maliyetinin Woodbury ile m×m'ye inip inmediği özetten anlaşılmıyor. **Düşük öncelik.** EASE/EDLAE kazanırsa bakılır. |
| **2609.11876** | Li, Liu, Jin, Zhou, Liu, Gao, Ren, "On the Regularization Landscape for the Linear Recommendation Models", Eylül 2026 | Önde gelen doğrusal modellerin hepsi ya nükleer norm ya Frobenius norm düzenlileştiricisi ekliyor. Nükleer normlular düşük ranklı ve kapalı formlu ama katı. Frobeniuslar daha güçlü ama tam ranklı ya da ADMM istiyor. İki yeni düşük ranklı kapalı form öneriliyor. | Bizde rank ≤ 482 olduğu için düşük ranklı model doğal. Yalnız özet okundu. **Düşük öncelik**, merak listesi. |
| 2305.12922 | Moon, Kim, Lee, "It's Enough: Relaxing Diagonal Constraints…", **SIGIR 2023** (yazar ve yayın yeri artık D) | `diag(B) = 0` yerine eşitsizlik kısıtı (RLAE, RDLAE). Sıfır köşegen düşük ranklı PC'lerin etkisini azaltıp popüler olmayan öğeleri kötüleştiriyor. Gevşetmek uzun kuyruğu iyileştiriyor. | Evet, EASE kolu için bir düğme (köşegen eşiği). Uzun kuyruk hedefimizle uyumlu. Orta öncelik. |
| 2110.11402 | Steck & Garcia Garcia 2021, "On the Regularization of Autoencoders" | Düşük ranklı EDLAE'nin dışbükey olmayan amacına kapalı formlu yaklaşık çözüm. Doğrusal olmayan AE, aynı son katman boyutundaki doğrusal AE'den daha iyi uyamaz. | Yalnız düşük ranklı yol için. Bizde tam rank zaten ucuz. Düşük öncelik. |

---

## 9. Örneklemeli ölçütler (Krichene & Rendle 2020)

Ana sonuç, aynı çizginin öncül makalesinden (Rendle 2019, arXiv 1912.02263, §1 ve §5)
doğrulandı. KDD metni okunamadı.

Örneklemeli ölçütler (ilgili öğe + az sayıda rastgele negatif) tam ölçütlerle **tutarsız**:
"A, B'den iyi" yargısını beklenen değerde bile korumuyorlar. Örneklem küçüldükçe ölçütler
arasındaki fark kayboluyor ve m = 1 negatif uç durumunda hepsi AUC'ye (sıranın doğrusal
iskontosuna) çöküyor. Yani üst sıraya odaklanan ölçütlerin (recall@K, NDCG) özelliği
yitiyor. Öneri: üst sıra ölçütü önemliyse örnekleme yapılmamalı; yapılıyorsa okur ölçülen
şeyin adındaki şey olmadığını bilmeli. KDD 2020 sürümü ayrıca örnekleme düzeltme
yöntemleri öneriyor (†, metin okunamadı).

**Bizde:** tam sıralama kullanılıyor. Doğru, korunmalı. "100 negatifle sıralamanın tersine
dönmesi" ayrıntısı †.

---

## 10. Uygulanacak formüller (tek yerde)

Hepsi numpy/scipy ile. Gösterim: i tohum, j aday. `q` eksen sorgusu, d derece, n liste boyu.

**F1 — RP3β / P3α (Dacrema uyumlu):**
```
S_i· = d_i^(−α) · ( x_iᵀ diag(n^(−α)) X ) ⊙ d^(−β);   S_ii = 0;   satır başına topK;   [satır-L1]
s = Σ_i q_i S_i·
```

**F2 — Genelleştirilmiş ItemKNN (Aiolli + Dacrema):**
```
S_ij = (Σ_p x_pi x_pj n_p^(−ρ)) / ( d_i^(1−a) d_j^(a) + h )
s_j  = Σ_i q_i S_ij^γ
```

**F3 — Liste-kNN (Aiolli kullanıcı tabanlı):**
```
w_p = ( Σ_i q_i x_pi / (‖q‖₁^{α'} n_p^{1−α'}) )^{γ'}
s_j = Σ_p w_p x_pj / d_j^{1−β'}
```

**F4 — EASE / EDLAE, Woodbury:**
```
Λ = λI + κ·diag(d)
K = I_m + X Λ⁻¹ Xᵀ
diag(P) = Λ⁻¹ − colsum( (L⁻¹ X Λ⁻¹)^∘2 )
qP = q⊙Λ⁻¹ − Λ⁻¹ ⊙ Xᵀ K⁻¹ X (q⊙Λ⁻¹)
s_j = −(qP)_j / P_jj
```

**F5 — Eğilim ağırlığı (Onishi 2025), her modele:**
```
s_j ← s_j · (1 + exp(−α₀ − β₀ log(d_j + 1)))
α₀ = −β₀ · (log(min d + 1) + log(max d + 1)) / 2
```

**F6 — GF-CF:**
```
R̃ = D_U^(−½) X D_I^(−½)
s = q R̃ᵀR̃ + α_g · q D_I^(−½) Ū_K Ū_Kᵀ D_I^(½)
```

**F7 — Tohum birleştirme ailesi:** `s_j = (Σ_i (q_i S_ij)^{1/τ})^τ`.
τ = 1 toplam, τ = 2 Pixie; ayrıca Aiolli γ ve MAX.

**F8 — Kalibrasyon (yalnız karma liste ve alt tarzlar için):** Steck açgözlü, KL, α = 0,01.

### Düzeltme listesi (önceki rapor 1'e)

1. Aiolli formülünde tohum ve aday üsleri yer değiştirmiş. α = 0,15 ADAYIN üssüdür.
   Tohumun üssü 0,85'tir.
2. "Kalibrasyonla 0,181" tek öğe tabanlı sıralayıcının değeri. Kazanan birleşim 0,17896.
3. RP3β'da satır-L1 normalizasyonu tohum derecesi çarpanını sadeleştirir. "a = α"
   düğmesi yalnız normalizasyon kapalıyken var.
4. RP3β/P3α'da α ızgarası 2'ye kadar gitmeli. Cooper'ın en iyisi α = 1,9.
5. GF-CF'nin doğrusal kısmı ρ = 1, a = b = ½ noktası (n_p^(−½) değil, n_p^(−1)).
   Amazon-book'taki %70 kazanç yalnız doğrusal süzgeçten geliyor. K = 256 bizde anlamsız,
   K ≤ 128 olmalı.
6. Dacrema shrink'i paydaya eklenir ve Koren'in çarpımsal büzülmesinden farklıdır. Bizde
   h ölçeği küçültülmeli.
7. SLIM'de alpha uniform, l1_ratio log-uniform.
8. EDLAE'nin tam rank kapalı formu `Λ = (p/q) diag(XᵀX)` ile verilir. `+λI` yalnız
   rank-1000 deneylerinde eklenmiş.
9. EASE Woodbury geçerli ve sayısal olarak doğrulandı. Ek bulgu: m < n iken λ → 0 limiti
   sonlu.
10. 2512.20896 doğrudan uygulanabilir bir popülerlik düğmesi veriyor:
    `B̂ · diag(1/p)`, log-sigmoid eğilim.
11. Pixie formülü doğrulandı. s_q'daki C = en büyük derece yazımı tutarsız görünüyor.

### Kaynak URL'leri

- EASE: https://arxiv.org/abs/1905.03375
- EDLAE: https://proceedings.neurips.cc/paper_files/paper/2020/hash/e33d974aae13e4d877477d51d8bafdc4-Abstract.html
- Cooper 2014: https://archives.iw3c2.org/www2014/proceedings/companion/p811.pdf
- Dacrema 2019: https://arxiv.org/abs/1907.06902
- Dacrema TOIS 2021: https://arxiv.org/abs/1911.07698
- Dacrema kodu: https://github.com/MaurizioFD/RecSys2019_DeepLearning_Evaluation
- Aiolli 2013: https://www.math.unipd.it/~aiolli/PAPERS/MSD_final.pdf
- Aiolli 2012: https://www.math.unipd.it/~aiolli/PAPERS/MSDaiolli.pdf
- GF-CF: https://arxiv.org/abs/2108.07567 · kod: https://github.com/yshenaw/GF_CF
- Pixie: https://arxiv.org/abs/1711.07601
- Kwieciński ve ark. 2023: https://arxiv.org/abs/2301.07946
- Paudel & Bernstein 2021: https://arxiv.org/abs/2102.09635
- Kaya & Bridge 2019: https://cora.ucc.ie/bitstreams/96b33b40-2fc6-4304-af35-15a2ce629d00/download
- da Silva & Jannach 2025: https://arxiv.org/abs/2507.02643
- Onishi ve ark. 2025: https://arxiv.org/abs/2512.20896
- Guo ve ark. 2026: https://arxiv.org/abs/2603.07402
- Li ve ark. 2026: https://arxiv.org/abs/2609.11876
- Moon ve ark. 2023: https://arxiv.org/abs/2305.12922
- Steck & Garcia Garcia 2021: https://arxiv.org/abs/2110.11402
- Rendle 2019: https://arxiv.org/abs/1912.02263
- Okunamayan künyeler:
  - TiiS: doi:10.1145/2955101
  - RecSys'15: doi:10.1145/2792838.2800180
  - RecSys'18: doi:10.1145/3240323.3240372
  - KDD'20: doi:10.1145/3394486.3403226
