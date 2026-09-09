# Ürün yolu — tek kullanıcıdan çok kullanıcıya

Tarih: 2026-09-01. Kullanıcı isteği: *"Kullanıcı Spotify hesabıyla giriş yapabilsin,
üye olabilsin, Apple Music ile üye olabilsin, mail ile üye olabilsin"* ve
*"bunu bir de iOS uygulaması yapalım"*.

Bu belge önce **ölçülen kısıtları** yazar, sonra bu kısıtlara rağmen isteği
karşılayan yolu. Sıra önemli: kısıtlardan biri istenen şeyin bir kısmını
doğrudan imkânsız kılıyor ve alternatifi ondan iyi.

---

## 1. Nerede duruyoruz (ölçüm, 2026-09-01)

| | |
|---|---|
| Albüm (senin kütüphanen) | 302 |
| Kredi satırı | 9.678 |
| Ayrılmış stem profili | 1.676 |
| Küme üyeliği (FCM) | 17.818 |
| Aday sanatçı / albüm | 219 / 621 |
| Çalma listesi / parça | 482 / 45.899 |
| Sanatçı birlikteliği (PMI) | 11.287 |
| Havuzdaki tekil sanatçı | 10.396 |
| CLAP gömüsü | 469 albüm + 2.163 parça |
| Ses kümesi üyeliği | 288 |
| Geri bildirim | 15 (3 beğendim / 3 tutmadı / 9 zaten biliyorum) |
| **`plays` (dinleme kaydı)** | **0** |

Son satır bu belgenin konusu. K16 çalma listelerini "kullanıcı kaydı yoksa
vekil" diye tanımlamıştı. Vekilin yerine gerçeği koymanın yolu artık açık.

---

## 2. Spotify: giriş mümkün ama tavan 5 kullanıcı

Ölçülen kısıtlar, kaynaklarıyla:

- **2024-11-27** — yeni uygulamalara kapatılan uçlar: `audio-features`,
  `audio-analysis`, `recommendations`, `related-artists`, featured playlists,
  30 sn önizleme URL'leri, Spotify editoryal listeleri.
- **2026-02** — Development Mode: uygulama **5 kullanıcıyla** sınırlı, uygulama
  sahibinin **aktif Premium aboneliği zorunlu** (abonelik biterse uygulama
  durur), `search` limiti 50 → 10, toplu getirme uçları (`GET /tracks`
  çoklu id) ve browse uçları kaldırıldı.
- **2026-07** — geliştirici hesabı başına 25 client ID; kota **geliştirici
  hesabı başına paylaşımlı** (uygulama başına değil).
- **Extended quota** (gerçek çok kullanıcılı erişim) — şartlar: tüzel kişilik,
  **en az 250.000 aylık aktif kullanıcı**, yayında olan bir servis, ticari
  sürdürülebilirlik.

**Sonuç:** Bireysel geliştiriciye açık tavan **5 kullanıcı**, üstelik Premium
şartıyla. Bu bir ürün değil, bir davetli listesi.

**Bizi ilgilendirmeyen kısım — önemli:** Kapatılan uçların neredeyse tamamı
bizde zaten kullanılmıyor. Ses ölçümünü kendimiz çıkarıyoruz (stem + CLAP),
benzerliği kendimiz hesaplıyoruz, öneriyi kendimiz üretiyoruz.
`audio-features`'ın kapanması binlerce hobi projesini öldürdü; bizi öldürmedi,
çünkü K12 ve K18 gereği o veriyi zaten dışarıdan almıyorduk. Spotify'dan
istediğimiz tek şey **kullanıcının dinleme geçmişi**. Sorun uçlar değil,
kullanıcı tavanı.

## 3. Apple: her kapı ücretli

- **Apple Music API / MusicKit** — developer token gerekiyor, token için Apple
  Developer Program üyeliği gerekiyor.
- **Sign in with Apple (web)** — Services ID gerekiyor; Services ID
  Certificates, Identifiers & Profiles panelinden alınıyor, o panel ücretli
  üyelik istiyor. Yani sadece "Apple ile üye ol" düğmesi bile ücretli.
- **App Store'da yayın** — aynı program. **99 $/yıl.**
- Kendi telefonuna kurmak ücretsiz (free provisioning) ama imza **7 günde bir
  bitiyor**, 3 cihaz / 10 App ID sınırı var. Kendin için olur, dağıtım için olmaz.

**K2 (bütçe: 0 TL) ile doğrudan çelişiyor.** Bu bir mühendislik kararı değil,
senin kararın; K2 bir anayasa maddesi ve onu ancak sen değiştirirsin.

## 4. E-posta: tamamen bizde, sınırsız

Hiçbir üçüncü tarafa bağlı değil, maliyeti yok, tavanı yok.

**Bu yüzden asıl hesap sistemi e-posta olmalı.** Spotify ve Apple "üyelik
yöntemi" değil, hesaba **bağlanan kimlik** olmalı. Aksi hâlde ürünün tavanını
Spotify'ın kotası belirler.

---

## 5. Kapıyı açan şey giriş değil, veri dışa aktarımı

Spotify'ın API'si kapalı ama **veri dışa aktarımı açık** — GDPR/KVKK hakkı,
ücretsiz, API çağrısı yok, kullanıcı tavanı yok, Premium şartı yok.

Kullanıcı: Spotify → Gizlilik ayarları → *Download your data*.

