from django.db.models import Count, Q
from django.shortcuts import render

from order.models import Order
from products.models import Produkt

from .access import owner_required


@owner_required
def dashboard(request):
    product_totals = Produkt.objects.aggregate(
        total=Count('pk'),
        active=Count('pk', filter=Q(is_active=True)),
        low_stock=Count('pk', filter=Q(inventory__lte=5)),
    )
    order_totals = Order.objects.aggregate(
        total=Count('pk'),
        unpaid=Count('pk', filter=Q(paid=False)),
    )

    context = {
        'product_totals': product_totals,
        'order_totals': order_totals,
        'latest_orders': Order.objects.select_related('user')[:8],
    }
    return render(request, 'owner_dashboard/dashboard.html', context)
