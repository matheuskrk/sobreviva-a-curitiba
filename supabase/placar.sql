-- Placar geral do Sobreviva a Curitiba!
-- Rode isto no Supabase: Dashboard > SQL Editor > New query > cole tudo > Run.
-- Depois copie, em Project Settings > API, a "Project URL" e a chave "anon public" para o PLACAR do index.html.

create table if not exists public.placar (
  id bigint generated always as identity primary key,
  nome text not null check (char_length(btrim(nome)) between 2 and 16),
  km numeric(6, 2) not null check (km > 0 and km <= 250),
  pontos integer not null check (pontos >= 0 and pontos <= 1000000),
  criado timestamptz not null default now()
);
create index if not exists placar_km on public.placar (km desc);

-- qualquer pessoa pode ler e inserir, mas ninguém pode editar ou apagar pelo site
grant select, insert on public.placar to anon;
grant usage on sequence public.placar_id_seq to anon;
alter table public.placar enable row level security;
drop policy if exists "ler placar" on public.placar;
create policy "ler placar" on public.placar for select to anon using (true);
drop policy if exists "inserir no placar" on public.placar;
create policy "inserir no placar" on public.placar for insert to anon with check (true);

-- trava contra enxurrada de envios: no máximo 40 por minuto no total
create or replace function public.placar_limite() returns trigger language plpgsql as $$
begin
  if (select count(*) from public.placar where criado > now() - interval '1 minute') >= 40 then
    raise exception 'placar ocupado, tente de novo em 1 minuto';
  end if;
  new.nome := btrim(new.nome);
  new.criado := now();
  return new;
end $$;
drop trigger if exists placar_limite on public.placar;
create trigger placar_limite before insert on public.placar for each row execute function public.placar_limite();
