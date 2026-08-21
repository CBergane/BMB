from django.urls import path

from django.contrib.auth import views

from core.views import frontpage, shop, signup, myaccount, myaccount_order_detail, edit_myaccount, about, discounted_products, news, stubbie_view, send_contact_email, bmb_exclusive_products
from products.views import produkt


urlpatterns = [
    path('', frontpage, name='frontpage'),
    path('send-email/', send_contact_email, name='send_email'),
    path('news/', news, name='news'),
    path('about/', about, name='about'),
    path('signup/', signup, name='signup'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('login/', views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('shop/', shop, name='shop'),
    path('shop/<slug:slug>/', produkt, name='produkt'),
    path('myaccount/', myaccount, name='myaccount'),
    path('myaccount/orders/<int:order_id>/', myaccount_order_detail, name='myaccount_order_detail'),
    path('edit_myaccount/', edit_myaccount, name='edit_myaccount'),
    path('discounted_products/', discounted_products, name='discounted_products'),
    path('stubbies/', stubbie_view, name='stubbies'),
    path('bmb-exclusive/', bmb_exclusive_products, name='bmb_exclusive_products'),
]
