# Generated by Django 4.2.4 on 2024-01-22 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0032_category_parent'),
    ]

    operations = [
        migrations.CreateModel(
            name='WashInstruction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('icon', models.ImageField(upload_to='icons/')),
            ],
        ),
        migrations.AddField(
            model_name='produkt',
            name='wash_instructions',
            field=models.ManyToManyField(blank=True, to='products.washinstruction'),
        ),
    ]
