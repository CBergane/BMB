from django.contrib import admin
from django.db.models import Count, Q
from .models import Category, Produkt, WashInstruction, Color, ProductVariant


class ParentCategoryListFilter(admin.SimpleListFilter):
    title = 'Parent Category'
    parameter_name = 'is_parent'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Parent Categories'),
            ('no', 'Non-Parent Categories'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(parent__isnull=True)
        elif self.value() == 'no':
            return queryset.filter(parent__isnull=False)
        return queryset

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'parent':
            # Filter out categories that already have a parent
            kwargs["queryset"] = Category.objects.filter(parent__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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
    list_display = ('namn', 'category', 'is_fabric', 'slug', 'is_stubbie', 'is_bmb_exclusive', 'is_active', 'pris', 'skapad', 'number_of_images')
    list_filter = ('category', 'is_fabric', 'is_stubbie', 'is_active')
    search_fields = ('namn', 'beskrivning', 'blandning', 'kvalitet', 'färg', 'motiv')
    filter_horizontal = ('wash_instructions',)
    inlines = [ProductVariantInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            # Filtrera bort kategorier som redan har en förälder
            kwargs["queryset"] = Category.objects.filter(parent__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def number_of_images(self, obj):
        """
        Räknar antalet bilder associerade med produkten.
        """
        images = [obj.image, obj.image2, obj.image3, obj.image4]
        return sum(1 for image in images if image)  # Räknar icke-tomma bilder

    number_of_images.short_description = 'Antal Bilder'


admin.site.register(Category, CategoryAdmin)
admin.site.register(Produkt, ProduktAdmin)
