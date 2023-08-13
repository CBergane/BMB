from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q

from products.models import Produkt, Category

from .forms import SignUpForm


def frontpage(request):
    produkt = Produkt.objects.all()[0:8]
    return render(request, 
    'core/frontpage.html',
    {'produkt': produkt},
    )

def shop(request):
    categories = Category.objects.all()
    produkt = Produkt.objects.all()

    active_category = request.GET.get('category', '')

    if active_category:
        produkt = produkt.filter(category__slug=active_category)

    query = request.GET.get('query', '')

    if query:
        produkt = produkt.filter(Q(namn__icontains=query) | Q(beskrivning__icontains=query))

    context = {
        'categories': categories,
        'produkt': produkt,
        'active_category': active_category,
        }

    return render(request, 
    'core/shop.html',
    context,
    )

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