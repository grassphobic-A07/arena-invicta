import datetime, os
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
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.apps import apps
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

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = "content_staff" if role == "content_staff" else "registered"
            profile.save(update_fields=["role"])

            if role == "content_staff":
                Group.objects.get_or_create(name="Content Staff")[0].user_set.add(user)
            else:
                # Pastikan tidak nyangkut di grup Content Staff
                user.groups.filter(name="Content Staff").delete()

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
    admin_username = os.getenv("ARENA_ADMIN_USER", "arena_admin")

    role_label = None
    if request.user.is_authenticated:
        if request.user.username == admin_username:
            role_label = "Admin"
        elif getattr(getattr(request.user, "profile", None), "role", "") == "content_staff":
            role_label = "Content Staff"
        else:
            role_label = "Registered"
            
    context = {
        'username': request.user.username,
        "admin_username": admin_username,
        'last_login': request.COOKIES.get('last_login', 'never'),
        'role_label': role_label,  # list nama role (agar template tidak memicu query lagi)
    }

    return render(request, 'home.html', context)

# Admin dashboard view
def is_arena_admin(user) -> bool:
    """Admin statis: username cocok ENV"""
    return user.is_authenticated and user.username == os.getenv("ARENA_ADMIN_USER", "arena_admin")

@login_required
@require_http_methods(["GET", "POST"])
def admin_dashboard(request):
    if not is_arena_admin(request.user):
        return HttpResponseForbidden("Admin only.")

    tab = request.GET.get("tab", "users")

    # ==== ACTIONS (POST) ====
    if request.method == "POST":
        op = request.POST.get("op", "")
        try:
            if op == "create_user":
                uname = (request.POST.get("username") or "").strip()
                pwd   = (request.POST.get("password") or "").strip()
                role  = (request.POST.get("role") or "registered").strip()
                if not uname or not pwd:
                    messages.error(request, "Username & password wajib diisi.")
                elif User.objects.filter(username=uname).exists():
                    messages.error(request, "Username sudah dipakai.")
                else:
                    u = User.objects.create_user(username=uname, password=pwd, is_active=True)
                    p, _ = Profile.objects.get_or_create(user=u)
                    p.role = "content_staff" if role == "content_staff" else "registered"
                    p.save(update_fields=["role"])
                    messages.success(request, f"User {uname} dibuat.")
                return redirect(request.path + "?tab=users")

            elif op == "set_role":
                uid  = int(request.POST["user_id"])
                role = (request.POST.get("role") or "registered").strip()
                u = User.objects.select_related("profile").get(pk=uid)
                if is_arena_admin(u) and role != "registered":
                    # admin tetap admin (role konten jangan diutak-atik)
                    messages.error(request, "Akun admin tidak diubah role kontennya.")
                else:
                    u.profile.role = "content_staff" if role == "content_staff" else "registered"
                    u.profile.save(update_fields=["role"])
                    if role == "content_staff":
                        Group.objects.get_or_create(name="Content Staff")[0].user_set.add(u)
                    else:
                        u.groups.filter(name="Content Staff").delete()
                    messages.success(request, f"Role {u.username} → {u.profile.role}.")
                return redirect(request.path + "?tab=users")

            elif op == "toggle_active":
                uid = int(request.POST["user_id"])
                u = User.objects.get(pk=uid)
                if is_arena_admin(u):
                    messages.error(request, "Tidak boleh menonaktifkan akun admin.")
                else:
                    u.is_active = not u.is_active
                    u.save(update_fields=["is_active"])
                    messages.success(request, f"User \"{u.username}\" {'diaktifkan' if u.is_active else 'dinonaktifkan'}.")
                return redirect(request.path + "?tab=users")

            elif op == "delete_user":
                uid = int(request.POST["user_id"])
                u = User.objects.get(pk=uid)
                if is_arena_admin(u):
                    messages.error(request, "Tidak boleh menghapus akun admin.")
                else:
                    u.delete()
                    messages.success(request, "Akun dihapus.")
                return redirect(request.path + "?tab=users")

        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect(request.path + "?tab=users")

    # ==== DATA (GET) ====
    q = (request.GET.get("q") or "").strip()
    list_of_users = User.objects.select_related("profile").all().order_by("username")
    if q:
        list_of_users = list_of_users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(profile__display_name__icontains=q))

    admin_username = os.getenv("ARENA_ADMIN_USER", "arena_admin")
    counts = {
        "total": User.objects.count(),
        "registered": Profile.objects.filter(role="registered")
                       .exclude(user__username=admin_username).count(),
        "content_staff": Profile.objects.filter(role="content_staff").count(),
    }

    # DB browser (read-only)
    all_models = []
    for m in apps.get_models():
        lbl = f"{m._meta.app_label}.{m.__name__}"
        if m._meta.app_label in {"admin","contenttypes","sessions"}:
            continue
        all_models.append(lbl)
    all_models.sort()

    model_label = request.GET.get("model") or ""
    fields, rows = None, None
    if tab == "db" and model_label in all_models:
        app_label, model_name = model_label.split(".")
        M = apps.get_model(app_label, model_name)
        fields = [f.name for f in M._meta.fields]
        rows = [[getattr(obj, f) for f in fields] for obj in M.objects.all()[:50]]

    return render(request, "admin_dashboard.html", {
        "tab": tab, 
        "list_of_users": list_of_users, 
        "q": q,
        "counts": counts,
        "all_models": all_models, 
        "model_label": model_label,
        "fields": fields, 
        "rows": rows,
        "admin_username": admin_username,        # ← kirim ke template
    })


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

    admin_username = os.getenv("ARENA_ADMIN_USER", "arena_admin")
    subject = profile.user  # user pemilik halaman profil

    if subject.username == admin_username:
        role_label = "Admin"
    elif profile.role == "content_staff":
        role_label = "Content Staff"
    else:
        role_label = "Registered"

    return render(request, "profile_detail.html", {
        "profile": profile,
        "role_label": role_label,
        "admin_username": admin_username,
    })

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