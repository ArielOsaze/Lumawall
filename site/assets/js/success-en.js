/* Halaman status pesanan.

   Halaman ini hanya meminta satu hal ke server: status pesanan dengan kode
   yang ada di URL. Server yang memutuskan apakah pembeli boleh melihat
   tautannya. Tidak ada token yang disimpan di localStorage dan tidak ada
   keputusan pembayaran yang dibuat di peramban - semuanya dari /api/order. */

(function () {
  'use strict';

  var states = {
    loading: document.getElementById('state-loading'),
    waiting: document.getElementById('state-waiting'),
    paid: document.getElementById('state-paid'),
    error: document.getElementById('state-error')
  };

  function show(name) {
    Object.keys(states).forEach(function (k) {
      if (states[k]) states[k].hidden = (k !== name);
    });
  }

  function orderCode() {
    try {
      var p = new URLSearchParams(window.location.search);
      var fromUrl = (p.get('order') || p.get('code') || '').trim().toUpperCase();
      if (fromUrl) return fromUrl;
      // iPaymu kadang mengembalikan tanpa parameter; kode yang disimpan saat
      // checkout jadi cadangannya.
      var saved = sessionStorage.getItem('lumawall_order');
      return saved ? String(saved).trim().toUpperCase() : '';
    } catch (e) {
      return '';
    }
  }

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function fail(message) {
    if (message) setText('err-text', message);
    show('error');
  }

  var code = orderCode();
  if (!code) {
    fail('This link has no order code in it. Open the link iPaymu gave you after payment, or contact support.');
    return;
  }

  var checks = 0;
  var maxChecks = 40; // ~2 menit menunggu konfirmasi bank

  function load() {
    fetch('/api/order?code=' + encodeURIComponent(code), { headers: { Accept: 'application/json' } })
      .then(function (res) {
        return res.json().then(function (d) { return { status: res.status, data: d }; });
      })
      .then(function (r) {
        var d = r.data || {};

        if (r.status === 404) {
          return fail(d.error || 'No order found with that code.');
        }
        if (r.status === 400) {
          return fail(d.error || 'That order code is not valid.');
        }
        if (!d.ok) {
          return fail(d.error || 'We cannot check your order right now. Try reloading this page.');
        }

        if (!d.paid) {
          setText('order-waiting', d.order || code);
          show('waiting');
          checks += 1;
          if (checks < maxChecks) setTimeout(load, 3000);
          return;
        }

        // Lunas: pasang tautan unduhannya.
        setText('order-paid', d.order || code);
        setText('meta-size', 'LumaWall-Setup.exe \u00b7 latest version');

        if (d.expired) {
          setText('meta-uses', 'Link expired');
        } else if (d.exhausted) {
          setText('meta-uses', 'Download limit reached');
        } else if (typeof d.usesLeft === 'number') {
          setText('meta-uses', 'Uses left: ' + d.usesLeft + ' of ' + d.maxUses);
        }

        var btn = document.getElementById('btn-download');
        if (btn) {
          if (d.expired || d.exhausted) {
            btn.removeAttribute('href');
            btn.setAttribute('aria-disabled', 'true');
            btn.style.opacity = '.5';
            btn.style.pointerEvents = 'none';
            btn.textContent = d.expired ? 'Link expired' : 'Download limit reached';
          } else {
            btn.href = d.downloadUrl;
          }
        }

        var copy = document.getElementById('btn-copy');
        if (copy) {
          copy.addEventListener('click', function () {
            var url = window.location.origin + d.downloadUrl;
            var done = document.getElementById('copy-done');
            var mark = function () {
              if (done) {
                done.hidden = false;
                setTimeout(function () { done.hidden = true; }, 2200);
              }
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
              navigator.clipboard.writeText(url).then(mark).catch(function () { window.prompt('Copy this link:', url); });
            } else {
              window.prompt('Copy this link:', url);
            }
          });
        }

        show('paid');
      })
      .catch(function () {
        fail('Could not reach the server. Check your connection and reload this page.');
      });
  }

  var reload = document.getElementById('btn-reload');
  if (reload) {
    reload.addEventListener('click', function () {
      show('loading');
      checks = 0;
      load();
    });
  }

  show('loading');
  load();
})();
