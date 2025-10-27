/* static/js/forms.js
   Melhorias:
   - Máscara dinâmica CPF/CNPJ e CAR (IMask) com fallbacks elegantes
   - Datepicker (flatpickr) com vínculo entre datas (emissão -> minDate do vencimento)
     e fallback usando inputs nativos (min/max) quando flatpickr não estiver disponível
   - Telefone com intl-tel-input estável (separateDialCode=false): UI nacional e envio em E.164
   - Normalização de valores iniciais (E.164 -> nacional) e dica dinâmica de destino (E.164)
   - Proteções contra reinicialização, UX/acessibilidade e mensagens amigáveis
*/

(function () {
  // ==========================
  // Utilitários
  // ==========================
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }
  function onReady(cb) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", cb, { once: true });
    else cb();
  }
  function debounce(fn, wait) {
    let t; return function (...args) {
      clearTimeout(t); t = setTimeout(() => fn.apply(this, args), wait);
    };
  }
  const E164_RE = /^\+[1-9]\d{7,14}$/; // regra geral E.164 (mín. 8 dígitos úteis)

  // Fallback simples de normalização de telefone caso intl-tel-input não esteja disponível
  function normalizePhoneE164(raw, defaultCountry = "+55") {
    if (!raw) return "";
    let v = String(raw).trim();
    if (v.toLowerCase().startsWith("whatsapp:")) v = v.split(":", 1)[0] ? v.split(":")[1].trim() : "";
    v = v.replace(/[()\s-]/g, "");
    if (!v) return "";
    if (!v.startsWith("+")) v = defaultCountry + v;
    // remove múltiplos '+'
    v = "+" + v.replace(/^\++/, "");
    return v;
  }

  function announcePolite(msg) {
    let live = document.querySelector('[data-live="forms"]');
    if (!live) {
      live = document.createElement("div");
      live.setAttribute("aria-live", "polite");
      live.setAttribute("class", "visually-hidden");
      live.setAttribute("data-live", "forms");
      document.body.appendChild(live);
    }
    live.textContent = msg || "";
  }

  function toast(type, title, message) {
    if (window.AgroTheme && typeof window.AgroTheme.toast === "function") {
      window.AgroTheme.toast({ type: type || "info", title: title || "", message: message || "" });
    }
  }

  onReady(function initForms() {
    // ==========================
    // 1) Máscaras CPF/CNPJ
    // ==========================
    $all('input.mask-doc').forEach(function (el) {
      try {
        if (!window.IMask) return; // graceful
        if (el.dataset.maskApplied === "1") return;

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
        el.dataset.maskApplied = "1";
      } catch (e) { console.error('Erro ao aplicar máscara CPF/CNPJ:', e); }
    });

    // ==========================
    // 2) Máscara CAR (UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)
    // ==========================
    $all('input.mask-car').forEach(function (el) {
      try {
        if (!window.IMask) return; // graceful
        if (el.dataset.maskApplied === "1") return;

        IMask(el, {
          mask: 'AA-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
          definitions: { 'A': /[A-Za-z]/, 'X': /[A-Za-z0-9]/ },
          prepare: s => s.toUpperCase(),
          commit: (v, m) => { m._value = v.toUpperCase(); }
        });

        el.dataset.maskApplied = "1";
      } catch (e) { console.error('Erro ao aplicar máscara CAR:', e); }
    });

    // ==========================
    // 3) Datas com vínculo (flatpickr) + fallback
    // ==========================
    (function initDates() {
      // Seletores compatíveis: com ou sem .date-picker
      const emissao = $('input[data-role="emissao"].date-picker, input.date-picker[data-role="emissao"], input[type="date"][data-role="emissao"]');
      const venc = $('input[data-role="vencimento"].date-picker, input.date-picker[data-role="vencimento"], input[type="date"][data-role="vencimento"]');

      // Genérico: data-min-from="id_ou_name_do_campo_emissao"
      $all('input[type="date"][data-min-from]').forEach(function (vencInput) {
        const ref = vencInput.getAttribute('data-min-from');
        let refEl = document.getElementById(ref) || document.querySelector(`input[name="${ref}"]`);
        if (!refEl) return;
        const syncMin = function () {
          if (refEl.value) {
            vencInput.min = refEl.value;
            if (vencInput.value && vencInput.value < refEl.value) {
              vencInput.value = refEl.value;
            }
          } else {
            vencInput.removeAttribute("min");
          }
        };
        refEl.addEventListener('change', syncMin);
        syncMin();
      });

      // flatpickr
      if (window.flatpickr) {
        try {
          if (flatpickr.l10ns && flatpickr.l10ns.pt) {
            flatpickr.localize(flatpickr.l10ns.pt);
          }
          let fpEmissao = null, fpVenc = null;

          if (emissao && !emissao.dataset.fpApplied) {
            fpEmissao = flatpickr(emissao, {
              dateFormat: 'Y-m-d',  // valor submetido
              altInput: true,
              altFormat: 'd/m/Y',   // exibido
              allowInput: true,
              onChange: function (selectedDates) {
                if (fpVenc) {
                  const min = selectedDates && selectedDates[0] ? selectedDates[0] : null;
                  fpVenc.set('minDate', min);
                  if (min && fpVenc.selectedDates[0] && fpVenc.selectedDates[0] < min) {
                    fpVenc.setDate(min, true);
                  }
                }
              }
            });
            emissao.dataset.fpApplied = "1";
          }

          if (venc && !venc.dataset.fpApplied) {
            fpVenc = flatpickr(venc, {
              dateFormat: 'Y-m-d',
              altInput: true,
              altFormat: 'd/m/Y',
              allowInput: true,
            });
            venc.dataset.fpApplied = "1";
          }

          if (fpEmissao && fpVenc && fpEmissao.selectedDates[0]) {
            fpVenc.set('minDate', fpEmissao.selectedDates[0]);
            if (fpVenc.selectedDates[0] && fpVenc.selectedDates[0] < fpEmissao.selectedDates[0]) {
              fpVenc.setDate(fpEmissao.selectedDates[0], true);
            }
          }
        } catch (e) {
          console.error('Erro ao inicializar flatpickr:', e);
        }
      } else {
        // Fallback: se não houver flatpickr, use min no input nativo
        if (emissao && venc) {
          const syncNative = function () {
            if (emissao.value) {
              venc.min = emissao.value;
              if (venc.value && venc.value < emissao.value) {
                venc.value = emissao.value;
              }
            } else {
              venc.removeAttribute("min");
            }
          };
          emissao.addEventListener('change', syncNative);
          syncNative();
        }
      }
    })();

    // ==========================
    // 4) Telefone (intl-tel-input) — UI nacional, submit em E.164
    // ==========================
    (function initPhones() {
      const inputs = $all('input.phone-input');
      if (!inputs.length) return;

      const hasITI = !!window.intlTelInput;
      inputs.forEach(function (el) {
        try {
          if (el.dataset.itiInitialized === '1') return;

          // Se não houver intl-tel-input, aplica apenas fallback no submit (abaixo)
          let iti = null;
          if (hasITI) {
            const initial = (el.getAttribute('data-initial-country') || 'br').toLowerCase();
            iti = window.intlTelInput(el, {
              initialCountry: initial,
              preferredCountries: ['br', 'us', 'pt', 'ar', 'py'],
              separateDialCode: false,
              nationalMode: true,
              autoPlaceholder: 'polite',
              placeholderNumberType: 'MOBILE',
              formatOnDisplay: true,
              autoInsertDialCode: false,
              // Nota: carregue o utils.js via <script> no template ou deixe a CDN:
              utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@23.7.3/build/js/utils.js',
            });
          }

          el.dataset.itiInitialized = '1';

          // Dica dinâmica (Destino: +E.164)
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
          const hint = getOrCreateHint();

          // Normaliza valor inicial vindo do backend (E.164 ou whatsapp:+E.164) -> UI nacional
          function normalizeInitial() {
            const raw = (el.value || '').trim();
            if (!raw) return;
            if (hasITI && iti) {
              // Se vier com whatsapp:+..., remove prefixo
              const clean = raw.toLowerCase().startsWith('whatsapp:') ? raw.split(':')[1].trim() : raw;
              // Se vier com +, setNumber entende E.164 e preenche nacional
              if (clean.startsWith('+')) {
                iti.setNumber(clean);
                if (window.intlTelInputUtils) {
                  const nat = iti.getNumber(intlTelInputUtils.numberFormat.NATIONAL);
                  if (nat) el.value = nat;
                }
              }
            } else {
              // Sem ITI: não altera, mas mantém compatibilidade
            }
          }

          // Atualiza a dica E.164
          const refreshHint = debounce(function () {
            if (hasITI && iti && window.intlTelInputUtils) {
              const isValid = iti.isValidNumber();
              if (isValid) {
                const e164 = iti.getNumber(); // com +
                hint.textContent = 'Destino: ' + e164;
                hint.classList.remove('text-danger');
              } else {
                const data = iti.getSelectedCountryData();
                const dial = data && data.dialCode ? '+' + data.dialCode : '+';
                hint.textContent = 'Informe um número válido. Ex.: ' + dial + '11999999999';
                hint.classList.add('text-danger');
              }
            } else {
              // Fallback: orientação genérica
              const v = (el.value || '').trim();
              if (v) hint.textContent = 'Destino no envio será normalizado para E.164 (ex.: +5511999999999).';
              else hint.textContent = '';
              hint.classList.remove('text-danger');
            }
          }, 80);

          // Listeners
          normalizeInitial();
          refreshHint();

          el.addEventListener('input', function () {
            // Se o usuário colar com "+", remove para não poluir a UI nacional (quando ITI ativo)
            if (hasITI && iti && el.value.trim().startsWith('+')) {
              el.value = el.value.replace(/^\++/, '');
            }
            refreshHint();
          });
          el.addEventListener('blur', refreshHint);
          el.addEventListener('countrychange', function () {
            normalizeInitial(); refreshHint();
          });

          // Submit: escreve E.164 no value (para o backend)
          const form = el.closest('form');
          if (form && !form.dataset.phoneSubmitBound) {
            form.addEventListener('submit', function (ev) {
              const required = el.hasAttribute('required');

              if (hasITI && iti && window.intlTelInputUtils) {
                const valid = iti.isValidNumber();
                if (required && !valid && el.value.trim()) {
                  ev.preventDefault();
                  refreshHint();
                  el.focus();
                  try { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch {}
                  toast("error", "WhatsApp", "Número inválido. Use E.164 (ex.: +5511999999999).");
                  return;
                }
                const e164 = iti.getNumber(); // +E.164 ou "" se vazio
                if (e164) el.value = e164;
              } else {
                // Fallback: normalização simples
                const e164 = normalizePhoneE164(el.value, "+55");
                if (e164 && !E164_RE.test(e164)) {
                  if (required) {
                    ev.preventDefault();
                    toast("error", "WhatsApp", "Número inválido. Use E.164 (ex.: +5511999999999).");
                    el.focus();
                    return;
                  }
                } else if (e164) {
                  el.value = e164;
                }
              }
            });
            form.dataset.phoneSubmitBound = "1";
          }
        } catch (e) {
          console.error('Erro ao inicializar telefone:', e);
        }
      });
    })();

    // ==========================
    // 5) Acessibilidade geral
    // ==========================
    // Indica ao leitor de tela quando um campo inválido for encontrado após submit nativo
    $all('form').forEach(function (form) {
      form.addEventListener('invalid', function (e) {
        announcePolite('Há campos inválidos no formulário. Verifique os destaques.');
      }, true);
    });
  });
})();