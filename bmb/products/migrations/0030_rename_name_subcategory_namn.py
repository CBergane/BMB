# Generated by Django 4.2.4 on 2024-01-14 15:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0029_subcategory_produkt_subcategory'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subcategory',
            old_name='name',
            new_name='namn',
        ),
    ]