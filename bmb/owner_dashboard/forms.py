from django import forms
from django.forms import inlineformset_factory

from products.models import Category, ProductVariant, Produkt


INPUT_CLASS = (
    'mt-2 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 '
    'text-sm text-gray-900 outline-none transition focus:border-gray-900 '
    'focus:ring-2 focus:ring-[#97d700]'
)
CHECKBOX_CLASS = (
    'h-5 w-5 rounded border-gray-300 text-gray-900 '
    'focus:ring-2 focus:ring-[#97d700]'
)


class OwnerProductFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Sök')
    status = forms.ChoiceField(
        required=False,
        label='Publiceringsstatus',
        choices=(('', 'Alla statusar'), *Produkt.PublicationStatus.choices),
    )
    active = forms.ChoiceField(
        required=False,
        label='Aktivitet',
        choices=(('', 'Alla'), ('yes', 'Aktiv'), ('no', 'Inaktiv')),
    )
    category = forms.ModelChoiceField(
        required=False,
        label='Kategori',
        queryset=Category.objects.none(),
        empty_label='Alla kategorier',
    )
    low_stock = forms.BooleanField(
        required=False,
        label='Endast lågt lager (5 eller färre)',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.order_by('namn')
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = CHECKBOX_CLASS
            else:
                field.widget.attrs['class'] = INPUT_CLASS


class OwnerProductForm(forms.ModelForm):
    class Meta:
        model = Produkt
        fields = (
            'namn',
            'category',
            'beskrivning',
            'pris',
            'inventory',
            'unit',
            'discount_percentage',
            'is_active',
            'is_fabric',
            'is_stubbie',
            'is_bmb_exclusive',
            'bredd',
            'vikt',
            'length',
            'blandning',
            'kvalitet',
            'färg',
            'motiv',
            'wash_instructions',
            'image',
            'image2',
            'image3',
            'image4',
            'image_url',
        )
        labels = {
            'namn': 'Produktnamn',
            'category': 'Kategori',
            'beskrivning': 'Beskrivning',
            'pris': 'Pris',
            'inventory': 'Lager',
            'unit': 'Enhet',
            'discount_percentage': 'Rabatt i procent',
            'is_active': 'Aktiv för försäljning',
            'is_fabric': 'Tygprodukt',
            'is_stubbie': 'Stuvbit',
            'is_bmb_exclusive': 'BMB Exclusive',
            'bredd': 'Bredd (cm)',
            'vikt': 'Vikt (gram)',
            'length': 'Stuvbitens längd (dm)',
            'blandning': 'Blandning',
            'kvalitet': 'Kvalitet',
            'färg': 'Färg',
            'motiv': 'Motiv',
            'wash_instructions': 'Tvättråd',
            'image': 'Huvudbild',
            'image2': 'Bild 2',
            'image3': 'Bild 3',
            'image4': 'Bild 4',
            'image_url': 'Extern bildadress',
        }
        help_texts = {
            'is_active': (
                'Aktiv styr om produkten kan säljas. Publiceringsstatus styr '
                'separat om den visas publikt.'
            ),
            'wash_instructions': 'Håll Ctrl intryckt för att välja flera tvättråd.',
            'image_url': 'Används endast för befintliga externa produktbilder.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.order_by('namn')
        self.fields['wash_instructions'].queryset = (
            self.fields['wash_instructions'].queryset.order_by('name')
        )

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = CHECKBOX_CLASS
            else:
                field.widget.attrs['class'] = INPUT_CLASS


class OwnerProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ('color', 'allow_custom_text', 'custom_text', 'additional_price')
        labels = {
            'color': 'Färgvariant',
            'allow_custom_text': 'Tillåt egen text',
            'custom_text': 'Förvald text',
            'additional_price': 'Pristillägg',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = CHECKBOX_CLASS
            else:
                field.widget.attrs['class'] = INPUT_CLASS


OwnerProductVariantFormSet = inlineformset_factory(
    Produkt,
    ProductVariant,
    form=OwnerProductVariantForm,
    fields=('color', 'allow_custom_text', 'custom_text', 'additional_price'),
    extra=1,
    can_delete=True,
)
