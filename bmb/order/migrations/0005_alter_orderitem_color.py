# Generated by Django 4.2.4 on 2024-02-01 08:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0036_productvariant_allow_custom_text'),
        ('order', '0004_orderitem_color_orderitem_custom_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='color',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='products.color'),
        ),
    ]
