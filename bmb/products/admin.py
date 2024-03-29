from django.contrib import admin
from django.db.models import Count
from .models import Category, Produkt, WashInstruction, Color, ProductVariant


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('namn', 'parent', 'slug', 'number_of_subcategories')
    list_filter = ('parent',)
    search_fields = ('namn',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(subcat_count=Count('children')).order_by('-subcat_count')

    def number_of_subcategories(self, obj):
        return obj.subcat_count
    number_of_subcategories.admin_order_field = 'subcat_count'
    number_of_subcategories.short_description = 'Antal Underkategorier'


@admin.register(WashInstruction)
class WashInstructionAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name']

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProduktAdmin(admin.ModelAdmin):
    list_display = ('namn', 'category', 'is_fabric','slug', 'is_stubbie', 'is_active', 'pris', 'skapad')
    list_filter = ('category', 'is_fabric', 'is_stubbie', 'is_active')
    search_fields = ('namn', 'beskrivning', 'blandning', 'kvalitet', 'färg', 'motiv')
    filter_horizontal = ('wash_instructions',)
    inlines = [ProductVariantInline]


admin.site.register(Category, CategoryAdmin)
admin.site.register(Produkt, ProduktAdmin)
