/**
 * auth-guard.js — Hub da Família Donato Suarez
 * Proteção por PIN de 6 dígitos. Incluir em TODAS as páginas.
 * Qualquer PIN válido libera o acesso (array de PINs).
 * Token salvo no localStorage por 30 dias.
 */
(function () {
  'use strict';

  // === CONFIG ===
  var VALID_PINS = ['142632', '300104'];
  var TOKEN_KEY = 'hub_auth_token';
  var TOKEN_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000; // 30 dias

  // === FAIL-SECURE: esconder body imediatamente ===
  document.body.style.visibility = 'hidden';

  // === VERIFICAR TOKEN EXISTENTE ===
  function isAuthenticated() {
    try {
      var raw = localStorage.getItem(TOKEN_KEY);
      if (!raw) return false;
      var token = JSON.parse(raw);
      if (!token || !token.timestamp) return false;
      return (Date.now() - token.timestamp) < TOKEN_MAX_AGE_MS;
    } catch (e) {
      return false;
    }
  }

  function grant() {
    try {
      localStorage.setItem(TOKEN_KEY, JSON.stringify({ timestamp: Date.now() }));
    } catch (e) { /* modo incógnito — segue sem salvar */ }
    var overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.remove();
    document.body.style.visibility = '';
  }

  if (isAuthenticated()) {
    document.body.style.visibility = '';
    return;
  }

  // === MONTAR OVERLAY ===
  var overlay = document.createElement('div');
  overlay.id = 'auth-overlay';
  overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;flex-direction:column;background:var(--bg-secondary,#f0f4f8);transition:background-color 0.3s;visibility:visible;';

  var box = document.createElement('div');
  box.style.cssText = 'text-align:center;max-width:320px;padding:24px;';

  // Lock icon
  var icon = document.createElement('div');
  icon.style.cssText = 'font-size:2.5rem;margin-bottom:16px;';
  icon.textContent = '🔒';

  // Title
  var title = document.createElement('h2');
  title.style.cssText = 'margin:0 0 8px;font-size:1.3rem;font-weight:800;color:var(--text-primary,#0A1928);font-family:var(--font-sans,Inter,sans-serif);';
  title.textContent = 'Hub da Família';

  // Subtitle
  var sub = document.createElement('p');
  sub.style.cssText = 'color:var(--text-muted,#718096);margin:0 0 24px;font-size:0.9rem;font-family:var(--font-sans,Inter,sans-serif);';
  sub.textContent = 'Digite o PIN para acessar';

  // PIN inputs container
  var pinRow = document.createElement('div');
  pinRow.id = 'pin-inputs';
  pinRow.style.cssText = 'display:flex;gap:8px;justify-content:center;margin-bottom:16px;';

  var inputs = [];
  for (var i = 0; i < 6; i++) {
    var inp = document.createElement('input');
    inp.type = 'tel';
    inp.inputMode = 'numeric';
    inp.pattern = '[0-9]';
    inp.maxLength = 1;
    inp.autocomplete = 'off';
    inp.style.cssText = 'width:44px;height:52px;text-align:center;font-size:1.5rem;font-weight:700;border:2px solid var(--border,#dde3ea);border-radius:8px;background:var(--bg-card,#fff);color:var(--text-primary,#0A1928);outline:none;transition:border-color 0.2s;font-family:var(--font-sans,Inter,sans-serif);-webkit-appearance:none;';
    (function (idx) {
      inp.addEventListener('focus', function () {
        this.style.borderColor = 'var(--cyan,#00B0FF)';
      });
      inp.addEventListener('blur', function () {
        this.style.borderColor = 'var(--border,#dde3ea)';
      });
      inp.addEventListener('input', function () {
        var v = this.value.replace(/\D/g, '');
        this.value = v.charAt(0) || '';
        if (v && idx < 5) inputs[idx + 1].focus();
        tryValidate();
      });
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !this.value && idx > 0) {
          inputs[idx - 1].focus();
          inputs[idx - 1].value = '';
        }
      });
      inp.addEventListener('paste', function (e) {
        e.preventDefault();
        var paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
        if (paste.length >= 6) {
          for (var j = 0; j < 6; j++) inputs[j].value = paste.charAt(j);
          inputs[5].focus();
          tryValidate();
        }
      });
    })(i);
    inputs.push(inp);
    pinRow.appendChild(inp);
  }

  // Error message
  var errMsg = document.createElement('p');
  errMsg.id = 'pin-error';
  errMsg.style.cssText = 'color:var(--red,#E53935);font-size:0.85rem;min-height:20px;font-family:var(--font-sans,Inter,sans-serif);margin:0;';

  function tryValidate() {
    var pin = '';
    for (var j = 0; j < 6; j++) pin += inputs[j].value;
    if (pin.length < 6) return;
    if (VALID_PINS.indexOf(pin) !== -1) {
      grant();
    } else {
      errMsg.textContent = 'PIN incorreto';
      for (var k = 0; k < 6; k++) {
        inputs[k].value = '';
        inputs[k].style.borderColor = 'var(--red,#E53935)';
      }
      inputs[0].focus();
      setTimeout(function () {
        for (var m = 0; m < 6; m++) inputs[m].style.borderColor = 'var(--border,#dde3ea)';
      }, 600);
    }
  }

  box.appendChild(icon);
  box.appendChild(title);
  box.appendChild(sub);
  box.appendChild(pinRow);
  box.appendChild(errMsg);
  overlay.appendChild(box);

  document.body.appendChild(overlay);

  // Focus first input after render
  setTimeout(function () { inputs[0].focus(); }, 50);
})();
