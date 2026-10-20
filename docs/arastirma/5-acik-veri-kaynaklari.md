# 5 — Açık veri kaynakları: öneriyi güçlendirebilecek ücretsiz ve yasal kaynaklar

*Araştırma tarihi: 2026-10-20. Kapsam: 0 TL, LLM yok, ≤5 kullanıcı, ticari olmayan, kişisel keşif aracı.*

---

## 0. Yöntem, sınırlar ve güven etiketleri

**Bu oturumda ne çalıştı, ne çalışmadı:**

- `WebFetch` hiçbir alan adında çalışmadı (DNS hatası: last.fm, discogs.com, wikipedia.org,
  readthedocs.io). Ajan vekil sunucusu da musicbrainz.org, wikidata.org, deezer.com ve
  listenbrainz.org'a çıkışı reddetti. Bu yüzden resmi sayfaları doğrudan okuyamadım.
- `WebSearch` ile **18 arama** yaptım. Sonra oturumdaki tüm ajanların paylaştığı arama
  bütçesi doldu. İstenen 25 aramaya ulaşamadım. Bunu aşmak için başka bir arama
  motoru ya da okuyucu servisi kullanmadım.
- Açıktan yalnız `raw.githubusercontent.com` çalıştı. MetaBrainz'in kendi depolarından
  **birincil kaynak** okudum: ListenBrainz sunucu kaynak kodu ve belgeleri, AcousticBrainz
  indirme sayfası şablonu, musicbrainz-docker README'si, musicbrainz-server web servisi
  kodu, troi LB Radio belgesi. Bunların yanında discogs-xml2db README'sini de okudum.
  Toplam 15'ten fazla dosya.

**Güven etiketleri (tablodaki her iddianın yanında):**

| Etiket | Anlamı |
|---|---|
| **[B]** | Birincil kaynakta doğrulandı: resmi belge ya da kaynak kod, bu oturumda okundu |
| **[İ]** | İkincil kaynak: arama özeti, üçüncü taraf sayfa ya da kullanım şartlarından alıntı yapan geliştirici tartışması |
| **[H]** | Benim önceki bilgim, bu oturumda doğrulanamadı. **Koda geçmeden önce resmi sayfada doğrulanmalı.** |

Proje kuralı şöyle: "yeni bir API kaynağı eklenmeden önce rate limit ve ToS durumu not
edilir". Bu yüzden [H] ve [İ] etiketli her ToS satırı, CLAUDE.md'ye girmeden önce resmi
sayfadan okunmalı. Bölüm 6'da taslak satırlar var.

---

## 1. Ana tablo — tüm adaylar

Sütunların anlamı:
- **Sinyal:** kredi, ilişki, benzerlik, etiket, birlikte dinleme, çalma listesi, ses, etki, sahne.
- **Uyum:** bu kullanıcının nişleri için uygunluk. Nişler: prog/teknik metal, jazz-fusion, Japon fusion, Türk rock, hip-hop.

### 1a. Yüksek ve orta uyumlu kaynaklar

