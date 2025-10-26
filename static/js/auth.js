// static/js/auth.js
// Regras: mínimo obrigatório 8 caracteres. Maiúscula, minúscula, número e especial são recomendações.
// Mantém: alternar senha, Caps Lock, barra de força, confirmação, loading no submit.

(function () {
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  // Alternar visibilidade da senha
  $all('[data-toggle-password]').forEach(function (btn) {
    const inputId = btn.getAttribute('data-toggle-password');
    const input = document.getElementById(inputId);
    if (!input) return;
    btn.addEventListener('click', function () {
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      const icon = btn.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-eye', showing);
        icon.classList.toggle('bi-eye-slash', !showing);
      }
      input.focus();
    });
  });

  // Caps Lock (quando existir o aviso)
  $all('input[type="password"]').forEach(function (pwd) {
    const caps = document.querySelector('[data-capslock="' + pwd.id + '"]');
    if (!caps) return;
    function update(e) {
      const on = e.getModifierState && e.getModifierState('CapsLock');
      caps.classList.toggle('d-none', !on);
    }
    pwd.addEventListener('keydown', update);
    pwd.addEventListener('keyup', update);
    pwd.addEventListener('blur', function(){ caps.classList.add('d-none'); });
  });

  // Força de senha (cadastro)
  (function initStrength() {
    const p1 = document.getElementById('id_password1') || document.getElementById('id_new_password1');
    if (!p1) return;
    const bar = $('[data-pwd-strength]');
    const text = $('[data-pwd-strength-text]');
    const reqList = $('[data-pwd-req]');
    const reqItems = reqList ? {
      length: reqList.querySelector('[data-req="length"]'),
      lower: reqList.querySelector('[data-req="lower"]'),
      upper: reqList.querySelector('[data-req="upper"]'),
      digit: reqList.querySelector('[data-req="digit"]'),
      special: reqList.querySelector('[data-req="special"]'),
    } : {};

    const form = p1.closest('form');
    const submitBtn = form ? form.querySelector('[data-submit]') : null;

    function rules(v) {
      return {
        length: v.length >= 8,                 // único obrigatório
        lower: /[a-z]/.test(v),
        upper: /[A-Z]/.test(v),
        digit: /\d/.test(v),
        special: /[^A-Za-z0-9]/.test(v),
      };
    }

    function varietyCount(r) {
      return [r.lower, r.upper, r.digit, r.special].filter(Boolean).length;
    }

    function computeScore(v, r) {
      if (!v) return 0;
      const len = v.length;
      // Base pelo tamanho
      let s = Math.min(60, len * 5); // até 60
      // Bônus por variedade (opcional)
      s += varietyCount(r) * 10;     // até +40
      // Penalizar muito curta (<8)
      if (!r.length) s = Math.min(s, 35);
      return Math.max(0, Math.min(100, s));
    }

    function label(score, r){
      if (!p1.value) return 'Digite uma senha';
      if (!r.length) return 'Muito curta (mín. 8)';
      if (score < 50) return 'Ok';
      if (score < 75) return 'Boa';
      if (score < 90) return 'Forte';
      return 'Excelente';
    }

    function color(score, r){
      if (!r.length) return 'bg-danger';
      if (score < 50) return 'bg-warning';
      if (score < 75) return 'bg-info';
      return 'bg-success';
    }

    function updateReqUI(r) {
      if (!reqList) return;
      // O item "length" é obrigatório — fica verde quando >=8
      Object.entries(reqItems).forEach(([key, el]) => {
        if (!el) return;
        const ok = r[key];
        el.classList.toggle('text-success', ok);
        el.classList.toggle('text-muted', !ok);
        const icon = el.querySelector('i');
        if (icon) {
          icon.classList.toggle('bi-check-circle', ok);
          icon.classList.toggle('bi-x-circle', !ok);
        }
      });
    }

    function update() {
      const val = p1.value || '';
      const r = rules(val);
      const s = computeScore(val, r);

      if (bar) {
        bar.style.width = s + '%';
        bar.className = 'progress-bar ' + color(s, r);
        bar.setAttribute('aria-valuenow', String(s));
      }
      if (text) text.textContent = 'Força da senha: ' + label(s, r);

      updateReqUI(r);

      // Único bloqueio de UX: mínimo de 8 caracteres
      if (submitBtn) {
        submitBtn.toggleAttribute('disabled', !r.length);
      }

      matchCheck(); // atualiza coerência com p2
    }

    p1.addEventListener('input', update);
    update();

    // Confirmação de senha
    const p2 = document.getElementById('id_password2') || document.getElementById('id_new_password2');
    const matchEl = $('[data-pwd-match]');
    function matchCheck() {
      if (!p2 || !matchEl) return;
      const ok = !!p1.value && p1.value === p2.value;
      matchEl.classList.toggle('d-none', !ok);
    }
    if (p2) {
      p2.addEventListener('input', matchCheck);
      matchCheck();
    }
  })();

  // Loading no submit e foco no primeiro campo
  $all('form.auth-form').forEach(function (form) {
    const btn = form.querySelector('[data-submit]');
    if (btn) {
      form.addEventListener('submit', function () {
        const spinner = btn.querySelector('.spinner-border');
        const label = btn.querySelector('.label');
        btn.setAttribute('disabled', 'disabled');
        if (spinner) spinner.classList.remove('d-none');
        if (label) label.textContent = 'Enviando...';
      });
    }
    const first = form.querySelector('input:not([type=hidden]):not([disabled])');
    if (first && !first.value) first.focus({ preventScroll: true });
  });
})();