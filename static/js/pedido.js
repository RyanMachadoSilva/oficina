/* Tela de novo orçamento / edição */
(function () {
  const { $, esc, num, brl, toast, abrirModal, fecharModal, getJSON, postJSON, camposVeiculo, ligarCamposVeiculo, lerCamposVeiculo, veiculoPreenchido, teclasBusca, atraso } = App;
  const estado = JSON.parse($('#estado').textContent);
  const issBase = JSON.parse($('#iss-base').textContent);
  const marcas = JSON.parse($('#marcas').textContent);
  let cliente = estado.cliente, veiculos = estado.veiculos || [], veiculoId = estado.veiculo_id;
  let itens = (estado.itens || []).map(i => ({ tipo: i.tipo || 'servico', descricao: i.descricao || '', quantidade: i.quantidade ?? 1, preco_unitario: i.preco_unitario ?? 0 }));

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

  /* ---------- itens ---------- */
  function linhas() {
    const tb = $('#itens');
    if (!itens.length) { tb.innerHTML = '<tr><td colspan="6" class="empty">Nenhum item ainda. Busque acima ou adicione um item avulso.</td></tr>'; totais(); return; }
    tb.innerHTML = itens.map((i, k) => `<tr>
      <td><input data-i="${k}" data-f="descricao" value="${esc(i.descricao)}" placeholder="Descrição"></td>
      <td><select data-i="${k}" data-f="tipo"><option value="peca"${i.tipo === 'peca' ? ' selected' : ''}>Peça</option><option value="servico"${i.tipo === 'servico' ? ' selected' : ''}>Serviço</option></select></td>
      <td><input data-i="${k}" data-f="quantidade" inputmode="decimal" value="${esc(String(i.quantidade).replace('.', ','))}" style="text-align:right"></td>
      <td><input data-i="${k}" data-f="preco_unitario" inputmode="decimal" value="${esc(String(i.preco_unitario).replace('.', ','))}" style="text-align:right"></td>
      <td class="r" id="lt${k}">${brl(num(i.quantidade) * num(i.preco_unitario))}</td>
      <td><button type="button" class="sm del" data-rm="${k}" aria-label="Remover">✕</button></td></tr>`).join('');
    totais();
  }
  function totais() {
    let pc = 0, sv = 0;
    itens.forEach(i => { const v = num(i.quantidade) * num(i.preco_unitario); i.tipo === 'peca' ? pc += v : sv += v; });
    const sub = pc + sv, pct = num($('#iss').value), iss = Math.round((issBase === 'servicos' ? sv : sub) * pct) / 100;
    $('#totais').innerHTML = `<div><span>Peças</span><span>${brl(pc)}</span></div><div><span>Serviços</span><span>${brl(sv)}</span></div><div><span>Subtotal</span><b>${brl(sub)}</b></div><div><span>ISS ${esc($('#iss').value)}% ${issBase === 'servicos' ? '(só serviços)' : ''}</span><span>${brl(iss)}</span></div><div class="big"><span>Total</span><span>${brl(sub + iss)}</span></div>`;
  }
  $('#itens').addEventListener('input', e => {
    const t = e.target; if (t.dataset.i === undefined) return;
    const i = itens[+t.dataset.i]; i[t.dataset.f] = t.value;
    const lt = $('#lt' + t.dataset.i); if (lt) lt.textContent = brl(num(i.quantidade) * num(i.preco_unitario));
    totais();
  });
  $('#itens').addEventListener('change', e => { if (e.target.dataset.f === 'tipo') { itens[+e.target.dataset.i].tipo = e.target.value; totais(); } });
  $('#itens').addEventListener('click', e => { const b = e.target.closest('[data-rm]'); if (b) { itens.splice(+b.dataset.rm, 1); linhas(); } });
  $('#iss').addEventListener('input', totais);

  function adicionar(item, focarPreco) {
    itens.push(item); linhas();
    const busca = $('#item-busca'); busca.value = ''; $('#item-res').innerHTML = '';
    if (focarPreco) $(`[data-i="${itens.length - 1}"][data-f="preco_unitario"]`).select(); else busca.focus();
  }
  const buscaItem = $('#item-busca');
  teclasBusca(buscaItem);
  buscaItem.addEventListener('input', atraso(async () => {
    const q = buscaItem.value.trim(), box = $('#item-res');
    if (!q) { box.innerHTML = ''; return; }
    const j = await getJSON('/api/catalogo/?q=' + encodeURIComponent(q));
    box.innerHTML = j.resultados.map((x, k) => `<button type="button" class="aci${k ? '' : ' on'}" data-k="${k}"><span>${esc(x.descricao)} <span class="tipo t-${x.tipo}">${x.tipo === 'peca' ? 'Peça' : 'Serviço'}</span></span><b>${brl(x.preco)}</b></button>`).join('')
      + `<button type="button" class="aci add" data-avulso>+ Adicionar "${esc(q)}" como item avulso</button>`;
    box.querySelectorAll('[data-k]').forEach(b => b.onclick = () => { const x = j.resultados[+b.dataset.k]; adicionar({ tipo: x.tipo, descricao: x.descricao, quantidade: 1, preco_unitario: x.preco }); });
    box.querySelector('[data-avulso]').onclick = () => adicionar({ tipo: 'peca', descricao: q, quantidade: 1, preco_unitario: 0 }, true);
  }, 150));
  $('#btn-avulso').onclick = () => { itens.push({ tipo: 'peca', descricao: '', quantidade: 1, preco_unitario: 0 }); linhas(); $(`[data-i="${itens.length - 1}"][data-f="descricao"]`).focus(); };

  /* ---------- envio ---------- */
  $('#form-pedido').addEventListener('submit', e => {
    if (!cliente) { e.preventDefault(); toast('Selecione o cliente'); return; }
    const validos = itens.filter(i => String(i.descricao).trim());
    if (!validos.length) { e.preventDefault(); toast('Adicione pelo menos um item'); return; }
    $('#itens_json').value = JSON.stringify(validos.map(i => ({ ...i, quantidade: num(i.quantidade), preco_unitario: num(i.preco_unitario) })));
  });
  // Enter dentro de um campo não envia o formulário sem querer
  $('#form-pedido').addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.tagName === 'INPUT') e.preventDefault(); });

  renderCliente(); renderVeiculos(); linhas();
})();
