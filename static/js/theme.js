/* static/js/theme.js
   Tema claro/escuro com:
   - Persistência (localStorage)
   - Respeito à preferência do sistema quando o usuário não escolheu
   - Crossfade suave entre temas usando overlay (respeita reduced-motion)
   - Suporte a múltiplos botões: #themeToggle e [data-theme-toggle]
   - Atualização de ícones dentro do botão (data-icon-light / data-icon-dark)
   - Repaint de calendários abertos (flatpickr) ao trocar o tema
   - Sincronização entre abas (evento storage)
   - API global: window.AgroTheme.toggle(), .apply(theme), .toast(...)
*/

(function () {
  const root = document.documentElement;

  // Botões de toggle: mantém compatibilidade com #themeToggle e adiciona [data-theme-toggle]
  function getToggleButtons() {
    const unique = new Set();
    const arr = [];
    const idBtn = document.getElementById('themeToggle');
    if (idBtn && !unique.has(idBtn)) { unique.add(idBtn); arr.push(idBtn); }
    document.querySelectorAll('[data-theme-toggle]').forEach((el) => {
      if (!unique.has(el)) { unique.add(el); arr.push(el); }
    });
    return arr;
  }

  // Overlay: usa #themeOverlay se existir ou cria um
  function ensureOverlay() {
    let overlay = document.getElementById('themeOverlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'themeOverlay';
      overlay.className = 'theme-overlay';
      document.body.appendChild(overlay);
    }
    return overlay;
  }

  // Storage helpers (compat: 'theme' e 'agrodocs.theme')
  const STORAGE_KEYS = ['agrodocs.theme', 'theme'];
  function getStoredTheme() {
    try {
      for (const k of STORAGE_KEYS) {
        const v = localStorage.getItem(k);
        if (v === 'light' || v === 'dark') return v;
      }
    } catch {}
    return null;
  }
  function setStoredTheme(theme) {
    try {
      STORAGE_KEYS.forEach((k) => localStorage.setItem(k, theme));
    } catch {}
  }

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored === 'light' || stored === 'dark') return stored;
    return systemPrefersDark() ? 'dark' : 'light';
  }

  function repaintFlatpickr() {
    document.querySelectorAll('.flatpickr-calendar.open').forEach(function (cal) {
      cal.style.display = 'none'; cal.offsetHeight; cal.style.display = '';
    });
  }

  function updateToggleButtonUI(btn, theme) {
    if (!btn) return;
    // Acessibilidade
    btn.setAttribute('aria-pressed', String(theme === 'dark'));
    btn.setAttribute('aria-label', theme === 'dark' ? 'Alternar para tema claro' : 'Alternar para tema escuro');
    btn.title = theme === 'dark' ? 'Tema: escuro' : 'Tema: claro';

    // Ícones: <span data-icon-light> / <span data-icon-dark>
    const lightIcon = btn.querySelector('[data-icon-light]');
    const darkIcon = btn.querySelector('[data-icon-dark]');
    if (lightIcon) lightIcon.style.display = (theme === 'dark') ? 'none' : 'inline-block';
    if (darkIcon) darkIcon.style.display = (theme === 'dark') ? 'inline-block' : 'none';
  }

  function updateAllToggles(theme) {
    getToggleButtons().forEach((b) => updateToggleButtonUI(b, theme));
  }

  function applyTheme(theme, { persist = true, silent = false } = {}) {
    const t = (theme === 'dark') ? 'dark' : 'light';
    root.setAttribute('data-bs-theme', t);
    if (persist) setStoredTheme(t);
    updateAllToggles(t);
    repaintFlatpickr();

    if (!silent) {
      // Evento custom para componentes interessados
      const ev = new CustomEvent('agrodocs:theme-change', { detail: { theme: t } });
      document.dispatchEvent(ev);
    }
  }

  function crossfadeTo(nextTheme) {
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const overlay = ensureOverlay();
    if (!overlay || reduce) { applyTheme(nextTheme); return; }

    // Passo 1: mostra overlay (bg atual)
    overlay.classList.add('show');
    // Passo 2: após breve fade-in, troca o tema e retira overlay
    window.setTimeout(function () {
      applyTheme(nextTheme);
      window.requestAnimationFrame(function () {
        overlay.classList.remove('show');
      });
    }, 140);
  }

  function toggleTheme() {
    const current = root.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
    crossfadeTo(current === 'dark' ? 'light' : 'dark');
  }

  // Toasts simples (compatível com theme.css .toast-container)
  const Toast = (function () {
    function ensureContainer() {
      let el = document.querySelector('.toast-container');
      if (!el) {
        el = document.createElement('div');
        el.className = 'toast-container';
        document.body.appendChild(el);
      }
      return el;
    }
    function show({ title = '', message = '', type = 'info', timeout = 3500 } = {}) {
      const container = ensureContainer();
      const el = document.createElement('div');
      el.className = `toast ${type}`;
      el.innerHTML = `
        <div class="title">${title || (type === 'success' ? 'Sucesso' : type === 'error' ? 'Erro' : 'Aviso')}</div>
        <div class="msg">${message}</div>
      `;
      container.appendChild(el);
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-6px)';
        setTimeout(() => el.remove(), 220);
      }, timeout);
    }
    return { show };
  })();

  // Inicializa tema atual
  applyTheme(getPreferredTheme(), { persist: false, silent: true });
  updateAllToggles(root.getAttribute('data-bs-theme') || 'light');

  // Observa preferência do sistema se usuário não escolheu manualmente
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    // Se não há escolha persistida, seguir sistema
    mq.addEventListener('change', (e) => {
      if (!getStoredTheme()) applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  // Clique/teclado nos botões
  getToggleButtons().forEach((btn) => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      toggleTheme();
    });
    // Acessibilidade via teclado
    btn.setAttribute('role', 'button');
    btn.tabIndex = btn.tabIndex || 0;
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTheme(); }
    });
  });

  // Sincronizar entre abas
  window.addEventListener('storage', function (e) {
    if (!STORAGE_KEYS.includes(e.key)) return;
    const v = e.newValue;
    if (v === 'light' || v === 'dark') {
      applyTheme(v, { persist: false });
    }
  });

  // API pública
  window.AgroTheme = {
    toggle: toggleTheme,
    apply: (t) => applyTheme(t),
    toast: (opts) => Toast.show(opts),
    get: () => (root.getAttribute('data-bs-theme') || getPreferredTheme()),
    setStored: setStoredTheme
  };
})();