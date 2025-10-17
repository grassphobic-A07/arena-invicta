import datetime
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Profile
from .forms import ProfileForm
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import LoginForm, RegisterWithRoleForm

def register(request):
    """
    GET  -> tampilkan form UserCreationForm (username, password1, password2)
    POST -> valid? simpan user lalu redirect ke halaman login
    """
    if request.method == "POST":
        form = RegisterWithRoleForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get("role")
            if role == "writer":
                group, _ = Group.objects.get_or_create(name="Writer")
                group.user_set.add(user)

            return redirect("accounts:login")
        else:
            form.add_error_styles()
    else:
        form = RegisterWithRoleForm()

    context = {
        'form': form
    }
    return render(request, "register.html", context)

def login_user(request):
    """
    GET  -> tampilkan LoginForm (username, password)
    POST -> valid? login() lalu:
            - kalau ada ?next= pakai itu (agar tim news/quiz bisa pakai proteksi)
            - kalau tidak ada, ke 'home'
    + Simpan cookie 'last_login' 
    """
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get('next') or reverse('accounts:home')

            response = HttpResponseRedirect(next_url)
            response.set_cookie('last_login', str(datetime.datetime.now()))
            return response
        else:
            form.add_error_styles()

    else:
        form = LoginForm(request)
    
    context = {
        'form': form
    }
    return render(request, "login.html", context)

def logout_user(request):
    """
    Logout dan hapus cookie last_login (biar bersih), lalu kembali ke login.
    """
    logout(request)
    response = redirect('accounts:login')
    response.delete_cookie('last_login')
    return response

# Kalo sudah login, akan diarahkan ke halaman beranda
def home(request):
    """
    Halaman sederhana sesudah login.
    """
    # hanya query groups kalau sudah login
    roles = []
    if request.user.is_authenticated:
        roles = list(request.user.groups.values_list('name', flat=True))

    context = {
        'username': request.user.username,
        'last_login': request.COOKIES.get('last_login', 'never'),
        'roles': roles,  # list nama role (agar template tidak memicu query lagi)
    }
    return render(request, 'home.html', context)

@login_required
def profile_detail(request):
    """
    Tampilkan profil user yang sedang login.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)  # Menggunakan related_name 'profile' dari OneToOneField
    roles = list(request.user.groups.values_list('name', flat=True))

    context = {
        'profile': profile,
        'roles': roles,
        "last_login": request.COOKIES.get("last_login", "never"),
    }

    return render(request, 'profile_detail.html', context)

@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile berhasil diperbarui.")
            return redirect('accounts:profile_detail')
    else:
        form = ProfileForm(instance=profile)

    context = {
        'form': form
    }
    return render(request, 'profile_edit.html', context)