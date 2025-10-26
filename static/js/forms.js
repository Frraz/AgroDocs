/* static/js/forms.js
   Melhorias:
   - Máscara dinâmica CPF/CNPJ e CAR
   - Datepicker (flatpickr) com vínculo entre datas (emissão -> minDate do vencimento)
   - Telefone com intl-tel-input estável (sem desalinhamento): separateDialCode=false, nacional na UI e E.164 no submit
   - Normalização de valores iniciais (E.164 -> nacional) e dica dinâmica de destino (E.164)
   - Proteção contra reinicialização e pequenos aprimoramentos de UX/acessibilidade
*/

(function () {
  // Utilitário simples
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  // ========== CPF/CNPJ dinâmico ==========
  $all('input.mask-doc').forEach(function (el) {
    try {
      IMask(el, {
        mask: [
          { mask: '000.000.000-00' },       // CPF
          { mask: '00.000.000/0000-00' }    // CNPJ
        ],
        lazy: true,
        overwrite: true,
        dispatch: function (appended, dynamicMasked) {
          const raw = (dynamicMasked.value + appended).replace(/\D+/g, '');
          return raw.length > 11 ? dynamicMasked.compiledMasks[1] : dynamicMasked.compiledMasks[0];
        }
      });
      // garante espaço suficiente para CNPJ com pontuação
      const ml = Number(el.getAttribute('maxlength') || 0);
      if (!ml || ml < 18) el.setAttribute('maxlength', '18');
    } catch (e) { console.error('Erro ao aplicar máscara CPF/CNPJ:', e); }
  });

  // ========== CAR recibo: UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX ==========
  $all('input.mask-car').forEach(function (el) {
    try {
      IMask(el, {
        mask: 'AA-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        definitions: { 'A': /[A-Za-z]/, 'X': /[A-Za-z0-9]/ },
        prepare: s => s.toUpperCase(),
        commit: (v, m) => { m._value = v.toUpperCase(); }
      });
    } catch (e) { console.error('Erro ao aplicar máscara CAR:', e); }
  });

  // ========== Date pickers (flatpickr) com vínculo emissão -> vencimento ==========
  (function initDates() {
    const emissao = $('input.date-picker[data-role="emissao"]');
    const venc = $('input.date-picker[data-role="vencimento"]');

    if (!window.flatpickr) return;

    try {
      flatpickr.localize(flatpickr.l10ns.pt);

      const fpEmissao = emissao ? flatpickr(emissao, {
        dateFormat: 'Y-m-d',  // valor submetido
        altInput: true,
        altFormat: 'd/m/Y',   // exibido
        allowInput: true,
        onChange: function (selectedDates) {
          if (fpVenc) {
            const min = selectedDates && selectedDates[0] ? selectedDates[0] : null;
            fpVenc.set('minDate', min);
            // Se o vencimento ficou antes da emissão, ajusta para a própria emissão
            if (min && fpVenc.selectedDates[0] && fpVenc.selectedDates[0] < min) {
              fpVenc.setDate(min, true);
            }
          }
        }
      }) : null;

      const fpVenc = venc ? flatpickr(venc, {
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: 'd/m/Y',
        allowInput: true,
      }) : null;

      // Inicial: se já houver emissão preenchida, aplica minDate no vencimento
      if (fpEmissao && fpVenc && fpEmissao.selectedDates[0]) {
        fpVenc.set('minDate', fpEmissao.selectedDates[0]);
        if (fpVenc.selectedDates[0] && fpVenc.selectedDates[0] < fpEmissao.selectedDates[0]) {
          fpVenc.setDate(fpEmissao.selectedDates[0], true);
        }
      }
    } catch (e) {
      console.error('Erro ao inicializar datepickers:', e);
    }
  })();

  // ========== Telefone (intl-tel-input) — UI nacional, submit em E.164 ==========
  (function initPhones() {
    if (!window.intlTelInput) return;

    $all('input.phone-input').forEach(function (el) {
      try {
        if (el.dataset.itiInitialized === '1') return;

        // O layout mais estável: sem dial code separado
        const iti = window.intlTelInput(el, {
          initialCountry: 'br',
          preferredCountries: ['br', 'us', 'pt', 'ar', 'py'],
          separateDialCode: false,      // evita bloco lateral que desalinha
          nationalMode: true,           // mostra nacional na UI
          autoPlaceholder: 'polite',
          placeholderNumberType: 'MOBILE',
          formatOnDisplay: true,        // formata conforme digita
          autoInsertDialCode: false,
          utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@23.7.3/build/js/utils.js',
        });
        el.dataset.itiInitialized = '1';

        const ready = iti.promise ? iti.promise : Promise.resolve();
        const utilsReady = () => !!window.intlTelInputUtils;

        function normalizeInitial() {
          if (!utilsReady()) return;
          const v = (el.value || '').trim();
          if (v.startsWith('+')) {
            // Valor vindo do backend (E.164) -> exibe como nacional
            iti.setNumber(v);
            const nat = iti.getNumber(intlTelInputUtils.numberFormat.NATIONAL);
            if (nat) el.value = nat;
          }
        }

        function getOrCreateHint() {
          let hint = el.parentElement.querySelector('[data-phone-hint]');
          if (!hint) {
            hint = document.createElement('div');
            hint.className = 'form-help mt-1';
            hint.setAttribute('data-phone-hint', '');
            el.insertAdjacentElement('afterend', hint);
          }
          return hint;
        }

        function updateHint() {
          const hint = getOrCreateHint();
          if (utilsReady() && iti.isValidNumber()) {
            hint.textContent = 'Destino: ' + iti.getNumber(); // E.164
          } else {
            const data = iti.getSelectedCountryData();
            const dial = data && data.dialCode ? '+' + data.dialCode : '+';
          }
        }

        ready.then(function () {
          normalizeInitial();
          updateHint();
        });

        el.addEventListener('input', function () {
          // Se o usuário colar com "+", remove para não poluir a UI nacional
          if (el.value.trim().startsWith('+')) {
            el.value = el.value.replace(/^\++/, '');
          }
          updateHint();
        });
        el.addEventListener('blur', updateHint);
        el.addEventListener('countrychange', function () {
          normalizeInitial();
          updateHint();
        });

        // No submit, envia E.164; se inválido e required, bloqueia
        const form = el.closest('form');
        if (form) {
          form.addEventListener('submit', function (ev) {
            if (!utilsReady()) return; // fallback: deixa o backend validar
            if (el.hasAttribute('required') && !iti.isValidNumber()) {
              ev.preventDefault();
              updateHint();
              el.focus();
              try { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch {}
              return;
            }
            const e164 = iti.getNumber(); // +E.164
            if (e164) el.value = e164;
          });
        }
      } catch (e) {
        console.error('Erro ao inicializar telefone:', e);
      }
    });
  })();

})();