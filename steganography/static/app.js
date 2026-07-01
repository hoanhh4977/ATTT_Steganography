'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  embedFile: null,
  extractFile: null,
  analyzeFile: null,
  audioEmbedFile: null,
  audioExtractFile: null,
  bitplaneFile: null,
  compareCoverFile: null,
  compareStegoFile: null,
  stegoDataUrl: null,
  stegoAudioDataUrl: null,
};

// ── Tab switching ──────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ── Mode toggle ────────────────────────────────────────────────────────────
function setMode(tab, mode, btn) {
  document.getElementById(tab + '-mode').value = mode;
  btn.closest('.mode-toggle').querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ── Password toggle ────────────────────────────────────────────────────────
function togglePw(inputId, btn) {
  const input = document.getElementById(inputId);
  input.type = input.type === 'password' ? 'text' : 'password';
  btn.textContent = input.type === 'password' ? '👁' : '🙈';
}

// ── Image Drag & Drop ──────────────────────────────────────────────────────
function setupDrop(dropId, fileInputId, stateKey, previewHintId, onFile) {
  const zone = document.getElementById(dropId);
  const inp = document.getElementById(fileInputId);
  if (!zone || !inp) return;

  inp.addEventListener('change', () => {
    if (inp.files[0]) handleImageFile(inp.files[0], stateKey, zone, previewHintId, onFile);
  });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f) handleImageFile(f, stateKey, zone, previewHintId, onFile);
  });
}

function handleImageFile(file, stateKey, zone, hintId, onFile) {
  state[stateKey] = file;
  const hint = document.getElementById(hintId);
  const reader = new FileReader();
  reader.onload = ev => {
    if (hint) hint.style.display = 'none';
    let img = zone.querySelector('img.preview');
    if (!img) { img = document.createElement('img'); img.className = 'preview'; zone.appendChild(img); }
    img.src = ev.target.result;
    img.style.display = 'block';
    if (onFile) onFile(file, ev.target.result);
  };
  reader.readAsDataURL(file);
}

