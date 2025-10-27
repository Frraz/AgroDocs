// static/js/auth.js
// Regras: mínimo obrigatório 8 caracteres. Maiúscula, minúscula, número e especial são recomendações.
// Mantém: alternar senha, Caps Lock, barra de força, confirmação, loading no submit.
// Melhorias:
// - Execução somente após DOMContentLoaded (evita listeners perdidos).
// - Acessibilidade: aria-pressed/aria-label no toggle de senha e aria-live para feedback.
// - Suporte opcional a modo "segurar" no toggle (data-toggle-password-mode="hold").
// - Barra de força mais informativa (penaliza padrões óbvios) e estados visuais.
// - Bloqueio de submit se confirmação não bater (quando houver p2).
// - Previne double-submit de forma segura.

(function () {
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function onReady(cb) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", cb, { once: true });
    } else {
      cb();
    }
  }

  onReady(function initAuthUI() {
    // -----------------------------
    // Alternar visibilidade da senha
    // -----------------------------
    $all('[data-toggle-password]').forEach(function (btn) {
      const inputId = btn.getAttribute('data-toggle-password');
      const input = document.getElementById(inputId);
      if (!input) return;

      const mode = btn.getAttribute('data-toggle-password-mode') || 'toggle'; // 'toggle' | 'hold'

      function setVisible(visible) {
        const wasText = input.type === 'text';
        input.type = visible ? 'text' : 'password';
        const nowVisible = input.type === 'text';
        const icon = btn.querySelector('i');
        if (icon) {
          icon.classList.toggle('bi-eye', !nowVisible);
          icon.classList.toggle('bi-eye-slash', nowVisible);
        }
        btn.setAttribute('aria-pressed', String(nowVisible));
        btn.setAttribute('aria-label', nowVisible ? 'Ocultar senha' : 'Mostrar senha');
        if (!wasText && nowVisible) input.focus();
      }

      if (mode === 'hold') {
        // Pressione e segure para mostrar
        btn.addEventListener('mousedown', function () { setVisible(true); });
        btn.addEventListener('mouseup', function () { setVisible(false); });
        btn.addEventListener('mouseleave', function () { setVisible(false); });
        btn.addEventListener('touchstart', function (e) { e.preventDefault(); setVisible(true); }, { passive: false });
        btn.addEventListener('touchend', function () { setVisible(false); });
      } else {
        // Alterna a cada clique
        btn.addEventListener('click', function () {
          const showing = input.type === 'text';
          setVisible(!showing);
        });
      }

      // Estado inicial de acessibilidade
      btn.setAttribute('role', 'button');
      btn.setAttribute('aria-pressed', String(input.type === 'text'));
      btn.setAttribute('aria-label', input.type === 'text' ? 'Ocultar senha' : 'Mostrar senha');
    });

    // -----------------------------
    // Caps Lock (quando existir o aviso)
    // -----------------------------
    $all('input[type="password"], input[data-password="true"]').forEach(function (pwd) {
      const caps = document.querySelector('[data-capslock="' + pwd.id + '"]');
      if (!caps) return;

      function update(e) {
        // Se o campo está como text (visível), esconder aviso
        if (pwd.type === 'text') { caps.classList.add('d-none'); return; }
        const on = e.getModifierState && e.getModifierState('CapsLock');
        caps.classList.toggle('d-none', !on);
      }
      pwd.addEventListener('keydown', update);
      pwd.addEventListener('keyup', update);
      pwd.addEventListener('focus', function (e) { update(e); });
      pwd.addEventListener('blur', function(){ caps.classList.add('d-none'); });
    });

    // -----------------------------
    // Força de senha (cadastro e alteração)
    // -----------------------------
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

      // Região aria-live para anunciar mudanças (acessibilidade)
      let live = $('[data-live="pwd"]');
      if (!live) {
        live = document.createElement('div');
        live.setAttribute('aria-live', 'polite');
        live.setAttribute('class', 'visually-hidden');
        live.setAttribute('data-live', 'pwd');
        document.body.appendChild(live);
      }
      function announce(msg){ if (live) live.textContent = msg; }

      const form = p1.closest('form');
      const submitBtn = form ? form.querySelector('[data-submit]') : null;

      // Regras
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
      function hasSequence(v) {
        // Detecta sequências simples (1234, abcd) ou repetição
        const seqs = ['0123456789','9876543210','abcdefghijklmnopqrstuvwxyz','zyxwvutsrqponmlkjihgfedcba','qwerty','asdfgh','password','senha'];
        const s = v.toLowerCase();
        if (/^(.)\1{3,}$/.test(s)) return true; // muitos repetidos
        return seqs.some(q => s.includes(q.substring(0,4)) && q.split('').some((_,i)=> s.includes(q.slice(i,i+4))));
      }
      function computeScore(v, r) {
        if (!v) return 0;
        const len = v.length;
        // Base pelo tamanho (um pouco mais agressivo para recompensar >12)
        let s = Math.min(60, len * 5); // até 60
        if (len >= 12) s += 5;
        // Bônus por variedade (opcional)
        s += varietyCount(r) * 10;     // até +40
        // Penalizar muito curta (<8)
        if (!r.length) s = Math.min(s, 35);
        // Penalizar padrões óbvios
        if (hasSequence(v)) s -= 15;
        // Clamp
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
        Object.entries(reqItems).forEach(([key, el]) => {
          if (!el) return;
          const ok = r[key];
          el.classList.toggle('text-success', ok);
          el.classList.toggle('text-muted', !ok);
          el.setAttribute('data-valid', ok ? '1' : '0');
          const icon = el.querySelector('i');
          if (icon) {
            icon.classList.toggle('bi-check-circle', ok);
            icon.classList.toggle('bi-x-circle', !ok);
          }
        });
      }

      // Confirmação de senha
      const p2 = document.getElementById('id_password2') || document.getElementById('id_new_password2');
      const matchEl = $('[data-pwd-match]');
      function matchCheck() {
        if (!p2) return true;
        const ok = !!p1.value && p1.value === p2.value;
        if (matchEl) matchEl.classList.toggle('d-none', !ok);
        // Visual leve nos campos
        if (p2.value) {
          p2.classList.toggle('is-invalid', !ok);
          p2.classList.toggle('is-valid', ok);
        } else {
          p2.classList.remove('is-invalid','is-valid');
        }
        return ok;
      }

      function update() {
        const val = p1.value || '';
        const r = rules(val);
        const s = computeScore(val, r);

        if (bar) {
          bar.style.width = s + '%';
          bar.className = 'progress-bar ' + color(s, r);
          bar.setAttribute('aria-valuemin', '0');
          bar.setAttribute('aria-valuemax', '100');
          bar.setAttribute('aria-valuenow', String(s));
        }
        const labelText = 'Força da senha: ' + label(s, r);
        if (text) text.textContent = labelText;
        announce(labelText);

        updateReqUI(r);

        const okLen = r.length;
        const okMatch = matchCheck();

        // Único bloqueio obrigatório: mínimo de 8 caracteres
        // Se houver confirmação e estiver preenchida porém diferente, também bloqueia.
        if (submitBtn) {
          const shouldDisable = !okLen || (p2 && p2.value && !okMatch);
          submitBtn.toggleAttribute('disabled', shouldDisable);
        }
      }

      p1.addEventListener('input', update);
      if (p2) p2.addEventListener('input', update);
      update();
    })();

    // -----------------------------
    // Loading no submit, foco e prevenção de double-submit
    // -----------------------------
    $all('form.auth-form').forEach(function (form) {
      const btn = form.querySelector('[data-submit]');
      let submitted = false;

      if (btn) {
        form.addEventListener('submit', function (e) {
          if (submitted) { e.preventDefault(); return; }
          submitted = true;
          btn.setAttribute('disabled', 'disabled');
          const spinner = btn.querySelector('.spinner-border');
          const label = btn.querySelector('.label');
          if (spinner) spinner.classList.remove('d-none');
          if (label) label.textContent = 'Enviando...';
        });
      }

      // Foco no primeiro campo
      const first = form.querySelector('input:not([type=hidden]):not([disabled]), select, textarea');
      if (first && !first.value) {
        try { first.focus({ preventScroll: true }); } catch(_) { first.focus(); }
      }
    });
  });
})();