| # | Kaynak | Sinyal | Erişim | Lisans / ToS | Hız sınırı | Boyut / tazelik | Uyum | Gerekçe |
|---|---|---|---|---|---|---|---|---|
| 1 | **MusicBrainz ilişkileri** (artist↔artist, recording↔artist, recording↔work) | Kadro (*member of band*: enstrüman özniteliği ve tarihlerle), turne müzisyeni (*supporting musician*), *collaboration*, *teacher*, *subgroup*, *tribute*, cover (performance + "cover" özniteliği), besteci, prodüktör | API `ws/2`, `inc=artist-rels`, `work-rels`, `recording-level-rels`, `work-level-rels`, `url-rels` [B: WebServiceInc.pm] | Çekirdek veri **CC0**. Önbellek sınırsız [İ] | 1 istek/sn, anlamlı User-Agent zorunlu [H; projede zaten uygulanıyor] | Canlı | **Yüksek** | Proje bunu zaten kısmen kullanıyor (`krediler.py`: `artist-rels+recordings+recording-level-rels+artist-credits`). Sanatçı↔sanatçı kadro ilişkileri ve work/cover ilişkileri ise hiç çekilmiyor. Yeni bağımlılık yok, lisans temiz |
| 2 | **Discogs aylık dump** (`artists`, `releases`, `masters`, `labels` XML.gz) | Release ve parça düzeyinde krediler (`extraartists` + `role`: Drums, Bass, Producer…), sanatçının üyeleri, grupları ve takma adları, **style** (Fusion, Prog Rock, Technical Death Metal…), ülke, yıl | Toplu indirme: `https://data.discogs.com/` [İ] | **CC0** [İ: Discogs geliştirici belgesinden alıntı] | Yok (dosya) | ~6,9 M sanatçı, ~12,5 M release, ~1,5 M label (discogs-xml2db örnek çıktısı) [B]. `releases.xml.gz` ≈10+ GB [H]. Ayda bir | **Yüksek** | Ölçekli kredi verisi. *style* + ülke ile Japon fusion ve Türk rock sahnesi kurulabilir. API'nin 6 saat tazelik maddesiyle önbellek çatışmasını da çözer (§2.1) |
| 3 | **Wikidata** (SPARQL + JSON dump) | Etki (P737 *influenced by*), tür (P136), üyelik (P463 / P527), enstrüman (P1303), kuruluş yeri (P740), köken ülke (P495), kuruluş yılı (P571), hoca/öğrenci (P1066 / P802), **kimlik eşleme** (MB, Discogs, Metallum, ProgArchives, Last.fm, Deezer ID'leri) | `https://query.wikidata.org/sparql` | Yapısal veri **CC0** [H; yaygın bilgi]. User-Agent politikası zorunlu. Varsayılan python-requests UA'sı engelleniyor [İ] | Sorgu başına 60 sn tavan. İstemci (UA+IP) başına dakikada 60 sn işlem. Dakikada 30 hatalı sorgu [İ: WDQS kılavuzundan alıntı] | Canlı. 2025-05'te "graf bölünmesi" oldu; müzik verisi ana grafta kaldı, yalnız bilimsel makaleler ayrıldı [İ] | **Yüksek** | Etki ve sahne ekseninin tek açık ve CC0 kaynağı. Proje Wikidata'yı zaten fotoğraf için kullanıyor (`kisi_gorsel.py`). P737 kapsaması müzisyenlerde seyrek [H], bu ölçülmeli |
| 4 | **Last.fm API** | `artist.getSimilar` (eşleşme skoru), `artist.getTopTags` / `album.getTopTags` (kalabalık etiketleri, sayılarıyla), `tag.getTopArtists`, `tag.getSimilar`, `track.getSimilar` | REST, ücretsiz API anahtarı (hesap gerekli) | **Yalnız ticari olmayan kullanım.** Ticari ya da **araştırma/akademik** kullanım için önce partners@last.fm'den izin [İ: ToS özeti]. Veri alt-lisanslanamaz [İ]. Önbellek HTTP başlıklarına uymalı. Eski metinde benzer-sanatçı ve chart verisi için "en az 1 hafta önbellek" maddesi var [İ]. Kaynak gösterme (bağlantı) gerekli [İ]. "Entegrasyon başına 100 MB" tavanı [İ, **doğrulanmadı**] | IP başına 5 istek/sn, 5 dk ortalaması (eski metin) [İ] | Canlı. Ad tabanlı, MBID her zaman yok | **Yüksek / Orta** | j-fusion, city pop, anadolu rock, türkçe rock gibi niş etiketler MB/LB'de seyrek; Last.fm'in kalabalık etiketleri burada en zengin kaynak [H]. ToS ise en kısıtlayıcı olanı (§4.4) |
| 5 | **ListenBrainz popularity API** | Sanatçının en çok dinlenen albümleri ve parçaları. Sanatçı, release, release-group ve recording için toplam dinlenme ve dinleyici sayısı | `GET /1/popularity/top-release-groups-for-artist/{mbid}` ve `top-recordings-for-artist` **kullanıcı token'ı ister**. `POST /1/popularity/artist` token istemez; tek istekte en çok 1000 MBID [B: kaynak kod] | Dinlenme verisi **CC0** [B: dump belgesi + İ] | İstemci başına 1 istek/sn, `X-RateLimit-*` başlıkları [B] | Canlı | **Yüksek** | İki iş görür: (a) yeni bir sanatçıdan hangi albüm önerilecek? (b) "bilinçli uzaklık" için popülerlik sönümü. Hesap ücretsiz |
| 6 | **ListenBrainz LB Radio + labs tag-similarity** | `artist:(…)`, `tag:(…)`, `country:(Turkey)` akışları. easy/medium/hard modu benzerlik listesinin başını, ortasını ya da kuyruğunu seçer. Popüler olmayan benzer etiketler | `GET /1/explore/lb-radio?prompt=…&mode=hard` (**token şart**, token başına 5 sn'de 5 istek) [B]. `labs.api.listenbrainz.org/tag-similarity/json?tag=…` [B: kaynak kod] | CC0 dinlenme verisi üzerine. Labs uçları deneysel | Aynı | Canlı | **Orta** | `mode=hard` doğrudan "kuyruk" veriyor; Türk ve Japon sahnesi için `country:` terimi de var. Ama çıktı bir kara kutu sıralaması, gerekçesi yok (K7'ye zayıf uyar) |
| 7 | **ListenBrainz labs similar-artists** (zaten kullanılıyor) | Birlikte dinleme benzerliği | `labs.api.listenbrainz.org/similar-artists/json` [B: kaynak kodda hâlâ var] | Türetilmiş benzerliğin lisansı ayrıca yazılmamış; dinlenme verisi CC0 [İ] | Aynı | Canlı | Orta (devam) | Labs ucu kararlı API sözü vermiyor; yedeği LB dump'ları (#9) |
| 8 | **AcousticBrainz dump'ları** | Düşük ve yüksek düzey ses öznitelikleri (kayıt MBID'siyle) | JSON: 30 arşiv × 1 M dosya, zstd. **CSV öznitelik dump'ı**: lowlevel / rhythm / tonal, her biri 29.460.584 satır [B] | **CC0** [B: "All of the data contained in AcousticBrainz is licensed under the CC0 license"] | Yok (dosya) | 2022-07-06'da donduruldu. "Site ve API **şimdilik** açık" [B] | **Orta / Yüksek** | Proje AB API'sine bağlı (K11), API ise yalnız "şimdilik" açık. CSV dump'ı küçük ve kalıcı bir sigorta |
| 9 | **ListenBrainz dinlenme dump'ları** | Ham dinlenme kaydı, yani gerçek ortak filtreleme yakıtı | Ayda iki tam dump, haftada iki artımlı. `listenbrainz-listens-dump.tar.zst` ve aylık JSON'a bölünmüş Spark sürümü [B] | **CC0** [B / İ] | Yok (dosya) | 800 M+ dinlenme (ISMIR 2024) [İ]. Boyutu GB olarak doğrulanamadı | **Orta / Düşük** | K16 vekilinin gerçeği. Ama M1 Mac'te ağır, ve LB'nin kendi benzerlik ucu bu veriden zaten türetiliyor. Ancak nişe özgü PMI gerekirse değer |
| 10 | **MusicBrainz tam veritabanı** (mbdump + mbdump-derived, ya da musicbrainz-docker aynası) | #1'in hepsi, yerelde SQL ile | Postgres dump + replikasyon | Çekirdek CC0. derived (etiketler, puanlar) **CC BY-NC-SA 3.0** [İ] | Yok | Arama indeksi olmadan **100 GB disk, 4 GB RAM** [B: musicbrainz-docker README] | **Orta** | API ile 1 istek/sn yetiyorsa gereksiz. İki adımlı kadro grafiği (kişi→grup→kişi) binlerce sanatçıya yayılırsa değer kazanır |
| 11 | **MusicBrainz etiketler / türler** (zaten kullanılıyor) | Tür ve etiket | `inc=tags+genres` | **CC BY-NC-SA 3.0**: ticari olmayan kullanım serbest, kaynak gösterme ve aynı lisansla paylaşma zorunlu [İ] | 1/sn | Canlı | Orta (devam) | Arayüzde gösterilen etiketin yanında "MusicBrainz" kaynak gösterimi olmalı |
| 12 | **Genius API** | Şarkı kredileri: `producer_artists`, `writer_artists`, `custom_performances` (ör. "Drums", "Guitar"). **`song_relationships`**: sample'ladığı, cover'ı olduğu, interpolasyon yaptığı parçalar | REST, ücretsiz istemci token'ı [H] | ToS doğrulanmadı [H]. Söz metni API'de yok | Belgelenmemiş [H] | Canlı | **Orta** (hip-hop ekseni için) | Hip-hop'ta sample grafiği kredi grafiğinin karşılığı. WhoSampled'ın yasal alternatifi. Prog/fusion'da krediler seyrek [H] |
| 13 | **Wikipedia metni** (tr / en / ja) | "Etkiler", "Müzik tarzı" bölümleri | MediaWiki API / REST | **CC BY-SA 4.0** [H], kaynak gösterme zorunlu | UA politikası [H] | Canlı | **Orta** | Faz 3 "neye dikkat et" çıkarımsal modu için alıntı. Türk rock'ta tr.wikipedia çoğu zaman tek düzgün metin [H] |
| 14 | **Deezer ek uçları** (`/artist/{id}/related`, `/artist/{id}/radio`, `/artist/{id}/top`, `/chart`, `/genre/{id}/artists`) | Katalog içi "benzer sanatçı" | Anahtarsız REST, belgelenmiş [H] | Deezer API kullanım şartları bu oturumda yeniden doğrulanamadı [H] | 5 sn'de 50 istek [H] | Canlı | **Orta** | İstemci zaten var (`calma_listesi.py`). `related` ucu bedava ikinci bir kalabalık sinyali; LB ve Last.fm ile üçlü oylama yapılabilir |
| 15 | **Setlist.fm API** | Konserde çalınan cover'lar (cover = etki), konuk müzisyenler, turne, aynı sahneyi paylaşanlar | REST, ücretsiz anahtar [H] | Yalnız ticari olmayan [H] | ~2/sn, ~1440/gün [H] | Canlı | **Orta / Düşük** | "Kim kimi cover'lıyor" iyi bir etki sinyali. Türk ve Japon konser kapsaması zayıf olabilir [H] |
| 16 | **CritiqueBrainz** (zaten kullanılıyor) | Kullanıcı yorumu | API | Yorum başına CC BY-SA ya da CC BY-NC-SA [H] | — | İnce (6 albümde 2 yorum, proje ölçümü) | Düşük (devam) | — |