| | kapsam | süre |
|---|---|---|
| Account data | son ~12 ay | birkaç gün |
| Extended streaming history | hesabın tüm ömrü | ~1 aya kadar |

Dosyalar JSON (`Streaming_History_Audio_YYYY-YYYY.json`). Alanlar: zaman damgası,
**`ms_played`**, parça adı, sanatçı adı, albüm adı, track URI, platform, ülke.

**Bu, API'nin vereceğinden fazlası.** `/me/top/tracks` en fazla 50 satır verir
ve nasıl sıralandığını söylemez. Dışa aktarım yüz binlerce satır ve her biri
için *ne kadar dinlendiği* bilgisini verir — yarıda bırakılan şarkı ile sonuna
kadar dinlenen şarkıyı ayırt edebiliriz. Ortak filtrelemenin gerçek yakıtı bu.

Apple Music'in de dışa aktarımı var (*Play History Daily Tracks*, CSV) — ve
buradaki nokta şu: **Apple Music kullanıcısı, biz 99 $ ödemeden sisteme
girebilir.** Ücretli olan Apple'ın API'si; kullanıcının kendi verisi değil.

---

## 6. Mimari sonuç: pahalı kısım paylaşımlı

Çok kullanıcılığın ucuz olmasının sebebi:

    PAHALI ve PAYLAŞIMLI          UCUZ ve KULLANICIYA ÖZEL
    ─────────────────────         ────────────────────────
    CLAP gömüleri (2.163)         isim eşleme
    stem ayrıştırma               küme üyeliği (FCM)
    çalma listesi hasadı          sıralama, geri bildirim
    PMI birlikteliği              dinleme kaydı

Yeni kullanıcı FLAC yüklemiyor — **geçmiş** yüklüyor. Yani gelen şey isim
listesi; onu paylaşımlı havuzda arıyoruz. Ses işleme yok. Kullanıcı başına
maliyet kümeleme + küme sorgusundan ibaret.

Dahası: **her yeni kullanıcı havuzu büyütüyor.** Kullanıcının geçmişindeki
tanımadığımız sanatçılar havuza giriyor, bir kez gömülüyor, herkes için
kullanılabilir hâle geliyor. 469 → 2.163 gömü geçişinde küme 11'in
önerilerinin nasıl değiştiğini ölçtük (bkz. karar günlüğü 2026-08-18). Ölçek
burada doğrudan kaliteye dönüşüyor.

---

## 7. Aşamalar

**Aşama 0 — `plays` tablosunu doldur (0 TL, bugün).**
Kendi Spotify dışa aktarımınla. K16'nın vekilinin yerine gerçek sinyali koy.
Ölçülecek şey: dinleme kaydı, çalma listesi PMI'ından daha iyi öneri veriyor mu?
Bu ölçülmeden çok kullanıcılığa geçmek erken olur.

**Aşama 1 — hesap katmanı (0 TL).**
E-posta ile üyelik, oturum, çok kiracılık. Şu an her tablo tek kütüphane
varsayıyor; `calisma_id` var ama kullanıcı yok. Ayrılması gereken şey:
kütüphane, kümeler, geri bildirim, dinleme kaydı. Ayrılmaması gereken şey:
gömüler, çalma listeleri, krediler, PMI.

**Aşama 2 — veri yükleme akışı (0 TL).**
"Spotify geçmişini yükle" / "Apple Music geçmişini yükle". Sınırsız kullanıcı.

**Aşama 3 — Spotify OAuth (0 TL + Premium).**
5 slot. Sen, hocan, birkaç kişi. Anlık ve zahmetsiz; ama tavanı belli,
ürünün omurgası olamaz. Aşama 2'nin üstüne bir kolaylık olarak eklenir.

**Aşama 4 — PWA (0 TL).**
Mevcut Starlette arayüzü telefona kurulabilir hâle gelir: ana ekran ikonu,
tam ekran, çevrimdışı kabuk. iPhone'da bugün çalışır. Native uygulamadan
farkı: arka planda ses, MusicKit ile tam şarkı, Shortcuts entegrasyonu yok.

**Aşama 5 — native iOS + Apple (99 $/yıl kararına bağlı).**
SwiftUI + MusicKit. Buradaki gerçek kazanç estetik değil: MusicKit, Apple
Music abonesine **tam şarkıyı** çaldırır. 30 saniyelik önizlemeyle
"beğendim/tutmadı" demek ile şarkının tamamını dinleyip demek arasında
geri bildirim kalitesi açısından ciddi fark var.

---

## 8. Karar bekleyen şeyler

1. **99 $/yıl (Apple).** K2'yi değiştirir. Karşılığında: Apple ile üyelik,
   Apple Music kütüphane erişimi, App Store, tam şarkı çalma.
2. **Sunucu.** Çok kullanıcılık için bir yerde çalışması gerekiyor.
   0 TL seçenekler var (Oracle Cloud ücretsiz ARM katmanı gibi); gömü havuzu
   diskte ~1,4 GB ve büyüyor, bunu hesaba katmak gerekiyor.
3. **KVKK.** Başkalarının dinleme geçmişini saklamak veri sorumluluğu doğurur.
   Tek kullanıcıyken yoktu. Asgari: ne saklandığının açık yazılması, silme
   hakkı, verinin üçüncü tarafa gitmemesi.
