/* Tela de novo orçamento / edição */
(function () {
  const { $, esc, num, brl, toast, abrirModal, fecharModal, getJSON, postJSON, camposVeiculo, ligarCamposVeiculo, lerCamposVeiculo, veiculoPreenchido, teclasBusca, atraso } = App;
  const estado = JSON.parse($('#estado').textContent);
  const issBase = JSON.parse($('#iss-base').textContent);
  const marcas = JSON.parse($('#marcas').textContent);
  const mecanicos = JSON.parse($('#mecanicos').textContent);

  let cliente = estado.cliente, veiculos = estado.veiculos || [], veiculoId = estado.veiculo_id;

  /* ---------- cliente ---------- */
  function renderCliente() {
    $('#cliente_id').value = cliente ? cliente.id : '';
    $('#cliente-box').innerHTML = cliente
      ? `<div class="chip"><span><b>${esc(cliente.nome)}</b> <span class="small mut">${esc(cliente.telefone || '')}</span></span><button type="button" class="sm" id="trocar">Trocar</button></div>`
      : `<div class="ac"><input id="cli-busca" autocomplete="off" placeholder="Digite nome, telefone, CPF ou placa"><div class="acl" id="cli-res"></div></div>`;
    if (cliente) $('#trocar').onclick = () => { cliente = null; veiculos = []; veiculoId = null; renderCliente(); renderVeiculos(); $('#cli-busca').focus(); };
    else {
      const inp = $('#cli-busca');
      teclasBusca(inp);
      inp.addEventListener('input', atraso(buscarCliente, 200));
    }
  }
  async function buscarCliente() {
    const q = $('#cli-busca').value.trim(), box = $('#cli-res');
    if (q.length < 2) { box.innerHTML = ''; return; }
    const j = await getJSON('/api/clientes/?q=' + encodeURIComponent(q));
    box.innerHTML = j.resultados.map((c, k) => `<button type="button" class="aci${k ? '' : ' on'}" data-k="${k}"><span><b>${esc(c.nome)}</b><span class="small mut">${esc(c.telefone)}${c.documento ? ' · ' + esc(c.documento) : ''}</span></span><span class="small mut" style="text-align:right">${c.veiculos.map(v => esc(v.placa || v.texto)).join('<br>')}</span></button>`).join('')
      + `<button type="button" class="aci add" data-novo>+ Cadastrar novo cliente${j.resultados.length ? '' : ': nenhum encontrado'}</button>`;
    box.querySelectorAll('[data-k]').forEach(b => b.onclick = () => {
      const c = j.resultados[+b.dataset.k];
      cliente = { id: c.id, nome: c.nome, telefone: c.telefone }; veiculos = c.veiculos;
      veiculoId = c.veiculo_encontrado || (veiculos.length === 1 ? veiculos[0].id : null);
      renderCliente(); renderVeiculos();
    });
    box.querySelector('[data-novo]').onclick = () => novoCliente(q);
  }
  function novoCliente(q) {
    abrirModal('Novo cliente', `<div class="f"><label class="w2">Nome / razão social *<input id="n-nome"></label><label>Telefone / WhatsApp<input id="n-tel" inputmode="tel"></label><label>CPF / CNPJ<input id="n-doc"></label></div>
      <h3 style="margin:16px 0 8px">Veículo</h3>${camposVeiculo(marcas)}`,
      '<button type="button" data-fechar>Cancelar</button><button type="button" class="pri" id="salvar-cli">Salvar cliente</button>');
    ligarCamposVeiculo();
    const limpo = q.replace(/[^a-zA-Z0-9]/g, '');
    if (/^[a-zA-Z]{3}[0-9][a-zA-Z0-9][0-9]{2}$/.test(limpo)) $('#v-placa').value = limpo.toUpperCase();
    else if (/^[0-9()\s.-]+$/.test(q)) $('#n-tel').value = q; else $('#n-nome').value = q;
    $('#salvar-cli').onclick = async () => {
      const v = lerCamposVeiculo();
      const dados = { nome: $('#n-nome').value.trim(), telefone: $('#n-tel').value.trim(), documento: $('#n-doc').value.trim(), ...(veiculoPreenchido(v) ? v : {}) };
      if (!dados.nome) { toast('Informe o nome'); return; }
      try {
        const j = await postJSON('/api/clientes/novo/', dados);
        cliente = j.cliente; veiculos = j.veiculos; veiculoId = j.veiculo_id;
        fecharModal(); renderCliente(); renderVeiculos(); toast('Cliente cadastrado');
      } catch (e) { toast(e.message); }
    };
  }

  /* ---------- veículo ---------- */
  function renderVeiculos() {
    const s = $('#veiculo_id');
    s.disabled = !cliente; $('#btn-veiculo').disabled = !cliente;
    if (!cliente) { s.innerHTML = '<option value="">Escolha o cliente</option>'; return; }
    s.innerHTML = `<option value="">${veiculos.length ? 'Selecione' : 'Nenhum veículo, inclua ao lado'}</option>` +
      veiculos.map(v => `<option value="${v.id}"${v.id === veiculoId ? ' selected' : ''}>${esc(v.texto)}</option>`).join('');
  }
  $('#veiculo_id').addEventListener('change', e => { veiculoId = +e.target.value || null; });
  $('#btn-veiculo').onclick = () => {
    if (!cliente) return;
    abrirModal('Incluir veículo de ' + esc(cliente.nome), camposVeiculo(marcas), '<button type="button" data-fechar>Cancelar</button><button type="button" class="pri" id="salvar-vei">Salvar veículo</button>');
    ligarCamposVeiculo();
    $('#salvar-vei').onclick = async () => {
      const v = lerCamposVeiculo();
      if (!veiculoPreenchido(v)) { toast('Informe marca e modelo'); return; }
      try {
        const j = await postJSON(`/api/clientes/${cliente.id}/veiculos/`, v);
        veiculos.push(j.veiculo); veiculoId = j.veiculo.id; fecharModal(); renderVeiculos(); toast('Veículo incluído');
      } catch (e) { toast(e.message); }
    };
  };

  /* ---------- itens: um quadro por mecânico ---------- */
  const MAX_GRUPOS = 2;
  const opcoesMec = sel => '<option value="">Selecione o mecânico</option>' + mecanicos
    .filter(m => m.ativo || m.id === sel)
    .map(m => `<option value="${m.id}"${m.id === sel ? ' selected' : ''}>${esc(m.nome)}</option>`).join('');
  const novoItem = (x = {}) => ({ tipo: x.tipo || 'servico', descricao: x.descricao || '', quantidade: x.quantidade ?? 1, preco_unitario: x.preco_unitario ?? 0 });

  // monta os quadros a partir dos itens salvos (agrupa pelo mecânico de cada item)
  let grupos = [];
  (() => {
    const principal = +$('#mecanico_principal').value || null;
    const porMec = new Map();
    (estado.itens || []).forEach(i => {
      const m = i.mecanico_id ? +i.mecanico_id : principal;
      if (!porMec.has(m)) porMec.set(m, []);
      porMec.get(m).push(novoItem(i));
    });
    if (porMec.has(principal)) { grupos.push({ mecanico_id: principal, itens: porMec.get(principal) }); porMec.delete(principal); }
    porMec.forEach((itens, m) => grupos.push({ mecanico_id: m, itens }));
    if (!grupos.length) grupos.push({ mecanico_id: principal, itens: [] });
  })();

  const todosItens = () => grupos.flatMap(g => g.itens);

  function renderGrupos() {
    $('#grupos').innerHTML = grupos.map((g, gi) => `
      <div class="grupo" data-g="${gi}">
        <div class="grupo-topo">
          <label>${grupos.length > 1 ? `Mecânico ${gi + 1}` : 'Mecânico'}<select data-g="${gi}" data-campo="mecanico">${opcoesMec(g.mecanico_id)}</select></label>
          ${gi > 0 ? `<button type="button" class="sm del" data-rmg="${gi}">Remover este mecânico</button>` : ''}
        </div>
        <div class="bar" style="align-items:flex-end;margin-bottom:8px"><div style="flex:3 1 240px"><span class="lb">Buscar peça ou serviço</span>
          <div class="ac"><input class="busca-item" data-g="${gi}" autocomplete="off" placeholder="Ex.: pastilha, alinhamento, óleo"><div class="acl"></div></div></div>
          <button type="button" data-avulso-g="${gi}">+ Item avulso</button></div>
        <div class="scroll"><table class="itens-tab"><thead><tr><th>Descrição</th><th>Tipo</th><th class="r" style="width:90px">Qtd</th><th class="r" style="width:130px">Unitário (R$)</th><th class="r">Total</th><th></th></tr></thead>
        <tbody>${linhas(g, gi)}</tbody></table></div>
        ${grupos.length > 1 ? `<div class="grupo-sub">Subtotal deste mecânico: <b data-sub="${gi}">${brl(subtotal(g))}</b></div>` : ''}
      </div>`).join('');
    $('#btn-grupo').style.display = grupos.length >= MAX_GRUPOS ? 'none' : '';
    document.querySelectorAll('.busca-item').forEach(ligarBusca);
    totais();
  }
  function linhas(g, gi) {
    if (!g.itens.length) return '<tr><td colspan="6" class="empty">Nenhum item ainda. Busque acima ou adicione um item avulso.</td></tr>';
    return g.itens.map((i, k) => `<tr>
      <td class="c-desc" data-l="Descrição"><input data-g="${gi}" data-i="${k}" data-f="descricao" value="${esc(i.descricao)}" placeholder="Descrição" maxlength="150"></td>
      <td class="c-tipo" data-l="Tipo"><select data-g="${gi}" data-i="${k}" data-f="tipo"><option value="peca"${i.tipo === 'peca' ? ' selected' : ''}>Peça</option><option value="servico"${i.tipo === 'servico' ? ' selected' : ''}>Serviço</option></select></td>
      <td class="c-qtd" data-l="Qtd"><input data-g="${gi}" data-i="${k}" data-f="quantidade" inputmode="numeric" maxlength="2" value="${esc(String(parseInt(num(i.quantidade)) || 1))}" style="text-align:right"></td>
      <td class="c-preco" data-l="Unitário (R$)"><input data-g="${gi}" data-i="${k}" data-f="preco_unitario" inputmode="decimal" maxlength="9" placeholder="0,00" value="${num(i.preco_unitario) ? esc(String(i.preco_unitario).replace('.', ',')) : ''}" style="text-align:right"></td>
      <td class="r c-total" data-lt="${gi}-${k}">${brl(num(i.quantidade) * num(i.preco_unitario))}</td>
      <td class="c-rm"><button type="button" class="sm del" data-rm="${gi}-${k}" aria-label="Remover">✕</button></td></tr>`).join('');
  }
  const subtotal = g => g.itens.reduce((a, i) => a + num(i.quantidade) * num(i.preco_unitario), 0);
  function totais() {
    let pc = 0, sv = 0;
    todosItens().forEach(i => { const v = num(i.quantidade) * num(i.preco_unitario); i.tipo === 'peca' ? pc += v : sv += v; });
    const sub = pc + sv, pct = num($('#iss').value), iss = Math.round((issBase === 'servicos' ? sv : sub) * pct) / 100;
    $('#totais').innerHTML = `<div><span>Peças</span><span>${brl(pc)}</span></div><div><span>Serviços</span><span>${brl(sv)}</span></div><div><span>Subtotal</span><b>${brl(sub)}</b></div><div><span>ISS ${esc($('#iss').value)}% ${issBase === 'servicos' ? '(só serviços)' : ''}</span><span>${brl(iss)}</span></div><div class="big"><span>Total</span><span>${brl(sub + iss)}</span></div>`;
    grupos.forEach((g, gi) => { const el = document.querySelector(`[data-sub="${gi}"]`); if (el) el.textContent = brl(subtotal(g)); });
  }

  // Limites: quantidade até 99 (2 dígitos) e preço até 999.999,99 (6 dígitos antes da vírgula)
  function limitar(t) {
    if (t.dataset.f === 'quantidade') t.value = t.value.replace(/\D/g, '').slice(0, 2);
    if (t.dataset.f === 'preco_unitario') {
      const v = t.value.replace(/\./g, ',').replace(/[^\d,]/g, '');
      const p = v.indexOf(',');
      t.value = p < 0 ? v.slice(0, 6) : v.slice(0, p).slice(0, 6) + ',' + v.slice(p + 1).replace(/,/g, '').slice(0, 2);
    }
  }
  const grp = $('#grupos');
  grp.addEventListener('input', e => {
    const t = e.target; if (t.dataset.i === undefined || t.dataset.f === 'tipo') return;
    limitar(t);
    const i = grupos[+t.dataset.g].itens[+t.dataset.i]; i[t.dataset.f] = t.value;
    const lt = document.querySelector(`[data-lt="${t.dataset.g}-${t.dataset.i}"]`); if (lt) lt.textContent = brl(num(i.quantidade) * num(i.preco_unitario));
    totais();
  });
  // ao tocar em quantidade ou preço, seleciona o valor: o que for digitado já substitui
  grp.addEventListener('focusin', e => {
    const t = e.target;
    if (t.dataset.f === 'quantidade' || t.dataset.f === 'preco_unitario') setTimeout(() => { try { t.select(); } catch (er) {} }, 0);
  });
  grp.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.f === 'tipo') { grupos[+t.dataset.g].itens[+t.dataset.i].tipo = t.value; totais(); }
    if (t.dataset.campo === 'mecanico') grupos[+t.dataset.g].mecanico_id = +t.value || null;
  });
  grp.addEventListener('click', e => {
    const rm = e.target.closest('[data-rm]');
    if (rm) { const [gi, k] = rm.dataset.rm.split('-').map(Number); grupos[gi].itens.splice(k, 1); renderGrupos(); return; }
    const rmg = e.target.closest('[data-rmg]');
    if (rmg) {
      const gi = +rmg.dataset.rmg;
      if (grupos[gi].itens.length) { grupos[0].itens.push(...grupos[gi].itens); toast('Os itens foram para o primeiro mecânico'); }
      grupos.splice(gi, 1); renderGrupos(); return;
    }
    const av = e.target.closest('[data-avulso-g]');
    if (av) { const gi = +av.dataset.avulsoG; grupos[gi].itens.push(novoItem({ tipo: 'peca' })); renderGrupos(); document.querySelector(`[data-g="${gi}"][data-i="${grupos[gi].itens.length - 1}"][data-f="descricao"]`).focus(); }
  });
  $('#btn-grupo').onclick = () => {
    if (grupos.length >= MAX_GRUPOS) return;
    grupos.push({ mecanico_id: null, itens: [] }); renderGrupos();
    document.querySelector(`select[data-g="${grupos.length - 1}"][data-campo="mecanico"]`).focus();
  };
  $('#iss').addEventListener('input', totais);

  function adicionar(gi, item, focarPreco) {
    grupos[gi].itens.push(novoItem(item)); renderGrupos();
    const k = grupos[gi].itens.length - 1;
    if (focarPreco) document.querySelector(`[data-g="${gi}"][data-i="${k}"][data-f="preco_unitario"]`).select();
    else document.querySelector(`.busca-item[data-g="${gi}"]`).focus();
  }
  function ligarBusca(input) {
    const gi = +input.dataset.g, box = input.nextElementSibling;
    teclasBusca(input);
    input.addEventListener('input', atraso(async () => {
      const q = input.value.trim();
      if (!q) { box.innerHTML = ''; return; }
      const j = await getJSON('/api/catalogo/?q=' + encodeURIComponent(q));
      box.innerHTML = j.resultados.map((x, k) => `<button type="button" class="aci${k ? '' : ' on'}" data-k="${k}"><span>${esc(x.descricao)} <span class="tipo t-${x.tipo}">${x.tipo === 'peca' ? 'Peça' : 'Serviço'}</span></span><b>${brl(x.preco)}</b></button>`).join('')
        + `<button type="button" class="aci add" data-avulso>+ Adicionar "${esc(q)}" como item avulso</button>`;
      box.querySelectorAll('[data-k]').forEach(b => b.onclick = () => { const x = j.resultados[+b.dataset.k]; adicionar(gi, { tipo: x.tipo, descricao: x.descricao, quantidade: 1, preco_unitario: x.preco }); });
      box.querySelector('[data-avulso]').onclick = () => adicionar(gi, { tipo: 'peca', descricao: q, quantidade: 1, preco_unitario: 0 }, true);
    }, 150));
  }

  /* ---------- envio ---------- */
  $('#form-pedido').addEventListener('submit', e => {
    if (!cliente) { e.preventDefault(); toast('Selecione o cliente'); return; }
    const validos = [];
    grupos.forEach(g => g.itens.forEach(i => { if (String(i.descricao).trim()) validos.push({ ...i, mecanico_id: g.mecanico_id }); }));
    if (!validos.length) { e.preventDefault(); toast('Adicione pelo menos um item'); return; }
    if (grupos.length > 1 && grupos[0].mecanico_id && grupos[0].mecanico_id === grupos[1].mecanico_id) { e.preventDefault(); toast('Os dois quadros estão com o mesmo mecânico'); return; }
    if (validos.some(i => { const q = num(i.quantidade); return q < 1 || q > 99 || q % 1; })) { e.preventDefault(); toast('Quantidade deve ser de 1 a 99'); return; }
    if (validos.some(i => num(i.preco_unitario) < 0 || num(i.preco_unitario) > 999999.99)) { e.preventDefault(); toast('Preço máximo: R$ 999.999,99'); return; }
    $('#mecanico_principal').value = grupos[0].mecanico_id || '';
    $('#itens_json').value = JSON.stringify(validos.map(i => ({ ...i, quantidade: num(i.quantidade), preco_unitario: num(i.preco_unitario) })));
  });
  // Enter dentro de um campo não envia o formulário sem querer
  $('#form-pedido').addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.tagName === 'INPUT') e.preventDefault(); });

  renderCliente(); renderVeiculos(); renderGrupos();
})();
