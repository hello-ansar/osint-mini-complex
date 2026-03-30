function safeText(v) {
  return v === null || v === undefined || v === '' ? '—' : String(v);
}

function escapeHtml(value) {
  if (value === null || value === undefined) return '—';
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function renderKV(obj) {
  return Object.entries(obj).map(([k, v]) => `
    <div class="kv">
      <div class="muted">${safeText(k)}</div>
      <div>${safeText(v && typeof v === 'object' ? JSON.stringify(v) : v)}</div>
    </div>
  `).join('');
}

function renderImageGenericMatches(items) {
  if (!items || !items.length) {
    return `<div class="muted">Совпадения не найдены.</div>`;
  }

  return items.map(item => `
    <div class="match-card">
      <div><strong>${safeText(item.title || item.platform || item.module)}</strong></div>
      <div class="meta">
        ${safeText(item.host || item.category)}
        ${item.similarity !== undefined ? ` · similarity ${item.similarity}%` : ''}
        ${item.confidence !== undefined ? ` · confidence ${item.confidence}%` : ''}
      </div>
      <div class="meta">${safeText(item.passage || item.evidence || item.status)}</div>
      ${item.page_url ? `<div class="meta"><a href="${escapeHtml(item.page_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.page_url)}</a></div>` : ''}
      ${item.profile_url ? `<div class="meta"><a href="${escapeHtml(item.profile_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.profile_url)}</a></div>` : ''}
    </div>
  `).join('');
}

function renderLocalMatches(items) {
  const box = document.getElementById('local-box');
  if (!box) return;

  if (!items || !items.length) {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">Локальная база пуста</div>
        <div class="muted">
          Для этого изображения локальные визуальные референсы отсутствуют.
        </div>
      </div>
    `;
    return;
  }

  box.innerHTML = items.map(item => `
    <div class="match-card">
      <div><strong>${escapeHtml(item.title || 'Без названия')}</strong></div>
      <div class="meta">
        ${escapeHtml(item.host || 'local')}
        ${item.similarity !== undefined ? ` · similarity ${item.similarity}%` : ''}
      </div>
      <div class="meta">${escapeHtml(item.passage || '')}</div>
      ${item.page_url ? `<div class="meta"><a href="${escapeHtml(item.page_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.page_url)}</a></div>` : ''}
    </div>
  `).join('');
}

function renderYandexMatches(bundle) {
  const box = document.getElementById('yandex-box');
  if (!box) return;

  const enabled = bundle?.enabled;
  const error = bundle?.error;
  const items = bundle?.results || [];

  if (error === 'disabled') {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">Yandex Search API отключён</div>
        <div class="muted">Включи поиск в .env, чтобы получать интернет-дубликаты.</div>
      </div>
    `;
    return;
  }

  if (error) {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">Yandex Search API недоступен</div>
        <div class="muted">Причина: ${escapeHtml(error)}</div>
        ${bundle?.endpoint ? `<div class="muted">Endpoint: ${escapeHtml(bundle.endpoint)}</div>` : ''}
        ${bundle?.debug ? `<div class="meta" style="margin-top:8px; white-space:pre-wrap;">${escapeHtml(bundle.debug)}</div>` : ''}
      </div>
    `;
    return;
  }

  if (!enabled && !items.length) {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">Интернет-поиск не активирован</div>
        <div class="muted">Внешние совпадения пока не запрашиваются.</div>
      </div>
    `;
    return;
  }

  if (!items.length) {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-title">Совпадения не найдены</div>
        <div class="muted">По текущему изображению интернет-дубликаты не найдены на первой странице выдачи.</div>
      </div>
    `;
    return;
  }

  box.innerHTML = `
    <div class="thumb-grid">
      ${items.slice(0, 10).map(item => `
        <a class="thumb-card" href="${escapeHtml(item.page_url || item.page || '#')}" target="_blank" rel="noopener noreferrer">
          <div class="thumb-image-wrap">
            <img class="thumb-image" src="${escapeHtml(item.url || '')}" alt="${escapeHtml(item.title || 'image')}">
          </div>
          <div class="thumb-title">${escapeHtml(item.title || 'Без названия')}</div>
          <div class="thumb-meta">${escapeHtml(item.host || '')}</div>
        </a>
      `).join('')}
    </div>
  `;
}

function renderImageResult(data) {
  const exif = data.exif || {};
  const hashes = data.hashes || {};
  const geo = data.location_assessment || {};
  const syn = data.synthetic_risk || {};
  const yandex = data.reverse_search?.yandex || {};
  const localMatches = data.reverse_search?.local_matches || [];
  const summary = data.analytical_conclusion || [];

  renderExifMap(data.map_data);

  const exifBox = document.getElementById('exif-box');
  const hashBox = document.getElementById('hash-box');
  const geoBox = document.getElementById('geo-box');
  const summaryBox = document.getElementById('image-summary');

  if (exifBox) {
    exifBox.innerHTML = renderKV({
      camera_make: exif.camera_make,
      camera_model: exif.camera_model,
      datetime_original: exif.datetime_original,
      gps: exif.gps ? `${exif.gps.lat}, ${exif.gps.lon}` : null
    });
  }

  if (hashBox) {
    hashBox.innerHTML = renderKV({
      phash: hashes.phash,
      dhash: hashes.dhash,
      ela_score: data.ela_score,
      synthetic_risk: `${safeText(syn.risk)} (${safeText(syn.score)}%)`
    });
  }

  if (geoBox) {
    geoBox.innerHTML = renderKV({
      method: geo.method,
      label: geo.label,
      confidence: geo.confidence
    });
  }

  renderYandexMatches(yandex);
  renderLocalMatches(localMatches);

  if (summaryBox) {
    summaryBox.innerHTML = summary.map(line => `<div class="summary-item">${safeText(line)}</div>`).join('');
  }
}


async function initEventDetection() {
  const statsEl = document.getElementById('event-stats');
  const listEl = document.getElementById('event-list');
  if (!statsEl || !listEl) return;

  const resp = await fetch('/api/event-detection');
  const data = await resp.json();
  const stats = data.stats || {};

  statsEl.innerHTML = `
    <div class="card stat"><div class="label">Всего событий</div><div class="value">${safeText(stats.total_events)}</div></div>
    <div class="card stat"><div class="label">Высокий приоритет</div><div class="value">${safeText(stats.high_severity)}</div></div>
    <div class="card stat"><div class="label">Источников</div><div class="value">${safeText(stats.sources)}</div></div>
    <div class="card stat"><div class="label">Средняя уверенность</div><div class="value">${safeText(stats.avg_confidence)}</div></div>
  `;

  listEl.innerHTML = (data.events || []).map(event => `
    <div class="event-card">
      <div class="event-head">
        <div>
          <h3>${safeText(event.title)}</h3>
          <div class="muted">${safeText(event.summary)}</div>
        </div>
        <div class="pill ${event.severity}">${safeText(event.severity)}</div>
      </div>
      <div class="event-meta">
        <div class="pill">${safeText(event.event_id)}</div>
        <div class="pill">${safeText(event.event_type)}</div>
        <div class="pill">${safeText(event.location)}</div>
        <div class="pill">публикаций: ${safeText(event.post_count)}</div>
        <div class="pill">источников: ${safeText(event.source_count)}</div>
        <div class="pill">уверенность: ${safeText(event.confidence)}</div>
      </div>
      <div class="muted">Последнее обновление: ${safeText(event.published_at)}</div>
    </div>
  `).join('');
}

async function initImageGeo() {
  const form = document.getElementById('image-form');
  const fileInput = document.getElementById('image-file');
  const preview = document.getElementById('image-preview');
  const wrap = document.getElementById('image-preview-wrap');

  if (!form || !fileInput) return;

  fileInput.addEventListener('change', () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    if (preview && wrap) {
      preview.src = URL.createObjectURL(file);
      wrap.classList.remove('hidden');
    }
  });

  form.onsubmit = async function (e) {
    e.preventDefault();

    const file = fileInput.files?.[0];
    if (!file) {
      alert('Выберите изображение');
      return false;
    }

    const fd = new FormData();
    fd.append('file', file);

    try {
      document.getElementById('image-summary').innerHTML = `<div class="summary-item">Выполняется анализ изображения...</div>`;

      const resp = await fetch('/api/image-geo/analyze', {
        method: 'POST',
        body: fd
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      renderImageResult(data);
    } catch (err) {
      document.getElementById('image-summary').innerHTML =
        `<div class="summary-item">Ошибка анализа: ${safeText(err.message)}</div>`;
      console.error(err);
    }

    return false;
  };
}

let geoMapInstance = null;

function renderExifMap(mapData) {
  const wrap = document.getElementById('geo-map-wrap');
  const empty = document.getElementById('geo-map-empty');
  const mapEl = document.getElementById('geo-map');

  if (!wrap || !empty || !mapEl) return;

  if (!mapData || mapData.lat === undefined || mapData.lon === undefined) {
    wrap.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }

  wrap.classList.remove('hidden');
  empty.classList.add('hidden');

  if (geoMapInstance) {
    geoMapInstance.remove();
    geoMapInstance = null;
  }

  geoMapInstance = L.map('geo-map').setView([mapData.lat, mapData.lon], mapData.zoom || 15);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(geoMapInstance);

  L.marker([mapData.lat, mapData.lon])
    .addTo(geoMapInstance)
    .bindPopup(mapData.popup || `${mapData.lat}, ${mapData.lon}`)
    .openPopup();

  setTimeout(() => {
    geoMapInstance.invalidateSize();
  }, 150);
}

// function renderImageResult(data) {
//   const exif = data.exif || {};
//   const hashes = data.hashes || {};
//   const geo = data.location_assessment || {};
//   const syn = data.synthetic_risk || {};
//   const yandex = data.reverse_search?.yandex || {};
//   const localMatches = data.reverse_search?.local_matches || [];
//   const summary = data.analytical_conclusion || [];

//   renderExifMap(data.map_data);

//   const exifBox = document.getElementById('exif-box');
//   const hashBox = document.getElementById('hash-box');
//   const geoBox = document.getElementById('geo-box');
//   const summaryBox = document.getElementById('image-summary');

//   if (exifBox) {
//     exifBox.innerHTML = renderKV({
//       camera_make: exif.camera_make,
//       camera_model: exif.camera_model,
//       datetime_original: exif.datetime_original,
//       gps: exif.gps ? `${exif.gps.lat}, ${exif.gps.lon}` : null
//     });
//   }

//   if (hashBox) {
//     hashBox.innerHTML = renderKV({
//       phash: hashes.phash,
//       dhash: hashes.dhash,
//       ela_score: data.ela_score,
//       synthetic_risk: `${safeText(syn.risk)} (${safeText(syn.score)}%)`
//     });
//   }

//   if (geoBox) {
//     geoBox.innerHTML = renderKV({
//       method: geo.method,
//       label: geo.label,
//       confidence: geo.confidence
//     });
//   }

//   renderYandexMatches(yandex);
//   renderLocalMatches(localMatches);

//   if (summaryBox) {
//     summaryBox.innerHTML = summary.map(line => `<div class="summary-item">${safeText(line)}</div>`).join('');
//   }
// }

function renderProfileRecords(items) {
  const filtered = (items || []).filter(item =>
    item.status === 'Found' || item.status === 'Registered'
  );

  if (!filtered.length) {
    return `<div class="muted">Совпадения не обнаружены.</div>`;
  }

  return filtered.map(item => `
    <div class="match-card">
      <div><strong>${escapeHtml(item.platform)}</strong></div>
      <div class="meta">
        ${escapeHtml(item.status)}
        ${item.category ? ` · ${escapeHtml(item.category)}` : ''}
        · confidence ${(Number(item.confidence || 0) * 100).toFixed(0)}%
      </div>
      ${
        item.url
          ? `<div class="meta"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.url)}</a></div>`
          : ''
      }
    </div>
  `).join('');
}

function renderProfileStats(summary) {
  const statsEl = document.getElementById('profile-stats');
  if (!statsEl) return;

  statsEl.innerHTML = `
    <div class="card stat">
      <div class="label">Всего проверок</div>
      <div class="value">${summary.total ?? 0}</div>
    </div>
    <div class="card stat">
      <div class="label">Позитивные совпадения</div>
      <div class="value">${summary.positive ?? 0}</div>
    </div>
    <div class="card stat">
      <div class="label">Отрицательные</div>
      <div class="value">${summary.negative ?? 0}</div>
    </div>
    <div class="card stat">
      <div class="label">Ошибки</div>
      <div class="value">${summary.errors ?? 0}</div>
    </div>
  `;
}

function startProfileLiveState() {
  const liveBox = document.getElementById('scan-live-box');
  const statusEl = document.getElementById('scan-live-status');
  const timerEl = document.getElementById('scan-live-timer');
  const stepsEl = document.getElementById('scan-live-steps');
  const progressEl = document.getElementById('scan-live-progress');
  const submitBtn = document.getElementById('scan-submit-btn');

  liveBox?.classList.remove('hidden');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Сканирование...';
  }

  const started = Date.now();
  let phase = 0;

  const phases = [
    { text: 'Инициализация OSINT-модуля...', progress: 10 },
    { text: 'Подготовка параметров поиска...', progress: 22 },
    { text: 'Запуск user-scanner...', progress: 35 },
    { text: 'Проверка доступности платформ...', progress: 52 },
    { text: 'Сбор результатов и нормализация...', progress: 73 },
    { text: 'Агрегация footprint-данных...', progress: 88 },
    { text: 'Формирование аналитической сводки...', progress: 96 }
  ];

  if (stepsEl) {
    stepsEl.innerHTML = '';
  }

  function addStep(text) {
    if (!stepsEl) return;
    stepsEl.innerHTML += `<div class="summary-item">${escapeHtml(text)}</div>`;
  }

  function tick() {
    const secs = ((Date.now() - started) / 1000).toFixed(1);
    if (timerEl) timerEl.textContent = `${secs} сек`;

    if (phase < phases.length) {
      const item = phases[phase];
      if (statusEl) statusEl.textContent = item.text;
      if (progressEl) progressEl.style.width = `${item.progress}%`;
      addStep(item.text);
      phase += 1;
    }
  }

  tick();
  const phaseInterval = setInterval(tick, 1400);

  return {
    finish(message = 'Сканирование завершено') {
      clearInterval(phaseInterval);
      const secs = ((Date.now() - started) / 1000).toFixed(1);
      if (timerEl) timerEl.textContent = `${secs} сек`;
      if (statusEl) statusEl.textContent = message;
      if (progressEl) progressEl.style.width = '100%';
      addStep(message);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Запустить разведку';
      }
    },
    fail(message = 'Ошибка выполнения сканирования') {
      clearInterval(phaseInterval);
      if (statusEl) statusEl.textContent = message;
      if (progressEl) progressEl.style.width = '100%';
      addStep(message);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Запустить разведку';
      }
    }
  };
}

function renderPlatforms(emailResults, usernameResults) {
  const el = document.getElementById('profile-platforms');
  if (!el) return;

  const merged = [...(emailResults || []), ...(usernameResults || [])]
    .filter(item => item.status === 'Found' || item.status === 'Registered');

  if (!merged.length) {
    el.innerHTML = `<div class="muted">Позитивные совпадения не выявлены.</div>`;
    return;
  }

  const grouped = {};
  for (const item of merged) {
    const key = item.platform || 'Unknown';
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(item);
  }

  el.innerHTML = Object.entries(grouped).map(([platform, items]) => {
    const first = items.find(x => x.url) || items[0];
    const cats = [...new Set(items.map(x => x.category || 'other'))].join(', ');
    return `
      <div class="match-card">
        <div><strong>${escapeHtml(platform)}</strong></div>
        <div class="meta">Категории: ${escapeHtml(cats)}</div>
        <div class="meta">Совпадений: ${items.length}</div>
        ${
          first?.url
            ? `<div class="meta"><a href="${escapeHtml(first.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(first.url)}</a></div>`
            : ''
        }
      </div>
    `;
  }).join('');
}

async function initDigitalProfile() {
  const form = document.getElementById('digital-profile-form');
  if (!form) return;

  form.onsubmit = async function (e) {
    e.preventDefault();

    const mode = document.getElementById('scan-mode')?.value || 'combined';
    const emailRaw = document.getElementById('scan-email')?.value?.trim() || '';
    const usernameRaw = document.getElementById('scan-username')?.value?.trim() || '';
    const category = document.getElementById('scan-category')?.value?.trim() || null;
    const module = document.getElementById('scan-module')?.value?.trim() || null;
    const proxyFile = document.getElementById('scan-proxy-file')?.value?.trim() || null;
    const validateProxies = !!document.getElementById('scan-validate-proxies')?.checked;

    const email = mode === 'username' ? null : (emailRaw || null);
    const username = mode === 'email' ? null : (usernameRaw || null);

    if (!email && !username) {
      alert('Укажи email, username, либо оба параметра.');
      return false;
    }

    const summaryEl = document.getElementById('profile-summary');
    const emailEl = document.getElementById('email-results');
    const userEl = document.getElementById('username-results');
    const platformsEl = document.getElementById('profile-platforms');

    summaryEl.innerHTML = `<div class="muted">Запуск анализа...</div>`;
    emailEl.innerHTML = '';
    userEl.innerHTML = '';
    platformsEl.innerHTML = '';

    const live = startProfileLiveState();

    try {
      const resp = await fetch('/api/digital-profile/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          username,
          category,
          module,
          proxy_file: proxyFile,
          validate_proxies: validateProxies
        })
      });

      const data = await resp.json();

      if (!resp.ok || data.ok === false) {
        summaryEl.innerHTML = `<div class="summary-item">Ошибка: ${escapeHtml(data.error || resp.status)}</div>`;
        live.fail('Сканирование завершилось с ошибкой');
        return false;
      }

      const summary = data.summary || {};
      renderProfileStats(summary);

      summaryEl.innerHTML = `
        <div class="summary-item">OSINT-скан выполнен успешно.</div>
        <div class="summary-item">Выявлено совпадений: ${summary.positive ?? 0}</div>
        ${(data.notes || []).map(n => `<div class="summary-item">${escapeHtml(n)}</div>`).join('')}
      `;

      emailEl.innerHTML = renderProfileRecords(data.email_results || []);
      userEl.innerHTML = renderProfileRecords(data.username_results || []);
      renderPlatforms(data.email_results || [], data.username_results || []);

      live.finish('Разведка завершена');
      console.log('digital-profile debug', data.debug);
    } catch (err) {
      summaryEl.innerHTML = `<div class="summary-item">Ошибка запроса: ${escapeHtml(err.message)}</div>`;
      live.fail('Ошибка запроса к серверу');
      console.error(err);
    }

    return false;
  };
}

document.addEventListener('DOMContentLoaded', () => {
  initDigitalProfile();
});

function renderSimpleList(items) {
  if (!items || !items.length) {
    return `<div class="muted">Данные не обнаружены.</div>`;
  }

  return items.map(item => {
    if (typeof item === 'object' && item !== null) {
      return `
        <div class="match-card">
          ${item.host ? `<div><strong>${escapeHtml(item.host)}</strong></div>` : ''}
          ${item.ip ? `<div class="meta">IP: ${escapeHtml(item.ip)}</div>` : ''}
          ${item.ssl_common_name ? `<div class="meta">CN: ${escapeHtml(item.ssl_common_name)}</div>` : ''}
          ${item.ssl_issuer ? `<div class="meta">Issuer: ${escapeHtml(item.ssl_issuer)}</div>` : ''}
          ${item.ssl_valid_from ? `<div class="meta">Valid from: ${escapeHtml(item.ssl_valid_from)}</div>` : ''}
          ${item.ssl_valid_to ? `<div class="meta">Valid to: ${escapeHtml(item.ssl_valid_to)}</div>` : ''}
        </div>
      `;
    }

    return `
      <div class="match-card">
        <div>${escapeHtml(item)}</div>
      </div>
    `;
  }).join('');
}

async function initInfrastructureIntel() {
  const form = document.getElementById('infra-form');
  if (!form) return;

  form.onsubmit = async function (e) {
    e.preventDefault();

    const domain = document.getElementById('infra-domain')?.value?.trim();
    if (!domain) {
      alert('Укажи домен.');
      return false;
    }

    const summaryEl = document.getElementById('infra-summary');
    const originEl = document.getElementById('infra-origin');
    const sslEl = document.getElementById('infra-ssl');
    const historyEl = document.getElementById('infra-history');
    const rawEl = document.getElementById('infra-raw');
    const btn = document.getElementById('infra-submit-btn');

    summaryEl.innerHTML = `<div class="summary-item">Выполняется инфраструктурный анализ...</div>`;
    originEl.innerHTML = '';
    sslEl.innerHTML = '';
    historyEl.innerHTML = '';
    rawEl.textContent = '';

    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Анализ...';
    }

    try {
      const resp = await fetch('/api/infrastructure-intel/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain })
      });

      const data = await resp.json();

      if (!resp.ok || data.ok === false) {
        summaryEl.innerHTML = `<div class="summary-item">Ошибка: ${escapeHtml(data.error || resp.status)}</div>`;
        return false;
      }

      summaryEl.innerHTML = (data.analytical_conclusion || []).map(
        line => `<div class="summary-item">${escapeHtml(line)}</div>`
      ).join('');

      originEl.innerHTML = renderSimpleList(data.origin_candidates || []);
      sslEl.innerHTML = renderSimpleList(data.ssl_signals || []);
      historyEl.innerHTML = renderSimpleList([
        ...(data.subdomain_signals || []),
        ...(data.history_signals || [])
      ]);

      summaryEl.innerHTML = `
        ${(data.analytical_conclusion || []).map(line => `<div class="summary-item">${escapeHtml(line)}</div>`).join('')}
        ${data.visible_ip ? `<div class="summary-item">Видимый IP: ${escapeHtml(data.visible_ip)}</div>` : ''}
      `;

      rawEl.textContent = data.stdout_preview || '';
    } catch (err) {
      summaryEl.innerHTML = `<div class="summary-item">Ошибка запроса: ${escapeHtml(err.message)}</div>`;
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Запустить анализ';
      }
    }

    return false;
  };
}