# 4 — Dinleyicinin sesi: öneri ve keşif hakkında insanlar gerçekte ne diyor?

Tarih: 2026-10-20 · Kapsam: Spotify Community, Hacker News, Reddit (arama özetleri
üzerinden), Ekşi Sözlük, Bandcamp/Last.fm/Pandora/RYM üzerine yazılar, müzik
gazeteciliği (NPR, TechCrunch, TechRadar), HCI/RecSys literatürü.

---

## 0. Yöntem ve sınırlar (önce bunu oku)

- **38 web araması** yapıldı (istenen asgari 30). Sonra oturumun paylaşılan arama
  bütçesi (200 çağrı, tüm ajanlar ortak) doldu; üç arama daha (canlı sürüm
  şikâyetleri, albüm odaklı dinleyici, YouTube Music) **yapılamadı**.
- **WebFetch hiçbir alan adında çalışmadı** (`getaddrinfo ENOTFOUND`: Spotify
  Community, Reddit, HN, Wikipedia, Substack…). Bu yüzden hiçbir sayfa tam
  okunamadı. **Tüm bulgular arama motorunun döndürdüğü özet ve alıntı
  parçalarına dayanıyor.** Alıntılar kısa tutuldu, kullanıcı adı yok.
- Reddit doğrudan okunamadı; Reddit içeriği yalnız arama sonuçlarında çıkan
  Redlib yansımaları ve özetler üzerinden geldi. r/drums, r/jazzfusion,
  r/Guitar ve r/turkey konu başlıkları aramada **yüzeye çıkmadı**; bu nişler
  için kanıt dergi/plakçı/Last.fm kaynaklarından.
- Kanıt işaretleri:
  - **[K]** — bu oturumda bir kaynakla görüldü (URL'si verilmiş).
  - **[G]** — genel bilgi, bu oturumda doğrulanmadı; kararda tek başına
    kullanılmamalı.
  - **[Ç]** — benim çıkarımım; ölçülerek doğrulanmalı (K19).
- Anekdot uyarısı: forum şikâyetleri **neden** göstermez, yalnız **neyin
  hissedildiğini** gösterir. Aşağıdaki sezgiler bu yüzden "kural" değil,
  **sınanacak hipotez** biçiminde yazıldı (her birinin yanında nasıl ölçüleceği).

---

## 1. Dinleyicilerin şikâyet ettiği başarısızlık kipleri

Sıra, şikâyetin sıklığına ve şiddetine göre (benim değerlendirmem).

### 1.1 "Zaten bildiğimi önerme" — yankı odası [K, en sık]

En çok tekrarlanan şikâyet. Keşif listeleri takip edilen ya da beğenilmiş
sanatçılarla doluyor.

- Bir kullanıcı Discover Weekly'nin 30 parçasından 11'inin **zaten beğendiği
  gruplardan** olduğunu yazıyor; bir başkası "yarısı takip ettiğim
  müzisyenlerden" diyor.
  https://community.spotify.com/t5/Content-Questions/More-Discover-Weekly-Problems/td-p/4653902 ·
  https://community.spotify.com/t5/Content-Questions/Why-does-my-radio-on-Spotify-play-mostly-the-same-songs-I-used/td-p/5248665
- Song Radio için ölçülmüş bir şikâyet: kabaca **%50'si zaten listede olan,
  %40'ı radyoda daha önce çıkmış** parçalar; "otomatik listelerin hepsi bana
  yalnız bildiğim müziği gösteren bir yankı odası kurdu."
  https://community.spotify.com/t5/Live-Ideas/Spotify-amp-quot-Song-Radio-quot-is-Essentially-Just-an-Echo/idc-p/5182396/highlight/true
- Bir lise gazetesi köşe yazısı: şarkı radyoları "neredeyse tamamen beğendiğim
  şarkılardan" oluşmaya başlamış, "yeni müzik bulma amacını yok ediyor."
  https://hhsepitaph.com/?p=13128
- Spotify moderatörünün açıklaması önemli bir mekanizma veriyor: Discover
  Weekly "benzer zevkteki kullanıcılar arasında popüler olanı" öneriyor ve
  **~30 sn'den önce atlanan parça olumsuz sinyal** sayılıyor. Yani kullanıcı
  "bunu zaten biliyorum" diye atladığında sistem bunu "sevmiyorum" diye
  okuyor — iki ayrı kararı tek sinyale çökertmek.
  https://community.spotify.com/t5/Accounts/Discover-weekly-playing-items-i-know/td-p/4593993

**Proje için önemi:** K21'deki üç ayrı karar (beğendim / tutmadı / zaten
biliyorum) tam olarak bu çöküşü önlüyor; dinleyicilerin en sık dile getirdiği
eksik bu. "Zaten biliyorum"un zevk isabeti paydasına girmemesi doğru karar.

### 1.2 Aynı sanatçının tekrar tekrar gelmesi; gizlenen sanatçının geri dönmesi [K, çok sık]

- "Aynı gruptan 4 şarkı", "20 parçada yalnız 12 farklı sanatçı", "gizlediğim
  sanatçıdan dört haftadır her hafta en az 3 şarkı."
  https://community.spotify.com/t5/Live-Ideas/Improve-discover-weekly-Less-repeat-artists/idi-p/7516193
- "Gizlenen şarkı ve sanatçılar büyük olasılıkla gelecek hafta yine çıkıyor";
  "Bu sanatçıyı çalma" seçeneğine rağmen istenmeyen türler gelmeye devam ediyor.
  https://community.spotify.com/t5/Desktop-Windows/Does-Discover-Weekly-quot-Don-t-Recommend-quot-button-also-not/td-p/2759293
- Aynı parça hem Discover Weekly'de hem Release Radar'da.
  https://community.spotify.com/t5/Music-Discussion/Why-Discovery-weekly-and-released-radar-have-same-song/td-p/7181995

**Ders:** Olumsuz kararın *kalıcı ve görünür* olmaması güveni en hızlı
öldüren şey. Kullanıcı "dediğimi dinlemiyor" hissine kapılıyor.

### 1.3 Olumsuz geri bildirim işe yaramıyor / ayar düğmesi yok [K, sık]

- Telugu dinleyen bir kullanıcı başka dildeki her parçayı beğenmediğini
  işaretlemiş, **davranış değişmemiş.**
  https://community.spotify.com/t5/iOS-iPhone-iPad/Spotify-Does-Not-Consider-Language-Preference-For/td-p/4737193
- "Tercihlerimizi ince ayarlayabileceğimiz, bir önerinin iyi ya da kötü
  olduğunu söyleyebileceğimiz yollar lazım."
  https://community.spotify.com/t5/Your-Library/Issues-with-Spotify-s-recommendation-algorithms/td-p/5646049
- Spotify'ın 2025'te "Tat profilinden hariç tut" özelliğini **parça düzeyine**
  indirmesi (önce yalnız çalma listesi düzeyindeydi) bu şikâyete verilmiş geç
  bir cevap. TechRadar'ın başlığı durumu özetliyor: "Peppa Pig'i heavy metal
  listenden uzak tutan özellik."
  https://newsroom.spotify.com/2025-10-01/exclude-tracks-taste-profile/ ·
  https://www.techradar.com/news/spotifys-new-feature-keeps-peppa-pig-away-from-your-heavy-metal-playlist
