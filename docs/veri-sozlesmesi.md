# Veri Sözleşmesi

Tüm kalıcı veri `data/db/kesif.sqlite` içinde. Ara çıktılar Parquet olarak `data/`.
Şema değişikliği bu dosyaya yansıtılmadan yapılmaz.

## albums
Kütüphanedeki her albüm için bir satır.

| Alan | Tip | Not |
|---|---|---|
| album_id | TEXT PK | yerel hash (sanatçı+albüm+yıl) |
| mbid | TEXT | MusicBrainz release-group ID, NULL olabilir |
| artist | TEXT | |
| title | TEXT | |
| year | INTEGER | |
| country | TEXT | zenginleştirmeden |
| label | TEXT | |
| path | TEXT | yerel klasör yolu |
| track_count | INTEGER | |
| eklenme_tarihi | TEXT | artımlı çalışma için |
| mbid_yok | INTEGER | 1 = kullanıcı "MusicBrainz karşılığı yok" dedi; eşleştirme ekranında bir daha sorulmaz |

`album_id` sanatçı+albüm+yıl normalize edilip hash'lenerek üretilir
(`python/metin.py:album_kimligi`). Albümü başka klasöre taşımak kimliği değiştirmez —
zenginleştirme emeği korunur. Normalizasyon "Meddle (2011 Remaster)" ile "Meddle"i
aynı albüm sayar; `title` alanında ham etiket durur, kimlikte normalize hali.

## dosyalar
Artımlı taramanın belleği (K6). Her ses dosyası için bir satır.

| Alan | Tip | Not |
|---|---|---|
| yol | TEXT PK | mutlak dosya yolu |
| album_id | TEXT FK | ON DELETE CASCADE |
| mtime | REAL | değişiklik zamanı |
| boyut | INTEGER | bayt |

mtime **ve** boyut değişmemişse dosyanın etiketi hiç okunmaz. Bu tablo aynı zamanda
silinen dosyaları tespit etmeyi ve `albums.track_count` / `albums.path` alanlarını
yeniden hesaplamayı sağlar.

## credits
Kredi grafiğinin temeli. Albüm–kişi–rol üçlüsü.

| Alan | Tip | Not |
|---|---|---|
| album_id | TEXT FK | |
| person_id | TEXT | MusicBrainz artist ID tercih edilir |
| person_name | TEXT | |
| role | TEXT | normalize edilmiş: drums, guitar, producer, mix... |
| kaynak | TEXT | musicbrainz / discogs |

Rol normalizasyonu şart: Discogs "Drums", "Drums [Additional]", "Percussion" gibi
onlarca varyant döndürür. Eşleme tablosu `python/enrich/rol_eslemesi.py` içinde.

## tags
| Alan | Tip |
|---|---|
| album_id | TEXT FK |
| tag | TEXT |
| agirlik | REAL |

## audio_features
Albüm düzeyinde ses profili. **Birincil anahtar `(album_id, kaynak)`** — aynı albümün
hem yerel hem dış profili yan yana durabilir.

`kaynak` değerleri:
- `yerel` — librosa, kullanıcının FLAC dosyalarından (en güvenilir)
- `acousticbrainz` — kayıt MBID'siyle çekilen hazır analiz (sende olmayan albümler için)
- `onizleme` — iTunes/Deezer 30 sn önizlemesinden (planlanan)

**Kaynaklar arası ham değer kıyaslanamaz** (ölçüldü: spektral merkez r=0.80 ama
librosa ort 2330, AcousticBrainz ort 1378). Karşılaştırma kaynak içinde
standartlaştırılarak yapılır.

| Alan | Tip |
|---|---|
| album_id | TEXT FK |
| kaynak | TEXT — PK'nın parçası |
| tempo_medyan | REAL |
| tempo_iqr | REAL |
| dinamik_aralik | REAL |
| nabiz_netligi | REAL — tempogram tepe/ortalama; nabız ne kadar net |
| vurus_degiskenligi | REAL — vuruş aralıklarının değişim katsayısı |
| spektral_merkez | REAL |
| onset_hizi | REAL — yalnızca AcousticBrainz |
| dans_edilebilirlik | REAL — yalnızca AcousticBrainz |
| akor_degisim_hizi | REAL — yalnızca AcousticBrainz |
| parca_sayisi | INTEGER — özetin kaç parçadan çıktığı |

