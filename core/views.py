import csv
import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, ProtectedError, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ClienteForm, ItemCatalogoForm, MecanicoForm
from .models import (Cliente, HistoricoStatus, ItemCatalogo, ItemPedido, Marca, Mecanico, Modelo, Parametros,
                     Pedido, Status, TipoItem, Veiculo)
from .templatetags.oficina import brl, num


# ---------------------------------------------------------------- utilidades
QTD_MAX = 99                        # quantidade de itens iguais: até 2 dígitos
PRECO_MAX = Decimal("999999.99")    # preço unitário: até 6 dígitos antes da vírgula

def dec(valor, padrao="0"):
    """Converte texto digitado (145 / 145,50 / 1.234,56 / 145.5) em Decimal."""
    s = str(valor if valor not in (None, "") else padrao).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal(padrao)


def so_letras_numeros(s):
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def pedidos_com_itens():
    return (Pedido.objects.select_related("cliente", "veiculo__modelo__marca", "mecanico", "vendedor")
            .prefetch_related(Prefetch("itens", queryset=ItemPedido.objects.select_related("mecanico"))))


def obter_ou_criar_modelo(marca_id, modelo_id, nova_marca, novo_modelo):
    """Resolve marca/modelo vindos do formulário, criando os novos quando informados."""
    nova_marca = (nova_marca or "").strip()
    novo_modelo = (novo_modelo or "").strip()
    if nova_marca:
        marca, _ = Marca.objects.get_or_create(nome=nova_marca)
    elif str(marca_id or "").isdigit():
        marca = Marca.objects.filter(pk=marca_id).first()
    else:
        marca = None
    if not marca:
        return None
    if novo_modelo:
        modelo, _ = Modelo.objects.get_or_create(marca=marca, nome=novo_modelo)
        return modelo
    if str(modelo_id or "").isdigit():
        return Modelo.objects.filter(pk=modelo_id, marca=marca).first()
    return None


def veiculo_json(v):
    return {"id": v.id, "texto": str(v), "placa": v.placa}


# ---------------------------------------------------------------- início
@login_required
def inicio(request):
    hoje = timezone.localdate()
    pedidos = list(pedidos_com_itens().exclude(status=Status.CANCELADO))
    cont = {s: 0 for s in Status.values}
    a_receber = recebido_mes = Decimal("0")
    for p in pedidos:
        cont[p.status] += 1
        if p.status == Status.FINALIZADO:
            a_receber += p.totais()["total"]
        if p.status == Status.PAGO and p.data.year == hoje.year and p.data.month == hoje.month:
            recebido_mes += p.totais()["total"]
    return render(request, "core/inicio.html", {
        "orcamentos": cont[Status.ORCAMENTO],
        "andamento": cont[Status.APROVADO] + cont[Status.EXECUCAO],
        "a_receber": a_receber,
        "recebido_mes": recebido_mes,
        "abertos": abertos_ordenados(pedidos),
        "status_abertos": [(s, l) for s, l in Status.choices if s in ABERTOS],
    })


# Pedidos "em aberto": ainda não pagos nem cancelados, na ordem do fluxo de trabalho
ABERTOS = [Status.EXECUCAO, Status.APROVADO, Status.ORCAMENTO, Status.FINALIZADO]


def abertos_ordenados(pedidos):
    ordem = {s: i for i, s in enumerate(ABERTOS)}
    lista = [p for p in pedidos if p.status in ordem]
    lista.sort(key=lambda p: (ordem[p.status], -p.data.toordinal(), -p.sequencia))
    return lista


# ---------------------------------------------------------------- pedidos
def filtrar_pedidos(params, qs):
    f = {k: str(params.get(k, "")).strip() for k in ("q", "status", "cliente", "mecanico", "de", "ate")}
    if f["q"]:
        placa = so_letras_numeros(f["q"])
        cond = Q(numero__icontains=f["q"]) | Q(cliente__nome__icontains=f["q"])
        if placa:
            cond |= Q(veiculo__placa__icontains=placa)
        qs = qs.filter(cond)
    if f["status"]:
        qs = qs.filter(status=f["status"])
    if f["cliente"]:
        qs = qs.filter(cliente_id=f["cliente"])
    if f["mecanico"]:
        qs = qs.filter(Q(mecanico_id=f["mecanico"]) | Q(itens__mecanico_id=f["mecanico"])).distinct()
    if f["de"]:
        qs = qs.filter(data__gte=f["de"])
    if f["ate"]:
        qs = qs.filter(data__lte=f["ate"])
    return qs, f


