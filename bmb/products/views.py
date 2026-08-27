from urllib.parse import parse_qs, urlencode, urlsplit

from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Category, Produkt, Review


def _category_return_context(produkt):
    if produkt.category.slug:
        category_query = urlencode({'category': produkt.category.slug})
        return f"{reverse('shop')}?{category_query}", produkt.category.namn

    return reverse('shop'), 'Butik'


def _validated_return_context(request, produkt):
    fallback_url, fallback_label = _category_return_context(produkt)
    return_to = request.GET.get('return_to', '')

    if not (
        return_to.startswith('/')
        and not return_to.startswith('//')
        and url_has_allowed_host_and_scheme(
            return_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        return fallback_url, fallback_label

    parsed_return_to = urlsplit(return_to)
    listing_labels = {
        reverse('discounted_products'): 'REA',
        reverse('news'): 'Nyheter',
        reverse('stubbies'): 'Stuvbitar',
        reverse('bmb_exclusive_products'): 'BMB Exclusive',
    }
    shop_url = reverse('shop')

    if parsed_return_to.path == shop_url:
        category_slug = parse_qs(parsed_return_to.query).get(
            'category',
            [None],
        )[-1]
        category = Category.objects.filter(slug=category_slug).only('namn').first()
        return return_to, category.namn if category else 'Butik'

    if parsed_return_to.path in listing_labels:
        return return_to, listing_labels[parsed_return_to.path]

    return fallback_url, fallback_label


def _category_navigation(produkt):
    category_products = Produkt.objects.public().filter(
        category_id=produkt.category_id,
    )
    previous_product = (
        category_products
        .filter(
            Q(skapad__gt=produkt.skapad)
            | Q(skapad=produkt.skapad, pk__gt=produkt.pk)
        )
        .order_by('skapad', 'pk')
        .first()
    )
    next_product = (
        category_products
        .filter(
            Q(skapad__lt=produkt.skapad)
            | Q(skapad=produkt.skapad, pk__lt=produkt.pk)
        )
        .order_by('-skapad', '-pk')
        .first()
    )
    related_products = (
        category_products
        .exclude(pk=produkt.pk)
        .order_by('-skapad', '-pk')[:4]
    )

    return previous_product, next_product, related_products


def produkt(request, slug):
    produkt = get_object_or_404(
        Produkt.objects.public().select_related('category__parent'),
        slug=slug,
    )

    # Kontrollera om någon variant tillåter anpassad text
    show_custom_text_field = produkt.variants.filter(allow_custom_text=True).exists()

    if produkt.is_fabric:
        produkt.inventory_in_meters = produkt.inventory / 10
    else:
        produkt.inventory_in_meters = produkt.inventory

    if request.method == 'POST':
        rating = request.POST.get('rating', 3)
        content = request.POST.get('content', '')

        if content:
            reviews = Review.objects.filter(created_by=request.user, product=produkt)

            if reviews.count() > 0:
                review = reviews.first()
                review.rating = rating
                review.content = content
                review.save()
            else:
                review = Review.objects.create(
                    product=produkt,
                    rating=rating,
                    content=content,
                    created_by=request.user
                )

            return redirect('produkt', slug=slug)

    return_to, return_label = _validated_return_context(request, produkt)
    previous_product, next_product, related_products = _category_navigation(
        produkt,
    )

    return render(request, 'products/product.html', {
        'produkt': produkt,
        'show_custom_text_field': show_custom_text_field,
        'return_to': return_to,
        'return_label': return_label,
        'previous_product': previous_product,
        'next_product': next_product,
        'related_products': related_products,
    })


