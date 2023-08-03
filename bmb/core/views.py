from django.shortcuts import render

from products.models import Produkt


def frontpage(request):
    produkt = Produkt.objects.all()[0:8]
    return render(request, 
    'core/frontpage.html',
    {'produkt': produkt},
    )

def shop(request):
    produkt = Produkt.objects.all()
    return render(request, 
    'core/shop.html',
    {'produkt': produkt},
    )