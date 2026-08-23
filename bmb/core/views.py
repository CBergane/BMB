from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Prefetch, Q
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from django.db.models import Count
from order.models import Order, OrderItem
from products.models import Produkt, Category
from .access import active_account_required
from .models import Meddelande

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
    # Hämta de första 8 produkterna
    produkter = Produkt.objects.public()[:8]

    # Hämta aktiva meddelanden vars slutdatum inte har passerat
    aktiva_meddelanden = Meddelande.objects.filter(
        is_active=True,
        end_date__gte=timezone.now()
    ).order_by('-start_date')

    # Skicka både produkter och meddelanden till templaten
    context = {
        'produkter': produkter,
        'meddelanden': aktiva_meddelanden
    }
    
    return render(request, 'core/frontpage.html', context)

def news(request):
    # Calculate the date two months ago from now
    two_months_ago = timezone.now() - timedelta(days=60)

    # Filter products added in the last two months
    recent_products = Produkt.objects.public().filter(skapad__gte=two_months_ago)[:8]

    return render(request, 'core/news.html', {'produkt': recent_products})

def about(request):
    return render(request, 'core/about.html', )

def shop(request):
    categories = Category.objects.filter(parent__isnull=True).annotate(num_subcats=Count('children')).order_by('-num_subcats')  # Endast överordnade kategorier
    active_category_slug = request.GET.get('category', None)
    products = Produkt.objects.public().none()  # Starta med en tom QuerySet

    if active_category_slug:
        active_category = Category.objects.filter(slug=active_category_slug).first()
        if active_category:
            if active_category.parent:  # Om det är en underkategori
                products = Produkt.objects.public().filter(category=active_category, is_stubbie=False)
            else:  # Om det är en överkategori
                subcategories = active_category.children.all()
                products = Produkt.objects.public().filter(category__in=subcategories, is_stubbie=False)

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
    discounted_products = Produkt.objects.public().filter(discount_percentage__gt=0)

    return render(request, 'core/discounted_products.html', {
        'discounted_products': discounted_products
    })

def stubbie_view(request):
    stubbies = Produkt.objects.public().filter(is_stubbie=True)
    return render(request, 'core/stubbie_template.html', {'stubbies': stubbies})

def bmb_exclusive_products(request):
    bmb_exclusive_products = Produkt.objects.public().filter(is_bmb_exclusive=True)
    return render(request, 'core/bmb_exclusive.html', {'produkt': bmb_exclusive_products})

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


def _account_order_queryset():
    return (
        Order.objects
        .prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('produkt', 'color'),
            )
        )
        .order_by('-created_at')
    )


@active_account_required
def myaccount(request):
    orders = _account_order_queryset().filter(user=request.user)
    return render(request, 'core/myaccount.html', {'orders': orders})


@active_account_required
def myaccount_order_detail(request, order_id):
    order = get_object_or_404(
        _account_order_queryset(),
        pk=order_id,
        user=request.user,
    )
    return render(request, 'core/myaccount_order_detail.html', {'order': order})

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

