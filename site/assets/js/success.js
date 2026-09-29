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
    fail('Tautan ini tidak memuat kode pesanan. Buka tautan yang diberikan iPaymu setelah pembayaran, atau hubungi dukungan.');
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
          return fail(d.error || 'Pesanan dengan kode itu tidak ditemukan.');
        }
        if (r.status === 400) {
          return fail(d.error || 'Kode pesanan tidak sah.');
        }
        if (!d.ok) {
          return fail(d.error || 'Kami tidak bisa memeriksa pesananmu sekarang. Coba muat ulang halaman ini.');
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
        setText('meta-size', 'LumaWall-Setup.exe \u00b7 versi terbaru');

        if (d.expired) {
          setText('meta-uses', 'Tautan sudah kedaluwarsa');
        } else if (d.exhausted) {
          setText('meta-uses', 'Batas unduhan sudah habis');
        } else if (typeof d.usesLeft === 'number') {
          setText('meta-uses', 'Sisa ' + d.usesLeft + ' dari ' + d.maxUses + ' unduhan');
        }

        var btn = document.getElementById('btn-download');
        if (btn) {
          if (d.expired || d.exhausted) {
            btn.removeAttribute('href');
            btn.setAttribute('aria-disabled', 'true');
            btn.style.opacity = '.5';
            btn.style.pointerEvents = 'none';
            btn.textContent = d.expired ? 'Tautan kedaluwarsa' : 'Batas unduhan habis';
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
              navigator.clipboard.writeText(url).then(mark).catch(function () { window.prompt('Salin tautan ini:', url); });
            } else {
              window.prompt('Salin tautan ini:', url);
            }
          });
        }

        show('paid');
      })
      .catch(function () {
        fail('Tidak bisa menghubungi server. Periksa koneksimu lalu muat ulang halaman ini.');
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
