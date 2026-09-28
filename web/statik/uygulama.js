/* İki dil: sayfanın `lang` özniteliği sunucuda etkin dile göre basılıyor.
 * Her betik metni iki dilde yazılır — biri boş kalamaz. */
window.t = (tr, en) => (document.documentElement.lang === 'en' ? en : tr);

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
    if (!yanit.ok) throw new Error(String(yanit.status));
    const veri = await yanit.json();
    if (typeof veri.liste === 'number') {
      document.querySelectorAll('[data-liste-sayac]').forEach((e) => { e.textContent = veri.liste; e.hidden = !veri.liste; });
    }
    kutu.querySelectorAll('button').forEach((d) => d.classList.remove('secili'));
    const kart = dugme.closest('.aday');
    if (veri.karar) {
      dugme.classList.add('secili');
      durum.textContent = t(`${veri.adet} albüm kaydedildi`, `${veri.adet} saved`);
      kart.classList.add('karar-verildi');
    } else {
      // Aynı düğmeye ikinci kez basmak kararı geri alır.
      durum.textContent = t('geri alındı', 'undone');
      kart.classList.remove('karar-verildi');
    }
    setTimeout(() => { durum.textContent = ''; }, 2200);
  } catch (hata) {
    durum.textContent = t('kaydedilemedi', 'couldn\'t save');
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
    durum.textContent = t('kaydedildi', 'saved');
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
  const yanit = await fetch('/api/eslestir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ album_id: dugme.dataset.album, mbid: dugme.dataset.mbid }),
  });
  // Yanıta bakmadan «bağlandı» yazmak tutulmayan bir söz olurdu.
  if (!yanit.ok) {
    durum.textContent = t('kaydedilemedi', 'couldn\'t save');
    dugme.disabled = false;
    return;
  }
  durum.textContent = dugme.dataset.mbid === '__yok__' ? t('karşılığı yok olarak işaretlendi', 'marked as no match') : t('bağlandı', 'linked');
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
    dugme.textContent = t('önizleme yok', 'no preview');
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
    durum.textContent = t('kaydedildi', 'saved');
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

// Aktarım ilerlemesi (/basla). Sayfa sunucuda çiziliyor; burada yalnız
// sayaç güncelleniyor, aşama değişince ya da iş bitince sayfa yeniden
// yükleniyor ki metin sunucunun gördüğüyle aynı kalsın.
(function () {
  const kutu = document.getElementById("aktarim");
  if (!kutu || kutu.dataset.calisiyor !== "evet") return;
  let asama = null;
  async function yokla() {
    try {
      const d = await (await fetch("/api/aktar/durum", { cache: "no-store" })).json();
      if (asama === null) asama = d.asama;
      if (!d.calisiyor || d.asama !== asama) { location.reload(); return; }
      const sayac = document.getElementById("aktarim-sayac");
      if (sayac && d.toplam) sayac.textContent = `${d.adim}/${d.toplam}`;
    } catch (_) { /* ağ kesintisi: bir sonraki turda yeniden dene */ }
    setTimeout(yokla, 4000);
  }
  setTimeout(yokla, 4000);
})();

/* ---------------------------------------------------------------------------
 * Bildirim — "listeye eklendi · Geri al". Tek kutu, üst üste binmez.
 * ------------------------------------------------------------------------- */
let bildirimZamani;
window.bildir = function bildir(metin, eylemAdi, eylem) {
  const kutu = document.getElementById('bildirim');
  if (!kutu) return;
  kutu.replaceChildren(document.createTextNode(metin));
  if (eylemAdi && eylem) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = eylemAdi;
    b.addEventListener('click', () => { kutu.classList.remove('acik'); eylem(); });
    kutu.append(b);
  }
  kutu.classList.add('acik');
  clearTimeout(bildirimZamani);
  bildirimZamani = setTimeout(() => kutu.classList.remove('acik'), eylem ? 4200 : 2400);
};

/* ---------------------------------------------------------------------------
 * Listem — durum anahtarı, silme, önizleme. Sayfa yenilenmez.
 * ------------------------------------------------------------------------- */
async function jsonGonder(yol, govde) {
  const yanit = await fetch(yol, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(govde),
  });
  if (!yanit.ok) throw new Error(String(yanit.status));
  return yanit.json();
}

