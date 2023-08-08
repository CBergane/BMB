from django.shortcuts import render, get_object_or_404

from .models import Produkt


def produkt(request, slug):

    produkt = get_object_or_404(Produkt, slug=slug)

    return render(request, 'products/product.html', {'produkt':produkt,})