@login_required
def pedidos(request):
    qs, f = filtrar_pedidos(request.GET, pedidos_com_itens())
    pagina = Paginator(qs, 30).get_page(request.GET.get("page"))
    cliente_sel = Cliente.objects.filter(pk=f["cliente"]).first() if f["cliente"] else None
    return render(request, "core/pedidos.html", {
        "pagina": pagina, "f": f, "status_opcoes": Status.choices,
        "mecanicos": Mecanico.objects.all(), "cliente_sel": cliente_sel,
    })


@login_required
def pedido_form(request, pk=None, duplicar_de=None):
    params = Parametros.atual()
    pedido = get_object_or_404(Pedido, pk=pk) if pk else None
    origem = pedido or (get_object_or_404(Pedido, pk=duplicar_de) if duplicar_de else None)
    erros = []

    if request.method == "POST":
        cliente = Cliente.objects.filter(pk=request.POST.get("cliente_id") or 0).first()
        veiculo = Veiculo.objects.filter(pk=request.POST.get("veiculo_id") or 0, cliente=cliente).first() if cliente else None
        mecanico = Mecanico.objects.filter(pk=request.POST.get("mecanico_id") or 0).first()
        vendedor = Mecanico.objects.filter(pk=request.POST.get("vendedor_id") or 0).first()
        ids_mecanicos = set(Mecanico.objects.values_list("pk", flat=True))
        try:
            itens = json.loads(request.POST.get("itens_json") or "[]")
        except json.JSONDecodeError:
            itens = []
        itens = [i for i in itens if str(i.get("descricao", "")).strip()]
        if not cliente:
            erros.append("Selecione o cliente.")
        if not itens:
            erros.append("Adicione pelo menos uma peça ou serviço.")
        for i in itens:
            q, p = dec(i.get("quantidade"), "1"), dec(i.get("preco_unitario"), "0")
            if q < 1 or q > QTD_MAX or q != q.to_integral_value():
                erros.append(f'Quantidade de "{str(i["descricao"])[:40]}" deve ser de 1 a {QTD_MAX}.')
            if p < 0 or p > PRECO_MAX:
                erros.append(f'Preço de "{str(i["descricao"])[:40]}" deve ser no máximo R$ 999.999,99.')
        if not erros:
            with transaction.atomic():
                novo = pedido is None
                p = pedido or Pedido(criado_por=request.user, iss_base=params.iss_base)
                p.cliente, p.veiculo, p.mecanico, p.vendedor = cliente, veiculo, mecanico, vendedor
                if novo:
                    try:
                        p.data = date.fromisoformat(request.POST.get("data", ""))
                    except ValueError:
                        p.data = timezone.localdate()
                try:
                    p.validade = date.fromisoformat(request.POST.get("validade", ""))
                except ValueError:
                    p.validade = None
                p.iss_percentual = dec(request.POST.get("iss_percentual"), str(params.iss_percentual))
                p.observacao = request.POST.get("observacao", "").strip()
                p.save()
                p.itens.all().delete()
                ItemPedido.objects.bulk_create([
                    ItemPedido(
                        pedido=p, ordem=n,
                        tipo=TipoItem.PECA if i.get("tipo") == TipoItem.PECA else TipoItem.SERVICO,
                        descricao=str(i["descricao"]).strip()[:150],
                        quantidade=dec(i.get("quantidade"), "1"),
                        preco_unitario=dec(i.get("preco_unitario"), "0"),
                        mecanico_id=(int(i["mecanico_id"]) if str(i.get("mecanico_id") or "").isdigit()
                                     and int(i["mecanico_id"]) in ids_mecanicos else None),
                    ) for n, i in enumerate(itens)
                ])
                if novo:
                    HistoricoStatus.objects.create(pedido=p, status=p.status, usuario=request.user)
            messages.success(request, f"Orçamento {p.numero} salvo.")
            return redirect("pedido_detalhe", pk=p.pk)
        # devolve o que foi digitado
        estado = {
            "cliente": {"id": cliente.id, "nome": cliente.nome, "telefone": cliente.telefone} if cliente else None,
            "veiculos": [veiculo_json(v) for v in cliente.veiculos.select_related("modelo__marca")] if cliente else [],
            "veiculo_id": veiculo.id if veiculo else None,
            "itens": itens,
        }
        valores = request.POST
    else:
        hoje = timezone.localdate()
        if origem:
            estado = {
                "cliente": {"id": origem.cliente_id, "nome": origem.cliente.nome, "telefone": origem.cliente.telefone},
                "veiculos": [veiculo_json(v) for v in origem.cliente.veiculos.select_related("modelo__marca")],
                "veiculo_id": origem.veiculo_id,
                "itens": [{"tipo": i.tipo, "descricao": i.descricao, "quantidade": str(i.quantidade.normalize()),
                           "preco_unitario": str(i.preco_unitario), "mecanico_id": i.mecanico_id}
                          for i in origem.itens.all()],
            }
            valores = {
                "mecanico_id": str(origem.mecanico_id or ""),
                "vendedor_id": str(origem.vendedor_id or ""),
                "data": (origem.data if pedido else hoje).isoformat(),
                "validade": (origem.validade.isoformat() if pedido and origem.validade
                             else (hoje + timedelta(days=params.validade_dias)).isoformat()),
                "iss_percentual": str(origem.iss_percentual.normalize()),
                "observacao": origem.observacao,
            }
        else:
            estado = {"cliente": None, "veiculos": [], "veiculo_id": None, "itens": []}
            valores = {
                "mecanico_id": "", "vendedor_id": "", "data": hoje.isoformat(),
                "validade": (hoje + timedelta(days=params.validade_dias)).isoformat(),
                "iss_percentual": str(params.iss_percentual.normalize()), "observacao": "",
            }

    return render(request, "core/pedido_form.html", {
        "pedido": pedido, "erros": erros, "valores": valores, "estado": estado,
        "mecanicos": Mecanico.objects.filter(ativo=True) | Mecanico.objects.filter(pk=(pedido.mecanico_id if pedido else 0)),
        "marcas": Marca.objects.all(),
        "mecanicos_json": [{"id": m.pk, "nome": m.nome, "ativo": m.ativo} for m in Mecanico.objects.all()],
        "iss_base": pedido.iss_base if pedido else params.iss_base,
    })


