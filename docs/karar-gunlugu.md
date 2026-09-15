# Karar Günlüğü

Her mimari karar buraya. Format: tarih — karar — gerekçe — alternatif neden elendi.

## 2026-08-11 — Uygulama, sohbet botu değil
Sistem kalıcı bir uygulama olarak kurulur; sohbet arayüzü birincil arayüz değildir.
**Gerekçe:** 30 sn önizleme çalma, kalıcı profil ve geri bildirim döngüsü, kümelemenin
tekrarlanabilirliği, forum taramasının önbelleklenmesi.
**Elenen:** Saf Cowork/sohbet botu — her oturum sıfırdan başlar, aynı araştırma maliyeti
tekrar tekrar ödenir, sistem kullanıcıyı öğrenmez.

## 2026-08-11 — Bulanık kümeleme (FCM)
**Gerekçe:** Bir albüm birden fazla eksene ait olabilir; keskin atama bilgi kaybettirir.
Üyelik dereceleri Faz 2'nin eksen ağırlıkları olarak doğrudan kullanılır.
**Not:** m = 1.3–1.6, öncesinde boyut indirgeme zorunlu.

## 2026-08-11 — Kümeleme R'da, alım/zenginleştirme Python'da  ~~GEÇERSİZ~~
> Bu karar aynı gün geri alındı — bkz. "Kümeleme ve arayüz de Python (K8)".
> Kayıt, neyin neden değiştiğini izleyebilmek için duruyor.

**Gerekçe:** Kullanıcının ana sahası R ve bulanık kümeleme ekosistemi orada olgun;
metadata ve API istemcisi ekosistemi Python'da güçlü.
**Köprü:** Dosya tabanlı (Parquet). `reticulate` kullanılmaz — sınır net olsun.

## 2026-08-11 — RateYourMusic kullanılmayacak
**Gerekçe:** Resmi API yok, scraping ToS'a aykırı.
**Yerine:** MusicBrainz + Discogs + Reddit yeterli kapsama veriyor.

## 2026-08-12 — Davulcu karakteri: iki ölçüt elendi, üçüncüsü tuttu (K12)
Kullanıcının "benzer davulcuları duyabileyim" isteği üç denemede çözüldü.

**Deneme 1 — tempogram entropisi.** Sekiz sanatçıda 0.878–0.891. Eminem 0.892,
Meshuggah 0.890. ELENDİ: hiçbir şey ayırt etmiyor.

**Deneme 2 — HPSS + senkop fazı.** Harmonik/perküsif ayrışımdan sonra onset'lerin
vuruş fazına bakıldı. Françoise Hardy 0.682, Meshuggah 0.600 çıktı. ELENDİ: ölçüt
ters çalışıyor. Sebep — HPSS yoğun mikste davulu ayıramıyor; "perküsif" bileşen
gitar atağını, vokal sessizini de içeriyor. Ayrıca faz eşiği (0.2–0.8) her pop
şarkısında bulunan 8'lik ofbiti de senkop sayıyor.

