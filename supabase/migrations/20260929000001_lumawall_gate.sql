-- LumaWall: pesanan, token unduhan, dan catatan percobaan unduhan.
--
-- Proyek ini KHUSUS LumaWall. Tidak ada tabel lain di sini, dan tidak ada
-- tabel LumaWall di proyek lain, supaya data penjualan LumaWall tidak pernah
-- tercampur dengan data produk lain.
--
-- Dua keputusan yang menentukan bentuk skema ini:
--
-- 1. Token unduhan disimpan sebagai SHA-256, bukan teks asli. Isi tabel yang
--    bocor karena itu tidak langsung berarti tautan unduhan yang bisa dipakai.
--
-- 2. Token terikat pada SATU alamat IP, dan pengikatan itu terjadi saat
--    pemakaian PERTAMA, bukan saat penerbitan. Pembeli sering membayar dari
--    satu jaringan (WiFi kantor, data seluler) lalu mengunduh dari jaringan
--    lain; mengunci saat penerbitan akan mengunci orang yang salah.


-- ══════════════════════════════════════════════════════════════════════════════
-- Pesanan
-- ══════════════════════════════════════════════════════════════════════════════
create table if not exists public.orders (
  id                uuid primary key default gen_random_uuid(),
  order_code        text        not null unique,
  product_code      text        not null default 'lumawall',
  nama_pembeli      text        not null,
  email_pembeli     text        not null,
  whatsapp          text,
  jumlah            integer     not null,
  status            text        not null default 'menunggu',
  catatan           text,
  sesi_pembayaran   text,
  acuan_pembayaran  text,
  trx_pembayaran    text,
  kedaluwarsa_pada  timestamptz,
  dibuat_pada       timestamptz not null default now(),
  dibayar_pada      timestamptz,
  diperbarui_pada   timestamptz
);

create index if not exists orders_code_idx on public.orders (order_code);
create index if not exists orders_status_idx on public.orders (status);
create index if not exists orders_dibuat_idx on public.orders (dibuat_pada desc);

-- Status hanya boleh salah satu dari ini. Tanpa batasan ini, salah ketik
-- ("dibayarr") membuat pesanan yang sudah lunas tidak pernah dikenali sebagai
-- lunas, dan pembeli tidak pernah mendapat tautannya.
alter table public.orders
  drop constraint if exists orders_status_check;
alter table public.orders
  add constraint orders_status_check
  check (status in ('menunggu', 'dibayar', 'gagal', 'kedaluwarsa', 'dibatalkan'));

-- Jumlah tidak boleh nol atau negatif: pesanan Rp0 yang lolos ke webhook akan
-- melewati pemeriksaan "jumlah >= harga" hanya kalau pemeriksaannya salah.
alter table public.orders
  drop constraint if exists orders_jumlah_check;
alter table public.orders
  add constraint orders_jumlah_check check (jumlah > 0);

comment on table public.orders is
  'Pesanan LumaWall. Baris dibuat sebelum pembayaran, dan status hanya naik ke dibayar lewat webhook iPaymu yang sudah diverifikasi.';


-- ══════════════════════════════════════════════════════════════════════════════
-- Token unduhan
-- ══════════════════════════════════════════════════════════════════════════════
create table if not exists public.download_tokens (
  id            uuid primary key default gen_random_uuid(),
  token_hash    text        not null unique,
  order_code    text        not null references public.orders (order_code) on delete cascade,
  product_code  text        not null default 'lumawall',
  pemilik_email text,
  bound_ip      text,
  max_uses      integer     not null default 3,
  uses          integer     not null default 0,
  kedaluwarsa   timestamptz not null default (now() + interval '72 hours'),
  dibuat_pada   timestamptz not null default now(),
  dipakai_pada  timestamptz,
  catatan       text
);

create index if not exists download_tokens_order_idx on public.download_tokens (order_code);
create index if not exists download_tokens_expiry_idx on public.download_tokens (kedaluwarsa);

alter table public.download_tokens
  drop constraint if exists download_tokens_uses_check;
alter table public.download_tokens
  add constraint download_tokens_uses_check check (uses >= 0 and uses <= max_uses);

comment on table public.download_tokens is
  'Token unduhan sekali pakai. Disimpan sebagai hash; terikat pada satu alamat IP sejak pemakaian pertama.';


-- ══════════════════════════════════════════════════════════════════════════════
-- Catatan percobaan unduhan
-- ══════════════════════════════════════════════════════════════════════════════
create table if not exists public.download_attempts (
  id           bigserial primary key,
  token_hash   text,
  ip           text,
  user_agent   text,
  hasil        text        not null,
  keterangan   text,
  dibuat_pada  timestamptz not null default now()
);

create index if not exists download_attempts_time_idx on public.download_attempts (dibuat_pada desc);

comment on table public.download_attempts is
  'Setiap percobaan unduhan, berhasil maupun ditolak. Tanpa ini, upaya bypass tidak terlihat.';


