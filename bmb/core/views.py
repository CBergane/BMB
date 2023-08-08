from django.shortcuts import render
from django.db.models import Q

from products.models import Produkt, Category


def frontpage(request):
    produkt = Produkt.objects.all()[0:8]
    return render(request, 
    'core/frontpage.html',
    {'produkt': produkt},
    )

def shop(request):
    categories = Category.objects.all()
    produkt = Produkt.objects.all()

    active_category = request.GET.get('category', '')

    if active_category:
        produkt = produkt.filter(category__slug=active_category)

    query = request.GET.get('query', '')

    if query:
        produkt = produkt.filter(Q(namn__icontains=query) | Q(beskrivning__icontains=query))

    context = {
        'categories': categories,
        'produkt': produkt,
        'active_category': active_category,
        }

    return render(request, 
    'core/shop.html',
    context,
    )