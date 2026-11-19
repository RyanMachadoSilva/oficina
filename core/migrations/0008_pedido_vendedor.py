import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0007_apagar_dados_demonstracao")]
    operations = [
        migrations.AddField(
            model_name="pedido",
            name="vendedor",
            field=models.ForeignKey(blank=True, help_text="Quem atendeu o cliente", null=True,
                                    on_delete=django.db.models.deletion.SET_NULL, related_name="vendas",
                                    to="core.mecanico"),
        ),
    ]
