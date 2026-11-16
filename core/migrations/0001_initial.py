from decimal import Decimal

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Parametros",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prefixo", models.CharField(default="ORC", max_length=10, verbose_name="prefixo do número")),
                ("validade_dias", models.PositiveIntegerField(default=30, verbose_name="validade do orçamento (dias)")),
                ("iss_percentual", models.DecimalField(decimal_places=2, default=Decimal("5"), max_digits=5, verbose_name="ISS padrão (%)")),
                ("iss_base", models.CharField(choices=[("tudo", "Peças + serviços"), ("servicos", "Só serviços")], default="tudo", max_length=10, verbose_name="ISS calculado sobre")),
            ],
            options={"verbose_name": "parâmetros", "verbose_name_plural": "parâmetros"},
        ),
        migrations.CreateModel(
            name="Marca",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=60, unique=True)),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Modelo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=80)),
                ("marca", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="modelos", to="core.marca")),
            ],
            options={"ordering": ["marca__nome", "nome"]},
        ),
        migrations.AddConstraint(
            model_name="modelo",
            constraint=models.UniqueConstraint(fields=("marca", "nome"), name="modelo_unico_por_marca"),
        ),
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150, verbose_name="nome / razão social")),
                ("telefone", models.CharField(blank=True, max_length=30)),
                ("documento", models.CharField(blank=True, max_length=20, verbose_name="CPF / CNPJ")),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("endereco", models.CharField(blank=True, max_length=200, verbose_name="endereço")),
                ("observacao", models.TextField(blank=True, verbose_name="observação")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Veiculo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ano", models.CharField(blank=True, max_length=9)),
                ("placa", models.CharField(blank=True, db_index=True, max_length=8)),
                ("cor", models.CharField(blank=True, max_length=30)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="veiculos", to="core.cliente")),
                ("modelo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="veiculos", to="core.modelo")),
            ],
            options={"ordering": ["modelo__marca__nome", "modelo__nome"], "verbose_name": "veículo"},
        ),
        migrations.CreateModel(
            name="Mecanico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100)),
                ("telefone", models.CharField(blank=True, max_length=30)),
                ("forma_pagamento", models.CharField(choices=[("A definir", "A definir"), ("% da mão de obra", "% da mão de obra"), ("Valor fixo por serviço", "Valor fixo por serviço"), ("Salário fixo", "Salário fixo"), ("Salário + comissão", "Salário + comissão")], default="A definir", max_length=40, verbose_name="forma de pagamento")),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={"ordering": ["nome"], "verbose_name": "mecânico"},
        ),
        migrations.CreateModel(
            name="ItemCatalogo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("peca", "Peça"), ("servico", "Serviço")], default="servico", max_length=10)),
                ("descricao", models.CharField(max_length=150, verbose_name="descrição")),
                ("preco", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="preço padrão")),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={"ordering": ["tipo", "descricao"], "verbose_name": "peça ou serviço", "verbose_name_plural": "peças e serviços"},
        ),
        migrations.CreateModel(
            name="Pedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.CharField(editable=False, max_length=20, unique=True, verbose_name="número")),
                ("ano", models.PositiveIntegerField(editable=False)),
                ("sequencia", models.PositiveIntegerField(editable=False)),
                ("data", models.DateField(default=django.utils.timezone.localdate)),
                ("validade", models.DateField(blank=True, null=True, verbose_name="válido até")),
                ("status", models.CharField(choices=[("orcamento", "Orçamento"), ("aprovado", "Aprovado"), ("execucao", "Em execução"), ("finalizado", "Finalizado"), ("pago", "Pago"), ("cancelado", "Cancelado")], db_index=True, default="orcamento", max_length=12)),
                ("iss_percentual", models.DecimalField(decimal_places=2, default=Decimal("5"), max_digits=5, verbose_name="ISS (%)")),
                ("iss_base", models.CharField(choices=[("tudo", "Peças + serviços"), ("servicos", "Só serviços")], default="tudo", max_length=10)),
                ("observacao", models.TextField(blank=True, verbose_name="observações")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="core.cliente")),
                ("criado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("mecanico", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="core.mecanico")),
                ("veiculo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pedidos", to="core.veiculo")),
            ],
            options={"ordering": ["-ano", "-sequencia"]},
        ),
        migrations.AddConstraint(
            model_name="pedido",
            constraint=models.UniqueConstraint(fields=("ano", "sequencia"), name="sequencia_unica_por_ano"),
        ),
        migrations.CreateModel(
            name="ItemPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("peca", "Peça"), ("servico", "Serviço")], max_length=10)),
                ("descricao", models.CharField(max_length=150, verbose_name="descrição")),
                ("quantidade", models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ("preco_unitario", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="preço unitário")),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="itens", to="core.pedido")),
            ],
            options={"ordering": ["ordem", "id"], "verbose_name": "item do pedido", "verbose_name_plural": "itens do pedido"},
        ),
        migrations.CreateModel(
            name="HistoricoStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("orcamento", "Orçamento"), ("aprovado", "Aprovado"), ("execucao", "Em execução"), ("finalizado", "Finalizado"), ("pago", "Pago"), ("cancelado", "Cancelado")], max_length=12)),
                ("em", models.DateTimeField(auto_now_add=True)),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historico", to="core.pedido")),
                ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["em"], "verbose_name": "histórico de status", "verbose_name_plural": "histórico de status"},
        ),
    ]
