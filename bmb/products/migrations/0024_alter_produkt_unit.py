# Generated by Django 4.2.4 on 2023-11-09 08:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0023_alter_produkt_beskrivning'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produkt',
            name='unit',
            field=models.CharField(choices=[('dm', 'Decimeter'), ('st', 'St')], default='st', help_text='Enhet för denna produkt', max_length=4),
        ),
    ]