@login_required
def pedido_duplicar(request, pk):
    return pedido_form(request, duplicar_de=pk)


@login_required
def pedido_detalhe(request, pk):
    p = get_object_or_404(pedidos_com_itens().prefetch_related("historico__usuario"), pk=pk)
    t = p.totais()
    linhas = [f"*{settings.EMPRESA_NOME}*", f"Orçamento {p.numero} - {p.data:%d/%m/%Y}", p.cliente.nome]
    if p.veiculo:
        linhas.append(str(p.veiculo))
    linhas.append("")
    linhas += [f"{num(i.quantidade)}x {i.descricao} - {brl(i.total)}" for i in p.itens.all()]
    linhas += ["", f"Subtotal: {brl(t['subtotal'])}", f"ISS {num(p.iss_percentual)}%: {brl(t['iss'])}", f"*Total: {brl(t['total'])}*"]
    if p.validade:
        linhas.append(f"Válido até {p.validade:%d/%m/%Y}")
    # itens separados por mecânico (só quando mais de um mecânico trabalhou)
    grupos = {}
    for i in p.itens.all():
        mec = i.mecanico or p.mecanico
        g = grupos.setdefault(mec.pk if mec else 0, {"mecanico": mec, "itens": [], "subtotal": Decimal("0")})
        g["itens"].append(i)
        g["subtotal"] += i.total
    grupos = list(grupos.values()) if len(grupos) > 1 else []
    return render(request, "core/pedido_detalhe.html", {
        "p": p, "t": t, "grupos": grupos, "status_opcoes": Status.choices, "texto_whatsapp": "\n".join(linhas),
    })


