from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from django.db.models import Count
from products.models import Produkt, Category

from .forms import SignUpForm

def send_contact_email(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        if not all([name, email, message]):
            return JsonResponse({'status': 'error', 'message': 'Alla fält måste fyllas i.'})

        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'status': 'error', 'message': 'Ogiltig e-postadress.'})

        if any(char in message for char in ['<', '>', 'script', 'alert']):
            return JsonResponse({'status': 'error', 'message': 'Ogiltiga tecken i meddelandet.'})

        if not name.replace(' ', '').isalpha():
            return JsonResponse({'status': 'error', 'message': 'Namnet får endast innehålla bokstäver.'})

        email_body = f"Namn: {name}\nE-post: {email}\n\nMeddelande:\n{message}"

        # Skicka e-post
        send_mail(
            subject=f"Meddelande från {name} via Kontaktformulär",
            message=email_body,
            from_email=email,
            recipient_list=['bmb@bramycketbattre.com'],
            fail_silently=False,
        )

        return JsonResponse({'status': 'success', 'message': 'E-post skickad'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Endast POST-metoden är tillåten'})


def frontpage(request):
    produkt = Produkt.objects.all()[0:8]
    return render(request, 
    'core/frontpage.html',
    {'produkt': produkt},
    )

def news(request):
    # Calculate the date two months ago from now
    two_months_ago = timezone.now() - timedelta(days=60)

    # Filter products added in the last two months
    recent_products = Produkt.objects.filter(skapad__gte=two_months_ago)[:8]

    return render(request, 'core/news.html', {'produkt': recent_products})

def about(request):
    return render(request, 'core/about.html', )

def shop(request):
    categories = Category.objects.filter(parent__isnull=True).annotate(num_subcats=Count('children')).order_by('-num_subcats')  # Endast överordnade kategorier
    active_category_slug = request.GET.get('category', None)
    products = Produkt.objects.none()  # Starta med en tom QuerySet

    if active_category_slug:
        active_category = Category.objects.filter(slug=active_category_slug).first()
        if active_category:
            if active_category.parent:  # Om det är en underkategori
                products = Produkt.objects.filter(category=active_category, is_stubbie=False)
            else:  # Om det är en överkategori
                subcategories = active_category.children.all()
                products = Produkt.objects.filter(category__in=subcategories, is_stubbie=False)

    query = request.GET.get('query', '')
    if query:
        products = products.filter(Q(namn__icontains=query) | Q(beskrivning__icontains=query))

    context = {
        'categories': categories,
        'products': products,
        'active_category': active_category_slug,
    }

    return render(request, 'core/shop.html', context)

def discounted_products(request):
    # Get all products with a discount_percentage greater than 0
    discounted_products = Produkt.objects.filter(discount_percentage__gt=0, is_active=True)

    return render(request, 'core/discounted_products.html', {
        'discounted_products': discounted_products
    })

def stubbie_view(request):
    stubbies = Produkt.objects.filter(is_stubbie=True, is_active=True)
    return render(request, 'core/stubbie_template.html', {'stubbies': stubbies})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = SignUpForm()

    return render(request, 'core/signup.html', {'form': form})


@login_required
def myaccount(request):
    return render(request, 'core/myaccount.html', )

@login_required
def edit_myaccount(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.save()

        return redirect('myaccount')
    return render(request, 'core/edit_myaccount.html', )