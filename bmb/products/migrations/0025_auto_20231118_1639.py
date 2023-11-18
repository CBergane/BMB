# Generated by Django 4.2.4 on 2023-11-18 16:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0024_alter_produkt_unit'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE products_produkt DROP COLUMN fabric_increment;",
            reverse_sql="ALTER TABLE products_produkt ADD COLUMN fabric_increment integer NOT NULL DEFAULT 0;"
        ),
    ]