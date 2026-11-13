/* «Müzik evrenin» — albümlerin üç boyutlu haritası (Sen sayfası).
 *
 * Veri sunucudan hazır gelir (python/sen.py:evren): nokta = [x, y, z, renk
 * sırası, ad], koordinatlar [-1, 1]. Burada yalnız izdüşüm ve çizim var;
 * tuval 2B, perspektif elle — birkaç yüz nokta için WebGL gereksiz.
 * Süs durum taşımaz: açı yalnız bu sayfada yaşar.
 */
(() => {
  const kok = document.getElementById('evren');
  const veri = JSON.parse(document.getElementById('evren-veri')?.textContent || 'null');
  if (!kok || !veri) return;
  const tuval = kok.querySelector('canvas');
  const etiket = kok.querySelector('.evren-etiket');
  const c = tuval.getContext('2d');
  const azHareket = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const stil = getComputedStyle(document.documentElement);
  const token = (ad) => stil.getPropertyValue(ad).trim();
  const renk = (i) => (i >= 0 && veri.renkler[i]) || veri.diger;
  const KAMERA = 3.2;                 // kameranın merkeze uzaklığı (birim küre = 1)

  let aciY = 0.6, aciX = -0.35;       // radyan
  let w = 0, h = 0, R = 0;
  let surukle = null, secili = -1, gorunur = true, donuyor = !azHareket;
  let ekran = [];                     // son çizimdeki [x, y, r, i] — isabet sınaması için

  function olc() {
    const o = devicePixelRatio || 1;
    w = tuval.clientWidth; h = tuval.clientHeight;
    tuval.width = w * o; tuval.height = h * o;
    c.setTransform(o, 0, 0, o, 0, 0);
    R = Math.min(w, h) * 0.44;
  }

  function izdusur(x, y, z) {
    const cy = Math.cos(aciY), sy = Math.sin(aciY), cx = Math.cos(aciX), sx = Math.sin(aciX);
    const x1 = x * cy + z * sy, z1 = z * cy - x * sy;
    const y1 = y * cx - z1 * sx, z2 = z1 * cx + y * sx;
    const f = KAMERA / (KAMERA - z2);
    return [w / 2 + x1 * f * R, h / 2 - y1 * f * R, z2, f];
  }

  function halka(yaricap) {            // yatay düzlemde yörünge: derinlik ipucu
    c.beginPath();
    for (let a = 0; a <= 64; a++) {
      const [x, y] = izdusur(Math.cos(a / 64 * 2 * Math.PI) * yaricap, 0, Math.sin(a / 64 * 2 * Math.PI) * yaricap);
      a ? c.lineTo(x, y) : c.moveTo(x, y);
    }
    c.stroke();
  }

  function ciz() {
    c.clearRect(0, 0, w, h);
    c.strokeStyle = token('--kenar'); c.lineWidth = 1;
    halka(0.5); halka(1);
    ekran = veri.noktalar.map((n, i) => {
      const [x, y, z, f] = izdusur(n[0], n[1], n[2]);
      return [x, y, 2.2 + f * 2.6, i, z];
    }).sort((a, b) => a[4] - b[4]);    // uzaktan yakına
    for (const [x, y, r, i, z] of ekran) {
      const n = veri.noktalar[i];
      const [tx, ty] = izdusur(n[0], 0, n[2]);   // düzlemdeki izi: yüksekliği okutan ince sap
      c.globalAlpha = 0.5; c.beginPath(); c.moveTo(x, y); c.lineTo(tx, ty); c.stroke();
      c.globalAlpha = 0.45 + 0.55 * (z + 1) / 2;
      c.fillStyle = renk(veri.noktalar[i][3]);
      c.beginPath(); c.arc(x, y, r, 0, 2 * Math.PI); c.fill();
      if (i === secili) {
        c.globalAlpha = 1; c.strokeStyle = token('--metin'); c.lineWidth = 1.5;
        c.beginPath(); c.arc(x, y, r + 4, 0, 2 * Math.PI); c.stroke();
        c.strokeStyle = token('--kenar'); c.lineWidth = 1;
      }
    }
    c.globalAlpha = 1;
  }

  function kare() {
    if (gorunur && donuyor && !surukle) { aciY += 0.0022; ciz(); }
    requestAnimationFrame(kare);
  }

  function sec(e) {
    const k = tuval.getBoundingClientRect();
    const px = e.clientX - k.left, py = e.clientY - k.top;
    let en = -1, enUzak = 16 * 16;
    for (const [x, y, , i] of ekran) {
      const u = (x - px) ** 2 + (y - py) ** 2;
      if (u <= enUzak) { en = i; enUzak = u; }   // eşitlikte öndeki (sonra çizilen) kazanır
    }
    if (en === secili) return;
    secili = en;
    etiket.replaceChildren();
    if (en >= 0) {
      const n = veri.noktalar[en];
      const tarz = veri.tarzlar.find((z) => z.renk === n[3]);
      etiket.append(n[4]);
      if (tarz) { const s = document.createElement('small'); s.textContent = tarz.ad; etiket.append(s); }
    }
    ciz();
  }

  tuval.addEventListener('pointerdown', (e) => {
    surukle = { x: e.clientX, y: e.clientY };
    tuval.setPointerCapture(e.pointerId);
    donuyor = false;                   // elle çevrildiyse kendi kendine dönmeyi bırak
    sec(e);
  });
  tuval.addEventListener('pointermove', (e) => {
    if (!surukle) { sec(e); return; }
    aciY += (e.clientX - surukle.x) * 0.008;
    aciX = Math.max(-1.3, Math.min(1.3, aciX - (e.clientY - surukle.y) * 0.008));
    surukle = { x: e.clientX, y: e.clientY };
    ciz();
  });
  const birak = () => { surukle = null; };
  tuval.addEventListener('pointerup', birak);
  tuval.addEventListener('pointercancel', birak);
  tuval.addEventListener('keydown', (e) => {
    const d = { ArrowLeft: [-0.12, 0], ArrowRight: [0.12, 0], ArrowUp: [0, 0.12], ArrowDown: [0, -0.12] }[e.key];
    if (!d) return;
    e.preventDefault();
    donuyor = false;
    aciY += d[0]; aciX = Math.max(-1.3, Math.min(1.3, aciX + d[1]));
    ciz();
  });

  new IntersectionObserver(([g]) => { gorunur = g.isIntersecting; }).observe(tuval);
  new ResizeObserver(() => { olc(); ciz(); }).observe(tuval);
  olc(); ciz();
  requestAnimationFrame(kare);
})();
