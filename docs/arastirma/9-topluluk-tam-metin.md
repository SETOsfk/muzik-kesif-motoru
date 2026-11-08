# 9 — Topluluk tam metin okuması: insanlar nasıl keşfediyor, neye "benzer" diyor, algoritmaya neden kızıyor

Tarih: 2026-10-20 · Önceki rapor: `4-dinleyici-sesi.md` (yalnız arama özetleri).
Bu rapor **tam iplik metinlerine** dayanıyor: 41 forum ipliği/sayfası (666 ileti) +
7 Hacker News ipliği (530 yorum) + HN yorum araması. Asıl ürün §3'teki
**insan küratörlü "X seviyorsan Y" çift tablosu** (K19 için küçük bir dış test kümesi).

---

## 0. Yöntem, erişim ve sınırlar (önce bunu oku)

**Reddit okunamadı.** `old.reddit.com` her sayfada (arama, iplik, `/top`) oturum
açmayan istemciyi `302 → /login/?reason=lor2` ile girişe yönlendiriyor; tam tarayıcı
başlıklarıyla da aynı. `www.reddit.com` yalnızca boş bir JS kabuğu döndürdü.
Toplam **4 Reddit sayfa isteği** yapıldı, hepsi engellendi. Redlib yansımaları ya da
arşiv kopyalarıyla bu duvarın etrafından dolaşılmadı (Reddit'in açık tercihi ve K10
ruhu). Bu yüzden istenen r/drums, r/jazzfusion, r/Guitar, r/hiphopheads, r/spotify,
r/citypop, r/indieheads, r/TurkishMusic **doğrudan okunmadı**; aynı soruların
cevabı erişilebilen forumlardan toplandı.

**Bot duvarı (Cloudflare/403/202) olan ve okunamayanlar:** progarchives.com,
forums.stevehoffman.tv, talkbass.com, thegearpage.net, sevenstring.org,
eksisozluk.com, technopat.net, jazzmusicarchives.com, discogs.com/forum, ilxor.com,
metalstorm.net, lemmy.world; web.archive.org ve sputnikmusic vekil üzerinden
bağlanmadı. Bunların içeriği yalnız arama motoru özetlerinden geldiyse tabloda
**[Ö]** (özet) işaretli ve onay sayısı verilmedi.

**Okunabilenler (tam metin):** Encyclopaedia Metallum forumu (phpBB, 14 iplik-sayfa),
Ultimate-Guitar forumu (8 iplik), DonanımHaber forumu (6 iplik, yazdırılabilir sürüm),
Uludağ Sözlük (1 başlık), MusicBanter (2 iplik, 5 sayfa), Physics Forums (1 iplik,
3 sayfa), Hacker News (Algolia'nın belgelenmiş açık API'si; 7 iplik).

**Gizlilik:** Kullanıcı adları hiçbir dosyaya yazılmadı. Aynı kişinin iki kez
sayılmaması için ad, bellekte tuzlu SHA-1 ile 5 hanelik bir etikete çevrildi
(`k3b97f` gibi); yalnız bu etiket tutuldu. HTML hiç diske yazılmadı, borudan
doğrudan düz metne çevrildi (`scratchpad/metin/`).

**"Onay" (endorsement) nasıl sayıldı:** bir iplikte öneriyi yazan ya da açıkça
destekleyen ("seconded", "bence de") **farklı kişi** sayısı; soran kişi (OP) ve
reklam botları hariç. Aynı kişi iki iplikte aynı öneriyi yaptıysa tek sayıldı
(etiket iplikler arası tutarlı olduğu için bu görülebildi — ör. Four Question Marks,
Nick Johnston, Counter-World Experience). Olumsuz anışlar ("kötü bir kopya")
onaydan düşüldü ve ayrıca yazıldı.

**Kanıtın yaşı ve yanlılığı:** forum iplikleri çoğunlukla 2009–2018; metal forumu
baskın. Tablo bu yüzden **teknik/prog metal ve gitar** tarafında güçlü, **J-füzyon
ve hip-hop** tarafında zayıf. Bu dengesizlik §5'te tasarım bulgusu olarak ele alındı.

---

## 1. Temalar ve kaba sayımlar

### 1.1 Forumlarda "benzer" ne demek? (641 ileti, 41 iplik-sayfa; anahtar sözcük sayımı + elle okuma)

Sayılar bir iletinin o temaya **değindiğini** gösterir; DonanımHaber'deki
alıntı tekrarları sayıyı biraz şişiriyor. Sıra, elle okumada da aynı çıktı.

| Tema | İleti | İplik | Ne diyorlar (örnek) |
|---|---:|---:|---|
| Teknik / ritim / ölçü / riff / davul | 118 | 29 | "poliritmik", "tuhaf ölçüler", "legato", "riff odaklı prog" |
| Vokal — ölçüt **ya da veto** | 53 | 20 | "growl'u bana göre değil", "domuz çığlığı vokale dayanamıyorum", "can sıkıcı vokaller", "böyle vokal performansı görmedim" |
| Tür etiketi kavgası | 47 | 16 | "Duman grunge mu, arabesk rock mu?", "AAL caz değil djent", "gerçek prog dinamik olmalı" |
| Atmosfer / duygu / ruh hâli | 45 | 21 | "uzay/bilimkurgu havası bonus", "duygu dolu şarkılar" |
| Albüm / dönem özgüllüğü | 41 | 18 | "ilk üç albümü", "Awake'ten sonra dağıldı", "Murat İlkan'lı zamanlar", "Reachin' ile başla" |
| Etki soyu ("kaynağa git") | 39 | 15 | "AAL ve Periphery için: bol Meshuggah, bol Holdsworth"; "Govan'ın frazı Vai'den" |
| Üretim / ton / sample | 31 | 19 | "gitar tonu ince", "hepsi caz sample'ı ağır" |
| Zaten biliyorum | 22 | 16 | "hepsini biliyorum ve hiçbiri benzemiyor" |
| Söz / anlam | 20 | 9 | "anlamlı, küfürlü değil", "araba-kız değil, anlamı olan" |
| **Kadro / kredi gerekçesi** | 20 (+elle 24 öneri) | 14 | "iki Cynic üyesi var", "ikinci şarkında o çalıyor", "Psychotic Waltz'ın adamı", "davulda Burak Gürpınar, basta Kerem Tüzün" |
| Açık ret | 16 | 10 | "bir dakikadan fazla dinleyemedim", "sıkıcı buldum" |

