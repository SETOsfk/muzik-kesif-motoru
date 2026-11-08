# 10 — Kaynak doğrulama: kullanım şartları birebir alıntı + kapsama ölçümü

*Tarih: 2026-10-20. Önceki rapor (`5-acik-veri-kaynaklari.md`) [H]/[İ] etiketli iddialarını resmi metinden
doğrulamak için yazıldı. Depoya hiçbir şey yazılmadı; ham sayfalar, betikler ve JSON çıktıları
`scratchpad/dogrulama/` altında.*

---

## 0. Yöntem ve sınırlar

- Sayfalar `curl` ile çekildi (vekil üzerinden), HTML satır içi Python ile metne çevrildi.
  Her istekte User-Agent `muzik-kesif-motoru/0.2 ( https://github.com/SETOsfk/muzik-kesif-motoru )`.
  Hiçbir istekte e-posta adresi yok.
- Hız: MusicBrainz 1,2 sn aralık (toplam 17 istek), ListenBrainz 1,5 sn (4 istek), Wikidata SPARQL
  2 sorgu, Deezer 6 istek (0,5 sn), AcousticBrainz 3 istek, Discogs API 1 istek.
- **Okunamayanlar (aşılmadı):**
  - `support.discogs.com` HTML'i Cloudflare "Just a moment…" sınamasıyla 403 verdi. Aynı makale
    Discogs yardım merkezinin herkese açık Zendesk makale API'sinden okundu:
    `https://support.discogs.com/api/v2/help_center/en-us/articles/360009334593.json`
    (makale kimliği aynı, `html_url` resmi sayfayı gösteriyor, `updated_at` 2025-07-23).
    `www.discogs.com/developers` aynı sınama yüzünden okunamadı.
  - `docs.genius.com` ve `genius.com/static/terms`: "make sure you're a human" sınaması (403).
    Aşılmadı → Genius şartları **doğrulanamadı**.
  - `developers.deezer.com/api/...` belge sayfaları artık girişe yönlendiriyor (aşağıda).
  - Wayback Machine (archive.org) önce 429, sonra bağlantı sıfırlama verdi; yedek olarak kullanılamadı.

**Etiketler:** **[B]** = bu oturumda birincil kaynaktan okundu (alıntı aşağıda) · **[Ö]** = bu oturumda
ölçüldü (canlı istek) · **[D]** = doğrulanamadı.

---

## 1. Hüküm tablosu (K5 "her şey kalıcı önbelleklenir" ile uyum)

| Kaynak | Lisans | K5 kalıcı önbellek | Hız sınırı | Atıf | Hüküm |
|---|---|---|---|---|---|
| MusicBrainz API | Çekirdek (ilişkiler dahil) CC0; etiket/tür/puan CC BY-NC-SA 3.0 [B] | **Uyumlu** (çekirdek) | IP başına ort. 1/sn; aşılırsa isteklerin %100'ü reddedilir [B] | Ek veri için zorunlu (BY) | Kullan. Ek veri (tür/etiket) gösterilirken kaynak yazılmalı |
| Discogs **API** | Krediler "CC0 Data" sınıfında [B] **ama** API şartları ayrı sözleşme | **UYUMSUZ** (§4: 6 saat + "gerekenden uzun saklanamaz", tüm Content için) [B] | Token'sız 25/dk [Ö başlık]; token'lı 60/dk [D] | Her verinin yanında "Data provided by Discogs." + bağlantı, uygulamada bağımsızlık bildirimi [B] | Kalıcı önbellek ve atıfsız gösterim şartlara aykırı. **Dump'a geç** |
| Discogs **dump** | "CC0 No Rights Reserved" [B] | **Uyumlu** | Yok (dosya) | Gerekmez | Kredilerin asıl kaynağı olmalı |
| Wikidata / WDQS | Yapısal veri CC0 [B] | **Uyumlu** | 60 sn/sorgu; UA+IP başına dakikada 60 sn işlem; 30 hatalı sorgu/dk; IP başına 5 paralel [B] | Gerekmez | Kullan (ülke/tür/kimlik). **Etki (P737) için yetersiz** [Ö] |
| Last.fm API | Kendi lisansı; yalnız ticari olmayan [B] | **UYUMSUZ** (toplam ≤100 MB, önbellek HTTP başlıklarına göre, lisans "temporary") [B] | Sayısal değer yok; "saniyede birkaç çağrı" askıya alma sebebi [B] | Last.fm'e atıf + katalog bağlantısı + "powered by AudioScrobbler" düğmesi; **herkese açık sayfa için yazılı onay** [B] | Ancak koşullarla; yayına açılmadan önce Last.fm'e yazılmalı |
| ListenBrainz (API + labs) | Dump'lar CC0 1.0 [B kaynak kod]; ToS = MetaBrainz sosyal sözleşmesi [B] | **Uyumlu** | "Her istemci saniyede BİR çağrıyı asla aşmaz" [B] | Belirtilmemiş | Kullan; projenin istemcisi şu an kuralı aşıyor (§4) |
| AcousticBrainz | CC0 [B] | **Uyumlu** | X-RateLimit: pencere başına 100 [Ö] | Gerekmez | API hâlâ açık [Ö], "şimdilik" [B]. Dump sigortası önerisi geçerli |
| Deezer API | Deezer'in kendi şartları; yalnız ticari olmayan, "kişisel uygulama" [B] | Metin verisi için madde yok. **Ses verisini yerelde saklamak "strictly forbidden"** [B] | Belgede bulunamadı [D] | Logo/marka kuralları | Metin verisi için kullan; ses/stem önbelleği riskli (§4) |
| Setlist.fm API | Kendi şartları; yalnız ticari olmayan [B] | **UYUMSUZ** ("yalnız kısa süreli önbellek") [B] | Belgede sayı yok; "oranı sınırlama hakkı saklı" [B] | Her yerde atıf bağlantısı, nofollow yok [B] | Eklenirse TTL'li ayrı önbellek gerekir |
| Genius API | [D] | [D] | [D] | [D] | Şartlar okunamadı → eklenmez |

