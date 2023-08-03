from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_produkt'),
    ]

    operations = [
        migrations.AddField(
            model_name='produkt',
            name='blandningen',
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name='produkt',
            name='bredd',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='produkt',
            name='färg',
            field=models.CharField(max_length=255),
        ),
        migrations.AddField(
            model_name='produkt',
            name='vikt',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='produkt',
            name='yta',
            field=models.CharField(max_length=255),
        ),
    ]
