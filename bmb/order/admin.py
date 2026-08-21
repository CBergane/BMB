from django.contrib import admin, messages

from .models import Order, OrderInventoryError, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['produkt']

class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['first_name', 'address']
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        obj._should_mark_as_paid = False

        if change and obj.pk:
            previous_paid = Order.objects.filter(pk=obj.pk).values_list('paid', flat=True).first()
            obj._should_mark_as_paid = obj.paid and not previous_paid

            if obj._should_mark_as_paid:
                obj.paid = False

        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if getattr(form.instance, '_should_mark_as_paid', False):
            try:
                form.instance.mark_as_paid()
            except OrderInventoryError as exc:
                self.message_user(
                    request,
                    f"Lageruppdateringen kunde inte genomföras: {exc}",
                    level=messages.ERROR,
                )

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