-- ══════════════════════════════════════════════════════════════════════════════
-- Produk
-- ══════════════════════════════════════════════════════════════════════════════
create table if not exists public.products (
  code        text primary key,
  nama        text    not null,
  harga       integer not null,
  max_device  integer not null default 1,
  fitur       jsonb   not null default '{}'::jsonb,
  dibuat_pada timestamptz not null default now()
);

insert into public.products (code, nama, harga, max_device, fitur)
values (
  'lumawall',
  'LumaWall',
  20000,
  1,
  '{"dynamic":true,"monitors":"unlimited","catalog":22233,"timer":true,"studio":true,"lifetime":true}'::jsonb
)
on conflict (code) do update
  set nama = excluded.nama,
      harga = excluded.harga,
      fitur = excluded.fitur;


-- ══════════════════════════════════════════════════════════════════════════════
-- Klaim token — satu-satunya jalan token bisa dipakai
-- ══════════════════════════════════════════════════════════════════════════════
--
-- Semua pemeriksaan (kedaluwarsa, sisa pemakaian, alamat IP) terjadi di dalam
-- SATU transaksi dengan SELECT ... FOR UPDATE. Itu bukan gaya penulisan, itu
-- keharusan: tanpa kunci baris, dua permintaan yang datang bersamaan sama-sama
-- membaca uses=0 dan sama-sama lolos, sehingga satu tautan terpakai melebihi
-- batasnya. Dengan kunci itu, permintaan kedua menunggu sampai yang pertama
-- selesai dan membaca nilai yang sudah diperbarui.
create or replace function public.claim_download_token(
  p_token_hash text,
  p_ip         text
)
returns table (ok boolean, alasan text, sisa integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.download_tokens%rowtype;
begin
  select * into v_row
    from public.download_tokens
   where token_hash = p_token_hash
   for update;

  if not found then
    return query select false, 'token tidak dikenal', 0;
    return;
  end if;

  if v_row.kedaluwarsa < now() then
    return query select false, 'token kedaluwarsa', 0;
    return;
  end if;

  if v_row.uses >= v_row.max_uses then
    return query select false, 'batas pemakaian tercapai', 0;
    return;
  end if;

  if v_row.bound_ip is null then
    update public.download_tokens
       set bound_ip = p_ip
     where id = v_row.id;
  elsif v_row.bound_ip <> p_ip then
    return query select false, 'token terikat ke alamat IP lain', 0;
    return;
  end if;

  update public.download_tokens
     set uses = uses + 1,
         dipakai_pada = now()
   where id = v_row.id;

  return query select true, 'ok', (v_row.max_uses - v_row.uses - 1);
end;
$$;

revoke all on function public.claim_download_token(text, text) from public, anon, authenticated;


-- ══════════════════════════════════════════════════════════════════════════════
-- Keamanan tingkat baris
-- ══════════════════════════════════════════════════════════════════════════════
--
-- RLS dinyalakan TANPA satu pun policy. Artinya: tidak ada peran yang bisa
-- membaca atau menulis tabel ini lewat API publik - termasuk anon key, yang
-- memang terlihat di kode peramban. Hanya service_role (kunci server) yang
-- melewati RLS, dan kunci itu hanya ada di environment Vercel.
alter table public.orders            enable row level security;
alter table public.download_tokens   enable row level security;
alter table public.download_attempts enable row level security;
alter table public.products          enable row level security;

revoke all on public.orders            from anon, authenticated;
revoke all on public.download_tokens   from anon, authenticated;
revoke all on public.download_attempts from anon, authenticated;
revoke all on public.products          from anon, authenticated;

grant all on public.orders            to service_role;
grant all on public.download_tokens   to service_role;
grant all on public.download_attempts to service_role;
grant all on public.products          to service_role;
grant usage, select on all sequences in schema public to service_role;


-- ══════════════════════════════════════════════════════════════════════════════
-- Pembersihan
-- ══════════════════════════════════════════════════════════════════════════════
--
-- Tanpa ini, tabel percobaan unduhan tumbuh tanpa batas. Setiap percobaan
-- ditulis (memang disengaja, supaya upaya bypass terlihat), jadi pembersihan
-- harus terjadwal, bukan mengandalkan seseorang ingat.
--
-- pg_cron tidak selalu tersedia; fungsi ini tetap berguna dipanggil manual atau
-- dari cron eksternal kalau ekstensinya tidak ada.
create or replace function public.purge_old_download_data(
  p_hari integer default 90
)
returns table (token_dihapus integer, percobaan_dihapus integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_token integer := 0;
  v_cobaan integer := 0;
begin
  delete from public.download_tokens
   where kedaluwarsa < now() - make_interval(days => p_hari);
  get diagnostics v_token = row_count;

  delete from public.download_attempts
   where dibuat_pada < now() - make_interval(days => p_hari);
  get diagnostics v_cobaan = row_count;

  return query select v_token, v_cobaan;
end;
$$;

revoke all on function public.purge_old_download_data(integer) from public, anon, authenticated;
