/* LumaWall site behaviour.
   Dependency-free: nav state, scroll reveal, kinetic text, count-up numbers,
   and honest download handling. Everything degrades gracefully if this file
   never loads — with JS off the page still reads, the numbers show their final
   values, and every download link works. */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── nav: solid background once the page has scrolled ────────────────────
  var nav = document.getElementById('nav');
  var onScroll = function () {
    if (!nav) return;
    nav.classList.toggle('scrolled', window.scrollY > 12);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ── split every headline into per-character spans ───────────────────────
  // The reveal is what makes a headline feel written rather than switched on.
  // Characters are wrapped in inline-block spans, so a headline with a gradient
  // must paint that gradient per character (a parent background-clip does not
  // reach through a transformed child).
  function splitElement(el) {
    if (el.dataset.split === 'done') return [];
    var text = el.textContent;
    var gradient = el.classList.contains('grad');

    el.textContent = '';
    el.dataset.split = 'done';
    // The gradient needs to know how many characters the line has, so each
    // character's slice of the background can be sized to the whole line.
    el.style.setProperty('--ch-total', String(text.replace(/ /g, '').length));

    var spans = [];
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === ' ') {
        el.appendChild(document.createTextNode(' '));
        continue;
      }
      var span = document.createElement('span');
      span.className = 'ch' + (gradient ? ' ch-grad' : '');
      span.textContent = ch;
      span.style.setProperty('--i', String(spans.length));
      el.appendChild(span);
      spans.push(span);
    }
    return spans;
  }

  if (!reduceMotion) {
    document.querySelectorAll('[data-split]').forEach(function (el) {
      splitElement(el);
    });
  }

  // ── reveal sections as they enter the viewport ──────────────────────────
  // The video block is deliberately excluded: it is the section most likely to
  // be captured by a crawler or a screenshot tool, and a poster that is still
  // faded out looks like a broken player.
  var targets = document.querySelectorAll(
    '.sec-head, .card, .shot, .dl-card, .note, .perf-row, .faq, .req, .table-wrap, .cta-mark, [data-split]'
  );

  if ('IntersectionObserver' in window && !reduceMotion) {
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

  // ── count-up numbers ────────────────────────────────────────────────────
  // A figure that counts to its value is read; a figure that appears is skimmed.
  // The final value is always in the HTML, so with JS off nothing is lost.
  function countUp(el) {
    if (el.dataset.counted === 'done') return;
    el.dataset.counted = 'done';

    var target = parseFloat(el.dataset.count);
    if (!isFinite(target)) return;

    var decimals = parseInt(el.dataset.decimals || '0', 10);
    var prefix = el.dataset.prefix || '';
    var suffix = el.dataset.suffix || '';
    var dur = parseInt(el.dataset.dur || '1400', 10);

    if (reduceMotion) {
      el.textContent = prefix + target.toFixed(decimals) + suffix;
      return;
    }

    var start = null;
    function step(now) {
      if (start === null) start = now;
      var t = Math.min(1, (now - start) / dur);
      // easeOutExpo: fast then settling, which reads as counting.
      var e = t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
      el.textContent = prefix + (target * e).toFixed(decimals) + suffix;
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = prefix + target.toFixed(decimals) + suffix;
    }
    requestAnimationFrame(step);
  }

  var counters = document.querySelectorAll('[data-count]');
  if ('IntersectionObserver' in window && counters.length) {
    var countObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        countUp(entry.target);
        countObserver.unobserve(entry.target);
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { countObserver.observe(el); });
  }

  // ── performance bars animate to their value when seen ──────────────────
  var bars = document.querySelectorAll('.bar-fill');
  if ('IntersectionObserver' in window && bars.length && !reduceMotion) {
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
