from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path

from cart.views import add_to_cart
from core.views import frontpage, shop, signup, login
from products.views import produkt

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', frontpage, name='frontpage'),
    path('signup', signup, name='signup'),
    path('login', login, name='login'),
    path('shop/', shop, name='shop'),
    path('shop/<slug:slug>/', produkt, name='produkt'),
    path('add_to_cart/<int:produkt_id>/', add_to_cart, name='add_to_cart'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
