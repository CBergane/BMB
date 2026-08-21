from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('order', '0008_protect_orderitem_product'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_status', models.CharField(choices=[('received', 'Mottagen'), ('processing', 'Behandlas'), ('packing', 'Packas'), ('shipped', 'Skickad'), ('completed', 'Slutförd'), ('cancelled', 'Avbruten'), ('archived', 'Arkiverad')], max_length=20)),
                ('new_status', models.CharField(choices=[('received', 'Mottagen'), ('processing', 'Behandlas'), ('packing', 'Packas'), ('shipped', 'Skickad'), ('completed', 'Slutförd'), ('cancelled', 'Avbruten'), ('archived', 'Arkiverad')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_status_changes', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='order.order')),
            ],
            options={
                'ordering': ('-created_at', '-pk'),
            },
        ),
    ]
