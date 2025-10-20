import datetime
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Profile
from .forms import ProfileForm, User
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.db.models.deletion import ProtectedError

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
            role = form.cleaned_role_value()

            if role == "content_staff":
                Group.objects.get_or_create(name="Content Staff")[0].user_set.add(user)
                # Catatan: permission publish bakal otomatis “nempel” via signals post_migrate

            return redirect("accounts:login")
        else:
            if hasattr(form, "add_error_styles"):
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
            if hasattr(form, "add_error_styles"): form.add_error_styles()

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
    response = redirect('accounts:home')
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


# Untuk keperluan AJAX pada profile_edit dan delete avatar yang nantinya munculin toast
def _is_ajax(request):
    # Django 4.x tidak punya request.is_ajax()
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

@login_required
def profile_detail(request, username):
    """
    Tampilkan profil user yang sedang login.
    """
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)
    roles = list(request.user.groups.values_list('name', flat=True))
    context = {
        'profile': profile,
        'roles': roles,
    }
    return render(request, "profile_detail.html", context)

@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "GET":
        form = ProfileForm(instance=profile)

        context = {
            'form': form,
            'profile': profile,
        }

        return render(request, "profile_edit.html", context)

        # Dulu ketika belum AJAX based
        # if form.is_valid():
        #     form.save()
        #     messages.success(request, "Profile berhasil diperbarui.")
        #     return redirect('accounts:profile_detail')
        
        # if request.POST.get("clear_avatar") == "1":
        #     form.instance.avatar_url = ""  # atau None kalau fieldnya null=True
        
    if _is_ajax(request):
        form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
        if form.is_valid():
            form.save()
            # Set pesan sukses agar muncul sebagai toast di halaman tujuan dengan AJAX
            redirect_url = reverse("accounts:profile_detail", args=[request.user.username])
            return JsonResponse({
                "Ok": True, 
                "redirect_url": redirect_url,
                "message": "Profil berhasil diperbarui."
            })
        else:
            # Kirim error form untuk ditampilkan di UI
            return JsonResponse({
                "Ok": False, 
                "errors": form.errors
                }, 
                status=400
            )

    context = {
        'form': form,
        'profile': profile,
    }

    return render(request, 'profile_edit.html', context, status=400)

# Untuk delete avatar via AJAX
@login_required
@require_POST
def delete_avatar(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    # hapus file fisik & kosongkan field
    if profile.avatar_url:
        profile.avatar_url = ""
        profile.save(update_fields=["avatar_url"])
    return JsonResponse({
        "ok": True, 
        "message": "Avatar berhasil dihapus."
    })


# Untuk delete account
@login_required
@require_POST
def delete_account(request):
    """
    Hapus akun user yang sedang login.
    """
    user = request.user
    try:
        # akhiri sesi dulu, lalu hapus user (pakai salinan referensi)
        logout(request)
        user.delete()
    except ProtectedError:
        if _is_ajax(request):
            return JsonResponse({
                "Ok": False, 
                "message": "Akun tidak bisa dihapus karena terkait data lain."
                }, 
                status=409
            )
        # fallback non-AJAX
        return redirect("accounts:home")

    if _is_ajax(request):
        return JsonResponse({
            "Ok": True, 
            "redirect_url": reverse("accounts:home"),
            "message": "Akun berhasil dihapus."
        })
    
    messages.success(request, "Akun berhasil dihapus.")
    return redirect("accounts:home")