`ritmik_karmasiklik` sütunu ELENDİ (eski veritabanlarında duruyor, kullanılmıyor):
tüm türlerde 0.88'e sıkışıp hiçbir şey ayırt etmiyordu. Yerine gelen iki ölçüt
nabız düzenliliğini ölçer, teknik zorluğu değil — bkz. karar günlüğü.

## plays
Dinleme geçmişi (Symfonium / ListenBrainz / Last.fm dışa aktarımı).
Gün düzeyinde toplanır: aynı gün aynı parça 3 kez dinlendiyse tek satır, `adet=3`.

| Alan | Tip | Not |
|---|---|---|
| album_id | TEXT FK | |
| tarih | TEXT ISO | gün (YYYY-AA-GG) |
| track | TEXT | |
| adet | INTEGER | o gün kaç kez |
| kaynak | TEXT | lastfm / listenbrainz / symfonium |

`UNIQUE(kaynak, album_id, tarih, COALESCE(track,''))` — içe aktarım idempotenttir,
aynı dosyayı iki kez aktarmak sayıları şişirmez. `kaynak` ayrımı olmasaydı iki farklı
dışa aktarım aynı günü kapsadığında biri diğerini ezerdi.

## Ara çıktı: data/ozellikler.parquet
`matris_kur.py` üretir, R tarafı okur. Bir satır = bir albüm.

| Sütun | Not |
|---|---|
| album_id | anahtar |
| kredi__&lt;isim&gt; | müzisyen ikili göstergesi, satır L2 normalize |
| sahne__ulke:XX / label:X / donem:1980lar | tek-sıcak, satır L2 normalize |
| etiket__&lt;etiket&gt; | ağırlık, satır L2 normalize |
| ses__&lt;öznitelik&gt; | robust z (medyan/IQR), eksikte 0 |

Sütun adı `blok__ad` biçimindedir; R tarafı blokları bu önekten ayırır ve blok
ağırlıklarını `R/config.R`'de uygular. Yan dosya `data/ozellikler_sozluk.csv`
her sütunun bloğunu, ham adını ve kaç albümde geçtiğini listeler.

## memberships
Kümeleme çıktısı. Her albüm × küme için bir satır (bulanık üyelik).

| Alan | Tip | Not |
|---|---|---|
| album_id | TEXT FK | |
| kume_id | INTEGER | |
| uyelik | REAL | 0–1, satır toplamı albüm başına 1 |
| calisma_id | TEXT | hangi kümeleme çalışması — versiyonlama |

## temsilciler
Kümeleme anında seçilen temsilci albümler (K4). Arayüz bunları okur.

| Alan | Tip | Not |
|---|---|---|
| calisma_id | TEXT | PK'nın parçası |
| kume_id | INTEGER | PK'nın parçası |
| album_id | TEXT FK | PK'nın parçası |
| sira | INTEGER | 0 = kümenin en tipik albümü |
| uyelik | REAL | o kümedeki üyelik derecesi |

Neden saklanıyor: arayüz temsilcileri yeniden hesaplasaydı, farklı ağırlık ya da
tohumla başka albümler çıkabilir ve kullanıcı isimlendirdiği kümeyi tanıyamazdı.
Gösterilen şey, çalışmanın verdiği karar olmalı.

## stem_profili
Albüm × stem düzeyinde icra ölçümü — Demucs `htdemucs` çıktısından (K12).
**Bir albüm tek geçişte dört stem'i birden üretir**; ayrıştırma pahalı olan kısım
olduğu için gitar profili istendiğinde davul yeniden ayrıştırılmaz.

