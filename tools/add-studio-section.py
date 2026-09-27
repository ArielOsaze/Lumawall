"""Announce the Studio features on both language pages.

A new section rather than more cards in the existing grid: the existing six are about why
the app is built the way it is, and these are things the user can now DO. Mixing them
would bury the new work inside a list about architecture.

Written into both pages, because a feature only announced in one language is a feature
half the visitors never hear about.
"""

from pathlib import Path

# ── Indonesian ───────────────────────────────────────────────────────────────
ID_SECTION = '''
<!-- ═══════════════ STUDIO (new in 4.1) ═══════════════ -->
<section class="sec sec-alt" id="studio">
  <div class="wrap">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">Baru di 4.1</span>
      <h2 class="h2">Studio: atur tiap monitor sendiri-sendiri</h2>
      <p class="lead">
        Semua efek di bawah dikerjakan GPU di compositor. Tidak ada frame yang
        disalin ke RAM, tidak ada resolusi yang diturunkan, dan decoder video
        tidak disentuh sama sekali &mdash; jadi biaya RAM-nya nol.
      </p>
    </div>

    <div class="grid grid-3">
      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>
        </div>
        <h3 class="h3">Koreksi warna</h3>
        <p>
          Kecerahan, kontras, saturasi, hue, dan gamma &mdash; masing-masing
          monitor punya nilainya sendiri. Geser slider, wallpaper di desktop
          langsung berubah tanpa perlu restart.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><path d="M4 6h16v12H4z"/><path d="M8 10h8M8 14h5"/></svg>
        </div>
        <h3 class="h3">Delapan filter siap pakai</h3>
        <p>
          Hitam putih, sepia, dingin, hangat, vivid, noir, dan dream. Filter
          bisa digabung dengan koreksi warna di atas, jadi hasilnya bukan
          sekadar preset yang kaku.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M5 8l7-5 7 5"/><path d="M5 16l7 5 7-5"/></svg>
        </div>
        <h3 class="h3">Flip &amp; framing</h3>
        <p>
          Balik kiri-kanan atau atas-bawah, pilih mode pas (penuh, utuh,
          regang, atau ukuran asli), lalu atur zoom dan geser posisinya
          supaya bagian penting tidak terpotong.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/></svg>
        </div>
        <h3 class="h3">HDR &amp; tone mapping</h3>
        <p>
          Roll-off highlight dan exposure dihitung sebagai kurva nada di GPU.
          Berguna untuk wallpaper yang bagian terangnya pecah, tanpa mengubah
          warna bagian gelapnya.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><rect x="3" y="6" width="12" height="12" rx="1.5"/><rect x="16" y="6" width="5" height="12" rx="1.5"/><path d="M15 12h1"/></svg>
        </div>
        <h3 class="h3">Wallpaper menyambung</h3>
        <p>
          Satu video yang sama dibagi ke beberapa monitor yang bersebelahan,
          jadi gambar lebarnya terlihat sebagai satu gambar utuh, bukan
          potongan yang diulang di tiap layar.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2"/><path d="M9 2h6"/></svg>
        </div>
        <h3 class="h3">Timer desktop</h3>
        <p>
          Hitung mundur, jam, atau stopwatch, mengambang di atas wallpaper.
          Empat bentuk, sembilan posisi, ukuran dan transparansi bebas.
          Tidak muncul di Alt+Tab dan klik tetap menembus ke desktop.
        </p>
      </article>
    </div>

    <div class="grid grid-2" style="margin-top:22px">
      <article class="card" data-reveal>
        <h3 class="h3">Kecepatan playback</h3>
        <p>
          Dari 0,25&times; sampai 4&times;, plus mode ping-pong yang memutar
          maju lalu mundur alih-alih melompat ke awal. Cocok untuk wallpaper
          yang gerakannya terlalu cepat atau terlalu kaku.
        </p>
      </article>
      <article class="card" data-reveal>
        <h3 class="h3">Tetap ringan</h3>
        <p>
          Semua di atas berjalan di GPU tanpa menyalin frame ke RAM. Saat
          wallpaper dihentikan, halaman-nya dikembalikan ke mode hemat memori
          secara otomatis, dan dinaikkan lagi begitu diminta bekerja.
        </p>
      </article>
    </div>
  </div>
</section>
'''

