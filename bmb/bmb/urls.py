from django.conf import settings
from django.contrib import admin

from django.conf.urls.static import static
from django.urls import path, include


urlpatterns = [
    path('', include('core.urls')),
    path('cart/', include('cart.urls')),
    path('order/', include('order.urls')),
    path('admin/', admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