| Alan | Tip | Not |
|---|---|---|
| album_id | TEXT | `albums.album_id` VEYA `adaylar.aday_id` — PK'nın parçası |
| tur | TEXT | album / aday |
| stem | TEXT | drums / bass / other / vocals — PK'nın parçası |
| onizleme_url | TEXT | ölçümün yapıldığı 30 sn klip |
| nota_vurus | REAL | vuruş başına nota — tempodan bağımsız yoğunluk |
| tempo | REAL | |
| enerji_payi | REAL | stem'in mikste kapladığı yer |
| dinamik_db | REAL | 95./5. yüzdelik farkı |
| sustain_orani | REAL | atak sonrası taşınan pay — uzun nota mı staccato mu |
| parlaklik | REAL | spektral merkez, Hz |
| harmonik_pay | REAL | HPSS harmonik enerji payı; temiz/tonal yüksek, distorsiyonlu düşük |
| zcr | REAL | sıfır geçiş oranı |
| izgara_entropi | REAL | **yalnız drums** — makine düşük, insan yüksek |
| tekme_payi / trampet_payi / zil_payi | REAL | **yalnız drums** — <120 / 120–2000 / >6000 Hz |
| perde_medyan | REAL | **yalnız perdeli stem** — C1'den yarım ton (0=C1, 12=C2) |
| perde_araligi | REAL | **yalnız perdeli stem** — 90./10. yüzdelik farkı |
| vibrato_hizi | REAL | **yalnız perdeli stem** — perde eğrisi salınım hızı, Hz |

**Ton dokusu için üç ölçüt ölçülüp ELENDİ** (sekiz zıt sanatçıda sınandı):
`duzluk` (spektral düzlük) Demucs çıktısında 0.000–0.012'ye sıkıştı — ayrıştırma
kaynak dışı binleri sıfırladığı için geometrik ortalama çöküyor. `tepe_orani`
(tepe/RMS dB) yönü bile tutturamadı: Annihilator 17.7 ile en yüksek, Animals As
Leaders 12.9. Spektral kontrast da ters çıktı (A-Ha 24.2 > Annihilator 21.1).
Ayakta kalan `harmonik_pay` ve `zcr` doğru sıralıyor (Annihilator 0.774/0.160,
A-Ha 0.973/0.039). n=8'de ikisi de `parlaklik` ile neredeyse aynı sıralamayı
verdiği için karar ERTELENMİŞTİ; n≈270'te `olcut_denetimi.py` ile verildi:
**`harmonik_pay` dört stem'de de bağımsız bilgi taşıyor** (artık payı 0.45–0.73),
`zcr` ise bas/gitar/vokalde parlaklığın kopyası çıkıp elendi (davulda kaldı).
Gitarda beklenenin tersi oldu — elenen `parlaklik`, kalan distorsiyon ölçütü.
Ertelemek doğru olmuş: sekiz satıra bakılıp karar verilseydi ikisi de yanlış
gerekçeyle atılırdı.