---

## 2. Birebir alıntılar

### 2.1 Discogs API Terms of Use

URL: <https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use>
("Last Updated: May 27th, 2025"; makale kaydı `updated_at` 2025-07-23)

**CC0 Data sınıfı (krediler burada):**
> "CC0 Data: The Content includes the following JSON- and XML-formatted, CC0 data (the "CC0 Data"):
> Release titles, notes, dates, format, track listings, barcodes and other identifiers, **credits**, versions,
> URL links to third-party sites · Artist names, notes, associated releases · Label, producer, manufacturer,
> distributor, etc. names and contact information, notes, and associated releases"

**Restricted Data:** "Discogs User Data" (kullanıcı adı, koleksiyon, istek listesi…), "Marketplace Data"
(fiyat, satış geçmişi…), "Images" (release/artist/label/user görselleri).

**Önbellek / tazelik maddesi (kritik):**
> "The Content within Our API is dynamic and is quickly outdated. You may not display in any format or to any
> audience the Content if it is more than six (6) hours older than the information on Our online properties
> or applications and applications. You may not cache or store the Content longer than is necessary to
> provide a service to Your application's users."

**Bu madde yalnız Restricted Data'ya mı?** Hayır. HTML yapısına bakıldı: Restricted Data kuralları
`<ol start="3">` altında iç içe liste; 6 saat maddesi ise ayrı bir `<ol start="4">` maddesi, yani
bölümün kendi maddesi. "Content" en başta "data made available through Our API" olarak tanımlanıyor ve
CC0 Data'yı da kapsıyor. **Sonuç:** API'den çekilip kalıcı tutulan Discogs kredileri bu maddeyle
çatışıyor. CC0 telif hakkından vazgeçiyor, ama API şartları ayrı bir sözleşme olarak bağlayıcı. Temkinli
okuma budur. Temiz yol dump.

**Atıf (zorunlu):**
> "We require You to display the following notice prominently on Your application …: "This application uses
> Discogs' API but is not affiliated with, sponsored or endorsed by Discogs. 'Discogs' is a trademark of Zink
> Media, LLC." This notice may be included in Your terms and conditions or usage documentation."

> "In addition, You must display the following notice directly next to any data You use from the Discogs API:
> "Data provided by Discogs." The notice must include a hyperlink to the discogs.com page that includes the
> data. The link back must not use any mechanism that prevents passing along search engine ranking credit to
> that page, such as 'nofollow'."

**Ticari kullanım:** "Commercial use of Our API and the Content is generally permitted, but may not be
permitted, if, in Our sole discretion …". Projeyi etkilemiyor.

**Hız:** API yanıt başlığı `x-discogs-ratelimit: 25` (token'sız, dakikada) [Ö]. Aynı yanıtta
`x-discogs-ratelimit-used: 16` vardı. Vekilin çıkış IP'si paylaşılıyor, yani sayaç bize ait değil.
Token'lı 60/dk değeri geliştirici sayfasında, o sayfa okunamadı [D].

### 2.2 Discogs veri dump'ları

URL: <https://data.discogs.com/>
> "Here you will find monthly dumps of Discogs Release, Artist, Label, and Master Release data. The data is
> in XML format and formatted according to the API spec … This data is made available under the CC0 No
> Rights Reserved license: http://creativecommons.org/about/cc0"

Güncel dosyalar [Ö, `?prefix=data/2026/` listesi]:

| Dosya | 2026-09-01 | 2026-10-01 |
|---|---|---|
| `releases.xml.gz` | 10,5 GB | 10,5 GB |
| `masters.xml.gz` | 596,8 MB | 600,5 MB |
| `artists.xml.gz` | 474,1 MB | 475,7 MB |
| `labels.xml.gz` | 86,4 MB | 87,0 MB |
| `CHECKSUM.txt` | 388 B | 388 B |

### 2.3 Last.fm API Terms of Service

URL: <https://www.last.fm/api/tos> (sayfada sürüm tarihi yok; altbilgi "© 2026")

Sayfa başı:
> "If you are planning to use our API for commercial or research/academic purposes, or have any questions about
> the license terms, please drop us a line prior to use via email at partners [at] last [dot] fm"

> **3.1** "You are permitted to use the Last.fm Data solely for non-commercial purposes and for no other purpose
> and subject always to any limitations or conditions as advised to You by Last.fm at any time."

> **4.3.4 (önbellek + tavan):** "… the licence granted to You is temporary and restricted to a small portion of
> Last.fm Data available via the API, not to exceed the Reasonable Usage Cap in total at any time. Any use,
> storage, publication, distribution, communication, making available or otherwise of Last.fm Data in excess
> of the Reasonable Usage Cap is strictly prohibited. The "Reasonable Usage Cap" is a maximum of 100 MB, as
> may be updated by Last.fm from time to time. … You will implement suitable caching in accordance with the
> HTTP headers sent with web service responses."

> **2.7 (atıf + yayın onayı):** "You agree to use one of the buttons saying "powered by AudioScrobbler" … such
> button linking back to Last.fm. … All links to Last.fm from pages displaying information on an artist, album
> or track should link to the appropriate catalogue page on Last.fm. … All button/link placements are subject
> to approval by Last.fm … **You agree to only give public access to pages using Last.fm's web services that
> have been previously approved by Last.fm in writing.**"

> **4.3.3** "You must not sub-license the Last.fm Data to a third party"

> **4.4 (hız):** "Last.fm sets and enforces limits on use of the API … (e.g. limiting the number of API requests
> that you may make or the number of users you may serve), in our sole discretion."

> **5.1.8** "You will not use any audio, audiovisual, images and/or artwork, whether or not accessible through
> the API, and all such content is expressly excluded from this Agreement"

