from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import StoreOwnerRegistrationForm
from django.contrib.auth import authenticate, login
from store.models import Store

def register_store_owner(request):
    if request.method == 'POST':
        form = StoreOwnerRegistrationForm(request.POST)
        if form.is_valid():
            # Create the user
            username = form.cleaned_data.get('username')
            phone_number = form.cleaned_data.get('phone_number')

            # Create the user and set phone number as the password
            user = User.objects.create_user(
                username=username,
                password=phone_number  # Use phone number as the password
            )

            # Create the store
            store = Store.objects.create(
                name=form.cleaned_data.get('name'),
                owner=user,
                address=form.cleaned_data.get('address'),
                phone_number=phone_number
            )

            # Automatically log in the user after registration
            login(request, user)
            messages.success(request, 'Mmiliki wa Duka amesajiliwa kwa mafanikio!')
            return redirect('dashboard')  # Redirect to the store dashboard
    else:
        form = StoreOwnerRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


# def store_owner_login(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')

#         # Authenticate user by username and phone number (as password)
#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             login(request, user)
#             messages.success(request, 'Umefanikiwa kuingia kikamilifu!')
#             return redirect('dashboard')  # Redirect to the store dashboard
#         else:
#             messages.error(request, 'Jina la mtumiaji au nambari ya simu si sahihi.')
    
#     return render(request, 'users/login.html')
def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if hasattr(user, 'seller_profile'):
                return redirect('add_sale')  # Redirect sellers to the add sale page
            else:
                return redirect('dashboard')  # Redirect store owners to their dashboard
    return render(request, 'users/login.html')