`sustain_orani` iki kez tanımlandı. İlki ("RMS tepenin %20'sinin üstünde kalan
kare oranı") ELENDİ: sürekli çalan stem'de tanım gereği 1.00 çıkıyordu — Alice In
Chains, Animals As Leaders ve Adam Nitti'nin `other` stem'leri tam 1.00 verdi.
İkinci tanım nota başına çürüme oranı; davulda iyi ayırıyor (April Wine 0.21,
Annihilator 0.94), `other` stem'inde dar (0.89–0.99). Dar olması işe yaramadığı
anlamına GELMİYOR: denetimde dört stem'de de ayakta kaldı (artık payı 0.57–0.85),
yani dar aralıkta da olsa diğer sütunlardan bağımsız bilgi taşıyor.

Davula özgü sütunlar perdeli stem'lerde NULL, perde sütunları davulda NULL. Bu
kasıtlı: tek tabloda tutmak stem'ler arası sorguyu (`enerji_payi` kıyaslaması gibi)
mümkün kılıyor, ölçülemeyen alana sayı uydurmak yerine NULL bırakılıyor.

**Rol → stem eşlemesi** (`python/enrich/icra_profili.py:ROL_STEM`):
drums/percussion → `drums`, bass → `bass`, vocals/backing_vocals → `vocals`,
guitar/keyboards/piano/organ/synthesizer/saxophone → `other`.
Demucs dört kaynak ayırır; gitarla klavyeyi ayırmaz. Bu yüzden "other"a düşen
rollerin profili enstrümana değil **o albümdeki melodik katmana** aittir —
gitar trio'sunda gitardır, klavyeli bir kayıtta ikisinin karışımıdır. Sınır
biliniyor ve arayüzde yazılı.

**Yabancı anahtar YOK ve bu kasıtlı.** Sahip olunmayan aday albümler de
profilleniyor (`tur='aday'`) — öneri "bu albümün davulcusu Duplantier
kalibresinde" diyebilsin diye. Adaylar `adaylar` tablosunda olduğu için
`albums`'a bağlı bir kısıt bu satırları reddediyordu. Kimlik uzayı ortak:
`aday_id` de `album_id` de `album_kimligi()` ile türetiliyor, yani bir aday
sonradan kütüphaneye girerse ölçülmüş profili olduğu yerde kalır.

Müzisyen düzeyine çıkarma `python/muzisyen.py:icra_profilleri` içinde: kişinin
`credits`'te o rolde geçtiği albümlerin stem satırları alınır, sütun sütun
**medyan**'ı hesaplanır (ortalama değil — tek bozuk klip medyanı bozamaz).

## davul_profili
Müzisyen düzeyinde davul profili — `stem_profili`'nin öncülü, hâlâ okunuyor.
`icra_profilleri()` önce `stem_profili`'ne bakar, orada satır yoksa buraya düşer;
33 profil burada duruyor ve yeniden ayrıştırma maliyetine girmemek için silinmedi.

| Alan | Tip | Not |
|---|---|---|
| kisi_anahtar | TEXT | normalize_esleme(ad) — PK'nın parçası |
| rol | TEXT | drums (ileride bass/guitar) — PK'nın parçası |
| kisi_adi | TEXT | okunabilir ad |
| nota_vurus | REAL | vuruş başına nota — tempodan bağımsız yoğunluk |
| izgara_entropi | REAL | 16'lık ızgara entropisi; programlanmış beat düşük, insan yüksek |
| tekme_payi / trampet_payi / zil_payi | REAL | <120 Hz / 120–2000 Hz / >6000 Hz enerji payı |
| dinamik_db | REAL | davul stem'inin 95./5. yüzdelik farkı |
| tempo | REAL | |
| klip_sayisi | INTEGER | medyanın kaç klipten çıktığı |
| rol_sayisi | INTEGER | kişinin toplam farklı rol sayısı — tanı |
| rol_kredi_payi | REAL | bu roldeki kredi / tüm kredileri — tanı |
| ornek_onizleme | TEXT | kullanıcının DUYABİLMESİ için 30 sn URL |

Kaynak her zaman 30 sn önizleme — tek kaynak olması karşılaştırmayı geçerli kılıyor.

`rol_sayisi` ve `rol_kredi_payi` OTOMATİK ELEME İÇİN DEĞİL, kullanıcının yargılaması
için. Eşik denendi ve bırakıldı: %25 kredi payı Bruce Swedien'i (11 rollü mühendis,
%13) doğru eliyor ama Matt Cameron'ı da eliyor (%22 — Soundgarden'da şarkı da
yazdığı için). Rol genişliği de ayırmıyor (Swedien 11, Bottrell 9, Cameron 8).
Temiz bir kural olmadığı için arayüz sayıyı gösterip uyarı basıyor.

## kisi_eslesme
Aynı kişinin farklı yazımları. Profil anahtarı `normalize_esleme(person_name)`
olduğu için kaynak ikilemesi (`discogs:NNN` ↔ MusicBrainz UUID) ve tipografik
fark (`O'Brien` / `O'Brien`) zaten birleşiyor — ölçüldü, bölünen kimlik 0/4541.
Bu tablo ADIN KENDİSİ farklı olan durumu çözer.

