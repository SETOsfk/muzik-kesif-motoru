/* Grafikler — Chart.js ile, uygulamanın kendi tasarım değişkenlerinden.
 *
 * Neden tarayıcıda (2026-09-28): sunucuda çizilen SVG viewBox'la ölçekleniyor,
 * yani aynı 12 px yazı bir kartta 9, ötekinde 17 px çıkıyordu; çizgi
 * kalınlıkları da öyle. Burada her grafik kartın GERÇEK genişliğinde çizilir,
 * yazı ve çizgi her yerde aynıdır.
 *
 * Sözleşme: `<canvas data-kaynak="ID">` + `<script type="application/json"
 * id="ID">` içinde bir tanım ({tur: ...}). Tanımlar yalnız sayı, renk ve
 * sunucuda kurulmuş (iki dilli) metin taşır. Renkler web/grafik.py:
 * TARZ_RENKLERI'nden gelir; nötrler stil.css tokenlarından okunur.
 *
 * Panoda tarz seçimi: `document` üzerinde `pano:secim` olayı (detail = kume
 * ya da ''). Her grafik kendi `vurgula(k)` işleviyle öbür tarzları soldurur.
 */
(() => {
  if (!window.Chart) return;
  const css = getComputedStyle(document.documentElement);
  const tok = (ad, yedek) => (css.getPropertyValue(ad).trim() || yedek);
  const T = {
    metin: tok('--metin', '#20232c'), metin2: tok('--metin-2', '#4d515c'),
    metin3: tok('--metin-3', '#6c6f7a'), kenar: tok('--kenar', '#dcd4c6'),
    izgara: tok('--zemin-2', '#eae4d8'), kart: tok('--kart', '#fbf9f4'),
    vurgu: tok('--vurgu', '#bb4628'), ikincil: tok('--ikincil', '#2e3a66'),
    govde: tok('--font-govde', 'Georgia, serif'), etiket: tok('--font-etiket', 'system-ui, sans-serif'),
  };
  const azHareket = matchMedia('(prefers-reduced-motion: reduce)').matches;

  Chart.defaults.font.family = T.govde;
  Chart.defaults.font.size = 12.5;
  Chart.defaults.color = T.metin2;
  Chart.defaults.borderColor = T.izgara;
  if (azHareket) Chart.defaults.animation = false;
  else { Chart.defaults.animation.duration = 550; Chart.defaults.animation.easing = 'easeOutQuart'; }
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.plugins.legend.display = false;
  Object.assign(Chart.defaults.plugins.tooltip, {
    backgroundColor: T.metin, titleColor: T.kart, bodyColor: T.kart, footerColor: T.kart,
    titleFont: { family: T.etiket, size: 11, weight: '600' }, bodyFont: { family: T.govde, size: 13 },
    padding: 10, cornerRadius: 8, boxPadding: 5, usePointStyle: true, caretSize: 5,
  });

  /* #rrggbb → rgba */
  const saydam = (hex, a) => {
    const h = hex.replace('#', '');
    const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  };
  const eksenYazi = { family: T.etiket, size: 11 };
  const secili = () => (document.querySelector('[data-pano]')?.dataset.secili || '');
  const soluk = (kume, k) => k !== '' && String(kume) !== String(k);
  const sayiBicim = (v) => new Intl.NumberFormat(document.documentElement.lang || 'tr').format(v);

  const cizerler = {
    /* Tarz haritası: kabarcık = tarz (alan ∝ albüm), çizgi = köprü albümler. */
    harita(tuval, d) {
      const enBuyuk = Math.max(...d.tarzlar.map((t) => t.album), 1);
      const yaricap = (t, gen) => (9 + 26 * Math.sqrt(t.album / enBuyuk)) * Math.min(1, gen / 520);
      // Üst üste binen kabarcıkları normalize uzayda it (deterministik).
      const nok = d.tarzlar.map((t) => ({ ...t }));
      const gen0 = tuval.parentElement.clientWidth || 600, yuk0 = tuval.parentElement.clientHeight || 320;
      for (let tur = 0; tur < 150; tur++) {
        let oynadi = false;
        for (let i = 0; i < nok.length; i++) for (let j = i + 1; j < nok.length; j++) {
          const a = nok[i], b = nok[j];
          const dx = (b.x - a.x) * gen0, dy = (b.y - a.y) * yuk0;
          const mes = Math.hypot(dx, dy) || 0.5;
          const gerek = yaricap(a, gen0) + yaricap(b, gen0) + (gen0 < 520 ? 52 : 30);  // + etiket payı
          if (mes < gerek) {
            const it = (gerek - mes) / 2, ux = dx / mes || 1, uy = dy / mes;
            a.x -= (ux * it) / gen0; a.y -= (uy * it) / yuk0; b.x += (ux * it) / gen0; b.y += (uy * it) / yuk0;
            oynadi = true;
          }
        }
        if (!oynadi) break;
      }
      // İtme kabarcıkları alanın dışına taşırabilir: 0–1'e geri kıs.
      nok.forEach((t) => { t.x = Math.min(1, Math.max(0, t.x)); t.y = Math.min(1, Math.max(0, t.y)); });
      const enR = (9 + 26) * Math.min(1, gen0 / 520);
      const yer = Object.fromEntries(nok.map((t, i) => [t.kume, i]));
      const enCok = Math.max(...d.kopruler.map((k) => k[2]), 1);
      const kopruCiz = {
        id: 'kopru',
        beforeDatasetsDraw(ch) {
          const c = ch.ctx, m = ch.getDatasetMeta(0).data, k = secili();
          c.save(); c.lineCap = 'round';
          d.kopruler.forEach(([a, b, n]) => {
            if (!(a in yer) || !(b in yer)) return;
            const p = m[yer[a]], q = m[yer[b]];
            const ilgili = k === '' || String(a) === k || String(b) === k;
            c.strokeStyle = saydam(T.metin3, ilgili ? 0.38 : 0.08);
            c.lineWidth = 1.5 + 7 * (n / enCok);
            c.beginPath(); c.moveTo(p.x, p.y); c.lineTo(q.x, q.y); c.stroke();
          });
          c.restore();
        },
        afterDatasetsDraw(ch) {
          const c = ch.ctx, m = ch.getDatasetMeta(0).data, k = secili();
          c.save(); c.textAlign = 'center';
          nok.forEach((t, i) => {
            const p = m[i], r = p.options.radius, sol = soluk(t.kume, k);
            c.globalAlpha = sol ? 0.25 : 1;
            c.fillStyle = '#fff'; c.font = `600 ${r > 16 ? 13 : 11}px ${T.etiket}`; c.textBaseline = 'middle';
            c.fillText(sayiBicim(t.album), p.x, p.y);
            c.fillStyle = T.metin; c.font = `500 12.5px ${T.govde}`; c.textBaseline = 'top';
            c.fillText(t.ad.length > 22 ? t.ad.slice(0, 21) + '…' : t.ad, p.x, p.y + r + 5);
          });
          c.restore();
        },
      };
      const ch = new Chart(tuval, {
        type: 'bubble',
        data: { datasets: [{
          data: nok.map((t) => ({ x: t.x, y: t.y })),   // r yok: yarıçap aşağıdaki işlevden
          radius: (ctx) => yaricap(nok[ctx.dataIndex], ctx.chart.width),
          hoverRadius: (ctx) => yaricap(nok[ctx.dataIndex], ctx.chart.width) + 3,
          backgroundColor: nok.map((t) => t.renk), borderColor: T.kart, borderWidth: 3, hoverBorderWidth: 3,
          clip: false,
        }] },
        options: {
          layout: { padding: { top: enR + 6, bottom: enR + 26, left: enR + 34, right: enR + 34 } },
          scales: { x: { display: false, min: -0.02, max: 1.02 }, y: { display: false, min: -0.02, max: 1.02, reverse: true } },
          plugins: { tooltip: { callbacks: {
            title: (it) => nok[it[0].dataIndex].ad,
            label: (it) => `${sayiBicim(nok[it.dataIndex].album)} ${d.birim}`,
          } } },
          onHover: (e, el) => { e.native.target.style.cursor = el.length ? 'pointer' : 'default'; },
          onClick: (e, el) => { if (el.length && window.panoSec) window.panoSec(String(nok[el[0].index].kume), true); },
        },
        plugins: [kopruCiz],
      });
      ch.vurgula = (k) => {
        ch.data.datasets[0].backgroundColor = nok.map((t) => (soluk(t.kume, k) ? saydam(t.renk, 0.18) : t.renk));
        ch.update();
      };
      return ch;
    },

    /* On yıl × tarz: yığılı sütun. Parçalar arası ince kâğıt aralığı. */
    yigin_sutun(tuval, d) {
      const ch = new Chart(tuval, {
        type: 'bar',
        data: { labels: d.etiketler, datasets: d.seriler.map((s) => ({
          label: s.ad, kume: s.kume, renk: s.renk, data: s.veri, backgroundColor: s.renk,
          borderColor: T.kart, borderWidth: { top: 2 }, borderRadius: 3, borderSkipped: 'bottom',
          maxBarThickness: 56,
        })) },
        options: {
          scales: {
            x: { stacked: true, grid: { display: false }, ticks: { font: eksenYazi }, border: { display: false } },
            y: { stacked: true, beginAtZero: true, grid: { color: T.izgara }, border: { display: false },
                 ticks: { font: eksenYazi, precision: 0, maxTicksLimit: 5 } },
          },
          interaction: { mode: 'index', intersect: false },
          plugins: { tooltip: { filter: (it) => it.raw > 0, itemSort: (a, b) => b.raw - a.raw,
            callbacks: { label: (it) => ` ${it.dataset.label}: ${it.raw} ${d.birim}` } } },
        },
      });
      ch.vurgula = (k) => {
        ch.data.datasets.forEach((ds) => { ds.backgroundColor = soluk(ds.kume, k) ? saydam(ds.renk, 0.13) : ds.renk; });
        ch.update();
      };
      return ch;
    },

    /* Netlik: tarz başına «net ait» (dolu) + «arada» (açık) yığını. */
    netlik(tuval, d) {
      const S = d.satirlar;
      const ch = new Chart(tuval, {
        type: 'bar',
        data: { labels: S.map((s) => s.ad), datasets: [
          { label: d.parcalar[0], data: S.map((s) => s.net), backgroundColor: S.map((s) => s.renk),
            borderRadius: { topLeft: 4, bottomLeft: 4 }, borderSkipped: false, barThickness: 14 },
          { label: d.parcalar[1], data: S.map((s) => s.arada), backgroundColor: S.map((s) => saydam(s.renk, 0.32)),
            borderRadius: { topRight: 4, bottomRight: 4 }, borderSkipped: false, barThickness: 14 },
        ] },
        options: {
          indexAxis: 'y',
          scales: {
            x: { stacked: true, grid: { color: T.izgara }, border: { display: false }, ticks: { font: eksenYazi, precision: 0, maxTicksLimit: 5 } },
            y: { stacked: true, grid: { display: false }, border: { display: false }, ticks: { color: T.metin } },
          },
          interaction: { mode: 'index', intersect: false },
          plugins: { tooltip: { callbacks: { label: (it) => ` ${it.dataset.label}: ${it.raw} ${d.birim}` } } },
        },
      });
      ch.vurgula = (k) => {
        ch.data.datasets[0].backgroundColor = S.map((s) => (soluk(s.kume, k) ? saydam(s.renk, 0.15) : s.renk));
        ch.data.datasets[1].backgroundColor = S.map((s) => saydam(s.renk, soluk(s.kume, k) ? 0.06 : 0.32));
        ch.update();
      };
      return ch;
    },

    /* Aralık: bant = alt–üst, nokta = orta (tempo çeyrekleri, Wilson aralıkları). */
    aralik(tuval, d) {
      const S = d.satirlar, b = d.yuzde ? '%' : '';
      const bicim = (v) => (d.uclar ? `${Math.round(v)}.` : d.yuzde ? `%${Math.round(v)}` : `${Math.round(v)}`);
      const ch = new Chart(tuval, {
        type: 'bar',
        data: { labels: S.map((s) => s.ad), datasets: [
          { type: 'scatter', label: 'orta', data: S.map((s, i) => ({ x: s.orta, y: s.ad })),
            pointRadius: 6.5, pointHoverRadius: 8, pointBackgroundColor: S.map((s) => s.renk),
            pointBorderColor: T.kart, pointBorderWidth: 2, clip: false },
          { label: 'aralık', data: S.map((s) => [s.alt, s.ust]), backgroundColor: S.map((s) => saydam(s.renk, 0.28)),
            borderRadius: 8, borderSkipped: false, barThickness: 12 },
        ] },
        options: {
          indexAxis: 'y',
          scales: {
            x: { min: d.yuzde ? d.alan[0] : Math.floor(d.alan[0] / 20) * 20,
                 max: d.yuzde ? d.alan[1] : Math.ceil(d.alan[1] / 20) * 20,
                 grid: { color: (c) => (d.uclar && c.tick.value === 50 ? T.kenar : T.izgara),
                         lineWidth: (c) => (d.uclar && c.tick.value === 50 ? 1.5 : 1) },
                 border: { display: false },
                 ticks: d.uclar
                   ? { font: eksenYazi, stepSize: 25, align: 'inner', autoSkip: false, maxRotation: 0,
                       callback: (v) => (v === 0 ? `← ${d.uclar[0]}` : v === 100 ? `${d.uclar[1]} →` : '') }
                   : { font: eksenYazi, maxTicksLimit: 7, stepSize: d.yuzde ? 25 : 20, callback: (v) => bicim(v) },
                 title: { display: !d.yuzde, text: d.birim, font: eksenYazi, color: T.metin3 } },
            y: { type: 'category', labels: S.map((s) => s.ad), grid: { display: false }, border: { display: false }, ticks: { color: T.metin } },
          },
          plugins: { tooltip: { filter: (it) => it.datasetIndex === 0, callbacks: {
            title: (it) => S[it[0].dataIndex].ad,
            label: (it) => { const s = S[it.dataIndex]; return ` ${bicim(s.orta)} (${bicim(s.alt)}–${bicim(s.ust)}${d.yuzde ? '' : ' ' + d.birim})`; },
            footer: (it) => S[it[0].dataIndex].not || '',
          } } },
        },
      });
      ch.vurgula = (k) => {
        ch.data.datasets[0].pointBackgroundColor = S.map((s) => (soluk(s.kume, k) ? saydam(s.renk, 0.2) : s.renk));
        ch.data.datasets[1].backgroundColor = S.map((s) => saydam(s.renk, soluk(s.kume, k) ? 0.07 : 0.28));
        ch.update();
      };
      return ch;
    },

    /* Yatay çubuk (sanatçılar, enstrüman dengesi…). */
    cubuk(tuval, d) {
      const S = d.satirlar;
      const ch = new Chart(tuval, {
        type: 'bar',
        data: { labels: S.map((s) => s.ad), datasets: [{ data: S.map((s) => s.deger),
          backgroundColor: S.map((s) => s.renk || T.ikincil), borderRadius: 4, borderSkipped: false, barThickness: 12 }] },
        options: {
          indexAxis: 'y',
          scales: {
            x: { beginAtZero: true, grid: { color: T.izgara }, border: { display: false },
                 ticks: { font: eksenYazi, maxTicksLimit: 5, precision: d.basamak ? undefined : 0 } },
            y: { grid: { display: false }, border: { display: false }, ticks: { color: T.metin } },
          },
          plugins: { tooltip: { callbacks: {
            label: (it) => ` ${sayiBicim(it.raw)} ${d.birim || ''}`,
            footer: (it) => S[it[0].dataIndex].not || '',
          } } },
        },
      });
      ch.vurgula = (k) => {
        ch.data.datasets[0].backgroundColor = S.map((s) => (soluk(s.kume, k) ? saydam(s.renk || T.ikincil, 0.15) : (s.renk || T.ikincil)));
        ch.update();
      };
      return ch;
    },

    /* Halka: kararların dağılımı, ortada beğeni oranı. */
    halka(tuval, d) {
      const merkez = {
        id: 'merkez',
        afterDraw(ch) {
          const { ctx, chartArea: a } = ch, x = (a.left + a.right) / 2, y = (a.top + a.bottom) / 2;
          ctx.save(); ctx.textAlign = 'center'; ctx.fillStyle = T.metin;
          ctx.font = `400 ${Math.min(34, a.width / 5)}px ${T.govde}`; ctx.textBaseline = 'alphabetic';
          ctx.fillText(d.merkez, x, y + 6);
          ctx.fillStyle = T.metin3; ctx.font = `500 10.5px ${T.etiket}`; ctx.textBaseline = 'top';
          ctx.fillText(d.merkez_alt.toLocaleUpperCase(document.documentElement.lang || 'tr'), x, y + 12);
          ctx.restore();
        },
      };
      return new Chart(tuval, {
        type: 'doughnut',
        data: { labels: d.parcalar.map((p) => p.ad), datasets: [{ data: d.parcalar.map((p) => p.deger),
          backgroundColor: d.parcalar.map((p) => p.renk), borderColor: T.kart, borderWidth: 3, hoverOffset: 4 }] },
        options: { cutout: '72%', plugins: { tooltip: { callbacks: { label: (it) => ` ${it.label}: ${it.raw}` } } } },
        plugins: [merkez],
      });
    },

    /* Radar: tarzların ses imzası, 50 = kütüphanenin ortası. */
    radar(tuval, d) {
      const ch = new Chart(tuval, {
        type: 'radar',
        data: { labels: d.eksenler, datasets: d.seriler.map((s) => ({
          label: s.ad, kume: s.kume, renk: s.renk, data: s.veri,
          borderColor: s.renk, backgroundColor: saydam(s.renk, 0.06), borderWidth: 2,
          pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: s.renk,
        })) },
        options: {
          layout: { padding: 4 },
          scales: { r: {
            min: 0, max: 100, beginAtZero: true,
            ticks: { display: false, stepSize: 25 },
            grid: { color: (c) => (c.tick.value === 50 ? T.metin3 : T.izgara), lineWidth: (c) => (c.tick.value === 50 ? 1.2 : 1) },
            angleLines: { color: T.izgara },
            pointLabels: { color: T.metin, font: { family: T.govde, size: 12.5 } },
          } },
          plugins: { tooltip: { callbacks: {
            label: (it) => ` ${it.dataset.label}: ${it.raw}. ${document.documentElement.lang === 'en' ? 'percentile' : 'yüzdelik'}`,
            afterBody: (it) => { const u = d.uclar[it[0].dataIndex]; return u ? `0 = ${u[0]} · 100 = ${u[1]}` : ''; },
          } } },
        },
      });
      ch.vurgula = (k) => {
        ch.data.datasets.forEach((ds) => {
          const sol = soluk(ds.kume, k), sec = k !== '' && !sol;
          ds.borderColor = sol ? saydam(ds.renk, 0.12) : ds.renk;
          ds.pointBackgroundColor = sol ? 'transparent' : ds.renk;
          ds.backgroundColor = saydam(ds.renk, sec ? 0.22 : sol ? 0 : 0.06);
          ds.borderWidth = sec ? 3 : 2;
        });
        ch.update();
      };
      return ch;
    },

    /* Kıvılcım: beğeni oranının karar sırasına göre seyri. */
    kivilcim(tuval, d) {
      return new Chart(tuval, {
        type: 'line',
        data: { labels: d.veri.map((_, i) => i + 1), datasets: [{ data: d.veri, borderColor: T.vurgu, borderWidth: 2,
          tension: 0.35, fill: true,
          backgroundColor: (c) => { const a = c.chart.chartArea; if (!a) return 'transparent';
            const g = c.chart.ctx.createLinearGradient(0, a.top, 0, a.bottom);
            g.addColorStop(0, saydam(T.vurgu, 0.25)); g.addColorStop(1, saydam(T.vurgu, 0)); return g; },
          pointRadius: (c) => (c.dataIndex === d.veri.length - 1 ? 3.5 : 0), pointBackgroundColor: T.vurgu }] },
        options: { scales: { x: { display: false }, y: { display: false, min: 0, max: 100 } },
          plugins: { tooltip: { callbacks: { title: (it) => `#${it[0].label}`, label: (it) => ` ${d.ad}: %${it.raw}` } } } },
      });
    },
  };

  const grafikler = [];
  document.querySelectorAll('canvas[data-kaynak]').forEach((tuval) => {
    const kaynak = document.getElementById(tuval.dataset.kaynak);
    if (!kaynak) return;
    let tanim;
    try { tanim = JSON.parse(kaynak.textContent); } catch (_) { return; }
    const ciz = cizerler[tanim.tur];
    if (ciz) grafikler.push(ciz(tuval, tanim));
  });
  const uygula = (k) => grafikler.forEach((g) => g.vurgula && g.vurgula(k));
  document.addEventListener('pano:secim', (o) => uygula(o.detail || ''));
  if (secili()) uygula(secili());
})();
