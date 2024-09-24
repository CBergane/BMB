from django.contrib import admin
from django.utils import timezone
from django.db.models import Case, When, Value, BooleanField
from .models import Meddelande

class MeddelandeAdmin(admin.ModelAdmin):
    list_display = ('text', 'start_date', 'end_date', 'is_active', 'status_indicator')
    list_filter = ('is_active', 'start_date', 'end_date')
    actions = ['make_active', 'make_inactive', 'update_status_based_on_date']
    date_hierarchy = 'start_date'  # Lägg till detta för att navigera genom datum

    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = "Aktivera valda meddelanden"

    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = "Inaktivera valda meddelanden"

    def update_status_based_on_date(self, request, queryset):
        now = timezone.now()
        queryset.update(
            is_active=Case(
                When(start_date__lte=now, end_date__gte=now, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )
    update_status_based_on_date.short_description = "Uppdatera status baserat på datum"

    def status_indicator(self, obj):
        if obj.is_active and obj.end_date < timezone.now():
            return 'Kommer att inaktiveras snart'
        elif obj.is_active:
            return 'Aktiv'
        return 'Inaktiv'
    status_indicator.short_description = 'Status Indikation'

    def save_model(self, request, obj, form, change):
        """ Anpassad spara för att automatiskt ställa in is_active baserat på datum. """
        if obj.start_date <= timezone.now() <= obj.end_date:
            obj.is_active = True
        else:
            obj.is_active = False
        super().save_model(request, obj, form, change)

admin.site.register(Meddelande, MeddelandeAdmin)