- Türkçe tarafta: Ekşi Sözlük'te "müzik zevki profilinden hariç tut" ipucu
  paylaşılıyor; Spotify Haziran 2025'te Haftalık Keşif'e (Premium'a) tür
  düğmeleri ekledi — haber, kullanıcıların "aynı şarkıların tekrarından ve tür
  sınıflandırma hatalarından" şikâyetini gerekçe olarak anıyor.
  https://eksisozluk.com/entry/150222266 ·
  https://webrazzi.com/2025/06/30/spotify-haftalik-kesif-calma-listelerinin-kisisellestirilmesine-izin-verecek/ ·
  https://www.teknoblog.com/spotify-haftalik-kesif-tur-filtre-guncellemesi/
- Bir bülten yazısı Release Radar'a gelen oturum kontrollerini "algoritmanın tek
  başına yetmediğinin örtük itirafı" diye yorumluyor.
  https://bobbylive505.substack.com/p/is-spotify-killing-music-the-algorithms

**Ders:** Sektör, kullanıcıya "hangi tarafını besleyeyim?" diye sormaya
(eksen seçimi) ancak 2025'te ve kısmen geldi. Projenin K1'deki "sistem karar
vermez, kullanıcıya sorar" ilkesi, dinleyicinin dile getirdiği ihtiyaçla
birebir örtüşüyor.

### 1.4 Alt tür çözünürlüğünün çökmesi: "hepsi aynı 40–50 şarkı" [K, sık]

- HN: Texas Country, Americana ve Red Dirt üç ayrı alt tür ama "Spotify'ın
  gözünde hepsi aynı 40–50 şarkı." Aynı yorumcu çeşitlilik için Pandora'yı
  daha iyi buluyor.
  https://news.ycombinator.com/item?id=15447706
- r/Djent: Spotify'ın djent listeleri "tekrarlı ya da fazla metal/deathcore-vari";
  kullanıcı **ölçü değişimleri ve disonan armoniler** olan daha progresif
  gruplar istiyor (yani benzerliği tür adıyla değil, yapısal/icra
  özellikleriyle tarif ediyor).
  https://lr.eu.psf.lt/r/Djent/hot (Redlib yansıması, geçici sayfa)
- Spotify Community'de türleri Discover Weekly'den dışlama talebi.
  https://community.spotify.com/t5/Live-Ideas/Exclude-genres-from-discover-weekly-and-allow-forced-algorithm/idi-p/7494104

### 1.5 Çoğunluk ekseninin azınlık eksenini yutması [K]

- HN: "Çok ambient dinliyorum ve önerilerimin %80'i o oluyor; oysa bir sürü
  öfkeli punk da dinliyorum." Başka biri kısa bir punk döneminden sonra
  Discover Weekly'nin ona punk itmeye devam ettiğini söylüyor.
  https://news.ycombinator.com/item?id=15447706
- Bir Substack yazarı Discover Weekly'nin zevkini tek tarza doğru yönlendirdiğini,
  "rock, elektro gitar, punk zamanla süzüldü" diye anlatıyor.
  https://mildatheart.substack.com/p/stop-finding-music-through-spotify
- HN'de iyi sonuç alanların ortak noktası: Spotify'ı **tek tür** için
  kullanmak ya da her tür için **ayrı çalma listesi** tutmak — yani elle eksen
  ayırmak.
  https://news.ycombinator.com/item?id=15447706

**Ders:** Kullanıcının profili (prog metal + füzyon + Türk rock + hip-hop) tam
bu tuzağın hedefi. Eksen başına ayrı deste/pay şart; çoğunluk ekseninin
oranı kütüphanedeki ağırlığını aşmamalı.

### 1.6 Dil ve ülke sızıntısı [K, sık ve öfkeli]

- HN: "Hollandalı değilim, Hollandaca bilmiyorum, hiç Hollandaca müzik
  dinlemedim; Discover Weekly'ye her hafta 2–4 Hollandaca şarkı koyuyor."
  https://news.ycombinator.com/item?id=15447706
- Telugu seçen kullanıcıya önerilerin ~%50'si Tamil/Malayalam/Hintçe/İngilizce;
  tek bir İbranice parça bir listenin tüm önerilerini İbraniceye çevirebiliyor.
  https://community.spotify.com/t5/Content-Questions/Wrong-language-suggestions/td-p/5394595 ·
  https://community.spotify.com/t5/iOS-iPhone-iPad/Spotify-Does-Not-Consider-Language-Preference-For/td-p/4737193
- **Türkiye'ye özgü:** Spotify personeli bir kullanıcıya "hesabın ülkesi
  Türkiye ise bu öneriler bundan" diye cevap vermiş — yani **hesap bölgesi
  bir öneri girdisi.**
  https://community.spotify.com/t5/Content-Questions/Strange-section-in-main-feed/m-p/5227359/highlight/true
- "Fans also like" şikâyetinde 1970'lerin bir **İngiliz** psikedelik grubu
  **Türk** gibi gösteriliyor; Hong Kong/Yeni Zelandalı bir şarkıcı İsveçli.
  Yorumcuların tahmini: ilişki dinleyici örtüşmesinden geliyor, tür ya da
  ülkeden değil.
  https://community.spotify.com/t5/Content-Questions/quot-Fans-Also-Like-quot-section-is-completely-wrong/m-p/6629310/highlight/true ·
  https://community.spotify.com/t5/Content-Questions/quot-Related-artists-quot-how-do-Spotify-decide-what-artists-are/td-p/1185597/page/3
- Ürün incelemesi: Smart Shuffle yumuşak pop oturumuna yüksek enerjili Pencap
  parçası sokuyor; ruh hâli filtresi dili hesaba katmıyor.
  https://theanxiouslab.substack.com/p/spotify-product-teardown

**Ders:** Dil, stil benzerliğinin **sahte vekili** olarak sızıyor; tersine de
çalışıyor (dil yüzünden ilgisiz stil). CLAUDE.md'deki "Sezen Aksu vakası"
bunun projedeki karşılığı. Dinleyici dili **ayrı ve açık** bir eksen olarak
istiyor, gizli bir benzerlik bileşeni olarak değil.

### 1.7 Bağlam / ruh hâli / etkinlik sızıntısı [K]

- HN tavsiyesi: yağmur sesi listesini ayrı tut, yoksa önerilere sızar.
  https://news.ycombinator.com/item?id=15447706
- Liz Pelly'nin *Mood Machine*'i: Spotify ruh hâli ve pasif dinlemeyi keşfin
  önüne koydu; ruh hâli listelerine (uyku, ders) düşük telifli "Perfect Fit
  Content" yerleştirildiği iddiası (Spotify reddediyor).
  https://recordstore.substack.com/p/interview-liz-pelly ·
  https://www.aristake.com/liz-pelly/
- Release Radar/Discover Weekly'ye "Songs for Feeling Nostalgic", "Best
  Roadtrip Bangers" gibi bağlam derlemelerinin dolması (bkz. 1.8).

**Ders:** K16 zaten "çalma listesi sinyali bağlam da taşır" diyor. Dinleyici
şikâyetleri bunu doğruluyor ve bir adım öteye götürüyor: **editoryal/ruh hâli
listeleri stil eksenine karışmamalı**; ayrı bir "dinleyici tipi" bilgisi olarak
kalmalı.

### 1.8 Derlemeler, yeniden paketler, cover'lar [K]

- Eylül 2025: Release Radar'a derleme albümler "yeni çıkış" diye girmiş — eski
  şarkılar yeni kapakla ("Sounds of the 90s" içinden "Cornflake Girl" gibi).
  Bir kullanıcı ucuz dinlenme için şarkıları derlemelere yeniden yükleyen bir
  şirketi suçluyor (doğrulanmamış iddia). Single'ları tek tek yayımlayan
  EP'ler de akışı dolduruyor: "single'ı bir kez, albümü bir kez göster."
  https://community.spotify.com/t5/Content-Questions/Release-Radar-showing-old-songs-due-to-compilations/m-p/7138150/highlight/true ·
  https://community.spotify.com/t5/Discovery-Promo/Why-is-Spotify-Putting-Songs-From-the-90s-in-Release-Radar/td-p/7138331
- Ünlü şarkıların cover'larının tekrar tekrar önerilmesi.
  https://community.spotify.com/t5/Live-Ideas/Improve-discover-weekly-Less-repeat-artists/idi-p/7516193

**Projede:** `python/discover/adaylar.py` derleme/canlı/demo/soundtrack'i zaten
süzüyor (`YOK_SAYILAN_TURLER`, `_DERLEME_IZLERI`). Ama bkz. 4.3 ve 4.4 —
bu süzgecin **iki niş için meşru istisnası** var.

### 1.9 Ad çakışması ve yanlış eşleme [K]

- Bir heavy metal grubunun kataloğuna aynı adlı tekno sanatçısının albümleri
  karışmış; Toronto'lu caz-füzyon grubu Vektor'un albümü thrash grubu Vektor'un
  sayfasında.
  https://community.spotify.com/t5/Your-Library/Release-radar-has-content-from-wrong-artists-with-the-same-name/m-p/5152657/highlight/true

**Projede:** MBID tabanlı kimlik ve K14 ("iki taraf da bizde varsa birleştir")
bunun doğru cevabı. Kartta yanlış sanatçı göstermek tek seferde güven kaybettirir.

### 1.10 Popülerlik yanlılığı ve "ana akım olmayan dinleyiciye en kötü öneri" [K, araştırma]

- Ana akım dışı dinleyiciler en zayıf önerileri alıyor (Last.fm verisiyle
  yeniden üretim çalışması).
  https://graz.elsevierpure.com/de/publications/the-unfairness-of-popularity-bias-in-music-recommendation-a-repro ·
  https://www.newswise.com/articles/algorithm-based-music-recommendations-low-accuracy-for-lovers-of-non-mainstream-music
- En isabetli model en çok popülerlik yanlılığı olan model çıkıyor (isabet ↔
  yanlılık ödünleşimi).
  https://ar5iv.arxiv.org/html/2208.09517
- MIDiA araştırmasından aktarılan cümle: "kullanıcılar algoritmaya ne kadar
  bağımlıysa o kadar az müzik duyuyor."
  https://tildes.net/~music/1r5u/the_algorithm_failed_music
- Karşı arzu: r/progmetal'da "100'den az aylık dinleyicisi olan favori
  gruplarınız" başlığı — niş dinleyici **bilinmezliği** bir değer olarak arıyor.
  https://www.reddit.com/r/progmetal/comments/q045g8/

**Projede:** PMI, ListenBrainz sönümlemesi ve "Coldplay metal kümesinde"
ölçümü bu sorunun zaten altı kez ölçüldüğünü gösteriyor. Dinleyici sesi bunu
doğruluyor; yeni bir şey eklemiyor, **raporlamayı** öneriyor (bkz. sezgi 10).

### 1.11 Bağlamsızlık ve uzun parçaların cezalandırılması [K]

- Kyle Chayka (*Filterworld*): sevdiği Coltrane kaydını Spotify üzerinden asla
  sevemezdi, çünkü parça o kadar uzun ki algoritma büyük olasılıkla önermezdi;
  üstelik uygulamada bir radyo DJ'inin verdiği bağlam yok. (Eleştirmenler
  kitabın geçmişi romantize ettiğini de not ediyor.)
  https://www.npr.org/2024/01/16/1225002436/book-review-kyle-chayka-filterworld ·
  https://reason.com/2024/01/23/filterworld-is-a-confused-critique-of-algorithms/

