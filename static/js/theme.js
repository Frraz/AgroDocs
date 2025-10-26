(function () {
  const root = document.documentElement;
  const btn = document.getElementById('themeToggle');
  const overlay = document.getElementById('themeOverlay');

  function getStoredTheme() {
    try { return localStorage.getItem('theme'); } catch { return null; }
  }
  function setStoredTheme(theme) {
    try { localStorage.setItem('theme', theme); } catch {}
  }
  function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function applyTheme(theme) {
    root.setAttribute('data-bs-theme', theme);
    setStoredTheme(theme);
    updateToggleIcon(theme);
    // Força repaint em calendários abertos (flatpickr)
    document.querySelectorAll('.flatpickr-calendar.open').forEach(function (cal) {
      cal.style.display = 'none'; cal.offsetHeight; cal.style.display = '';
    });
  }
  function updateToggleIcon(theme) {
    if (!btn) return;
    if (theme === 'dark') {
      btn.setAttribute('aria-label', 'Alternar para tema claro');
      btn.title = 'Tema: escuro';
    } else {
      btn.setAttribute('aria-label', 'Alternar para tema escuro');
      btn.title = 'Tema: claro';
    }
  }

  // Inicializa tema
  applyTheme(getPreferredTheme());

  // Observa preferência do sistema se usuário não escolheu
  if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', e => {
      if (!getStoredTheme()) applyTheme(e.matches ? 'dark' : 'light');
    });
  }

  // Crossfade entre temas
  function crossfadeTo(nextTheme) {
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!overlay || reduce) {
      applyTheme(nextTheme);
      return;
    }
    // Passo 1: pinta o overlay com o BG atual e mostra
    overlay.classList.add('show');
    // Passo 2: após breve fade-in, troca o tema e esmaece
    window.setTimeout(function () {
      applyTheme(nextTheme);
      // aguarda o repaint do CSS e tira o overlay
      window.requestAnimationFrame(function () {
        overlay.classList.remove('show');
      });
    }, 140); // tempo curto para o olho perceber o crossfade
  }

  // Toggle no clique
  if (btn) {
    btn.addEventListener('click', function () {
      const current = root.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
      crossfadeTo(current === 'dark' ? 'light' : 'dark');
    });
  }
})();