@login_required
@require_POST
def pedido_status(request, pk):
    p = get_object_or_404(Pedido, pk=pk)
    novo = request.POST.get("status")
    if novo in Status.values and novo != p.status:
        p.status = novo
        p.save(update_fields=["status", "atualizado_em"])
        HistoricoStatus.objects.create(pedido=p, status=novo, usuario=request.user)
        messages.success(request, f"Status alterado para {p.get_status_display()}.")
    return redirect("pedido_detalhe", pk=pk)


@login_required
@require_POST
def pedido_excluir(request, pk):
    p = get_object_or_404(Pedido, pk=pk)
    if p.status in (Status.PAGO, Status.FINALIZADO):
        messages.error(request, "Pedido finalizado ou pago não pode ser excluído. Mude o status para Cancelado.")
        return redirect("pedido_detalhe", pk=pk)
    numero = p.numero
    p.delete()
    messages.success(request, f"Pedido {numero} excluído.")
    return redirect("pedidos")


# ---------------------------------------------------------------- clientes
@login_required
def clientes(request):
    q = request.GET.get("q", "").strip()
    qs = Cliente.objects.prefetch_related(Prefetch("veiculos", queryset=Veiculo.objects.select_related("modelo__marca")))
    if q:
        placa = so_letras_numeros(q)
        cond = Q(nome__icontains=q) | Q(telefone__icontains=q) | Q(documento__icontains=q)
        if placa:
            cond |= Q(veiculos__placa__icontains=placa)
        qs = qs.filter(cond).distinct()
    pagina = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "core/clientes.html", {"pagina": pagina, "q": q})


@login_required
def cliente_form(request, pk=None):
    cliente = get_object_or_404(Cliente, pk=pk) if pk else None
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == "POST" and form.is_valid():
        c = form.save()
        modelo = obter_ou_criar_modelo(request.POST.get("marca"), request.POST.get("modelo"),
                                       request.POST.get("nova_marca"), request.POST.get("novo_modelo"))
        if modelo:
            Veiculo.objects.create(cliente=c, modelo=modelo, ano=request.POST.get("ano", "").strip(),
                                   placa=request.POST.get("placa", ""), cor=request.POST.get("cor", "").strip())
        messages.success(request, "Cliente salvo.")
        if request.POST.get("continuar"):
            return redirect("cliente_editar", pk=c.pk)
        return redirect("clientes")
    veiculos = cliente.veiculos.select_related("modelo__marca") if cliente else []
    return render(request, "core/cliente_form.html", {
        "form": form, "cliente": cliente, "veiculos": veiculos, "marcas": Marca.objects.all(),
        "total_pedidos": cliente.pedidos.count() if cliente else 0,
    })


@login_required
@require_POST
def cliente_excluir(request, pk):
    c = get_object_or_404(Cliente, pk=pk)
    try:
        c.delete()
        messages.success(request, "Cliente excluído.")
        return redirect("clientes")
    except ProtectedError:
        messages.error(request, "Esse cliente tem pedidos e não pode ser excluído.")
        return redirect("cliente_editar", pk=pk)


@login_required
@require_POST
def veiculo_excluir(request, pk):
    v = get_object_or_404(Veiculo, pk=pk)
    cliente_id = v.cliente_id
    try:
        v.delete()
        messages.success(request, "Veículo removido.")
    except ProtectedError:
        messages.error(request, "Esse veículo está em pedidos e não pode ser removido.")
    return redirect("cliente_editar", pk=cliente_id)


# ---------------------------------------------------------------- mecânicos e catálogo
@login_required
def mecanicos(request):
    return render(request, "core/mecanicos.html", {"mecanicos": Mecanico.objects.all()})


@login_required
def mecanico_form(request, pk=None):
    obj = get_object_or_404(Mecanico, pk=pk) if pk else None
    form = MecanicoForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mecânico salvo.")
        return redirect("mecanicos")
    return render(request, "core/form_simples.html", {
        "form": form, "titulo": "Editar mecânico" if obj else "Novo mecânico", "voltar": "mecanicos",
        "nota": "A regra de pagamento ainda vai ser definida. Quando estiver, o sistema calcula quanto cada mecânico tem a receber.",
    })


