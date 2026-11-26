-- Sobreviva a Curitiba! — pinhões, loja e placar validados no servidor (anti-trapaça)
-- Rode no Supabase: SQL Editor > New query > cole tudo > Run. Pode rodar de novo sem problema.
--
-- Como fecha a trapaça:
-- * os pinhões ficam no servidor; o navegador só mostra o que o servidor diz
-- * cada partida começa no servidor (hora de início) e, no fim, o servidor limita os km ao que dá para
--   andar naquele tempo (no máximo 60 m/s) e os pinhões pegos aos km andados
-- * só uma partida aberta por jogador: para "fabricar" pinhões é preciso esperar o tempo real da partida
-- * compras usam a tabela de preços do servidor
-- * o placar só aceita a distância validada de uma partida terminada

create table if not exists public.jogador (
  codigo text primary key check (codigo ~ '^[A-Z0-9]{12}$'),
  moedas integer not null default 0 check (moedas >= 0),
  tem text[] not null default array['colete:lima', 'chapeu:laranja', 'jet:classico'],
  usa jsonb not null default '{"colete":"lima","chapeu":"laranja","jet":"classico"}',
  best integer not null default 0,
  criado timestamptz not null default now()
);
create table if not exists public.partida (
  id uuid primary key default gen_random_uuid(),
  codigo text not null references public.jogador (codigo) on delete cascade,
  inicio timestamptz not null default now(),
  fim timestamptz,
  km numeric(6, 2),
  pontos integer,
  no_placar boolean not null default false
);
create index if not exists partida_codigo on public.partida (codigo, inicio desc);
create table if not exists public.preco (item text primary key, valor integer not null);
insert into public.preco (item, valor) values
  ('colete:lima', 0), ('colete:laranja', 30), ('colete:rosa', 40), ('colete:jeans', 40), ('colete:roxo', 60), ('colete:ouro', 150),
  ('chapeu:laranja', 0), ('chapeu:touca', 50), ('chapeu:capacete', 60), ('chapeu:bone', 60), ('chapeu:palha', 80), ('chapeu:coroa', 200),
  ('jet:classico', 0), ('jet:tubo', 60), ('jet:biarticulado', 80), ('jet:araucaria', 80), ('jet:noite', 120)
on conflict (item) do update set valor = excluded.valor;

-- tudo fechado: só as funções abaixo mexem nas tabelas
alter table public.jogador enable row level security;
alter table public.partida enable row level security;
alter table public.preco enable row level security;
revoke all on public.jogador, public.partida, public.preco from anon, authenticated;
-- o placar deixa de aceitar inserção direta (só pela função enviar_placar)
revoke insert on public.placar from anon;
drop policy if exists "inserir no placar" on public.placar;

create or replace function public._estado(p text) returns jsonb language sql stable security definer set search_path = public as $$
  select jsonb_build_object('moedas', moedas, 'tem', to_jsonb(tem), 'usa', usa, 'best', best) from jogador where codigo = p;
$$;

-- devolve o estado; cria o jogador na primeira vez (trazendo até 300 pinhões e o recorde que já estavam no aparelho)
create or replace function public.estado(p_codigo text, p_moedas integer default 0, p_best integer default 0) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if p_codigo !~ '^[A-Z0-9]{12}$' then raise exception 'código inválido'; end if;
  insert into jogador (codigo, moedas, best) values (p_codigo, least(greatest(coalesce(p_moedas, 0), 0), 300), least(greatest(coalesce(p_best, 0), 0), 20000))
  on conflict (codigo) do nothing;
  return _estado(p_codigo);
end $$;

create or replace function public.iniciar_partida(p_codigo text) returns uuid
language plpgsql security definer set search_path = public as $$
declare v uuid;
begin
  if not exists (select 1 from jogador where codigo = p_codigo) then raise exception 'jogador não existe'; end if;
  update partida set fim = now(), km = 0, pontos = 0 where codigo = p_codigo and fim is null; -- partida largada no meio não conta
  insert into partida (codigo) values (p_codigo) returning id into v;
  return v;
end $$;

create or replace function public.terminar_partida(p_codigo text, p_id uuid, p_km numeric, p_pinhoes integer, p_pontos integer) returns jsonb
language plpgsql security definer set search_path = public as $$
declare pt partida; seg numeric; v_km numeric; v_pin integer; v_pts integer; v_ganho integer;
begin
  select * into pt from partida where id = p_id and codigo = p_codigo for update;
  if not found or pt.fim is not null then raise exception 'partida inválida'; end if;
  seg := extract(epoch from now() - pt.inicio);
  v_km := least(greatest(coalesce(p_km, 0), 0), seg * 0.060, 250);               -- no máximo 60 m/s
  v_pin := least(greatest(coalesce(p_pinhoes, 0), 0), floor(v_km / 2.4)::int + 1); -- um pinhão a cada ~2,4 km, no máximo
  v_pts := least(greatest(coalesce(p_pontos, 0), 0), (v_km * 5000)::int + 1000);
  v_ganho := round(v_km * 3)::int + v_pin * 10;
  update partida set fim = now(), km = round(v_km, 2), pontos = v_pts where id = p_id;
  update jogador set moedas = moedas + v_ganho, best = greatest(best, v_pts) where codigo = p_codigo;
  return _estado(p_codigo) || jsonb_build_object('ganho', v_ganho, 'km', round(v_km, 2));
end $$;

create or replace function public.comprar(p_codigo text, p_item text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare v integer; j jogador;
begin
  select valor into v from preco where item = p_item; if not found then raise exception 'item não existe'; end if;
  select * into j from jogador where codigo = p_codigo for update; if not found then raise exception 'jogador não existe'; end if;
  if not (p_item = any (j.tem)) then
    if j.moedas < v then raise exception 'pinhões insuficientes'; end if;
    update jogador set moedas = moedas - v, tem = array_append(tem, p_item) where codigo = p_codigo;
  end if;
  update jogador set usa = jsonb_set(usa, array[split_part(p_item, ':', 1)], to_jsonb(split_part(p_item, ':', 2))) where codigo = p_codigo;
  return _estado(p_codigo);
end $$;

create or replace function public.enviar_placar(p_codigo text, p_id uuid, p_nome text) returns void
language plpgsql security definer set search_path = public as $$
declare pt partida;
begin
  select * into pt from partida where id = p_id and codigo = p_codigo for update;
  if not found or pt.fim is null or pt.no_placar or pt.km < 0.2 then raise exception 'partida inválida'; end if;
  if char_length(btrim(p_nome)) not between 2 and 16 then raise exception 'apelido inválido'; end if;
  insert into placar (nome, km, pontos) values (btrim(p_nome), pt.km, pt.pontos);
  update partida set no_placar = true where id = p_id;
end $$;

-- o trigger do placar roda como dono da função, então continua valendo o limite de 40 por minuto
revoke all on function public._estado(text) from public, anon;
revoke all on function public.estado(text, integer, integer), public.iniciar_partida(text), public.terminar_partida(text, uuid, numeric, integer, integer),
  public.comprar(text, text), public.enviar_placar(text, uuid, text) from public;
grant execute on function public.estado(text, integer, integer), public.iniciar_partida(text), public.terminar_partida(text, uuid, numeric, integer, integer),
  public.comprar(text, text), public.enviar_placar(text, uuid, text) to anon;
