/* Navbar behaviour, on every page.
 *
 * This is separate from main.js on purpose. main.js is the home page's
 * behaviour — the reveal, the promo video, the performance bars — and it is
 * loaded only there. The navbar is on every page, so putting its behaviour in
 * main.js left the checkout and success pages with a menu button that did
 * nothing: the markup was there and the script was not.
 *
 * Everything here is optional: each piece checks that the element it needs
 * exists before wiring anything up, so a page with a simpler navbar simply
 * skips the parts it does not have.
 *
 * No dependencies, no build step, and it degrades gracefully — with JavaScript
 * off the links are still in the markup and still work. */

(function () {
  'use strict';

  // ── the two grouped menus ───────────────────────────────────────────────
  //
  // Six flat links filled the bar, so the sections are grouped behind two
  // headings. What matters is that the menu is reachable without a mouse and
  // closes the way a menu is expected to:
  //
  //   - it opens on hover for a pointer, and on click for a keyboard or a
  //     touch, where hover does not exist;
  //   - Escape closes it and returns focus to its button, so the keyboard is
  //     not left stranded inside a closed menu;
  //   - a click anywhere else closes it;
  //   - focus leaving it closes it, which covers tabbing away.
  var drops = Array.prototype.slice.call(document.querySelectorAll('.nav-drop'));

  function closeDrop(drop) {
    drop.classList.remove('open');
    var b = drop.querySelector('button');
    if (b) b.setAttribute('aria-expanded', 'false');
  }

  function closeAllDrops(except) {
    drops.forEach(function (d) { if (d !== except) closeDrop(d); });
  }

  drops.forEach(function (drop) {
    var button = drop.querySelector('button');
    if (!button) return;

    var open = function () {
      closeAllDrops(drop);
      drop.classList.add('open');
      button.setAttribute('aria-expanded', 'true');
    };

    button.addEventListener('click', function (event) {
      event.stopPropagation();
      if (drop.classList.contains('open')) closeDrop(drop);
      else open();
    });

    // Hover is a convenience for a pointer, never the only way in. It is
    // skipped on touch, where a tap would otherwise fire this and the click
    // both.
    var hoverable = window.matchMedia && window.matchMedia('(hover: hover)').matches;
    if (hoverable) {
      drop.addEventListener('mouseenter', open);
      drop.addEventListener('mouseleave', function () { closeDrop(drop); });
    }

    drop.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape') return;
      closeDrop(drop);
      button.focus();
    });

    // Tabbing out closes it. Deferred by a task: while focus moves between two
    // elements inside the menu there is a moment when it is in neither, and
    // reading it then would close the menu under the visitor's hands.
    drop.addEventListener('focusout', function () {
      setTimeout(function () {
        if (!drop.contains(document.activeElement)) closeDrop(drop);
      }, 0);
    });

    // Choosing something closes the menu, so it does not stay over the section
    // it just jumped to.
    drop.querySelectorAll('.nav-drop-panel a').forEach(function (link) {
      link.addEventListener('click', function () { closeDrop(drop); });
    });
  });

  if (drops.length) {
    document.addEventListener('click', function () { closeAllDrops(null); });
  }

  // ── the small-screen menu ───────────────────────────────────────────────
  //
  // Below 760px the links are hidden by the stylesheet, so this button is the
  // only route to any section. It is on every page, including checkout and the
  // order status page — which is exactly where a visitor most needs a way back.
  var burger = document.querySelector('.nav-burger');
  var mobileMenu = document.getElementById('nav-mobile');

  if (burger && mobileMenu) {
    var setMenu = function (open) {
      mobileMenu.classList.toggle('open', open);
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    };

    burger.addEventListener('click', function (event) {
      event.stopPropagation();
      setMenu(!mobileMenu.classList.contains('open'));
    });

    mobileMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () { setMenu(false); });
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') setMenu(false);
    });

    // A resize past the breakpoint would otherwise leave the panel open while
    // the bar's own links became visible, listing the same destinations twice.
    window.addEventListener('resize', function () {
      if (window.innerWidth > 760) setMenu(false);
    }, { passive: true });
  }
})();
