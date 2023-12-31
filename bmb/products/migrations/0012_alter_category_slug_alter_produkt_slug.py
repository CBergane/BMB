# Generated by Django 4.2.4 on 2023-08-08 09:07

import autoslug.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_alter_produkt_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from='namn', unique=True),
        ),
        migrations.AlterField(
            model_name='produkt',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from='namn', unique=True),
        ),
    ]
