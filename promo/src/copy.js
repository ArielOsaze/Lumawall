// copy.js — every word the promo draws, in both languages.
//
// ── why this file exists ─────────────────────────────────────────────────────
//
// The promo was written with its Indonesian copy inline in each scene. Adding English
// that way would have meant two copies of every scene, which drift: the layout gets
// fixed in one and not the other, and nothing fails - one of the two renders is just
// quietly wrong.
//
// So the copy lives here, keyed, and the scenes read it. The renderer picks a language
// once (`window.__lang`) and every scene follows.
//
// ── how to write an entry ────────────────────────────────────────────────────
//
// The keys are the Indonesian strings, verbatim. That is deliberate: it means a scene
// can be converted to `t('...')` one line at a time and the piece keeps rendering, and
// it means a missing translation is visible as the Indonesian text rather than as a
// blank or a key name.
//
// The English is not a literal translation. The note that prompted this work was that
// the Indonesian copy reads badly - so the English is written as English, with the
// same claim in the same space. Where a line is a headline that has to fit a fixed
// box, the English is short enough to fit it; where it is body copy, it reads as a
// sentence a person would say.
//
// ── what must NOT be translated ──────────────────────────────────────────────
//
// Numbers, units, product names, format names and file extensions. `2.4%`, `4K`,
// `DXVA2`, `HEVC 10-bit`, `1920×1080`, `Windows 11`, `Display 1`, `PAUSED`, `PLAYING`.
// A translator that localises `1920×1080` into words has broken a specification.

export const ID = {
  // ── hook ──
  'Wallpaper hidup di desktop Windows — diproses chip grafis, bukan CPU.':
    'Wallpaper hidup di desktop Windows — diproses chip grafis, bukan CPU.',
  'Windows 10 / 11': 'Windows 10 / 11',
  '5.000+ wallpaper': '5.000+ wallpaper',
  'Pause per monitor': 'Pause per monitor',

  // ── problem ──
  'Masalahnya': 'Masalahnya',
  'Wallpaper hidup': 'Wallpaper hidup',
  'biasanya makan': 'biasanya makan',
  'CPU.': 'CPU.',
  'Animasi diproses di prosesor, laptop jadi panas, kipas berisik, baterai cepat habis.':
    'Animasi diproses di prosesor, laptop jadi panas, kipas berisik, baterai cepat habis.',
  'Task Manager — CPU': 'Task Manager — CPU',
  'Wallpaper engine': 'Wallpaper engine',
  '1 proses · 12 utas': '1 proses · 12 utas',
  'Browser': 'Browser',
  'Explorer': 'Explorer',
  'Spotify': 'Spotify',

  // ── browse ──
  'Katalog': 'Katalog',
  '5.000+ wallpaper': '5.000+ wallpaper',
  'cari, filter, unduh — semuanya di dalam aplikasi':
    'cari, filter, unduh — semuanya di dalam aplikasi',

  // ── apply ──
  'Terapkan': 'Terapkan',
  'Pilih, klik,': 'Pilih, klik,',
  'langsung ganti.': 'langsung ganti.',
  'Tanpa keluar dari aplikasi, tanpa atur file manual.':
    'Tanpa keluar dari aplikasi, tanpa atur file manual.',
  'Diterapkan ke Display 1': 'Diterapkan ke Display 1',
  'Sedang dipakai': 'Sedang dipakai',

  // ── multi ──
  'Multi-monitor': 'Multi-monitor',
  'Tiap layar, pengaturannya sendiri.': 'Tiap layar, pengaturannya sendiri.',
  'Display 1': 'Display 1',
  'Display 2': 'Display 2',
  'Display 3': 'Display 3',

  // ── pause ──
  'Pause': 'Pause',
  'Berhenti tanpa': 'Berhenti tanpa',
  'menutup apa pun.': 'menutup apa pun.',
  'Wallpaper yang berat tidak perlu dihapus — cukup dijeda saat kamu butuh tenaganya.':
    'Wallpaper yang berat tidak perlu dihapus — cukup dijeda saat kamu butuh tenaganya.',
  'Wallpaper dijeda — aplikasi tetap jalan': 'Wallpaper dijeda — aplikasi tetap jalan',
  'PLAYING': 'PLAYING',
  'PAUSED': 'PAUSED',

  // ── gpu ──
  'Arsitektur': 'Arsitektur',
  'Didekode di': 'Didekode di',
  ', bukan di CPU.': ', bukan di CPU.',
  'GPU': 'GPU',
  'CPU': 'CPU',
  'dekode · komposit · tampil': 'dekode · komposit · tampil',
  'hampir tidak tersentuh': 'hampir tidak tersentuh',
  'PEMAKAIAN CPU': 'PEMAKAIAN CPU',
  'FRAME RATE': 'FRAME RATE',
  'RESOLUSI': 'RESOLUSI',
  'fps': 'fps',
  'K': 'K',

  // ── perf ──
  'Hasil': 'Hasil',
  'Beban CPU, diukur pada animasi yang sama.':
    'Beban CPU, diukur pada animasi yang sama.',
  'Wallpaper engine biasa': 'Wallpaper engine biasa',
  'LumaWall (GPU)': 'LumaWall (GPU)',
  '1920×1080 · 60 fps · animasi 4K yang sama':
    '1920×1080 · 60 fps · animasi 4K yang sama',
  'diukur di Windows 11, Ryzen 5': 'diukur di Windows 11, Ryzen 5',

  // ── quality ──
  'Kualitas': 'Kualitas',
  'Resolusi asli,': 'Resolusi asli,',
  'tanpa dikompres ulang.': 'tanpa dikompres ulang.',
  'File kamu diputar apa adanya lewat dekoder perangkat keras — tidak di-encode lagi, tidak diperkecil.':
    'File kamu diputar apa adanya lewat dekoder perangkat keras — tidak di-encode lagi, tidak diperkecil.',
  'RESOLUSI': 'RESOLUSI',
  'BITRATE': 'BITRATE',
  'KODEK': 'KODEK',

  // ── library ──
  'Pustaka': 'Pustaka',
  'Ribuan wallpaper,': 'Ribuan wallpaper,',
  'semuanya hidup.': 'semuanya hidup.',
  'Setiap pratinjau di pustaka berjalan sungguhan — bukan gambar diam.':
    'Setiap pratinjau di pustaka berjalan sungguhan — bukan gambar diam.',
  // The count on its own, for the stat row - where it is the figure and 'wallpaper'
  // is the label under it, rather than the one-line '5.000+ wallpaper' elsewhere.
  '5.000+': '5.000+',
  'wallpaper': 'wallpaper',
  'siap pakai': 'siap pakai',
  'langganan': 'langganan',

  // ── close ──
  'Wallpaper hidup, tanpa membebani komputer.':
    'Wallpaper hidup, tanpa membebani komputer.',
  'Unduh gratis di lumawall.xinet.id': 'Unduh gratis di lumawall.xinet.id',
  'Gratis': 'Gratis',
  'Tanpa akun': 'Tanpa akun',
  'LumaWall': 'LumaWall',
};

