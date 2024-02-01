from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from products.models import Produkt, Color

class Cart(object):
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, produkt_id, quantity=1, color_id=None, custom_text='', update_quantity=False):
        produkt_id_str = str(produkt_id)
        # Skapa en unik nyckel för varje unik produktvariant (produkt + färg + text)
        cart_key = f"{produkt_id_str}_{color_id}_{custom_text}"

        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'quantity': 0, 
                'produkt_id': produkt_id,
                'color_id': color_id, 
                'custom_text': custom_text
            }

        if update_quantity:
            self.cart[cart_key]['quantity'] = quantity
        else:
            self.cart[cart_key]['quantity'] += quantity

        # Uppdatera kvantiteten, men se till att den inte överstiger lagret
        produkt = Produkt.objects.get(pk=produkt_id)
        if self.cart[cart_key]['quantity'] > produkt.inventory:
            self.cart[cart_key]['quantity'] = produkt.inventory

        if self.cart[cart_key]['quantity'] <= 0:
            del self.cart[cart_key]
        else:
            self.save()

    def __iter__(self):
        for key, value in self.cart.items():
            produkt_id_str, color_id_str, custom_text = key.split('_')
            produkt_id = int(produkt_id_str)
            color_id = int(color_id_str) if color_id_str != 'None' else None

            produkt = get_object_or_404(Produkt, pk=produkt_id)
            color = get_object_or_404(Color, pk=color_id) if color_id else None

            thumbnail_url = produkt.get_thumbnail()

            item = {
                'cart_key': key,
                'produkt_id': produkt_id,
                'produkt_namn': produkt.namn,
                'slug': produkt.slug,
                'thumbnail_url': thumbnail_url,  # Lägg till thumbnail URL här
                'color': color,
                'custom_text': custom_text if custom_text != 'None' else '',
                'total_price': int(produkt.pris * value['quantity']),
                'quantity': value['quantity']
            }
            yield item


    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, produkt_id):
        if produkt_id in self.cart:
            del self.cart[produkt_id]
            self.save()
    
    def increment_item(self, cart_key):
        if cart_key in self.cart:
            self.cart[cart_key]['quantity'] += 1
            self.save()

    def decrement_item(self, cart_key):
        if cart_key in self.cart and self.cart[cart_key]['quantity'] > 1:
            self.cart[cart_key]['quantity'] -= 1
            self.save()
        elif cart_key in self.cart and self.cart[cart_key]['quantity'] == 1:
            del self.cart[cart_key]
            self.save()

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.session.modified = True

    def get_total_cost(self):
        total_cost = 0
        for key in self.cart.keys():
            produkt_id_str, _, _ = key.split('_')  # Dela nyckeln och få produkt_id
            produkt_id = int(produkt_id_str)  # Konvertera produkt_id till ett heltal
            produkt = Produkt.objects.get(pk=produkt_id)
            total_cost += int(produkt.pris * self.cart[key]['quantity'])
        return total_cost

    def get_item(self, produkt_id):
        if str(produkt_id) in self.cart:
            return self.cart[str(produkt_id)]
        else:
            return None