**Deneme 3 — Demucs ile davul stem'i ayırıp yalnız onu ölçmek. TUTTU.**
Aynı sekiz sanatçıda sonuç müzikal olarak doğru (tablo K12'de). Ayırt eden şey
bant dağılımı: Meshuggah zil %62 / trampet %17 (Haake'nin ride ağırlıklı, trampet
cimri stili), TOOL tekme %41 (Carey'nin tom-tekme sesi), Michael Jackson trampet
%49. Izgara entropisi programlanmış beat'i yakalıyor: Eminem 0.755, insanlar
0.94–0.99.

**Neden işe yaradı:** Önceki iki deneme "davul sesini yalıtmaya çalışan" sinyal
işleme hileleriydi. Demucs eğitilmiş bir kaynak ayrıştırma modeli ve davulu
gerçekten ayırıyor. Ölçüt aynı kaldı, GİRDİ düzeldi.

**Maliyet ve tasarım sonucu:** demucs+torch ≈ 2 GB, MPS'te klip başına ~12 sn.
Bu yüzden analiz albüm düzeyinde değil MÜZİSYEN düzeyinde yapılıyor — 40 davulcu
× 2 klip ≈ 16 dakika, 302 albüm × 10 parça saatler sürerdi. Zaten doğru birim de
bu: soru "bu davulcu nasıl çalıyor".

**Kalite koruması:** Vuruş başına 0.5 notadan az düşen klip atılıyor. Ian Paice
0.18 çıkmıştı — klip sessiz bir pasaja denk gelmiş, 2 klibin medyanını zehirliyordu.

**Kullanıcıya değdiği yer:** Müzisyenler sekmesinde her benzer davulcunun 30 sn
örneği çalınabiliyor. "Danny Carey → Matt Cameron (0.71)" yazmakla kalmıyor,
ikisini arka arkaya dinletiyor.

## 2026-08-12 — Kullanıcı yorumu kaynağı: CritiqueBrainz açık ama ince
Reddit reddedildikten sonra "kullanıcı yorumları" için CritiqueBrainz test edildi
(MetaBrainz'in CC lisanslı inceleme sitesi, anahtarsız API).
**Ölçüldü:** 6 albümde 2 yorum. Kapsama ana sinyal olamayacak kadar ince;
yardımcı sinyal (puan) olarak durabilir.
**Araştırma notu:** AcousticBrainz'in resmi halefi diye bir şey yok; MetaBrainz'in
kendi önerisi "Essentia + kendi ses kaynağın". Bizim önizleme boru hattımız tam
olarak bu — bağımsız olarak aynı tasarıma varmışız.

## 2026-08-12 — Faz 2 aday üretimi: iki strateji, şablonlu gerekçe
`python/discover/adaylar.py`. 302 albümlük kütüphanede 9 stabil eksen için 108 aday
üretildi (52 kredi sıçraması + 56 sahne komşuluğu), 93'ünde 30 sn önizleme var.

**Kredi sıçraması Discogs'tan gider, MusicBrainz'den DEĞİL.** MB'nin `artist=`
araması yalnızca ASIL SANATÇI olduğu kayıtları döndürüyor; "Neil Peart'ın çaldığı
albümler" sorgusu MB API'sinde yok. Discogs `/artists/{id}/releases` `role=Appearance`
ile tam olarak bunu veriyor.

**Yol boyunca çıkan ve düzeltilen kusurlar (hepsi gerçek veriyle görüldü):**
1. Tek müzisyen listeyi dolduruyordu — Casiopea'nın klavyecisi 6 adayın 6'sını almıştı.
   Kişi başına azami 2 aday + kişiler arası dönüşümlü sıralama.
2. Oyun müziği, tren hattı açılış BGM'i, "Fortitude + Magma" paket listeleri aday
   oluyordu. Discogs topluluk koleksiyonu eşiği (≥25) bunları kesiyor; gerçek
   albümler yüzlerce/binlerce koleksiyonda (Gojira Fortitude 4892, oyun müziği 2).
3. Derleme/canlı albümler sızıyordu: `format` alanı master kayıtlarda BOŞ geldiği
   için biçim süzgeci işlemiyordu. Başlık üzerinden ikinci süzgeç eklendi.
4. Mühendis/mix kredisiyle öneri geliyordu ("bu albümü şu mix mühendisi mikslemiş"
   zayıf bir gerekçe). Kredi sıçraması artık yalnızca İCRACI rollerinden gider.
5. **En ciddisi:** Kullanıcının zaten sahip olduğu sanatçı "keşif" diye önerildi.
   ListenBrainz "Masayoshi Takanaka"yı 高中正義 olarak döndürüyor, kütüphanede
   romanize adı var, isim eşleşmesi tutmuyordu — bir eksende ilk 5 adayın 4'ü.
   Kök neden `sanatci_mbid_bul`'daydı: MusicBrainz'de asıl ad Japonca, romanize
   hâli TAKMA AD listesinde. Artık ad + sort-name + bütün takma adlar deneniyor
   ve sahiplik MBID üzerinden süzülüyor. Ayrıca Latin yazımlı ad varsa arayüzde
   o gösteriliyor: "Tatsuro Yamashita (山下達郎)".

**Sonuç örneği (jazz-fusion ekseni):** Issei Noro — Sweet Sphere (Casiopea'nın
gitaristinin solo albümü), Tetsuo Sakurai — Dewdrops (basçısı), Tatsuro Yamashita,
Junko Ohashi, Spyro Gyra.

## 2026-08-12 — Önizlemede kaynak devri: bir kaynak düşerse diğerine geçilir
`onizleme_bul` artık `IstekBasarisiz`i de yakalıyor.
**Gerekçe:** Apple iTunes Search bu IP'yi 403 ile kısıtladığında bütün tur çöküyordu
— oysa Deezer sorunsuz cevap veriyordu. İki kaynak koymanın sebebi tam olarak buydu
ama devir kodu yalnızca `AgYok`u yakalıyordu. Ayrıca 403 yeniden denenebilir sayıldı
(Apple hız sınırını böyle bildiriyor) ve istemciler tur boyunca bir kez kuruluyor —
her aday için yenisini yaratmak rate-limit sayacını sıfırlıyordu.
**Ölçüldü:** düzeltmeden önce 52 adayın 3'ünde önizleme vardı, sonra 40'ında.

## 2026-08-12 — CJK başlıklar normalizasyonda boşa düşüyordu
`normalize()` ASCII dışı her şeyi atınca "ウチュウノアバレンボー" → "" oluyordu.
**Neden tehlikeli:** Boş anahtar, bütün Japonca başlıkları birbirine eşit yapar ve
yanlış eşleşme üretir. Aday tarafında Japon fusion albümleri bol.
**Çözüm:** ASCII sonucu boşsa özgün metnin temizlenmiş hâline geri düşülür.
Kütüphanede etkilenen albüm YOK (ölçüldü), yani album_id'ler oynamadı.

## 2026-08-11 — Kalabalık sinyalinin birimi EKSEN, kütüphane geneli değil
`python/discover/listenbrainz.py`. Komşu sanatçılar kütüphane genelinde toplanınca
sonuç işe yaramıyor; küme (eksen) bazında toplanınca işe yarıyor.
**Ölçüldü (aynı veri, iki farklı toplama birimi):**

| birim | ilk öneriler |
|---|---|
| kütüphane geneli | AC/DC, David Bowie, The Doors, Aerosmith |
| jazz-fusion ekseni | Spyro Gyra, Yellow Magic Orchestra, Victor Wooten, Chuck Loeb |
| hip-hop ekseni | Tyler The Creator, Frank Ocean, Travis Scott |

**Neden:** Ham komşuluk skorları popülerlikle ölçekleniyor. Eksen içinde birden çok
sanatçının komşu listesi kesiştirilince popülerlik sönüyor, ortak nokta kalıyor.
İki düzeltme birlikte gerekiyordu: (1) her kaynak sanatçının listesini kendi içinde
normalize et — Metallica'nın skorları Casiopea'nınkinin kat kat üstünde; (2) log(N/df)
ile herkesin komşusu olan ismi sönümle.
**Sınır:** Tek sanatçılı eksende çalışmıyor — Rush kümesi yine Queen/Beatles veriyor,
çünkü kesiştirilecek ikinci bir liste yok.
**Sonuç:** CLAUDE.md'nin Faz 2 tasarımı ("eksen seçimi + eksene özgü aday stratejileri")
ampirik olarak doğrulandı; aday üretimi eksen başına yapılacak.

## 2026-08-11 — AcousticBrainz ile librosa aynı şeyi ölçmüyor (kalibrasyon)
19 albümde iki kaynak da ölçüldü ve korelasyonlar hesaplandı:

| öznitelik | r | yorum |
|---|---|---|
| spektral merkez | +0.80 | sıralama uyuşuyor, mutlak değer uyuşmuyor (2330 vs 1378) |
| tempo | +0.47 | orta; yarı/iki kat hatası YOK (0/19) |
| tempo IQR | +0.50 | orta |
| dinamik | +0.42 | zayıf — zaten farklı tanım (dB yüzdelik farkı vs Essentia dynamic_complexity) |

**Sonuç:** Ham değerler kaynaklar arası KIYASLANAMAZ. `audio_features` birincil
anahtarı `(album_id, kaynak)` yapıldı; karşılaştırma kaynak içinde z ile
standartlaştırılarak yapılır. En güvenilir ortak eksen spektral merkez.

## 2026-08-11 — `ritmik_karmasiklik` elendi, yerine iki ölçüt
Tempogramın normalize Shannon entropisi ölçüt olarak ATILDI.
**Gerekçe:** Sekiz sanatçıda ölçüldü ve hepsi 0.878–0.891 arasında çıktı — Eminem
0.892, Casiopea 0.879, Gojira 0.891, Meshuggah 0.890. Hiçbir şey ayırt etmiyordu.
**Yerine:** `nabiz_netligi` (tempogram tepe/ortalama) ve `vurus_degiskenligi`
(vuruş aralıklarının değişim katsayısı). Bunlar ayırıyor: Gojira 4.2 / Casiopea 7.7
nabız netliği; Animals As Leaders 0.068 / Michael Jackson 0.019 vuruş değişkenliği.
**Ama adları dürüst olmalı:** bu ikisi nabız DÜZENLİLİĞİNİ ölçer, teknik zorluğu
değil. Meshuggah polritmik olarak en karmaşık gruplardan biri ama metronomik olarak
katı olduğu için "düzenli" çıkıyor (0.033). "İyi davulcu" sorusunun cevabı ses
dalgasında değil; forum katmanında (K10).
**Yan bulgu:** `dinamik_aralik` beklenmedik biçimde güçlü bir sinyal — Gojira ve
Meshuggah 4.2 dB (modern metal mastering'i), Eminem 16.7, TOOL 13.2.

## 2026-08-11 — Müzisyen benzerliğinde ses bloğu standartlaştırılır
`_kosinus(..., standartlastir=True)`.
**Gerekçe:** Ham ses profiliyle kosinüs benzerliği işe yaramıyordu: 6 boyut ve
hepsi pozitif olduğu için bütün vektörler aynı yöne bakıyor. Ölçüldü — ses
ağırlığını 0'dan 0.85'e çıkarmak sıralamayı HİÇ değiştirmedi, yalnızca skorları
0.84'ten 0.98'e şişirdi. Sütun bazında z ile merkezlenince benzerlik ayırt etmeye
başladı.
**Varsayılan ses ağırlığı 0.5, ölçümle seçildi:** 0.5'te Danny Carey → Garstka,
Lopez, Portnoy (isabetli); 0.85'te Mario Duplantier → Ian Paice, Steven Adler
(bozuluyor). Ses öznitelikleri prodüksiyon karakterini ölçtüğü için fazla ağırlık
sonucu bozuyor.

## 2026-08-11 — 30 sn önizleme iki iş görür: dinletme + aday analizi
Faz 2/3'te önerilen albüm kullanıcının kütüphanesinde olmadığı için ses öznitelikleri
hesaplanamaz. iTunes Search / Deezer'ın 30 sn önizlemesi hem çalınacak hem
`parca_analiz(--sure 30)` ile analiz edilecek.
**Kaynak durumu (canlı test edildi):** iTunes ve Deezer anahtarsız ve ücretsiz;
6 örnek albümün 5'inde ikisi de önizleme verdi (Türkçe albüm dahil), niş Japon
fusion grubunda ikisi de vermedi. **Qobuz:** üçüncü taraflara açık ücretsiz API'si
yok, ortaklık gerektiriyor — belgelenmemiş uç nokta kullanmak RateYourMusic için
zaten reddedilen kategoriye girer. **Spotify:** 2024 sonunda yeni uygulamalar için
`preview_url` kapatıldı.
**Yapılacak:** `audio_features`'a `kaynak` sütunu (yerel / önizleme). Önizlemeler
AAC'ye sıkıştırılmış ve ses seviyesi normalize edilmiş olduğu için `dinamik_aralik`
kaynaklar arası kıyaslanamaz; karşılaştırma kaynak içinde standartlaştırılmalı.

## 2026-08-11 — Müzisyen düzeyi ayrı bir nesne (python/muzisyen.py)
Albüm kümelemesinin yanına müzisyen profili ve müzisyen–müzisyen benzerliği eklendi.
**Gerekçe:** Kullanıcının sorusu — "Neil Peart, Mario Duplantier ve Weather Report'un
davulcusu benzer kalibrede adamlar; senin yöntemin bu üçünü kümeleyebilir mi?" —
albüm kümelemesiyle cevaplanamaz. Kredi grafiği BİRLİKTE ÇALMIŞ kişileri bağlar,
BENZER kişileri değil. Peart (Rush, küme 1) ile Duplantier (Gojira, küme 9) hiç aynı
albümde bulunmadı; aralarında hiçbir yol yok ve hiçbir blok ağırlığı onları bir araya
getiremez. Müzisyen kendi başına bir varlık olarak ele alınmadan bu soru sorulamıyor.
**Profil:** rol dağılımı, çaldığı albümlerin tür merkezi, ses profili, kullanıcının
eksenlerine dağılımı, dinleme yükü. Benzerlik bu profillerin kosinüsü.
**Ölçüldü:** Duplantier'e en yakın davulcular — Martin Lopez (Opeth), Sean Reinert
(Cynic/Death), Mike Portnoy (Dream Theater), Matt Garstka (Animals As Leaders),
Danny Carey (TOOL). Peart'a en yakınlar — Ian Paice, Alex Van Halen, Chad Smith.
**Sınır, açıkça raporlanıyor:** ses öznitelikleri boşken benzerlik tür merkezine
düşüyor, yani "aynı TÜRDE çalan" demek oluyor, "aynı KALİBREDE çalan" değil.
Peart'ın listesinin klasik rock davulcularıyla dolması bundan. Kalibre sorusunun
asıl cevabı `ritmik_karmasiklik` — şu an %0 kapsamda.
**Rol filtresi tek yönlü:** "ana rolü davul olan" değil, "davul çalan". Peart'ın en
sık kredisi percussion (12), davul (10) ondan az — ana role bakan filtre onu
davulcu saymıyordu.

## 2026-08-11 — Küme kadrosu: sık geçen değil, ayırt eden
Panel artık "lift" gösteriyor: müzisyenin bu kümedeki payı eksi kütüphane genelindeki
payı.
**Gerekçe:** Sık geçeni göstermek yanıltıcıydı; kütüphanede çok albümü olan sanatçı
hiç ait olmadığı kümede bile listenin başına çıkıyordu.

## 2026-08-11 — Boyut indirgemenin ölçütü açıklanan varyans DEĞİL, ayrışabilirlik
`ayar.bilesen = 8` sabit; "varyansın %80'ini açıkla" kuralı kaldırıldı.
**Gerekçe:** K3 boyut indirgemeyi "üyelikler 1/c'ye yakınsıyor" diye istiyor, yani
amaç varyans korumak değil o çöküşü engellemek. Gerçek kütüphanede ölçüldü
(302 albüm, 1287 öznitelik, %1,4 doluluk):

| boyut | açıklanan varyans | PE(norm) | sonuç |
|---|---|---|---|
| 100 | %86 | 1.00 | yapı yok |
| 30 | %50 | 0.93 | yapı yok |
| 10 | %27 | 0.48 | zayıf yapı |
| 8 | %23 | 0.28 | kullanılabilir |

Varyans hedefi tam ters çalışıyor: %80 varyans 80 bileşen istiyor ve o boyutta
mesafeler tamamen yoğunlaşıyor (en yakın/en uzak komşu farkı kayboluyor).
**Bedel:** Varyansın dörtte üçü atılıyor. Kabul edildi — atılan varyans, her biri
2–3 albümde geçen yüzlerce seyrek müzisyen sütununun kendi başına oluşturduğu
yönlerden ibaret ve bunlar hiçbir albüm çiftini yaklaştırmıyor.

## 2026-08-11 — c seçimi stabilite süzgecinden geçer
`en_iyi_c` artık önce "tüm kümeleri stabil olan" c adaylarını süzüyor, Xie-Beni
kararı onların arasında veriyor. c taramasında her c için 20 bootstrap koşuluyor.
**Gerekçe:** K3 üç ölçüt sayıyor ama ilk uygulamada stabilite yalnızca sonradan
yapılan bir kontroldü. Gerçek veride XB c arttıkça düşmeye devam edip aralığın
sonuna kaçıyordu: c=13'te XB en düşüktü ama kümeler 11 albüme inmiş ve 13'ün
yalnızca 12'si stabildi. Süzgeçle c=6 seçiliyor — altı kümenin altısı da stabil.

## 2026-08-11 — Kredi bloğu ikiye ayrıldı: kim çaldı / kim üretti
`kredi` (ENSTRUMAN_ROLLERI) ve `uretim` (URETIM_ROLLERI) ayrı bloklar, ağırlıkları
1.0 ve 0.5.
**Gerekçe:** Ayrılmadan önce bu kütüphanenin en güçlü kredi bağlantısı **Bob Ludwig**
idi — 15 albümde geçen bir mastering mühendisi. O 15 albümün müzikal ortak yanı yok;
aynı stüdyodan geçmişler. Projenin tezi "kim çaldı", mastering zinciri değil.

## 2026-08-11 — Temsilci ve kadro seçiminde 1/c tabanı
Hem `temsilci_sec` hem arayüzdeki kadro paneli, üyelik 1/c'nin altındaki albümleri
saymıyor.
**Gerekçe:** "Üst %20" yüzdeliği TÜM kütüphane üzerinden hesaplanıyordu; 38 albümlük
bir kümede 302 albümün %80'lik dilimi u=0.13'e denk geliyor ve kümeye ait olmayan
albümler temsilci seçiliyordu. Kadro panelinde aynı hata daha görünürdü: 13 Rush
albümünün 0.1'lik üyelikleri toplanınca hip-hop kümesinin kadrosu Rush görünüyordu.
1/c "hiçbir şey bilmiyoruz" üyeliğidir; altındaki bir albüm o kümeyi temsil edemez.

## 2026-08-11 — MusicBrainz nitelikleri rolün kendisi değil
`MB_DEGISTIRICILER` — "additional", "co", "task", "guest", "solo" gibi nitelikler
ayıklanıp ilişkinin `type` alanına düşülüyor.
**Gerekçe:** MB `type=engineer, attributes=['task']` döndürüyor. Kod nitelikleri
role tercih ettiği için 111 mühendislik/prodüksiyon kredisi "task" diye bilinmeyene
düşüyor ve gerçek rol tamamen kayboluyordu.

## 2026-08-11 — Kümeleme ve arayüz de Python (K8) — ÖNCEKİ KARARI GEÇERSİZ KILAR
Aşağıdaki "Kümeleme R'da, alım/zenginleştirme Python'da" kararı geri alındı. Kümeleme
`python/kumeleme/` altında numpy ile, arayüz Streamlit ile yazıldı.
**Gerekçe:** Boru hattının geri kalanı zaten Python; kümeleme ortada tek başına duran
bir R adasıydı. Faz 2 (aday üretimi, kredi grafiği gezinmesi) ve Faz 3 (Reddit,
özetleme) de Python olacak — kümeleme çıktısı orada yeniden okunacak. İki çalışma
zamanı = iki bağımlılık ağacı + dosya köprüsü.
**Somut sürtünme:** R tarafının Parquet okuyucusu `arrow` bu makinede ikili paket
olarak kurulmadı; köprü daha ilk adımda CSV'ye düşecekti. `fclust` da yoktu.
**Performans gerekçe DEĞİL:** 2000 albüm × ~30 boyut, c taraması + 50 bootstrap iki
dilde de saniyeler. Bunu açıkça not ediyorum çünkü değişikliğin tetikleyicisi
"Python daha hızlı olur" düşüncesiydi ve bu, bu ölçekte doğru değil.
**Bedeli:** `fclust`/`fpc`'nin test edilmiş geçerlilik indeksleri ve Hennig stabilite
yordamı yerine kendi kodumuz — FCM ~30 satır, XB/PE birer formül, bootstrap Jaccard
~50 satır. Karşılığında `tests/test_kumeleme.py` bunların bilinen yapıyı geri
bulduğunu doğruluyor.
**Elenen ara yol:** Kümeleme Python + arayüz Shiny — dil birliğini sağlıyor ama iki
çalışma zamanı sorununu çözmüyordu.

## 2026-08-11 — Sentetik örnek kütüphane ile doğrulama
`scripts/ornek_veri.py` yapısı önceden bilinen 60 albümlük bir kütüphane üretir:
4 sahne, sahneler arası ortak kadro, ve bilinçli olarak iki sahnenin ortasında duran
4 melez albüm.
**Gerekçe:** Gerçek kütüphaneyle test edilirken doğru cevap bilinmiyor; FCM 5 küme
bulduğunda bunun iyi mi kötü mü olduğu söylenemez. Kurulu yapı geri bulunabiliyorsa
kod doğrudur — kümelerin anlamlı olup olmadığı ayrı bir soru ve onu ancak kullanıcı
gerçek kütüphanesinde cevaplayabilir.
**Ölçüldü:** c=4 seçildi, 4 küme de stabil (Jaccard 0.99–1.00), melez albümler
bulanık üyelikte doğru işaretlendi (İki Nehir: %52 + %45).

## 2026-08-11 — Temsilciler kümeleme anında donar
`temsilciler` tablosu eklendi (bkz. veri sözleşmesi).
**Gerekçe:** Arayüz temsilcileri kendi hesaplasaydı, farklı blok ağırlığı ya da
tohumla başka albümler gösterebilirdi; kullanıcı isimlendirdiği kümeyi tanıyamazdı.
Arayüz, çalışmanın verdiği kararı göstermeli.

## 2026-08-11 — Ses bloğu diğer bloklarla aynı mertebeye ölçekleniyor
`matris_kur.py` ses bloğunu, satır normlarının ortalaması 1 olacak şekilde tek bir
katsayıyla böler.
**Gerekçe:** Diğer üç blok satır-L2 ile normalize edildiği için her satırın enerjisi
tam 1; ses bloğu ham robust-z olarak bırakılınca 5 sütunla toplam enerjinin %44'ünü
kapıyordu ve blok ağırlıkları söyledikleri şeyi yapmıyordu (ölçüldü). Satır bazında
normalize etmek yanlış olurdu: medyana yakın, yani bilgi taşımayan bir albümün
değerlerini yapay olarak büyütürdü.
**Sonuç:** Düzeltmeden sonra enerji payları kredi %52, etiket %26, sahne %13, ses %9 —
kredi bloğunun domine etmesi (mimari.md) artık gerçekten sağlanıyor.

## 2026-08-11 — Matriste blok içi normalizasyon: satır L2, seste robust z
Kredi/sahne/etiket blokları satır bazında L2'ye, ses bloğu sütun bazında medyan/IQR'a
normalize edilir. Blok **ağırlıkları** matriste uygulanmaz, kümeleme ayarına bırakılır
(`python/kumeleme/ayar.py`; karar alındığında `R/config.R` planlanıyordu).
**Gerekçe:** Ham sayım kullanılırsa mesafeyi müzikal yakınlık değil, albümün Discogs'ta
ne kadar iyi belgelendiği belirler — 46 kredili albüm 5 kredili albümden "daha büyük"
görünür. Seste ortalama/sd yerine medyan/IQR: tempo ve spektral merkezde aykırı değer
olağan. Ağırlığın kümeleme adımında kalması, parametrelerle oynarken matrisin
yeniden kurulmasını gereksiz kılar.
**Eksik ses verisi:** normalize sonrası 0 (yani medyan) ile doldurulur — albümü ne
kendine ne başkasına yaklaştırır. Kaç albümde eksik olduğu raporlanır.

## 2026-08-11 — Seyreklik eşiği: bir öznitelik en az 2 albümde geçmeli
`--min-album` varsayılanı 2.
**Gerekçe:** Tek albümde geçen müzisyen veya etiket hiçbir albüm çiftini birbirine
yaklaştırmaz, sadece boyut ekler. K3 zaten yüksek boyutta FCM üyeliklerinin 1/c'ye
yakınsadığını söylüyor; matrisi baştan şişirmenin anlamı yok.
**Not:** Eşiğe takılan sütun sayısı ayrıca raporlanır — "veri yok" ile "eşik eledi"
karıştırılmasın diye.

## 2026-08-11 — Kişiler kaynaklar arası isimle birleştirilir
Kredi bloğunda sütunlar `person_id` değil, küçük harfe indirgenmiş isim üzerinden
gruplanır.
**Gerekçe:** Aynı kişi MusicBrainz'de MBID, Discogs'ta `discogs:123` ile gelir; iki
kaynağı birleştiren tek ortak alan isimdir. Birleştirilmezse Terry Brown iki ayrı
sütun olur ve iki albümü paylaştığı halde matriste hiç örtüşmez.
**Bedel:** Adaş müzisyenler tek sütunda toplanır. Kütüphane ölçeğinde (bir kişinin
kütüphanesi) bu riskin maliyeti, kaynak ayrımının maliyetinden düşük.

## 2026-08-11 — Discogs aday kapısı: başlık tutmuyorsa kredi alınmaz
`aday_uygun_mu` — arama sonucunun normalize başlığı (ve varsa sanatçısı) albümle
tutmuyorsa aday reddedilir. Ayrıca master kaydı olan adaya öncelik verilir.
**Gerekçe:** İlk sürümde arama ne döndürdüyse kabul ediliyordu; bu, yanlış albümün
kredilerini kütüphaneye yazma riskiydi — MBID tarafında bu kapı vardı, Discogs'ta
yoktu. Master önceliği ölçüldü: kaset baskısı 0 kredi verirken master'ın ana baskısı
24 kredi verdi (Perdeler).

## 2026-08-11 — API istemcisi tek katman: musicbrainzngs yerine doğrudan HTTP
`musicbrainzngs` bağımlılığı kaldırıldı; MusicBrainz de Discogs de `python/onbellek.py`
üzerinden `requests` ile çağrılıyor.
**Gerekçe:** K5 "her şey önbelleklenir" diyor. Kütüphane kendi HTTP'sini yapınca önbellek
ve rate limit iki ayrı yerde iki farklı biçimde uygulanmak zorunda kalıyordu. Tek katman:
tek anahtarlama, tek yeniden deneme politikası, tek `--cevrimdisi` bayrağı.
**Bedel:** MB'nin şema ayrıntılarını elle ayrıştırmak. Kabul edilebilir — kullanılan uç
nokta sayısı üç.

## 2026-08-11 — Boş sonuç da önbelleklenir, çevrimdışı mod var
404 ve boş arama sonuçları da diske yazılır; `--cevrimdisi` yalnızca önbellekten çalışır.
**Gerekçe:** "Bu albümün Discogs'ta karşılığı yok" bilgisi de bir saniyeye mal olmuştur.
Önbelleklenmezse kredisiz albümler her turda yeniden sorulur ve tur süresi hiç düşmez.
Ölçüldü: 3 albümlük kredi turu 32 sn → 0,2 sn.

## 2026-08-11 — MBID eşleşmesinde şüphe insana sorulur, yıl farkı tek başına şüphe değil
Otomatik kabul yalnızca normalize başlık+sanatçı tam tutuyorsa. Tek tam eşleşme varsa
yıl tutmasa da kabul edilir; birden fazla tam eşleşme varsa ve yıl ayıramıyorsa CSV'ye
düşer.
**Gerekçe:** Yanlış MBID, yanlış kredileri kütüphaneye taşır — kredi grafiği projenin
çekirdeği olduğu için bu hata pahalıdır. Ama etiketteki yıl çoğu zaman yeniden basımın
yılıdır (ölçüldü: Perdeler etiket 2005, MB 2001); bunu şüphe saymak raporu şişirip
insanı okumaz hale getirir. Asıl risk yıl farkı değil, **rakip aday**.

## 2026-08-11 — Bilinmeyen roller sessizce yutulmaz, rapora düşer
`rol_eslemesi.py` sözlüğünde olmayan roller `data/raporlar/bilinmeyen_roller.csv`
dosyasına sayılarıyla yazılır. Müzikal içeriği olmayan roller (artwork, management)
ise bilinçli "atılan" listesindedir ve rapora girmez.
**Gerekçe:** Sözlük asla tam olmayacak. Sessiz düşürme, kredi grafiğinde fark edilmeyen
boşluk bırakır — ilk turda 6 rol yakalandı (minimoog, farfisa, assistant, effects,
cymbal, hi-hat) ve sözlüğe işlendi. Rapor, sözlüğün büyüme mekanizmasıdır.

## 2026-08-11 — Ses analizi parçanın ortasından 60 sn
**Gerekçe:** Tam parça analizi 2000 albümlük kütüphanede saatler sürer; intro/outro da
albümün karakterini temsil etmez. `--sure 0` ile tam analiz açılabilir.
**Not:** Ritmik karmaşıklık ölçütü tempogramın normalize Shannon entropisi (0–1) —
tek ve net nabızda düşük, değişken ritimde yüksek.

## 2026-08-11 — Artımlı taramanın belleği ayrı tabloda, dinleme içe aktarımı idempotent
K6 "hangi kayıtlar yeni?" sorusunu somutlaştırmak için iki şema eklemesi yapıldı
(bkz. veri sözleşmesi): `dosyalar` tablosu (yol, mtime, boyut, album_id) ve
`plays.kaynak` sütunu.
**Gerekçe:** Dosya mtime'ı bir yerde tutulmadan "değişmemişse atla" kuralı çalışmaz;
`albums.eklenme_tarihi` bu iş için yetmez, dosya değil albüm düzeyindedir. Dinleme
tarafında ise (kaynak, albüm, gün, parça) tekilliği aynı dışa aktarımın iki kez
aktarılmasını zararsız kılar — dinleme sayısı öznitelik matrisine giriyor, şişmesi
kümelemeyi bozar.
**Elenen:** Tarama durumunu JSON dosyasında tutmak — veritabanı zaten oradayken ikinci
bir kalıcılık biçimi gereksiz. Dinleme satırlarını olduğu gibi (ham scrobble) yazmak —
tekilleştirme dayanağı kalmaz, tekrar aktarımda çift sayılır.

## 2026-08-11 — Sistem LLM'e bağımlı değil, bütçe 0 TL
Proje sıfır maliyetle geliştirilecek ve çalıştırılacak. Faz 1 ve Faz 2'de hiçbir LLM
çağrısı yok; kullanılan tüm veri kaynakları ücretsiz.
**Karar:** LLM çekirdeğe gömülmez. Faz 3'teki özetleme `ozetle(metinler, mod)` arayüzünün
arkasına konur — varsayılan `cikarimsal` (0 TL), opsiyonel `yerel` (Ollama, M1 Mac) ve
`api` modları. Hiçbir kod yolu LLM'in varlığını varsaymaz.
**Elenen kullanımlar:** küme isimlendirme önerisi (kullanıcı zaten kendisi isimlendiriyor),
öneri gerekçesi (bkz. aşağıdaki karar).

## 2026-08-11 — "Neden bu albüm" şablonla üretilir
**Gerekçe:** Gerekçe, aday üretiminde kullanılan yolun kendisidir; kredi grafiğinden gelen
bir öneri kendi açıklamasını taşır. Şablonun boşlukları sorgudan gelen gerçek sayılarla
dolduğu için modelin üreteceğinden daha güvenilir — uydurma riski yok, doğrulanabilir.
**Sonuç:** Her aday üretim stratejisinin kendi şablonu olur.

## 2026-08-16 — İcra profili dört enstrümana genellendi

**Karar:** `davul_profili` yerine `stem_profili`; Demucs'un dört çıktısı da (drums,
bass, other, vocals) tek geçişte kaydediliyor. Rol → stem eşlemesi ve rol başına
ayrı ölçüt kümesi eklendi.

**Neden:** Kullanıcı gitar ve vokal de istedi. Teknik gerekçe daha güçlü: htdemucs
zaten dört kaynağı birlikte üretiyor, üçünü atmak bedava veriyi atmaktı. Ayrıştırma
maliyetin tamamına yakını; ölçüm kısmı stem başına ~1 sn.

**Ölçüt seçimi neden role bağlı:** Davulun perdesi yok, vokalin tekme payı yok.
Tek bir ortak vektör kullanılsaydı vokalleri karşılaştırırken `tekme_payi` NaN
olurdu ve kosinüs benzerliği rastgele davranırdı. `ROL_SUTUNLARI` her rol için
yalnızca anlamlı sütunları veriyor; eksik ölçüm kişiyi elemiyor, o boyut atlanıyor
(test: `test_eksik_olcum_kisiyi_elemez`).

**Doğrulama işaretleri:** perde medyanı stem'ler arası müzikal olarak tutarlı
çıkıyor — bas ~9 (G1), `other` ~21–29 (A2–F3), vokal ~24 (C3). Yani perde takibi
bir gürültü ölçmüyor, gerçekten kaydın register'ını ölçüyor.

**Alınmayan yol:** htdemucs_6s (piyano ve gitarı ayrı ayırır). Dört-kaynak modelin
altında kalite veriyor ve iki kat süre alıyor; gitar/klavye ayrımı için ödenecek
bedel bu aşamada fazla. Sınır dokümante edilip bırakıldı.

**pyin → yin:** albüm başına 43 sn CPU'dan ~7 sn'ye. Kaybedilen voicing olasılığı
yerine RMS eşiği kondu.

## 2026-08-16 — Stem önbelleği; ton dokusu ölçütünde üç eleme

**Stem önbelleği (`data/cache/stemler/`).** Ayrılmış stem'ler 22.05 kHz mono FLAC
olarak diske alınıyor, anahtar önizleme URL'sinin sha1'i. Albüm başına ~1 MB,
302 albüm ≈ 300 MB.

Gerekçe maliyet dağılımı: ayrıştırma klip başına ~12 sn (MPS), ölçüm ise saniyenin
altında. Öznitelik tasarımı bir kerede oturmuyor — bu projede şimdiye kadar beş
ölçüt ölçülüp elendi. Önbelleksiz her deneme 302 albümü yeniden ayrıştırmak
demekti (~1 saat); önbellekle dakikalar. Bu oturumda üç distorsiyon adayı arka
arkaya sınanabildi, tam da bu yüzden.

**Ton dokusu: üç eleme.** Gitar için "distorsiyonlu mu temiz mi" ölçmek gerekti.
- `duzluk` (spektral düzlük): 0.000–0.012. Demucs kaynak dışı binleri sıfırlıyor,
  geometrik ortalama çöküyor. Thrash (0.002) ile temiz gitar (0.001) ayrılmıyor.
- `tepe_orani` (tepe/RMS dB): yön yanlış. Annihilator 17.7 EN YÜKSEK, Animals As
  Leaders 12.9. 30 sn'lik karışık pasajda tepe/RMS aranjman yoğunluğunu ölçüyor.
- spektral kontrast: A-Ha (temiz synthpop) 24.2 > Annihilator 21.1. Ters.

Kalanlar `harmonik_pay` (HPSS harmonik enerji payı) ve `zcr`. Sekiz sanatçıda
sıralama müzikal olarak doğru: Annihilator 0.774/0.160 … A-Ha 0.973/0.039.

**Ama karar ERTELENDİ.** O sekiz sanatçıda harmonik_pay sıralaması `parlaklik`
sıralamasıyla neredeyse aynı; ölçüt "distorsiyon" mu yoksa sadece "parlaklık" mı
ölçüyor, n=8'de ayrılamaz. İkisi de saklanıyor, ölçüt kümesine alınma kararı tüm
kütüphanede (n≈300) parlaklik kontrol edilerek kısmi korelasyonla verilecek.
Göz kararıyla sekiz satıra bakıp karar vermek, elenen üç ölçütü baştan üretmiş
olan hatanın aynısı olurdu.

**sustain_orani yeniden tanımlandı.** Eski tanım ("RMS tepenin %20'sinin üstünde
kalan kare oranı") sürekli çalan stem'de tanım gereği 1.00 veriyordu — tavana
yapışmış ölçüt hiçbir şey ayırmaz. Yeni tanım nota başına çürüme oranı. Davulda
ayırıyor (April Wine 0.21 – Annihilator 0.94), `other`'da hâlâ dar (0.89–0.99);
o da aynı teste giriyor.

## 2026-08-16 — Ölçüt kümesi denetimle belirlendi; adaylar da profilleniyor

**Ölçüt kümeleri artık elle seçilmiyor.** `olcut_denetimi.py` üretiyor: kısmi
korelasyon + geriye doğru adımsal eleme, n≈270. Kullanıcı seçimi ("denetimden
geçen tam küme"). Rol başına ~10 öznitelik.

Metodolojik iki not:
- **Eleme sıralı olmalı.** Eşzamanlı testte `zil_payi` (Meshuggah %62 ride ile
  müzikal olarak doğrulanmış ölçüt) 0.234 ile elenecek görünüyordu. Artıklığını
  `parlaklik` ile paylaşıyordu — zil parlaktır — ve parlaklık zaten eleniyordu.
  Sıralı elemede parlaklık gidince zil_payi eşiğin üstüne döndü.
- **Bileşimsel sütunlar regresyondan çıkarılır.** tekme+trampet+zil = 1 olduğu
  için artık payları tanım gereği sıfır çıkıyordu; bu bulgu değil aritmetik.

`harmonik_pay` dört stem'de de ayakta kaldı (0.45–0.73). Önceki turda "n=8'de
parlaklıktan ayrılamıyor" diye karar ertelenmişti; n≈270'te ayrıldı ve gitarda
tam tersi çıktı — `parlaklik` elendi, distorsiyon ölçütü kaldı. Kararı ertelemek
doğru olmuş.

**stem_profili artık albums'a bağlı değil.** 108 aday albüm de profilleniyor
(`tur='aday'`). Öneri kartında "Nasıl çalıyorlar" satırı: adayın stem'ine en
yakın KÜTÜPHANE müzisyenleri, rol rol. Kredi grafiğinin söyleyemediği şey buydu.
Göç sırasında bir kez yarıda kalma yaşandı (yeni şemada olmayan elenmiş sütun
yüzünden INSERT patladı, 289 albümlük ölçüm görünmez oldu) — göç artık kendini
toparlıyor, `stem_profili_eski` duruyorsa kopyayı tamamlıyor.

**Yanlış alarm, düzeltildi.** Kredilerde 1289 kişi hem `discogs:NNN` hem
MusicBrainz UUID'siyle görünüyor. Kimlik ikilemesi gibi durdu ama profiller
`person_id`'ye değil `normalize_esleme(person_name)`'e göre gruplanıyor:
bölünen kimlik 0/4541. Tipografik kesme işareti de birleşiyor. Gerçekten ayrı
kalan yalnız takma ad / yazı sistemi farkı (神保彰 ↔ Akira Jimbo, Bob Siebenberg
↔ Bob C. Benberg); bunlar isimden çözülemez, MusicBrainz alias verisi gerekir.
Açık iş olarak duruyor.

## 2026-08-16 — Dinleyici profili ekranı ve grafikler

Kullanıcı isteği: "grafikler de ekleyebilirsin... veyahut dinleyici profilleri
ekleyebiliriz kütüphanene göre sen böyle birisin."

**Referans sorunu ve verilen karar.** "Sen şöyle birisin" bir karşılaştırma
gerektirir. Uydurma bir "ortalama dinleyici" normu ÜRETİLMEDİ — öyle bir veri
yok, üretmek dürüst olmazdı. Yerine iki gerçek çapa:
1. Bu kütüphanede ölçülmüş uçlar (`profil.CAPALAR`): Eminem 0.755 programlanmış
   beat, Meshuggah 0.62 ride ağırlığı, Annihilator 0.77 distorsiyon.
2. Kullanıcının kendi isimlendirdiği kümeler — "Kümelerinin ses imzası" ısı
   haritası. Kümeler kredi ve tür verisinden çıkmıştı; nasıl SESLENDİKLERİ ilk
   kez görünüyor.
Çapası olmayan eksende konum cümlesi kurulmuyor (`_capa_cumlesi` None döner).

**Sayının yanına sesi koymak.** Albüm başına TEK 30 sn klip ölçülüyor ve klip
atipik bir yere denk gelebiliyor — TOOL "Fear Inoculum" en TEMİZ ton çıktı
(0.993), büyük olasılıkla klip temiz arpej girişine düştü. Uç değerleri
gizlemek yerine yanlarına önizleme çalar konuldu: kullanıcı 30 saniyeyi dinleyip
ölçümün albümü temsil edip etmediğine kendi karar veriyor.

**Davul haritasındaki eğilim kısmen aritmetik.** Saçılımda tekme–zil arasında net
bir düşen eğilim var; paylar 1'e toplandığı için bunun bir kısmı yapısal. Başlıkta
yazılı: okunacak şey eğilim değil, ona göre nerede durulduğu ve dikey saçılım.

**Grafik okunabilirliği ölçülerek düzeltildi.** Isı haritasında eksenler yatayda
-35 derece ile denendi, Vega sekiz etiketin yarısını atıyordu; eksenler çevrildi
(eksen adları dikeyde, küme adları yatayda). Uygulama tarayıcıda açılıp
doğrulandı: 6 grafik, 19 önizleme çalar, 0 istisna.

**Test bir hata yakaladı.** `eksen_ozeti` eksik sütunda KeyError atıyordu — eski
bir veritabanı ya da kısmi ölçüm tüm profil ekranını çökertirdi. Sütun kontrolü
eklendi.

## 2026-08-16 — Üçüncü aday stratejisi: bilinçli uzaklık

Faz 2 planının eksik ayağı. Diğer iki strateji kütüphanenin bir adım yakınında
kalıyor (`kredi_sicramasi` zaten dinlenen müzisyenin başka işi, `sahne_komsulugu`
doğrudan komşu); kullanıcının "yeni müzikler keşfedemiyorum" sorununu asıl bu
kırmalı.

**Tanım:** kalabalık grafiğinde iki adım — eksen sanatçıları → 1. adım komşular
(köprüler) → 2. adım komşular. Havuzdan köprüler ve sahip olunanlar çıkarılır.
"Uzak" uydurulmuyor, sayılıyor: birinci adımda görünmemiş olmak.

**İKİ KEZ ÖLÇÜLDÜ, İKİ KEZ BAŞARISIZ OLDU.**

1. *Sıralama = köprü sayısı.* Sonuç doğrudan mainstream: Green Day, The
   Offspring ve en fenası Coldplay — Meshuggah/Slipknot/Gojira/Opeth kümesinde.
   Sebep yapısal: popüler sanatçıya çok köprü işaret eder, tam da popüler olduğu
   için. Köprü çeşitliliği keşif sinyali değil, popülerlik vekiliymiş.
2. *Eksen-özgüllüğü ÇARPAN olarak.* `köprü × skor × ln(1+eksen/df)`. Dokuz
   eksende eşik beşe çıktı, yalnız Bob Dylan elendi; Muse (df=3) ve The
   Offspring (df=4) listenin başında kaldı. Zayıf bir IDF, popülerlik vekiliyle
   çarpılan bir skoru çeviremiyor.

**Çalışan çözüm: özgüllük BİRİNCİL SIRALAMA ölçütü.** `(df artan, destek azalan)`
artı df ≥ eksen/3 olanların tamamen elenmesi. Ölçüm net: metal ekseninde df=1
adaylar Motörhead, Anthrax, Children of Bodom, Dark Tranquillity, Arch Enemy,
Soilwork; aynı eksende çarpımsal puanlamanın getirdikleri Green Day ve AC/DC idi.

Köprü sayısı ile özgüllük gerilimli — df=1 adayların neredeyse hepsi tek köprülü.
Müzikal sinyali taşıyan taraf özgüllük. Bu, `sahne_komsulugu`'ndaki kesişim ve
`kume_kadrosu`'ndaki lift ile aynı aile: popülerlik yanlılığı bu projede üçüncü
kez aynı yolla çözüldü ve üçünde de SIRALAMA ölçütü olarak, çarpan olarak değil.

**Sonuç dürüstçe: kütüphanenin niş olduğu eksende çok iyi, mainstream olduğu
eksende hâlâ zayıf.** "jazz işi" ekseni city pop / Japon AOR getirdi (Kaoru
Akimoto, Mariya Takeuchi, Miki Matsubara, Yumi Matsutoya) — kütüphanede Casiopea
ve 高中正義 olan biri için tam isabet. Metal ekseni melodik death metal getirdi.
Ama hip-hop ve pop eksenlerinde hâlâ Drake, Travis Scott, Maroon 5, U2 çıkıyor.
Bu bir kusur değil sınır: kalabalık grafiği mainstream bir eksenden iki adım
gidince yine mainstream'e varıyor, çünkü elinde başka bilgi yok. Ses uzaklığını
(stem profili) sıralamaya katmak bunu kırabilir — açık iş.

**Yan bulgu: canlı kayıt süzgeci.** MusicBrainz canlı kayıtları da
`primary-type=Album` döndürüyor; ayırt eden `secondary-types`. Süzülmediği için
öneri listesine bootleg konser kayıtları doluyordu (The Killers için ilk üç
adayın ikisi "2004-11-12: Manchester" gibi tarih başlıklıydı; Rage Against the
Machine için "Live & Rare"). `gercek_albumler()` ortak süzgeci eklendi — hata
`sahne_komsulugu`'nda da vardı, ikisi birden düzeldi.

## 2026-08-17 — Ses uzaklığı: kalabalık grafiğinin göremediği boyut

`bilincli_uzaklik`'in raporlanan sınırıydı: kütüphanenin niş olduğu eksende iyi,
mainstream olduğu eksende zayıf. Sebep, kalabalık grafiğinin elinde "bu ikisi
kulağa farklı geliyor" bilgisinin OLMAMASI. O bilgi `stem_profili`'nde var.

`python/discover/ses_uzakligi.py`: adayın ayrılmış stem'leriyle eksenin ses
merkezi arasındaki standartlaştırılmış mesafe.

**Ölçek kütüphane sigması, aday havuzu değil.** Aday havuzuyla ölçeklenirse birim
o gün hangi adayların üretildiğine göre değişir ve iki çalışma kıyaslanamaz.

**Eksik boyut medyanla DOLDURULMUYOR.** Doldurmak enstrümantal bir albüme
"vokali ortalama" demek olurdu. Mesafe yalnız iki tarafta da ölçülmüş
boyutlardan hesaplanıyor, kaç boyuttan çıktığı da dönüyor.

**Kök ortalama kare, ham Öklid değil.** Ham Öklid'de dört stem'i ölçülmüş aday,
yalnız davulu ölçülmüş adaydan otomatik "daha uzak" çıkardı — mesafe boyut
sayısıyla büyür. Normalize edilince farklı kapsamalı adaylar kıyaslanabiliyor.

**Doğrulandı — kütüphanenin kendi içinde ayırıyor.** Metal ekseni (Küme 2) için
uzaklık medyanları: kendi üyeleri 0.76, rock kümeleri 0.89–1.01, jazz 1.10,
hip-hop 1.31, en uzak Küme 3 1.38. Jazz ekseninde ikinci sırada «rush» (prog
rock) çıkıyor — füzyona gerçekten komşu. Ayrım +0.34 / +0.30 sigma.

**Her eksende işe yaramıyor.** «istemiyen» ekseninde kendi üyeleri 0.98, diğerleri
1.01 — fark 0.03, yani ayrım yok. Heterojen bir kümenin ses merkezi anlamlı
değil. Arayüz tabanı gösteriyor, kullanıcı ölçütün o eksende işe yarayıp
yaramadığını kendisi görebiliyor.

Sıralamaya ÜRETİM sırasında giremiyor: uzaklık ancak aday profillendikten sonra
bilinebiliyor. Arayüzde sonradan uygulanan bir sıralama/etiket olarak duruyor.

## 2026-08-17 — İki yazma hatası

**1. Yeniden üretim önizlemeleri siliyordu.** `adaylari_yaz` `INSERT OR REPLACE`
kullanıyordu; satırın TAMAMINI değiştiriyor ve `onizleme_url` sütun listesinde
olmadığı için NULL'a çekiyordu. Ölçüldü: bir yeniden üretimden sonra 253 satırın
253'ünde önizleme silinmişti. `ON CONFLICT ... DO UPDATE SET` ile yalnız üretimin
sahibi olduğu sütunlar güncelleniyor — `profil_yaz`daki ayrımın aynısı.

**2. Bayat adaylar ortada kalıyordu.** Canlı kayıt süzgeci eklendikten sonra
"Rage Against the Machine — Live & Rare" listede durmaya devam etti: kullanıcı
düzeltilmiş bir sistemin düzeltilmemiş çıktısını görüyordu. `bayat_adaylari_temizle`
bu turda üretilmeyen eski satırları siliyor — ama KARAR VERİLENLERİ değil,
beğenilen bir albümün kaydını kaybetmek geri bildirim geçmişini boşa çıkarırdı.
Mevcut veritabanında 8 satır silindi (canlı kayıt, DJ mix, "Chopped Not Slopped"
remiks, Nirvana bootleg'leri), geri bildirimli 3 satır korundu.

## 2026-08-17 — Geri bildirim döngüsü: üç karar, İKİ ayrı eksen

Faz 3'ün son yazılmamış parçası. En kolay hata üç kararı tek bir "iyi–kötü"
ekseninde toplamak olurdu; oysa «zaten biliyorum» bambaşka bir şey söylüyor:

    beğendim         → zevk tuttu   ✓   keşif oldu ✓
    tutmadı          → zevk tutmadı ✗   keşif oldu ✓  (yeni bir şeydi)
    zaten biliyorum  → zevk hakkında BİLGİ YOK     ✗  keşif OLMADI

İki ayrı oran hesaplanıyor: zevk isabeti «zaten biliyorum»u PAYDAYA ALMAZ,
keşif oranı alır. Bir strateji zevkte mükemmel olup keşifte tamamen başarısız
olabilir ve projenin çıkış noktası göz önüne alınınca ikincisi daha ağır bir
başarısızlık.

**İlk ölçüm bunu hemen gösterdi.** `sahne_komsulugu`: zevk isabeti 2/2 (%100)
ama keşif oranı %20 (Wilson %90: %7–%46). On karardan sekizi «zaten biliyorum»,
çoğu Nirvana. Yani kullanıcının kesin seveceği ama zaten bildiği albümleri
buluyor. `kredi_sicramasi` tersi: keşif 3/3 ama zevk 1/3.

**Küçük örneklem: Wilson skor aralığı.** Ham oran bu boyutta yanıltıcı — 1/1 =
%100 ile 80/80 = %100 aynı sayı değil. Normal yaklaşım p=0 ya da p=1'de
genişliği sıfır veriyor, yani tek gözlemde kesinlik iddia ediyor. Arayüz tek
sayı değil aralık gösteriyor.

**Kendi tuzağıma düştüm ve test yakaladı.** Cümle üretimi yalnız
`kesif_ust < 0.75` arıyordu; tek kararlık `bilincli_uzaklik` (n=1, üst sınır
0.73) on kararlık `sahne_komsulugu` ile AYNI alarmı aldı — bu modülün baştan
kaçınmak için yazıldığı hatanın ta kendisi. `ASGARI_N = 4` eklendi.

**Geri bildirimin işe yaradığı yer.** "Eksen ağırlıklarını güncelle" demedik —
kullanıcı ekseni zaten kendi seçiyor, bulanık bir çarpan dürüst olmazdı. Somut
kullanım: bir sanatçıyı «zaten biliyorum» dediysen o sanatçının DİĞER albümleri
de büyük olasılıkla biliniyordur. Öneri listesi onları geri plana atıyor —
ELEMİYOR, çünkü Nirvana'yı bilip «Bleach»i duymamış olabilirsin. Doğrulandı:
grunge ekseninde 4 aday sona alındı ve listenin başı Radiohead oldu.

## 2026-08-17 — Görsel dil tek yerde toplandı

Uygulama dokuz sekmeye büyürken her sekme kendi biçimini üretmişti. `app/tema.py`
ve `.streamlit/config.toml` bunu topluyor.

**Başlık Faz 1'den kalmaydı.** "Ayna — kendi kümelerini isimlendir" uygulamanın
ilk halini anlatıyordu; artık aday üretiyor, icra profili ölçüyor, geri
bildirimden öğreniyor. Yeni başlık ne yaptığını söylüyor ve altında boru
hattının beslendiği aşamalar sayaç olarak duruyor — uygulama sessizce eksik
veriyle çalışabildiği için (stem yoksa icra ekranı boş) bunu sekmeye girip
keşfetmek yerine üstte görmek dürüst.

**Renk seçimi keyfi değil.** Sıralı ölçüler (uzaklık, yayılım) tek renk üzerinden
koyudan açığa; iki yönlü ölçüler (medyandan SAPMA) sıcak–soğuk, çünkü orada
sıfırın iki yanı farklı anlam taşıyor. Strateji rozetlerinin rengi de stratejinin
ne yaptığına bağlı: kadrondan (sıcak) → 1 adım (ara) → 2 adım (soğuk/uzak).

**Kategorik palet elle seçildi.** Altair'in varsayılanı koyu zeminde iki maviyi
yan yana koyuyor ve 12 kümeli bir saçılımda kümeler ayırt edilemiyordu.

**Üç somut kusur ölçülüp düzeltildi:**
- Üst sayaçlar başlığın yanına konunca sayfanın %40'ına sıkışıp etiketler
  "3.." diye kırpılıyordu → tam genişliğe alındı.
- Ham `snake_case` sütun adları arayüze sızıyordu (`bu_rolde_album`, `rol_payi`,
  `sanatcilar`) → `tema.SUTUN_ADLARI` tek sözlükte topladı.
- `from app import tema` dairesel import veriyordu: Streamlit betiğin klasörünü
  de sys.path'e ekliyor, `app` adı hem paketi hem çalışmakta olan modülü
  işaret ediyor → düz modül adıyla alındı.

**`@st.cache_data` içinde `st.metric` çağırmak yanlış.** Önbellek dönüş değerini
saklar, çizimi değil; ikinci çalıştırmada ekrana hiçbir şey basılmaz. Veri
çekme (`_boru_hatti_sayilari`) ve çizim (`_ust_ozet`) ayrıldı.

## 2026-08-17 — Alias birleştirme: aynı kişi, farklı ad

Öneri listesinde görünen kusur: bir aday için "en yakın davulcular" listesinde
aynı kişi iki kez, iki farklı puanla çıkıyordu (神保彰 +0.887, Akira Jimbo
+0.769). Profilleri bölünmüş, her biri albümlerinin yarısından hesaplanmıştı.

`normalize_esleme` bu sınıfı çözemez — ortak token yok. Kaynak MusicBrainz
alias verisi, ama ham alias listesini almak tehlikeli: geniş, bazen grup
adlarını içeriyor. İki kısıt kondu: (1) yalnız iki tarafı da kredilerde var
olan adlar birleşir, (2) yalnız `type=Person`.

**Sonuç: 65 birleşme, hepsi doğrulanabilir.** `bob c benberg → bob siebenberg`,
`edward van halen → eddie van halen`, `joe duplantier → joseph duplantier`
(metal kümesinin kadrosunda!), `lerxst → alex lifeson`, `133 → craig jones`
(Slipknot üye numarası), `marshall mathers → eminem`, `clown → shawn crahan`.

**Kendi eşiğim, çözmeye çalıştığı sorunu gizliyordu.** İlk sürümde hedef küme
"enstrüman rolünde ≥2 albümde geçen MB kimlikli kişiler" idi (262 kişi, ~4 dk).
Başlangıç örneğim 神保彰 bu kümeye GİRMEDİ: MusicBrainz kimliğiyle tek albümde
geçiyor. Oysa bölünmenin tanımı gereği kişinin albümleri ikiye ayrılıyor ve her
yarı eşiğin altında kalabiliyor. Eşik 1'e indirildi (1065 kişi, ~18 dk).

Okuma tarafı İKİ yerde: `muzisyen._anahtar` ve `icra_profili.muzisyen_profilleri`.
Biri birleştirip diğeri birleştirmezse kişi arayüzde görünür ama icra profili
"yok" çıkar — testle sabitlendi.

**Kusur düzeldi, ölçüldü.** Aerosmith «Get Your Wings» için en yakın davulcular
listesi ÖNCE: Neil Peart +0.890, 神保彰 +0.887, Akira Jimbo +0.769 (aynı kişi
iki kez, bölünmüş profillerle). SONRA: Neil Peart +0.894, Michael Derosier
+0.880, Akira Jimbo +0.858 — tek satır, üç klipten hesaplanmış profille ve
daha yüksek benzerlikle.

## 2026-08-18 — Streamlit bırakıldı: Starlette + Jinja2 + elle SVG

Kullanıcı: "streamlit çok amatör duruyor... gerekirse streamliti bırakıp başka
bir yapıya geç."

**Gerekçe biçimsel değildi.** Üç somut sorun:
1. Her etkileşim tüm betiği yeniden çalıştırıyor. Bir aday için 👍'ye basınca
   sayfa baştan kuruluyor ve ÇALAN 30 SANİYELİK ÖNİZLEME KESİLİYORDU — oysa bu
   uygulamanın çekirdek eylemi "dinle ve karar ver".
2. Durum URL'de yok: bir eksene bağlantı verilemiyor, geri tuşu çalışmıyor,
   yenileyince seçim kayboluyor.
3. Görünüm ancak Streamlit'in CSS'ini geri döndürerek denetlenebiliyordu;
   `app/tema.py` giderek Streamlit'e karşı yazılmış bir yama listesine dönüştü.

**Seçilen yığın: Starlette + Jinja2 + uvicorn. YENİ BAĞIMLILIK YOK** — üçü de
zaten kuruluydu, Streamlit'in kendi bağımlılıklarıydı. K8 (tek dil) ve K2 (0 TL)
korunuyor. FastAPI bile eklenmedi; Starlette tek başına yetiyor.

**Grafikler elle SVG** (`web/grafik.py`). Üç seçenek tartıldı: Vega-Lite+JS
(~350 KB ve kendi tipografi varsayımları — Streamlit'te bastırmak için verilen
savaşın aynısı), sunucuda PNG (yeni bağımlılık, yakınlaştırınca bulanık), elle
SVG (bağımlılık sıfır, her ölçekte keskin, `<title>` ile ipucu bedava). Çizilen
dört tür de basit geometri: yatay çubuk, saçılım, ısı haritası, aralık.

**Hesap katmanı HİÇ DEĞİŞMEDİ.** `python/` altındaki modüller zaten DataFrame
döndüren saf fonksiyonlardı; taşıma tamamen görüntü katmanıydı. Bu, katmanları
ayrı tutmanın somut getirisi.

**Kazanılan:** karar verirken ses kesilmiyor (doğrulandı: `fetch` ile kaydediliyor,
`<audio>` elemanı yerinde kalıyor, sayfa yenilenmiyor), aynı düğmeye ikinci kez
basmak kararı geri alıyor, her ekranın kendi URL'si var, ve **görüntü katmanı
artık test edilebilir** — Starlette test istemcisi sunucuyu ayağa kaldırmadan
istek atabiliyor (`tests/test_web.py`). Streamlit'te bunun karşılığı yoktu.

**Yol boyunca üç hata:**
- Starlette 1.3 imzası `TemplateResponse(request, ad, bağlam)`; eski çağrı
  şablon adı yerine sözlük alıp "cannot use 'tuple' as a dict key" gibi
  anlaşılmaz bir hatayla düşüyordu.
- `kendi.get(x) == kendi.get(x)` NaN kontrolü DEĞİL: eksik sütunda ikisi de
  None döner ve `None == None` doğrudur.
- `width:100%` + `height:auto` görünüm kutusunun oranını koruduğu için geniş
  kolonda 720×420'lik saçılım 1094×638'e şişiyordu; `max-height` ile sınırlandı.

`app/` ve `.streamlit/` kaldırıldı. Özellik denkliği sağlandı — MusicBrainz
elle eşleştirme ekranı da taşındı (55 albüm onu bekliyor).

## 2026-08-18 — Çalma listesi katmanı: kullanıcı kaydı olmadan ortak filtreleme

Kullanıcı önerileri beğenmiyordu ve yönü kendisi verdi: "interneti kullan,
bolca şarkı bul, dinleyici tipi bul, playlist bul."

**Teşhis — ölçülen dört sebep:**
1. `plays` boş. Sistem neye SAHİP olduğunu biliyor, neyi SEVDİĞİNİ bilmiyor;
   302 albüm eşit ağırlıkta.
2. Aday havuzu 116 sanatçı — kütüphanedeki 149'un altında.
3. ListenBrainz `similar-artists` sanatçı düzeyinde ve popülerliğe yanlı;
   `sahne_komsulugu` kararlarının %80'i «zaten biliyorum» aldı.
4. 12 küme × 302 albüm = küme başına ~25; zevk tarifi değil kaba bölme.

**Netflix düzeltmesi.** Kullanıcı 70 bin kategoriyi kümelemeyle bulunmuş
sanıyordu. Değil: insan etiketçiler filmleri onlarca boyutta etiketledi,
kategoriler o etiketlerin KOMBİNASYONU. Bu bizim lehimize — albüm başına
ölçtüğümüz eksenler (ızgara entropisi, zil/tekme, harmonik pay, perde aralığı)
zaten aynı türden bir etiket kümesi. Açık iş olarak duruyor.

**Yapılan: çalma listesi hasadı** (`python/discover/calma_listesi.py`).
Kaynak Deezer'ın anahtarsız genel API'si — belgelenmiş uçlar, Reddit/RYM'de
reddedilen "onaysız uç nokta" kategorisine girmiyor (K2 korunuyor).

Sonuç: **482 liste, 45.899 parça, 10.360 ayrı sanatçı.** Aday havuzu 116'dan
10.360'a çıktı. 358 tek-sanatçılık derleme elendi.

**İki tuzak ölçülerek çözüldü:**

1. *Tek sanatçılık listeler.* "meshuggah" aramasının ilk sonucu «100%
   Meshuggah», 50 parçanın 50'si aynı gruptan — birliktelik sinyali sıfır ama
   en alâkalı sonuç olduğu için hep başa geliyor. Bir sanatçı listenin
   yarısından fazlasını kaplıyorsa liste atılıyor.

2. *Popülerlik.* İlk 22 listelik örneklemde ham birliktelik **Van Halen ↔
   Madonna, Haddaway, KC & the Sunshine Band** verdi — bunlar 80'ler PARTİ
   listeleri, sinyal "müzikal benzerlik" değil "ikisi de 80'ler". Çözüm PMI
   (bu projede popülerlik yanlılığının dördüncü kez aynı aileden bir ölçütle
   çözülüşü: kesişim, lift, eksen-özgüllüğü, şimdi PMI).

**482 listede PMI müzikal olarak doğru çıkıyor:** The Ocean ↔ Pineapple Thief /
Devin Townsend / Klone / Caligula's Horse (modern prog metal), Emerson Lake
Palmer ↔ Gentle Giant, Vega ↔ TNK / Dört x Dört (Türkçe rock), King Gizzard ↔
Psychedelic Porn Crumpets, Mushroomhead ↔ Coal Chamber / Ill Niño / Mudvayne,
Adam Nitti ↔ Nathan East (iki füzyon basçısı).

**Yeni strateji PARÇA düzeyinde.** Diğer üçü albüm öneriyor ve önizlemesini
sonradan arıyor; bu parça öneriyor ve önizlemesi hasattan hazır geliyor.
277 parça adayı, 106 yeni sanatçı, hepsi dinlenebilir. Metal ekseninde
Car Bomb / Between the Buried and Me / Pain of Salvation, jazz ekseninde
Spyro Gyra / Nathan East / Alain Caron.

**Yan bulgu — "dinleyici tipi" sinyali liste BAŞLIKLARINDA.** «GYMeshuggah»,
«CHUG», «chill», «instrumental», «fusion», «doom», «soundtrack», «jam»:
kalabalığın kendi kelime dağarcığı. Saklanıyor, çok boyutlu etiketlemenin
kaynağı olacak.

## 2026-08-18 — Öneri kartı sanatçı düzeyinde

Ölçüldü: aday listesinde sanatçı başına ~2,2 albüm ve skora göre sıralama
aynı sanatçının albümlerini arka arkaya diziyordu — bir eksende ilk ON sıra ÜÇ
sanatçıdan ibaretti (RATM ×4, NIN ×4, Nirvana ×2). Kullanıcı on kart kaydırıp
üç fikir görüyordu.

Gerekçe zaten sanatçı düzeyinde ("bunu dinleyenler şunu da dinliyor"); albüm
düzeyinde tekrarlamak bilgi eklemiyordu. Artık bir sanatçı = bir kart,
albümleri/şarkıları kartın içinde ızgarada. Karar da sanatçı düzeyinde —
«zaten biliyorum» zaten grup hakkında bir cümle; veritabanında yine albüm
başına satır duruyor, tek istekte hepsi yazılıyor.

Ayrıca `adaylar.onizleme_parca` eklendi: hangi şarkının çaldığı yazılı olmadan
kart içindeki liste okunmuyordu.

## 2026-08-18 — Önizleme yanlış albümün klibini getiriyordu

Arayüzde görüldü: Mariya Takeuchi'nin üç ayrı albümü (*Beginning* 1978,
*University Street* 1979, *Love Songs* 1980) aynı şarkıyı gösteriyordu —
«Plastic Love», ki 1984 *Variety* albümünden. Üçünün ses uzaklığı da aynıydı
(0.90), yani üçü de aynı klipten ölçülmüştü.

Kök neden: `onizleme_bul` SANATÇIYI doğruluyor (`_uyuyor_mu`) ama ALBÜMÜ
doğrulamıyordu. Zayıf albüm eşleşmesinde arama, sanatçının hit şarkısına
düşüyor. Ölçüldü: 6 grup, 13 aday etkilenmiş (RATM, Smashing Pumpkins,
Tatsuro Yamashita, Junko Ohashi, Geddy Lee dahil).

**Bedeli sadece yanlış şarkı çalmak değildi:** aday albümün stem ölçümü o
klipten yapılıyor, yani `ses_uzakligi` de yanlış albümü anlatıyordu. 49 zehirli
stem ölçümü silindi.

`_album_uyuyor_mu` eklendi. Aşırı katı olmamak için varyantlar kabul ediliyor
(«Gish» ↔ «Gish (Remastered)», «Use Your Illusion I» ↔ «Use Your Illusion 1»)
ama farklı albüm reddediliyor. Doğrulanamıyorsa önizleme YOK sayılıyor —
yanlışını göstermekten iyi.

Bedel kapsamada: albüm adaylarında %90'dan %88'e. Parça adayları (çalma listesi
hasadı) %100 — onların klibi zaten parçanın kendisi, eşleştirme sorunu yok.

## 2026-08-18 — Sözlük ve çok boyutlu etiketleme

**Sözlük** (`python/sozluk.py`, `/sozluk`). 28 terim; her biri dört parça
taşıyor: bir cümlelik tanım, nasıl ölçüldüğü, BU KÜTÜPHANEDE ölçülmüş çapalar
(TOOL zil 0.17 · Meshuggah 0.62 gibi) ve varsa ölçütün bilinen sınırı. Çapalar
gerçek ölçüm; uydurma referans yok (K13). Sınırlar gizlenmiyor — ör. ızgara
entropisinin işini kuyrukta yaptığı, `enerji_payi`nın icra değil prodüksiyon
anlattığı, ses uzaklığının heterojen eksende işe yaramadığı yazılı.

**Etiketleme** (`python/etiket.py`, `/etiketler`). Netflix modeli doğru
anlaşılmış hâliyle: ~76 bin kategori kümelemeyle BULUNMADI, insan etiketlerinin
KOMBİNASYONUYDU. Üç eksen MTG-Jamendo'nun yapısını izliyor (o veri kümesi 195
etiketi tür/enstrüman/ruh-tema diye ayırıyor):

    tür        MusicBrainz etiketleri + dönem + ülke
    enstrüman  ayrılmış stem ölçümleri
    doku       ton, dinamik, tempo

**Eşikler veriden geliyor, elle yazılmıyor.** Bir albüm bir eksende etiket
ancak KUYRUKTAYSA alıyor (üst/alt %20). "Zil ağırlıklı" demek ancak
kütüphanenin geri kalanına göre anlamlı; sabit eşik (örn. > 0.5) başka bir
kütüphanede saçmalardı. Ortadaki albümler etiket ALMIYOR — her albüme her
etiketi yapıştırmak etiketi bilgisizleştirirdi.

Sonuç: 302 albüme 3.527 etiket, 237 ayrı etiket, 60 tarif. Örnekler:
«ağır, yoğun davullu rock» (13 albüm), «geniş dinamik, programlanmış ritimli
rock» (10), «tok, kalın vokallı electronic» (10).

**İki dilbilgisi hatası, ikisini de test yakaladı:**
- Düz birleştirme "davullı", "söyleyişlı", "ritimlı" üretiyordu → ünlü uyumu
  (`_lu`).
- Her onyıla `'ler` ekleniyordu; Türkçede değişiyor — 1990'**lar** (doksanlar),
  1980'**ler** (seksenler), 1960'**lar** (altmışlar).

## 2026-08-18 — Veri kümesi araştırması

Kullanıcı üç bağlantı verdi (FMA, MSD, MTG-Jamendo) + The Atlantic'in AI eğitim
veri kümeleri yazısı.

**Etik not.** Atlantic yazısı FMA içeriğinin ticari AI müzik modellerini
eğitmekte, sanatçılara sorulmadan kullanılmasıyla ilgili. Bizim kullanımımız
farklı kategori — üretken model eğitmiyoruz — ama ses indirilmiyor ve
dağıtılmıyor; yalnız CC BY 4.0 metadata/öznitelik kullanılacaksa kullanılıyor.

**Değerlendirme:**
- **MTG-Jamendo**: 55.525 parça, 195 etiket (87 tür / 40 enstrüman / 56
  ruh-tema). Sesi 508 GB, GEREKMİYOR. Alınan şey ÜÇ EKSENLİ YAPI — etiketleme
  bu modele göre kuruldu.
- **FMA**: `fma_metadata.zip` yalnız 342 MB ve içinde 106.574 parçanın librosa
  öznitelikleri + 161 türlük hiyerarşi var, sesi gerekmeden. Bu, kendi 30 sn
  kliplerimizden aynı öznitelikleri hesaplayıp tür sınıflandırıcısı eğitmeyi
  mümkün kılar — MusicBrainz etiketi olmayan adayları da etiketleyebilmek için.
  AÇIK İŞ.
- **MSD**: asıl değeri Taste Profile (ortak filtreleme) ama MSD↔MusicBrainz
  eşleştirmesi zahmetli ve kullanıcı dinleme geçmişini sonraya bıraktı.
  ERTELENDİ.

## 2026-08-18 — Bağlam etiketleri ve adayların etiketlenmesi

Etiketler kütüphane albümlerinde vardı ama ADAYLARDA yoktu — oysa etiketin asıl
işe yarayacağı yer öneri kartı.

**1. Bağlam etiketleri («dinleyici tipi»).** Çalma listesi başlıkları kalabalığın
müziği hangi bağlama koyduğunu söylüyor: «Evening Chill», «GYMeshuggah»,
«Calm jazz for work», «Dimanche Matin». Kredi grafiği de tür etiketi de bunu
söyleyemiyor.

Sözlük KONTROLLÜ, serbest kelime toplanmıyor. Başlıklarda sanatçı adları
(«GOJIRA DEEZER», «Ritchie Blackmore»), kişisel notlar («new staff», «Jesse
john's») ve coğrafya («Top Croatia») var. Sözlük MTG-Jamendo'nun 56 ruh/tema
etiketinden türetildi, çok dilli varyantlarıyla (relax/chill/douceur/sakin).

**Eşik kararı ölçülerek verildi.** İki listede geçme şartı kapsamayı öldürüyordu:
kütüphanenin 147 sanatçısından yalnız 18'i etiket alıyordu (eşik 1'de 79).
Sebep, liste başlıklarının yalnız %17'sinin sözlükten terim içermesi. Çözüm bu
projede tekrarlayan çözüm — otomatik elemek yerine KANITI GÖSTERMEK: etiket kaç
listeden geldiğini taşıyor, bir listeden gelen bir kişinin kararı, beşten gelen
bir örüntü.

**2. Adayların ölçüm etiketleri.** `aday_olcum_etiketleri` adayın kendi
stem'lerinden etiket üretiyor. Eşikler KÜTÜPHANEDEN, aday havuzundan değil:
etiketin anlamı "senin kütüphanene göre zil ağırlıklı" olmalı. Aday havuzuna
göre ölçeklenirse etiket o gün hangi adayların üretildiğine bağlı hale gelir —
`ses_uzakligi`'ndaki ölçek kararının aynısı. Testle sabitlendi.

**Kartta iki renk.** Gri = adayın kendi ölçümünden (sesin kendisi), mavi ◑ =
çalma listesi bağlamından (insanların onu nereye koyduğu). İki kaynak farklı
şeyler söylüyor, renkle ayrılıyor. Bağlam etiketine tıklayınca aynı etiketli
her şey geliyor. İpucu etiketin ne demek olduğunu yazıyor — «ayak yüklü davul:
bas davul mikste öne çıkıyor».

Sonuç: 176 aday albümde ölçüm etiketi, 3.119 sanatçıda bağlam etiketi.

## 2026-08-18 — Etiketleme: iki başarısız yol, bir çalışan yol

Kullanıcı "Netflix seviyesinde, hatta bugünün teknolojisiyle daha iyisi" istedi
ve veri kümeleri önerdi (FMA, MSD, MTG-Jamendo). Üç yöntem denendi.

### 1. Sıfır-atışlı CLAP etiketleme — YETMEDİ

CLAP sesi ve metni aynı uzaya gömüyor; etiketi doğal dille yazıp eğitimsiz
sınıflandırma yapılabiliyor. Kurulumda iki tuzak aşıldı:
- `laion/larger_clap_music` transformers 5.15'te BOZUK: ses kulesi girdiden
  bağımsız neredeyse sabit gömü veriyor (beyaz gürültü ↔ saf sinüs kosinüs
  0.98), dört etiket de tam 0.25 alıyor. `laion/clap-htsat-unfused` doğru.
- 22.05 kHz sesi 48 kHz diye vermek modele yanlış perde/tempo gösteriyor;
  o durumda her klip "hip hop" çıkıyordu.

Düzeltilince küçük örneklemde doğru göründü (Meshuggah → death metal 0.65,
Opeth → doom 0.68, Eminem → hip hop). Ama TÜM kütüphanede çöktü: TOOL →
"anadolu" 0.96, Eminem → "türk rock" 1.0.

Sebep ölçüldü — İSTEM YANLILIĞI. "anadolu" istemi tüm kütüphanede ortalama
+0.506, "türk rock" +0.505 alıyor; "ambient" +0.091. Bu istemler her şeye
yapışıyor. İstem başına standartlaştırma bazılarını düzeltti (Casiopea:
hard rock → funk) ama başkalarını bozdu (TOOL → klasik). Altıda üç.

### 2. FMA ile denetimli tür sınıflandırıcı — AKTARILAMADI

`fma_metadata.zip` (342 MB, ses gerekmiyor) 106.574 parçanın 518 librosa
özniteliğini ve tür etiketlerini taşıyor. Öznitelikler birebir aynı düzende
yeniden hesaplandı, sınıflandırıcı SANATÇIYA göre bölünmüş testte eğitildi
(rastgele bölme aynı sanatçıyı iki tarafa koyup doğruluğu şişirirdi).

FMA'nın kendi testinde: **doğruluk 0.677, makro F1 0.521** (9 sınıf, şans
0.11). Rock 0.80, Electronic 0.72, Hip-Hop 0.65.

Bizim kliplerimizde ÇÖKTÜ: her şey "Rock" ya da "Experimental". Eminem → Rock,
Casiopea → Rock, Meshuggah → Experimental.

Teşhis iki aşamalı yapıldı. Önce öznitelik uzayı kıyaslandı: 518 sütunun
25'inde |z|>3 sapma vardı ve en sapanlar `spectral_rolloff max` (bizim 4.2 kHz,
FMA 9.4 kHz — TAM YARISI) ve `spectral_bandwidth max`. Sebep bizim erken bir
kararımızdı: stem önbelleği disk tasarrufu için 22.05 kHz, yani Nyquist 11 kHz,
yani tizde hiçbir şey yok. Yukarı örnekleme kaybı geri getirmiyor.

Özgün önizleme 44.1 kHz'te indirilip kullanıldı (ayrıca stem TOPLAMI özgün miks
değil — Demucs artığı spektrumu değiştiriyor). Sapma 25'ten 14'e düştü ama
tahminler düzelmedi. Kalan sebep ALAN KAYMASI: FMA açık lisanslı amatör/bağımsız
müzik, ticari metal ve hip-hop prodüksiyonu onun sınıflarına benzemiyor.

### 3. CLAP BENZERLİK uzayı — ÇALIŞIYOR, ve en iyi sonuç

Aynı gömüler metne eşlemede değil, ALAN İÇİ benzerlikte kullanılınca çok iyi
çalışıyor — orada ne istem yanlılığı var ne alan kayması.

Kütüphane içi komşuluk: Meshuggah → Gojira/The Ocean · Casiopea → Scott
Henderson/Animals As Leaders · Opeth → Dream Theater · Slipknot → Mushroomhead ·
Eminem → Kendrick Lamar.

**Bir düzeltme gerekti: hubness.** Ham kosinüste bir albüm HER ŞEYE en yakın
çıkıyordu («Foo Fighters — Today's Song», beş adayın dördünde) ve skorlar
0.92–0.98'e sıkışmıştı. Gömü uzaylarının bilinen olgusu. Adayın tüm kütüphaneye
ortalama benzerliği çıkarıldı — bu projede popülerlik/hub yanlılığının BEŞİNCİ
kez aynı aileden bir ölçütle çözülüşü (kesişim, lift, eksen-özgüllüğü, PMI,
şimdi hubness).

Düzeltmeden sonra: metal ekseni → Arch Enemy (← Meshuggah), Children of Bodom
(← Meshuggah), Megadeth (← Annihilator). Jazz ekseni → Brad Mehldau
(← Casiopea), Minoru Mukaiya (← Mezzoforte; Mukaiya Casiopea'nın klavyecisi).
Küme 6 → Radiohead «Kid A» (← Joji), Bonobo (← Joji).

Beşinci strateji `ses_benzerligi` olarak eklendi. Projenin baştan beri eksik
parçasıydı: kredi grafiği "kim çalmış", kalabalık "kim dinliyor" diyordu; bu
"kulağa nasıl geliyor" diyor. Gerekçe kendiliğinden doğrulanabilir — hangi
albüme benzediği yazılı, kullanıcı ikisini arka arkaya dinleyebiliyor.

### Arayüz sadeleştirmesi

Dokuz düz menü öğesi üç öbeğe ayrıldı (Keşfet / Kütüphanen / Bakım). Öneriler
sayfasında dört filtre grubu ikiye indi: Eksen ve "Nereden" görünür, geri
kalanı katlanmış ⚙ ayarlar'da. Strateji çoklu-onay yerine tek seçim ve
okunur adlarla ("kadrondaki müzisyenler", "1 adım — komşuların"). Boru hattı
sayaçları katlanabilir oldu.

## 2026-08-18 — Ses kümeleri: türü etiketten değil sesten keşfetmek

Kullanıcı çerçevemi düzeltti: **"sahip olduğumu seviyorum, bu yüzden
kümeliyoruz. j-fusion sahibim, rock sahibim, grunge sahibim. ve seviyorum...
j-fusion önerisi istediğimde elimde olmayan bir öneri gelsin. bu kadar basit.
biz de müzik genrelerine takılı kalmayalım, gerekirse tüm müzikleri analiz edip
yeni genreler keşfedelim."**

Bu düzeltme önemli ve kabul edildi. Ben `plays` tablosunun boş olmasını temel
bir eksik sayıyordum; oysa kütüphane KÜRASYONLA kurulmuş — 302 albümün her biri
zaten bir "evet". Sahiplik tercih sinyalidir. `plays` bir zenginleştirme, ön
koşul değil. (K7'nin "en çok dinlediğin %10'da" şablonu bu yüzden zorunlu
değil, opsiyonel.)

**Yapılan: CLAP gömüsünde kümeleme** (`python/ses_kume.py`). Hiçbir tür etiketi,
kredi ya da metadata kullanılmıyor — yalnız sesin kendisi.

Boyut indirgeme şart çıktı: 512 boyutta siluet 0.10'da takılıyor (mesafe
yoğunlaşması — K3'teki FCM gerekçesinin aynısı), PCA 16 boyutta 0.168.

**Bulunanlar anlamlı ve mevcut kümelemeden FARKLI.** Uyum ARI 0.073, yani
neredeyse ilgisiz — çelişki değil, iki ayrı bakış: `memberships` "kim çalmış,
nasıl etiketlenmiş", `ses_kumesi` "kulağa nasıl geliyor".

    Küme 11  Masayoshi Takanaka · Casiopea · Plini      ← kullanıcının j-fusion'ı
    Küme 5   Kendrick Lamar · Eminem · Madvillain
    Küme 0   Naniwa Express · Steve Vai · Jam Track Central
    Küme 8   Animals As Leaders · Led Zeppelin · Gergo Borlai

Küme adı UYDURULMUYOR: merkeze en yakın üç sanatçıyla anlatılıyor. Etiket
icat etmek yerine "Casiopea · Takanaka · Plini gibi" demek hem doğrulanabilir
hem kullanıcının kendi adını vermesine açık (K4 gerekçesi).

**Sonuç — kullanıcının tam olarak istediği şey.** Küme 11 seçilince gelenler:
Dizzy Gillespie, Antônio Carlos Jobim, Azymuth, Brad Mehldau, The Blackbyrds,
Booker T. & the M.G.'s, Bonobo, Miki Matsubara. Hiçbiri kütüphanede yok,
hepsi o sesin komşusu, ve her biri "senin şu albümüne benziyor" diye
gerekçeli.

**Havuz büyütüldü.** CLAP benzerliği en iyi yöntemdi ama 469 klipte arıyordu.
Çalma listesi hasadından 45.899 parça kimliği çıkarıldı — TEK API ÇAĞRISI
YAPILMADAN, yerel önbellekten.

Yol boyunca bir şey bulundu: **Deezer önizleme URL'leri kısa ömürlü imzalı.**
Ölçüldü — hasattan saatler sonra 10 URL'nin 10'u da 403 döndü. Kalıcı olan
parça kimliği; taze URL gömme anında `track/{id}` ile alınıyor. Bu yüzden
`liste_parca.parca_id` eklendi.

**Tekilleştirme gerekti:** aynı parça farklı listelerde farklı kimlikle
gömülebiliyor, «Green Onions» iki kez çıkmıştı. Sanatçı+ad ile tekilleştirilip
en yüksek skorlusu tutuluyor.

## 2026-08-18 — Ses kümeleri dinlenebilir oldu; havuz büyüdü

**Eksik olan şey dinlemekti.** Ses kümeleri sayfası tablo olarak çıkmıştı ve
ses yoktu — oysa kullanıcının çekirdek eylemi "dinle ve karar ver".

Engel teknikti: çalma listesi parçalarının saklanan önizleme URL'leri ölü
(Deezer kısa ömürlü imzalıyor). Çözüm `/api/onizleme/{parca_id}`: kullanıcı
"dinle"ye bastığında TAZE URL çekiliyor. Kalıcı olan parça kimliği.

Yönlendirme yerine JSON dönüyor ki tarayıcı `<audio src>`'yi kendi ayarlasın —
böylece bir kez alınan URL sayfa açık kaldığı sürece çalışıyor.

**Ses kümelerine isim verilebiliyor** (`ses_kume_adi`). Kullanıcı "j-fusion"
diyebiliyor; altında hesabın verdiği ad («Casiopea · Takanaka · Plini gibi»)
duruyor. K4'ün gerekçesi: gösterilen şey hesabın verdiği karar olmalı, ama
kimliklendirme kullanıcının.

**Havuz büyümesi kaliteyi ölçülebilir biçimde artırdı.** 469 → 2.163 gömü.
Küme 11 (j-fusion) önerileri:

    469 gömüyle:   Booker T., Jobim, Azymuth, Brad Mehldau
    2.163 gömüyle: Miles Davis (Concierto de Aranjuez, Summertime),
                   Jiro Inagaki and His Soul Media (70'ler Japon jazz-funk),
                   Young Gun Silver Fox (modern yacht rock)

Jiro Inagaki, Casiopea–Takanaka dinleyen biri için tam isabet ve hiçbir tür
etiketi kullanılmadan bulundu. Havuz arka planda büyümeye devam ediyor.

## 2026-09-01 — Değerlendirme düzeneği: motor artık bir sayı veriyor

Bugüne kadar "öneri iyi mi?" sorusu kulakla cevaplandı. `python/degerlendirme.py`
her erişim yoluna bir sayı veriyor.

**Ölçüt kullanıcının seçimi:** başarı = HİÇ DUYMADIĞIN SANATÇI, "zaten
biliyorum" bir başarısızlık. Bu seçim düzeneğin biçimini belirledi.

**Neden albüm değil, SANATÇI gizleniyor.** Klasik leave-one-out bir albümü
gizler. Burada o ölçüt yanlış olurdu: sanatçının diğer albümleri kütüphanede
kalır, motor onu kredi bağından bulur, kullanıcı "zaten biliyorum" der.
Ölçtüğümüz şey tam olarak kaçındığımız şey olurdu. Bu yüzden sanatçının TÜM
albümleri gizleniyor; kalan kütüphane, o sanatçıyı hiç tanımayan birinin
kütüphanesi.

**Kurarken üç şey ölçüldü, üçü de tasarımı değiştirdi:**

1. *Saklanmış PMI tablosu kendi kendini değerlendiremez.* `liste_birlikteligi`
   hesaplanırken kütüphane sanatçıları aday havuzundan çıkarılıyor — ölçüldü,
   1.615 aday anahtarının 0'ı kütüphanede. O tablo kullanılsaydı recall
   yapısal olarak 0 çıkar ve "motor kötü" diye okunurdu. PMI yeniden
   hesaplanıyor.
2. *`adaylar.ses_benzerligi` açık havuzda arama yapmıyor.* `adaylar` tablosunu
   (621 satır) yeniden sıralıyor. Gizlenen sanatçı orada olmadığı için asla
   bulunamaz. Değerlendirilen şey `ses_kume`'nin açık havuz erişimi — Jiro
   Inagaki'yi bulan yol da buydu. **Bu, ürünün kendisinde de bir eksik:**
   öneri sayfasının ses stratejisi kapalı havuzda çalışıyor.
3. *Tavan ayrı raporlanmalı.* 147 kütüphane sanatçısının 132'si çalma
   listelerinde geçiyor, 103'ünün CLAP gömüsü var. Erişilemeyen sanatçı
   sıralama hatası değil kapsama boşluğudur.

**İlk sonuçlar (147 sanatçı, eksen kapsamı):**

    erişim                  tavan  bulunan    @10    @50     MRR  medyan
    liste_birlikteligi    109/147       95   0.00   0.07   0.006     249
    ses_benzerligi        102/147      102   0.01   0.08   0.008     490

**Eksen kümelemesi ölçülebilir biçimde kazandırıyor.** Aynı sınama sorguyu tüm
kütüphaneye karşı yapınca:

    liste_birlikteligi (tüm kütüphane)   @50 0.01   medyan  982
    liste_birlikteligi (eksen)           @50 0.07   medyan  249

K3'ün bulanık kümelemesi bugüne kadar yalnız kuramsal olarak savunuluyordu;
artık 7 kat recall farkı ile ölçülmüş durumda.

**Düzeneğin ilk kazancı: npmi.** Ham PMI'nın nadir-öğe yanlılığı ölçüldü — iki
listede geçip ikisinde de tohumla yan yana olan sanatçı, yüz listede geçip elli
kez yan yana gelenden yüksek skor alıyordu.

    ölçüt   @10    @50     MRR  medyan
    pmi    0.00   0.07   0.006     249
    npmi   0.03   0.14   0.024     159

Üretime alındı (`calma_listesi.birliktelik`, varsayılan `olcut="npmi"`).
Popülerlik/nadirlik yanlılığının bu projede altıncı kez ölçülüp düzeltilişi ve
yine aynı desenle: sönümleme çarpanı değil, ölçütün kendisinin değişmesi.
Skor ölçeği değişti (−1…+1), gerekçe metni ve sözlük buna göre güncellendi.

**Sayıların dürüst okunuşu.** recall@10 ≈ 0,03 iyi bir sonuç değil. Ama bu
sayı bir ALT SINIR: gerçek etiketimiz yalnızca 147 sanatçı için var, gizlenen
sanatçıyı geçen adayların çoğu da iyi öneri olabilir ve bunu ölçemiyoruz
(recsys yazınında missing-not-at-random). Düzeneğin asıl değeri mutlak
seviye değil, yöntemler arası KIYAS — npmi kararı tam olarak bunun örneği.

**Havuz eşiği 3'ten 2'ye indirildi.** Kullanıcının ölçütü "hiç duymadığım
sanatçı" olunca uzun kuyruk değerli hâle geliyor: çok listede geçen sanatçı
zaten popüler, yani muhtemelen biliniyor. ≥2 listede geçen 2.714 sanatçı
gömülüyor (469 → 2.163 → 3.018 ve artıyor).

## 2026-09-02 — Ses stratejisi açık havuza taşındı; iki ölçüm dersi

**Öneri sayfasının ses stratejisi kapalı havuzda çalışıyordu.** `benzer_adaylar`
yalnızca `stem_profili`'ndeki 125 aday albümü yeniden sıralıyordu. Ses kümeleri
sayfası ise 4.183 gömülük açık havuzda arıyordu — Jiro Inagaki'yi bulan yol.
İki sayfa aynı motoru kullanmıyordu ve bunu düzenek görünür kıldı.

`acik_havuz_adaylari` yazıldı, `ses_benzerligi` ona bağlandı. Sonuç: strateji
30 sanatçıdan **87 sanatçıya** çıktı, hepsi çalınabilir. Eksen 0 (metal) artık
Primordial, Thy Catafalque, Whitechapel, Orbit Culture getiriyor.

**HATA DÜZELTMESİ — "taze önizleme" taze değildi.** Geçen oturumda çalışıyor
diye raporlanan `/api/onizleme/{parca_id}` ucu bozuktu: K5 gereği her dış
çağrı önbellekleniyor, dolayısıyla önbellekli çağrı URL'nin ESKİ hâlini
döndürüyordu. Ölçüldü — dönen URL'nin imzası 1.053 saniye önce dolmuştu, ses
dosyası 403 veriyordu. Deezer imzası 900 saniye yaşıyor; yani önbellek 15
dakikadan sonra her zaman ölü URL veriyordu.

Düzeltme `yenile=True`. Genel kural: **kısa ömürlü imzalı URL önbelleklenmez.**
Regresyon testi eklendi — sessizce geri gelirse uygulamanın çekirdek eylemi
("dinle ve karar ver") çalışmaz.

**ÖLÇÜM DERSİ — recall@k farklı havuz boyları arasında kıyaslanamaz.**
Havuz 2.163'ten 4.183 gömüye çıkarıldı (≥2 listede geçen sanatçılar; iş
tamamlandı: 3.050 denendi, 2.020 gömüldü, 1.030'unda önizleme yoktu). Ses
erişiminin recall@50'si 0,08'den 0,03'e DÜŞTÜ.

Bu "erişim kötüleşti" diye okunabilirdi ve yanlış olurdu: havuz iki katına
çıkınca rakip sayısı da iki katına çıkıyor, sabit k'lı ölçüt bunu ceza olarak
yazıyor. Aynı ölçümde yüzdelik (sıra / havuz) 0,349'dan 0,311'e İYİLEŞTİ.
`medyan_yuzdelik` eklendi; farklı havuz boyları arasında yalnız o kıyaslanır.

**ASIL BULGU — çalma listesi sinyali CLAP'ten çok daha güçlü.**

    erişim                 havuz  yüzdelik   rastgeleye göre
    liste_birlikteligi     1.724     0,092         5,4 kat iyi
    ses_benzerligi         2.416     0,347         1,4 kat iyi

Bu şaşırtıcı değil ve CLAP'in kötü olduğu anlamına GELMİYOR. Çalma listesi
birlikteliği örtük bir ortak filtreleme sinyali: listeyi yapan insan zaten
"bunları seven aynı kişi" bilgisini taşıyor, yani sınamanın hedefiyle
(sahiplik) doğrudan aynı hizada. CLAP yalnızca tınıyı kodluyor.

Yani düzenek "sahip olacağın sanatçı" sorusunu ölçüyor; CLAP'in cevapladığı
soru "sende olana BENZEYEN sanatçı" ve ikisi aynı değil. Vekilin sınırı burada
görünüyor. Bir sonraki ölçülebilir adım melez sıralama: hem akustik olarak
yakın hem liste komşusu olan adaylar.

## 2026-09-02 (2) — Melez sıralama: iki sinyalin kaynaşması

Ölçüm melez sıralamayı işaret etmişti; kuruldu, süpürüldü, üretime alındı.

**Kaynaşma yöntemi: sıra toplamı, skor toplamı DEĞİL.** İki sinyalin ölçekleri
kıyaslanamaz — npmi [-1, +1], hubness düzeltmeli CLAP kabaca [-0,35, 0]. Ham
toplamda ölçeği büyük olan kararı verirdi. Karşılıklı sıra kaynaşması (RRF,
k=60) ölçekten bağımsız:

    skor(x) = Σ_i  a_i / (k + sıra_i(x))

Listede olmamak cezalandırılıyor ama sıfırlamıyor: bir listede birinci ama
diğerinde hiç olmayan aday 1/(k+1) alır; iki listede de ellinci olan 2/(k+50)
alır ve ikincisi kazanır. **Kesişim yine bir sönümleme çarpanı olarak değil,
sıralama ölçütü olarak kullanılıyor** — projede bu desenin yedinci uygulaması.

**Ağırlık süpürüldü** (147 sanatçı, eksen kapsamı, npmi):

    ağırlık liste:ses  tavan   @5    @10    @50    MRR   medyan
    1:1                  123  0.02  0.05  0.12  0.022      356
    2:1                  123  0.03  0.04  0.16  0.025      288   ← seçildi
    3:1                  123  0.02  0.04  0.16  0.022      262
    5:1                  123  0.01  0.05  0.14  0.025      238
    yalnız npmi          109  0.01  0.03  0.14  0.024      159
    yalnız ses           104  0.00  0.01  0.03  0.004      840

**Asıl kazanç sıralama değil ERİŞİM ve bunu abartmamak gerek.** Tavan 109'dan
123'e çıkıyor: 14 sanatçı yalnız ses tarafından erişilebilir durumda, çalma
listesi onları hiç göremiyor. recall@50 de 0,14'ten 0,16'ya çıkıyor. Ama
n=147'de bir sanatçı 0,7 puan demek; @5 ve @10'daki 0,01'lik farklar bir-iki
sanatçıdır ve gürültüdür. Güvenilir olan iki bulgu: **tavan farkı (14 sanatçı)
ve recall@50 farkı.**

`melez` altıncı strateji olarak eklendi. Üretilen 108 adayın **19'unda iki
sinyal de var** — en yüksek güvenli olanlar bunlar: Night Verses, Pelican,
Car Bomb, Coheed and Cambria. Bu kartlarda gerekçe ikisini birden yazıyor.

**K19'a uyum:** RRF işlevi `python/discover/adaylar.py` içinde yaşıyor,
`degerlendirme` onu oradan alıyor. Tersi olsaydı değerlendirme kendi
uydurduğu bir sıralamayı ölçerdi.

## 2026-09-02 (3) — Beş stratejinin tam tablosu; üçü ölçüldü ve çöktü

Kalan üç strateji (`kredi_sicramasi`, `sahne_komsulugu`, `bilincli_uzaklik`)
ağ istiyordu; `cevrimdisi=True` istemcilerle ÖNBELLEKTEN ölçüldü. Kütüphanenin
bellekteki kopyası alınıp gizlenen sanatçının albümleri siliniyor; `albums`
üzerindeki ON DELETE CASCADE `credits`/`memberships`/`stem_profili`'yi de
temizliyor. Böylece ölçülen şey üretim kodunun kendisi (K19), kopyası değil.

**Ölçümün geçerliliği önce doğrulandı:** 147 gizlemenin hiçbirinde önbellek
yetersizliği olmadı (ölçülemedi = 0/147, her üç strateji için). Yani aşağıdaki
sıfırlar "veri yoktu" değil, "strateji bulamadı" demek.

    erişim                  tavan  havuz     @10    @50     MRR  yüzdelik
    melez                 123/147   2637   0.04   0.16   0.025     0.105
    liste_birlikteligi    109/147   1724   0.03   0.14   0.024     0.092
    ses_benzerligi        104/147   2416   0.01   0.03   0.004     0.347
    kredi_sicramasi         1/147     81   0.01   0.01   0.001     0.062
    sahne_komsulugu         0/147     61   0.00   0.00   0.000         —
    bilincli_uzaklik        0/147     55   0.00   0.00   0.000         —

**Sorun sıralama değil ERİŞİM.** Üç strateji 147 gizlemenin TAMAMINDA topu
topu 55–81 tekil sanatçı görüyor. Havuzda 10.396 sanatçı var; bu üçü
%1'inden azına bakıyor. Eksen başına ~10 aday üretiyorlar ve o kadar.

**Dar AYARLANDIKLARI için mi başarısızlar?** Ölçüldü: hayır.
Geniş ayarla (tohum 6→20, komşu 15→60) `sahne_komsulugu` 61→58,
`bilincli_uzaklik` 55→29 sanatçı; ikisi de yine 0/147. Genişletmek yardım
etmiyor, hatta daraltıyor — çünkü ek tohumların komşuları da aynı dar
kalabalığa çıkıyor. (`kredi_sicramasi`'nın geniş ölçümü SONUÇSUZ: önbellek dar
ayarla kurulmuştu, geniş tohum kümesi için Discogs verisi yok. Dar ölçümü
zaten yeterince açık.)

**Yorumun sınırı yazılmalı.** Bu ölçüt "sahip olduğun sanatçıyı bulabiliyor
mu" diye soruyor. `kredi_sicramasi` "kütüphanendeki müzisyenin BAŞKA işi"ni
buluyor — oturum davulcusunun öbür grubu gibi — ve o şeyler tanım gereği
sahip olmadığın şeyler. Yani vekil bu stratejiyi bir miktar haksız
cezalandırıyor. Ama 81 sanatçılık evren, vekilden bağımsız bir gerçek.

Geri bildirim de aynı yöne işaret ediyordu: `sahne_komsulugu`'nun 11 kararının
9'u "zaten biliyorum". Tutarlı — sahip olduğuna sıkı bağlı şeyler getiriyor,
onlar da bildiğin şeyler.

**Karar kullanıcıya bırakıldı** (emekliye ayırma / niş bölüm / olduğu gibi
bırakma), çünkü bu üçü projenin özgün fikriydi ve ölçüt onları tam olarak
ölçmüyor.

**Karar: niş bölüme alındı** (kullanıcı, 2026-09-02). Üçü de silinmedi ama
ana akıştan çıktı:

- «Nereden» menüsü iki gruba ayrıldı: *ölçüldü ve tuttu* (melez, çalma
  listesi, ses) ve *niş — kadro grafiği*.
- «Ana yolların hepsi» seçiliyken niş stratejiler LİSTEYE GİRMİYOR; açıkça
  seçilmeleri gerekiyor. Regresyon testiyle korunuyor.
- Niş bir yol seçilince sayfada ne olduğu yazılı: kaç sanatçı görebildiği,
  havuzda kaç sanatçı olduğu ve ölçütün bu yolu neden tam ölçmediği.

Silinmemelerinin sebebi ölçütün sınırı: «müzisyen paylaşan başka kayıt» tanım
gereği sahip OLMADIĞIN bir şey, yani gizleme sınaması onu göremiyor. Sayı
yanlış değil ama bu üç yolun işini ölçmüyor; bunu bilerek karar verildi.

Sözlüğe dört terim eklendi (32 oldu): gizleme sınaması, tavan, yüzdelik,
melez sıralama. Her birinde ölçülmüş çıpalar ve uyarı satırı var.

## 2026-09-02 (4) — Kanıt gücü; ve ölçütün hedefle çeliştiği yer

**Etiketleme dört stem'e dengelendi** (kullanıcı: "hep davulla etiketleme
yapmışsın"). Haklıydı: 20 etiketin 9'u davuldu, bas TEK etiketle geçiyordu ve
gitar/klavye tarafı hiç adlandırılmamıştı — «distorsiyonlu», «parlak», «kesik»
hangi enstrümandan geldiğini söylemiyordu. Yeni küme 40 etiket: davul 14
(4'ü parça düzeyi), gitar/klavye 10, vokal 9, bas 7.

Kullanılmayan ölçümler açıldı: `enerji_payi` (stem'in mikste kapladığı yer —
hiç kullanılmamıştı), `vibrato_hizi`, `trampet_payi`, perdeli stem'lerde
`nota_vurus`. Sonuçlar müzikal olarak tutuyor: Meshuggah'ta *serbest ritim*,
Eminem'de *programlanmış ritim* + *hızlı söyleyiş*, Rush'ta *kuru davul*.

**İki hata çıktı, ikisi de düzeltildi:**
1. Öznitelik denetimi ÇÖKÜYORDU: sonradan göçle eklenen `tur` sütununu
   `SELECT *` öznitelik sanıyordu. Sayısal sütun süzgeci eklendi; kara liste
   tek başına yetmezdi, bir sonraki metin sütunu yine sızardı.
2. «yoğun davul» etiketi `nota_vurus`'a dayanıyordu ama o ölçüt davul için
   denetimde ELENMİŞTİ (artık payı 0,296). Kullanıcıya bağımsız bilgi gibi
   gösterilen şey başka etiketlerin kopyasıydı. Artık her etiketin denetimden
   geçmiş bir (sütun, stem) çiftine dayandığı testle korunuyor.

**KANIT GÜCÜ — sayısal olarak projenin en büyük kazancı.** npmi'nin tavanı +1
ve iki liste onu doldurmaya yetiyordu; «2 listede birlikte» ile «16 listede
birlikte» aynı skoru alabiliyordu. `n/(n+k)` çarpanı eklendi.

**Ve burada projenin merkezindeki gerilim ortaya çıktı.** İlk süpürmede k=4
seçilmişti çünkü recall en yüksek orada. Sonra ikinci bir ölçüt eklendi:
önerilen sanatçıların medyan çalma listesi görünürlüğü — popülerlik vekili.

    k   @10   @50    MRR   görünürlük
    0  0.03  0.14  0.024        2
    1  0.13  0.27  0.063        7   ← seçilen
    2  0.18  0.27  0.093       16
    4  0.18  0.27  0.099       20
    8  0.17  0.27  0.095       22
                                     (kütüphanenin kendi medyanı: 6)

k büyüdükçe erişim ölçütü DOYUYOR (recall@50 zaten 0,27) ama popülerlik
tırmanmaya devam ediyor. k=4, fazladan 0,05 recall@10 için popülerliği üçe
katlıyor — ve ölçüldü, öneriler kullanıcının kendi kütüphanesinden popüler
hâle gelmişti (medyan 8–9'a karşı 6).

Sebep yapısal: gizleme sınaması "SAHİP OLDUĞUN sanatçıyı bulabildin mi" diye
soruyor, sahip olunanlar popülere kayıyor, dolayısıyla **ölçütü kovalamak
kullanıcının asıl istediğinden ("hiç duymadığım sanatçı") uzaklaştırıyor.**
Tek sayıya bakılsaydı k=4 seçilir ve yanlış olurdu. k=1'e düzeltildi;
öneriler şimdi medyan 5 listede görünüyor, kütüphanenin 6'sının altında.

Ders K19'a ek olarak: **tek ölçüt yeterli değil.** Erişim ölçütünün yanında
her zaman belirsizlik ölçütü raporlanacak.

## 2026-09-06 — Kalan işler kapandı: MBID, takma adlar, geri bildirim döngüsü

### MBID eşleştirme: 249 → 277 (302 albümün %92'si)

Altı sistematik kusur bulundu, hepsi ölçülerek:

1. **Apostrof arama sorgusunu bozuyordu.** `normalize_esleme` apostrofu boşluğa
   çeviriyor («we're» → «we re») ve MusicBrainz bölünmüş sözcükle bulamıyordu.
   Aramaya özel `arama_basligi()` yazıldı — baskı süsünü atıyor, apostrofu
   koruyor. Kimlik normalizasyonu dondurulmuş olduğu için ona dokunulmadı.
2. **Kadro adı ≠ lider adı.** «Jeff Beck — Truth» MusicBrainz'de skor 100 ve
   başlık birebir tutarken şüpheli kalıyordu, çünkü kayıt «Jeff Beck Group»
   adına. `_kadro_uyumu()`: kısa adın her sözcüğü uzun adda geçiyorsa ve kısa
   ad en az iki sözcükse kabul. «Beck» ⊄ «Jeff Beck» — tek sözcük asla.
3. **Yeniden basım yılı.** «Pantera — Cowboys From Hell» etikette 2010,
   MusicBrainz'de 1990 ve 1994. Etiket yılı adayların hepsinden sonraysa
   etiket bir reissue'dur; en eski yayın grubu doğru olandır.
4. **Alt başlık.** «Periphery II» ↔ «Periphery II: This Time It's Personal».
   Önek kuralı dar: kalan kısım ayraçla başlamalı, yoksa «Truth» ile
   «Truthful» eşleşirdi.
5. **Sanatçı süzgeci sorguyu öldürüyordu.** `artist:"THE SQUARE / T-SQUARE"`
   sıfır sonuç (eğik çizgi Lucene'i bozuyor); `artist:"Yngwie Malmsteen"` de
   sıfır (MB'de «Yngwie J. Malmsteen's Rising Force»). Çözüm tırnaksız TEK
   SÖZCÜK: `artist:malmsteen`. Yalnız başlıkla aramak yetmiyor — «Odyssey»
   gibi yaygın başlıklarda doğru sanatçı ilk ona girmiyor (ölçüldü).
6. **Tipografik tire.** MusicBrainz «T‐SQUARE» (U+2010) yazıyor. Ayrıca
   `normalize_esleme` «the»yi attığı için iki ad AYNI sözcük kümesine iniyordu
   ve «eşitse reddet» koruyucusu onları reddediyordu — eşitlik artık kabul.

Kalan 24 albümün çoğu yapısal olarak eşleşemez: tek-parçalık kırpıntılar
(Pink Floyd «Wish You Were Here» 1 parça), backing-track yayıncıları
(Jam Track Central), MusicBrainz'de olmayan derlemeler. Otomatiği zorlamak
YANLIŞ eşleşme üretir ve o, eşleşmemekten kötüdür.

### Takma ad birleştirme: 65 → 106 eşleme

Casiopea kadrosu tek profilde toplandı: 野呂一生 → Issei Noro, 櫻井哲夫 →
Tetsuo Sakurai, 向谷実 → Minoru Mukaiya, 東原力哉 → Rikiya Higashihara,
伊藤八十八 → Yasohachi Itoh, フレネシ → Frenesi.

`_latin_mi` düzeltildi: noktalama Latin sayılmıyordu, dolayısıyla «Brendan
O'Brien» (U+2019) ve «Jean‐Marie Horvat» (U+2010) Latin dışı görünüyordu —
57 addan 49'u yanlış sınıflanmıştı. Etkisi kozmetikti (kanonik ad seçimi) ama
yanlıştı.

**Ölçülüp geri alınan bir kaygı:** tipografi 56 adı "bölünmüş" gösteriyordu,
ama `normalize_esleme` hepsini zaten aynı anahtara indiriyor — gerçek bir
profil bölünmesi YOK. Ölçmeden düzeltmeye kalkılsaydı var olmayan bir sorun
için kod yazılacaktı.

Dört Japonca ad hâlâ eşleşmiyor (清水興, 青柳誠, 岩見和彦, 佐々木隆) ve bu
DOĞRU davranış: Latin yazımları kütüphanede hiç geçmiyor, MusicBrainz'in
tanımadığımız bir kişiye dair iddiası veritabanına sızmamalı.

### Geri bildirim döngüsü kapandı

Kararlar şimdiye kadar yalnız kaydediliyordu; sıralamaya tek etkisi
"bildiklerimi geri at" kutusuydu. `yakinlik_etkisi()`: beğendiğine CLAP
uzayında yakın adaylar yukarı, tutmadığına yakın olanlar aşağı.

Çalma listesi sinyali BURADA KULLANILAMAZ ve sebebi yapısal:
`liste_birlikteligi` yalnız kütüphane↔aday bağı taşıyor, iki adayın birbirine
yakınlığını söylemiyor. Beğendiğin sanatçı da bir aday.

**Etki bilerek küçük: en fazla 0,5 σ.** n=2 beğendim, n=3 tutmadı — bu, etkiyi
ölçmeye yetmez. K19 "ölçülmeden üretime girmez" diyor; buradaki istisna
bilinçli ve bedeli tavanla sınırlandı: kararlar sıralamayı DEVİRMİYOR,
kaydırıyor. Ölçülebilir hâle gelince katsayı süpürülecek.

**Etki görünür.** Kart üzerinde «👍 dediğin «Issei Noro» ile aynı sesten»
yazıyor. Kullanıcı bir şeyin neden yukarı çıktığını göremezse sistemin
öğrendiğine güvenemez.

## 2026-09-15 — Çok kiracılık ve oturum katmanı

Kullanıcı isteği: "Kullanıcılar Spotify hesapları ile bağlanıp bu uygulamayı
kullanabilsin. 5 kullanıcıya izin verebiliyordun galiba." Ve ayrıca: "uygulama
tam son formuna ulaşmış gibi hissettirmiyordu, güzelce cilala."

**Spotify kısıtları yeniden doğrulandı (Şubat 2026 kuralları bugün geçerli):**
ihtiyacımız olan uçların hepsi açık — `/me`, `/me/top/artists`, `/me/top/tracks`,
`/me/albums`, `/me/tracks`, `/me/player/recently-played`, `/me/playlists`,
`/me/following`. Kapalı olanlar başkasının profili/listesi, toplu getirme ve
browse; hiçbiri bize lazım değil. Tavan beş kullanıcı, uygulama sahibinin
aktif Premium'u zorunlu, geliştirici başına tek Client ID.

### Şema ikiye ayrıldı — ve 262 sorgu yerinin hiçbiri değişmedi

Etki alanı önce ölçüldü: kütüphaneyi okuyan 145, paylaşımlı tabloları okuyan
117 sorgu yeri. `kullanici_id` sütunu eklemek de, sorguları elle niteleme de
yüzlerce dokunuş demekti.

Üçüncü yol SQLite'ın ad çözümlemesi: niteliksiz tablo adı önce `main`de,
bulunamazsa ATTACH edilmiş veritabanında aranıyor. Bir tablo yalnız birinde
varsa mevcut sorgular DEĞİŞMEDEN doğru yere gidiyor. Kurmadan önce ölçüldü —
okuma, yazma ve iki veritabanı arası JOIN çalışıyor.

    data/db/kullanici/<id>.sqlite   albums, clusters, memberships, temsilciler,
                                    adaylar, feedback, album_etiket, ses_kumesi,
                                    ses_kume_adi, liste_birlikteligi, plays, dosyalar
    data/db/ortak.sqlite            credits, tags, audio_features, stem_profili,
                                    davul_profili, kisi_eslesme, calma_listesi,
                                    liste_parca, kullanici, oturum

Ayrım ölçütü: kayıt ALBÜMÜ ya da KİŞİYİ tarif ediyorsa paylaşımlı (bir kez
hesaplanır, herkes yararlanır); KULLANICININ kütüphanesini ya da tercihini
tarif ediyorsa ona özel. `liste_birlikteligi` ve `album_etiket` paylaşımlı
DEĞİL — ikisi de kütüphaneye görelidir (PMI kütüphane sanatçısı × dışarıdaki
bağıdır, etiket eşikleri kütüphanenin kendi dağılımının kuyruğundan gelir).

**Üç kusur kurulum sırasında yakalandı, üçü de sessizce bozacaktı:**
1. Veritabanları arası yabancı anahtar yok sayılmıyor, PATLIYOR
   ("no such table: ortak.albums"). Paylaşımlı DDL'lerden `REFERENCES albums`
   otomatik sökülüyor. Kaybedilen CASCADE semantik olarak zaten yanlış olurdu:
   bir kullanıcının albümü silinince krediler silinmemeli, başkası ona sahip olabilir.
2. `CREATE UNIQUE INDEX` ve `CREATE INDEX ... ON tablo` sınıflandırılamıyordu;
   indeksler iki tarafa da yazılmaya çalışılıp olmayan tabloda patlıyordu.
3. `ortak_yolu` varsayılan argümanı TANIMLAMA ANINDA bağlanıyordu, dolayısıyla
   test gerçek paylaşımlı veritabanına yazdı. Artık çağrı anında okunuyor.

98.894 satır göç etti (`python -m python.goc_cokkullanici`); özgün
`kesif.sqlite` yerinde bırakıldı, geri dönüş onu kullanmaktan ibaret.

### Oturum katmanı

`python/hesap.py`: scrypt parola özeti (standart kütüphane, yeni bağımlılık
yok), sabit zamanlı karşılaştırma, `secrets` jetonu, 30 günlük çerez.

Parola ZORUNLU DEĞİL: Spotify ile bağlanan hesabın parolası olmaz
(`parola_ozeti` NULL) ve o hesaba yalnız Spotify'la girilir. `parola_tutuyor_mu`
None gördüğünde False döner — aksi hâlde boş parolayla girilebilirdi.

Giriş başarısızlığında TEK MESAJ dönüyor: "kullanıcı yok" ile "parola yanlış"
ayrımı hangi e-postaların kayıtlı olduğunu ele verir. Kullanıcı bulunamadığında
da kukla bir özet hesaplanıyor, çünkü yanıt süresi farkı aynı bilgiyi sızdırır.

**Yetki denetimi ARA KATMANDA, rota bazında değil.** Rota bazında olsaydı bir
gün biri unutulur ve o sayfa sessizce herkese açık kalırdı. Kapalı olmak
varsayılan, açık olmak istisna (`ACIK_YOLLAR`). Regresyon testi sekiz sayfanın
oturumsuz erişimde girişe yönlendiğini doğruluyor.

**Aktif kullanıcı bağlam değişkeninde.** `_baglanti()` on ayrı yerden
argümansız çağrılıyordu; imzasını değiştirmek her çağrı yerine istek nesnesi
taşımak demekti. `ContextVar` Starlette'in görev bağlamında doğru çalışıyor:
her istek kendi kopyasını görür.

Beş kullanıcı sınırı üyelik akışında da uygulanıyor — panele eklenmeyen hesap
Spotify tarafında zaten giremez; sınırı burada uygulamak anlaşılmaz bir hata
yerine anlaşılır bir mesaj vermeyi sağlıyor.

Uçtan uca doğrulandı: üyelik → çerez → korumalı sayfa → **yeni kullanıcının
kütüphanesi boş** (yalıtım kanıtı) → çıkış → erişim kapanıyor. 197 test geçiyor.
