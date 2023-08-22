from django.shortcuts import render, get_object_or_404, redirect

from .models import Produkt, Review


def produkt(request, slug):

    produkt = get_object_or_404(Produkt, slug=slug)

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

    return render(request, 'products/product.html', {'produkt':produkt,})