**Ders [Ç]:** Prog'da 20 dakikalık epikler, füzyonda uzun doğaçlamalar normal.
30 sn önizleme ve "en popüler parça" seçimi (bkz. `python/medya.py:albumden`
"en popüler parçası") bu türlerde albümün **temsilcisi olmayan** kısa single'ı
ya da radyo kurgusunu getirebilir.

### 1.12 Kara kutu ve kredisizlik [K]

- Last.fm'i öven bir yazı: Last.fm önerinin nasıl çalıştığını gösteriyor
  ("Arctic Monkeys dinleyenler The Strokes da dinliyor" anlaşılır), Spotify
  kara kutu.
  https://www.bespacific.com/?p=114515
- Spotify'da krediler var ama "müzisyenler için bölüm yok" (moderatör);
  kullanıcılar session müzisyenlerinin kredilendirilmesini istiyor. 2025'te
  sızan "SongDNA" katkıcıları (vokalist, mühendis, prodüktör…) gezilebilir
  yapacaktı; sonra referanslar kaldırıldı. Tidal'ın kredileri tıklanabilir ve
  sıralanabilir.
  https://community.spotify.com/t5/Implemented-Ideas/Displaying-album-credits/idc-p/4096191/highlight/true ·
  https://www.digitalmusicnews.com/2025/10/16/jane-wong-spotify-songdna-discovery/ ·
  https://www.engadget.com/2020-02-12-spotify-songwriter-pages-beta.html

### 1.13 Keşif *aracının* kaybı: Every Noise at Once yası [K]

- Spotify, Aralık 2023 işten çıkarmalarında Glenn McDonald'ı çıkardı; ~1 milyon
  sanatçıyı 6.291 türe ayıran harita güncellenemez oldu. Tepki sert:
  "Spotify'da yeni sanatçı bulmak zorlaştı… bıktım."
  https://techcrunch.com/2024/02/12/every-noise-shut-down-spotify-layoffs ·
  https://www.techradar.com/audio/spotify/finding-new-artists-on-spotify-just-got-harder-after-layoffs-put-an-end-to-useful-music-encyclopedia-and-im-tired-of-it ·
  https://www.headphonesty.com/2024/02/spotify-layoff-kills-top-music-discovery-tool/

**Ders:** Meraklı dinleyici yalnız *akış* değil, **gezilebilir bir harita**
istiyor; kendi elleriyle yürüyebileceği bir uzay. HN'de de Every Noise en çok
anılan araç.

---

## 2. Bir öneriyi meraklı dinleyici için İYİ ve GÜVENİLİR yapan ne?

### 2.1 Şeffaflık güveni artırır — ama "yüksek bilişsel ihtiyaçlı" kullanıcıda dikkat [K, araştırma]

- Sinha & Swearingen (beş müzik öneri sistemi): kullanıcılar şeffaf
  algıladıkları önerileri daha çok seviyor ve onlara daha çok güveniyor.
  https://bebop.berkeley.edu/papers/MusicCHI_RSFinal.pdf
- Millecamp vd. (IUI 2019): açıklamalar **düşük** "bilişsel ihtiyaç" (need
  for cognition) sahibi kullanıcının güvenini artırıyor; **yüksek** bilişsel
  ihtiyaçlı kullanıcıda güveni **düşürebiliyor.** Rasyonel düşünen kullanıcılar
  öneriyi **ayarlamaya yarayan, denetlenebilir (scrutable)** açıklama istiyor.
  https://www.cs.ubc.ca/~conati/522/532b-2019/papers/MillecampIUI2019.pdf ·
  https://lirias.kuleuven.be/retrieve/525282

**Proje için en önemli bulgulardan biri [Ç]:** Kullanıcı istatistik yüksek
lisans öğrencisi, ayrıntı seven, gerekçe bekleyen biri — tipik yüksek bilişsel
ihtiyaç profili. Bu kişide süs açıklama ("bunu seveceğine eminiz") **güveni
düşürür.** İşe yarayan: sayı + kaynak + kanıtın gücü + itiraz edilebilirlik
("bu bağ yalnız 3 listeye dayanıyor"). `python/gerekce.py`'deki "Zayıf kanıt:"
cümlesi tam bu literatürün önerdiği şey.

### 2.2 Jargon açıklama işe yaramaz; çalınabilir kanıt işe yarar [K]

- 2006'dan bir Pandora deneyimi: "bu parça neden çaldı?" sorusuna "speed metal
  üslupları, deneysel sesler, **hafif ritmik senkop**, değişken tempo ve ölçü"
  cevabı. Yazar SSS'yi okuduktan sonra bile terimleri anlamadığını söylüyor.
  https://www.johnjosephadams.com/2006/01/04/pandora-radio/
- Last.fm'in "X'i dinleyenler Y'yi de dinliyor" cümlesi ise herkesçe
  anlaşılıyor. https://www.bespacific.com/?p=114515

**Ders:** Öznitelik adı (ızgara entropisi, düzlük) tek başına açıklama değil.
K13'ün "her uç değerin yanında klip çalınabilir" ilkesi dinleyici açısından
doğru; aynısı öneri kartındaki ses/icra eşleşmesi için de geçerli olmalı:
"şu albümünü andırıyor" + **o albümden çalınabilir bir klip** yan yana.

### 2.3 "Çünkü…" cümlesi: kalabalık özelliğe göre ister [K, araştırma]

- r/ifyoulikeblank şablonu: "[IIL] (sevdiğin şarkı) **çünkü** (önerilerde olmasını
  istediğin belirli bir özellik), [WEWIL?]". İstek, sanatçıyla değil
  **özellikle** kuruluyor.
  https://www.reddit.com/r/ifyoulikeblank/ (kurallar; Redlib yansımaları üzerinden görüldü)
- CSCW 2024 çalışması (r/ifyoulikeblank nitel analizi): insanlar oraya
  "popüler arama sistemlerini tükettikten sonra", "neyi nasıl arayacağını
  bilmediği için" ve "kalabalığın arama sisteminden çok bildiğine inandığı
  için" geliyor. Yeni bulgular: istekler eserin **yapıldığı araçlara** göre
  (ör. enstrüman, ekipman) kurulabiliyor ve **zaman kısıtı** belirtmek öneriyi
  iyileştiriyor.
  https://arxiv.org/abs/2408.06201

