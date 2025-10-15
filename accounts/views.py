from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
import datetime


# Ketika arena_invicta diakses, tampilan pertama kali muncul adalah halaman register berasal dari urls.py yang ada di arena_invicta
def register(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirect ke halaman beranda jika sudah login
    
    # Bind form hanya kalau ada data POST; kalau tidak, jadikan unbound form.
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Akun berhasil dibuat! Silahkan login.")
        return redirect('accounts:login')
    
    context = {
        'form': form
    }

    return render(request, 'register.html', context)

def login_user(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')  # Redirect ke halaman beranda jika sudah login
    
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)

        # Simpan last_login ke cookie
        response = HttpResponseRedirect(request.GET.get('next') or reverse('accounts:home'))
        response.set_cookie('last_login', str(datetime.datetime.now()))
        return response
    
    context = {
        'form': form
    }

    return render(request, 'login.html', context)

def logout_user(request):
    logout(request)
    response = redirect('accounts:login')
    response.delete_cookie('last_login')
    return response

# Kalo sudah login, akan diarahkan ke halaman beranda
@login_required(login_url='/login')
def home(request):
    return render(request, 'home.html', {
        'last_login': request.COOKIES.get('last_login', 'never')
    })