export const EN = {
  // ── hook ──
  //
  // "Live wallpaper" is the phrase people actually search for and the one Wallpaper
  // Engine uses, so it leads. The second half is the claim, and it is short because it
  // sits under a 86px wordmark.
  'Wallpaper hidup di desktop Windows — diproses chip grafis, bukan CPU.':
    'Live wallpaper on your Windows desktop — decoded on the GPU, not the CPU.',
  'Windows 10 / 11': 'Windows 10 / 11',
  '5.000+ wallpaper': '5,000+ wallpapers',
  'Pause per monitor': 'Per-monitor pause',

  // ── problem ──
  //
  // The eyebrow is a label, so it stays one word. The headline keeps its three-line
  // shape because the layout is built around three lines - "Live wallpaper usually"
  // / "eats your" / "CPU." is the same rhythm as the Indonesian.
  'Masalahnya': 'The problem',
  'Wallpaper hidup': 'Live wallpaper',
  'biasanya makan': 'usually eats your',
  'CPU.': 'CPU.',
  'Animasi diproses di prosesor, laptop jadi panas, kipas berisik, baterai cepat habis.':
    'The animation runs on the processor. The laptop gets hot, the fans spin up, the battery drains.',
  'Task Manager — CPU': 'Task Manager — CPU',
  'Wallpaper engine': 'Wallpaper engine',
  '1 proses · 12 utas': '1 process · 12 threads',
  'Browser': 'Browser',
  'Explorer': 'Explorer',
  'Spotify': 'Spotify',

  // ── browse ──
  'Katalog': 'Catalog',
  '5.000+ wallpaper': '5,000+ wallpapers',
  'cari, filter, unduh — semuanya di dalam aplikasi':
    'search, filter, download — all inside the app',

  // ── apply ──
  'Terapkan': 'Apply',
  'Pilih, klik,': 'Pick one, click,',
  'langsung ganti.': 'and it changes.',
  'Tanpa keluar dari aplikasi, tanpa atur file manual.':
    'No leaving the app, no handling files by hand.',
  'Diterapkan ke Display 1': 'Applied to Display 1',
  'Sedang dipakai': 'Now playing',

  // ── multi ──
  'Multi-monitor': 'Multi-monitor',
  'Tiap layar, pengaturannya sendiri.': 'Every screen, its own setup.',
  'Display 1': 'Display 1',
  'Display 2': 'Display 2',
  'Display 3': 'Display 3',

  // ── pause ──
  'Pause': 'Pause',
  'Berhenti tanpa': 'Stop it without',
  'menutup apa pun.': 'closing anything.',
  'Wallpaper yang berat tidak perlu dihapus — cukup dijeda saat kamu butuh tenaganya.':
    'A heavy wallpaper does not have to be deleted — just pause it when you need the power back.',
  'Wallpaper dijeda — aplikasi tetap jalan': 'Wallpaper paused — the app keeps running',
  'PLAYING': 'PLAYING',
  'PAUSED': 'PAUSED',

  // ── gpu ──
  //
  // "Decoded on" + "GPU" + ", not the CPU." is split across three text nodes because
  // the GPU is a different colour - so the English has to split at a place that still
  // reads as one sentence when the colour changes.
  'Arsitektur': 'Architecture',
  'Didekode di': 'Decoded on the',
  ', bukan di CPU.': ', not the CPU.',
  'GPU': 'GPU',
  'CPU': 'CPU',
  'dekode · komposit · tampil': 'decode · composite · present',
  'hampir tidak tersentuh': 'barely touched',
  'PEMAKAIAN CPU': 'CPU LOAD',
  'FRAME RATE': 'FRAME RATE',
  'RESOLUSI': 'RESOLUTION',
  'fps': 'fps',
  'K': 'K',

  // ── perf ──
  'Hasil': 'The result',
  'Beban CPU, diukur pada animasi yang sama.':
    'CPU load, measured on the same animation.',
  'Wallpaper engine biasa': 'Typical wallpaper engine',
  'LumaWall (GPU)': 'LumaWall (GPU)',
  '1920×1080 · 60 fps · animasi 4K yang sama':
    '1920×1080 · 60 fps · the same 4K animation',
  'diukur di Windows 11, Ryzen 5': 'measured on Windows 11, Ryzen 5',

  // ── quality ──
  'Kualitas': 'Quality',
  'Resolusi asli,': 'Native resolution,',
  'tanpa dikompres ulang.': 'never re-compressed.',
  'File kamu diputar apa adanya lewat dekoder perangkat keras — tidak di-encode lagi, tidak diperkecil.':
    'Your file is played as it is, through the hardware decoder — not re-encoded, not scaled down.',
  'RESOLUSI': 'RESOLUTION',
  'BITRATE': 'BITRATE',
  'KODEK': 'CODEC',

  // ── library ──
  'Pustaka': 'Library',
  'Ribuan wallpaper,': 'Thousands of wallpapers,',
  'semuanya hidup.': 'all of them alive.',
  'Setiap pratinjau di pustaka berjalan sungguhan — bukan gambar diam.':
    'Every preview in the library is really running — not a still image.',
  '5.000+': '5,000+',
  'wallpaper': 'wallpapers',
  'siap pakai': 'ready to use',
  'langganan': 'subscriptions',

  // ── close ──
  'Wallpaper hidup, tanpa membebani komputer.':
    'Live wallpaper, without weighing down your PC.',
  'Unduh gratis di lumawall.xinet.id': 'Download free at lumawall.xinet.id',
  'Gratis': 'Free',
  'Tanpa akun': 'No account',
  'LumaWall': 'LumaWall',
};

// ── the lookup ──────────────────────────────────────────────────────────────

const TABLES = { id: ID, en: EN };

/** The language the renderer asked for, or Indonesian. */
export function currentLang() {
  if (typeof window !== 'undefined' && window.__lang && TABLES[window.__lang]) {
    return window.__lang;
  }
  return 'id';
}

/**
 * The string for a key, in the current language.
 *
 * A key with no entry falls back to the key itself, which is the Indonesian text - so
 * an untranslated line renders as the original rather than as a blank or a key name.
 * That is visible in the render and obvious in a diff, which is the point.
 */
export function t(key) {
  const table = TABLES[currentLang()] || ID;
  return table[key] !== undefined ? table[key] : key;
}

/** Every key, so a check can confirm both tables are complete. */
export function allKeys() {
  return Object.keys(ID);
}

export { TABLES };
