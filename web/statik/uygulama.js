/* Sayfa yenilenmeden çalışan iki etkileşim.
 *
 * Streamlit'te 👍'ye basmak tüm betiği yeniden çalıştırıyor ve ÇALAN 30 SANİYELİK
 * ÖNİZLEME KESİLİYORDU — oysa bu uygulamanın çekirdek eylemi "dinle ve karar ver".
 * Burada karar bir fetch ile gidiyor, ses çalmaya devam ediyor.
 */

document.addEventListener('click', async (olay) => {
  const dugme = olay.target.closest('.kararlar button');
  if (!dugme) return;

  const kutu = dugme.closest('.kararlar');
  const durum = kutu.querySelector('.durum');
  dugme.disabled = true;
  try {
    const yanit = await fetch('/api/karar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Kart artık SANATÇI düzeyinde: karar o sanatçının listelenen tüm
      // albümlerine uygulanır. "Zaten biliyorum" zaten sanatçı düzeyinde bir
      // cümle; albüm albüm sormak gereksiz tekrar olurdu.
      body: JSON.stringify({
        aday_kimlikleri: kutu.dataset.adaylar.split(','),
        calisma_id: kutu.dataset.calisma,
        karar: dugme.dataset.karar,
      }),
    });
    const veri = await yanit.json();
    kutu.querySelectorAll('button').forEach((d) => d.classList.remove('secili'));
    const kart = dugme.closest('.aday');
    if (veri.karar) {
      dugme.classList.add('secili');
      durum.textContent = `${veri.adet} albüm kaydedildi`;
      kart.classList.add('karar-verildi');
    } else {
      // Aynı düğmeye ikinci kez basmak kararı geri alır.
      durum.textContent = 'geri alındı';
      kart.classList.remove('karar-verildi');
    }
    setTimeout(() => { durum.textContent = ''; }, 2200);
  } catch (hata) {
    durum.textContent = 'kaydedilemedi';
  } finally {
    dugme.disabled = false;
  }
});

/* Küme adı: yazmayı bırakınca kaydeder. Kaydet düğmesi koymak, isimlendirme
 * akışını gereksiz yere yavaşlatırdı. */
let zamanlayici;
document.addEventListener('input', (olay) => {
  const alan = olay.target.closest('.kume-adi');
  if (!alan) return;
  clearTimeout(zamanlayici);
  const durum = alan.parentElement.querySelector('.durum');
  durum.textContent = '…';
  zamanlayici = setTimeout(async () => {
    await fetch('/api/kume-adi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kume_id: alan.dataset.kume,
        calisma_id: alan.dataset.calisma,
        ad: alan.value,
      }),
    });
    durum.textContent = 'kaydedildi';
    setTimeout(() => { durum.textContent = ''; }, 1800);
  }, 600);
});

/* Elle MusicBrainz eşleştirme — satır satır, sayfa yenilemeden. */
document.addEventListener('click', async (olay) => {
  const dugme = olay.target.closest('button.esle');
  if (!dugme) return;
  const kart = dugme.closest('.aday');
  const durum = kart.querySelector('.durum');
  dugme.disabled = true;
  await fetch('/api/eslestir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ album_id: dugme.dataset.album, mbid: dugme.dataset.mbid }),
  });
  durum.textContent = dugme.dataset.mbid === '__yok__' ? 'karşılığı yok işaretlendi' : 'bağlandı';
  kart.classList.add('karar-verildi');
});

/* Çalma listesi parçasının önizlemesi İSTEK ANINDA alınıyor.
 * Deezer URL'leri kısa ömürlü imzalı — ölçüldü, saatler sonra hepsi 403.
 * Kalıcı olan parça kimliği; kullanıcı "dinle"ye basınca taze URL çekiliyor. */
document.addEventListener('click', async (olay) => {
  const dugme = olay.target.closest('button.cal');
  if (!dugme) return;
  const yuva = dugme.nextElementSibling;
  dugme.disabled = true;
  dugme.textContent = '…';
  try {
    const yanit = await fetch(`/api/onizleme/${dugme.dataset.parca}`);
    if (!yanit.ok) throw new Error('yok');
    const { url } = await yanit.json();
    const ses = document.createElement('audio');
    ses.controls = true; ses.src = url; ses.autoplay = true;
    yuva.replaceWith(ses);
    dugme.remove();
  } catch (hata) {
    dugme.textContent = 'önizleme yok';
  }
});

/* Ses kümesine isim ver — yazmayı bırakınca kaydeder. */
let sesZaman;
document.addEventListener('input', (olay) => {
  const alan = olay.target.closest('.ses-kume-adi');
  if (!alan) return;
  clearTimeout(sesZaman);
  const durum = alan.parentElement.querySelector('.durum');
  durum.textContent = '…';
  sesZaman = setTimeout(async () => {
    await fetch('/api/ses-kume-adi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kume: alan.dataset.kume, ad: alan.value }),
    });
    durum.textContent = 'kaydedildi';
    setTimeout(() => { durum.textContent = ''; }, 1800);
  }, 600);
});

/* Servis çalışanını kaydet — PWA'nın ana ekrana kurulabilmesi için gerekli.
 * Başarısız olursa sessizce geçiyoruz: servis çalışanı bir iyileştirme,
 * uygulamanın çalışması ona bağlı değil. */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