@login_required
def catalogo(request):
    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    qs = ItemCatalogo.objects.all()
    if q:
        for palavra in q.split():
            qs = qs.filter(descricao__icontains=palavra)
    if tipo:
        qs = qs.filter(tipo=tipo)
    pagina = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "core/catalogo.html", {"pagina": pagina, "q": q, "tipo": tipo, "tipos": TipoItem.choices})


@login_required
def catalogo_form(request, pk=None):
    obj = get_object_or_404(ItemCatalogo, pk=pk) if pk else None
    form = ItemCatalogoForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Item salvo.")
        return redirect("catalogo")
    return render(request, "core/form_simples.html", {
        "form": form, "titulo": "Editar item" if obj else "Nova peça ou serviço", "voltar": "catalogo",
        "nota": "O preço é só uma sugestão: dá pra mudar o valor em cada orçamento.",
    })


# ---------------------------------------------------------------- relatórios
def dados_relatorio(request):
    hoje = timezone.localdate()
    params = request.GET.dict()
    params["de"] = params.get("de") or hoje.replace(day=1).isoformat()
    params["ate"] = params.get("ate") or hoje.isoformat()
    qs, f = filtrar_pedidos(params, pedidos_com_itens())
    if not f["status"]:
        qs = qs.exclude(status__in=[Status.ORCAMENTO, Status.CANCELADO])
    lista = []
    tot = {"pecas": Decimal("0"), "servicos": Decimal("0"), "iss": Decimal("0"), "total": Decimal("0"), "pago": Decimal("0")}
    por_mec = {}
    for p in qs.order_by("data", "sequencia"):
        t = p.totais()
        lista.append((p, t))
        for k in ("pecas", "servicos", "iss", "total"):
            tot[k] += t[k]
        if p.status == Status.PAGO:
            tot["pago"] += t["total"]
        # cada item conta para o mecânico que fez; sem mecânico no item, vale o principal do pedido
        vistos = set()
        for i in p.itens.all():
            mec = i.mecanico or p.mecanico
            nome = mec.nome if mec else "Sem mecânico"
            m = por_mec.setdefault(nome, {"nome": nome, "qtd": 0, "servicos": Decimal("0"), "pecas": Decimal("0")})
            if nome not in vistos:
                m["qtd"] += 1
                vistos.add(nome)
            m["servicos" if i.tipo == TipoItem.SERVICO else "pecas"] += i.total
    return f, lista, tot, sorted(por_mec.values(), key=lambda x: x["nome"])


@login_required
def relatorios(request):
    f, lista, tot, por_mec = dados_relatorio(request)
    cliente_sel = Cliente.objects.filter(pk=f["cliente"]).first() if f["cliente"] else None
    return render(request, "core/relatorios.html", {
        "f": f, "lista": lista, "tot": tot, "por_mec": por_mec, "cliente_sel": cliente_sel,
        "status_opcoes": Status.choices, "mecanicos": Mecanico.objects.all(), "querystring": request.GET.urlencode(),
    })


@login_required
def relatorios_csv(request):
    f, lista, tot, _ = dados_relatorio(request)

    def br(v):
        return f"{v:.2f}".replace(".", ",")

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="pedidos_{f["de"]}_{f["ate"]}.csv"'
    resp.write("﻿")  # BOM para o Excel abrir com acento certo
    w = csv.writer(resp, delimiter=";")
    w.writerow(["Número", "Data", "Cliente", "CPF/CNPJ", "Veículo", "Vendedor", "Mecânicos", "Peças", "Serviços", "ISS", "Total", "Status"])
    for p, t in lista:
        w.writerow([p.numero, f"{p.data:%d/%m/%Y}", p.cliente.nome, p.cliente.documento, str(p.veiculo or ""),
                    p.vendedor.nome if p.vendedor else "",
                    p.mecanicos_nomes(), br(t["pecas"]), br(t["servicos"]), br(t["iss"]),
                    br(t["total"]), p.get_status_display()])
    w.writerow(["TOTAL", "", "", "", "", "", "", br(tot["pecas"]), br(tot["servicos"]), br(tot["iss"]), br(tot["total"]), ""])
    return resp