| Alan | Tip | Not |
|---|---|---|
| anahtar | TEXT PK | `normalize_esleme(varyant ad)` |
| kanonik | TEXT | `normalize_esleme(kalacak ad)` |
| kaynak | TEXT | musicbrainz / elle |

Kaynak MusicBrainz alias verisi (`/artist/{mbid}?inc=aliases`). **İki kısıt
var ve ikisi de gerekli:**
1. Yalnız İKİ TARAFI DA kredilerde var olan adlar yazılır. MusicBrainz'in
   bilmediğimiz bir kişiye dair iddiası veritabanına sızmamalı.
2. Yalnız `type=Person`. Grup aliasları kişi grafiğini bozar.

Kanonik ad: kütüphanede en çok kredisi olan yazım, eşitlikte Latin yazımlı.
Az kullanılan yazım çoğa katılır, böylece mevcut profillerin çoğu korunur.

Üretim: `python -m python.enrich.kisi_birlestir`. Okuma tarafı iki yerde ve
İKİSİ DE gerekli — `python/muzisyen.py:_anahtar` ve
`python/enrich/icra_profili.py:muzisyen_profilleri`. Biri birleştirip diğeri
birleştirmezse kişi arayüzde görünür ama icra profili "yok" çıkar.

## ses_kumesi / ses_kume_adi
Türü ETİKETTEN değil sesten keşfeden kümeleme (K18). CLAP gömüsü PCA ile 16
boyuta indirilip k-ortalamalar uygulanıyor; 512 boyutta siluet 0.10'da takılıyor
(mesafe yoğunlaşması), 16 boyutta 0.168.

| Alan | Tip | Not |
|---|---|---|
| album_id | TEXT PK | |
| kume | INTEGER | |
| merkez_uzakligi | REAL | küme adı, merkeze en yakın sanatçılardan üretilir |

`memberships` ile AYNI ŞEY DEĞİL — o kredi/etiket/sahne matrisinden geliyor.
Ölçüldü: uyumları ARI 0.073, yani iki ayrı bakış ("kim çalmış" ve "kulağa nasıl
geliyor").

`ses_kume_adi (kume PK, ad)` kullanıcının verdiği isim. Kümeleme yeniden
koşarsa numaralar değişir ve bu tablo temizlenmelidir.

## adaylar (Faz 2)
Üretilen aday albümler. `albums` yalnızca SAHİP OLUNANLARI tutar; adaylar burada.

| Alan | Tip | Not |
|---|---|---|
| aday_id | TEXT | album_kimligi ile aynı türetme |
| calisma_id | TEXT | hangi kümeleme çalışmasına göre üretildi |
| eksen | INTEGER | hangi küme için |
| strateji | TEXT | kredi_sicramasi / sahne_komsulugu |
| artist / title / year | | Latin yazım varsa o (özgün ad `dayanak`ta) |
| mbid / discogs_id | TEXT | kaynak kimliği |
| skor | REAL | strateji içinde sıralama |
| gerekce | TEXT | K7 şablonu, gerçek sayılarla dolu |
| dayanak | TEXT | JSON — gerekçedeki her sayının kaynağı |
| onizleme_url | TEXT | 30 sn iTunes/Deezer |

PK `(calisma_id, eksen, strateji, aday_id)`: aynı albüm iki farklı stratejiden
gelebilir ve ikisinin gerekçesi farklıdır — ikisi de saklanır.

## feedback (Faz 3)
| Alan | Tip | Not |
|---|---|---|
| aday_id | TEXT | PK'nın parçası |
| calisma_id | TEXT | PK'nın parçası |
| eksen | INTEGER | |
| karar | TEXT | begendim / tutmadi / zaten_biliyorum |
| tarih | TEXT | |

## clusters
| Alan | Tip | Not |
|---|---|---|
| kume_id | INTEGER | PK, `calisma_id` ile birlikte |
| calisma_id | TEXT | PK'nın diğer yarısı — çalışmalar arası versiyonlama |
| kullanici_adi | TEXT | kullanıcının verdiği isim |
| stabilite | REAL | bootstrap Jaccard ortalaması |
| stabil_mi | INTEGER | 0/1 — eşik 0.6 |


