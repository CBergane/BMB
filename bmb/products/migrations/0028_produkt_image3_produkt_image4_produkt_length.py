# Generated by Django 4.2.4 on 2024-01-14 13:50

import cloudinary.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0027_produkt_image2'),
    ]

    operations = [
        migrations.AddField(
            model_name='produkt',
            name='image3',
            field=cloudinary.models.CloudinaryField(blank=True, help_text='Valfri: Lägg till en andra bild av produkten.', max_length=255, null=True, verbose_name='image3'),
        ),
        migrations.AddField(
            model_name='produkt',
            name='image4',
            field=cloudinary.models.CloudinaryField(blank=True, help_text='Valfri: Lägg till en andra bild av produkten.', max_length=255, null=True, verbose_name='image4'),
        ),
        migrations.AddField(
            model_name='produkt',
            name='length',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Length of the stubbie product (in decimeters)', max_digits=10, null=True),
        ),
    ]