> **2.3** "… provided that if You live in a country outside the European Economic Area, You may only use and
> access and use Last.fm data in that country if Users have expressly given their permission for You to do so
> when they registered as a User." Kullanıcı Türkiye'de, yani AEA dışında. Madde belirsiz; büyük
> olasılıkla Last.fm kullanıcılarının kişisel verisi için yazılmış.

<https://www.last.fm/api/intro>:
> "Please use an identifiable User-Agent header on all requests. … Your account may be suspended if your
> application is continuously making several calls per second or if you're making excessive calls."

**Önceki raporun düzeltmeleri:**
- "IP başına 5 istek/sn" güncel metinde **yok**.
- "Benzer veri ≥1 hafta önbellek" maddesi güncel metinde **yok**. Yerine "HTTP başlıklarına göre önbellek" var.
- "100 MB tavanı" **doğrulandı** (§4.3.4).
- Önceki raporda olmayan yeni bulgu: herkese açık sayfa için yazılı onay şartı (§2.7). Uygulama Tailscale
  Funnel ile internete açık; girişle korunuyor ama "public access" tanımı belirsiz.

### 2.4 ListenBrainz / MetaBrainz

API belgesi: <https://listenbrainz.readthedocs.io/en/latest/users/api/index.html>
> "All users of the API must ensure that each of their client applications never make more than ONE call per
> second."
> "If the client exceeds the number of requests allowed, the server will respond with error code 429 … Requests
> that provide the Authorization header with a valid user token may receive higher rate limits"
> "We require that all requests to the ListenBrainz API include a valid User-Agent header, with enough
> information for us (MetaBrainz) to contact the application maintainers. … Requests without a valid user
> agent may be blocked without further notice as collateral damage in our fight against scrapers and botnets."
> Biçim: "Application name/<version> ( contact-url )" ya da "( contact-email )".

Kullanım şartları: LB'nin kendi ToS sayfası kaynak kodda (`frontend/js/src/about/terms-of-service/TermsOfService.tsx`):
> "ListenBrainz' terms of service are defined by the social contract and privacy policies of the Foundation."

