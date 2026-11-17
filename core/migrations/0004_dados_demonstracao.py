"""Dados de demonstração (clientes, veículos, mecânicos e um pedido de cada status).

Tudo que é criado aqui fica anotado em DemoRegistro. Para remover só esses dados,
basta uma migração que apague os registros listados (ver 0005, quando for a hora).
"""
from datetime import timedelta
from decimal import Decimal

import django.utils.timezone
from django.db import migrations, models

CLIENTES = [
    ("Marcos Pereira", "(34) 99876-1234", "", [("Ford", "Fiesta", "2014", "QWE1A23", "Prata")]),
    ("Ana Souza", "(34) 99765-4321", "", [("Fiat", "Argo", "2021", "RTY2B34", "Branco"), ("Fiat", "Strada", "2019", "UIO3C45", "Vermelho")]),
    ("Transportes Lima Ltda", "(34) 3214-5566", "12.345.678/0001-90", [("Volkswagen", "Saveiro", "2018", "PAS4D56", "Branco")]),
    ("Juliana Costa", "(34) 99654-7788", "", [("Hyundai", "HB20", "2020", "DFG5E67", "Cinza")]),
    ("Roberto Almeida", "(34) 99543-2211", "", [("Chevrolet", "Onix", "2017", "HJK6F78", "Preto")]),
]
MECANICOS = [("Carlos Mendes", "(34) 99111-2233"), ("João Ribeiro", "(34) 99222-3344")]

# (dias atrás, cliente, veículo, mecânico, status, histórico, itens [(tipo, descrição, qtd, preço)], observação)
PEDIDOS = [
    (0, 0, 0, 0, "orcamento", ["orcamento"],
     [("servico", "Diagnóstico com scanner", 1, "100.00"), ("servico", "Balanceamento (4 rodas)", 1, "60.00")],
     "Cliente vai confirmar por WhatsApp."),
    (2, 1, 0, 1, "aprovado", ["orcamento", "aprovado"],
     [("servico", "Revisão de freios", 1, "120.00"), ("peca", "Disco de freio (par)", 1, "380.00"), ("peca", "Jogo de pastilha de freio", 1, "145.00")], ""),
    (4, 2, 0, 0, "execucao", ["orcamento", "aprovado", "execucao"],
     [("peca", "Amortecedor dianteiro", 2, "320.00"), ("servico", "Mão de obra", 2, "60.00"), ("servico", "Alinhamento", 1, "80.00")],
     "Peças chegam amanhã de manhã."),
    (6, 3, 0, 1, "finalizado", ["orcamento", "aprovado", "execucao", "finalizado"],
     [("servico", "Troca de óleo", 1, "40.00"), ("peca", "Óleo 5W30 (litro)", 4, "42.00"), ("peca", "Filtro de óleo", 1, "35.00"), ("peca", "Filtro de ar", 1, "48.00")], ""),
    (9, 0, 0, 0, "pago", ["orcamento", "aprovado", "execucao", "finalizado", "pago"],
     [("servico", "Cambagem", 2, "98.00"), ("servico", "Caster", 2, "98.00"), ("peca", "Jogo de pastilha de freio", 1, "145.00"), ("servico", "Mão de obra", 1, "60.00")], ""),
    (11, 4, 0, 1, "cancelado", ["orcamento", "cancelado"],
     [("peca", "Kit de embreagem", 1, "780.00"), ("servico", "Mão de obra embreagem", 1, "350.00")],
     "Cliente achou caro e não aprovou."),
]


def carregar(apps, schema_editor):
    Marca = apps.get_model("core", "Marca")
    Modelo = apps.get_model("core", "Modelo")
    Cliente = apps.get_model("core", "Cliente")
    Veiculo = apps.get_model("core", "Veiculo")
    Mecanico = apps.get_model("core", "Mecanico")
    Pedido = apps.get_model("core", "Pedido")
    ItemPedido = apps.get_model("core", "ItemPedido")
    HistoricoStatus = apps.get_model("core", "HistoricoStatus")
    Parametros = apps.get_model("core", "Parametros")
    Demo = apps.get_model("core", "DemoRegistro")

    def anotar(nome, obj):
        Demo.objects.create(modelo=nome, obj_id=obj.pk)
        return obj

    params = Parametros.objects.get_or_create(pk=1)[0]
    clientes = []
    for nome, tel, doc, veiculos in CLIENTES:
        c = anotar("cliente", Cliente.objects.create(nome=nome, telefone=tel, documento=doc,
                                                     observacao="Cadastro de demonstração"))
        vs = []
        for marca, modelo, ano, placa, cor in veiculos:
            m = Modelo.objects.get_or_create(marca=Marca.objects.get_or_create(nome=marca)[0], nome=modelo)[0]
            vs.append(anotar("veiculo", Veiculo.objects.create(cliente=c, modelo=m, ano=ano, placa=placa, cor=cor)))
        clientes.append((c, vs))
    mecanicos = [anotar("mecanico", Mecanico.objects.create(nome=n, telefone=t)) for n, t in MECANICOS]

    hoje = django.utils.timezone.localdate()
    for dias, ci, vi, mi, status, historico, itens, obs in PEDIDOS:
        data = hoje - timedelta(days=dias)
        seq = (Pedido.objects.filter(ano=data.year).aggregate(m=models.Max("sequencia"))["m"] or 0) + 1
        c, vs = clientes[ci]
        p = anotar("pedido", Pedido.objects.create(
            numero=f"{params.prefixo}{data.year}-{seq:04d}", ano=data.year, sequencia=seq, data=data,
            validade=data + timedelta(days=params.validade_dias), cliente=c, veiculo=vs[vi],
            mecanico=mecanicos[mi], status=status, iss_percentual=params.iss_percentual,
            iss_base=params.iss_base, observacao=obs))
        for n, (tipo, desc, qtd, preco) in enumerate(itens):
            ItemPedido.objects.create(pedido=p, ordem=n, tipo=tipo, descricao=desc,
                                      quantidade=Decimal(qtd), preco_unitario=Decimal(preco))
        for s in historico:
            HistoricoStatus.objects.create(pedido=p, status=s)


class Migration(migrations.Migration):
    dependencies = [("core", "0003_mais_marcas_modelos")]
    operations = [
        migrations.CreateModel(
            name="DemoRegistro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("modelo", models.CharField(max_length=30)),
                ("obj_id", models.PositiveIntegerField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "registro de demonstração", "verbose_name_plural": "registros de demonstração"},
        ),
        migrations.RunPython(carregar, migrations.RunPython.noop),
    ]