### 1b. Düşük uyumlu ya da elenen kaynaklar

| # | Kaynak | Sinyal | Erişim | Lisans / ToS | Uyum | Gerekçe |
|---|---|---|---|---|---|---|
| 17 | Spotify Web API (kalan uçlar) | — | OAuth | 2024-11-27'den beri yeni ve geliştirme modundaki uygulamalara kapalı: *related-artists*, *recommendations*, *audio-features*, *audio-analysis*, featured/category playlists, `preview_url`, Spotify'ın kendi editoryal listeleri [H]. Geliştirme modunda 5 kullanıcı (CLAUDE.md) | **Düşük** | Yalnız mevcut kullanım kalsın: kütüphane ve kendi listeler |
| 18 | Million Playlist Dataset (Spotify / AIcrowd) | 1 M çalma listesi, 2010–2017 | Kayıtla indirme [H] | **Yalnız araştırma, ticari olmayan**; yeniden dağıtım yasak [H] | **Düşük / Orta** | K16 PMI'sını 482 listeden 1 M'ye çıkarırdı. Ama lisans "araştırma" diyor; kişisel araç bu kapsama girer mi belirsiz. ABD ağırlıklı, Türk ve Japon niş içeriği ince [H]. **Kullanmadan önce lisans okunmalı, gerekirse hocaya danışılmalı** |
| 19 | Echo Nest Taste Profile / Million Song Dataset | Dinleme üçlüleri (2011) | İndirme | Araştırma [H] | Düşük | Eski, katalog 2011'de duruyor |
| 20 | LFM-1b / LFM-2b | Last.fm dinleme kayıtları | Talep | Araştırma. LFM-2b lisans nedeniyle geri çekildi [H] | Düşük | Erişim belirsiz |
| 21 | Music4All / Music4All-Onion | Klip, etiket, öznitelik | Talep [H] | Akademik | Düşük | Ses klipleri telif sorunlu; erişim talebe bağlı |
| 22 | FMA, MTG-Jamendo, Song Describer, MusicCaps | ML veri setleri | İndirme | CC (çeşitli) [H] | Düşük | Katalog nişle örtüşmüyor. FMA'dan ses indirmek proje kuralıyla yasak |
| 23 | Jamendo API, SoundCloud API | CC müzik / yükleme | Anahtar [H] | Ticari olmayan [H] | Düşük | Katalog uyumsuz |
| 24 | Internet Archive Live Music Archive | Konser kayıtları, metadata | Belgelenmiş arama / metadata API [H] | Metadata açık [H] | Düşük | Jam-band odaklı |
| 25 | YouTube Data API | Video metadata | Günde 10.000 birim [H] | Veri en çok 30 gün saklanabilir [H]. `relatedToVideoId` 2023'te kaldırıldı [H] | Düşük | Benzerlik sinyali kalmadı |
| 26 | TheAudioDB | Biyografi, mood/style alanı | Test anahtarı; tam erişim Patreon üzerinden ücretli [H] | Belirsiz [H] | Düşük | Kapsamı ince; ücretli katman K2'ye aykırı |
| 27 | Songkick | Konser ve sahne | API yeni başvurulara kapalı / ortaklık şartı [H] | — | **Elendi** | Erişim yok |
| 28 | Bandcamp | "Bunu alan şunu da aldı" | Resmi keşif API'si yok; ToS kazımayı yasaklıyor [H] | — | **Elendi** | Yalnız satın alma bağlantısı (zaten var) |
| 29 | AllMusic | Etki, stil, mood | API yok; ToS kazımayı yasaklıyor [H] | — | **Elendi** | RYM ile aynı gerekçe |
| 30 | Every Noise at Once | Tür haritası | Statik; 2023 sonundan beri donmuş [H] | Lisans yok | **Elendi** | Kazıma gerekir |
| 31 | Chosic, Music-Map, Gnod | Benzerlik | API yok | ToS belirsiz | **Elendi** | Kazıma gerekir |
| 32 | Encyclopaedia Metallum | Metal kadroları, çok ayrıntılı | **Resmi API yok**. Python sarmalayıcılar (enmet, python-metallum) aslında kazıyıcı [İ] | Kullanım şartı bulunamadı [İ] | **Elendi** | Proje kuralı: belgelenmemiş uç yok. Yalnız **Wikidata'daki kimlik** (P1952 grup, P1989 kişi [İ]) ile kullanıcıya dış bağlantı verilebilir |
| 33 | ProgArchives | Prog veritabanı, inceleme | API yok, yalnız yasal uyarı sayfası [İ] | — | **Elendi** | Aynı gerekçe. Wikidata'da "Prog Archives artist ID" özelliği var [İ], o yalnız dış bağlantı için |
| 34 | Jazz diskografi projeleri (jazzdisco.org, Lord) | Seans kadroları | Statik HTML / ücretli [H] | Telif | **Elendi** | Aynı bilgi MB + Discogs dump'ında var |
| 35 | Ekşi Sözlük ve Türk forumları | Söylem | Herkese açık API yok [H] | — | **Elendi** | Reddit ile aynı kategori: onaysız uç |

---

## 2. Projede zaten kullanılan kaynaklarla ilgili önemli bulgular

### 2.1 Discogs API: 6 saatlik tazelik maddesi ile K5 kalıcı önbelleği çatışabilir [İ]

