-- A laranja na cabeça vira segredo: só quem passa de 100 km numa partida ganha. O padrão é sem chapéu.
insert into public.preco (item, valor) values ('chapeu:nenhum', 0), ('chapeu:laranja', 999999)
on conflict (item) do update set valor = excluded.valor;
alter table public.jogador alter column tem set default array['colete:lima', 'chapeu:nenhum', 'jet:classico'];
alter table public.jogador alter column usa set default '{"colete":"lima","chapeu":"nenhum","jet":"classico"}';
-- quem já tinha a laranja "de graça" perde (o segredo é novo), a não ser que já tenha feito 100 km
update public.jogador j set tem = array_append(array_remove(tem, 'chapeu:laranja'), 'chapeu:nenhum'),
  usa = case when usa->>'chapeu' = 'laranja' then jsonb_set(usa, '{chapeu}', '"nenhum"') else usa end
where not exists (select 1 from public.partida p where p.codigo = j.codigo and p.km >= 100) and not ('chapeu:nenhum' = any (tem));

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
  -- segredo: 100 km numa partida libera a laranja na cabeça
  if v_km >= 100 then update jogador set tem = array_append(tem, 'chapeu:laranja') where codigo = p_codigo and not ('chapeu:laranja' = any (tem)); end if;
  return _estado(p_codigo) || jsonb_build_object('ganho', v_ganho, 'km', round(v_km, 2), 'laranja', v_km >= 100);
end $$;
