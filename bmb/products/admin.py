from django.contrib import admin

from .models import Category, Produkt

class ProduktAdmin(admin.ModelAdmin):
    list_display = ('namn', 'category', 'is_fabric', 'is_stubbie', 'is_active', 'pris', 'skapad')
    list_filter = ('category', 'is_fabric', 'is_stubbie', 'is_active')
    search_fields = ('namn', 'beskrivning', 'blandning', 'kvalitet', 'färg', 'motiv')

admin.site.register(Category)
admin.site.register(Produkt, ProduktAdmin)
