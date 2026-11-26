-- Progresso salvo na nuvem (pinhões e roupas da loja), por código de recuperação.
-- Rode no Supabase: SQL Editor > New query > cole tudo > Run.
-- A tabela fica fechada; o site só chega nela pelas duas funções abaixo, que exigem o código certo.
-- Assim ninguém consegue listar os códigos dos outros.

create table if not exists public.progresso (
  codigo text primary key check (codigo ~ '^[A-Z0-9]{12}$'),
  dados jsonb not null check (pg_column_size(dados) < 4000),
  atualizado timestamptz not null default now()
);
alter table public.progresso enable row level security; -- sem políticas: acesso direto negado
revoke all on public.progresso from anon, authenticated;

create or replace function public.salvar_progresso(p_codigo text, p_dados jsonb) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_codigo !~ '^[A-Z0-9]{12}$' then raise exception 'código inválido'; end if;
  insert into public.progresso (codigo, dados, atualizado) values (p_codigo, p_dados, now())
  on conflict (codigo) do update set dados = excluded.dados, atualizado = now();
end $$;

create or replace function public.carregar_progresso(p_codigo text) returns jsonb
language sql security definer set search_path = public stable as $$
  select dados from public.progresso where codigo = upper(regexp_replace(p_codigo, '[^A-Za-z0-9]', '', 'g'));
$$;

revoke all on function public.salvar_progresso(text, jsonb) from public;
revoke all on function public.carregar_progresso(text) from public;
grant execute on function public.salvar_progresso(text, jsonb) to anon;
grant execute on function public.carregar_progresso(text) to anon;