MetaBrainz sosyal sözleşmesi (<https://metabrainz.org/social-contract>):
> "The factual database content will be in the public domain and the non-factual database content will be
> released under Creative Commons licenses." · "This contract is not a legally binding contract; for legal
> information … please consult the license pages of the specific project."

MetaBrainz veri kümeleri (<https://metabrainz.org/datasets>):
> "We ask commercial supporters to support us … Personal use of our datasets will always be free."

**Dump lisansı:** Belge sayfası lisans söylemiyor. Ama dump üreticisi `listenbrainz/dumps/exporter.py`,
`DUMP_LICENSE_FILE_PATH = …/db/licenses/COPYING-PublicDomain` dosyasını arşive koyuyor. Bu dosyanın
içeriği "CC0 1.0 Universal" [B, raw.githubusercontent.com].

**Dump boyutu** [Ö, `data.musicbrainz.org/pub/musicbrainz/listenbrainz/fullexport/`, 2026-10-15]:
- listens dump: **233 GB**
- spark dump: 232 GB
- statistics: 23 GB

Önceki raporun "M1 Mac'te ağır" notu doğru, hatta hafif kalıyor.

**labs similar-artists:** <https://labs.api.listenbrainz.org/> dizininde `similar-artists` hâlâ listeleniyor
[B]. Token'sız 4/4 istek 200 döndü (aşağıda §3.3). Yanıtta `X-RateLimit-*` başlığı yok.

### 2.5 MusicBrainz

Lisans: <https://musicbrainz.org/doc/About/Data_License>
> "Core data: The core data of the database is licensed under the CC0 … No restrictions, no worries!"
> "Supplementary data: The remaining portions of the database are released under the Creative Commons
> Attribution-NonCommercial-ShareAlike 3.0 license. This allows for non-commercial use of the data as long as
> MusicBrainz is given credit and that derivative works … are also made available under the same license."

Ayrım: <https://musicbrainz.org/doc/MusicBrainz_Database>
- Çekirdek: Artists, Recordings, Releases… ve **"Relationships & URLs"**.
- Ek veri: "user submitted annotations, **tags (including genre associations)** and ratings · derived
  statistics · search indexes · edit history".

→ `artist-rels` ve kredi ilişkileri CC0. Projenin kullandığı MB etiket ve türleri (ör. `tarz_adi.py`'nin
ayırt eden etiketi) ise BY-NC-SA, yani gösterimde "MusicBrainz" atfı gerekir.

Hız: <https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting>
> "The rate at which your IP address is making requests is measured. If that rate is too high, all your
> requests will be declined (http 503) until the rate drops again. Currently that rate is (on average) 1
> request per second." · "if your requests are coming in at 4 requests per second, we don't honour 25% of them
> and decline the other 75% - we decline 100% of them" · "Global: We allow through 300 requests each second"
> UA: "Each request sent to MusicBrainz needs to include a User-Agent header, with enough information … to
> contact the application maintainers" — biçim "Application name/<version> ( contact-url )".
> "Please refrain from having your applications wake up at a certain time of the day …" ·
> "If you want your application to poll MusicBrainz to see if some metadata has changed, please don't do this."

### 2.6 Wikidata / Wikimedia

Lisans: <https://www.wikidata.org/wiki/Wikidata:Licensing>
> "All structured data (i.e. the main, Property, Lexeme, and EntitySchema namespaces) is released into the
> public domain under Creative Commons Zero."

WDQS sınırları: <https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual>
> "There is a hard query deadline configured which is set to 60 seconds." · "One client (user agent + IP) is
> allowed 60 seconds of processing time each 60 seconds" · "One client is allowed 30 error queries per minute"
> · "Clients exceeding the limits above are throttled with HTTP code 429. If the client ignores 429 responses
> and continues …, it can be temporarily banned" · "Clients who don't comply with the User-Agent policy may be
> blocked completely" · "access to the service is limited to 5 parallel queries per IP".

UA politikası: <https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy>
> "Scripts should use an informative User-Agent string with contact information, or they may be blocked without
> notice." · "The generic format is <client name>/<version> (<contact information>) <library/framework
> name>/<version>" · "Do not use generic agents such as "curl", "lwp", "Python-urllib""

Bot politikası: <https://wikitech.wikimedia.org/wiki/Robot_policy>
> Action API: "If unauthenticated, keep the concurrency of your requests to 1 at a time, and below 5 requests
> per second overall." · Media API (upload.wikimedia.org): "Always keep a total concurrency of at most 2 …
> Only use originals or one of our standard thumbnail sizes"

<https://www.mediawiki.org/wiki/Common_thumbnail_sizes>:
> "Current standard sizes in Wikimedia production: 20px, 40px, 60px, 120px, 250px, 330px, 500px, 960px, 1280px,
> 1920px, 3840px" · "requests that go through PHP … will be rounded up to the closest standard size; direct
> requests (hotlinking) will be rejected unless they use a standard size."

→ `kisi_gorsel.py` `Special:FilePath/…?width=400` kullanıyor. Bu PHP üzerinden gittiği için büyük
olasılıkla 500'e yuvarlanıyor. Kırılmaz, ama 330 ya da 500 seçmek daha doğru.

### 2.7 Deezer

Şartlar: <https://developers.deezer.com/termsofuse> (tarihsiz)
> "access free of charge the DEEZER application programming interface … in order to customize his personal site
> and/or develop personal web pages, blog … and personal applications"
> **IV. NON-COMMERCIAL USE:** "The Developer agrees that the use of the Services is strictly limited for a
> non-commercial purpose and in a non-commercial environment." · "The Developer undertakes to inform by any
> means any person accessing the Content through the Webpages and/or Personal Applications of its conditions of
> use and notably that the streaming of the recordings is limited to a strictly private use within a family
> scope." · "The use of the Content is limited to a strictly private use within a family scope."
> **V. DRM:** "The Developer undertakes not to bypass, by any means, these measures, for the purpose of
> downloading the Content …"
> **III.3:** "Will not modify, edit, disassemble, decompile or reverse-engineer the DEEZER API …"

Yönergeler: <https://developers.deezer.com/guidelines>
> "**Local Storage/Offline Storage policy** — Important: Local Storage/Offline Storage of audio data is strictly
> forbidden. If in some cases you need to optimize your application and store audio data, please contact Deezer."

Şartlarda **metin verisinin önbelleklenmesiyle ilgili madde yok**. Sayısal hız sınırı da yok.
Önceki rapordaki "5 sn'de 50 istek" bu oturumda doğrulanamadı [D].

**`/artist/{id}/related` belgede mi?**
- `https://developers.deezer.com/api/artist/related` şimdi şuraya yönleniyor:
  `/login?redirect=/api/artist/related`. Sayfa metni: "You have to login to accept the terms and
  conditions of the simple API."
- `/api` kökü de aynı şekilde yönleniyor.
- Yönlendirmenin yolu koruması belge sayfasının var olduğunu gösteriyor. Ama içerik giriş yapılmadan okunamadı [D].
- Yeni bulgu: Deezer artık API belgesine erişim için **Simple API şartlarının hesapla kabul edilmesini**
  istiyor. Uç noktalar hâlâ anahtarsız çalışıyor [Ö]. Bu kabul kullanıcının işi; Claude hesap açamaz.

### 2.8 AcousticBrainz

<https://acousticbrainz.org/>:
> "In 2022, the decision was made to stop collecting data. For now, the website and its API will continue to be
> available." · "All of the data contained in AcousticBrainz is licensed under the CC0 license (public domain)."

<https://acousticbrainz.org/download>:
> "2022-07-06: We provide downloadable archives of all submissions made to AcousticBrainz (29,460,584
> submissions)" · "Dumps are split into 30 archives, each with 1 million data files … zstandard" · "Smaller CSV
> files … Each file contains 29,460,584 rows of data."

Canlı sınama [Ö, 2026-10-20]:
- Belgedeki örnek MBID `96685213-…` için `/api/v1/{mbid}/count` → `{"count":132}`; `/high-level` → tam yanıt.
- Başlıklar: `x-ratelimit-limit: 100`, `x-ratelimit-reset-in: 8`. Pencere ≈10 sn olduğu için kabaca 10 istek/sn.
- <https://acousticbrainz.readthedocs.io/api.html>: "the client must use these headers to determine the rate".

### 2.9 Setlist.fm

<https://api.setlist.fm/docs/1.0/index.html>:
> "Note that the setlist.fm API is, according to the API terms of service, only free for non-commercial
> projects." · "API keys … must be included in the request with the x-api-key header."

<https://www.setlist.fm/help/terms> ("Last Updated: October 14, 2019"):
> "Use of Setlist.fm API — You are permitted to use the API solely for non-commercial purposes … If the primary
> purpose of your application is to derive revenue, it is considered commercial."
> "**Retain any copies of the Setlist.fm data, except for the purposes of retaining cached information for short
> periods.** You must make direct server calls to the API for the Setlist.fm data and distribute the Setlist.fm
> data to end users on your website immediately upon receipt by your servers."
> "you must display attribution on your website or client application wherever Setlist.fm data is used. When
> using the API, you must use the attribution link each API response contains. You may not tag links to
> Setlist.fm with a nofollow attribute"
> "We reserve the right to limit the rate at which calls may be made to the API"

Sayısal sınır (önceki rapordaki "~2/sn, ~1440/gün") belgede bulunamadı [D].

### 2.10 Genius

`docs.genius.com` ve `genius.com/static/terms` insan doğrulaması istiyor. `api.genius.com/songs/…` token'sız
401 döndü [Ö]. **Şartlar okunamadı.** Proje kuralına göre okunmadan eklenmez.

---

## 3. Ampirik kapsama

Sanatçı kimlikleri MusicBrainz aramasından alındı, ad ya da takma ad tam eşleşmesiyle.
- "Duman" ilk aramada Kazak şarkıcıya düştü. Doğrusu `country:TR` ile bulundu: `f8a9a911-…`, "Turkish rock".
- Masayoshi Takanaka MB'de "高中正義" adıyla kayıtlı, takma ad eşleşmesiyle bulundu.
- Wikidata QID'leri **MB'nin kendi `url-rels` bağlantısından** alındı (15/15 var). Ad eşleştirmesi
  yapılmadı, K14 ile uyumlu.

### 3.1 Wikidata (1 SPARQL sorgusu, 278 satır)

Sütunlar: P737 = influenced by; P737← = bu sanatçıdan etkilenenler; P463← / P527← = ters yönde üyelik.

| Sanatçı | P737 | P737← | P136 | P495 | P740 | P27 | P527 | P463 | P463← | P1303 | P1953 Discogs | P2722 Deezer | P3192 Last.fm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Casiopea | 0 | 0 | 3 | 1 | 1 | – | 10 | – | 10 | – | 1 | 1 | 1 |
| T-Square | 0 | 0 | 1 | 1 | **0** | – | 17 | – | 18 | – | 1 | 2 | 1 |
| Masayoshi Takanaka | 0 | 0 | 5 | – | – | 1 | – | 4 | 0 | 2 | 1 | 1 | 1 |
| Meshuggah | 0 | 2 | 4 | 1 | 1 | – | 1 | – | 5 | – | 1 | 1 | 1 |
| Plini | 0 | 0 | 3 | – | – | 1 | – | 0 | 0 | **0** | **0** | **0** | **0** |
| Animals as Leaders | 0 | 0 | 1 | 1 | 1 | – | 1 | – | 1 | – | 1 | 1 | 2 |
| Allan Holdsworth | 0 | 0 | 3 | – | – | 1 | – | 3 | 0 | 2 | 1 | 1 | 0 |
| Duman | 0 | 0 | 3 | 1 | 1 | – | **0** | – | 2 | – | 1 | 0 | 0 |
| Şebnem Ferah | 0 | 0 | 1 | – | – | 1 | – | 0 | 0 | 2 | 1 | 1 | 0 |
| Barış Manço | 0 | 0 | 6 | – | – | 1 | – | 1 | 0 | 2 | 1 | 0 | 0 |
| Erkin Koray | 0 | 0 | 4 | – | – | 1 | – | 0 | 0 | 11 | 1 | 1 | 0 |
| Cem Karaca | 0 | 0 | 3 | – | – | 1 | – | 1 | 0 | 2 | 1 | 1 | 0 |
| Mor ve Ötesi | 0 | 0 | 2 | 1 | 1 | – | 1 | – | 1 | – | 1 | 2 | 1 |
| Gojira | 0 | 1 | 3 | 1 | 1 | – | 4 | – | 4 | – | 2 | 1 | 1 |
| Tigran Hamasyan | **3** | 2 | 2 | – | – | 2 | – | 0 | 0 | 4 | 1 | 1 | 1 |

("–" = o tür varlık için anlamsız: P495/P740/P527 gruplar, P27/P463/P1303 kişiler için.)

**Kapsama özeti (15 sanatçı):**
- **P737 etki:**
  - İleri yönde 1/15. Yalnız Tigran Hamasyan: Chick Corea, Avet Terterian, Arno Babajanian.
  - Ters yönde 3/15. Meshuggah ← Vildhjarta, SEES; Gojira ← HESKEN; Tigran ← Viken Arman + 1.
  - Toplam 8 kenar, 3 sanatçı. **Türk ve Japon sanatçıların hiçbirinde kenar yok (0/9).**
  - → Wikidata bu nişlerde etki ekseninin kaynağı **olamaz**. Önceki raporun [H] uyarısı doğrulandı.
- **P136 tür:**
  - 15/15, toplam 44 değer (ortalama 2,9).
  - "Anatolian rock" 4 sanatçıda: Duman, Manço, Koray, Karaca. "city pop" Takanaka'da. "jazz fusion" 5 sanatçıda.
  - Kalite sorunu: Şebnem Ferah'ın tek türü "pop music".
  - Lisans CC0, yani MB türlerinin (BY-NC-SA) aksine atıfsız gösterilebilir.
- **Ülke:**
  - Gruplarda P495 7/7, kişilerde P27 8/8 → **15/15**.
  - Kuruluş yeri P740: 6/7 grup. T-Square'de yok.
- **Kadro:**
  - Gruplarda P527 6/7. Duman'da yok, ama iki kişi P463 ile Duman'ı gösteriyor.
  - Her iki yön birlikte sayılınca 7/7 grubun en az bir üye bağı var.
  - Kişilerde P463 (üyesi olduğu grup) 4/8.
  - MB'yle kıyas: Meshuggah'ta Wikidata 5 üye bağı, MB 8. Duman'da Wikidata 2, MB 5.
- **Enstrüman P1303:** 7/8 kişi (Plini'de yok). Erkin Koray'da 11 değer.
- **Kimlik eşleme:**

  | Özellik | Kapsama |
  |---|---|
  | P434 MB | 15/15 |
  | P1953 Discogs | 14/15 (Plini yok) |
  | P2722 Deezer | 12/15 |
  | P3192 Last.fm | 8/15 |
  | P1952 Metallum grup | 2 (Meshuggah, Gojira) |
  | P1989 Metallum kişi | 2 (Holdsworth, Ş. Ferah) |

  Özellik adları sorguyla doğrulandı: P2722 "Deezer artist ID", P3192 "Last.fm ID",
  P1952/P1989 "Encyclopaedia Metallum band/artist ID", P1902 "Spotify artist ID".

### 3.2 MusicBrainz `artist/{mbid}?inc=artist-rels+url-rels` (15 sanatçı, istenen 5'in üstü)

| Sanatçı | Toplam artist-rels | member of band | supporting | diğer | enstrüman öznitelikli | tarihli |
|---|---|---|---|---|---|---|
| Casiopea | 18 | 15 | 2 | tribute 1 | 17 | 17 |
| T-Square | 27 | 21 | 3 | subgroup 3 | 23 | 23 |
| Masayoshi Takanaka | 4 | 3 (→ Sadistics, Sadistic Mika Band…) | 1 | – | 3 | 2 |
| Meshuggah | 9 | 8 | 0 | tribute 1 | 8 | 8 |
| Plini | 1 | 0 | 1 | – | 1 | 0 |
| Animals as Leaders | 6 | 6 | 0 | – | 6 | 6 |
| Allan Holdsworth | 16 | 15 (→ Soft Machine, Tony Williams Lifetime, U.K.…) | 1 | – | 4 | 7 |
| Duman | 5 | 5 | 0 | – | **0** | **0** |
| Şebnem Ferah | 2 | 2 (→ Volvox) | 0 | – | 2 | 2 |
| Barış Manço | 4 | 3 (→ Kurtalan Ekspres, Moğollar, Kaygısızlar) | 0 | named after 1 | **0** | 1 |
| Erkin Koray | 3 | 3 | 0 | – | **0** | **0** |
| Cem Karaca | 6 | 5 (→ Apaşlar, Kardaşlar, Moğollar…) | 0 | parent 1 | **0** | 5 |
| Mor ve Ötesi | 4 | 4 | 0 | – | 4 | 4 |
| Gojira | 5 | 4 | 0 | tribute 1 | 4 | 4 |
| Tigran Hamasyan | 1 | 1 (→ Jazz-Iz-Christ) | 0 | – | 1 | 1 |
| **Toplam** | **111** | **95** | **8** | 8 | **73 (%66)** | **80 (%72)** |

**Bulgular:**
- **Hiçbir sanatçıda `collaboration` ya da `teacher` ilişkisi yok (0/15).** Kadro grafiği neredeyse
  tümüyle `member of band` ve `supporting musician`'dan oluşuyor.
- Japon fusion (Casiopea, T-Square) MB'de **çok zengin**: 45 ilişki, %89'u enstrümanlı ve tarihli.
  Örnek: "神保彰 [drums (drum set)]" supporting musician. Buradan "kadro sıçraması" stratejisi doğrudan kurulabilir.
- **Türk rock'un dört sanatçısında enstrüman özniteliği 0** (Duman, Manço, Koray, Karaca: 18 ilişkide 0).
  Daha yeni kuşakta durum iyi: Mor ve Ötesi 4/4, Şebnem Ferah 2/2. "Davulda X var" şablonu Anadolu
  rock ve Duman için MB'den kurulamaz. Wikidata P1303 kişi düzeyinde bu boşluğu kısmen kapatıyor
  (Koray 11, diğerleri 2'şer).
- Kişi sanatçıların "member of band →" bağları (Holdsworth 15, Karaca 5) iki adımlı sıçramanın köprüsü.
  Örnek yol: kişi → grup → o grubun diğer üyeleri.

### 3.3 ListenBrainz labs `similar-artists` (token'sız)

Algoritma projeninki: `session_based_days_7500_…_skip_30`. 4/4 istek **200**, her biri 100 sonuç
döndü [Ö, 2026-10-20].

| Sorgu | İlk 6 |
|---|---|
| Meshuggah | Gojira 2013, Mastodon, Opeth, Lamb of God, Slayer, In Flames |
| Casiopea | T‐SQUARE 244, 高中正義 91, 大橋純子 84, Frank Zappa, Spyro Gyra, Gorillaz |
| Duman | Teoman 137, mor ve ötesi 128, maNga, Şebnem Ferah, Pinhani, Sertab Erener |
| Erkin Koray | Barış Manço 229, Selda Bağcan, Cem Karaca, Moğollar, Fikret Kızılok, 3 Hürel |

Not: Casiopea listesinin 6. sırasından sonra popüler gürültü giriyor (Gorillaz, Michael Jackson,
Jamiroquai). Skorlar küçük (≤244); düşük dinleyicili nişte sinyal ince.

### 3.4 Deezer `/artist/{id}/related` (anahtarsız)

3/3 istek başarılı. Her biri `total: 20` döndü; uç en çok 20 sonuç veriyor [Ö].

| Sorgu (Deezer kimliği) | İlk 6 |
|---|---|
| Meshuggah (2175) | Lamb of God, Gojira, Jinjer, Fear Factory, The Haunted, Strapping Young Lad |
| Casiopea (1380184) | Masayoshi Takanaka, T-Square, The Square / T-Square, Himiko Kikuchi, Naniwa Express, Sadistics |
| Duman (14826) | Şebnem Ferah, Mor ve Ötesi, Adamlar, Teoman, maNga, Pinhani |

Japon fusion'da Deezer listesi LB'den **daha temiz**: ilk 10'un 10'u da sahne içi (Jun Fukamachi,
Yuji Ohno, Sadao Watanabe…). Bir sorun var: aynı grubun iki ayrı kaydı ("T-Square" ve "The Square /
T-Square") ayrı sanatçı olarak geliyor. MBID eşlemesinde birleştirilmeli (K14).

---

## 4. Projenin bugünkü kodunda görülen uyum açıkları (salt okundu, değiştirilmedi)

| # | Yer | Durum | Kural | Önerilen düzeltme |
|---|---|---|---|---|
| 1 | `python/onbellek.py` (Discogs istemcisi, TTL yok) | Discogs API yanıtları kalıcı | Discogs §4: 6 saat / "gerekenden uzun saklanamaz" | Kredileri CC0 dump'tan al. API'yi yalnız dump'ta olmayan yeni release için kullan, TTL koy |
| 2 | `web/` (grep: "Discogs" geçmiyor) | Atıf yok | "Data provided by Discogs." + bağlantı (veri yanında) + bağımsızlık bildirimi | Discogs kaynaklı kredilerin yanına atıf; bildirimi `/gizlilik`e ekle (iki dilde, K22) |
| 3 | `python/discover/listenbrainz.py` | `istek_araligi=0.6` (≈1,7 istek/sn). UA `muzik-kesif-motoru/0.1 (kisisel arastirma)` iletişim içermiyor | LB: "never make more than ONE call per second"; geçersiz UA "blocked without further notice" | Aralığı ≥1,0 sn yap; UA'ya depo URL'sini ekle |
| 4 | `python/kisi_gorsel.py` (Wikidata) | UA `muzik-kesif-motoru/0.1`, iletişim yok. `istek_araligi=0.2` (5/sn, sınırda) | Wikimedia UA politikası: iletişim bilgisi şart; Action API <5 istek/sn, eşzamanlılık 1 | UA'ya iletişim URL'si; aralık ≥0,25 sn; `width=400` yerine 330 ya da 500 |
| 5 | `python/discover/acousticbrainz.py` UA | İletişimsiz | MetaBrainz ailesinde aynı UA beklentisi | Aynı düzeltme |
| 6 | `python/onbellek.py:musicbrainz()` | `MUSICBRAINZ_USER_AGENT` tanımlı değilse yer tutucu (`ornek@…`) kullanılıyor | MB: UA'da gerçek iletişim | Varsayılanı depo URL'li biçime çevir |
| 7 | `python/tur_sinif.py` (`data/cache/onizleme/*.m4a`, kalıcı) ve `python/enrich/icra_profili.py` (`data/cache/stemler`; Deezer önizlemesi yedek kaynak) | Önizleme sesi ve ondan türeyen stem'ler diskte kalıcı | Deezer: "Local Storage/Offline Storage of audio data is strictly forbidden" | Deezer kaynaklı klipleri analizden sonra sil. Stem önbelleğinde yalnız sayısal öznitelik tut. iTunes önizlemesinin saklama şartı ayrıca okunmalı (bu raporun kapsamı dışında) |
| 8 | Deezer içerik koşulu | Kullanıcılara koşul bildirimi yok (gördüğüm kadarıyla) | ToS IV: kullanıcılar "strictly private use within a family scope" konusunda bilgilendirilmeli | `/gizlilik`e tek cümle |

---

## 5. CLAUDE.md "Veri kaynakları ve sınırları" tablosu için taslak satırlar (yapıştırmaya hazır)

| Kaynak | Kullanım | Sınır |
|---|---|---|
| MusicBrainz ilişkileri | Kadro sıçraması: `member of band` (enstrüman + tarih), `supporting musician`, `subgroup` — `artist/{mbid}?inc=artist-rels+url-rels` | Çekirdek veri (ilişkiler dahil) CC0, kalıcı önbellek serbest. Etiket/tür/puan "ek veri": CC BY-NC-SA 3.0, gösterimde atıf. IP başına ort. 1 istek/sn, aşılırsa isteklerin TÜMÜ 503. UA `ad/sürüm ( iletişim-url )` zorunlu; belli saatte toplu çalıştırma ve değişiklik yoklaması yok. Ölçüldü (15 sanatçı, 2026-10-20): 111 ilişki, %66 enstrümanlı; Japon fusion zengin (%89 enstrümanlı); Duman/Manço/Koray/Karaca'da enstrüman özniteliği 0 (18 ilişki); `collaboration`/`teacher` 0 |
| Discogs API | Yalnız dump'ta henüz olmayan yeni release | API Terms (2025-05-27) §4: içerik sitedekinden 6 saatten eski gösterilemez, "hizmet için gerekenden uzun" saklanamaz — **kalıcı önbellekle uyumsuz**, TTL şart. Her verinin yanında "Data provided by Discogs." + discogs.com bağlantısı (nofollow yok); uygulamada bağımsızlık bildirimi. Token'sız 25 istek/dk (başlıkla ölçüldü) |
| Discogs aylık dump | Krediler (`extraartists` + `role`), üyeler/gruplar, style, ülke, yıl | `data.discogs.com`: "CC0 No Rights Reserved"; API şartları uygulanmaz. Ayda bir; 2026-10: releases 10,5 GB, artists 476 MB, masters 601 MB, labels 87 MB (gz). SHA-256 `CHECKSUM.txt` |
| Wikidata | Ülke (P495 grup / P27 kişi), kuruluş yeri (P740), tür (P136), üyelik (P527/P463), enstrüman (P1303), kimlik eşleme (P1953 Discogs, P2722 Deezer, P3192 Last.fm); QID MB `url-rels`'ten | Yapısal veri CC0, kalıcı önbellek serbest. WDQS: sorgu başına 60 sn; istemci (UA+IP) başına dakikada 60 sn işlem; dakikada 30 hatalı sorgu; IP başına 5 paralel; 429'u yok sayan geçici yasak yer. UA'da iletişim bilgisi şart, yoksa uyarısız engel. Action API: tek eşzamanlı, <5 istek/sn. Görsel: standart küçük resim boyutu (330/500). **P737 (etki) ölçüldü: 3/15, Türk/Japon 0/9 — etki kaynağı olarak kullanılmaz** |
| ListenBrainz | "Bunu dinleyen şunu da dinliyor" (labs `similar-artists`, anahtarsız — 2026-10-20'de 4/4 çalıştı) | Dump'lar CC0 1.0; ToS = MetaBrainz sosyal sözleşmesi ("kişisel kullanım her zaman ücretsiz"). Her istemci saniyede EN ÇOK 1 çağrı; UA `ad/sürüm ( iletişim )`, yoksa uyarısız engel. popularity top-* ve lb-radio kullanıcı token'ı ister. Tam dinlenme dump'ı 233 GB |
| AcousticBrainz | Sende olmayan parçanın ses profili (K11) | CC0. 2022'de durduruldu: "For now, the website and its API will continue to be available" — 2026-10-20'de yanıt veriyor. `X-RateLimit` başlıklarına uy (≈100 istek/10 sn). Kalıcı sigorta: 29.460.584 gönderimlik CSV/JSON dump |
| Deezer | 30 sn önizleme (yedek) + çalma listeleri + `/artist/{id}/related` (anahtarsız, ≤20 sanatçı) | Developers ToS: yalnız ticari olmayan, "kişisel uygulama"; içerik "strictly private use within a family scope", kullanıcılara bildirilir. **Ses verisi yerel/çevrimdışı saklanamaz** (yönerge) — önizleme/stem dosyası analizden sonra silinir, yalnız sayı tutulur. API belgesi artık hesapla Simple API şartlarının kabulünü istiyor. Metin önbelleği ve sayısal hız sınırı belgede yok |
| Last.fm | **ŞİMDİLİK EKLENMEDİ** (aday: kalabalık etiketleri, benzer sanatçı) | Yalnız ticari olmayan; araştırma/akademik kullanım öncesi partners@last.fm'e yazılır. Saklanan Last.fm verisi toplamda ≤100 MB, önbellek HTTP başlıklarına göre — **kalıcı önbellekle uyumsuz**. Atıf + katalog sayfası bağlantısı + "powered by AudioScrobbler" düğmesi; herkese açık sayfa için Last.fm'in YAZILI onayı. Görsel kullanılamaz. Sayısal hız sınırı yok ("saniyede birkaç çağrı" askıya alma sebebi) |
| Setlist.fm | **ŞİMDİLİK EKLENMEDİ** (aday: konser cover'ları, konuk müzisyen) | Yalnız ticari olmayan; ücretsiz anahtar (`x-api-key`). Veri "yalnız kısa süreli önbellek" — kalıcı önbellekle uyumsuz. Veri kullanılan her yerde yanıttaki atıf bağlantısı (nofollow yok). Sayısal hız sınırı belgede yok |
| Genius | **KULLANILMAZ (şartlar okunamadı)** | Belge ve şart sayfaları insan doğrulamasıyla kapalı (2026-10-20). API token'sız 401. Kural gereği şartlar okunmadan eklenmez |

---

## 6. Açık sorular ve kullanıcının yapacakları

1. **Discogs kararı.** İki yol var:
   - (a) Kredileri aylık CC0 dump'a taşı ve API'yi TTL'li tut.
   - (b) API önbelleğine 6 saatlik gösterim kuralı uygula. Bu, K5 ekonomisini bozar.

   Yol (a) önerilir. Her durumda arayüze iki Discogs bildirimi eklenmeli.
2. **Last.fm.** Uygulama Tailscale Funnel ile internete açık. §2.7'nin "public access" şartı girişle
   korunan bir sayfayı kapsıyor mu, belirsiz. Last.fm eklenecekse önce partners@last.fm'e yazılmalı.
   Bu kullanıcının işi; Claude e-posta göndermez. Tez ya da ders kullanımı varsa "research/academic"
   bildirimi de aynı yazıya girer.
3. **Deezer.** Kullanıcı developers.deezer.com'a kendi hesabıyla girip Simple API şartlarını kabul etmeli.
   Ardından `/api/artist/related` belge sayfası okunup bu rapora "[B]" olarak eklenmeli.
4. **Deezer ses saklama.** `data/cache/onizleme` ve `data/cache/stemler` içindeki Deezer kaynaklı
   dosyalar yönergeyle çatışıyor. Dosyaların hangi kaynaktan geldiğini ayırmak için `kaynak`
   bilgisinin dosya önbelleğine de yazılması gerekiyor.
5. **Genius ve Discogs geliştirici sayfası:** Bot sınaması yüzünden okunamadı. Kullanıcı tarayıcıdan
   okuyup token'lı Discogs hız sınırını (60/dk) ve Genius API şartlarını doğrulamalı.
6. **K19 önerisi.** Bu ölçümler yalnız 15 sanatçılık örneklemden geliyor. Tavan ölçümü için aynı
   betikler kütüphanenin 147 sanatçısına uygulanmalı (MB ~2,5 dk, Wikidata tek sorgu):
   - "gizlenen sanatçı MB kadro grafiğinde 1–2 adımda var mı?"
   - "Deezer related ya da LB similar listesinde var mı?"

---

## Ek: bu oturumun dosyaları

- Ham sayfalar ve metinler: `scratchpad/dogrulama/sayfalar/` (`discogs_tos.txt`, `lastfm_tos.txt`, `lb_api.txt`,
  `mb_license.txt`, `mb_db.txt`, `mb_ratelimit.txt`, `wd_lic.txt`, `wdqs_manual.txt`, `wm_ua.txt`,
  `wm_robot.txt`, `wm_thumb.txt`, `dz_tos.txt`, `dz_guide.txt`, `sfm_terms.txt`, `sfm_docs.txt`, `ab_home.txt`,
  `ab_dl.txt`, `ab_api.txt`)
- Ölçüm çıktıları: `scratchpad/dogrulama/veri/` (`mb_mbid.json`, `mb_rels.json`, `wd_satirlar.json`,
  `lb_similar.json`, `deezer_related.json`)
- Betikler: `scratchpad/dogrulama/betik/` (`getir.sh`, `metin.py`, `mb_ara.py`, `mb_rels.py`, `wd_sorgu.py`,
  `lb_test.py`, `deezer_test.py`)
