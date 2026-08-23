from django.db import migrations, models


def publish_existing_products(apps, schema_editor):
    Produkt = apps.get_model('products', 'Produkt')
    Produkt.objects.update(publication_status='published')


def reset_products_to_draft(apps, schema_editor):
    Produkt = apps.get_model('products', 'Produkt')
    Produkt.objects.update(publication_status='draft')


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0038_use_ckeditor5'),
    ]

    operations = [
        migrations.AddField(
            model_name='produkt',
            name='publication_status',
            field=models.CharField(
                choices=[
                    ('draft', 'Utkast'),
                    ('published', 'Publicerad'),
                    ('archived', 'Arkiverad'),
                ],
                default='draft',
                max_length=10,
            ),
        ),
        migrations.RunPython(
            publish_existing_products,
            reset_products_to_draft,
        ),
    ]
