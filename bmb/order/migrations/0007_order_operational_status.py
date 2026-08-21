from django.db import migrations, models


def map_legacy_statuses_forward(apps, schema_editor):
    Order = apps.get_model('order', 'Order')
    Order.objects.filter(status='ordered').update(status='received')


def map_statuses_reverse(apps, schema_editor):
    Order = apps.get_model('order', 'Order')
    Order.objects.filter(
        status__in=['received', 'processing', 'packing']
    ).update(status='ordered')
    Order.objects.filter(
        status__in=['shipped', 'completed']
    ).update(status='shipped')
    Order.objects.filter(
        status__in=['cancelled', 'archived']
    ).update(status='ordered')


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0006_order_submission_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('received', 'Mottagen'),
                    ('processing', 'Behandlas'),
                    ('packing', 'Packas'),
                    ('shipped', 'Skickad'),
                    ('completed', 'Slutförd'),
                    ('cancelled', 'Avbruten'),
                    ('archived', 'Arkiverad'),
                ],
                default='received',
                max_length=20,
            ),
        ),
        migrations.RunPython(
            map_legacy_statuses_forward,
            map_statuses_reverse,
        ),
    ]
