from django.urls import path

from .views import (
    dashboard,
    product_archive,
    product_create,
    product_edit,
    product_list,
    product_move_to_draft,
    product_preview,
    product_publish,
    order_change_status,
    order_detail,
    order_list,
    order_mark_paid,
)


app_name = 'owner_dashboard'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('orders/', order_list, name='order_list'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('orders/<int:order_id>/mark-paid/', order_mark_paid, name='order_mark_paid'),
    path(
        'orders/<int:order_id>/status/<str:new_status>/',
        order_change_status,
        name='order_change_status',
    ),
    path('products/', product_list, name='product_list'),
    path('products/new/', product_create, name='product_create'),
    path('products/<int:product_id>/edit/', product_edit, name='product_edit'),
    path(
        'products/<int:product_id>/preview/',
        product_preview,
        name='product_preview',
    ),
    path(
        'products/<int:product_id>/publish/',
        product_publish,
        name='product_publish',
    ),
    path(
        'products/<int:product_id>/draft/',
        product_move_to_draft,
        name='product_move_to_draft',
    ),
    path(
        'products/<int:product_id>/archive/',
        product_archive,
        name='product_archive',
    ),
]
