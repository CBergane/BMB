from django.shortcuts import render


def produkt(request):
    return render(request, 'products/product.html')
