from django.contrib import admin
from .models import Category, Produkt

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('namn', 'parent', 'slug')  # Visa namn, överordnad kategori och slug
    list_filter = ('parent',)  # Filtrera baserat på överordnad kategori
    search_fields = ('namn',)

class ProduktAdmin(admin.ModelAdmin):
    list_display = ('namn', 'category', 'is_fabric', 'is_stubbie', 'is_active', 'pris', 'skapad')
    list_filter = ('category', 'is_fabric', 'is_stubbie', 'is_active')
    search_fields = ('namn', 'beskrivning', 'blandning', 'kvalitet', 'färg', 'motiv')

admin.site.register(Category, CategoryAdmin)
admin.site.register(Produkt, ProduktAdmin)
