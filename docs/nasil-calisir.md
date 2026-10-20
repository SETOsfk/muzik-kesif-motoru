# Müzik Keşif Motoru — Nasıl Çalışır?

Güncel: 2026-10-20 · Sürüm 0.2.0

## 1. Amaç

Kütüphanendeki albümlerden zevk eksenlerini (tarzlarını) çıkarır ve her eksen
için **sende olmayan** sanatçılar önerir. Her önerinin yanında **neden**
önerildiği, gerçek sayılarla yazar. Sistem LLM kullanmaz ve maliyeti 0 TL'dir.

## 2. Boru hattı (uçtan uca)

| Adım | Ne yapılır | Kod |
|---|---|---|
| 1. Alım | FLAC etiketleri okunur, ya da Spotify kütüphanesi / sanatçı listesi aktarılır | `python/ingest/`, `python/aktarim.py`, `python/spotify.py` |
| 2. Zenginleştirme | MusicBrainz + Discogs kredileri (kim çalmış, prodüktör), MBID eşleştirme | `python/enrich/krediler.py`, `mbid_eslestir.py` |
| 3. Ses analizi | librosa öznitelikleri, CLAP ses gömüsü, Demucs ile stem ayırma (davul/bas/gitar/vokal icra profili) | `python/enrich/ses_ozellikleri.py`, `etiket_clap.py`, `enrich/icra_profili.py` |
| 4. Kümeleme | Bulanık c-ortalamalar (FCM), boyut indirgeme (spektral/PCA), küme sayısı Xie-Beni + entropi + bootstrap Jaccard ile | `python/kumeleme/` |
| 5. Aday üretimi | Her eksen için 6 strateji aday üretir (bkz. §3) | `python/discover/adaylar.py` |
| 6. Deste | Adaylar sıralanıp kaydırmalı kartlara dönüşür (bkz. §4) | `python/kesif.py` |
| 7. Geri bildirim | Her kaydırma kaydedilir, sıralamayı ve kaynak payını günceller | `python/geri_bildirim.py` |

Etkin kümeleme: `20260928T190536-c12-m1.4-spektral12` — 12 tarz, m = 1,4,
50 bootstrap'ta 12/12 stabil.

**Neden bulanık kümeleme?** Bir albüm aynı anda birden fazla tarza ait
olabilir (ör. hem prog metal hem füzyon). Üyelik dereceleri doğrudan öneri
ağırlığı olarak kullanılır.

## 3. Öneri kaynakları (6 strateji)

| Strateji | Soru | Veri | Durum |
|---|---|---|---|
| **Çalma listesi birlikteliği** | Bu sanatçıyı seven insanlar listelerine yanına neyi koyuyor? | 482 Deezer listesi, 45.899 parça, 10.360 sanatçı; normalize PMI + kanıt büzülmesi `n/(n+1)` | Destede ana kaynak |
| **Ses benzerliği** | Kulağa sendekine benzeyen ne var? | CLAP gömüsü, hubness düzeltmeli; «çok sesli» kural: en yakın 3 albümün ≥ 2'si eksende olmalı | Destede ana kaynak |
| **Melez** | İkisi birlikte | Liste ve ses sıralarının karşılıklı sıra kaynaşması (RRF, k = 60, ağırlık 1:2 ses lehine) | Destede ana kaynak |
| **Kredi sıçraması** | Sevdiğin müzisyenler başka nerede çaldı? | MusicBrainz/Discogs kredileri | «Cesur» kaynak |
| **Sahne komşuluğu** | Dinleyici kalabalığı neyi birlikte dinliyor? | ListenBrainz benzer sanatçılar | «Cesur» kaynak |
| **Bilinçli uzaklık** | Tarzlarına uzak ama komşuların sevdiği ne? | Kalabalık grafiğinde 2 adım, eksen-özgüllüğüyle sıralı | «Cesur» kaynak |

Popülerlik yanlılığı her yolda ayrıca düzeltilir (PMI, hubness düzeltmesi,
eksen-özgüllüğü) — ünlü olduğu için değil, sana yakın olduğu için önerilsin.

## 4. Deste kartı nasıl seçiliyor?

1. **Strateji içi sıra:** stratejinin kendi skoru
   + **geri bildirim kayması** — beğendiğin sanatçılara ses olarak yakın olan
   yukarı, tutmadıklarına yakın olan aşağı (en çok 0,5 σ)
   + **uzlaşma ödülü (yeni)** — aynı sanatçıyı başka bağımsız yollar da
   gösteriyorsa her biri için +0,5 σ (en çok 1 σ).