Discogs API Terms of Use (son güncelleme 2025-05-27 [İ]) içeriği iki sınıfa ayırıyor:
- **CC0 Data:** release ayrıntıları, sanatçı ve label bilgisi.
- **Restricted Data:** koleksiyon, istek listesi, fiyat ve benzerleri.

Discogs'a uyum için değişiklik yapan geliştirici tartışmaları ToS'tan iki madde alıntılıyor
(ör. `WOIII-me/Discogs-MCP` PR #69, "6h cache cap, attribution"):
- "Our online properties"teki bilgiden **6 saatten eski içerik gösterilemez**.
- İçerik **"uygulama kullanıcılarına hizmet için gerekenden uzun" saklanamaz**.

Projede `python/onbellek.py` Discogs yanıtlarını TTL'siz, kalıcı olarak tutuyor (K5).
Bu maddenin yalnız Restricted Data'ya mı, yoksa tüm içeriğe mi uygulandığını resmi metinden
okuyamadım. Krediler büyük olasılıkla CC0 Data sınıfında, yani risk düşük olabilir. Ama
belirsiz.

**Temiz çözüm:** kredileri **CC0 aylık dump'tan** almak (Öneri 2). Dump CC0 olduğu için
tazelik maddesi ona uygulanmıyor; bunu dump'ı API'den ayrı tutan geliştirici tartışması da
destekliyor [İ]. API yalnız "dump'ta henüz olmayan yeni release" için kalır.

> Kullanıcının resmi sayfayı okuması gereken madde: <https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use>, "Restricted Data" ve "caching" bölümleri.

### 2.2 ListenBrainz "pahalı" uçları artık token istiyor [B]

`api_tools.py:ensure_user_token_for_expensive_endpoint()` şu mesajla 401 dönüyor:
"Due to bad actors and AI scrapers causing undue traffic on our sites, you need to provide
an Auth token for this endpoint."

Etkilenen uçlar:
- `/1/popularity/top-recordings-for-artist/…`
- `/1/popularity/top-release-groups-for-artist/…`
- `/1/explore/lb-radio`

Token ücretsiz LB hesabıyla geliyor. `.env`'e `LISTENBRAINZ_TOKEN` olarak girmeli ve
CLAUDE.md kuralı gereği değeri asla yazdırılmamalı.

Token **istemeyen** uçlar şunlar: `POST /1/popularity/artist|release|release-group|recording`
(tek istekte en çok 1000 MBID, `MAX_ITEMS_PER_GET = 1000`), `/1/metadata/artist/` ve labs uçları.

Kural tüm LB API'si için geçerli: **istemci başına saniyede bir istek** ve
`Uygulama/<sürüm> ( iletişim )` biçiminde User-Agent [B].

### 2.3 AcousticBrainz API yalnız "şimdilik" açık [B]

AB ana sayfa şablonundaki ifade: "In 2022, the decision was made to stop collecting data.
For now, the website and its API will continue to be available."

K11'in %92 kapsaması bu API'ye bağlı. İndirilebilir **CSV öznitelik dump'ları** var:
- lowlevel: `average_loudness`, `dynamic_complexity`, `mfcc_zero_mean`
- rhythm: `bpm`, `danceability`, `onset_rate`…
- tonal: `key_key`, `key_scale`…

Her biri 29.460.584 satır. Projenin kullandığı yüksek düzey sınıflandırıcılar ise yalnız
JSON highlevel dump'ında (30 arşiv × 1 M dosya, zstd). İkisi de CC0 [B].

**Öneri:** ses profili için hangi alanların kullanıldığını çıkar. Önce CSV dump'ı indir.
Highlevel gerekiyorsa yalnız kütüphane ve aday MBID'lerini arşivlerden süzüp sakla.
Dosya adları `highlevel/m/b/i/mbid-n.json` düzeninde olduğu için süzme kolay [B].

### 2.4 MusicBrainz etiketleri CC BY-NC-SA 3.0 [İ]

Çekirdek veri (kimlikler ve **ilişkiler**) CC0. Etiketler, türler, puanlar ve türetilmiş
istatistikler ise ek veri sınıfında. Ek veri ticari olmayan kullanımda serbest ama kaynak
gösterme ve aynı lisansla paylaşma şartı var. Profil ekranında ya da kartta MB etiketi
gösteriliyorsa küçük bir "kaynak: MusicBrainz" notu gerekli.

---

## 3. Kaynak ayrıntıları (öne çıkanlar)

### 3.1 MusicBrainz: henüz çekilmeyen ilişkiler

Doğrulanan include adları [B: `WebServiceInc.pm`]:
- Her ilişkilendirilebilir varlık için `{varlık}-rels`: `artist-rels`, `recording-rels`,
  `work-rels`, `url-rels`, `release-group-rels`, `label-rels`, `place-rels`, `event-rels`,
  `series-rels`, `instrument-rels`, `area-rels`, `genre-rels`.
- Ek olarak `recording-level-rels`, `release-group-level-rels`, `work-level-rels`.

**(a) Sanatçı↔sanatçı (kadro grafiği):**
```
GET https://musicbrainz.org/ws/2/artist/{mbid}?inc=artist-rels+url-rels&fmt=json
```
İlişki türleri [H, türler MB'de uzun süredir sabit]:

| İlişki türü | Ne verir |
|---|---|
| `member of band` | Öznitelikler: enstrümanlar, "original", "minor"; başlangıç ve bitiş tarihi |
| `supporting musician`, `instrumental supporting musician`, `vocal supporting musician` | Turne ve stüdyo misafiri |
| `collaboration` | Ortak proje |
| `teacher` | Hoca–öğrenci |
| `subgroup` | Alt grup |
| `tribute` | Tribute grubu |
| `is person` | Sahne adı ↔ gerçek kişi |
| `url-rels` | Wikidata, Discogs, Bandcamp, resmi site bağlantıları; kimlik eşleme için bedava |

Prog metal ve fusion için en değerli olanı `member of band` + enstrüman özniteliği. Örnek
gerekçe: "Davulcusu X, kütüphanendeki Y grubunda 1995–2001 arası çaldı."

**(b) Cover ve beste (etki):** Mevcut release çağrısına iki include eklemek yeterli. Ek istek gerekmiyor:
```
GET /ws/2/release/{id}?inc=artist-rels+recordings+recording-level-rels+artist-credits+work-rels+work-level-rels&fmt=json
```
Recording→work ilişkisi `performance` ve özniteliklerinde `cover` varsa, `work-level-rels`
o eserin `composer` / `lyricist` bilgisini verir. Bundan "A grubu B'nin şarkısını
cover'lamış" kenarı çıkar. Bu, Wikidata P737'den daha sık dolu bir etki sinyali [H, ölçülmeli].

**Lisans ve hız:** CC0, 1 istek/sn, UA zorunlu. Önbellek kalıcı olabilir.

### 3.2 Discogs CC0 dump'ı

- **Dosyalar:** `discogs_YYYYMM01_artists.xml.gz`, `…_releases.xml.gz`, `…_masters.xml.gz`,
  `…_labels.xml.gz` ve SHA-256 `…_CHECKSUM.txt` [B: discogs-xml2db README].
- **Yapı [H]:**
  - `artists.xml`: `<members>`, `<groups>`, `<aliases>`, `<namevariations>`, `<realname>`.
  - `releases.xml`: `<extraartists><artist><id/><name/><role/></artist>` (release düzeyi)
    ve `<track>` içinde parça düzeyi `extraartists`; ayrıca `<genres>`, `<styles>`,
    `<country>`, `<released>`, `<master_id>`.
- **Ölçek ve süre:** discogs-xml2db örnek çıktısında ~12,5 M release yaklaşık 1280 release/sn
  hızla işleniyor, yani tek geçiş ~2,5 saat [B]. Bu Apache-2.0 araç SQLite'a da yazabiliyor [B].
  Ama projenin "tek dil, bağımlılık az" çizgisine göre `xml.etree.iterparse` ile **akış
  halinde süzmek** daha uygun.
- **Ne kazandırır:**
  - **Kredi:** Bugün Discogs kredileri albüm başına API'den geliyor. Dump'la "bu davulcunun
    çaldığı TÜM release'ler" tek yerel sorgu olur. API'deki
    `artists/{id}/releases?per_page=…` sınırı ortadan kalkar.
  - **Sahne:** `country='Japan' AND style IN ('Fusion','Jazz-Funk','City Pop'…)` ve
    `country='Turkey' AND style IN ('Psychedelic Rock','Folk Rock','Prog Rock'…)` ile
    dönem penceresi birleşince somut bir sahne komşuluğu çıkar.
  - **K9 notu:** label bilgisi gelir ama matrise girmez, yalnız saklanır.
- **K6 (artımlı):** dump her ay tam görüntü. Artımlılık için release kimliği ve
  `data_quality` / içerik özeti karşılaştırılır, yalnız değişen satırlar yazılır.

### 3.3 Wikidata

**Kimlik eşleme özellikleri:**
- [H, yüksek güven]: P434 MusicBrainz sanatçı ID, P436 MB release-group ID, P1953 Discogs sanatçı ID.
- [İ]: P1952 Metallum grup ID, P1989 Metallum kişi ID.
- [H, doğrula]: P2722 Deezer sanatçı ID, P3192 Last.fm ID, P1902 Spotify sanatçı ID.

**İçerik özellikleri [H, yüksek güven]:** P737 etkilendiği, P136 tür, P463 üyesi olduğu,
P527 parçaları/üyeleri, P1303 enstrüman, P740 kuruluş yeri, P495 köken ülke, P27 vatandaşlık,
P571 kuruluş, P1066 öğrencisi olduğu, P31=Q5 insan. Ülkeler: Q43 Türkiye, Q17 Japonya.

**Kapsama uyarısı [H]:** P737 yazar ve filozoflarda dolu, müzisyenlerde seyrek ve büyük
ölçüde İngilizce Vikipedi bilgi kutusundan aktarılmış durumda. **Önce ölçülmeli:**
kütüphanedeki 147 sanatçıdan kaçında en az bir P737 kenarı var? Sorgu §4.3'te.

**Graf bölünmesi [İ]:** 2025-05-09'dan beri bilimsel makaleler ayrı bir uç noktada. Müzik
sorguları `query.wikidata.org`'da değişmeden çalışır.

### 3.4 Last.fm

- **Etiketler:** `artist.getTopTags`, `album.getTopTags` ve `tag.getTopArtists&tag=japanese+fusion`.
  "Japon fusion", "anadolu rock" ve "türkçe rock" gibi etiketleri MB'de yok denecek kadar az
  kişi girmiş. Last.fm'de ise kalabalık etiketi on yıllardır birikiyor [H].
- **Benzerlik:** `artist.getSimilar` yanıtında 0–1 arası `match` var. `mbid` alanı çoğu zaman
  dolu, boşsa MB araması gerekir. K14 gereği eşleme kimlikle yapılmalı.
- **ToS riski:** "research/academic" kullanım izin istiyor [İ]. Proje kişisel bir araç.
  Ama kullanıcı bunu tezde ya da derste kullanırsa izin gerekir. Bu not CLAUDE.md'ye girmeli.

### 3.5 Genius (hip-hop ekseni için ayrıca)

`GET https://api.genius.com/songs/{id}` yanıtında `producer_artists`, `writer_artists`,
`custom_performances` ve `song_relationships` (type: samples, sampled_in, interpolates,
cover_of, remix_of…) alanları var [H]. Hip-hop'ta prodüktör ve sample ağı, prog'daki kadro
ağının karşılığı. ToS ve hız sınırı bu oturumda doğrulanamadı. Önce <https://docs.genius.com>
okunmalı.

---

## 4. Bu kullanıcı için ilk 5 öneri

Seçim ölçütleri:
1. Nişe katkı: prog metal ve fusion müzisyen kredileri, Türk rock sahnesi ve etkisi, Japon fusion.
2. Lisans temizliği.
3. Yeni bağımlılık ve maliyet.
4. K7 uyumu: gerekçeyi kendisi taşıyor mu?

### Öneri 1 — MusicBrainz ilişki genişletmesi (kadro + cover)  ·  Uyum: Yüksek

- **Neden:** Kredi ekseni projenin çekirdeği. Bugün yalnız "albümde kim çalmış" çekiliyor.
  "Bu kişi hangi gruplarda, hangi enstrümanla, hangi yıllarda çalmış" ve "kimin şarkısını
  cover'lamış" çekilmiyor. Lisans CC0, istemci ve hız sınırı aynı, yeni bağımlılık yok.
- **Uç noktalar:**
  - `GET /ws/2/artist/{mbid}?inc=artist-rels+url-rels&fmt=json` (kişi başına bir çağrı, önbellekli)
  - Mevcut release çağrısına `+work-rels+work-level-rels` (ek istek yok)
- **Strateji:** "kadro sıçraması", yani kişi → başka grup → o grubun albümü. Turne
  müzisyeni (`supporting musician`) köprüleri.
- **Örnek şablon (K7):** "Davulda {kişi} var. {kişi}, kütüphanendeki {grup} grubunda
  {yıl1}–{yıl2} arasında çaldı (MusicBrainz). Kütüphanende {grup}'tan {n} albüm var."
- **K14:** kenar ancak iki ucu da (kişi ve grup) kendi kredilerimizde ya da aday havuzunda
  varsa gerekçeye girer.
- **ToS notu:** MusicBrainz çekirdek verisi (ilişkiler dahil) CC0. 1 istek/sn ve anlamlı UA
  zorunlu. Önbellek kalıcı olabilir.

### Öneri 2 — Discogs CC0 aylık dump'ı (kredi + style + ülke)  ·  Uyum: Yüksek

- **Neden:**
  1. Kredilerde ölçek: kişinin tüm release'leri yerelde.
  2. **Japon fusion** ve **Türk rock** için en iyi sahne verisi: `country` + `styles` + yıl.
     Discogs'ta bu iki pazar koleksiyoncu ilgisi yüzünden iyi kataloglanmış [H, K19 ile ölçülmeli].
  3. API'nin 6 saat tazelik ve "gerektiğinden uzun saklama" maddesini aşar (§2.1).
- **Erişim:** `https://data.discogs.com/` → `discogs_YYYYMM01_artists.xml.gz` ve
  `discogs_YYYYMM01_releases.xml.gz`. SHA-256 doğrulaması yapılır.
- **Süzme planı:**
  1. `artists.xml`'den kütüphanedeki Discogs kişi kimliklerinin `groups` / `members` /
     `aliases` bilgisini çıkar. Sonuç: tanıdık kişiler + grupları.
  2. `releases.xml`'i akış halinde oku. Kredisi (`artists` / `extraartists`) bu kümeye
     değen release'leri tut. Ayrıca `country ∈ {Japan, Turkey}` ve `styles` niş
     listesindeki release'leri tut.
  3. Ortak veritabanına (`ortak.sqlite`) yaz. Şema değişikliği `docs/veri-sozlesmesi.md`'ye işlenir.
- **Örnek şablon:** "Discogs'ta 1978–1984 Japonya çıkışlı ve «Fusion» etiketli 312 release
  var. Kütüphanende bu kesitten 9 albüm var, bu sanatçıdan hiç yok."
- **ToS notu:** aylık dump'lar CC0. API Terms ayrı bir metin: CC0 Data ile Restricted Data
  ayrımı ve 6 saatlik tazelik maddesi var [İ, resmi metinden doğrulanmalı]. Dump boyutu ~10+ GB
  sıkıştırılmış [H]. API hız sınırı token'la dakikada 60 [H].

### Öneri 3 — Wikidata SPARQL (etki + sahne + kimlik eşleme)  ·  Uyum: Yüksek

- **Neden:** "Etki" ve "sahne" eksenleri için CC0 tek açık kaynak. Kimlik eşleme de bedava:
  MB→Discogs ve MB→Last.fm eşleşmesi sağlar, Metallum ve ProgArchives'e dış bağlantı verir.
  K14 gereği her eşleşme kimlikle kurulur.
- **Sorgu 1: kütüphane sanatçılarının etki ağı, iki yönde** (MBID'ler en çok 200'lük partilerle):
```sparql
SELECT ?yon ?a ?aMbid ?b ?bLabel ?bMbid WHERE {
  VALUES ?aMbid { "MBID-1" "MBID-2" }            # kütüphane sanatçıları
  ?a wdt:P434 ?aMbid .
  { ?a wdt:P737 ?b . BIND("etkilendi" AS ?yon) }
  UNION
  { ?b wdt:P737 ?a . BIND("etkiledi"  AS ?yon) }
  OPTIONAL { ?b wdt:P434 ?bMbid . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "tr,en,ja". }
}
```
- **Sorgu 2: Türk rock sahnesi** (kuruluş yeri ve dönem; tür QID'si yerine etiketle seçildi, QID'ler doğrulanmadı):
```sparql
SELECT DISTINCT ?s ?sLabel ?mbid ?discogs ?yerLabel ?kurulus ?turLabel WHERE {
  VALUES ?turAd { "Anatolian rock"@en "psychedelic rock"@en "progressive rock"@en "hard rock"@en "heavy metal"@en }
  ?tur rdfs:label ?turAd .
  ?s wdt:P136 ?tur .
  { ?s wdt:P495 wd:Q43 } UNION { ?s wdt:P27 wd:Q43 }      # Türkiye
  OPTIONAL { ?s wdt:P434  ?mbid }
  OPTIONAL { ?s wdt:P1953 ?discogs }
  OPTIONAL { ?s wdt:P740  ?yer }
  OPTIONAL { ?s wdt:P571  ?kurulus }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "tr,en". }
}
```
- **Sorgu 3: Japon fusion:** Sorgu 2 ile aynı, `?turAd` yerine `"jazz fusion"@en "jazz-funk"@en "city pop"@en`, ülke olarak `wd:Q17`, etiket dili `"ja,en"`.
- **Sorgu 4: kadro ve enstrüman** (Öneri 1 için çapraz doğrulama):
```sparql
SELECT ?kisi ?kisiLabel ?kisiMbid ?grupMbid ?enstrumanLabel WHERE {
  VALUES ?grupMbid { "MBID-1" }
  ?grup wdt:P434 ?grupMbid .
  { ?grup wdt:P527 ?kisi } UNION { ?kisi wdt:P463 ?grup }
  ?kisi wdt:P31 wd:Q5 .
  OPTIONAL { ?kisi wdt:P434 ?kisiMbid }
  OPTIONAL { ?kisi wdt:P1303 ?enstruman }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "tr,en". }
}
```
- **Örnek şablon:** "Wikidata'ya göre {B}, kütüphanendeki {A}'dan etkilenmiş ({B_Q}).
  Kütüphanende {A}'dan {n} albüm var."
- **Önce ölçüm (K19):** P737 kapsamını çıkar (kaç sanatçıda kenar var?). Sonra
  leave-one-artist-out sınamasıyla tavanı ölç: gizlenen sanatçı etki grafiğinde 1–2 adımda
  bulunuyor mu?
- **ToS notu:** Wikidata yapısal veri CC0. WDQS'de 60 sn sorgu tavanı, UA+IP başına dakikada
  60 sn işlem, dakikada 30 hatalı sorgu [İ]. Wikimedia User-Agent politikası zorunlu; varsayılan
  python-requests UA'sı engelleniyor [İ]. Paralel sorgu yok, sonuçlar kalıcı önbelleğe.

### Öneri 4 — Last.fm API (niş etiketler + benzerlik)  ·  Uyum: Yüksek / Orta

- **Neden:** Japon fusion ve Türk rock'ta MB ve LB'nin etiket ve dinleyici verisi ince.
  Last.fm'in kalabalık etiketleri ve `similar` sinyali bu nişlerde muhtemelen en zengin
  kaynak [H, ölçülmeli]. K10 "kalabalık katmanı" için ikinci, bağımsız bir ses olur.
- **Uç noktalar** (`https://ws.audioscrobbler.com/2.0/?format=json&api_key=…`):
  - `method=artist.getSimilar&mbid={mbid}`: `mbid` yoksa `artist={ad}` + `autocorrect=0`
  - `method=artist.getTopTags&mbid={mbid}`
  - `method=tag.getTopArtists&tag=japanese%20fusion`
  - `method=tag.getSimilar&tag=anadolu%20rock`
- **Örnek şablon:** "Last.fm dinleyicileri bu sanatçıyı en çok «japanese fusion» (412 kez) ve
  «city pop» ile etiketlemiş. Kütüphanende bu iki etiketi taşıyan 7 sanatçı var."
- **ToS notu (en dikkat gerektiren):**
  - Yalnız ticari olmayan kullanım.
  - Ticari **ya da araştırma/akademik** kullanım için partners@last.fm'den önceden izin [İ].
  - Veri alt-lisanslanamaz [İ].
  - Önbellek HTTP başlıklarına uymalı. Eski metne göre benzer ve chart verisi en az 1 hafta
    önbelleklenir [İ].
  - IP başına 5 istek/sn (5 dk ortalaması) [İ].
  - Last.fm'e bağlantılı kaynak gösterme [İ].
  - "100 MB saklama tavanı" doğrulanmadı.
  - API anahtarı `.env`'e girer, asla yazdırılmaz.
  - **Resmi metin (<https://www.last.fm/api/tos>) kod yazılmadan önce okunmalı.**

### Öneri 5 — ListenBrainz popularity + LB Radio + labs tag-similarity  ·  Uyum: Yüksek

- **Neden:**
  1. Yeni bir sanatçıdan hangi albüm önerilecek? Bugün MB release-group sırası kullanılıyor
     (yıl ya da ilk 25). `top-release-groups-for-artist` gerçek dinleyici kararını veriyor.
  2. "Bilinçli uzaklık"ta Coldplay vakası (karar günlüğü): `POST /1/popularity/artist`
     ile toplam dinleyici sayısından popülerlik cezası hesaplanabilir. 1000 MBID tek istekte
     gider, token gerekmez.
  3. LB Radio `mode=hard` doğrudan kuyruk keşfi. `country:(Turkey)` ve `country:(Japan)`
     sahne akışları var.
- **Uç noktalar [B]:**
  - `GET https://api.listenbrainz.org/1/popularity/top-release-groups-for-artist/{artist_mbid}`, `Authorization: Token …`
  - `POST https://api.listenbrainz.org/1/popularity/artist`, gövde `{"artist_mbids":[…]}`
  - `GET https://api.listenbrainz.org/1/explore/lb-radio?prompt=tag:(jazz fusion) country:(Japan)&mode=hard` (token)
  - `GET https://labs.api.listenbrainz.org/tag-similarity/json?tag=jazz%20fusion` (popüler etiketler dışarıda)
  - `GET https://api.listenbrainz.org/1/metadata/artist/?artist_mbids=…&inc=tag` (etiket sayıları)
- **ToS notu:**
  - Dinlenme verisi CC0.
  - İstemci başına 1 istek/sn ve `X-RateLimit-*` başlıklarına uyum [B].
  - UA biçimi `Uygulama/sürüm ( iletişim )`; geçersiz UA "uyarısız engellenebilir" [B].
  - Popularity top-* uçları ve LB Radio için kullanıcı token'ı şart; LB Radio token başına 5 sn'de 5 istek [B].
  - Labs uçları deneysel.

### Sıralamanın dışında kalan iki güçlü aday

- **AcousticBrainz CSV/JSON dump'ı:** K11'in sigortası. API yalnız "şimdilik" açık (§2.3).
  Bu yeni bir sinyal değil, mevcut sinyalin kalıcılığı. Bu yüzden ilk beşe girmedi, ama
  kısa vadede indirilmeli.
- **Genius API:** hip-hop ekseni için sample grafiği. ToS doğrulanınca 6. sıraya girer.

---

## 5. Elenenler: tek satırda gerekçe

| Kaynak | Gerekçe | Proje kuralı |
|---|---|---|
| Encyclopaedia Metallum, ProgArchives, AllMusic, Chosic, Music-Map/Gnod, Every Noise | API yok, kazıma gerekir | "Belgelenmemiş uç yok", RYM gerekçesi |
| Bandcamp, Songkick | Resmi keşif API'si yok ya da başvuruya kapalı | Aynı |
| Ekşi Sözlük / forumlar | API yok | Reddit gerekçesi |
| FMA, MTG-Jamendo ses dosyaları | Ses indirme yasak, katalog uyumsuz | "FMA'dan ses indirilmez" |
| Spotify related-artists, recommendations, audio-features | Yeni ve geliştirme modundaki uygulamalara kapalı [H] | — |
| TheAudioDB tam erişim | Ücretli (Patreon) [H] | K2 |
| MPD, LFM-1b/2b, Music4All | "Yalnız araştırma" lisansı ya da geri çekilmiş [H] | Lisans okunmadan girmez |

---

## 6. CLAUDE.md "Veri kaynakları" tablosuna taslak satırlar

*(Proje kuralı. Satırlar CLAUDE.md'ye **resmi sayfa okunduktan sonra** girmeli. [İ]/[H] işaretli hücreler kontrol edilmeli.)*

| Kaynak | Kullanım | Sınır |
|---|---|---|
| MusicBrainz ilişkileri | Kadro (`member of band` + enstrüman, tarih), turne müzisyeni, cover→besteci | CC0 (çekirdek), 1 istek/sn, UA zorunlu. `inc=artist-rels+url-rels` / `+work-rels+work-level-rels` |
| Discogs aylık dump | Krediler, üyeler/gruplar, style, ülke, yıl | **CC0**, `data.discogs.com`, ayda bir, ~10+ GB. API Terms (6 saat tazelik, Restricted Data) dump'a uygulanmaz [doğrula] |
| Wikidata | Etki (P737), sahne (P740/P495/P571), kimlik eşleme | CC0. WDQS 60 sn tavan, UA+IP başına dakikada 60 sn işlem, UA politikası zorunlu |
| Last.fm | Kalabalık etiketleri, benzer sanatçı | Anahtar ücretsiz. **Yalnız ticari olmayan**; araştırma/akademik kullanım izne tabi. IP başına 5/sn. Önbellek HTTP başlıklarına göre, benzer veri ≥1 hafta. Kaynak gösterme zorunlu [doğrula] |
| ListenBrainz popularity / LB Radio | En çok dinlenen albüm, popülerlik sönümü, kuyruk keşfi | CC0. 1 istek/sn. top-* ve lb-radio **token ister**; POST popularity token istemez (≤1000 MBID) |
| AcousticBrainz dump | K11 sigortası | CC0. 29,46 M gönderim. CSV öznitelik dump'ı + 30×1 M JSON arşiv. API "şimdilik" açık |

---

## 7. Açık sorular / kullanıcının doğrulaması gerekenler

1. **Discogs API Terms**: 6 saat tazelik ve "gerektiğinden uzun saklama" maddeleri CC0 Data'ya
   da uygulanıyor mu? Uygulanıyorsa mevcut kalıcı Discogs önbelleği ToS'a aykırı demektir.
   O durumda Öneri 2 öncelik kazanır.
2. **Last.fm ToS**: "research/academic" kapsamı. Proje tezde ya da derste kullanılacak mı?
   Kullanılacaksa izin e-postası gerekir.
3. **MPD lisansı**: kişisel, ticari olmayan bir keşif aracı "research" sayılır mı? Hocaya
   danışılabilecek bir soru.
4. **Deezer ToS ve `/artist/{id}/related`**: bu oturumda yeniden doğrulanamadı. Proje Deezer'ı
   zaten kullandığı için CLAUDE.md'deki satıra resmi ToS maddeleri eklenmeli: önbellek ve
   kaynak gösterme.
5. **Kapsama ölçümleri (K19):**
   - P737 kenar sayısı
   - MB `member of band` kapsamı (kütüphanedeki gruplar)
   - Discogs dump'ında Türkiye ve Japonya niş style sayıları
   - Last.fm etiket kapsamı

   Her biri leave-one-artist-out ile **tavan** ve **iki paydalı recall** olarak, mevcut yollarla kıyaslanarak raporlanmalı.

---

## Kaynaklar

**Birincil kaynaklar (bu oturumda okundu [B]):**
- ListenBrainz API kök ve hız sınırı belgesi: <https://github.com/metabrainz/listenbrainz-server/blob/master/docs/users/api/index.rst> (yayın: <https://listenbrainz.readthedocs.io/en/latest/users/api/index.html>)
- ListenBrainz dump belgesi: <https://github.com/metabrainz/listenbrainz-server/blob/master/docs/users/listenbrainz-dumps.rst> (yayın: <https://listenbrainz.readthedocs.io/en/latest/users/listenbrainz-dumps.html>, indirme: <https://listenbrainz.org/data>)
- LB popularity API kaynak kodu: <https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/webserver/views/popularity_api.py>
- LB token zorunluluğu ve `MAX_ITEMS_PER_GET`: <https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/webserver/views/api_tools.py>
- LB Radio ucu: <https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/webserver/views/explore_api.py>
- LB metadata ucu: <https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/webserver/views/metadata_api.py>
- LB labs similar-artists ve tag-similarity: <https://github.com/metabrainz/listenbrainz-server/tree/master/listenbrainz/labs_api/labs/api>
- LB Radio istem söz dizimi: <https://github.com/metabrainz/troi-recommendation-playground/blob/main/docs/lb_radio.rst>
- AcousticBrainz indirme sayfası şablonu: <https://github.com/metabrainz/acousticbrainz-server/blob/master/webserver/templates/index/downloads.html> (yayın: <https://acousticbrainz.org/download>)
- AcousticBrainz CC0 ve "şimdilik açık" ifadesi: <https://github.com/metabrainz/acousticbrainz-server/blob/master/webserver/templates/index/index.html>
- musicbrainz-docker gereksinimleri: <https://github.com/metabrainz/musicbrainz-docker>
- MB web servisi include adları: <https://github.com/metabrainz/musicbrainz-server/blob/master/lib/MusicBrainz/Server/WebService/WebServiceInc.pm>
- discogs-xml2db (dump yapısı ve ölçeği): <https://github.com/philipmat/discogs-xml2db>

**İkincil kaynaklar ve resmi sayfalar (arama sonuçlarıyla ulaşıldı, tam metin okunamadı [İ]):**
- MusicBrainz veri lisansı: <https://musicbrainz.org/doc/About/Data_License>, <https://musicbrainz.readthedocs.io/en/latest/musicbrainz_database/index.html>, <https://en.wikipedia.org/wiki/MusicBrainz>
- Last.fm API ToS: <https://www.last.fm/api/tos>, <https://www.last.fm/api/intro>, <https://www.last.fm/legal>
- Last.fm eski ToS alıntıları: <https://github.com/jkovacs/lastfm-java/wiki/Getting-Started>, <https://github.com/api-evangelist/lastfm>
- Discogs API Terms of Use: <https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use>
- Discogs geliştirici belgesi: <https://www.discogs.com/developers>; dump'lar: <https://data.discogs.com/>
- Discogs 6 saat / kaynak gösterme tartışmaları: <https://github.com/WOIII-me/Discogs-MCP/pull/69>, <https://github.com/johnzastrow/myvinyl/issues/18>, <https://github.com/asuteau/sillon/issues/43>
- WDQS sınırları (R paket belgesindeki alıntı): <https://archive.linux.duke.edu/cran/web/packages/WikidataQueryServiceR/refman/WikidataQueryServiceR.html>
- WDQS UA politikası: <https://phabricator.wikimedia.org/T226709>
- WDQS graf bölünmesi: <https://meta.wikimedia.org/wiki/WikiCite/WDQS_graph_split>, <https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/WDQS_backend_update/October_2023_scaling_update>
- Wikidata Metallum kimlik özelliği: <https://citygraph.abudhabi.nyu.edu/wiki/Property:P1989>
- Wikidata'da ProgArchives kimliği örneği: <https://www.wikidata.org/wiki/Q315811>
- Metallum resmi olmayan sarmalayıcılar: <https://en.wikipedia.org/wiki/Encyclopaedia_Metallum>, <https://github.com/lukjak/enmet>, <https://pypi.org/project/python-metallum/>
- ProgArchives yasal uyarısı: <https://tostracker.app/document/progarchivescom-tos>, <http://www.progarchives.com/Legalnotice.asp>
- ListenBrainz Listens Dataset (ISMIR 2024): <https://ismir2024program.ismir.net/poster_317.html>

**Bu oturumda doğrulanamayan, kullanıcının okuması gereken resmi sayfalar [H]:**
- Deezer API: <https://developers.deezer.com/api/artist>, şartlar: <https://developers.deezer.com/termsofuse>
- Spotify Web API değişiklikleri (2024-11-27): <https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api>
- Genius API: <https://docs.genius.com/>
- Setlist.fm API: <https://api.setlist.fm/docs/1.0/index.html>
- Million Playlist Dataset: <https://www.aicrowd.com/challenges/spotify-million-playlist-dataset-challenge>
- Wikidata lisansı: <https://www.wikidata.org/wiki/Wikidata:Licensing>; P737: <https://www.wikidata.org/wiki/Property:P737>
- Wikimedia User-Agent politikası: <https://meta.wikimedia.org/wiki/User-Agent_policy>
- MusicBrainz hız sınırı: <https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting>
