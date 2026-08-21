from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from order.models import Order
from products.models import Produkt

from .access import owner_required
from .forms import (
    OwnerProductFilterForm,
    OwnerProductForm,
    OwnerProductVariantFormSet,
)


PRODUCTS_PER_PAGE = 20


@owner_required
@require_GET
def dashboard(request):
    product_totals = Produkt.objects.aggregate(
        total=Count('pk'),
        active=Count('pk', filter=Q(is_active=True)),
        low_stock=Count('pk', filter=Q(inventory__lte=5)),
        published=Count('pk', filter=Q(publication_status=Produkt.PublicationStatus.PUBLISHED)),
        draft=Count('pk', filter=Q(publication_status=Produkt.PublicationStatus.DRAFT)),
        archived=Count('pk', filter=Q(publication_status=Produkt.PublicationStatus.ARCHIVED)),
    )
    order_totals = Order.objects.aggregate(
        total=Count('pk'),
        unpaid=Count('pk', filter=Q(paid=False)),
    )

    context = {
        'product_totals': product_totals,
        'order_totals': order_totals,
        'latest_orders': Order.objects.select_related('user')[:8],
    }
    return render(request, 'owner_dashboard/dashboard.html', context)


@owner_required
@require_GET
def product_list(request):
    products = Produkt.objects.select_related('category').order_by('-skapad', '-pk')
    filter_form = OwnerProductFilterForm(request.GET)

    if filter_form.is_valid():
        query = filter_form.cleaned_data['q']
        status = filter_form.cleaned_data['status']
        active = filter_form.cleaned_data['active']
        category = filter_form.cleaned_data['category']
        low_stock = filter_form.cleaned_data['low_stock']

        if query:
            products = products.filter(
                Q(namn__icontains=query) | Q(slug__icontains=query)
            )
        if status:
            products = products.filter(publication_status=status)
        if active:
            products = products.filter(is_active=(active == 'yes'))
        if category:
            products = products.filter(category=category)
        if low_stock:
            products = products.filter(inventory__lte=5)

    paginator = Paginator(products, PRODUCTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'owner_dashboard/product_list.html', {
        'filter_form': filter_form,
        'page_obj': page_obj,
        'filter_query': query_params.urlencode(),
    })


@owner_required
@require_http_methods(['GET', 'POST'])
def product_create(request):
    product = Produkt(publication_status=Produkt.PublicationStatus.DRAFT)
    form = OwnerProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    variant_formset = OwnerProductVariantFormSet(
        request.POST or None,
        instance=product,
        prefix='variants',
    )

    if request.method == 'POST':
        form_is_valid = form.is_valid()
        variants_are_valid = variant_formset.is_valid()
        if form_is_valid and variants_are_valid:
            with transaction.atomic():
                product = form.save(commit=False)
                product.publication_status = Produkt.PublicationStatus.DRAFT
                product.save()
                form.save_m2m()
                variant_formset.instance = product
                variant_formset.save()

            messages.success(
                request,
                f"Produkten '{product.namn}' skapades som utkast.",
            )
            return redirect('owner_dashboard:product_edit', product_id=product.pk)

    return render(request, 'owner_dashboard/product_form.html', {
        'form': form,
        'variant_formset': variant_formset,
        'product': None,
        'is_create': True,
    })


@owner_required
@require_http_methods(['GET', 'POST'])
def product_edit(request, product_id):
    product = get_object_or_404(
        Produkt.objects.select_related('category'),
        pk=product_id,
    )
    publication_status = product.publication_status
    form = OwnerProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    variant_formset = OwnerProductVariantFormSet(
        request.POST or None,
        instance=product,
        prefix='variants',
    )

    if request.method == 'POST':
        form_is_valid = form.is_valid()
        variants_are_valid = variant_formset.is_valid()
        if form_is_valid and variants_are_valid:
            with transaction.atomic():
                product = form.save(commit=False)
                product.publication_status = publication_status
                product.save()
                form.save_m2m()
                variant_formset.save()

            messages.success(request, f"Produkten '{product.namn}' sparades.")
            return redirect('owner_dashboard:product_edit', product_id=product.pk)

    return render(request, 'owner_dashboard/product_form.html', {
        'form': form,
        'variant_formset': variant_formset,
        'product': product,
        'is_create': False,
    })


@owner_required
@require_GET
def product_preview(request, product_id):
    product = get_object_or_404(
        Produkt.objects
        .select_related('category')
        .prefetch_related('wash_instructions', 'variants__color', 'reviews'),
        pk=product_id,
    )
    product.inventory_in_meters = (
        product.inventory / 10 if product.is_fabric else product.inventory
    )

    return render(request, 'products/product.html', {
        'produkt': product,
        'show_custom_text_field': product.variants.filter(
            allow_custom_text=True
        ).exists(),
        'owner_preview': True,
    })


def _set_publication_status(request, product_id, status):
    product = get_object_or_404(Produkt.objects.all(), pk=product_id)
    Produkt.objects.filter(pk=product.pk).update(publication_status=status)
    return product


@owner_required
@require_POST
def product_publish(request, product_id):
    product = _set_publication_status(
        request,
        product_id,
        Produkt.PublicationStatus.PUBLISHED,
    )
    if product.is_active:
        messages.success(request, f"Produkten '{product.namn}' publicerades.")
    else:
        messages.warning(
            request,
            f"Produkten '{product.namn}' publicerades men är inaktiv och visas "
            'därför fortfarande inte i butiken.',
        )
    return redirect('owner_dashboard:product_edit', product_id=product.pk)


@owner_required
@require_POST
def product_move_to_draft(request, product_id):
    product = _set_publication_status(
        request,
        product_id,
        Produkt.PublicationStatus.DRAFT,
    )
    messages.success(request, f"Produkten '{product.namn}' flyttades till utkast.")
    return redirect('owner_dashboard:product_edit', product_id=product.pk)


@owner_required
@require_POST
def product_archive(request, product_id):
    product = _set_publication_status(
        request,
        product_id,
        Produkt.PublicationStatus.ARCHIVED,
    )
    messages.success(request, f"Produkten '{product.namn}' arkiverades.")
    return redirect('owner_dashboard:product_edit', product_id=product.pk)