# ── English ──────────────────────────────────────────────────────────────────
EN_SECTION = '''
<!-- ═══════════════ STUDIO (new in 4.1) ═══════════════ -->
<section class="sec sec-alt" id="studio">
  <div class="wrap">
    <div class="sec-head" data-reveal>
      <span class="eyebrow">New in 4.1</span>
      <h2 class="h2">Studio: tune each display on its own</h2>
      <p class="lead">
        Everything below is GPU work in the compositor. No frame is copied into
        system RAM, no resolution is reduced, and the video decoder is never
        touched &mdash; so the RAM cost is zero.
      </p>
    </div>

    <div class="grid grid-3">
      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg>
        </div>
        <h3 class="h3">Colour correction</h3>
        <p>
          Brightness, contrast, saturation, hue and gamma &mdash; each display
          keeps its own values. Move a slider and the wallpaper on the desktop
          changes immediately, with no restart.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><path d="M4 6h16v12H4z"/><path d="M8 10h8M8 14h5"/></svg>
        </div>
        <h3 class="h3">Eight ready filters</h3>
        <p>
          Grayscale, sepia, cool, warm, vivid, noir and dream. A filter stacks
          with the colour controls above, so the result is not a rigid preset.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M5 8l7-5 7 5"/><path d="M5 16l7 5 7-5"/></svg>
        </div>
        <h3 class="h3">Flip and framing</h3>
        <p>
          Mirror horizontally or vertically, pick a fit mode (cover, contain,
          stretch, or original size), then set zoom and pan so the part that
          matters is not cropped away.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/></svg>
        </div>
        <h3 class="h3">HDR and tone mapping</h3>
        <p>
          Highlight roll-off and exposure computed as a tone curve on the GPU.
          For wallpapers whose bright areas clip, without shifting the shadows.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><rect x="3" y="6" width="12" height="12" rx="1.5"/><rect x="16" y="6" width="5" height="12" rx="1.5"/><path d="M15 12h1"/></svg>
        </div>
        <h3 class="h3">Stretched wallpaper</h3>
        <p>
          One video split across adjacent monitors, so a wide picture reads as
          a single continuous image instead of the same crop repeated on every
          screen.
        </p>
      </article>

      <article class="card" data-reveal>
        <div class="card-ico">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2"/><path d="M9 2h6"/></svg>
        </div>
        <h3 class="h3">Desktop timer</h3>
        <p>
          A countdown, a clock, or a stopwatch, floating over the wallpaper.
          Four shapes, nine positions, any size and opacity. It stays out of
          Alt+Tab and clicks pass straight through to the desktop.
        </p>
      </article>
    </div>

    <div class="grid grid-2" style="margin-top:22px">
      <article class="card" data-reveal>
        <h3 class="h3">Playback rate</h3>
        <p>
          From 0.25&times; to 4&times;, plus a ping-pong mode that plays forward
          then backward instead of jumping to the start. For wallpapers whose
          motion is too fast, or too rigid.
        </p>
      </article>
      <article class="card" data-reveal>
        <h3 class="h3">Still light</h3>
        <p>
          All of the above runs on the GPU without copying frames into RAM.
          When a wallpaper is stopped its page is returned to a low-memory
          state automatically, and raised again the moment it is asked to work.
        </p>
      </article>
    </div>
  </div>
</section>
'''

# Insert before the performance section, which follows features on both pages.
ANCHORS = {
    'site/index.html': ('<!-- ═══════════════ PERFORMANCE ═══════════════ -->', ID_SECTION),
    'site/en/index.html': ('<!-- ═══════════════ PERFORMANCE ═══════════════ -->', EN_SECTION),
}

for path, (anchor, section) in ANCHORS.items():
    p = Path(path)
    if not p.exists():
        print('  MISSING %s' % path)
        continue
    with p.open(encoding='utf-8', newline='') as handle:
        text = handle.read()
    if 'id="studio"' in text:
        print('  %s already has the studio section' % path)
        continue
    if anchor not in text:
        print('  %s: anchor not found - inserting before #performance by line search' % path)
        # Fall back to the section tag itself.
        marker = '<section class="sec sec-alt" id="performance">'
        if marker not in text:
            print('  %s: performance section not found either; skipped' % path)
            continue
        text = text.replace(marker, section.strip() + '\n\n' + marker, 1)
    else:
        text = text.replace(anchor, section.strip() + '\n\n' + anchor, 1)
    with p.open('w', encoding='utf-8', newline='') as handle:
        handle.write(text)
    print('  %s: studio section added (%d -> %d bytes)' % (path, len(text) - len(section), len(text)))
