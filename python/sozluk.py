"""Terimlerin tek kaynağı — arayüzdeki her sayının ne olduğu.

Uygulama ölçtüğü şeyleri kısaltılmış adlarla gösteriyor: `zil_payi`,
`izgara_entropi`, `harmonik_pay`, `bilincli_uzaklik`. Bunlar kullanıcının
kafasında bir karşılık bulmuyorsa ekranda duran sayı bir bilgi değil, gürültü.

Her terim dört parça taşıyor:

  `kisa`    — bir cümlelik tanım, ipucu olarak gösterilir
  `nasil`   — nasıl ölçüldüğü; sayıya güvenip güvenmeyeceğine bu belirler
  `capalar` — bu KÜTÜPHANEDE ölçülmüş uç örnekler. Soyut bir aralık yerine
              "Meshuggah 0.62, TOOL 0.17" demek, sayıyı anında yerine oturtuyor
  `uyari`   — ölçütün bilinen sınırı, varsa. Gizlenmiyor.

Çapaların hepsi gerçek ölçüm; uydurma referans yok (K13).
"""

from __future__ import annotations

#: terim -> (okunur ad, kısa tanım, nasıl ölçülür, çapalar, uyarı)
SOZLUK: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- stem --
    "stem": {
        "ad": "stem",
        "kisa": "Bir kaydın tek bir enstrümana ayrılmış hâli — davul kanalı, "
                "bas kanalı, vokal kanalı.",
        "nasil": "Demucs (htdemucs) modeli 30 saniyelik klibi dört kanala "
                 "ayırıyor: drums, bass, other, vocals.",
        "capalar": "Gitar ile klavye AYRI ayrılamıyor, ikisi de `other` içinde.",
        "uyari": "Ayrıştırma kusursuz değil; yoğun mikste kanallar birbirine "
                 "sızabiliyor. Ölçümler bu gürültüyle birlikte okunmalı.",
    },
    "izgara_entropi": {
        "ad": "ızgara entropisi",
        "kisa": "Vuruşların 16'lık ızgaraya ne kadar kilitli olduğu. "
                "Düşük = makine, yüksek = insan eli.",
        "nasil": "Davul stem'indeki her vuruşun ölçü içindeki yeri 16 kutuya "
                 "dağıtılıp entropisi alınıyor. Programlanmış beat birkaç "
                 "kutuda toplanır, insan yayılır.",
        "capalar": "Eminem 0.755 (programlanmış) · Meshuggah ve Casiopea 0.99 "
                   "(insan). Kütüphanenin medyanı 0.98.",
        "uyari": "Kütüphanenin çoğu 0.95–0.99'da toplanıyor; ölçüt işini "
                 "KUYRUKTA yapıyor, ortada ayrım azdır.",
    },
    "tekme_payi": {
        "ad": "tekme payı",
        "kisa": "Davul sesinin ne kadarının bas davuldan (kick) geldiği.",
        "nasil": "Davul stem'inin 120 Hz altındaki enerjisinin toplam davul "
                 "enerjisine oranı.",
        "capalar": "Casiopea 0.17 (hafif ayak) · TOOL 0.41 (tom-tekme "
                   "ağırlıklı). Kütüphanenin medyanı 0.21.",
        "uyari": "tekme + trampet + zil ≈ 1. Biri artınca diğeri düşmek "
                 "zorunda; üçünü bağımsız okuma.",
    },
    "trampet_payi": {
        "ad": "trampet payı",
        "kisa": "Davul sesinin ne kadarının trampet ve tomlardan geldiği.",
        "nasil": "Davul stem'inin 120–2000 Hz arası enerji payı.",
        "capalar": "Meshuggah 0.17 (trampet cimri) · Eminem 0.45.",
        "uyari": "tekme/trampet/zil toplamı ≈ 1 (bileşimsel).",
    },
    "zil_payi": {
        "ad": "zil ağırlığı",
        "kisa": "Davul sesinin ne kadarının zillerden (ride, hi-hat, crash) "
                "geldiği.",
        "nasil": "Davul stem'inin 6000 Hz üstü enerji payı.",
        "capalar": "TOOL 0.17 (tok, zil cimri) · Meshuggah 0.62 (ride "
                   "ağırlıklı) · Casiopea 0.52. Medyan 0.37.",
        "uyari": "tekme/trampet/zil toplamı ≈ 1 (bileşimsel).",
    },
    "nota_vurus": {
        "ad": "nota/vuruş",
        "kisa": "Vuruş başına düşen nota sayısı — tempodan bağımsız yoğunluk.",
        "nasil": "Tespit edilen nota başlangıçları, tespit edilen vuruş "
                 "sayısına bölünüyor. Hızlı ama seyrek çalan düşük, yavaş ama "
                 "yoğun çalan yüksek çıkar.",
        "capalar": "Eminem 1.51 · TOOL 1.96 · Casiopea 2.73 · Meshuggah 2.88.",
        "uyari": "",
    },
    "harmonik_pay": {
        "ad": "harmonik pay",
        "kisa": "Sesin ne kadarının düzenli (tonal), ne kadarının gürültülü "
                "olduğu. Distorsiyon bunu düşürür.",
        "nasil": "HPSS ile harmonik ve vurmalı bileşen ayrılıp harmonik "
                 "enerjinin payı alınıyor.",
        "capalar": "Annihilator 0.77 (thrash, distorsiyonlu) · A-Ha 0.97 "
                   "(temiz synth). `other` stem'inde medyan 0.88.",
        "uyari": "Distorsiyonu doğrudan ölçmüyor, gürültülülüğü ölçüyor. "
                 "Üç aday ölçüt (spektral düzlük, tepe oranı, spektral "
                 "kontrast) bu iş için denenip elendi.",
    },
    "perde_medyan": {
        "ad": "perde",
        "kisa": "Kaydın o kanaldaki tipik perdesi — kalın mı ince mi.",
        "nasil": "yin algoritmasıyla temel frekans izleniyor, C1'den itibaren "
                 "yarım ton cinsinden medyanı alınıyor. 0 = C1, 12 = C2, "
                 "24 = C3.",
        "capalar": "Bas stem'i ~9 (G1) · gitar/klavye ~24 · vokal ~37.",
        "uyari": "Davulda ölçülmüyor (perde yok).",
    },
    "perde_araligi": {
        "ad": "perde aralığı",
        "kisa": "Melodinin ne kadar geniş bir alanda gezindiği.",
        "nasil": "Ölçülen perdelerin 90. ve 10. yüzdelikleri arasındaki fark, "
                 "yarım ton cinsinden.",
        "capalar": "Vokalde Panchiko 8.9 (düz söyleyiş) · Death 37.8 (geniş "
                   "gezinme). Medyan 26.",
        "uyari": "Tek bir 30 sn klipten; albümün sakin bir yerine denk "
                 "gelirse dar çıkar.",
    },
    "vibrato_hizi": {
        "ad": "vibrato",
        "kisa": "Perdenin saniyede kaç kez salındığı — düz söyleyen düşük.",
        "nasil": "Perde eğrisinin hareketli ortalamadan sapmasının işaret "
                 "değiştirme sıklığı.",
        "capalar": "Vokalde medyan 5.6 Hz.",
        "uyari": "",
    },
    "sustain_orani": {
        "ad": "sustain",
        "kisa": "Notanın atağından sonra ne kadar çınladığı. Staccato düşük, "
                "uzun tutan yüksek.",
        "nasil": "Her nota başlangıcı için, atak tepesiyle bir sonraki notaya "
                 "kadarki (en çok 300 ms) pencerenin sonundaki enerji oranı; "
                 "notalar üzerinden medyan.",
        "capalar": "April Wine davul 0.21 · Annihilator davul 0.94.",
        "uyari": "İlk tanım («RMS tepenin %20'sinin üstünde kalan kare oranı») "
                 "sürekli çalan kanalda hep 1.00 veriyordu, elendi.",
    },
    "parlaklik": {
        "ad": "parlaklık",
        "kisa": "Sesin ağırlık merkezinin ne kadar tizde olduğu.",
        "nasil": "Spektral merkez (spectral centroid), Hz.",
        "capalar": "Bas ~260 Hz · gitar/klavye ~1660 · davul ~3680 · "
                   "vokal ~2450.",
        "uyari": "",
    },
    "dinamik_db": {
        "ad": "dinamik",
        "kisa": "En yüksek ve en kısık anlar arasındaki fark.",
        "nasil": "RMS'in 95. ve 5. yüzdelikleri arasındaki fark, dB.",
        "capalar": "",
        "uyari": "Önizlemeler seviye normalize edilmiş olabiliyor; kaynaklar "
                 "arası kıyaslanamaz.",
    },
    "enerji_payi": {
        "ad": "enerji payı",
        "kisa": "O enstrümanın mikste kapladığı yer.",
        "nasil": "Stem enerjisinin tüm miks enerjisine oranı.",
        "capalar": "Dört stem 1'e toplanmaz — Demucs artığı ve örtüşme var.",
        "uyari": "Miks kararına bağlı; icra hakkında değil prodüksiyon "
                 "hakkında bilgi verir.",
    },
    # ------------------------------------------------------------- kavramlar --
    "eksen": {
        "ad": "eksen",
        "kisa": "Kütüphanenin bulanık kümelemeyle çıkarılmış zevk yönlerinden "
                "biri. İsimlerini sen veriyorsun.",
        "nasil": "Albümler kredi, tür, sahne ve ses bloklarından kurulan bir "
                 "matriste bulanık c-ortalamalar (FCM) ile kümeleniyor.",
        "capalar": "Bir albüm birden çok eksene ait olabilir — keskin atama "
                   "bilgi kaybettirirdi.",
        "uyari": "12 küme × 302 albüm = küme başına ~25. Bu kaba bir bölme; "
                 "ince tarif için etiketlere bak.",
    },
    "uyelik": {
        "ad": "üyelik",
        "kisa": "Bir albümün bir eksene ne kadar ait olduğu (0–1).",
        "nasil": "FCM'in ürettiği u_ij değeri. Bir albümün tüm eksenlerdeki "
                 "üyelikleri 1'e toplanır.",
        "capalar": "",
        "uyari": "",
    },
    "stabilite": {
        "ad": "stabilite (Jaccard)",
        "kisa": "Kümeleme yeniden yapılsa bu küme yine aynı yerde çıkar mı?",
        "nasil": "Bootstrap örneklemleriyle kümeleme tekrarlanıp kümelerin "
                 "Jaccard benzerliğinin ortalaması alınıyor. Eşik 0.60.",
        "capalar": "Kararsız kümeler isimlendirmeye açılmıyor — bir daha aynı "
                   "yerde çıkmayacak bir şeyi kimliklendirmek yanlış olurdu.",
        "uyari": "",
    },
    "ses_uzakligi": {
        "ad": "ses uzaklığı",
        "kisa": "Bir adayın, seçtiğin eksenin ses merkezinden ne kadar uzak "
                "olduğu. Birim: kütüphanenin standart sapması.",
        "nasil": "Adayın ayrılmış stem ölçümleriyle eksenin medyan profili "
                 "arasındaki, kütüphane sigmasıyla ölçeklenmiş uzaklık "
                 "(boyut sayısına göre normalize).",
        "capalar": "Kıyas için kütüphanenin kendi albümleri: metal ekseninde "
                   "kendi üyeleri 0.76, rock kümeleri ~0.95, hip-hop 1.31.",
        "uyari": "Her eksende işe yaramıyor. Heterojen bir kümenin ses "
                 "merkezi anlamlı değil — «istemiyen» ekseninde kendi üyeleri "
                 "0.98, diğerleri 1.01, yani ayrım yok. Arayüz tabanı gösterir.",
    },
    "icra_profili": {
        "ad": "icra profili",
        "kisa": "Bir müzisyenin NASIL çaldığı — türü ya da prodüksiyonu değil.",
        "nasil": "Kişinin o rolde geçtiği albümlerin ilgili stem ölçümlerinin "
                 "medyanı.",
        "capalar": "Bir davulcunun zil/tekme dengesi, ızgara entropisi ve "
                   "nota yoğunluğu.",
        "uyari": "Kredi verisine dayanıyor; bir kişi çok rollüyse ve o roldeki "
                 "payı düşükse profil onu temsil etmeyebilir (arayüz uyarır).",
    },
    # ------------------------------------------------------------ stratejiler --
    "kredi_sicramasi": {
        "ad": "kredi sıçraması",
        "kisa": "Kütüphanendeki bir müzisyenin, senin duymadığın başka işleri.",
        "nasil": "Eksenin kadrosundaki müzisyenler bulunup Discogs'ta "
                 "katıldıkları diğer kayıtlar taranıyor.",
        "capalar": "«Bas, gitar, synthesizer olarak Geddy Lee var. "
                   "Kütüphanende onun çaldığı 13 albüm var.»",
        "uyari": "Ölçüldü: keşif oranı yüksek (yeni şeyler getiriyor) ama "
                 "zevk isabeti düşük (3 karardan 1'i beğenildi).",
    },
    "sahne_komsulugu": {
        "ad": "sahne komşuluğu",
        "kisa": "Senin dinlediklerini dinleyenlerin dinlediği sanatçılar — "
                "kalabalık grafiğinde BİR adım.",
        "nasil": "ListenBrainz `similar-artists`; eksenin sanatçılarının "
                 "komşuları, birden çok sanatçının işaret ettiği önce.",
        "capalar": "",
        "uyari": "Ölçüldü: kararlarının %80'i «zaten biliyorum». Zevkini "
                 "tutturuyor ama KEŞİF sağlamıyor — ünlü komşuyu getiriyor.",
    },
    "bilincli_uzaklik": {
        "ad": "bilinçli uzaklık",
        "kisa": "Komşunun komşusu, ama senin doğrudan komşun değil — "
                "kalabalık grafiğinde İKİ adım.",
        "nasil": "1. adım komşular köprü sayılıp onların komşuları alınıyor; "
                 "köprüler ve sahip olunanlar çıkarılıyor. Sıralama "
                 "EKSEN-ÖZGÜLLÜĞÜ: kaç ayrı eksenin havuzunda görünüyor.",
        "capalar": "Metal ekseninde Children of Bodom, Dark Tranquillity.",
        "uyari": "Köprü sayısıyla sıralamak mainstream'e düşürüyordu — "
                 "Coldplay metal kümesinde çıkmıştı. Özgüllük birincil ölçüt.",
    },
    "liste_birlikteligi": {
        "ad": "liste birlikteliği",
        "kisa": "Seninkilerle AYNI çalma listelerinde geçen şarkılar. "
                "Kullanıcı kaydı olmadan ortak filtrelemenin vekili.",
        "nasil": "Deezer'dan toplanan 482 listede (45.899 parça) birlikte "
                 "görülme, PMI ile popülerlikten arındırılıyor.",
        "capalar": "The Ocean ↔ Pineapple Thief · Vega ↔ TNK · "
                   "Adam Nitti ↔ Nathan East.",
        "uyari": "Çalma listesi müzikal benzerlik kadar BAĞLAM da taşır "
                 "(spor, chill, parti). Ham sayı kullanılsaydı Van Halen ↔ "
                 "Madonna çıkıyordu — ikisi de 80'ler olduğu için.",
    },
    # ------------------------------------------------------------- değerlendirme --
    "loao": {
        "ad": "gizleme sınaması",
        "kisa": "Bir sanatçının TÜM albümleri kütüphaneden gizlenir, motora "
                "\"bunu bulabilir misin\" diye sorulur.",
        "nasil": "147 sanatçının her biri sırayla gizlenir. Kalan kütüphane, "
                 "o sanatçıyı hiç tanımayan birinin kütüphanesidir. Sanatçı "
                 "gizlenir, albüm değil: albüm gizlense sanatçı kütüphanede "
                 "kalır, motor onu kredi bağından bulur ve sen \"zaten "
                 "biliyorum\" dersin — yani kaçındığımız şey ölçülmüş olur.",
        "capalar": "melez 123/147 sanatçıya ulaşabiliyor · yalnız çalma "
                   "listesi 109 · yalnız ses 104 · kadro grafiği 55–81.",
        "uyari": "Sonuç bir ALT SINIR. Gerçek etiketimiz yalnız sahip olduğun "
                 "147 sanatçı için var; gizleneni geçen adayların çoğu da iyi "
                 "öneri olabilir ve bunu ölçemiyoruz. Bu yüzden mutlak seviye "
                 "değil, yöntemler arası KIYAS güvenilir.",
    },
    "tavan": {
        "ad": "tavan",
        "kisa": "Gizlenen sanatçı, o yolun baktığı havuzda VAR MI?",
        "nasil": "Havuzda olmayan sanatçı bulunamaz; bu bir sıralama hatası "
                 "değil kapsama boşluğudur. İkisi ayrı raporlanıyor.",
        "capalar": "melez 123/147 · çalma listesi 109 · ses 104.",
        "uyari": "Karıştırılırsa yanlış işe yatırım yapılır: sıralamayı "
                 "düzeltmek, havuzda olmayan sanatçıyı getirmez.",
    },
    "yuzdelik": {
        "ad": "yüzdelik",
        "kisa": "Bulunan sanatçının sırası, havuz boyuna bölünmüş.",
        "nasil": "medyan sıra / havuzdaki sanatçı sayısı. Rastgele bir "
                 "erişim 0,50 verir; küçük olan iyi.",
        "capalar": "çalma listesi 0,092 (rastgeleden 5,4 kat iyi) · "
                   "ses 0,347 (1,4 kat iyi).",
        "uyari": "FARKLI HAVUZ BOYLARI ARASINDA YALNIZ BU KIYASLANIR. "
                 "Ölçüldü: havuz 2.163'ten 4.183 gömüye çıkınca recall@50 "
                 "0,08'den 0,03'e düştü — çünkü rakip sayısı da iki katına "
                 "çıktı. Aynı ölçümde yüzdelik 0,349'dan 0,311'e iyileşti.",
    },
    "melez": {
        "ad": "melez sıralama",
        "kisa": "İki sinyalin —çalma listesi komşuluğu ve kulağa benzerlik— "
                "SIRALARININ birleştirilmesi.",
        "nasil": "skor(x) = Σ a/(60 + sıra). Skorlar toplanmıyor çünkü "
                 "ölçekleri kıyaslanamaz (bağ gücü −1…+1, ses ≈ −0,35…0). "
                 "Çalma listesi 2, ses 1 ağırlıkta; oran ölçülerek seçildi.",
        "capalar": "Bir listede birinci ama diğerinde hiç yok olan aday, iki "
                   "listede de ellinci olana yenilir — kesişim ödüllendirilir.",
        "uyari": "Asıl kazancı sıralama değil ERİŞİM: 14 sanatçıya yalnız ses "
                 "tarafından ulaşılabiliyor, çalma listesi onları hiç görmüyor.",
    },
    "pmi": {
        "ad": "bağ gücü (npmi)",
        "kisa": "İki sanatçının aynı listelerde birlikte görülmesi, tek tek "
                "görülme sıklıklarının gerektirdiğinden ne kadar fazla.",
        "nasil": "log( P(a,b) / (P(a)·P(b)) ), sonra −log P(a,b)'ye bölünüp "
                 "−1 ile +1 arasına sıkıştırılır. Ünlü sanatçı her listede "
                 "olduğu için paydası büyür ve skoru söner.",
        "capalar": "+1'e yaklaşan: hep birlikte görülüyorlar. 0 civarı: "
                   "birliktelik tesadüf kadar. Eksi: birbirinden kaçıyorlar.",
        "uyari": "Bölme (normalizasyon) şart. Ham PMI'da iki listede geçen "
                 "bir sanatçı, yüz listede geçenden yüksek skor alıyordu — "
                 "nadirlik primi. Ölçüldü (147 sanatçılık leave-one-out): "
                 "normalize edilince recall@50 0,07'den 0,14'e çıktı.",
    },
    # ------------------------------------------------------------ geri bildirim --
    "kesif_orani": {
        "ad": "keşif oranı",
        "kisa": "Önerilen şey senin için YENİ miydi?",
        "nasil": "1 − («zaten biliyorum» sayısı / toplam karar).",
        "capalar": "sahne_komsulugu %20 · kredi_sicramasi %100.",
        "uyari": "«Zaten biliyorum» bir zevk kararı değildir; bu oranın "
                 "paydasına girer ama zevk isabetininkine girmez.",
    },
    "zevk_isabeti": {
        "ad": "zevk isabeti",
        "kisa": "Yeni olanların içinde beğendiklerinin payı.",
        "nasil": "beğendim / (beğendim + tutmadı). «Zaten biliyorum» hariç — "
                 "o albümü beğenip beğenmediğini söylemedin.",
        "capalar": "sahne_komsulugu %100 ama keşif oranı %20 — sevdiğin ama "
                   "zaten bildiğin şeyleri buluyor.",
        "uyari": "",
    },
    "wilson": {
        "ad": "Wilson aralığı",
        "kisa": "Küçük örneklemde oranın belirsizlik aralığı.",
        "nasil": "Wilson skor aralığı (%90). Normal yaklaşım p=0 ya da p=1'de "
                 "genişliği sıfır verip tek gözlemde kesinlik iddia ediyor.",
        "capalar": "1/1 = %100 ile 80/80 = %100 aynı sayı değildir; aralık "
                   "genişliği bunu görünür kılar.",
        "uyari": "",
    },
    "yayilim": {
        "ad": "yayılım",
        "kisa": "Bir eksende ne kadar geniş bir dinleyici olduğun.",
        "nasil": "(p95 − p5) / medyan.",
        "capalar": "Tekme ağırlığı 1.53 (geniş) · ızgara entropisi 0.26 (dar).",
        "uyari": "Dar eksende sapan bir aday riskli demektir.",
    },
}


def terim(anahtar: str) -> dict[str, str] | None:
    return SOZLUK.get(anahtar)


def ipucu(anahtar: str) -> str:
    """`title=` özniteliğine konacak tek satırlık metin."""
    t = SOZLUK.get(anahtar)
    if not t:
        return ""
    parcalar = [t["kisa"]]
    if t.get("capalar"):
        parcalar.append(t["capalar"])
    return "  —  ".join(parcalar)
