/* LumaWall site behaviour.
   Small and dependency-free: nav state, scroll reveal, and honest download
   handling. Everything degrades gracefully if this file never loads. */

(function () {
  'use strict';

  // ── nav: solid background once the page has scrolled ────────────────────
  var nav = document.getElementById('nav');
  var onScroll = function () {
    if (!nav) return;
    nav.classList.toggle('scrolled', window.scrollY > 12);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ── reveal sections as they enter the viewport ──────────────────────────
  // The video block is deliberately excluded: it is the section most likely to
  // be captured by a crawler or a screenshot tool, and a poster that is still
  // faded out looks like a broken player.
  var targets = document.querySelectorAll(
    '.sec-head, .card, .shot, .dl-card, .note, .perf-row, .faq, .req, .table-wrap, .cta-mark'
  );

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in');
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });

    targets.forEach(function (el, i) {
      el.classList.add('reveal');
      // Stagger items inside the same grid so they cascade instead of popping
      // in all at once. Capped so long lists do not feel slow.
      el.style.transitionDelay = Math.min(i % 6, 5) * 55 + 'ms';
      io.observe(el);
    });
  }

  // ── performance bars animate to their value when seen ──────────────────
  var bars = document.querySelectorAll('.bar-fill');
  if ('IntersectionObserver' in window && bars.length) {
    var barObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        var target = el.style.getPropertyValue('--w');
        el.style.setProperty('--w', '0%');
        requestAnimationFrame(function () {
          requestAnimationFrame(function () { el.style.setProperty('--w', target); });
        });
        barObserver.unobserve(el);
      });
    }, { threshold: 0.4 });
    bars.forEach(function (b) { barObserver.observe(b); });
  }

  // ── year in the footer ─────────────────────────────────────────────────
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = String(new Date().getFullYear());

  // ── downloads: confirm the file is really there before navigating ───────
  // A dead link on a download page is the worst possible failure, so each
  // download is probed first and the button reports a problem instead of
  // silently doing nothing.
  document.querySelectorAll('a[download]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      var href = link.getAttribute('href');
      if (!href) return;

      var original = link.innerHTML;
      link.style.pointerEvents = 'none';
      link.style.opacity = '.75';

      fetch(href, { method: 'HEAD' })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          link.style.pointerEvents = '';
          link.style.opacity = '';
        })
        .catch(function () {
          event.preventDefault();
          link.innerHTML = 'File belum tersedia — coba lagi nanti';
          link.style.opacity = '.6';
          setTimeout(function () {
            link.innerHTML = original;
            link.style.pointerEvents = '';
            link.style.opacity = '';
          }, 3200);
        });
    });
  });
})();
