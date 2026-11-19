"""Remove os dados de demonstração (só os anotados em DemoRegistro). Cadastros reais não são tocados.

Se algum cliente, veículo ou mecânico de exemplo já foi usado num pedido real, ele é mantido
para não quebrar esse pedido.
"""
from django.db import migrations
from django.db.models import ProtectedError

ORDEM = [("pedido", "Pedido"), ("veiculo", "Veiculo"), ("cliente", "Cliente"), ("mecanico", "Mecanico")]


def apagar(apps, schema_editor):
    Demo = apps.get_model("core", "DemoRegistro")
    for chave, nome_modelo in ORDEM:
        Modelo = apps.get_model("core", nome_modelo)
        ids = list(Demo.objects.filter(modelo=chave).values_list("obj_id", flat=True))
        for obj in Modelo.objects.filter(pk__in=ids):
            try:
                obj.delete()
            except ProtectedError:
                print(f"  mantido (em uso num pedido real): {nome_modelo} {obj.pk}")
    Demo.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0006_itempedido_mecanico")]
    operations = [migrations.RunPython(apagar, migrations.RunPython.noop)]
