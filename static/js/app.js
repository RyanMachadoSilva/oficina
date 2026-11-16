/* Funções comuns a todas as telas */
window.App = (function () {
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = v => { let s = String(v ?? '').trim(); if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.'); const n = parseFloat(s); return isNaN(n) ? 0 : n; };
  const brl = v => (+v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const csrf = () => $('meta[name=csrf-token]').content;

  function toast(t) {
    const e = $('#toast'); if (!e) return;
    e.textContent = t; e.classList.add('show');
    clearTimeout(toast.h); toast.h = setTimeout(() => e.classList.remove('show'), 2400);
  }
  function abrirModal(titulo, corpo, rodape) {
    $('#modal').innerHTML = `<div class="mh"><h2>${titulo}</h2><button type="button" class="sm" data-fechar aria-label="Fechar">✕</button></div><div id="mb">${corpo}</div><div class="mf">${rodape || ''}</div>`;
    $('#ov').classList.add('open');
    const f = $('#mb input, #mb select'); if (f) setTimeout(() => f.focus(), 30);
  }
  const fecharModal = () => $('#ov') && $('#ov').classList.remove('open');

  async function getJSON(url) {
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    if (!r.ok) throw new Error('Erro ' + r.status);
    return r.json();
  }
  async function postJSON(url, dados) {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(dados) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.erro || 'Erro ao salvar');
    return j;
  }

  /* Campos de veículo (marca -> modelo), usados no novo cliente e no + Veículo */
  function camposVeiculo(marcas) {
    return `<div class="f">
      <label>Marca<select id="v-marca"><option value="">Selecione</option>${marcas.map(m => `<option value="${m.id}">${esc(m.nome)}</option>`).join('')}<option value="__n">+ Outra marca</option></select>
        <input id="v-nova-marca" placeholder="Nome da nova marca" style="display:none"></label>
      <label>Modelo<select id="v-modelo"><option value="">Escolha a marca</option></select>
        <input id="v-novo-modelo" placeholder="Nome do novo modelo" style="display:none"></label>
      <label>Ano<input id="v-ano" inputmode="numeric" maxlength="9"></label>
      <label>Placa<input id="v-placa" style="text-transform:uppercase" maxlength="8"></label>
      <label>Cor<input id="v-cor"></label></div>`;
  }
  function ligarCamposVeiculo() {
    const sm = $('#v-marca'), so = $('#v-modelo');
    sm.addEventListener('change', async () => {
      const nova = sm.value === '__n';
      $('#v-nova-marca').style.display = nova ? 'block' : 'none';
      so.style.display = nova ? 'none' : 'block';
      $('#v-novo-modelo').style.display = nova ? 'block' : 'none';
      so.innerHTML = '<option value="">Carregando...</option>';
      if (!sm.value || nova) { so.innerHTML = '<option value="">Escolha a marca</option>'; return; }
      const j = await getJSON('/api/modelos/?marca=' + sm.value);
      so.innerHTML = '<option value="">Selecione</option>' + j.modelos.map(m => `<option value="${m.id}">${esc(m.nome)}</option>`).join('') + '<option value="__n">+ Outro modelo</option>';
    });
    so.addEventListener('change', () => { $('#v-novo-modelo').style.display = so.value === '__n' ? 'block' : 'none'; });
  }
  function lerCamposVeiculo() {
    const marca = $('#v-marca').value, modelo = $('#v-modelo').value;
    return {
      marca: marca === '__n' ? '' : marca,
      nova_marca: marca === '__n' ? $('#v-nova-marca').value.trim() : '',
      modelo: modelo === '__n' ? '' : modelo,
      novo_modelo: (marca === '__n' || modelo === '__n') ? $('#v-novo-modelo').value.trim() : '',
      ano: $('#v-ano').value.trim(), placa: $('#v-placa').value.trim(), cor: $('#v-cor').value.trim(),
    };
  }
  const veiculoPreenchido = d => (d.marca || d.nova_marca) && (d.modelo || d.novo_modelo);

  async function copiar(texto, ok) {
    try { await navigator.clipboard.writeText(texto); toast(ok); }
    catch (e) { abrirModal('Copie o texto abaixo', `<textarea style="min-height:240px" readonly>${esc(texto)}</textarea>`, '<button type="button" data-fechar>Fechar</button>'); }
  }

  /* comportamentos globais */
  document.addEventListener('click', e => {
    if (e.target.closest('[data-fechar]') || e.target.id === 'ov') { fecharModal(); return; }
    const linha = e.target.closest('tr[data-href]');
    if (linha && !e.target.closest('a,button,input,select')) location.href = linha.dataset.href;
    if (!e.target.closest('.ac')) document.querySelectorAll('.acl').forEach(l => l.innerHTML = '');
    const cp = e.target.closest('[data-copiar]');
    if (cp) copiar(document.getElementById(cp.dataset.copiar).value, cp.dataset.ok || 'Copiado');
    const cf = e.target.closest('[data-confirmar]');
    if (cf && !cf.dataset.ok2) { e.preventDefault(); cf.dataset.ok2 = '1'; cf.textContent = cf.dataset.confirmar; }
  }, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharModal(); });
  document.addEventListener('change', e => { if (e.target.matches('[data-auto]')) e.target.form.submit(); });

  /* Navegação por teclado nas listas de busca (setas + Enter) */
  function teclasBusca(input) {
    input.addEventListener('keydown', e => {
      const l = input.nextElementSibling, it = [...l.querySelectorAll('.aci')];
      if (!it.length || !['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) return;
      e.preventDefault();
      let k = it.findIndex(x => x.classList.contains('on'));
      if (e.key === 'Enter') { (it[k] || it[0]).click(); return; }
      if (e.key === 'Escape') { l.innerHTML = ''; return; }
      if (it[k]) it[k].classList.remove('on');
      k = e.key === 'ArrowDown' ? Math.min(k + 1, it.length - 1) : Math.max(k - 1, 0);
      it[k].classList.add('on'); it[k].scrollIntoView({ block: 'nearest' });
    });
  }
  function atraso(fn, ms) { let h; return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); }; }

  return { $, esc, num, brl, toast, abrirModal, fecharModal, getJSON, postJSON, camposVeiculo, ligarCamposVeiculo, lerCamposVeiculo, veiculoPreenchido, copiar, teclasBusca, atraso };
})();
