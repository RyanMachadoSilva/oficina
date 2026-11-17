from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

CENTAVO = Decimal("0.01")


class Parametros(models.Model):
    """Configurações gerais. Existe uma linha só (id=1)."""

    BASE_TUDO = "tudo"
    BASE_SERVICOS = "servicos"
    BASES_ISS = [(BASE_TUDO, "Peças + serviços"), (BASE_SERVICOS, "Só serviços")]

    prefixo = models.CharField("prefixo do número", max_length=10, default="ORC")
    validade_dias = models.PositiveIntegerField("validade do orçamento (dias)", default=30)
    iss_percentual = models.DecimalField("ISS padrão (%)", max_digits=5, decimal_places=2, default=Decimal("5"))
    iss_base = models.CharField("ISS calculado sobre", max_length=10, choices=BASES_ISS, default=BASE_TUDO)

    class Meta:
        verbose_name = "parâmetros"
        verbose_name_plural = "parâmetros"

    def __str__(self):
        return "Parâmetros do sistema"

    @classmethod
    def atual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Marca(models.Model):
    nome = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Modelo(models.Model):
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name="modelos")
    nome = models.CharField(max_length=80)

    class Meta:
        ordering = ["marca__nome", "nome"]
        constraints = [models.UniqueConstraint(fields=["marca", "nome"], name="modelo_unico_por_marca")]

    def __str__(self):
        return f"{self.marca.nome} {self.nome}"


class Cliente(models.Model):
    nome = models.CharField("nome / razão social", max_length=150)
    telefone = models.CharField(max_length=30, blank=True)
    documento = models.CharField("CPF / CNPJ", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    observacao = models.TextField("observação", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Veiculo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="veiculos")
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name="veiculos")
    ano = models.CharField(max_length=9, blank=True)
    placa = models.CharField(max_length=8, blank=True, db_index=True)
    cor = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["modelo__marca__nome", "modelo__nome"]
        verbose_name = "veículo"

    def __str__(self):
        txt = f"{self.modelo.marca.nome} {self.modelo.nome}"
        return f"{txt} · {self.placa}" if self.placa else txt

    def save(self, *args, **kwargs):
        self.placa = (self.placa or "").upper().replace("-", "").replace(" ", "")
        super().save(*args, **kwargs)


class Mecanico(models.Model):
    FORMAS = [
        ("A definir", "A definir"),
        ("% da mão de obra", "% da mão de obra"),
        ("Valor fixo por serviço", "Valor fixo por serviço"),
        ("Salário fixo", "Salário fixo"),
        ("Salário + comissão", "Salário + comissão"),
    ]
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=30, blank=True)
    forma_pagamento = models.CharField("forma de pagamento", max_length=40, choices=FORMAS, default="A definir")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "mecânico"

    def __str__(self):
        return self.nome


class TipoItem(models.TextChoices):
    PECA = "peca", "Peça"
    SERVICO = "servico", "Serviço"


class ItemCatalogo(models.Model):
    tipo = models.CharField(max_length=10, choices=TipoItem.choices, default=TipoItem.SERVICO)
    descricao = models.CharField("descrição", max_length=150)
    preco = models.DecimalField("preço padrão", max_digits=10, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "descricao"]
        verbose_name = "peça ou serviço"
        verbose_name_plural = "peças e serviços"

    def __str__(self):
        return self.descricao


class Status(models.TextChoices):
    ORCAMENTO = "orcamento", "Orçamento"
    APROVADO = "aprovado", "Aprovado"
    EXECUCAO = "execucao", "Em execução"
    FINALIZADO = "finalizado", "Finalizado"
    PAGO = "pago", "Pago"
    CANCELADO = "cancelado", "Cancelado"


class Pedido(models.Model):
    numero = models.CharField("número", max_length=20, unique=True, editable=False)
    ano = models.PositiveIntegerField(editable=False)
    sequencia = models.PositiveIntegerField(editable=False)
    data = models.DateField(default=timezone.localdate)
    validade = models.DateField("válido até", null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="pedidos", null=True, blank=True)
    mecanico = models.ForeignKey(Mecanico, on_delete=models.PROTECT, related_name="pedidos", null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ORCAMENTO, db_index=True)
    iss_percentual = models.DecimalField("ISS (%)", max_digits=5, decimal_places=2, default=Decimal("5"))
    iss_base = models.CharField(max_length=10, choices=Parametros.BASES_ISS, default=Parametros.BASE_TUDO)
    observacao = models.TextField("observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-ano", "-sequencia"]
        constraints = [models.UniqueConstraint(fields=["ano", "sequencia"], name="sequencia_unica_por_ano")]

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                params = Parametros.objects.select_for_update().get_or_create(pk=1)[0]
                self.ano = self.data.year
                ultimo = Pedido.objects.filter(ano=self.ano).aggregate(m=models.Max("sequencia"))["m"] or 0
                self.sequencia = ultimo + 1
                self.numero = f"{params.prefixo}{self.ano}-{self.sequencia:04d}"
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    # ---- totais (calculados a partir dos itens) ----
    def totais(self):
        pecas = servicos = Decimal("0")
        for i in self.itens.all():
            if i.tipo == TipoItem.PECA:
                pecas += i.total
            else:
                servicos += i.total
        subtotal = pecas + servicos
        base = servicos if self.iss_base == Parametros.BASE_SERVICOS else subtotal
        iss = (base * self.iss_percentual / 100).quantize(CENTAVO, ROUND_HALF_UP)
        return {"pecas": pecas, "servicos": servicos, "subtotal": subtotal, "iss": iss, "total": subtotal + iss}


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    tipo = models.CharField(max_length=10, choices=TipoItem.choices)
    descricao = models.CharField("descrição", max_length=150)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    preco_unitario = models.DecimalField("preço unitário", max_digits=10, decimal_places=2, default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "item do pedido"
        verbose_name_plural = "itens do pedido"

    def __str__(self):
        return self.descricao

    @property
    def total(self):
        return (self.quantidade * self.preco_unitario).quantize(CENTAVO, ROUND_HALF_UP)


class HistoricoStatus(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="historico")
    status = models.CharField(max_length=12, choices=Status.choices)
    em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["em"]
        verbose_name = "histórico de status"
        verbose_name_plural = "histórico de status"


class DemoRegistro(models.Model):
    """Anota cada registro criado como demonstração, para poder apagar só eles depois."""

    modelo = models.CharField(max_length=30)
    obj_id = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "registro de demonstração"
        verbose_name_plural = "registros de demonstração"
