# Generated by Django 4.2.4 on 2023-08-03 13:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Produkt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('namn', models.CharField(max_length=255)),
                ('slug', models.SlugField()),
                ('beskrivning', models.TextField(blank=True, null=True)),
                ('pris', models.IntegerField()),
                ('skapad', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produkt', to='products.category')),
            ],
            options={
                'ordering': ('-skapad',),
            },
        ),
    ]
