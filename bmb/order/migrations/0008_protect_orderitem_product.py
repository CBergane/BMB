import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0007_order_operational_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='produkt',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='items',
                to='products.produkt',
            ),
        ),
    ]
