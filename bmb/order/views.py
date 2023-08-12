from django.shortcuts import render, redirect

from cart.cart import Cart

from .models import Order, OrderItem

def start_order(request):
    cart = Cart(request)

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        address = request.POST.get('address')
        zipcode = request.POST.get('zipcode')
        city = request.POST.get('city')
        phone = request.POST.get('phone')

        order = Order.objects.create(user=request.user, first_name=first_name, last_name=last_name, email=email, phone=phone, address=address, zipcode=zipcode, city=city)

        for item in cart:
            produkt = item['produkt']
            quantity = int(item['quantity'])
            price = produkt.pris * quantity

            item = OrderItem.objects.create(order=order, produkt=produkt, price=price, quantity=quantity)

        return redirect('myaccount')
    return redirect('cart')