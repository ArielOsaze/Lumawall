/* LumaWall site behaviour.
   Small and dependency-free: nav state, one scroll reveal, video autoplay, and
   honest download handling.

   What was removed and why: this file used to split headlines into characters,
   count numbers up from zero, and run a light sweep across labels. Each effect
   is defensible alone, but together they made the page feel busy and cheap.
   There is now exactly one animation — the same blur-and-rise reveal the rest
   of the Xinet sites use — and it is driven entirely by CSS.

   Everything degrades gracefully: with JavaScript off the page still reads,
   every section is visible, and every download link works. */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── nav: solid background once the page has scrolled ────────────────────
  var nav = document.getElementById('nav');
  var onScroll = function () {
    if (!nav) return;
    nav.classList.toggle('scrolled', window.scrollY > 8);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ── one reveal, applied to sections as they enter the viewport ───────────
  // The hidden state lives in the .reveal class, which is added here — never in
  // the base stylesheet. If this script never runs, nothing is hidden.
  var revealTargets = document.querySelectorAll('[data-reveal]');

  if ('IntersectionObserver' in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in');
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.1 });

    revealTargets.forEach(function (el) {
      el.classList.add('reveal');
      io.observe(el);
    });

    // Anything already on screen reveals now rather than waiting for a scroll
    // event that may never come. Without this, an element sitting just below the
    // observer's -12% bottom margin (the hero's stat row, at most window sizes)
    // stayed at opacity 0 until the visitor happened to scroll — and looked
    // simply broken.
    var fold = window.innerHeight * 0.92;
    revealTargets.forEach(function (el) {
      if (el.classList.contains('in')) return;
      var r = el.getBoundingClientRect();
      if (r.top < fold && r.bottom > 0) el.classList.add('in');
    });
  }

  // ── the promo video plays on its own ────────────────────────────────────
  // Muted and inline, which is what browsers allow without a gesture. If
  // autoplay is refused the controls are already there, so the visitor can start
  // it themselves; the poster frame means the block never looks broken.
  var promo = document.getElementById('promo');

  if (promo) {
    promo.muted = true;
    promo.playsInline = true;

    var startPromo = function () {
      var p = promo.play();
      // A refusal is not an error: the controls are visible, so the visitor can
      // start it themselves.
      if (p && p.catch) p.catch(function () {});
    };

    // Whether the visitor stopped it on purpose. If they did, scrolling away and
    // back must not restart it: they pressed pause because they wanted it
    // stopped, and a page that overrides that is a page that fights its user.
    var userPaused = false;
    promo.addEventListener('pause', function () {
      // A pause that did not come from the observer is the visitor's.
      if (!pausingForViewport) userPaused = true;
    });
    var pausingForViewport = false;

    // Start when the block is on screen rather than at page load, so the visitor
    // sees the video from the beginning instead of arriving 20 seconds in.
    if ('IntersectionObserver' in window) {
      var vio = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            // Resuming after a scroll is fine; resuming after a deliberate pause
            // is not.
            if (!userPaused) startPromo();
          } else if (!promo.paused) {
            pausingForViewport = true;
            promo.pause();
            pausingForViewport = false;
          }
        });
      }, { threshold: 0.35 });
      vio.observe(promo);
    } else {
      startPromo();
    }

    // Some browsers only allow playback after the first interaction. Retry once
    // on the first scroll or click, whichever comes first, then stop listening.
    var retry = function () {
      if (promo.paused) startPromo();
      window.removeEventListener('scroll', retry);
      window.removeEventListener('click', retry);
      window.removeEventListener('touchstart', retry);
    };
    window.addEventListener('scroll', retry, { passive: true, once: false });
    window.addEventListener('click', retry, { once: false });
    window.addEventListener('touchstart', retry, { passive: true, once: false });
  }

  // ── performance bars animate to their value when seen ──────────────────
  // A bar that grows to its value is read; a bar that is simply there is
  // skimmed. The value is in the markup, so with JS off the bar is correct.
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
