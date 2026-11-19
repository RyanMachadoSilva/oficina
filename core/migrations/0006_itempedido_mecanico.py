import django.db.models.deletion
from django.db import migrations, models


def preencher(apps, schema_editor):
    """Pedidos já existentes: os serviços passam a ser do mecânico principal do pedido."""
    ItemPedido = apps.get_model("core", "ItemPedido")
    for item in ItemPedido.objects.filter(tipo="servico", pedido__mecanico__isnull=False).select_related("pedido"):
        item.mecanico_id = item.pedido.mecanico_id
        item.save(update_fields=["mecanico"])


class Migration(migrations.Migration):
    dependencies = [("core", "0005_orcamento_cliente_luis")]
    operations = [
        migrations.AddField(
            model_name="itempedido",
            name="mecanico",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name="itens", to="core.mecanico", verbose_name="mecânico"),
        ),
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