document.addEventListener('click', async (olay) => {
  const d = olay.target.closest('.durum-anahtar button');
  if (!d) return;
  const oge = d.closest('.lo');
  try {
    await jsonGonder('/api/liste/durum', { aday_id: oge.dataset.aday, durum: d.dataset.durum });
    oge.querySelectorAll('.durum-anahtar button').forEach((x) =>
      x.setAttribute('aria-pressed', String(x === d)));
    oge.dataset.durum = d.dataset.durum;
  } catch (_) {
    bildir(t('Durum kaydedilemedi', 'Couldn\'t save the status'));
  }
});

document.addEventListener('click', async (olay) => {
  const b = olay.target.closest('.lo-sil');
  if (!b) return;
  const oge = b.closest('.lo');
  try {
    const v = await jsonGonder('/api/liste/sil', { aday_id: oge.dataset.aday });
    oge.classList.add('siliniyor');
    setTimeout(() => oge.remove(), 300);
    document.querySelectorAll('[data-liste-sayac]').forEach((e) => { e.textContent = v.liste; e.hidden = !v.liste; });
    bildir(t(`${oge.dataset.sanatci} listeden çıkarıldı`, `${oge.dataset.sanatci} removed from your list`));
  } catch (_) {
    bildir(t('Silinemedi', 'Couldn\'t remove it'));
  }
});

/* Listem önizlemesi: tek ortak çalar; başka bir öğeye basınca öncekini keser. */
let listeCalar;
document.addEventListener('click', async (olay) => {
  const b = olay.target.closest('.lo-cal');
  if (!b) return;
  if (!listeCalar) listeCalar = new Audio();
  if (b.classList.contains('caliyor')) {
    listeCalar.pause();
    b.classList.remove('caliyor'); b.textContent = '▶';
    return;
  }
  document.querySelectorAll('.lo-cal.caliyor').forEach((x) => { x.classList.remove('caliyor'); x.textContent = '▶'; });
  b.textContent = '…';
  try {
    const yanit = await fetch(`/api/medya/${b.dataset.aday}`, { cache: 'no-store' });
    const m = await yanit.json();
    if (!m.onizleme) throw new Error('yok');
    listeCalar.src = m.onizleme;
    await listeCalar.play();
    b.classList.add('caliyor'); b.textContent = '❚❚';
    listeCalar.onended = () => { b.classList.remove('caliyor'); b.textContent = '▶'; };
  } catch (_) {
    b.textContent = '▶';
    bildir(t('Bunun önizlemesi yok', 'No preview for this one'));
  }
});

/* Kapak yüklenemezse (ölü adres, CSP) yer tutucu görünür kalsın. */
document.addEventListener('error', (olay) => {
  const img = olay.target;
  if (img.tagName === 'IMG' && img.dataset.kapak !== undefined) img.remove();
}, true);

/* ---------------------------------------------------------------------------
 * Liste içi arama — `data-suz` taşıyan kutu, hedef öğeleri `data-ara`
 * metnine göre süzer (Müzisyenler). Türkçe küçük harf: İ→i, I→ı.
 * ------------------------------------------------------------------------- */
document.addEventListener('input', (olay) => {
  const kutu = olay.target.closest('[data-suz]');
  if (!kutu) return;
  const q = kutu.value.toLocaleLowerCase(document.documentElement.lang || 'tr').trim();
  document.querySelectorAll(kutu.dataset.suz).forEach((o) => {
    o.hidden = q !== '' && !(o.dataset.ara || '').includes(q);
  });
});

/* Müzisyenler: "bu müzisyen gibi çalan" kartındaki ♥ — destedeki sağa
 * kaydırmayla aynı kayıt. */
document.addEventListener('click', async (olay) => {
  const b = olay.target.closest('.mz-ekle');
  if (!b || b.classList.contains('eklendi')) return;
  b.disabled = true;
  try {
    const v = await jsonGonder('/api/liste/ekle', { aday_id: b.dataset.aday });
    b.classList.add('eklendi');
    b.textContent = t('✓ Listende', '✓ Saved');
    document.querySelectorAll('[data-liste-sayac]').forEach((e) => { e.textContent = v.liste; e.hidden = !v.liste; });
    bildir(t(`♥ ${b.dataset.sanatci} listene eklendi`, `♥ ${b.dataset.sanatci} saved to your list`));
  } catch (_) {
    b.disabled = false;
    bildir(t('Eklenemedi', 'Couldn\'t save it'));
  }
});

/* Kapağı olmayan aday kartları görünür olunca kapağı çözdür (Müzisyenler).
 * `/api/medya` ilk çağrıda Deezer'a sorar ve sonucu saklar; sonraki
 * ziyaretlerde kapak sunucudan doğrudan gelir. */
(() => {
  const kartlar = [...document.querySelectorAll('.mz-kart[data-aday]')]
    .filter((k) => !k.querySelector('.mz-kart-kapak img'));
  if (!kartlar.length || !('IntersectionObserver' in window)) return;
  const gozcu = new IntersectionObserver((girdiler) => {
    girdiler.forEach(async (g) => {
      if (!g.isIntersecting) return;
      gozcu.unobserve(g.target);
      try {
        const m = await (await fetch(`/api/medya/${g.target.dataset.aday}`)).json();
        if (!m.kapak) return;
        const img = new Image();
        img.alt = ''; img.decoding = 'async'; img.dataset.kapak = '';
        img.onload = () => g.target.querySelector('.mz-kart-kapak').insertBefore(
          img, g.target.querySelector('.mz-kart-kapak .lo-cal'));
        img.src = m.kapak;
      } catch (_) { /* yer tutucu kalır */ }
    });
  }, { rootMargin: '200px' });
  kartlar.forEach((k) => gozcu.observe(k));
})();

/* ---------------------------------------------------------------------------
 * «Sayılarla sen» panosu: bir tarz seçilince `data-tarz` taşıyan her işaret
 * (kabarcık, sütun parçası, çubuk, köprü) seçili tarza ait değilse solar ve
 * yan panel o tarzı anlatır. Seçim `#tarz-N` ile paylaşılabilir. Durum yalnız
 * sayfada; sunucu her zaman tam resmi çizer (JS yoksa pano yine eksiksiz).
 * ------------------------------------------------------------------------- */
(() => {
  const pano = document.querySelector('[data-pano]');
  if (!pano) return;
  const sec = (k) => {
    k = k || '';
    pano.dataset.secili = k;
    pano.querySelectorAll('[data-tarz]').forEach((el) => {
      const ait = el.dataset.tarz.split(' ').includes(k);
      el.classList.toggle('soluk', k !== '' && !ait);
    });
    pano.querySelectorAll('[data-panel]').forEach((p) => {
      p.hidden = p.dataset.panel !== (k || 'tum');
    });
    pano.querySelectorAll('[data-sec]').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.sec === k));
    });
    try {
      history.replaceState(null, '', k ? `#tarz-${k}` : location.pathname + location.search);
    } catch (_) { /* çerçeve içinde izin verilmeyebilir */ }
    // Chart.js grafikleri (grafikler.js) kendilerini bu olayla boyar.
    document.dispatchEvent(new CustomEvent('pano:secim', { detail: k }));
  };
  // Harita kabarcığı (tuval) buradan seçer; ikinci dokunuş seçimi kaldırır.
  window.panoSec = (k, degistir) => sec(degistir && pano.dataset.secili === k ? '' : k);
  const tikla = (hedef) => {
    const k = hedef.dataset.sec !== undefined ? hedef.dataset.sec : hedef.dataset.tarz;
    sec(pano.dataset.secili === k ? '' : k);
  };
  pano.addEventListener('click', (olay) => {
    const h = olay.target.closest('[data-sec], .g-tarz');
    if (h) tikla(h);
  });
  pano.addEventListener('keydown', (olay) => {
    const h = olay.target.closest('.g-tarz');
    if (h && (olay.key === 'Enter' || olay.key === ' ')) { olay.preventDefault(); tikla(h); }
  });
  const m = location.hash.match(/^#tarz-(\d+)$/);
  if (m) sec(m[1]);
})();

/* Kütüphane kapakları («Senin müziğin»): `data-kapak-yukle="<album_id>"`
 * taşıyan kutu görünür olunca `/api/medya/<id>` sorulur (ilk seferde Deezer,
 * sonra tablo). Kapak yoksa üretilmiş yer tutucu kalır. */
(() => {
  const kutular = [...document.querySelectorAll('[data-kapak-yukle]')];
  if (!kutular.length || !('IntersectionObserver' in window)) return;
  const gozcu = new IntersectionObserver((girdiler) => {
    girdiler.forEach(async (g) => {
      if (!g.isIntersecting) return;
      gozcu.unobserve(g.target);
      try {
        const m = await (await fetch(`/api/medya/${g.target.dataset.kapakYukle}`)).json();
        if (!m.kapak) return;
        const img = new Image();
        img.alt = ''; img.decoding = 'async'; img.dataset.kapak = '';
        img.onload = () => { g.target.appendChild(img); g.target.classList.add('dolu'); };
        img.src = m.kapak;
      } catch (_) { /* yer tutucu kalır */ }
    });
  }, { rootMargin: '200px' });
  kutular.forEach((k) => gozcu.observe(k));
})();
