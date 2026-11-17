"""Completa a lista de marcas e modelos (só adiciona; não apaga nem muda o que já foi cadastrado)."""
from django.db import migrations


def completar(apps, schema_editor):
    from core.dados import MARCAS

    Marca = apps.get_model("core", "Marca")
    Modelo = apps.get_model("core", "Modelo")
    for nome_marca, modelos in MARCAS.items():
        marca, _ = Marca.objects.get_or_create(nome=nome_marca)
        for nome in modelos:
            Modelo.objects.get_or_create(marca=marca, nome=nome)


class Migration(migrations.Migration):
    dependencies = [("core", "0002_carga_inicial")]
    operations = [migrations.RunPython(completar, migrations.RunPython.noop)]
