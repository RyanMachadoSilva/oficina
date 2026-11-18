"""Cadastro real (não é demonstração): cliente Luis e o orçamento feito no protótipo em 18/11/2026."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import migrations, models

ITENS = [
    ("servico", "Desempeno do eixo traseiro", "1", "400.00"),
    ("servico", "Caster", "2", "120.00"),
    ("servico", "Cambagem", "21", "12.00"),
    ("servico", "Alinhamento", "1", "0.00"),
    ("servico", "Balanceamento", "1", "0.00"),
]


def criar(apps, schema_editor):
    Cliente = apps.get_model("core", "Cliente")
    Pedido = apps.get_model("core", "Pedido")
    ItemPedido = apps.get_model("core", "ItemPedido")
    HistoricoStatus = apps.get_model("core", "HistoricoStatus")
    Parametros = apps.get_model("core", "Parametros")

    params = Parametros.objects.get_or_create(pk=1)[0]
    cliente, _ = Cliente.objects.get_or_create(nome="Luis", telefone="3499004038")
    data = date(2026, 11, 18)
    if Pedido.objects.filter(cliente=cliente, data=data).exists():
        return  # já criado
    seq = (Pedido.objects.filter(ano=data.year).aggregate(m=models.Max("sequencia"))["m"] or 0) + 1
    p = Pedido.objects.create(
        numero=f"{params.prefixo}{data.year}-{seq:04d}", ano=data.year, sequencia=seq, data=data,
        validade=data + timedelta(days=30), cliente=cliente, status="orcamento",
        iss_percentual=Decimal("5"), iss_base=params.iss_base)
    for n, (tipo, desc, qtd, preco) in enumerate(ITENS):
        ItemPedido.objects.create(pedido=p, ordem=n, tipo=tipo, descricao=desc,
                                  quantidade=Decimal(qtd), preco_unitario=Decimal(preco))
    HistoricoStatus.objects.create(pedido=p, status="orcamento")


class Migration(migrations.Migration):
    dependencies = [("core", "0004_dados_demonstracao")]
    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