**Ders [Ç]:** "Araçlara göre istek" K12'nin stem/icra profilinin dinleyici
dilindeki karşılığı ("bu davulcu gibi çalan"). "Zaman kısıtı" ise dönem
eksenine işaret ediyor (70'ler Anadolu rock'ı ≠ 2000'ler Türkçe rock).

### 2.4 Kredi ve kadro: "kim çalmış" sorusu meraklının ana yolu [K]

- The Liner Notes Project: kredilerdeki her ad tıklanabilir, tıklayınca o
  kişinin diğer işleri açılıyor; örnek olarak Steve Gadd'in 648 albümde davul
  çaldığı gösteriliyor; *Kind of Blue*'nun prodüktöründen diğer albümlere
  geçiliyor.
  https://jazzfuel.com/steve-lieblich-the-liner-notes-project/
- Blog yazıları: albüm notlarını okuyup "hangi parçada kim neyi çalmış"
  bakarak az bilinen müzisyenleri keşfetmek; eski session müzisyenlerinin
  nihayet kredilendirilmesi üzerine yeni bir yazı (Ekim 2026).
  https://vinylives.wordpress.com/2023/07/17/session-players-and-sidemen/ ·
  https://www.thatericalper.com/2026/10/13/how-session-musicians-from-the-old-days-are-finally-getting-credit/
- Forum: "AllMusic, sevdiğim sanatçılardan yola çıkıp başka iyi caz bulmak
  için rehber" (caz yan müzisyen ağı). Alıntı arama özetinde aşağıdaki
  forum ipliklerinden birine aitti; hangisi olduğu sayfa açılamadığı için
  kesinleştirilemedi.
  https://www.stereonet.com/forums/topic/31606-how-do-you-discover-new-and-old-music/ ·
  https://whatsbestforum.com/threads/whats-the-best-way-to-discover-new-music.37221/ ·
  https://forums.audioholics.com/forums/threads/where-do-you-find-new-music.23887/post-451268
- Plini ve Intervals'ın turne kadroları **aynı**; birbirlerinin setlerine
  çıkıyorlar. Last.fm'in "benzer sanatçılar" listelerinde de yan yana.
  https://metalinsider.net/?p=129940 · https://www.last.fm/music/Polyphia/+similar

**Ders:** Meraklılar için benzerliğin önemli bir kısmı **sosyal/kadro ağı**
(birlikte çalanlar, turneye çıkanlar). Kredi grafiğinin projenin çekirdeği
olması dinleyici sesiyle tutarlı.

### 2.5 İnsan kürasyonu: label, Bandcamp koleksiyonları, gerçek kişilerin listeleri [K]

- HN "Nasıl müzik keşfediyorsunuz?": çoğunluk Bandcamp diyor. Yöntemler:
  **label takip etmek** (küçük label'lar dar bir tür odağına sahip), küçük bir
  sanatçıyı **destekleyenlerin koleksiyonlarına** bakmak, şehir+etiket
  filtresi, zaten çalan parçalardan yola çıkmak.
  https://news.ycombinator.com/item?id=32835559
- "Resmî Spotify listelerinden kaçının, gerçek insanların yaptığı listelere
  bakın."
  https://news.ycombinator.com/item?id=15447706
- Bandcamp rehberleri: koleksiyon gezintisi ve çoklu etiket en güçlü araçlar,
  label katalogları "insan eliyle kürate edilmiş öneri" gibi çalışıyor.
  https://www.stevelawson.net/2023/10/how-to-find-music-on-bandcamp/ ·
  https://www.chartlex.com/blog/marketing/bandcamp-discovery-algorithm-fan-finding-2026
- Last.fm'in eski kullanıcısı: asıl değer otomatik "benzer sanatçılar"da değil,
  **komşular ve arkadaşlar** ağındaydı.
  https://www.subtraction.com/2007/10/05/thats-the-la/

**Not (K9 ile gerilim):** HN'de label takibi güçlü bir yöntem olarak anılıyor.
K9 label'ı matristen çıkarmıştı ("ortak yan dağıtım anlaşması"). Dinleyici
kanıtı bunun **küçük, tür odaklı label'lar için** yanlış olabileceğini
düşündürüyor (Shrapnel, Sensory, InsideOut gibi [G]); büyük label'lar için K9
doğru. Bu, ölçülmesi gereken bir fark (bkz. sezgi 16).

### 2.6 Kombinasyonlu filtre: RYM tanımlayıcıları [K]

- Bir Lemmy kullanıcısı RYM'in özel grafik aracıyla tür + etki + tanımlayıcıyı
  birleştirip "krautrock'tan etkilenmiş enstrümantal noise rock" gibi çok dar
  sorgular kurduğunu, algoritmaların ise ona "çoğunlukla zaten bildiklerini"
  önerdiğini anlatıyor.
  https://lemmy.dbzer0.com/post/1993/12553
- Heavy Blog Is Heavy (2016): akış servisleri çok müzik veriyor ama keşfe az
  yardım ediyor; Spotify'ın "related artists"i yanlış olabiliyor; RYM ve
  AllMusic'i keşif aracı olarak öneriyor.
  https://www.heavyblogisheavy.com/2016/04/13/sailing-the-seas-of-sound-a-brief-overview-of-music-exploration-tools/

(RYM kazıması bu projede yasak — burada yalnız *dinleyicinin ne istediğinin*
kanıtı olarak anılıyor: kesişim sorgusu.)

---

## 3. Meraklılar elle nasıl keşfediyor? (yöntem envanteri)

| Yöntem | Kanıt | Projedeki karşılığı |
|---|---|---|
| Kredileri / albüm notlarını okumak, session müzisyenini izlemek | [K] Liner Notes Project, vinylives, stereonet | `kredi_sicramasi` (şu an "cesur" kaynakta) |
| Ortak kadro / turne kadrosu | [K] Plini–Intervals (metalinsider) | kredi grafiği |
| Küçük label kataloğunu izlemek | [K] HN 32835559, Bandcamp rehberleri | K9 ile çıkarıldı — yeniden ölçülebilir |
| Bandcamp: destekçinin koleksiyonuna bakmak | [K] HN 32835559 | ListenBrainz / çalma listesi birlikteliği |
| Etiket + şehir/sahne filtresi | [K] HN 32835559 | `sahne_komsulugu` |
| Gerçek kişilerin listeleri (resmî değil) | [K] HN 15447706 | Deezer çalma listeleri (PMI) |
| Tür haritasında gezinmek (Every Noise) | [K] HN, TechCrunch | yok — gezilebilir harita fırsatı |
| Tohum sanatçıdan radyo/liste (Gnod, Spotibot: "Anekdoten'den başladım") | [K] whathifi forumu | eksen + deste |
| Forum "X seviyorsan Y" iplikleri | [K] r/ifyoulikeblank, CSCW 2024 | yok (Reddit kapalı, K10) |
| Editoryal yıl sonu / yarıyıl listeleri | [K] Heavy Blog "Top 25 of 2023 so far" | yok |
| Yeni çıkış listeleri + satın almadan önce YouTube'da dinlemek | [K] stereonet/audioholics | önizleme + Listem |
| Pandora/Tidal radyosuna bir parça verip devam ettirmek | [K] HN 15447706 | ses benzerliği |
| Festival kadroları, yan projeler, grup üyelerinin solo işleri | [G] (bu oturumda doğrudan kaynak bulunamadı) | kredi grafiği (üyelik) |
| Örneklenen (sample) kaynağa geri gitmek: vaporwave/future funk → city pop | [K] Plastic Love kaynakları | yok |

Kaynaklar: https://news.ycombinator.com/item?id=32835559 ·
https://news.ycombinator.com/item?id=15447706 ·
https://forums.whathifi.com/threads/looking-for-new-music-let-gnod-and-spotibot-help-you.40504/latest ·
https://www.heavyblogisheavy.com/2023/07/25/heavy-blogs-top-25-albums-of-2023-so-far/ ·
https://forums.audioholics.com/forums/threads/where-do-you-find-new-music.23887/post-451268

Ek gözlem: Deezer anketi keşfin ~25 yaş civarında zirve yapıp sonra azaldığını
söylüyor; HN'de bunun nedeninin kısmen "zaten sevdiğini veren algoritmalar"
olduğu tartışılıyor. Kullanıcının "DAP'tan kendi kütüphanemi dinliyorum,
keşfedemiyorum" cümlesi bu kalıbın ta kendisi.
https://happymag.tv/the-age-we-stop-seeking-new-music/ ·
https://hn.nuxtjs.org/item/40147534

---

## 4. Kullanıcının nişlerine özel

### 4.1 Teknik / prog metal

- Hayranların benzerlik tarifi **yapısal ve icrasal**: tek sayılı ölçüler
  (5/4, 7/8, 11/8…), teknik çalım, sık tempo/ton/ruh hâli değişimi. Bir
  r/progmetal yorumu türün "katılaşmış tek bir sese pek elvermediğini"
  söylüyor — yani **tür etiketi** iki prog grubunun benzer olduğunu
  söylemekte zayıf.
  https://www.reddit.com/r/progmetal/comments/bdlv9q/ ·
  https://tuonelamagazine.com/the-10-most-delicious-metal-songs-with-proggy-time-signatures/ ·
  https://www.heavyblogisheavy.com/2016/02/18/beyond-the-veil-a-match-made-in-seven-or-progressive-metals-affair-with-78/
- r/Djent: algoritmik djent listeleri deathcore'a kayıyor; istenen ölçü
  değişimi ve disonans (bkz. 1.4).
- r/progmetal öneri ipliklerinde metalcore'dan gelen birine Haken, Skyharbor,
  Karnivool, BTBAM, Intronaut; djent girişi için Monuments öneriliyor —
  öneriler bir **giriş kapısı** mantığıyla veriliyor ("nereden geliyorsun?").
  https://lr.vern.cc/r/progmetal/comments/1cpvag9/new_listener_based_on_what_i_like_what_else/l3tpxjm/
- Davulcu ağı: Gavin Harrison King Crimson'da Pat Mastelotto'yla çift davul;
  Craig Blundell Steven Wilson, Steve Hackett, Frost*; dergi listeleri prog
  davulcularını **gruplar arası dolaşan kişiler** olarak anlatıyor.
  https://en.wikipedia.org/wiki/Gavin_Harrison ·
  https://www.musicradar.com/news/the-7-best-prog-drummers-in-the-world-right-now
- Spotify'ın kendi "Prog Monsters" listesi bir topluluk ipliğinde "gizli
  hazineler ve klasikler" için iyi bulunuyor — editoryal liste nişte bazen
  işe yarıyor.
  https://community.spotify.com/t5/Music-Discussion/Prog-rock-fans/m-p/4868462/highlight/true

### 4.2 Gitar virtüözleri / enstrümantal

- Last.fm benzerlik kümesi: Polyphia → Intervals, Plini, Animals as Leaders,
  Scale the Summit, Sithu Aye… Aynı "enstrümantal gitar" etiketi altında
  ama bir konser incelemesi Plini'nin AAL'ye göre "daha yumuşak, dingin"
  olduğunu vurguluyor.
  https://www.last.fm/music/Polyphia/+similar · https://showsigoto.com/?p=63812
- **Ders [Ç]:** Kalabalık/kadro sinyali bu kümeyi tek parça görüyor; ayırt
  edici olan **ses/icra karakteri** (yoğunluk, parlaklık, distorsiyon). K12'nin
  `other` stem profili tam bu ayrımın aracı. Kartta "aynı sahne, ama daha
  dingin" gibi *fark* cümlesi, yalnız benzerlik cümlesinden daha bilgilendirici.

### 4.3 Japon füzyonu ve city pop

- Casiopea'ya giriş için en çok önerilen kayıt **Mint Jams (1982) — canlı
  albüm** (plakçı blogu; satış odaklı kaynak). T-Square = Casiopea kadrosu +
  alto saksafon; Prism, Naniwa Express, Jimsaku aynı sahne. Casiopea ve
  T-Square 1989 "Super Fusion" etkinliğinde ve 2003'te birlikte çaldı —
  **ortak sahne/etkinlik** bir bağ türü.
  https://goodtasterecords.com/blogs/news/casiopea-on-vinyl-where-to-start-with-the-japanese-fusion-pioneers ·
  https://en.wikipedia.org/wiki/T-Square_(band) · https://tiffanyjohns.com/blog/lp2
- **Proje için somut çatışma:** `python/discover/adaylar.py:YOK_SAYILAN_TURLER`
  "Live" ikincil türünü atıyor; `python/medya.py` de Mint Jams'in Deezer'da
  "MINT JAMS(Live)" diye geçtiğini not etmiş. Yani füzyonun **kanonik giriş
  kaydı** aday süzgecinden düşebilir. Bootleg süzgeci gerekli (The Killers
  ölçümü), ama "canlı = öneri değil" kuralı caz/füzyonda fazla sert.
- City pop'un yeniden doğuşu **tek bir şarkı** üzerinden oldu: "Plastic Love"
  küçük bir YouTube kanalına yüklendi, öneri sistemi onu itti, tür için
  "giriş kapısı" oldu; vaporwave/future funk örneklemeleri dinleyiciyi
  özgün sanatçılara geri götürdü. Neden o yüklemenin seçildiği belirsiz.
  https://www.openculture.com/2018/10/youtubes-algorithm-turned-obscure-1980s-japanese-song-enormously-popular-hit-discover-mariya-takeuchis-plastic-love.html ·
  https://pages.vassar.edu/musicalurbanism/?p=2066 ·
  https://en.wikipedia.org/wiki/Plastic_Love ·
  https://www.koreatimes.co.kr/amp/world/20220222/city-pop-the-soundtrack-to-japans-boom-years-goes-viral
- **Ders [Ç]:** (a) "Tek şarkının taşıdığı sanatçı" riski gerçek — bir viral
  parça sanatçının tamamını temsil etmez. (b) City pop dalgası, füzyon
  dinleyicisini vokal pop'a çekebilir: Takanaka/Casiopea ile Takeuchi/Yamashita
  aynı çalma listelerinde sık durur ama biri enstrümantal icra, öteki şarkı
  yazarlığı. Çalma listesi sinyali burada **sahne/dönem** bilgisi taşıyor,
  icra benzerliği değil; ses/stem ekseni ayırmalı.
- [G] Japon kataloglarının bir kısmı uzun süre akış servislerinde yoktu ya da
  bölgeye kısıtlıydı; önizleme bulunamaması bu nişte yapısal olabilir
  (bu oturumda doğrulanmadı).

### 4.4 Türk rock / Anadolu rock

- Batılı dinleyici için keşif yolu büyük ölçüde **derleme ve yeniden baskı
  label'ları**: *Turkish Freakout!* (DJ Remould'un 45'liklerden iğne-düşürme
  kayıtları; 1. cilt daha rock, 2. cilt kadın vokal ağırlıklı), Finders Keepers
  (Gökçen Kaynatan'ın erken elektronik işleri, Ersen). NPR, türün doğuşunu
  bir gazetenin şarkıların Türkçe ya da halk ezgisi uyarlaması olmasını
  şart koşan yarışmasına bağlıyor ([G]: Hürriyet'in Altın Mikrofon'u).
  Bir kullanıcı yorumu derlemenin Selda, Moğollar, Edip Akbayram'ı atladığını,
  Erkin Koray, Barış Manço ve Cem Karaca'yı içerdiğini söylüyor.
  https://www.npr.org/2011/10/18/140432961/turkish-freakout-a-musical-turkish-delight ·
  https://forcedexposure.com/Catalog/FKR.091LP.html ·
  https://www.desertcart.lk/products/7575811-turkish-freakout
- **Yapısal sorun [Ç]:** Dönemin ana biçimi **45'lik single**. Albüm odaklı bir
  motor (Discogs `single` ve `comp` biçimlerini atan `_ISTENMEYEN_BICIM`)
  bu sanatçıların erken dönemini göremeyebilir; onların "albümü" çoğu zaman
  sonradan yapılmış derlemedir. Çok sanatçılı **sahne derlemeleri** ise öneri
  öğesi olmasa da güçlü bir **sahne kanıtıdır** (bir küratörün aynı plağa
  koyması ≈ insan eliyle verilmiş birliktelik).
- Ülke/dil karışması bu nişte iki yönlü: Spotify bir İngiliz psych grubunu Türk
  gösteriyor (1.6); hesap ülkesi Türkiye olunca öneriler "bundan" (1.6).
  Türkçe rock dinleyicisine "Türkçe" diye pop/arabesk sızması riski (CLAUDE.md
  Sezen Aksu vakası) dinleyici şikâyetleriyle aynı aile.
- Türkiye'de Spotify, Rekabet Kurumu soruşturmasıyla (hangi sanatçılara
  görünürlük verildiği) ve Bakan Yardımcısı'nın halk/arabesk eleştirisiyle
  karşı karşıya — görünürlüğün tarafsız olmadığı algısı yaygın.
  https://www.musicbusinessworldwide.com/spotify-could-exit-turkey-amid-government-probe-over-provocative-playlists-report ·
  https://routenote.com/blog/?p=105137 · https://newsroom.spotify.com/tag/turkiye
- Ekşi Sözlük'te Haftalık Keşif'e özgü bir şikâyet başlığı bulunamadı;
  bulunan entry'ler sistemin "benzer zevkli binlerce kişilik havuz" mantığını
  ve "profilden hariç tut" ayarını anlatıyor.
  https://eksisozluk.com/entry/67578668 · https://eksisozluk.com/entry/150222266

### 4.5 Hip-hop

Bu oturumda hip-hop'a özgü dinleyici kanıtı **toplanamadı** (bütçe). [G]:
Hip-hop meraklılarının bilinen yolu prodüktör (beat yapımcısı) ve sample
kaynağı üzerinden keşif; projenin kredi grafiğindeki "producer" rolü bu eksen
için davuldaki davulcunun karşılığı olabilir. Ölçülmeden karar verilmemeli.

---

## 5. Somut, sınanabilir tasarım sezgileri

Sıralama: dinleyicilerin bunu ne sıklıkla ve ne şiddetle dile getirdiği.
Her biri için: **kural**, **ölçüm** (K19 ruhunda), **projedeki durum**.

### S1 — Kullanıcının zaten bildiği sanatçıyı önerme; "biliyorum" ≠ "sevmiyorum"
- Kanıt: 1.1 (en sık şikâyet; atlama = olumsuz sinyal çöküşü).
- Kural: kütüphane + "zaten biliyorum" + daha önce yargılanan sanatçılar
  sanatçı düzeyinde dışarıda. "Zaten biliyorum" zevk isabeti paydasına girmez.
- Ölçüm: strateji başına "zaten biliyorum" oranı (keşif oranı). Hedef örneğin
  < %15; aşan strateji "popüler kenar" üretiyordur.
- Durum: **var** (K21, `geri_bildirim.py`). Ek fikir: kütüphanedeki bir
  grubun **üyesinin solo projesi** "biliyorum"a yakın mı, yoksa tam aranan
  kredi sıçraması mı? Oranı ayrıca raporla.

### S2 — Tek sanatçı tek kart; reddedilen asla geri gelmez
- Kanıt: 1.2 ("gizlediğim sanatçı her hafta geliyor").
- Kural: destede sanatçı başına ≤1 kart; "tutmadı" kalıcı.
- Ölçüm: deste başına farklı sanatçı / kart oranı = 1.0; reddedilen
  sanatçının tekrar görünme sayısı = 0 (test olarak yazılabilir).
- Durum: **var** (karar sanatçı düzeyinde).

### S3 — Tek bir tohumun (liste, kütüphane sanatçısı, müzisyen) desteyi ele geçirmesine tavan
- Kanıt: 1.5 ("%80 ambient"), 1.6 ("tek İbranice parça tüm önerileri
  çeviriyor"), Spotify'ın "profilden hariç tut"u.
- Kural: bir pencerede (ör. 10 kart) aynı kaynak sanatçıdan / aynı çalma
  listesinden gelen kart ≤ N (ör. 2–3).
- Ölçüm: kartların gerekçesindeki `kaynak_sanatcilar` dağılımının entropisi;
  en büyük tohumun payı.
- Durum: **kısmen** — `KISI_BASINA_AZAMI = 2` kredi yolunda var (Mukaiya
  vakası); liste ve ses yollarında tohum başına tavan görülmedi.

### S4 — Eksenler ayrı tutulsun; çoğunluk ekseni azınlığı yutmasın
- Kanıt: 1.4, 1.5; Spotify'ın 2025 tür düğmeleri.
- Kural: eksen başına pay kullanıcının seçimine bağlı; seçim yoksa
  kütüphanedeki ağırlıktan fazla değil.
- Ölçüm: destedeki eksen payı ↔ hedef pay farkı; azınlık eksenlerinin
  zevk isabeti ayrı raporlanır.
- Durum: **var** (eksen seçimi + round-robin, K1/K21).

### S5 — Dil, stilin gizli vekili olmasın; ayrı ve açık bir eksen olsun
- Kanıt: 1.6 (Hollandaca, Telugu, İbranice, "hesap ülkesi Türkiye").
- Kural: yalnız dil/ülke ortaklığına dayanan bağ stil ekseninde öneri
  sayılmaz; dil isteniyorsa açık bir seçim olur.
- Ölçüm: CLAUDE.md'deki açık iş (2): bağ, dil/ruh hâli başlıklı listeler
  **dışında** da var mı? Liste-türü-dışlamalı PMI ile gizleme sınaması.
- Durum: **kısmen** (`gerekce.py` ≤3 listede "dil ya da ruh hâli listelerinden
  gelebilir" uyarısı veriyor); ölçüm açık.

### S6 — Bağlam listeleri (uyku, spor, parti, "nostalji") stil sinyaline girmesin
- Kanıt: 1.7, 1.8 (Pelly, "Roadtrip Bangers", yağmur sesi).
- Kural: başlığı etkinlik/ruh hâli sözlüğüne düşen listeler stil PMI'sinden
  çıkarılır ya da ayrı "bağlam" sinyali olur (K16 zaten saklıyor).
- Ölçüm: bağlam listeleri dahil/hariç PMI ile leave-one-artist-out recall@50
  kıyası; hariç sürüm kötüleşmiyorsa hariç tut.
- Durum: **kısmen** (başlıklar saklanıyor; süzgeç ölçülmedi).

### S7 — Ortak müzisyeni (davulcu, basçı, prodüktör) kartın üstünde göster — hangi yoldan gelirse gelsin
- Kanıt: 2.4 (Liner Notes Project, session müzisyeni kredisi talepleri,
  SongDNA, Tidal; Plini–Intervals ortak kadro).
- Kural: aday hangi stratejiden gelirse gelsin, kütüphaneyle **ortak bir
  kredi** varsa kartta ayrı satır: "Davulda X — kütüphanende onun 4 albümü var."
- Ölçüm: ortak-kredi satırı olan kartların zevk isabeti ↔ olmayanlar
  (deterministik tohumla eşleştirilmiş kıyas; Wilson aralığı).
- Durum: **kısmen** — `kredi_sicramasi` "cesur" kaynakta, ana destede değil;
  K21'in `KANIT_AILESI`/uzlaşma mekanizması bu satırı taşıyabilir.

### S8 — Açıklama sayısal, denetlenebilir ve çalınabilir olsun; jargon tek başına açıklama değil
- Kanıt: 2.1 (yüksek bilişsel ihtiyaçlı kullanıcıda süs açıklama güveni
  düşürür), 2.2 (Pandora "hafif ritmik senkop").
- Kural: her gerekçe = sayı + kaynak + kanıt gücü + (ses yolunda) çalınabilir
  karşılaştırma klibi.
- Ölçüm: **kalibrasyon** — kanıt gücü kovalarına (ör. 1–3 / 4–10 / 10+ liste)
  göre zevk isabeti artmalı. Artmıyorsa gerekçe yanlış bir güven veriyor.
- Durum: **var** (K7, K13, `gerekce.py`); kalibrasyon ölçümü önerilir.

### S9 — Öneri öğesi stüdyo albümü olsun — ama iki meşru istisna
- Kanıt: 1.8 (derleme/cover/yeniden paket şikâyeti); 4.3 (Mint Jams canlı ama
  kanonik giriş); 4.4 (Anadolu rock'ında single + sonradan derleme).
- Kural: derleme/bootleg/cover öneri öğesi olmaz. **İstisna:** sanatçının
  topluluk koleksiyonu en yüksek kaydı canlıysa (Discogs `ASGARI_KOLEKSIYON`
  verisi zaten var) canlı kayıt öğe olabilir; stüdyo albümü olmayan
  dönem/sanatçıda tek-sanatçı derlemesi öğe olabilir. Çok sanatçılı sahne
  derlemesi öğe değil, **kanıt** olur.
- Ölçüm: süzgeçten düşen ama koleksiyon sayısı sanatçının diğer kayıtlarının
  üstünde olan kayıtların sayımı (bu istisnanın kaç kez tetikleneceği).
- Durum: **katı süzgeç var**; istisna yok.

### S10 — Popülerliği sönümle ama kartta bilinirliği söyle
- Kanıt: 1.10 (ana akım dışına en kötü öneri; "100'den az dinleyici"
  arzusu).
- Kural: aday popülerliği kütüphanenin kendi popülerlik dağılımına yakın
  ya da biraz altında; kartta bilinirlik bandı ("kütüphanendeki ortalama
  sanatçıdan daha az biliniyor").
- Ölçüm: aday popülerlik yüzdelikleri ↔ kütüphane dağılımı (KS mesafesi);
  bilinirlik bandı başına keşif oranı ve zevk isabeti.
- Durum: **sönümleme var** (PMI, LB); kartta bilinirlik gösterimi yok.

### S11 — Tek parçanın taşıdığı sanatçıyı ayıkla; kanıt birden çok parçadan gelsin
- Kanıt: 4.3 (Plastic Love tek-şarkı kapısı), 1.11 (uzun parçalar
  önerilmiyor), `medya.albumden` "en popüler parça" seçimi.
- Kural: ses/liste kanıtı ≥2 parça ya da ≥2 albümden gelmeli, yoksa "zayıf"
  etiketi; önizleme olarak sanatçının en popüler single'ı yerine kanıtı
  taşıyan parça çalınsın.
- Ölçüm: tek-parça kanıtlı kartların zevk isabeti ↔ çok-parça kanıtlı kartlar.
- Durum: **kısmen** (`_ses_cumlesi` çok-albüm kanıtını ayırt ediyor; önizleme
  seçimi popülerliğe dayanıyor).

### S12 — Tazelik: aynı yargılanmamış kartı sonsuza dek döndürme
- Kanıt: 1.1–1.2 ("aynı 30 şarkı her listede", radyonun %40'ı daha önce çıkmış).
- Kural: yargılanmamış bir kart k kez (ör. 3) gösterildiyse geri plana iner;
  ardışık destelerin Jaccard örtüşmesi raporlanır.
- Ölçüm: gösterim sayısı dağılımı; ardışık deste Jaccard'ı.
- Durum: **bilinmiyor** — deste tohumu karar sayısına bağlı (aynı durum aynı
  deste, K2); karar verilmeden açılıp kapanırsa aynı kartlar gelir. Bu
  tekrarlanabilirlik için doğru, tazelik için ölçülmeli.

### S13 — İnsan kürasyonunu ağırlıkla; şirket editoryalini ayır
- Kanıt: 2.5 ("resmî listelerden kaçının, gerçek insanlarınkine bakın"),
  Pelly'nin PFC iddiası.
- Kural: kullanıcı-yapımı listeler ile platform editoryal listeleri ayrı
  sayılır; PMI ikisinde ayrı hesaplanıp kıyaslanır.
- Ölçüm: iki kaynakla ayrı ayrı gizleme sınaması.
- Durum: **bilinmiyor** (Deezer listelerinin sahibi ayrıştırılıyor mu
  bakılmadı).

### S14 — Gezilebilir harita: akışın yanında yürüme
- Kanıt: 1.13 (Every Noise yası), 2.4 (Liner Notes'ta tıklanabilir ad).
- Kural: kart üstündeki her müzisyen adı o kişinin diğer kayıtlarına
  tıklanabilir; kütüphanede olmayanlar işaretli.
- Ölçüm: tıklama → Listem'e ekleme dönüşümü.
- Durum: **yok** (deste var, kredi gezintisi yok).

### S15 — "Ne kadar uzağa?" düğmesi
- Kanıt: 1.3 (ince ayar talebi), Spotify oturum kontrolleri.
- Kural: "güvenli / cesur" ayrımı kullanıcıya açık; cesur kartta neden uzak
  olduğu yazılı.
- Durum: **var** (`KAYNAKLAR = ana / cesur / hepsi`).

### S16 — Küçük, tür odaklı label'ı yeniden ölç
- Kanıt: 2.5 (HN'de label takibi en çok anılan yollardan).
- Kural önerisi değil, **ölçüm önerisi**: K9 kararını label büyüklüğüne göre
  ayır (katalog ≤ N sürüm). Küçük label birlikteliği gizleme sınamasında
  rastgeleden iyi mi?
- Durum: K9 ile kapalı; yeniden açmak kullanıcı kararı.

### S17 — Metadata hijyeni: ad çakışmasında MBID, yoksa gösterme
- Kanıt: 1.9 (Vektor, aynı adlı tekno).
- Durum: **var** (MBID, K14, `/eslestirme`).

### S18 — Dönem ve araç kısıtı istekte yer alabilsin
- Kanıt: 2.3 (CSCW 2024: zaman kısıtı ve "yapıldığı araçlar").
- Kural: deste filtresi olarak dönem (on yıl) ve rol/enstrüman ("davulu
  benzesin") seçimi.
- Durum: **kısmen** (stem profili var; deste filtresi olarak sunuluyor mu
  bakılmadı).

---

## 6. Kısa sentez

1. Dinleyicinin en çok öfkelendiği şey **bilineni önermek** ve **reddedileni
   geri getirmek**; ikisi de güveni bir kartta bitiriyor. Proje bu iki
   konuda sektörden önde.
2. İkinci büyük aile **sızıntı**: dil, ülke, ruh hâli/bağlam, tek bir
   tohumun ağırlığı, çoğunluk ekseni. Ortak kökleri "birliktelik sinyalinin
   müzik dışı nedenleri". Projede kısmen ele alınmış; en çok ölçüm borcu
   burada (S3, S5, S6).
3. Meraklının güvendiği gerekçe **kişi** (kim çalmış, kiminle turneye çıkmış)
   ve **kanıtın kendisi** (çalınabilir klip, sayı). Kullanıcının profili
   (yüksek bilişsel ihtiyaç) süs açıklamayı cezalandırır, denetlenebilir
   açıklamayı ödüllendirir.
4. Nişlerin iki özel tuzağı var: füzyonda kanonik **canlı** kayıtlar,
   Anadolu rock'ında **single + derleme** biçimi. Projenin katı albüm
   süzgeci ikisinde de meşru adayı düşürebilir (S9).
5. Kalabalık sinyali (liste, Last.fm) Plini/Intervals/Polyphia gibi kümeleri
   ve city pop/füzyon gibi sahneleri **tek parça** görüyor; içlerini ayıran
   ses/icra ekseni (K12) ve "aynı sahne ama farklı karakter" cümlesi.

---

## 7. Kaynaklar

### Spotify Community (dinleyici şikâyetleri)
- https://community.spotify.com/t5/Live-Ideas/Improve-discover-weekly-Less-repeat-artists/idi-p/7516193
- https://community.spotify.com/t5/Desktop-Windows/Does-Discover-Weekly-quot-Don-t-Recommend-quot-button-also-not/td-p/2759293
- https://community.spotify.com/t5/Your-Library/Discover-Weekly-constantly-terrible/m-p/6153790/highlight/true
- https://community.spotify.com/t5/Music-Discussion/Why-Discovery-weekly-and-released-radar-have-same-song/td-p/7181995
- https://community.spotify.com/t5/Live-Ideas/Spotify-amp-quot-Song-Radio-quot-is-Essentially-Just-an-Echo/idc-p/5182396/highlight/true
- https://community.spotify.com/t5/Your-Library/Keep-getting-recommended-the-same-songs/td-p/5504758/page/3
- https://community.spotify.com/t5/Your-Library/Issues-with-Spotify-s-recommendation-algorithms/td-p/5646049
- https://community.spotify.com/t5/Accounts/Discover-weekly-playing-items-i-know/td-p/4593993
- https://community.spotify.com/t5/Content-Questions/More-Discover-Weekly-Problems/td-p/4653902
- https://community.spotify.com/t5/Your-Library/Yet-another-Discover-Weekly-question/m-p/4981380
- https://community.spotify.com/t5/Content-Questions/Why-does-my-radio-on-Spotify-play-mostly-the-same-songs-I-used/td-p/5248665
- https://community.spotify.com/t5/Content-Questions/Wrong-language-suggestions/td-p/5394595
- https://community.spotify.com/t5/iOS-iPhone-iPad/Spotify-Does-Not-Consider-Language-Preference-For/td-p/4737193
- https://community.spotify.com/t5/Content-Questions/Strange-section-in-main-feed/m-p/5227359/highlight/true
- https://community.spotify.com/t5/Content-Questions/Release-Radar-showing-old-songs-due-to-compilations/m-p/7138150/highlight/true
- https://community.spotify.com/t5/Discovery-Promo/Why-is-Spotify-Putting-Songs-From-the-90s-in-Release-Radar/td-p/7138331
- https://community.spotify.com/t5/Content-Questions/quot-Fans-Also-Like-quot-section-is-completely-wrong/m-p/6629310/highlight/true
- https://community.spotify.com/t5/Content-Questions/quot-Related-artists-quot-how-do-Spotify-decide-what-artists-are/td-p/1185597/page/3
- https://community.spotify.com/t5/Your-Library/Release-radar-has-content-from-wrong-artists-with-the-same-name/m-p/5152657/highlight/true
- https://community.spotify.com/t5/Live-Ideas/Exclude-genres-from-discover-weekly-and-allow-forced-algorithm/idi-p/7494104
- https://community.spotify.com/t5/Implemented-Ideas/Displaying-album-credits/idc-p/4096191/highlight/true
- https://community.spotify.com/t5/Music-Discussion/Prog-rock-fans/m-p/4868462/highlight/true

### Hacker News, Reddit, forumlar
- https://news.ycombinator.com/item?id=15447706
- https://news.ycombinator.com/item?id=32835559
- https://news.ycombinator.com/item?id=22194107
- https://news.ycombinator.com/item?id=20724959
- https://hn.nuxtjs.org/item/40147534 (HN 40147534 yansıması)
- https://www.reddit.com/r/progmetal/comments/q045g8/ (Redlib yansıması üzerinden görüldü)
- https://www.reddit.com/r/progmetal/comments/bdlv9q/ (Redlib yansıması üzerinden görüldü)
- https://lr.vern.cc/r/progmetal/comments/1cpvag9/new_listener_based_on_what_i_like_what_else/l3tpxjm/
- https://lr.eu.psf.lt/r/Djent/hot (geçici liste sayfası)
- https://www.reddit.com/r/ifyoulikeblank/ (kurallar)
- https://lemmy.dbzer0.com/post/1993/12553
- https://tildes.net/~music/1r5u/the_algorithm_failed_music
- https://www.head-fi.org/threads/prog-rock.211107/page-287
- https://forums.whathifi.com/threads/looking-for-new-music-let-gnod-and-spotibot-help-you.40504/latest
- https://www.stereonet.com/forums/topic/31606-how-do-you-discover-new-and-old-music/
- https://forums.audioholics.com/forums/threads/where-do-you-find-new-music.23887/post-451268
- https://eksisozluk.com/entry/67578668
- https://eksisozluk.com/entry/150222266

### Gazetecilik, deneme, bülten
- https://newsroom.spotify.com/2025-10-01/exclude-tracks-taste-profile/
- https://www.techradar.com/news/spotifys-new-feature-keeps-peppa-pig-away-from-your-heavy-metal-playlist
- https://webrazzi.com/2025/06/30/spotify-haftalik-kesif-calma-listelerinin-kisisellestirilmesine-izin-verecek/
- https://www.teknoblog.com/spotify-haftalik-kesif-tur-filtre-guncellemesi/
- https://www.engadget.com/2020-02-12-spotify-songwriter-pages-beta.html
- https://www.digitalmusicnews.com/2025/10/16/jane-wong-spotify-songdna-discovery/
- https://techcrunch.com/2024/02/12/every-noise-shut-down-spotify-layoffs
- https://www.techradar.com/audio/spotify/finding-new-artists-on-spotify-just-got-harder-after-layoffs-put-an-end-to-useful-music-encyclopedia-and-im-tired-of-it
- https://www.headphonesty.com/2024/02/spotify-layoff-kills-top-music-discovery-tool/
- https://www.npr.org/2024/01/16/1225002436/book-review-kyle-chayka-filterworld
- https://reason.com/2024/01/23/filterworld-is-a-confused-critique-of-algorithms/
- https://recordstore.substack.com/p/interview-liz-pelly
- https://www.aristake.com/liz-pelly/
- https://hhsepitaph.com/?p=13128
- https://mildatheart.substack.com/p/stop-finding-music-through-spotify
- https://bobbylive505.substack.com/p/is-spotify-killing-music-the-algorithms
- https://theanxiouslab.substack.com/p/spotify-product-teardown
- https://happymag.tv/the-age-we-stop-seeking-new-music/
- https://www.bespacific.com/?p=114515
- https://pxlnv.com/blog/something-new-in-something-old/
- https://www.subtraction.com/2007/10/05/thats-the-la/
- https://www.johnjosephadams.com/2006/01/04/pandora-radio/
- https://www.heavyblogisheavy.com/2016/04/13/sailing-the-seas-of-sound-a-brief-overview-of-music-exploration-tools/
- https://www.heavyblogisheavy.com/2023/07/25/heavy-blogs-top-25-albums-of-2023-so-far/
- https://www.stevelawson.net/2023/10/how-to-find-music-on-bandcamp/
- https://www.chartlex.com/blog/marketing/bandcamp-discovery-algorithm-fan-finding-2026
- https://jazzfuel.com/steve-lieblich-the-liner-notes-project/
- https://vinylives.wordpress.com/2023/07/17/session-players-and-sidemen/
- https://www.thatericalper.com/2026/10/13/how-session-musicians-from-the-old-days-are-finally-getting-credit/
- https://www.musicbusinessworldwide.com/spotify-could-exit-turkey-amid-government-probe-over-provocative-playlists-report
- https://routenote.com/blog/?p=105137
- https://newsroom.spotify.com/tag/turkiye

### Nişler (prog, gitar, Japon füzyonu, Anadolu rock)
- https://tuonelamagazine.com/the-10-most-delicious-metal-songs-with-proggy-time-signatures/
- https://www.heavyblogisheavy.com/2016/02/18/beyond-the-veil-a-match-made-in-seven-or-progressive-metals-affair-with-78/
- https://www.musicradar.com/news/the-7-best-prog-drummers-in-the-world-right-now
- https://en.wikipedia.org/wiki/Gavin_Harrison
- https://metalinsider.net/?p=129940
- https://www.last.fm/music/Polyphia/+similar
- https://showsigoto.com/?p=63812
- https://goodtasterecords.com/blogs/news/casiopea-on-vinyl-where-to-start-with-the-japanese-fusion-pioneers
- https://en.wikipedia.org/wiki/T-Square_(band)
- https://tiffanyjohns.com/blog/lp2
- https://www.openculture.com/2018/10/youtubes-algorithm-turned-obscure-1980s-japanese-song-enormously-popular-hit-discover-mariya-takeuchis-plastic-love.html
- https://pages.vassar.edu/musicalurbanism/?p=2066
- https://en.wikipedia.org/wiki/Plastic_Love
- https://www.koreatimes.co.kr/amp/world/20220222/city-pop-the-soundtrack-to-japans-boom-years-goes-viral
- https://www.npr.org/2011/10/18/140432961/turkish-freakout-a-musical-turkish-delight
- https://forcedexposure.com/Catalog/FKR.091LP.html
- https://www.desertcart.lk/products/7575811-turkish-freakout

### Araştırma
- https://bebop.berkeley.edu/papers/MusicCHI_RSFinal.pdf (Sinha & Swearingen)
- https://www.cs.ubc.ca/~conati/522/532b-2019/papers/MillecampIUI2019.pdf (Millecamp vd., IUI 2019)
- https://lirias.kuleuven.be/retrieve/525282
- https://arxiv.org/abs/2408.06201 (r/ifyoulikeblank, CSCW 2024)
- https://ar5iv.arxiv.org/html/2208.09517 (popülerlik yanlılığı, ticari servisler)
- https://graz.elsevierpure.com/de/publications/the-unfairness-of-popularity-bias-in-music-recommendation-a-repro
- https://www.newswise.com/articles/algorithm-based-music-recommendations-low-accuracy-for-lovers-of-non-mainstream-music
- https://arxiv.org/abs/2003.11634