**Elle sayılan kredi gerekçeli öneriler (24):** Exivious ("iki Cynic üyesi"),
Gnostic (Atheist yan projesi), Aghora (Sean Malone + Sean Reinert), Blotted Science
(Ron Jarzombek; "Alex Webster'ı Cannibal Corpse dışında duymak"), Beyond Creation
(Augury'den Forest Lapointe), Trepallium ("Gojira'dan biri prodüktör"), Nick Johnston
("ikinci şarkında o çalıyor"), Conquering Dystopia (Jeff Loomis), Josh Middleton
(Sylosis), Deadsoul Tribe ("Psychotic Waltz'taki adam"), Direwolf (Behold… the
Arctopus gitaristi), Teramobil (Dom Lapointe), GPS ("Guthrie çalıyor"), Tony
MacAlpine'in CAB'ı, Howe–Kotzen ortak albümleri (Tilt, Project), Shawn Lane +
Jonas Hellborg, Tetsuo Sakurai'nin Gentle Hearts'ı (Casiopea basçısı), Takeshi Hirai
("eski Trix"), Takashi Masuzaki (Dimension), Kurtalan Ekspres ("Barış Manço ile
çalışmış"), Blues Blues Band ("Yavuz Çetin'den dolayı"), Pentagram ("Murat İlkan'lı
zamanlar"), Kurban (Burak Gürpınar davul, Kerem Tüzün slap bas), Redd ("Kim
Bunlar'ın evrilmiş hâli"). **Metal, füzyon ve Türk rock'ta aynı gerekçe dili
kullanılıyor** — K7 şablonunun dili, insanların kendi dili.

### 1.2 İsteklerin biçimi (≈25 istek ipliği)

| Biçim | Kaç istekte | Örnek |
|---|---:|---|
| Birden çok tohum (2–30 sanatçı) | ~20 | "Cynic, Atheist, Pestilence, Mekong Delta, Watchtower, Spastic Ink gibi" |
| Tohum + **nitelik** | ~20 | "melodik öğe bonus", "**iyi bas çalımı zorunlu**", "riff odaklı", "caz etkili", "hızlı tempo" |
| **Olumsuz kısıt** ("şunu verme") | ~11 | "djent verme", "metalcore/deathcore yok", "gitar kahramanı solo albümü yok", "doom değil", "küfürlü değil", "growl istemem", "eski okul tech yok" |
| İşlev/bağlam | 3 | "ödev yaparken arka plan", "arabada dinlemelik", "uzun yol müziği" |

### 1.3 Nasıl keşfediyorlar? (HN 5 iplik ~250 üst düzey yorum + DH 4 iplik + forumlardaki anışlar)

| Yol | Kaba sayı | Not |
|---|---:|---|
| Spotify Discover Weekly / radyo / Daily Mix | ~14 | yarısı memnun, yarısı "yankı odası" |
| YouTube (öneriler, derlemeler, **yorumlar**, kullanıcı yüklemeleri) | ~10 | Türk kullanıcılar YTM'yi **arşiv genişliği** için seçiyor (Spotify'da olmayan, canlı/remix) |
| İnsan radyosu / DJ setleri (KEXP, NTS, BBC 6, SomaFM, Radio Paradise) | ~9 | "insan programlamasının üstü yok" |
| Arkadaş | ~6 | "sinyal/gürültü oranı açık ara en yüksek" |
| Niş forum / subreddit / metal-archives tavşan deliği | ~6 | "geniş /r/music işe yaramaz, niş olanlar yarar" |
| Kadro, label, kayıt mühendisi, Wikipedia/AllMusic/Discogs gezintisi | ~6 | "üyelere, label'a, mühendise bak — bağlar seni yeni şeye götürecek kadar gevşek, aynı şeye kapatacak kadar sıkı değil" |
| Bandcamp (label takibi, "x items in common") | ~4 | küçük, tür odaklı label = insan kürasyonu |
| Last.fm (benzer + komşular) | ~5 | çoğu geçmiş zamanla, "o algoritma inanılmazdı" |
| RYM / Sputnik / Angry Metal Guy / RSS | ~6 | liste ve inceleme okuyarak |
| Every Noise at Once | ~4 | "alt türün adını öğrenmek" bir keşif aracı |
| Shazam / dizi-film / mağaza müziği | ~4 | |

### 1.4 Algoritma şikâyetleri (HN DW ipliği 62 üst düzey yorum + HN DW-sıkıcı 15 + HN YTM yorum araması 30 + DH 6 iplik)

| Şikâyet | Kaba sayı | Temsilî ifade (parafraz) |
|---|---:|---|
| Bildiğimi / aynı şarkıları döndürüyor | ~14 | "10–20 şarkılık liste dönüp duruyor"; "kendi müziğimden oluşan listeler çalmaya başladı" |
| Jenerik / popüler / ödemeli | ~8 | "yeni değil, trend olanı öneriyor"; "payola'dan şüpheleniyorum" |
| Bağlam sızıntısı | ~7 | işte arka plan vaporwave'i tüm listeyi doldurdu; PS4'te oyun müziği; çocuk şarkıları; **YouTube video geçmişi YTM'ye karışıyor** |
| Son dinlenene aşırı ağırlık / kısa hafıza | ~5 | "R&B dinledim, sonra j-pop; liste tamamen j-pop oldu"; "bir süre dinleyip bıraktığımı sonra 'keşif' diye önüyor" |
| Dil / ülke sızıntısı | ~5 | İsveçli kullanıcıya %30 Fince; Norveççe dinleyene "İskandinav"; Türkçe dinlemeyen kullanıcıya Türkçe (technopat [Ö]) |
| Tek çekere düşme | ~3 | "hangi tohumla başlasam 20–30 şarkı sonra Ra Ra Rasputin" |
| Örtük geri bildirim belirsiz; açık geri bildirim isteği | ~4 | "algoritma eylemlerimden ne çıkarıyor hep merak ediyorum" |
| "Gürültü / tuhaflık düzeyi" sürgüsü isteği | ~3 | "sürgüyü sonuna kadar çekerdim" |
| Kendini sansürleme | 1 | "DW yanlış anlamasın diye bir türü dinlemekten korkuyorum" |
| "Top songs", deep cut yok; tam albüm | 2 | uzun kütüphaneli dinleyici: "otomatik oynatmayı bıraktım, albümleri baştan sona çalıyorum" |

---

## 2. Forumdaki "kaydırma" verisi: OP'lerin öneriye verdiği kararlar

Bu, araştırmanın en beklenmedik kazancı. Bazı OP'ler önerilerin **her birine** tek
tek cevap vermiş — K21'deki üç yönün (beğendim / tutmadı / zaten biliyorum) insan
uzmanlar arasındaki doğal oranlarını veriyor.

| İplik (tohum) | Yargılanan | Zaten biliyor | Yeni+beğendi | Yeni+tutmadı/kararsız |
|---|---:|---:|---:|---:|
| Tech death/prog uzun liste (91925) | 37 | 23 | 8 | 6 |
| Howe/Govan gibi gitaristler (UG 990479) | 12 | 10 | 0 (1 "dinleyeceğim") | 1 |
| Tool etkili gruplar (123705) | 8 | 0 | 3 | 5 (2 ret, 3 ~) |
| Meshuggah + caz/prog, poliritim (87613) | 7 | 1 | 5 | 1 |
| AAL + Amogh Symphony (91621) | 5 | 0 | 4 | 1 (~) |
| AAL + Gru, arka plan (92820) | 6 | 3 | 1 (+3 "kulağa iyi") | 1 (doom) |
| Gojira (80725) | 4 | 0 | 3 | 1 (tartışmalı) |
| Obscura (54023) | 3 | 0 | 3 | 0 |
| Cynic/Atheist (63469) | 3 | 2 | 1 | 0 |
| Diğer (Holdsworth ×2, AAL→Cynic, Casiopea çaylağı) | ~7 | 2 | 3 | 3 |
| **Toplam** | **~92** | **~41 (%45)** | **~31** | **~20** |

- İnsan uzmanların uzman OP'ye önerisinde bile **"zaten biliyorum" ~%45**. En çok
  bilen OP'de %62 (23/37), Howe/Govan OP'sinde %83 (10/12: "hepsini biliyorum ve
  hiçbiri benzemiyor"). Spotify'a yöneltilen "bildiğimi önerme" şikâyetinin
  insanlarda da yapısal olduğu görülüyor.
- **Yeni** önerilerde beğenme oranı ~%61 (31/51; Wilson %95 aralığı kabaca %47–73). Kaba bir "insan tavanı".
- Kararlar kısa gerekçe taşıyor: "gitar tonu ince", "yeterince lead yok", "doom
  değil hızlı istiyorum", "vokal yüzünden dinleyemedim", "sıkıcı",
  "Linkin Park gibi". Ret nedenleri az sayıda kovaya düşüyor:
  **vokal, tempo/enerji, ton/üretim, fazla zor/sıkıcı, yanlış alt tür**.

---

## 3. İnsan küratörlü çift tablosu (test kümesi adayı)

**Sütunlar:** *Onay* = bağımsız öneren sayısı (§0). *OP* = sorana göre karar:
**+** beğendi · **−** tutmadı · **B** zaten biliyordu · **~** kararsız · boş = yazmadı.
*Gerekçe*: **[kredi]** kadro/çalan/prodüktör · **[ses]** icra/ses tarifi ·
**[soy]** etki zinciri · **[sahne]** · **[söz]**.
Bir satırda birden çok öneri varsa her biri ayrı çifttir; onay sayısı her biri için geçerli.

**Boyut (tablodan sayıldı):** **263 çift**, 27 tohum (çoğu 2–30 sanatçılık tohum
kümesi). **100 çekirdek** (≥2 bağımsız onay **ya da** OP'nin o öneriye açık kararı)
+ 163 tek onaylı. Ayrıca §3.10'da 6 açık **olumsuz** satır (≈15 çift) ve sayılmayan
[Ö] özet satırları.

| Bölüm | Tohum | Çekirdek | Tek onaylı |
|---|---:|---:|---:|
| 3.1 Meshuggah ekseni | 2 | 9 | 5 |
| 3.2 Cynic/Atheist, tuhaf ölçü | 3 | 9 | 19 |
| 3.3 Enstrümantal prog / gitar (AAL, Plini, Polyphia) | 5 | 15 | 23 |
| 3.4 Tech/prog-death (komşu eksen) | 4 | 32 | 11 |
| 3.5 Tool / atmosferik prog | 2 | 10 | 8 |
| 3.6 Gitar virtüözleri / füzyon gitar | 4 | 12 | 33 |
| 3.7 Japon füzyonu | 3 | 5 | 29 |
| 3.8 Türkçe rock + rap | 2 | 6 | 16 |
| 3.9 Hip-hop | 2 | 2 | 19 |

Çekirdeğin üçte biri (32) kullanıcının asıl ekseni olmayan tech-death komşusunda;
kullanıcının nişlerinde (3.1–3.3, 3.5–3.9) çekirdek **68 çift**.

### 3.1 Teknik/prog metal — Meshuggah ekseni

| Tohum | Öneri | Onay | OP | Gerekçe / not | Kaynak |
|---|---|---:|:-:|---|---|
| Meshuggah | Four Question Marks | 2 (2 iplik) | + | aynı öneren iki iplikte; ikinci OP seçti | https://forum.metal-archives.com/viewtopic.php?t=113959 · https://forum.metal-archives.com/viewtopic.php?t=87613 |
| Meshuggah | Vortice | 2 | | | t=113959 |
| Meshuggah | Hi-Tech | 1 | + | [ses] "Meshuggah ile Fear Factory karışımı" | t=113959 |
| Meshuggah (+caz/prog, poliritim) | Revocation | 1 | + | [kredi/ses] solist Berklee'de poliritim çalışmış | t=87613 |
| 〃 | Pain of Salvation (Entropia) | 1 | + | "en funky'si ilk albüm" | t=87613 |
| 〃 | Stargazer · Continuo Renacer | 1 · 1 | + · + | | t=87613 |
| 〃 | Coprofago | 1 | | [ses] "son iki albümde cazlı Meshuggah" | t=87613 |
| 〃 | Periphery · Tesseract · Cloudkicker · After the Burial (*Rareform*, yalnız breakdown'lar) | 1 | | albüm/bölüm düzeyinde öneri | t=87613 |
| 〃 | ARK | 1 | − | "gitar tonu ince" (fretless bası övüyor) | t=87613 |
| 〃 | Atheist | 1 | B | | t=87613 |
| Meshuggah [Ö] | Textures, Tesseract, Sybreed, Mnemic, Special Defects, Animals as Leaders, Bulb, Ion Dissonance, Fragment ("en büyük klon") | ? | | yalnız arama özeti | https://sevenstring.org/threads/bands-like-meshuggah.94661/ · https://sevenstring.org/threads/bands-similar-to-meshuggah.38372/ |

### 3.2 Caz-death / tuhaf ölçü — Cynic, Atheist, Watchtower ekseni

| Tohum | Öneri | Onay | OP | Gerekçe / not | Kaynak |
|---|---|---:|:-:|---|---|
| Cynic · Atheist | Gordian Knot | 3 | | [ses] "Cynic'in enstrümantal hâli gibi" | https://forum.metal-archives.com/viewtopic.php?t=63469 |
| Cynic · Atheist | Exivious | 3 | | **[kredi]** "iki Cynic üyesi var" | t=63469 |
| Cynic · Atheist | Cadaver (*…In Pains*) | 2 | | "teknik ve progresif ama şımarık değil" | t=63469 |
| Cynic · Atheist | Martyr | 2 (2 iplik) | B | | t=63469 · t=61976 |
| Cynic · Atheist | Aghora · Gnostic | 1 · 1 | | **[kredi]** Malone + Reinert · Atheist yan projesi | t=63469 |
| Cynic · Atheist | Gorod | 1 (4 iplikte anıldı) | B | Obscura, Gojira, wankery ipliklerinde de | t=63469 |
| Cynic · Atheist | Voivod · Vektor · Vuvr · Pestilence · Amogh Symphony · Capharnaum · Hieronymus Bosch · Gory Blister | 1 | | | t=63469 |
| Cynic · Atheist · Pestilence · Mekong Delta · Watchtower · Spastic Ink | Blotted Science | 2 (+1 başka iplik) | | **[kredi]** Ron Jarzombek; Alex Webster | https://forum.metal-archives.com/viewtopic.php?t=61976 |
| 〃 | Gorguts (*Obscura*) | 2 | | [ses] "en duvardan duvara ölçüler" | t=61976 |
| 〃 | Sceptic · Anacrusis · Thought Industry (*Songs for Insects*) · Coroner (*Mental Vortex*) · Believer (son üç) · Decapitated · Gonin-Ish · Theory in Practice | 1 | | çoğu **albüm düzeyinde** | t=61976 |
| AAL · Periphery · Painted in Exile | Cynic · Atheist | 2 | **−** | [soy] "asıl caz-füzyon death bu"; OP: "bir dakikadan fazla dinleyemedim" (vokal) | https://www.ultimate-guitar.com/forum/showthread.php?t=1307546 |
| 〃 | Exivious | 1 | | | t=1307546 |

### 3.3 Enstrümantal prog / gitar odaklı — AAL, Plini, Polyphia, Chon

| Tohum | Öneri | Onay | OP | Gerekçe / not | Kaynak |
|---|---|---:|:-:|---|---|
| AAL · Amogh Symphony | Exivious | 1 | + | "o kadar benzemiyor ama akıl almaz" | https://forum.metal-archives.com/viewtopic.php?t=91621 |
| 〃 | Chimp Spanner · Sleep Terror | 1 · 1 | + · + | | t=91621 |
| 〃 | Counter-World Experience | 1 (2 iplik) | + | aynı öneren 91925'te de; **iki ayrı OP beğendi** | t=91621 · t=91925 |
| 〃 | Scale the Summit | 1 | ~ | "iyi şarkıları var, etkilemedi" | t=91621 |
| 〃 | Intervals · Continuo Renacer | 1 | | | t=91621 |
| AAL · Gru (ders çalışırken arka plan) | Scale the Summit | 1 | + | "tam aradığım" | https://forum.metal-archives.com/viewtopic.php?t=92820 |
| 〃 | Electro Quarterstaff | 2 | | | t=92820 |
| 〃 | Russian Circles · Quest for Blood | 1 | B | | t=92820 |
| 〃 | Hungry Ghost · Travis Larson Band · Anomaly | 1 | ~+ | "kulağa iyi ama arka plan değil" | t=92820 |
| Plini · Chon · Thank You Scientist (+caz) | Angel Vivaldi · Polyphia · I Built the Sky · Scale the Summit · Pomegranate Tiger · Exivious · Erra | 1 | + (genel) | tek liste | https://forum.metal-archives.com/viewtopic.php?t=39353&start=760 |
| 〃 | Nick Johnston (*Remarkably Human*) · AAL (*The Joy of Motion*) | 1 | | albüm düzeyinde | t=39353&start=760 |
| Polyphia | Nick Johnston (*Remarkably Human*) | 1 (aynı kişi 2 iplikte) | | **[kredi]** "ikinci şarkında o çalıyor" | https://forum.metal-archives.com/viewtopic.php?t=118934 |
| Polyphia | Buckethead (*Glacier*) · Crow'sclaw · Thousand Leaves · Demetori | 1 | | | t=118934 |
| Tesseract'ın vokalsiz hâli / "metal ile klasik" | Polyphia | 3 | | | https://www.ultimate-guitar.com/forum/showthread.php?t=1702554 |
| 〃 | Cloudkicker (*Beacons*) | 2 (+87613'te 1 → 3 kişi) | | | t=1702554 |
| 〃 | Animals as Leaders | 2 (1 karşı) | | karşı görüş: "Blotted Science varken AAL neden var" | t=1702554 |
| 〃 | Plini · David Maxim Micic · Desolate Dreams · CHON · Apocalyptica | 1 | | | t=1702554 |
| 〃 | Conquering Dystopia · Josh Middleton | 1 · 1 | | **[kredi]** Jeff Loomis · Sylosis'ten | t=1702554 |

İplikler arası toplam (aynı kişi bir kez): **Exivious 7 kişi/5 iplik**, Polyphia 4,
Scale the Summit 3 (OP: 1 +, 1 ~), Cloudkicker 3, Counter-World Experience 2 (2 OP +),
Continuo Renacer 2 (1 OP +, 1 ~).

### 3.4 Tech-death / prog-death (kullanıcının ekseninin komşusu)

| Tohum | Öneri | Onay | OP | Not | Kaynak |
|---|---|---:|:-:|---|---|
| Obscura | Necrophagist | 2 (+1 ikircikli) | ~+ | | https://forum.metal-archives.com/viewtopic.php?t=54023 |
| Obscura | Quo Vadis | 2 | | | t=54023 |
| Obscura | Spawn of Possession | 1 | + | "en sevdiğim" | t=54023 |
| Obscura | Augury · Neuraxis · Illogicist · Decapitated · Visceral Bleeding · Gorod · Luen-Ta | 1 | | | t=54023 |
| Beyond Creation · Obscura · Contortionist · AAL · Exivious… (30 tohum) | Vale of Pnath | 3 | + (yeni) | | https://forum.metal-archives.com/viewtopic.php?t=91925 |
| 〃 | Fallujah · Augury | 3 · 3 | B+ · B+ | | t=91925 |
| 〃 | Archspire | 2 | + (yeni) | | t=91925 |
| 〃 | First Fragment · Anomalous | 2 · 2 | B+ · B+ | | t=91925 |
| 〃 | Allegaeon · Brain Drill | 2 · 2 | B~ · B~ | | t=91925 |
| 〃 | Diskreet | 2 | B− | "bana göre değil" | t=91925 |
| 〃 | Ever Forthright · Widek · Kamikabe · The Boy Will Drown | 1 | + (yeni) | Widek: "AAL, Periphery, Veil of Maya dediğin için" | t=91925 |
| 〃 | Phantasmagory · Viatrophy · Recueil Morbide · Henker | 1 | − | "yeterince lead yok", "aklımda kalmadı" | t=91925 |
| Brain Drill · Viraemia ("tech wank") | Necrophagist · Origin | 4 · 4 | | | https://forum.metal-archives.com/viewtopic.php?t=62505 |
| 〃 | Psycroptic · Decrepit Birth · The Faceless | 3 | | | t=62505 |
| 〃 | Malebolgia · Anomalous · Sleep Terror · Arsis | 2 | | | t=62505 |
| 〃 | Beyond Creation | 1 | | **[kredi]** "Augury'den Forest Lapointe bas çalıyor" | t=62505 |
| Gojira | Aabsinthe · Martriden · Vielikan | 1 | + · + · + | | https://forum.metal-archives.com/viewtopic.php?t=80725 |
| Gojira | Klone · Gorod | 1 | | | t=80725 |
| Gojira | Trepallium | 1 | | **[kredi]** "Gojira'dan biri prodüktör" | t=80725 |

### 3.5 Tool / atmosferik-alternatif prog

| Tohum | Öneri | Onay | OP | Not | Kaynak |
|---|---|---:|:-:|---|---|
| Tool | Soen | 3 | + | davulcunun Tool üzerine sözünü alıntılıyorlar | https://forum.metal-archives.com/viewtopic.php?t=123705 |
| Tool | Deadsoul Tribe | 3 | + | **[kredi]** "Psychotic Waltz'taki adamın grubu" | t=123705 |
| Tool | Rishloo · Wheel | 1 · 1 | + · ~ | Rishloo: "bunlar gerçekten nitelikli"; Wheel: "bir sonraki Tool albümünü beklerken" (OP'nin övgüsü Soen'e mi Wheel'e mi, belirsiz) | t=123705 |
| Tool | Chevelle · Earshot | 1 | ~ · ~ | "ton benzer, sürreal tavır yok" | t=123705 |
| Tool | Cobalt · Anciients | 1 | | | t=123705 |
| Tool · APC · Isis | Cult of Luna · Neurosis · Rosetta | 3 · 3 · 3 | | Cult of Luna'ya vokal uyarısı | https://www.ultimate-guitar.com/forum/showthread.php?t=1503817 |
| 〃 | Dead Letter Circus | 2 | | | t=1503817 |
| 〃 | Karnivool · Katatonia · Pelican · Russian Circles · Devin Townsend · God Is an Astronaut | 1 | | | t=1503817 |

### 3.6 Gitar virtüözleri / füzyon gitar

| Tohum | Öneri | Onay | OP | Not | Kaynak |
|---|---|---:|:-:|---|---|
| Govan · Howe · Lane | **Scott Henderson / Tribal Tech** | **5 (3 iplik)** | | en tutarlı öneri | https://www.ultimate-guitar.com/forum/showthread.php?t=1527703 · https://www.ultimate-guitar.com/forum/showthread.php?t=990479 · https://www.ultimate-guitar.com/forum/showthread.php?t=1410836 |
| 〃 | Allan Holdsworth | 5 (4 iplik) | **− (2 OP)** | [soy] "içine giremiyorum", "beni sıkıyor"; giriş: *Ruhkukah*, *Hard Hat Area* | t=1527703 · t=990479 · https://www.ultimate-guitar.com/forum/showthread.php?t=1670339 |
| 〃 | Al Di Meola | 4 (3 iplik) | ~ | "Guthrie'den çok Howe'a yakın" | t=1527703 · t=990479 · t=1670339 |
| 〃 | Steve Morse · Brett Garsed · Wayne Krantz | 3 · 3 · 3 | | Morse: *StressFest*, *Structural Damage* | t=1527703 · t=990479 · t=1670339 |
| 〃 | Frank Gambale | 3 | **−** | "sıkıcı buldum"; öneren: *Get Live!* (canlı), *Great Explorers* | t=990479 |
| 〃 | Richie Kotzen | 2 | | **[kredi]** Howe ile *Tilt*, *Project* | t=990479 |
| 〃 | Jimmy Herring · Joel Hoekstra · Mike Stern | 2 | | | t=1527703 · t=990479 |
| 〃 | GPS (*Window to the Soul*) | 1 | | **[kredi]** "Guthrie çalıyor" | t=990479 |
| 〃 | Steve Vai | 1 | B | [soy] "Guthrie'nin frazı Vai'ye çok yakın" | t=990479 |
| 〃 | Jennifer Batten (*Tribal Rage*) · Cosmosquad · Michael Landau · Bozzio Levin Stevens · Prashant Aswani · Richard Hallebeek · Pat Metheny | 1 | | albüm düzeyinde çoğu | t=990479 |
| 〃 | Shawn Lane + Jonas Hellborg | 1 | | **[kredi]** ortak kayıtlar | t=1527703 |
| 〃 | John McLaughlin · Christophe Godin · Chris Poland · James Muller · Mike Miller · John Scofield · Daniele Gottardo · T.J. Helmerich · Gabriel Marin | 1 | | | t=1527703 |
| Govan ama "daha az ileri" | Tom Quayle · Alex Machacek · Allen Hinds · Martin Miller · Alex Hutchings · Larry Carlton · Jeff Beck | 1 | | tek uzun liste | t=1670339 |
| Jimmy Herring | Allan Holdsworth | (OP kendi buldu) | + | [soy] "Herring'in büyük etkisi" | t=1410836 |
| Holdsworth · Herring | Guthrie Govan · Greg Howe · Scott Henderson · Dixie Dregs · Return to Forever · Jean-Luc Ponty · Pat Metheny | 1 | + (teşekkür) | "legato'larıyla bilinirler" | t=1410836 |
| Holdsworth [Ö] | Shawn Lane · Scott McGill · Ron Jarzombek · Fredrik Thordendal (*Sol Niger Within*) · Bill Connors · Alex Machacek · Brett Garsed · Francis Dunnery · Richard Hallebeek | ? | | özet | https://www.progarchives.com/forum/forum_posts.asp?TID=500 · https://sevenstring.org/threads/guitarists-that-have-assumed-someone-elses-style.19946/ · https://forums.stevehoffman.tv/threads/recommend-me-guitarists-like-bill-connors-allan-holdsworth-andy-summers.897792/ |

### 3.7 Japon füzyonu (zayıf; bkz. §5 S31)

| Tohum | Öneri | Onay | OP | Not | Kaynak |
|---|---|---:|:-:|---|---|
| "Japon caz/füzyon gitaristi" | Kazumi Watanabe · Issei Noro (Casiopea) · Takashi Masuzaki (Dimension) · Takeshi Hirai (eski Trix) · Masayoshi Takanaka · Tak Matsumoto · Char · Akira Takasaki | 1 | | tek liste; **[kredi]** grup üyeliğiyle tanıtılmış | https://www.ultimate-guitar.com/forum/showthread.php?t=1367790 |
| 〃 | Ryo Kawasaki · Tsuneo Imahori (Seatbelts) | 1 · 1 | | | t=1367790 |
| Casiopea · T-Square | Tetsuo Sakurai'nin Gentle Hearts'ı (Greg Howe, Dennis Chambers ile) | 1 küratör + 1 yeni dinleyici | + | **[kredi]** Casiopea basçısı | https://www.physicsforums.com/threads/todays-fusion-music-t-square-cassiopeia-rei-kanade-sato.1055897/ |
| 〃 | Senri Kawaguchi (Triangle) · Etsuji Ogawa · Koichi Yabori | 1 + 1 | + | | aynı iplik |
| 〃 | Rei/Suzaku · Jazz Avengers · D_Drive · Juna Serita (Tokyo Brass Style) · Kanade Sato | 1 | | tek küratör | aynı iplik (s. 1–4) |
| 〃 | Mahavishnu Orchestra · Tony Williams Lifetime · Steve Morse/Jerry Peek · Jeff Beck "Blue Wind" · Mike Stern | 1 | B (Beck) | "T-Square'in çoğu bana fazla smooth, 1994'teki kayıt ise yangın" — **dönem özgüllüğü** | aynı iplik s. 2 |
| Xaal · Sean Malone · DT *I&W* doğaçlamaları (**bas çalımı zorunlu**) | Kenso · Unit Wail · Lye By Mistake (*Fea Jur*) · Kopecky · Tenebris · The Fractured Dimension · Buzzard · Amogh Symphony (*Vectorscan*) · Serious Beak · Whoopgnash | 1 | | | https://forum.metal-archives.com/viewtopic.php?t=39353&start=720 |
| T-Square [Ö] | Jimsaku · Yuji Toriyama · Cory Wong | ? | | r/JazzFusion, yalnız özet | https://www.reddit.com/r/JazzFusion/comments/1861kae/ |
| Casiopea [Ö] | Kazumi Watanabe (*Mobo I/II*) · Masahiro Andoh · Takanaka · Kenso · Kennedy · Machine & the Synergistic Nuts · Mezzoforte; üslup kıyası Al Di Meola / Lee Ritenour | ? | | progarchives, yalnız özet | https://www.progarchives.com/forum/forum_posts.asp?TID=17870 |

### 3.8 Türkçe rock ve Türkçe rap

| Tohum | Öneri | Onay | OP | Not | Kaynak |
|---|---|---:|:-:|---|---|
| Duman | Kurban | 4 (1 karşı) | | biri "tarzı Duman gibi değil ama"; karşı: "cover'dan başka işe yaramaz" | https://forum.donanimhaber.com/duman-dan-baska-turk-rock-grubu-sarmiyor--52766610 |
| Duman | Şebnem Ferah | 3 | | biri: "şarkıları arasındaki benzerliğe bak" | aynı iplik |
| Duman | Pilli Bebek ("Siyah Beyaz") | 2 (+1 katılan) | | [söz/vokal] "böyle sözler, böyle vokal, böyle gitar solosu" | aynı iplik |
| Duman | Ogün Şanlısoy | 2 | | "bütün albümlerini dinle" | aynı iplik |
| Duman | Mor ve Ötesi · Kramp ("Lan Noldu") · Cem Karaca · Özlem Tekin · Demir Demirkan · Direc-t · Malt · Pinhani · Kargo (*Yalnızlık Mevsimi*) | 1 | | Kargo için "eski kadro" — **[kredi/dönem]** | aynı iplik |
| Duman | Teoman | 1 (tartışmalı) | | "o soft rock" | aynı iplik |
| Sagopa Kajmer + Ceza ("anlamlı, küfürlü değil") | İstanbul Attack | 2 (+1 katılan) | | "müzik ağırlıklı, arabada" — bağlam | https://forum.donanimhaber.com/sagopa-ve-ceza-dan-baska-iyi-turkce-rap-yapan-isimler-ariyorum--23240599 |
| 〃 | Cash Flow | 2 | | | aynı iplik |
| 〃 | Şanışer · Bela · Mode XL ("küfür nadir") · Kurşun (*Kapak Olsun*) · Yener · Fuat Ergin | 1 | | | aynı iplik |

**Çift değil, birliktelik verisi:** Uludağ "en iyi türk rock grupları" (25 entry):
Kurban 6, maNga 6, Mor ve Ötesi 4, Pentagram 4, Flört 4, Redd 3, Duman 3, Athena 2,
Malt 2, Neyse 2, Şebnem Ferah 2. Bir entry Kurban/Athena/Flört için "**arabesk ve
alaturkadan uzak**, arı bir Türkçe rock" diyor — Türk rock dinleyicisinin dil aynı
olsa bile arabesk/pop'u açıkça ayrı tuttuğunun kanıtı.
https://www.uludagsozluk.com/k/en-iyi-t%C3%BCrk-rock-gruplar%C4%B1/

### 3.9 Hip-hop

| Tohum | Öneri | Onay | OP | Not | Kaynak |
|---|---|---:|:-:|---|---|
| A Tribe Called Quest · De La Soul (konşiyöz) | Digable Planets (*Reachin'*) | 2 | | "Reachin' iyi başlangıç" | https://www.musicbanter.com/rap-hip-hop/49247-rap-hip-hop-recommendation-thread.html |
| 〃 | Black Sheep | 2 (+1 "bayıldım") | | "ATCQ'ya benzer, yaramaz bir bükülmeyle" | aynı iplik s. 1–2 |
| 〃 | The Roots · Common · Nas · Mos Def · Pete Rock · KMD · Fugees · Rakim · Dilated Peoples · Slum Village · Cypress Hill · Hadag Nahash | 1 | | Pete Rock bir **prodüktör** | aynı iplik s. 1–2 |
| Caz sample'lı hip-hop | Hieroglyphics (*Third Eye Vision*) · Slum Village (*Fan-Tas-Tic Vol. 2*) · Little Brother (*The Minstrel Show*) · The Pharcyde (*Bizarre Ride II*) · Nujabes · Jazz Liberatorz · Y Society | 1 | | **[ses/üretim]** "hepsi caz sample'ı ağır" | aynı iplik s. 30 |

### 3.10 Açık olumsuz / çelişkili çiftler (negatif etiket olarak değerli)

| Tohum | Öneri | Kim, ne dedi | Kaynak |
|---|---|---|---|
| Howe · Govan | Paul Gilbert, Jason Becker, Tony MacAlpine, Marty Friedman, Uli Jon Roth, Blackmore, Vinnie Moore | OP: "hepsini biliyorum, hiçbiri Howe/Govan'a benzemiyor" — **aynı tür, farklı üslup** | t=990479 |
| Tool | Karnivool · 10 Years | OP: "Tool benzerliği yok, Linkin Park gibi" (öbür iplikte Karnivool +1) | t=123705 vs t=1503817 |
| Meshuggah (+caz) | Textures | OP önceden denemiş, sevmemiş | t=87613 |
| AAL · Periphery | Cynic · Atheist | OP: vokal yüzünden dinleyemedi | t=1307546 |
| Gojira | Hacride | bir öneren +, bir başkası "kötü bir kopya" | t=80725 |
| AAL · Gru (arka plan) | Bongripper · Pelican (doom) | OP: "doom değil, hızlı istiyorum" | t=92820 |

### 3.11 Bu tablo test kümesi olarak nasıl kullanılır (K19 ile uyumlu öneri)

1. **Yalnız kütüphanedeki tohumlar.** Tohumu kullanıcının kütüphanesinde olan
   satırlar seçilir (Meshuggah, TOOL, Casiopea, Plini, Polyphia, Duman… ne varsa).
   Öneri sanatçısı kütüphanedeyse satır **atılır** (gerçek "zaten biliyorum").
2. **Tavan önce.** Her (tohum, öneri) için: öneri sanatçısı ilgili aday havuzunda
   (kredi, liste-PMI, ses, kalabalık) var mı? Bu, K19'un "kapsama mı sıralama mı"
   ayrımını dış kanıtla yapar.
3. **Ağırlık.** 100 çekirdek çift (68'i kullanıcının nişlerinde); tek onaylılar ikinci kademe.
   OP "+" = güçlü pozitif, OP "−" ve §3.10 = **negatif** (sıralamada üstte
   çıkmaları ceza). OP "B" satırları "keşif oranı" kalibrasyonu için.
4. **Ölçüt.** Tohum başına recall@k (k=10, 50) + negatiflerin ortalama sırası.
   Kıyas zorunlu: rastgele ve popülerlik taban çizgisiyle (K19).
5. **Sınır yazılır.** Forum 2009–2018, metal ağırlıklı, Batı forumu; J-füzyon ve
   hip-hop satırı az. Mutlak değer değil, **yöntemler arası kıyas** güvenilir.

---

## 4. Hacker News (tam iplik)

| İplik | Yorum | Ana bulgu |
|---|---:|---|
| "Spotify's Discover Weekly: How machine learning finds new music" — https://news.ycombinator.com/item?id=15447706 | 269 | 62 üst düzey yorumda ~8 memnun, ~12 olumsuz; ~5 Last.fm/Rdio'yu daha iyi buluyor; bağlam sızıntısı (iş, PS4, Norveç *russ* şarkıları) ~4; dil/ülke ~3; "gürültü/tuhaflık sürgüsü" ~3. Bir yorum: "ses analizi fazla sığ — insanlar ortak **armonik yapı ya da ritim** için dinler, aynı spektrum için değil." Bir başkası: "DW yanlış anlamasın diye bir türü dinlemekten korkuyorum." |
| "Why Spotify's Discover Weekly is getting really boring?" — https://news.ycombinator.com/item?id=12786653 | 51 | "8. haftadan sonra hep aynı tını"; bir yorum: caz dinleyicisinin vektörü daha özgül olduğu için DW cazcılara daha iyi çalışır — **niş zevk daha kolay hedef** sezgisi. |
| "Ask HN: How do you discover new music?" — https://news.ycombinator.com/item?id=32840864 | 51 | Albüm odaklı, çevrimdışı oynatıcıyla dinleyen biri (kullanıcının DAP profili): "dinleme geçmişim dışında bir şeye bağımlıyım" → küçük inceleme siteleri RSS, niş label'ları Bandcamp'ta takip, niş subreddit. Başka biri: "bir sanatçı seç, **üyelerine, label'ına, Wikipedia'sına, kayıt mühendisine** bak". |
| "Ask HN: How do you find new music?" — https://news.ycombinator.com/item?id=35993740 · https://news.ycombinator.com/item?id=42788152 | 28 | Radyo/insan küratörlüğü, RYM ve Sputnik listeleri, "metal-archives tavşan delikleri", Wikipedia "20XX in heavy metal" sayfaları; rock belgeselinde anılan **çağdaşlar ve etkiler**. |
| Every Noise at Once — https://news.ycombinator.com/item?id=26668426 · kapanış https://news.ycombinator.com/item?id=39351347 | 131 | "Sevdiğim bir alt türün **adını öğrenmek**" en sık övgü; "benzer ama farklı bulmayı kolaylaştırmıyorlar" şikâyeti; kapanışta "kültürel açıdan önemli bir veri" yası. |
| YouTube Music yorum araması (30 yorum) — ör. https://news.ycombinator.com/item?id=25073571 · https://news.ycombinator.com/item?id=48296715 | 30 | ~10 olumsuz (Ra Ra Rasputin çekeri, izlenen videoların oylarını içe aktarma, konum/hava durumu), ~8 olumlu, ~4 "Batı dışı müzikte arşiv çok daha iyi". 2026'dan bir yorum, kullanıcının kendi profilini anlatıyor: büyük kütüphane, kısa hafıza, son dinlenene aşırı ağırlık, "top songs" — deep cut yok, sonunda "albümleri baştan sona çalıyorum". |
| ListenBrainz | — | ListenBrainz için yalnız teknik iplikler var (TimescaleDB'ye geçiş, servis kesintileri); öneri kalitesi tartışılmamış. Proje için anlamı: LB benzer-sanatçı uç noktası hakkında **dış kullanıcı kanıtı yok**, kendi ölçümümüz tek dayanak. |

---

## 5. Türkçe kaynaklar

- **Ekşi Sözlük bu oturumdan okunamadı (403).** Başlık adları bile tema veriyor
  ([Ö]): "haftalık keşif", "spotify algoritması", "spotify'ın aynı şarkıyı tekrar
  önermesi", "spotify'ın satılık müzik listeleri", "youtube music vs spotify",
  "son 10 yılın en iyi türk rock müzik grubu", "anadolu rock".
  https://eksisozluk.com/haftalik-kesif--4874896 · https://eksisozluk.com/spotifyin-ayni-sarkiyi-tekrar-onermesi--7290087 · https://eksisozluk.com/spotifyin-satilik-muzik-listeleri--6163057
- **Technopat (403, [Ö]):** "Haftalık keşifte alakasız şarkılar" — neredeyse hiç
  Türkçe dinlemeyen kullanıcının listesi Türkçe dolmuş; Arapça müzik tekrar
  tekrar geliyor. Önceki raporun "hesap ülkesi Türkiye ise bu yüzden" bulgusunu
  bir kez daha doğruluyor. https://www.technopat.net/sosyal/konu/spotify-haftalik-kesifte-alakasiz-sarkilarin-cikmasi.2212258/
- **DonanımHaber (tam metin):**
  - "Spotify'da nasıl yeni müzik keşfediyosunuz?" — "dinlediğim gruplara benzer
    sanatçı bulmak istiyorum ama Daily Mix hep aynı; ruh hâli listeleri de belli
    başlı 40–50 şarkı". Cevaplar: Haftalık Keşif, radyo, tür listeleri, gnoosic.
    https://forum.donanimhaber.com/spotify-da-nasil-yeni-muzik-kesfediyosunuz--130153443
  - "Spotify'da sürekli aynı şarkıları dinlemek" — aynı kişi: "10–20 şarkılık
    liste dönüyor; yeni bir şey açsam da beğenmeyeceğim, beğenmediğimi neden
    zorla dinleyeyim" — **kötü önerinin maliyetinden kaçınan** dinleyici; kullanıcının
    "DAP'tan kendi kütüphanemi dinliyorum" cümlesinin akrabası.
    https://forum.donanimhaber.com/spotifyda-surekli-ayni-sarkilari-dinlemek--150846817
  - "Youtube Music vs Spotify", "Spotify mı YT Music mi?" — YTM'yi seçenlerin
    gerekçesi öneri değil **arşiv**: kullanıcı yüklemeleri, Spotify'da olmayanlar,
    canlı/remix. Spotify'ı seçenler arayüz ve öneri; bir kullanıcı 2017'den beri
    441 parçalık Türkçe rap listesi tutuyor.
    https://forum.donanimhaber.com/youtube-music-vs-spotify--146093022 ·
    https://forum.donanimhaber.com/spotify-mi-yt-music-mi--158712179
- **Türk rock'ta benzerlik dili** (DH Duman ipliği 47 cevap + Uludağ):
  prog/füzyondan farklı olarak ölçüt **söz, duygu, vokal** ("şarkıları o kadar
  anlamlı", "böyle sözler, böyle vokal performansı"); tartışmanın yarısı **etiket**
  üzerine (grunge mu, blues mu, "arabesk rock" mu — "Kaan'ın sesinden kaynaklanan
  bir algı"). Bir de **kimlik/utanç** katmanı var ("Duman ergen müziği" —
  "bu tribden çıkın"). Kadro dili yine var: Kurban'ın davulcusu ve basçısı, Pentagram'ın
  Murat İlkan dönemi, Kargo'nun eski kadrosu, Blues Blues Band ve Yavuz Çetin.
- **Türkçe rap:** dil **açık bir seçim** ("Türkçe olmak zorunda mı?" → "anlamak
  için Türkçe"), içerik kısıtı ("küfürlü değil").

---

## 6. Tasarım sezgileri — güncelleme (önceki S1–S18'e ek)

Her biri **hipotez**; yanında ölçüm (K19). Önceki raporla ilişki parantez içinde.

**S19 — "Zaten biliyorum" yüksek olmak zorunda; hedefi buna göre koy.**
Kanıt: §2, insan uzmanların önerisinde ~%45 (en bilgili OP'de %62–83).
Kural: keşif oranı için "%15 altı" gibi bir hedef (S1) gerçekçi değil; insan
tavanı ~%55 yeni. Ölçüm: strateji başına "zaten biliyorum" oranı, insan tablosundaki
B oranıyla birlikte raporlanır; ayrıca **yeni** kartlarda beğenme oranı (insan ~%61)
ayrı payda.

**S20 — Kadro/kredi ilişkisini ilk sınıf kenar yap: üye, yan proje, ortak kayıt, prodüktör.**
Kanıt: §1.1, 24 kredi gerekçeli öneri; metal, füzyon ve Türk rock'ta aynı dil.
Kural: "X grubunun üyesi Y'de de çalıyor" (MusicBrainz *member of band*),
"yan proje", "ortak albüm" (Howe–Kotzen), "prodüktörü" (Trepallium) ayrı kenar türleri;
kartta türü yazılsın ("iki Cynic üyesi"). Ölçüm: bu kenar türlerinin tablodaki
çekirdek çiftleri ne kadar geri getirdiği (tavan + recall), kenar türüne göre ayrı.
(S7'yi güçlendirir.)

**S21 — Vokal bir veto eksenidir; ölç ve filtre olarak sun.**
Kanıt: §1.1'de 20 iplikte vokal ölçüt/veto; §3.10'da vokal yüzünden ret.
Kural: K12 `vocals` stem'inden "sert vokal" göstergesi (düşük harmonik pay,
düşük perde güveni) albüm düzeyinde; destede "sert vokal yok" anahtarı; "tutmadı"
sonrası isteğe bağlı neden düğmesi (vokal / tempo / ton / fazla zor / alt tür).
Ölçüm: neden etiketli retlerin dağılımı; "vokal" retlerinin göstergeyle ilişkisi
(AUC). Gösterge tutmuyorsa arayüze girmez (söz verme ilkesi).

**S22 — İstek = çoklu tohum + nitelik + olumsuz kısıt.**
Kanıt: §1.2 (~20/25 nitelikli, ~11/25 olumsuz kısıtlı).
Kural: eksen seçiminin yanına "şunu da istiyorum" (stem ölçütünden: "bas önde",
"davul yoğun", "tempo hızlı") ve "şunu istemiyorum" (bir kütüphane albümü ya da
tarz) alanları. Olumsuz kısıt sert filtre değil, skor cezası.
Ölçüm: kısıtlı ve kısıtsız destelerin zevk isabeti (eşleştirilmiş tohumla).

**S23 — Öneri albüm ve dönemle gelir; karar sanatçı düzeyinde olsa bile.**
Kanıt: §1.1'de 41 ileti albüm/dönem özgüllüğü; "T-Square'in çoğu fazla smooth ama
1994'teki yangın"; "Scariot'un her albümü bambaşka"; "Awake'ten sonra";
"Murat İlkan'lı zamanlar"; "Kargo'nun eski kadrosu".
Kural: kart sanatçıyı değil **giriş albümünü** önerir (kanıtın geldiği albüm);
K21'in sanatçı düzeyindeki "tutmadı"sı, dönemi çok değişen sanatçıda yanlış
genelleme yapabilir. Ölçüm: aynı sanatçının albümleri arasında ses/stem
profili varyansı (sanatçı içi / sanatçılar arası); yüksek varyanslı sanatçılarda
"tutmadı" kararının ikinci bir albümle sınanması **önce ölçülür**, sonra karar.

**S24 — "Kaynağa git" (etki soyu) önerileri çok onay alır ama sık reddedilir.**
Kanıt: Holdsworth 5 onay, 2/2 OP ret; Cynic/Atheist 2 onay, OP ret;
"edinilmiş zevk, viski gibi".
Kural: etki soyunu ayrı bir kanıt ailesi say ve **uzlaşma** puanına doğrudan
katma (K21 2026-10-20 uzlaşma kuralı). Kartta "zorlu dinleme" uyarısı +
erişilebilir giriş parçası. Ölçüm: etki-soyu kaynaklı kartların isabeti ayrı; insan
tablosunda "onay sayısı ↔ OP +" ilişkisi (bu veride zayıf: Exivious 7 kişi +,
Holdsworth 5 kişi −).

**S25 — "Aynı tür, ünlü isim" tembel benzerliğini cezalandır.**
Kanıt: Howe/Govan OP'sine 7 shred ismi → "hepsini biliyorum, hiçbiri benzemiyor".
Kural: popülerlik sönümü (S10) yetmez; öneri **ayırt edici nitelikte** (legato,
füzyon armonisi, `other` stem'inde perde aralığı/sustain) tohuma yakın olmalı,
tür etiketinde değil. Ölçüm: §3.10 negatiflerinin motor sıralamasındaki yeri.

**S26 — Eksene göre benzerlik dili değişir: prog/füzyonda icra, Türk rock ve rap'te söz/duygu/vokal ve dil.**
Kanıt: §5; "arabesk ve alaturkadan uzak arı Türkçe rock"; "anlamak için Türkçe".
Kural: eksen başına gerekçe şablonu ayrı (Türk rock'ta kadro + vokal + dönem;
prog'da icra + kadro). Dil açık seçim olsun (S5); **"Türkçe" ≠ "Türk rock"** —
liste/CLAP sinyalinde arabesk/pop'a karşı bir negatif çapa (Sezen Aksu vakası).
Ölçüm: Türk rock ekseninde arabesk/pop sanatçılarının deste payı, çapalı/çapasız.

**S27 — Tür etiketi kartın en tartışmalı cümlesidir.**
Kanıt: 47 ileti / 16 iplik etiket kavgası.
Kural: kartta tür adı iddia olarak değil, kaynak etiketi olarak ("MusicBrainz'e göre")
yazılır; benzerlik iddiası kişi/ses sayısıyla kurulur (K18 ile tutarlı).

**S28 — Uzlaşma ≠ uyum; uzlaşma kuralını bu tabloyla ölç.**
Kanıt: çok onaylı Holdsworth reddedildi; tek onaylı Ever Forthright "bayıldım";
Karnivool iki iplikte çelişkili.
Kural: K21'in "birden çok kanıt ailesi öne alınır" kuralı için `kesif.uzlasma_isabeti`
ölçümüne ek olarak bu tabloda: onay sayısı kovası (1 / 2 / ≥3) başına motorun
geri getirme oranı ve OP + oranı.

**S29 — İşlev bağlamı istekte de var; çalma listesi bağlamıyla aynı aile.**
Kanıt: "ders çalışırken arka plan", "arabada", "uzun yol"; HN'de iş/oyun sızıntısı.
Kural: K16'daki bağlam etiketi bir istek seçeneği olabilir ("arka plan için") ama
stil eksenine karışmaz (S6). Ölçüm: yok — önce kullanıcı ister mi diye sorulur.

**S30 — Büyük kütüphaneli albüm dinleyicisinin dört şikâyeti tasarım şartı.**
Kanıt: HN 48296715, 32840864 (kullanıcının profiliyle birebir).
Kural: (a) kalıcı hafıza — sahip olunan ve "biliyorum" denen asla "keşif" olmaz
(K17, var); (b) son dinlenene aşırı ağırlık yok (K21 kararları zaman ağırlıksız mı,
bakılmalı); (c) önizleme "en popüler parça" değil kanıt parçası (S11); (d) öneri
birimi albüm (S23).

**S31 — J-füzyonda insan kanıtı ince ve tek küratörlü; kredi grafiği asıl yol.**
Kanıt: §3.7 — erişilebilir forumlarda J-füzyon çifti çoğunlukla tek kişiden;
zengin yerler (r/JazzFusion, progarchives, Steve Hoffman) giriş/bot duvarında.
Buna karşın verilen gerekçeler hep kadro: "Casiopea basçısının grubu", "eski Trix",
"Dimension'dan".
Kural: bu eksende forum çiftleri "zayıf kanıt"; test kümesini kullanıcı kendisi
10–15 tohumla elle kurar (Casiopea → ?, T-Square → ?, Takanaka → ?). Kredi
grafiğinde Casiopea/T-Square/Trix/Dimension/Jimsaku/Casiopea-P4 kadro ağının
kapsaması ayrıca ölçülür (Discogs'ta Japon baskıların kredileri).

**S32 — "İlk izlenim yanıltır" — 30 sn kararının gürültüsü ölçülmeli.**
Kanıt: "Unexpect'ten yıllarca nefret ettim, bir şarkısının şemasını çıkarınca
sevdim"; "ilk parça harika, üç parça sonra kimse indirmesin"; Holdsworth "edinilmiş
zevk".
Kural: K21'de "tutmadı" kalıcı; bunu değiştirmeden önce ölçüm: "tutmadı" denilen
sanatçının daha sonra başka yoldan Listem'e eklenme oranı. Oran anlamlıysa "şimdilik
geç" gibi yumuşak bir yön düşünülür; değilse hiçbir şey değişmez.

**S33 — Popüler bir tohumda insan önerisi de "bilinen"e kayar; niş tohumda daha isabetli.**
Kanıt: Govan seedi %83 B; Obscura/Gojira/AAL gibi niş seedlerde B ~0, + yüksek.
HN: "caz dinleyicisinin vektörü daha özgül".
Kural: tohumun popülerliği kartın kanıt gücünü etkiler; popüler tohumdan gelen kart
için "zaten biliyorum" beklentisi yüksek. Ölçüm: tohum popülerlik dilimine göre
"biliyorum" oranı.

---

## 7. Kısa sentez

1. İnsanlar benzerliği en çok **icra/ritim**, sonra **vokal**, **atmosfer**,
   **albüm/dönem** ve **etki soyu** üzerinden kuruyor; tür etiketi çoğunlukla
   kavga konusu. Kadro gerekçesi sayıca az ama en ikna edici ve her türde aynı dil.
2. Forumdaki OP kararları K21'in üç yönünün doğal oranlarını veriyor:
   **~%45 "biliyorum", yenilerin ~%61'i beğeni.** "Bildiğimi önerme" yalnız
   algoritmanın değil, uzman dinleyiciye öneri yapmanın yapısal sorunu.
3. Algoritma şikâyetleri önceki raporla tutarlı (tekrar, jenerik, bağlam ve dil
   sızıntısı, son dinlenene aşırı ağırlık); yeni olan, **büyük kütüphaneli albüm
   dinleyicisinin** bunları tam kullanıcının profilinde dile getirmesi.
4. Test kümesi: **263 çift, 100'ü çekirdek** (68'i kullanıcının nişlerinde), 6 açık
   negatif satır; teknik/prog metal ve gitar tarafında güçlü, J-füzyon (5 çekirdek)
   ve hip-hop (2 çekirdek) tarafında ince. J-füzyon için
   kullanıcının kendi el yapımı çiftleri gerekiyor.

---

## 8. Kaynaklar (tam metin okunanlar)

**Encyclopaedia Metallum forumu**
- https://forum.metal-archives.com/viewtopic.php?t=113959 (Meshuggah gibi)
- https://forum.metal-archives.com/viewtopic.php?t=87613 (Poliritim)
- https://forum.metal-archives.com/viewtopic.php?t=63469 (Cynic, Atheist gibi)
- https://forum.metal-archives.com/viewtopic.php?t=61976 (prog death/thrash, tuhaf ölçüler)
- https://forum.metal-archives.com/viewtopic.php?t=91621 (Amogh Symphony, AAL gibi)
- https://forum.metal-archives.com/viewtopic.php?t=54023 (Obscura gibi)
- https://forum.metal-archives.com/viewtopic.php?t=80725 (Gojira gibi)
- https://forum.metal-archives.com/viewtopic.php?t=62505 (tech wank)
- https://forum.metal-archives.com/viewtopic.php?t=91925 (Tech death/prog)
- https://forum.metal-archives.com/viewtopic.php?t=118934 (melodik gitar enstrümantal)
- https://forum.metal-archives.com/viewtopic.php?t=92820 (enstrümantal gruplar)
- https://forum.metal-archives.com/viewtopic.php?t=39353&start=720 · &start=760 (Prog yardım ipliği s. 19–20)
- https://forum.metal-archives.com/viewtopic.php?t=123705 (Tool etkili gruplar)

**Ultimate-Guitar forumu**
- https://www.ultimate-guitar.com/forum/showthread.php?t=1702554 (enstrümantal metal)
- https://www.ultimate-guitar.com/forum/showthread.php?t=1367790 (Japon caz/füzyon gitaristi)
- https://www.ultimate-guitar.com/forum/showthread.php?t=1527703 (Govan, Lane, Howe gibi)
- https://www.ultimate-guitar.com/forum/showthread.php?t=1670339 (Govan gibi ama daha az ileri)
- https://www.ultimate-guitar.com/forum/showthread.php?t=990479 (Howe/Govan'a benzeyen gitaristler)
- https://www.ultimate-guitar.com/forum/showthread.php?t=1410836 (Allan Holdsworth)
- https://www.ultimate-guitar.com/forum/showthread.php?t=1307546 (caz/metal füzyon üslubu)
- https://www.ultimate-guitar.com/forum/showthread.php?t=1503817 (Tool/APC/Isis gibi)

**Türkçe**
- https://forum.donanimhaber.com/duman-dan-baska-turk-rock-grubu-sarmiyor--52766610 (3 sayfa)
- https://forum.donanimhaber.com/sagopa-ve-ceza-dan-baska-iyi-turkce-rap-yapan-isimler-ariyorum--23240599 (s. 1)
- https://forum.donanimhaber.com/spotify-da-nasil-yeni-muzik-kesfediyosunuz--130153443
- https://forum.donanimhaber.com/spotifyda-surekli-ayni-sarkilari-dinlemek--150846817
- https://forum.donanimhaber.com/youtube-music-vs-spotify--146093022
- https://forum.donanimhaber.com/spotify-mi-yt-music-mi--158712179
- https://www.uludagsozluk.com/k/en-iyi-t%C3%BCrk-rock-gruplar%C4%B1/

**Diğer**
- https://www.musicbanter.com/rap-hip-hop/49247-rap-hip-hop-recommendation-thread.html (s. 1, 2, 30, 90)
- https://www.musicbanter.com/rap-hip-hop/102137-rap-beats-do-half-storytelling.html
- https://www.physicsforums.com/threads/todays-fusion-music-t-square-cassiopeia-rei-kanade-sato.1055897/ (s. 1, 2, 4)
- HN: https://news.ycombinator.com/item?id=15447706 · https://news.ycombinator.com/item?id=12786653 · https://news.ycombinator.com/item?id=32840864 · https://news.ycombinator.com/item?id=35993740 · https://news.ycombinator.com/item?id=42788152 · https://news.ycombinator.com/item?id=26668426 · https://news.ycombinator.com/item?id=39351347 · https://news.ycombinator.com/item?id=25073571 · https://news.ycombinator.com/item?id=48296715

**Yalnız özet düzeyinde görülenler [Ö]** — okunamadı, onay sayısı yok:
r/JazzFusion 1861kae; progarchives TID=17870, 500, 71025; Steve Hoffman 897792,
1188811; sevenstring 94661, 38372, 110369, 19946; technopat 2212258; Ekşi
"haftalık keşif", "spotify'ın aynı şarkıyı tekrar önermesi", "spotify'ın satılık
müzik listeleri".