# ---------------------------------------------------------------- API (JSON) usada pelas buscas da tela
@login_required
def api_clientes(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"resultados": []})
    placa = so_letras_numeros(q)
    digitos = "".join(ch for ch in q if ch.isdigit())
    cond = Q(nome__icontains=q)
    if len(placa) >= 3:
        cond |= Q(veiculos__placa__icontains=placa)
    if len(digitos) >= 4:
        cond |= Q(telefone__icontains=digitos) | Q(documento__icontains=digitos) | Q(telefone__icontains=q) | Q(documento__icontains=q)
    qs = (Cliente.objects.filter(cond).distinct()
          .prefetch_related(Prefetch("veiculos", queryset=Veiculo.objects.select_related("modelo__marca")))[:8])
    res = []
    for c in qs:
        veiculos = list(c.veiculos.all())
        achou = next((v for v in veiculos if len(placa) >= 3 and placa in v.placa), None)
        res.append({"id": c.id, "nome": c.nome, "telefone": c.telefone, "documento": c.documento,
                    "veiculos": [veiculo_json(v) for v in veiculos], "veiculo_encontrado": achou.id if achou else None})
    return JsonResponse({"resultados": res})


@login_required
@require_POST
def api_cliente_criar(request):
    dados = json.loads(request.body or "{}")
    nome = str(dados.get("nome", "")).strip()
    if not nome:
        return JsonResponse({"erro": "Informe o nome do cliente."}, status=400)
    c = Cliente.objects.create(nome=nome[:150], telefone=str(dados.get("telefone", "")).strip()[:30],
                               documento=str(dados.get("documento", "")).strip()[:20])
    veiculo = None
    modelo = obter_ou_criar_modelo(dados.get("marca"), dados.get("modelo"), dados.get("nova_marca"), dados.get("novo_modelo"))
    if modelo:
        veiculo = Veiculo.objects.create(cliente=c, modelo=modelo, ano=str(dados.get("ano", ""))[:9],
                                         placa=str(dados.get("placa", "")), cor=str(dados.get("cor", ""))[:30])
    return JsonResponse({"cliente": {"id": c.id, "nome": c.nome, "telefone": c.telefone},
                         "veiculos": [veiculo_json(veiculo)] if veiculo else [],
                         "veiculo_id": veiculo.id if veiculo else None})


@login_required
@require_POST
def api_veiculo_criar(request, cliente_id):
    c = get_object_or_404(Cliente, pk=cliente_id)
    dados = json.loads(request.body or "{}")
    modelo = obter_ou_criar_modelo(dados.get("marca"), dados.get("modelo"), dados.get("nova_marca"), dados.get("novo_modelo"))
    if not modelo:
        return JsonResponse({"erro": "Informe marca e modelo."}, status=400)
    v = Veiculo.objects.create(cliente=c, modelo=modelo, ano=str(dados.get("ano", ""))[:9],
                               placa=str(dados.get("placa", "")), cor=str(dados.get("cor", ""))[:30])
    v = Veiculo.objects.select_related("modelo__marca").get(pk=v.pk)
    return JsonResponse({"veiculo": veiculo_json(v)})


@login_required
def api_modelos(request):
    marca_id = request.GET.get("marca", "")
    modelos = Modelo.objects.filter(marca_id=marca_id).order_by("nome").values("id", "nome") if marca_id.isdigit() else []
    return JsonResponse({"modelos": list(modelos)})


@login_required
def api_catalogo(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"resultados": []})
    qs = ItemCatalogo.objects.filter(ativo=True)
    for palavra in q.split():
        qs = qs.filter(descricao__icontains=palavra)
    return JsonResponse({"resultados": [
        {"id": i.id, "tipo": i.tipo, "descricao": i.descricao, "preco": str(i.preco)} for i in qs[:12]
    ]})


# ---------------------------------------------------------------- PWA
def manifest(request):
    dados = {
        "name": settings.EMPRESA_NOME,
        "short_name": "Oficina",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#0f120f",
        "theme_color": "#0f120f",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    return JsonResponse(dados, content_type="application/manifest+json", json_dumps_params={"ensure_ascii": False})


def service_worker(request):
    caminho = settings.BASE_DIR / "static" / "js" / "sw.js"
    if not caminho.exists():
        raise Http404
    resp = FileResponse(open(caminho, "rb"), content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp
