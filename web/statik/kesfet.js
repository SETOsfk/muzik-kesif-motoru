/* Keşfet destesi — kaydır, dinle, karar ver.
 *
 * DURUM TEK YERDE: `d` nesnesi. DOM onun bir yansıması; `ciz()` kuyruğun
 * ilk üç kartını ekrana uydurur. Karar önce ekranda uygulanır (kart uçar,
 * sıradaki çalar), sonra sunucuya gider; sunucu reddederse kart GERİ GELİR
 * ve kullanıcıya söylenir — "kaydedildi" sanılan bir kararın sessizce
 * kaybolması, bu projenin "tutulamayacak söz verme" kuralını çiğnerdi.
 *
 * Güvenlik: sunucudan gelen metinler yalnız `textContent` ile basılır.
 * `innerHTML` tek yerde: sunucunun ürettiği (ve kaçırdığı) yer tutucu SVG.
 */
(() => {
  const kok = document.getElementById('kesfet');
  if (!kok) return;

  const deste = document.getElementById('deste');
  const bos = document.getElementById('deste-bos');
  const yukleniyor = document.getElementById('deste-yukleniyor');
  const oynatici = document.getElementById('oynatici');
  const arka = document.getElementById('kesfet-arka');
  const azHareket = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CEVRE = 201;          // dk-cal halkasının çevresi (r=32)
  const ESIK_X = 0.26;        // kart genişliğinin oranı — yatay karar eşiği
  const ESIK_Y = 0.18;        // kart yüksekliğinin oranı — yukarı karar eşiği
  const ESIK_HIZ = 0.55;      // px/ms — kısa ama hızlı savuruş da karar sayılır

  let sesAcik = true;
  try { sesAcik = localStorage.getItem('kesif_ses') !== '0'; } catch (_) { /* gizli pencere */ }

  const d = {
    calisma: kok.dataset.calisma,
    eksen: kok.dataset.eksen,
    kaynak: kok.dataset.kaynak || 'ana',
    muzisyen: kok.dataset.muzisyen || '',
    rol: kok.dataset.rol || 'drums',
    bitis: null,
    kuyruk: [],            // sıradaki kartlar; [0] en üstte
    gecmis: [],            // geri alma yığını: {k, eylem}
    getiriliyor: false,
    bitti: false,
    etkilesim: false,      // tarayıcı ilk dokunuştan önce sesi çaldırmaz
    islemde: false,
  };

  /* ------------------------------------------------------------ ağ --- */

  async function api(yol, secenek = {}) {
    const yanit = await fetch(yol, {
      headers: { 'Content-Type': 'application/json' }, cache: 'no-store', ...secenek,
    });
    if (yanit.status === 401) { location.href = '/giris'; throw new Error('oturum'); }
    if (!yanit.ok) throw new Error(String(yanit.status));
    return yanit.json();
  }

  async function partiGetir() {
    if (d.getiriliyor || d.bitti) return;
    d.getiriliyor = true;
    const q = new URLSearchParams({
      calisma: d.calisma, adet: '8', kaynak: d.kaynak,
      haric: d.kuyruk.map((k) => k.aday_id).join(','),
    });
    if (d.eksen !== '') q.set('eksen', d.eksen);
    if (d.muzisyen) { q.set('muzisyen', d.muzisyen); q.set('rol', d.rol); }
    try {
      const v = await api(`/api/kesfet/deste?${q}`);
      const mevcut = new Set(d.kuyruk.map((k) => k.aday_id));
      const yeni = v.kartlar.filter((k) => !mevcut.has(k.aday_id));
      d.kuyruk.push(...yeni);
      if (v.kalan === 0) { d.bitti = true; d.bitis = v.bitis || null; d.bitisBilgi = v; }
    } catch (h) {
      if (h.message !== 'oturum') bildir(t('Kartlar alınamadı. Bağlantını kontrol et.', 'Couldn\'t load cards. Check your connection.'));
    } finally {
      d.getiriliyor = false;
    }
    ciz();
    onYukle();
  }

  /* Kart medyası (kapak + taze önizleme). İlk üç kart için önceden. */
  async function medyaHazirla(k) {
    if (k._medya) return k._medya;
    k._medya = api(`/api/medya/${k.aday_id}`).then((m) => {
      Object.assign(k, {
        kapak: m.kapak || k.kapak, sanatci_gorsel: m.sanatci_gorsel || k.sanatci_gorsel,
        parca_adi: m.parca_adi || k.parca_adi, album_adi: m.album_adi || k.album_adi,
        onizleme: m.onizleme || null, yedek: m.yedek || 0,
        _alinma: Date.now(),
      });
      if (k.kapak) { const i = new Image(); i.decoding = 'async'; i.src = k.kapak; }
      kartGuncelle(k);
      return k;
    }).catch(() => { k._medya = null; return k; });
    return k._medya;
  }

  function onYukle() {
    d.kuyruk.slice(0, 4).forEach((k, i) => {
      medyaHazirla(k).then(() => {
        // Sıradaki kartın sesini ısıt: kart üste çıktığında gecikme olmasın.
        if (i === 1 && k.onizleme) { const a = new Audio(); a.preload = 'auto'; a.src = k.onizleme; }
      });
    });
  }

  /* ---------------------------------------------------------- çizim --- */

  function ogeler(kart) {
    return {
      gorsel: kart.querySelector('.dk-gorsel'),
      cal: kart.querySelector('.dk-cal'),
      halka: kart.querySelector('.dk-cal circle'),
      sag: kart.querySelector('.dk-damga.sag'),
      sol: kart.querySelector('.dk-damga.sol'),
      ust: kart.querySelector('.dk-damga.ust'),
    };
  }

  function el(etiket, sinif, metin) {
    const e = document.createElement(etiket);
    if (sinif) e.className = sinif;
    if (metin != null) e.textContent = metin;
    return e;
  }

  function disBag(ad, url) {
    const a = el('a', 'dis-link', ad);
    a.href = url; a.target = '_blank'; a.rel = 'noopener';
    return a;
  }

  function kartOlustur(k) {
    const kart = el('article', 'deste-kart');
    kart.dataset.aday = k.aday_id;
    kart.setAttribute('aria-label', `${k.artist} — ${k.title}`);

    const gorsel = el('div', 'dk-gorsel');
    gorsel.innerHTML = k.yer_tutucu || '';           // sunucuda kaçırılmış SVG
    const ust = el('div', 'dk-ust');
    ust.append(el('span', 'rozet mavi', k.eksen_ad), el('span', 'rozet mor', k.strateji_ad));
    gorsel.append(ust,
      el('div', 'dk-damga sag', t('Listeye', 'Save')), el('div', 'dk-damga sol', t('Geç', 'Pass')),
      el('div', 'dk-damga ust', t('Biliyorum', 'Know it')));
    const cal = el('button', 'dk-cal');
    cal.type = 'button';
    cal.setAttribute('aria-label', t('Önizlemeyi çal', 'Play preview'));
    cal.innerHTML = `<svg viewBox="0 0 68 68" aria-hidden="true"><circle cx="34" cy="34" r="32"/></svg><span>▶</span>`;
    gorsel.append(cal);

    const govde = el('div', 'dk-govde');
    govde.append(el('h2', 'dk-sanatci', k.artist));
    const eser = el('p', 'dk-eser');
    eser.append(el('b', null, k.title));
    govde.append(eser, el('p', 'dk-parca'), el('p', 'dk-geri-bildirim'));
    const gerekce = el('p', 'dk-gerekce', k.gerekce);
    gerekce.title = t('Dokun, tamamını göster', 'Tap to read it all');
    govde.append(gerekce);
    const etiketler = el('div', 'etiketler');
    (k.olcum || []).forEach((e) => etiketler.append(el('span', 'rozet gri', e)));
    (k.baglam || []).forEach((e) => etiketler.append(el('span', 'rozet mavi', `◑ ${e}`)));
    if (etiketler.childElementCount) govde.append(etiketler);
    govde.append(el('div', 'dk-dis'));

    kart.append(gorsel, govde);
    kartGuncelle(k, kart);
    surukleBagla(kart);
    return kart;
  }

  /* Medya geldikçe kartı yerinde güncelle (yeniden kurmadan). */
  function kartGuncelle(k, kart) {
    kart = kart || deste.querySelector(`.deste-kart[data-aday="${k.aday_id}"]:not(.giden)`);
    if (!kart) return;
    const g = kart.querySelector('.dk-gorsel');
    // Ana görsel: albüm kapağı; yoksa sanatçı fotoğrafı. Kapak varken fotoğraf
    // köşede yuvarlak durur — kart hem albümü hem sanatçıyı gösterir.
    const ana = k.kapak || k.sanatci_gorsel;
    if (ana && !g.querySelector('img.dk-ana')) {
      const img = new Image();
      img.alt = ''; img.decoding = 'async'; img.draggable = false;
      img.className = 'dk-ana';
      img.onload = () => img.classList.add('yuklendi');
      img.onerror = () => img.remove();          // yer tutucu görünür kalır
      img.src = ana;
      g.insertBefore(img, g.querySelector('.dk-ust'));
    }
    if (k.kapak && k.sanatci_gorsel && !g.querySelector('img.dk-avatar')) {
      const av = new Image();
      av.alt = k.artist; av.decoding = 'async'; av.draggable = false;
      av.className = 'dk-avatar';
      av.onload = () => av.classList.add('yuklendi');
      av.onerror = () => av.remove();
      av.src = k.sanatci_gorsel;
      g.append(av);
    }
    const eser = kart.querySelector('.dk-eser');
    eser.replaceChildren(el('b', null, k.title));
    const ek = [k.album_adi && k.album_adi !== k.title ? k.album_adi : null, k.year].filter(Boolean);
    if (ek.length) eser.append(document.createTextNode(` · ${ek.join(' · ')}`));

    const parca = kart.querySelector('.dk-parca');
    parca.replaceChildren();
    if (k.parca_adi && k.parca_adi !== k.title) parca.append(`▸ ${k.parca_adi}`);
    if (k.yedek) parca.append(el('span', 'yedek', t('  · önerilen parçanın önizlemesi yok, yerine bu çalıyor', '  · the suggested track has no preview, playing this one instead')));

    const gb = kart.querySelector('.dk-geri-bildirim');
    gb.textContent = k.geri_bildirim || '';
    gb.className = `dk-geri-bildirim ${k.geri_bildirim_yon === 'eksi' ? 'eksi' : ''}`;

    const q = `${k.artist} ${k.parca_adi || k.title}`;
    const dis = kart.querySelector('.dk-dis');
    dis.replaceChildren(el('span', 'etiket-ust', t('tam dinle', 'full track')),
      disBag('Spotify', `https://open.spotify.com/search/${encodeURIComponent(q)}`),
      disBag('YT Music', `https://music.youtube.com/search?q=${encodeURIComponent(q)}`),
      disBag('Deezer', `https://www.deezer.com/search/${encodeURIComponent(q)}`),
      disBag('Bandcamp', `https://bandcamp.com/search?q=${encodeURIComponent(`${k.artist} ${k.album_adi || k.title}`)}`));

    // Medya çözülene kadar düğme açık; çözüldü ve önizleme yoksa kapalı.
    const cal = kart.querySelector('.dk-cal');
    cal.disabled = 'onizleme' in k && !k.onizleme;
    if (cal.disabled) cal.title = t('Bunun önizlemesi yok. Tam dinlemek için alttaki bağlantıları kullan.', 'No preview for this one. Use the links below to hear it in full.');
    if (kart.dataset.sira === '0') arkaPlan(k);
  }

  function ciz() {
    const canli = [...deste.querySelectorAll('.deste-kart:not(.giden)')];
    const hedef = d.kuyruk.slice(0, 3);
    // Kuyrukta artık olmayan kartları kaldır.
    canli.forEach((kart) => {
      if (!hedef.some((k) => k.aday_id === kart.dataset.aday)) kart.remove();
    });
    hedef.forEach((k, i) => {
      let kart = deste.querySelector(`.deste-kart[data-aday="${k.aday_id}"]:not(.giden)`);
      if (!kart) {
        // Giriş animasyonu CSS'te (`.giris`), durum ise HEMEN doğru. Eskiden
        // kart görünmez (sira=3) doğup bir rAF ile yerine alınıyordu; sekme
        // arka plandayken rAF çalışmıyor ve deste boş görünüyordu (ölçüldü).
        kart = kartOlustur(k);
        kart.dataset.sira = String(i);
        kart.classList.add('giris');
        deste.prepend(kart);
      } else {
        kart.dataset.sira = String(i);
      }
      kart.style.zIndex = String(10 - i);
    });
    yukleniyor.hidden = d.kuyruk.length > 0 || !d.getiriliyor;
    const bitti = d.kuyruk.length === 0 && !d.getiriliyor;
    bos.hidden = !bitti;
    if (bitti) { oynatici.pause(); arka.classList.remove('acik'); bitisMetni(); }
    const ustte = d.kuyruk[0];
    if (ustte && deste.dataset.calan !== ustte.aday_id) {
      deste.dataset.calan = ustte.aday_id;
      calmayaHazirla(ustte);
    }
  }

  /* Müzisyen destesi bittiğinde NEDEN bittiğini söyle: benzerlik eşiğin
   * altına düştü mü, yoksa bu müzisyenin ölçülmüş profili mi yok. */
  function bitisMetni() {
    if (!d.muzisyen) return;
    const ad = kok.dataset.muzisyenAdi || '';
    const v = d.bitisBilgi || {};
    const esik = Math.round((v.esik || 0.5) * 100);
    const baslik = bos.querySelector('h2');
    const metin = document.getElementById('deste-bos-metin');
    if (d.bitis === 'profil_yok') {
      baslik.textContent = t('Karşılaştıracak profil yok', 'Nothing to compare against');
      metin.textContent = t(`${ad} için ayrılmış kanal profili ya da ölçülmüş aday bulunamadı.`,
                            `There's no separated-stem profile for ${ad}, or no measured picks to compare.`);
    } else {
      baslik.textContent = t(`${ad} gibi çalan başka kimse yok`, `No one else plays like ${ad}`);
      metin.textContent = t(`Kalan adayların benzerliği %${esik}'in altına düştü. Daha uzaktakileri göstermek, benzemeyenleri benziyor diye sunmak olurdu.`,
                            `Everyone left is under ${esik}% alike. Showing them would mean passing off poor matches as similar.`);
    }
  }

  function ustKart() {
    return deste.querySelector('.deste-kart[data-sira="0"]:not(.giden)');
  }

  function arkaPlan(k) {
    const img = arka.querySelector('img');
    const kaynak = k.kapak || k.sanatci_gorsel;
    if (!kaynak) { arka.classList.remove('acik'); return; }
    if (img.getAttribute('src') !== kaynak) {
      arka.classList.remove('acik');
      img.onload = () => arka.classList.add('acik');
      img.src = kaynak;
    } else {
      arka.classList.add('acik');
    }
  }

  /* ---------------------------------------------------------- ses --- */

  async function calmayaHazirla(k) {
    oynatici.pause();
    halkaSifirla();
    await medyaHazirla(k);
    if (d.kuyruk[0] !== k) return;              // bu arada kaydırıldı
    arkaPlan(k);
    medyaOturumu(k);
    // İmzalı adres ~15 dk yaşıyor; kart uzun süre bekletildiyse tazele.
    if (k.onizleme && Date.now() - (k._alinma || 0) > 12 * 60 * 1000) {
      k._medya = null; await medyaHazirla(k);
    }
    if (!k.onizleme) { calDugmesi(false); return; }
    oynatici.src = k.onizleme;
    if (sesAcik && d.etkilesim) oynatici.play().catch(() => calDugmesi(false));
  }

  function calDugmesi(caliyor) {
    const kart = ustKart();
    if (!kart) return;
    const s = kart.querySelector('.dk-cal span');
    if (s) s.textContent = caliyor ? '❚❚' : '▶';
    kart.querySelector('.dk-cal')?.setAttribute('aria-label', caliyor ? t('Durdur', 'Pause') : t('Önizlemeyi çal', 'Play preview'));
  }

  function halkaSifirla() {
    const h = ustKart()?.querySelector('.dk-cal circle');
    if (h) h.style.strokeDashoffset = String(CEVRE);
  }

  function calDurdur() {
    const k = d.kuyruk[0];
    if (!k || !k.onizleme) return;
    d.etkilesim = true;
    if (oynatici.paused) {
      if (!oynatici.src) oynatici.src = k.onizleme;
      oynatici.play().catch(() => bildir(t('Önizleme çalınamadı', 'Couldn\'t play the preview')));
    } else {
      oynatici.pause();
    }
  }

  oynatici.addEventListener('play', () => calDugmesi(true));
  oynatici.addEventListener('pause', () => calDugmesi(false));
  oynatici.addEventListener('ended', () => calDugmesi(false));
  oynatici.addEventListener('timeupdate', () => {
    const h = ustKart()?.querySelector('.dk-cal circle');
    if (h && oynatici.duration) {
      h.style.strokeDashoffset = String(CEVRE * (1 - oynatici.currentTime / oynatici.duration));
    }
  });
  // İmza dolmuşsa (403) bir kez tazele ve yeniden dene.
  oynatici.addEventListener('error', async () => {
    const k = d.kuyruk[0];
    if (!k || k._yenilendi) return;
    k._yenilendi = true; k._medya = null;
    await medyaHazirla(k);
    if (d.kuyruk[0] === k && k.onizleme) {
      oynatici.src = k.onizleme;
      if (d.etkilesim && sesAcik) oynatici.play().catch(() => {});
    }
  });

  /* Kilit ekranı / bildirim merkezi: kapak, sanatçı, albüm. */
  function medyaOturumu(k) {
    if (!('mediaSession' in navigator)) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: k.parca_adi || k.title, artist: k.artist, album: k.album_adi || k.title,
        artwork: k.kapak ? [{ src: k.kapak, sizes: '1000x1000', type: 'image/jpeg' }] : [],
      });
      navigator.mediaSession.setActionHandler('play', () => oynatici.play());
      navigator.mediaSession.setActionHandler('pause', () => oynatici.pause());
    } catch (_) { /* eski tarayıcı */ }
  }

  /* -------------------------------------------------------- karar --- */

  async function karar(eylem, surukleme) {
    const kart = ustKart();
    const k = d.kuyruk[0];
    if (!kart || !k || d.islemde) return;
    d.etkilesim = true;
    d.islemde = true;

    const [yx, yy] = { begendim: [1, 0], tutmadi: [-1, 0], zaten_biliyorum: [0, -1] }[eylem];
    const dy = surukleme ? surukleme.dy : 0;
    kart.classList.remove('surukleniyor');
    kart.classList.add('giden');
    kart.style.transform = azHareket ? '' :
      `translate(${yx * innerWidth * 1.05}px, ${yy ? -innerHeight : dy}px) rotate(${yx * 22}deg)`;
    kart.style.opacity = '0';
    setTimeout(() => kart.remove(), 450);
    if (navigator.vibrate) navigator.vibrate(eylem === 'begendim' ? [8, 30, 8] : 8);
    dugmeVurgula(eylem);

    d.kuyruk.shift();
    d.gecmis.push({ k, eylem });
    if (d.gecmis.length > 30) d.gecmis.shift();
    ciz();
    d.islemde = false;
    if (d.kuyruk.length < 4) partiGetir();
    onYukle();

    try {
      const v = await api('/api/kesfet/karar', {
        method: 'POST',
        body: JSON.stringify({ aday_id: k.aday_id, calisma_id: k.calisma_id || d.calisma, karar: eylem }),
      });
      sayaclar(v);
      if (eylem === 'begendim') bildir(t(`♥ ${k.artist} listene eklendi`, `♥ ${k.artist} saved to your list`), t('Geri al', 'Undo'), geriAl);
    } catch (h) {
      // Sunucu kabul etmedi: kartı geri koy. Kaybolmuş sanılan bir karar
      // kaydedilmiş sanılan bir karardan iyidir.
      const i = d.gecmis.findIndex((g) => g.k === k);
      if (i >= 0) d.gecmis.splice(i, 1);
      d.kuyruk.unshift(k);
      ciz();
      if (h.message !== 'oturum') bildir(t('Karar kaydedilemedi, kart geri geldi.', 'Couldn\'t save that, so the card is back.'));
    }
  }

  async function geriAl() {
    const son = d.gecmis.pop();
    if (!son) { bildir(t('Geri alınacak bir karar yok', 'Nothing to undo')); return; }
    try {
      const v = await api('/api/kesfet/geri-al', {
        method: 'POST', body: JSON.stringify({ aday_id: son.k.aday_id, calisma_id: son.k.calisma_id || d.calisma }),
      });
      sayaclar(v);
    } catch (_) {
      d.gecmis.push(son);
      bildir(t('Geri alınamadı', 'Couldn\'t undo'));
      return;
    }
    d.kuyruk.unshift(son.k);
    // Kart gittiği yönden geri gelir: önce oraya koy, sonra bırak.
    deste.dataset.calan = '';
    ciz();
    const kart = ustKart();
    if (kart && !azHareket && kart.animate) {
      // Tek anahtar kare: bitiş, kartın kendi (CSS) konumu. Animasyon bitince
      // hiçbir iz bırakmaz — durum yine yalnız `data-sira`da.
      const [yx, yy] = { begendim: [1, 0], tutmadi: [-1, 0], zaten_biliyorum: [0, -1] }[son.eylem];
      kart.classList.remove('giris');
      kart.animate(
        [{ transform: `translate(${yx * innerWidth}px, ${yy * innerHeight}px) rotate(${yx * 22}deg)`, opacity: 0 }],
        { duration: 480, easing: 'cubic-bezier(.34,1.36,.64,1)' });
    }
    bildir(t(`↺ ${son.k.artist}: karar geri alındı`, `↺ ${son.k.artist}: decision undone`));
  }

  function sayaclar(v) {
    if (typeof v.liste === 'number') {
      document.querySelectorAll('[data-liste-sayac]').forEach((e) => { e.textContent = v.liste; e.hidden = !v.liste; });
    }
    if (v.bugun) {
      for (const [ad, deger] of Object.entries(v.bugun)) {
        const e = document.querySelector(`[data-gunluk="${ad}"]`);
        if (e) e.textContent = deger;
      }
      const seri = document.querySelector('.gunluk .seri');
      if (seri) seri.hidden = !v.bugun.seri;
    }
  }

  function dugmeVurgula(eylem) {
    const b = document.querySelector(`.deste-dugmeler [data-eylem="${eylem}"]`);
    if (!b) return;
    b.animate([{ transform: 'scale(1)' }, { transform: 'scale(.86)' }, { transform: 'scale(1)' }],
      { duration: 220, easing: 'cubic-bezier(.34,1.36,.64,1)' });
  }

  /* ---------------------------------------------------- sürükleme --- */

  function surukleBagla(kart) {
    let s = null;
    const o = ogeler(kart);

    kart.addEventListener('pointerdown', (e) => {
      if (kart.dataset.sira !== '0' || e.button > 0) return;
      if (e.target.closest('a, .dk-gerekce, .dk-cal')) return;
      d.etkilesim = true;
      s = { x0: e.clientX, y0: e.clientY, t0: performance.now(), dx: 0, dy: 0 };
      kart.setPointerCapture(e.pointerId);
      kart.classList.add('surukleniyor');
    });

    kart.addEventListener('pointermove', (e) => {
      if (!s) return;
      s.dx = e.clientX - s.x0;
      s.dy = e.clientY - s.y0;
      kart.style.transform = `translate(${s.dx}px, ${s.dy}px) rotate(${s.dx / 18}deg)`;
      const w = kart.offsetWidth, h = kart.offsetHeight;
      const yatay = Math.abs(s.dx) >= Math.abs(s.dy);
      o.sag.style.opacity = yatay ? Math.max(0, Math.min(1, s.dx / (w * ESIK_X))) : 0;
      o.sol.style.opacity = yatay ? Math.max(0, Math.min(1, -s.dx / (w * ESIK_X))) : 0;
      o.ust.style.opacity = yatay ? 0 : Math.max(0, Math.min(1, -s.dy / (h * ESIK_Y)));
    });

    const birak = (e) => {
      if (!s) return;
      const sure = Math.max(1, performance.now() - s.t0);
      const vx = s.dx / sure, vy = s.dy / sure;
      const w = kart.offsetWidth, h = kart.offsetHeight;
      const hareket = Math.hypot(s.dx, s.dy);
      const surukleme = s;
      s = null;
      [o.sag, o.sol, o.ust].forEach((x) => { x.style.opacity = 0; });

      if (hareket < 6) {                           // dokunuş: görsele dokun = çal/durdur
        kart.classList.remove('surukleniyor');
        kart.style.transform = '';
        if (e && e.target.closest('.dk-gorsel')) calDurdur();
        return;
      }
      const yatay = Math.abs(surukleme.dx) >= Math.abs(surukleme.dy);
      if (yatay && (surukleme.dx > w * ESIK_X || vx > ESIK_HIZ)) return karar('begendim', surukleme);
      if (yatay && (surukleme.dx < -w * ESIK_X || vx < -ESIK_HIZ)) return karar('tutmadi', surukleme);
      if (!yatay && (surukleme.dy < -h * ESIK_Y || vy < -ESIK_HIZ)) return karar('zaten_biliyorum', surukleme);
      // Eşik aşılmadı: yayla yerine dön.
      kart.classList.remove('surukleniyor');
      kart.style.transform = '';
    };
    kart.addEventListener('pointerup', birak);
    kart.addEventListener('pointercancel', () => birak(null));

    o.cal.addEventListener('click', (e) => { e.stopPropagation(); calDurdur(); });
    kart.querySelector('.dk-gerekce').addEventListener('click', (e) => {
      e.currentTarget.classList.toggle('acik');
    });
  }

  /* ------------------------------------------------ düğme / klavye --- */

  const egitimAcik = () => !document.getElementById('egitim')?.hidden;

  document.querySelector('.deste-dugmeler').addEventListener('click', (e) => {
    const b = e.target.closest('[data-eylem]');
    if (!b) return;
    const eylem = b.dataset.eylem;
    if (eylem === 'geri') geriAl();
    else if (eylem === 'ses') sesDegistir();
    else karar(eylem);
  });

  function sesDegistir() {
    sesAcik = !sesAcik;
    try { localStorage.setItem('kesif_ses', sesAcik ? '1' : '0'); } catch (_) { /* yok say */ }
    const b = document.querySelector('.deste-dugmeler [data-eylem="ses"]');
    if (b) b.textContent = sesAcik ? '🔊' : '🔇';
    if (!sesAcik) oynatici.pause();
    else { d.etkilesim = true; calDurdur(); }
    bildir(sesAcik ? t('Otomatik çalma açık', 'Autoplay on') : t('Otomatik çalma kapalı', 'Autoplay off'));
  }
  if (!sesAcik) {
    const b = document.querySelector('.deste-dugmeler [data-eylem="ses"]');
    if (b) b.textContent = '🔇';
  }

  document.addEventListener('keydown', (e) => {
    if (e.target.closest('input, select, textarea') || e.metaKey || e.ctrlKey || e.altKey) return;
    if (egitimAcik()) return;
    const tus = { ArrowRight: 'begendim', ArrowLeft: 'tutmadi', ArrowUp: 'zaten_biliyorum' }[e.key];
    if (tus) { e.preventDefault(); karar(tus); return; }
    if (e.key === ' ') { e.preventDefault(); calDurdur(); return; }
    if (e.key === 'z' || e.key === 'Z' || e.key === 'Backspace') { e.preventDefault(); geriAl(); return; }
    if (e.key === 'm' || e.key === 'M') sesDegistir();
  });

  // Tarayıcı ilk kullanıcı hareketinden önce ses çaldırmaz. İlk dokunuş
  // otomatik çalmayı açar ve üstteki kartı başlatır.
  const ilk = () => {
    if (d.etkilesim) return;
    d.etkilesim = true;
    if (sesAcik && d.kuyruk[0]?.onizleme && oynatici.paused && oynatici.src) {
      oynatici.play().catch(() => {});
    }
  };
  addEventListener('pointerdown', ilk, { once: true, capture: true });
  addEventListener('keydown', ilk, { once: true, capture: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) oynatici.pause();
  });

  /* ------------------------------------------------------ büyütme --- */

  bos.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-eylem="buyut"]');
    if (!b) return;
    b.disabled = true;
    b.textContent = t('Kartlar hazırlanıyor…', 'Finding more cards…');
    bos.hidden = true;
    yukleniyor.hidden = false;
    try {
      const v = await api(`/api/kesfet/buyut?calisma=${encodeURIComponent(d.calisma)}`, { method: 'POST' });
      if (v.durum === 'tavan') {
        document.getElementById('deste-bos-metin').textContent =
          t('Ölçülmüş sınıra (her eksende 50 sıra) ulaştın. Cesur modu dene ya da yeni bir kümeleme çalıştır.',
            'You\'ve reached the measured limit (50 deep per axis). Try bold mode, or run a new clustering.');
        b.remove();
      } else {
        bildir(t(`✦ ${v.yeni} yeni aday hazır`, `✦ ${v.yeni} new candidates ready`));
      }
      d.bitti = false;
      await partiGetir();
    } catch (_) {
      bildir(t('Yeni kart getirilemedi', 'Couldn\'t find more cards'));
      b.disabled = false;
      b.textContent = t('✦ Daha derinden kart getir', '✦ Dig deeper for more cards');
      ciz();
    }
  });

  /* ---------------------------------------------------- ilk ziyaret --- */

  const egitim = document.getElementById('egitim');
  let egitimGoruldu = false;
  try { egitimGoruldu = localStorage.getItem('kesif_egitim') === '1'; } catch (_) { /* yok say */ }
  if (egitim && !egitimGoruldu) egitim.hidden = false;
  egitim?.addEventListener('click', (e) => {
    if (!e.target.closest('[data-eylem="egitim-tamam"]')) return;
    egitim.hidden = true;
    d.etkilesim = true;
    try { localStorage.setItem('kesif_egitim', '1'); } catch (_) { /* yok say */ }
    if (sesAcik && d.kuyruk[0]?.onizleme) calDurdur();
  });

  partiGetir();
})();
