"""Carrega marcas/modelos, um catálogo inicial de exemplo e os parâmetros padrão."""
from decimal import Decimal

from django.db import migrations


def carregar(apps, schema_editor):
    from core.dados import CATALOGO_INICIAL, MARCAS

    Marca = apps.get_model("core", "Marca")
    Modelo = apps.get_model("core", "Modelo")
    ItemCatalogo = apps.get_model("core", "ItemCatalogo")
    Parametros = apps.get_model("core", "Parametros")

    Parametros.objects.get_or_create(pk=1)
    for nome_marca, modelos in MARCAS.items():
        marca, _ = Marca.objects.get_or_create(nome=nome_marca)
        for nome in modelos:
            Modelo.objects.get_or_create(marca=marca, nome=nome)
    if not ItemCatalogo.objects.exists():
        for tipo, desc, preco in CATALOGO_INICIAL:
            ItemCatalogo.objects.create(tipo=tipo, descricao=desc, preco=Decimal(preco))


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(carregar, migrations.RunPython.noop)]
