from django.conf import settings

from products.models import Produkt

class Cart(object):
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)

        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}

        self.cart = cart

    def __iter__(self):
        for p in self.cart.keys():
            self.cart[str(p)]['produkt'] = Produkt.objects.get(pk=p)

        for item in self.cart.values():
            item['total_price'] = int(item['produkt'].pris * item['quantity'])

            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def add(self, produkt_id, quantity=1, update_quantity=False):
        produkt_id = str(produkt_id)

        if produkt_id not in self.cart:
            self.cart[produkt_id] = {'quantity': 1, 'id': produkt_id,}

        if update_quantity:
            self.cart[produkt_id]['quantity'] += int(quantity)

            if self.cart[produkt_id]['quantity'] == 0:
                self.remove(produkt_id)
        
        self.save()

    def remove(self, produkt_id):
        if produkt_id in self.cart:
            del self.cart[produkt_id]
            self.save()

    def get_total_cost(self):
        for p in self.cart.keys():
            self.cart[str(p)]['produkt'] = Produkt.objects.get(pk=p)

        return int(sum(item['produkt'].pris * item['quantity'] for item in self.cart.values()))