// ── Audio Drag & Drop ──────────────────────────────────────────────────────
function setupAudioDrop(dropId, fileInputId, stateKey, hintId, nameId) {
  const zone = document.getElementById(dropId);
  const inp = document.getElementById(fileInputId);
  if (!zone || !inp) return;

  const handle = (file) => {
    state[stateKey] = file;
    document.getElementById(hintId).style.display = 'none';
    const nameEl = document.getElementById(nameId);
    nameEl.textContent = `🎵 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    nameEl.style.display = 'block';
  };

  inp.addEventListener('change', () => { if (inp.files[0]) handle(inp.files[0]); });
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f) handle(f);
  });
}

// ── Initialize all drop zones ──────────────────────────────────────────────
setupDrop('embed-drop', 'embed-file', 'embedFile', 'embed-hint', null);
setupDrop('extract-drop', 'extract-file', 'extractFile', 'extract-hint', null);
setupDrop('analyze-drop', 'analyze-file', 'analyzeFile', 'analyze-hint', null);
setupAudioDrop('audio-embed-drop', 'audio-embed-file', 'audioEmbedFile', 'audio-embed-hint', 'audio-embed-name');
setupAudioDrop('audio-extract-drop', 'audio-extract-file', 'audioExtractFile', 'audio-extract-hint', 'audio-extract-name');
setupDrop('bitplane-drop', 'bitplane-file', 'bitplaneFile', 'bitplane-hint', renderBitPlanes);
setupDrop('compare-cover-drop', 'compare-cover-file', 'compareCoverFile', 'compare-cover-hint', null);
setupDrop('compare-stego-drop', 'compare-stego-file', 'compareStegoFile', 'compare-stego-hint', null);

// ── Loading state helpers ──────────────────────────────────────────────────
function setLoading(id, on) {
  const btn = document.getElementById('btn-' + id);
  const spin = document.getElementById('spin-' + id);
  const lbl = document.getElementById('lbl-' + id);
  if (!btn) return;
  btn.disabled = on;
  if (spin) spin.style.display = on ? 'block' : 'none';
  if (lbl) lbl.style.opacity = on ? '0.5' : '1';
}

function showResult(id, text, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'result-box' + (isError ? ' error' : '');
  el.style.display = 'block';
}

// ── IMAGE EMBED ────────────────────────────────────────────────────────────
async function doEmbed() {
  const file = state.embedFile;
  const message = document.getElementById('embed-message').value.trim();
  const password = document.getElementById('embed-password').value;
  const mode = document.getElementById('embed-mode').value;

  if (!file) return showResult('embed-result', 'Please upload a cover image.', true);
  if (!message) return showResult('embed-result', 'Please enter a message.', true);
  if (!password) return showResult('embed-result', 'Please enter a password.', true);

  setLoading('embed', true);
  document.getElementById('embed-result').style.display = 'none';

  const fd = new FormData();
  fd.append('image', file);
  fd.append('message', message);
  fd.append('password', password);
  fd.append('mode', mode);

  try {
    const res = await fetch('/api/embed', { method: 'POST', body: fd });
    const data = await res.json();
    if (!data.success) { showResult('embed-result', '✗ ' + data.error, true); return; }

    state.stegoDataUrl = data.stego_image;
    const outputZone = document.getElementById('embed-output-preview');
    document.getElementById('embed-output-hint').style.display = 'none';
    let img = outputZone.querySelector('img.preview');
    if (!img) { img = document.createElement('img'); img.className = 'preview'; outputZone.appendChild(img); }
    img.src = data.stego_image;

    const psnrPct = Math.min(100, ((data.psnr - 30) / 30) * 100);
    document.getElementById('psnr-fill').style.width = psnrPct + '%';
    document.getElementById('psnr-val').textContent = data.psnr.toFixed(1) + ' dB';
    document.getElementById('cap-fill').style.width = Math.min(100, data.capacity_used_pct * 5) + '%';
    document.getElementById('cap-val').textContent = data.capacity_used_pct.toFixed(3) + '%';
    document.getElementById('embed-metrics').style.display = 'flex';
    document.getElementById('btn-download').style.display = 'inline-flex';

    showResult('embed-result', `✓ Embedded ${data.message_bytes} bytes | PSNR ${data.psnr} dB | imperceptible`);
  } catch (err) {
    showResult('embed-result', '✗ Network error: ' + err.message, true);
  } finally {
    setLoading('embed', false);
  }
}

function downloadStego() {
  if (!state.stegoDataUrl) return;
  const a = document.createElement('a');
  a.href = state.stegoDataUrl;
  a.download = 'stego_output.png';
  a.click();
}

// ── IMAGE EXTRACT ──────────────────────────────────────────────────────────
async function doExtract() {
  const file = state.extractFile;
  const password = document.getElementById('extract-password').value;
  const mode = document.getElementById('extract-mode').value;

  if (!file) return showResult('extract-result', 'Please upload a stego image.', true);
  if (!password) return showResult('extract-result', 'Please enter a password.', true);

  setLoading('extract', true);
  document.getElementById('extract-result').style.display = 'none';

  const fd = new FormData();
  fd.append('image', file);
  fd.append('password', password);
  fd.append('mode', mode);

  try {
    const res = await fetch('/api/extract', { method: 'POST', body: fd });
    const data = await res.json();
    if (!data.success) showResult('extract-result', '✗ ' + data.error, true);
    else showResult('extract-result', '✓ Message:\n\n' + data.message);
  } catch (err) {
    showResult('extract-result', '✗ Network error: ' + err.message, true);
  } finally {
    setLoading('extract', false);
  }
}

// ── ANALYZE ────────────────────────────────────────────────────────────────
async function doAnalyze() {
  const file = state.analyzeFile;
  const threshold = parseFloat(document.getElementById('analyze-threshold').value) || 0.15;

  if (!file) return showResult('analyze-error', 'Please upload an image.', true);

  setLoading('analyze', true);
  document.getElementById('analyze-error').style.display = 'none';
  document.getElementById('analyze-result').style.display = 'none';
  document.getElementById('chart-wrap').style.display = 'none';

  const fd = new FormData();
  fd.append('image', file);
  fd.append('threshold', threshold);

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: fd });
    const data = await res.json();
    if (!data.success) { showResult('analyze-error', '✗ ' + data.error, true); return; }

    const rsRate = data.rs_rate >= 0 ? data.rs_rate : 0;
    document.getElementById('rs-num').textContent = (rsRate * 100).toFixed(1) + '%';
    document.getElementById('rs-fill').style.width = Math.min(100, rsRate * 100) + '%';
    document.getElementById('rs-val').textContent = (rsRate * 100).toFixed(1) + '%';

    const spaRate = data.spa_rate >= 0 ? data.spa_rate : 0;
    document.getElementById('spa-fill').style.width = Math.min(100, spaRate * 100) + '%';
    document.getElementById('spa-val').textContent = (spaRate * 100).toFixed(1) + '%';

    const chi2Max = Math.max(data.chi2_score, 500);
    document.getElementById('chi2-fill').style.width = Math.min(100, (data.chi2_score / chi2Max) * 100) + '%';
    document.getElementById('chi2-val').textContent = data.chi2_score.toFixed(0);

    const badge = document.getElementById('verdict-badge');
    badge.textContent = data.verdict;
    badge.className = 'verdict ' + data.verdict.toLowerCase();
    document.getElementById('analyze-result').style.display = 'block';

    if (data.chart) {
      document.getElementById('chart-img').src = data.chart;
      document.getElementById('chart-wrap').style.display = 'block';
    }
  } catch (err) {
    showResult('analyze-error', '✗ Network error: ' + err.message, true);
  } finally {
    setLoading('analyze', false);
  }
}

// ── AUDIO EMBED ────────────────────────────────────────────────────────────
async function doAudioEmbed() {
  const file = state.audioEmbedFile;
  const message = document.getElementById('audio-embed-message').value.trim();
  const password = document.getElementById('audio-embed-password').value;
  const mode = document.getElementById('audio-embed-mode').value;

  if (!file) return showResult('audio-embed-result', 'Please upload a WAV file.', true);
  if (!message) return showResult('audio-embed-result', 'Please enter a message.', true);
  if (!password) return showResult('audio-embed-result', 'Please enter a password.', true);

  setLoading('audio-embed', true);
  document.getElementById('audio-embed-result').style.display = 'none';
  document.getElementById('audio-embed-output').style.display = 'none';

  const fd = new FormData();
  fd.append('audio', file);
  fd.append('message', message);
  fd.append('password', password);
  fd.append('mode', mode);

  try {
    const res = await fetch('/api/audio/embed', { method: 'POST', body: fd });
    const data = await res.json();

    if (!data.success) { showResult('audio-embed-result', '✗ ' + data.error, true); return; }

    state.stegoAudioDataUrl = data.stego_audio;
    document.getElementById('audio-embed-player').src = data.stego_audio;
    document.getElementById('audio-embed-output').style.display = 'block';

    showResult('audio-embed-result',
      `✓ Embedded ${data.message_bytes} bytes | Capacity used: ${data.capacity_used_pct.toFixed(3)}%\n` +
      `Sample rate: ${data.sample_rate} Hz | Samples: ${data.num_samples.toLocaleString()}`
    );
  } catch (err) {
    showResult('audio-embed-result', '✗ Network error: ' + err.message, true);
  } finally {
    setLoading('audio-embed', false);
  }
}

function downloadStegoAudio() {
  if (!state.stegoAudioDataUrl) return;
  const a = document.createElement('a');
  a.href = state.stegoAudioDataUrl;
  a.download = 'stego_audio.wav';
  a.click();
}

// ── AUDIO EXTRACT ──────────────────────────────────────────────────────────
async function doAudioExtract() {
  const file = state.audioExtractFile;
  const password = document.getElementById('audio-extract-password').value;
  const mode = document.getElementById('audio-extract-mode').value;

  if (!file) return showResult('audio-extract-result', 'Please upload a stego WAV file.', true);
  if (!password) return showResult('audio-extract-result', 'Please enter a password.', true);

  setLoading('audio-extract', true);
  document.getElementById('audio-extract-result').style.display = 'none';

  const fd = new FormData();
  fd.append('audio', file);
  fd.append('password', password);
  fd.append('mode', mode);

  try {
    const res = await fetch('/api/audio/extract', { method: 'POST', body: fd });
    const data = await res.json();
    if (!data.success) showResult('audio-extract-result', '✗ ' + data.error, true);
    else showResult('audio-extract-result', '✓ Message:\n\n' + data.message);
  } catch (err) {
    showResult('audio-extract-result', '✗ Network error: ' + err.message, true);
  } finally {
    setLoading('audio-extract', false);
  }
}

// ── BIT-PLANE VIEWER ───────────────────────────────────────────────────────
function renderBitPlanes(file, dataUrl) {
  const img = new Image();
  img.onload = () => {
    const MAX_W = 600;
    const scale = img.width > MAX_W ? MAX_W / img.width : 1;
    const w = Math.round(img.width * scale);
    const h = Math.round(img.height * scale);

    // Offscreen canvas to read pixel data
    const src = document.createElement('canvas');
    src.width = w; src.height = h;
    const sCtx = src.getContext('2d');
    sCtx.drawImage(img, 0, 0, w, h);
    const srcData = sCtx.getImageData(0, 0, w, h).data;

    const grid = document.querySelector('#bitplane-grid > div');
    grid.innerHTML = '';

    // Render bit 7 down to bit 0
    for (let bit = 7; bit >= 0; bit--) {
      const wrapper = document.createElement('div');
      wrapper.style.textAlign = 'center';

      const label = document.createElement('p');
      const isLSB = bit === 0;
      const isMSB = bit === 7;
      label.style.cssText = `font-size:0.78rem;margin-bottom:4px;color:${isLSB ? '#5EEAD4' : isMSB ? '#00D4FF' : '#64748B'}`;
      label.textContent = `Bit ${bit}${isMSB ? ' (MSB)' : isLSB ? ' (LSB)' : ''}`;

      const canvas = document.createElement('canvas');
      canvas.width = w; canvas.height = h;
      canvas.style.cssText = 'width:100%;border-radius:4px;background:#0F172A';
      const ctx = canvas.getContext('2d');
      const planeData = ctx.createImageData(w, h);

      for (let i = 0; i < srcData.length; i += 4) {
        // Use average of R, G, B channels for the bit value
        const r = (srcData[i] >> bit) & 1;
        const g = (srcData[i+1] >> bit) & 1;
        const b = (srcData[i+2] >> bit) & 1;
        // majority vote or just average for grayscale display
        const v = Math.round(((r + g + b) / 3)) * 255;
        planeData.data[i]   = v;
        planeData.data[i+1] = v;
        planeData.data[i+2] = v;
        planeData.data[i+3] = 255;
      }
      ctx.putImageData(planeData, 0, 0);

      wrapper.appendChild(label);
      wrapper.appendChild(canvas);
      grid.appendChild(wrapper);
    }

    document.getElementById('bitplane-hint').style.display = 'none';
    document.getElementById('bitplane-grid').style.display = 'block';
  };
  img.src = dataUrl;
}

// ── IMAGE COMPARE ──────────────────────────────────────────────────────────
function doCompare() {
  const coverFile = state.compareCoverFile;
  const stegoFile = state.compareStegoFile;
  if (!coverFile || !stegoFile) return alert('Please upload both cover and stego images.');

  const loadImage = (file) => new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = ev => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  });

  Promise.all([loadImage(coverFile), loadImage(stegoFile)]).then(([coverImg, stegoImg]) => {
    const w = coverImg.width;
    const h = coverImg.height;

    // If sizes differ, abort
    if (w !== stegoImg.width || h !== stegoImg.height) {
      return alert('Images must be the same size.');
    }

    // Draw both to offscreen canvases and get pixel data
    const getPixels = (img) => {
      const c = document.createElement('canvas');
      c.width = w; c.height = h;
      c.getContext('2d').drawImage(img, 0, 0);
      return c.getContext('2d').getImageData(0, 0, w, h).data;
    };

    const coverPx = getPixels(coverImg);
    const stegoPx = getPixels(stegoImg);

    // Compute MSE and max diff (RGB channels only)
    let mse = 0, maxDiff = 0, count = 0;
    const diffArr = new Uint8ClampedArray(coverPx.length);
    for (let i = 0; i < coverPx.length; i += 4) {
      for (let c = 0; c < 3; c++) {
        const d = Math.abs(coverPx[i+c] - stegoPx[i+c]);
        mse += d * d;
        maxDiff = Math.max(maxDiff, d);
        diffArr[i+c] = Math.min(255, d * 64);
        count++;
      }
      diffArr[i+3] = 255;
    }
    mse /= count;
    const psnr = mse === 0 ? Infinity : 20 * Math.log10(255) - 10 * Math.log10(mse);

    // Update badge values
    document.getElementById('cmp-psnr').textContent = isFinite(psnr) ? psnr.toFixed(2) + ' dB' : '∞';
    document.getElementById('cmp-mse').textContent = mse.toFixed(4);
    document.getElementById('cmp-maxdiff').textContent = maxDiff;

    // Draw canvases (scaled down for display)
    const MAX_W = 400;
    const displayScale = w > MAX_W ? MAX_W / w : 1;
    const dw = Math.round(w * displayScale);
    const dh = Math.round(h * displayScale);

    const drawTo = (canvasId, img) => {
      const canvas = document.getElementById(canvasId);
      canvas.width = dw; canvas.height = dh;
      canvas.getContext('2d').drawImage(img, 0, 0, dw, dh);
    };

    drawTo('cmp-canvas-cover', coverImg);
    drawTo('cmp-canvas-stego', stegoImg);

    // Draw diff
    const diffCanvas = document.getElementById('cmp-canvas-diff');
    diffCanvas.width = dw; diffCanvas.height = dh;
    const dCtx = diffCanvas.getContext('2d');
    const diffFull = document.createElement('canvas');
    diffFull.width = w; diffFull.height = h;
    const dfCtx = diffFull.getContext('2d');
    const diffImageData = dfCtx.createImageData(w, h);
    diffImageData.data.set(diffArr);
    dfCtx.putImageData(diffImageData, 0, 0);
    dCtx.drawImage(diffFull, 0, 0, dw, dh);

    document.getElementById('compare-result').style.display = 'block';
  });
}