2. **Stratejiler arası pay:** Thompson örneklemesi. Her kaynak için gerçek
   kararlarından Beta(1 + beğendim, 1 + tutmadı); sende tutan kaynaktan daha
   çok kart gelir, az veriyle bile her kaynak örneklenmeye devam eder.
3. **Eksenler arası:** sırayla dönülür; adlandırdığın eksenler önce.
4. **Tekrar yok:** karar verdiğin ya da listende olan sanatçı bir daha gelmez.
5. **Tekrarlanabilir:** rastgelelik çalışma + karar sayısıyla tohumlanır;
   aynı durum aynı desteyi verir.

Kararlar: sağ = listeme (beğendim), sol = geç (tutmadı), yukarı = zaten
biliyorum. «Zaten biliyorum» zevk isabetine girmez, yalnız keşif oranına.

## 5. Gerekçe

Gerekçe şablondan, kaydedilmiş sayılardan kurulur (`python/gerekce.py`), iki
dilde. Örnek:

> Çalma listelerinde Meshuggah ile yan yana duruyor: 5 ayrı listede birlikte,
> bağ gücü +0,67. Sesi kütüphanendeki birden çok albüme yakın: «Obzen»,
> «Nothing». Ayrıca bağımsız olarak ortak müzisyenler de bu sanatçıyı gösteriyor.

≤ 3 listeye dayanan bağ «zayıf kanıt» olarak işaretlenir.

## 6. Ölçüm (K19)

Her yöntem değişikliği **leave-one-artist-out** ile ölçülür
(`python/degerlendirme.py`): bir sanatçının tüm albümleri gizlenir, motor onu
geri bulabiliyor mu? Raporlanan: tavan (havuzda var mı), recall@1/5/10/50, MRR,
medyan sıra. Güncel (spektral çalışma, 147 sanatçı):

| Yol | @50 | Yüzdelik sıra (küçük iyi) |
|---|---|---|
| Liste birlikteliği | 0,15 | 0,094 |
| Ses (çok sesli) | 0,03 | 0,045 |
| Melez (çok sesli) | 0,08 | 0,076 |

Gerçek zevk ise kararlarından ölçülür: kaynak başına beğeni oranı, Wilson
%90 aralığıyla, en az 4 kararla (Sayılarla sayfası).

## 7. Bu sürümde yapılanlar (2026-10-20)

- **Kaynak uzlaşması:** birden çok bağımsız kanıtın gösterdiği sanatçı öne
  alınır ve kart bunu söyler. Melezin kendi kaynakları iki kez sayılmaz. Eşit
  skorlarda da eşitlik bozucu.
- **Daha stabil geri bildirim:** kayma ölçeği en büyük değer yerine 90.
  yüzdelikten alınıyor. Tek bir aykırı aday artık tüm kaymaları ezmiyor, yeni
  bir kararla sıra sıçramıyor.
- **Ölçüm yolu:** Sayılarla sayfasında «tek kanıt yolu» ↔ «birden çok kanıt
  yolu» beğeni oranı. Uzlaşma ödülü henüz ölçülmedi; birden çok yolun
  isabeti yüksek çıkmazsa kaldırılacak.

## 8. Kullanılan kaynaklar ve araçlar

**Veri (hepsi ücretsiz):** MusicBrainz (kimlik, krediler), Discogs (detaylı
krediler), ListenBrainz (benzer sanatçılar), Deezer (çalma listeleri, 30 sn
önizleme), iTunes Search (önizleme), AcousticBrainz (sende olmayan kaydın ses
profili), CritiqueBrainz (yorumlar), Spotify (yalnız giriş + kütüphane okuma).
**Kullanılmayanlar:** Reddit (API reddedildi), RateYourMusic (ToS), Apple Music
API (ücretli).

**Araçlar:** Python; numpy (FCM ve geçerlilik indeksleri elle yazılı), pandas,
librosa, CLAP, Demucs; SQLite (ortak + kullanıcı başına veritabanı, en çok 5
kullanıcı); Starlette + Jinja2 + vanilla JS + Chart.js arayüz; Docker + Caddy.

## 9. Sıradaki adımlar

1. Uzlaşma ödülünü gerçek kararlarla ölç (grup başına ≥ 30 karar hedefi).
2. Kaynak başına ≥ 30 sanatçı kararı biriktir; Thompson payını ve geri bildirim
   tavanını ölç.
3. Çalma listesi adayında tek bağ yerine eksendeki kaç sanatçıya bağlı
   olduğunu da hesaba katmayı K19 ile dene (`aday_parcalar` şu an en güçlü tek
   bağı, `MAX(pmi)`, kullanıyor).
