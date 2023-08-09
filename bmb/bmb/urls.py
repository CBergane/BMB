from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views
from django.conf.urls.static import static
from django.urls import path

from cart.views import add_to_cart
from core.views import frontpage, shop, signup
from products.views import produkt

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', frontpage, name='frontpage'),
    path('signup/', signup, name='signup'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('login/', views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('shop/', shop, name='shop'),
    path('shop/<slug:slug>/', produkt, name='produkt'),
    path('add_to_cart/<int:produkt_id>/', add_to_cart, name='add_to_cart'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
