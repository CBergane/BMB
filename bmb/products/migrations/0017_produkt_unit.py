# Generated by Django 4.2.4 on 2023-08-16 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0016_alter_produkt_image_alter_produkt_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='produkt',
            name='unit',
            field=models.CharField(choices=[('dm', 'Decimeter'), ('st', 'St')], default='st', help_text='Enhet för denna produkt', max_length=4),
        ),
    ]