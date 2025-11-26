import json
import datetime, os
from sqlite3 import IntegrityError
from django.contrib.auth import authenticate, login, logout
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
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.password_validation import validate_password

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
            next_url = request.GET.get('next') or reverse('news:show_news')

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
    response = redirect('news:show_news')
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
        if request.user.is_superuser:
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
    """Admin dashboard: boleh semua superuser, dan tetap kompat untuk arena_admin (root)."""
    return user.is_authenticated and (
        user.is_superuser or user.username == os.getenv("ARENA_ADMIN_USER", "arena_admin")
    )

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
                role  = (request.POST.get("role") or "registered").strip().lower()

                if not uname or not pwd:
                    messages.error(request, "Username & password wajib diisi.")
                    return redirect(request.path + "?tab=users")
                if User.objects.filter(username=uname).exists():
                    messages.error(request, "Username sudah dipakai.")
                    return redirect(request.path + "?tab=users")

                u = User.objects.create_user(username=uname, password=pwd, is_active=True)
                p, _ = Profile.objects.get_or_create(user=u)

                if role == "admin":
                    if request.user.username != os.getenv("ARENA_ADMIN_USER", "arena_admin"):
                        messages.error(request, "Hanya admin induk yang bisa membuat Admin baru.")
                        return redirect(request.path + "?tab=users")
                    
                    u.is_active = True
                    u.is_superuser = True
                    u.is_staff = False
                    u.save(update_fields=["is_active", "is_superuser", "is_staff"])
                    u.groups.filter(name="Content Staff").delete()

                elif role == "content_staff":
                    p.role = "content_staff"; 
                    p.save(update_fields=["role"])
                    Group.objects.get_or_create(name="Content Staff")[0].user_set.add(u)

                else:
                    p.role = "registered"; p.save(update_fields=["role"])
                    u.groups.filter(name="Content Staff").delete()

                messages.success(request, f"User {uname} dibuat.")
                return redirect(request.path + "?tab=users")

            elif op == "set_role":
                uid  = int(request.POST["user_id"])
                role = (request.POST.get("role") or "registered").strip().lower()
                u = User.objects.select_related("profile").get(pk=uid)

                # Jangan turunkan admin terakhir
                if (u.is_superuser or u.username == os.getenv("ARENA_ADMIN_USER", "arena_admin")) and role != "admin":
                    other_admins = User.objects.filter(is_superuser=True, is_active=True).exclude(id=u.id).count()
                    if other_admins == 0:
                        messages.error(request, "Tidak bisa menurunkan Admin terakhir.")
                        return redirect(request.path + "?tab=users")

                if role == "admin":
                    if request.user.username != os.getenv("ARENA_ADMIN_USER", "arena_admin"):
                        messages.error(request, "Hanya admin induk yang bisa mempromosikan ke Admin.")
                        return redirect(request.path + "?tab=users")
                    u.is_superuser = True
                    u.is_staff = False
                    u.save(update_fields=["is_superuser", "is_staff"])
                    # role konten biarkan apa adanya
                    messages.success(request, f"{u.username} dipromosikan menjadi Admin.")

                elif role == "content_staff":
                    if u.is_superuser:
                        u.is_superuser = False
                        u.is_staff = False
                        u.save(update_fields=["is_superuser", "is_staff"])
                    u.profile.role = "content_staff"; u.profile.save(update_fields=["role"])
                    Group.objects.get_or_create(name="Content Staff")[0].user_set.add(u)
                    messages.success(request, f"Role {u.username} → Content Staff.")

                else:  # registered
                    if u.is_superuser:
                        u.is_superuser = False
                        u.is_staff = False
                        u.save(update_fields=["is_superuser", "is_staff"])
                    u.profile.role = "registered"; u.profile.save(update_fields=["role"])
                    u.groups.filter(name="Content Staff").delete()
                    messages.success(request, f"Role {u.username} → Registered.")

                return redirect(request.path + "?tab=users")


            elif op == "toggle_active":
                uid = int(request.POST["user_id"])
                u = User.objects.get(pk=uid)
                if u.is_superuser or u.username == os.getenv("ARENA_ADMIN_USER", "arena_admin"):
                    messages.error(request, "Tidak boleh mengubah status/menghapus akun Admin.")
                    return redirect(request.path + "?tab=users")

                else:
                    u.is_active = not u.is_active
                    u.save(update_fields=["is_active"])
                    messages.success(request, f"User \"{u.username}\" {'diaktifkan' if u.is_active else 'dinonaktifkan'}.")
                return redirect(request.path + "?tab=users")

            elif op == "delete_user":
                uid = int(request.POST["user_id"])
                u = User.objects.get(pk=uid)
                # if u.is_superuser or u.username == os.getenv("ARENA_ADMIN_USER", "arena_admin"):
                #     messages.error(request, "Tidak boleh mengubah status/menghapus akun Admin.")
                #     return redirect(request.path + "?tab=users")
                # else:
                u.delete()
                messages.success(request, "Akun berhasil dihapus.")
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
        "list_of_users": list_of_users,          # List semua user yang ada
        "q": q,
        "counts": counts,                        # Hitung berapa banyak user
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
        return redirect("news:show_news")

    if _is_ajax(request):
        return JsonResponse({
            "Ok": True, 
            "redirect_url": reverse("news:show_news"),
            "message": "Akun berhasil dihapus."
        })
    
    messages.success(request, "Akun berhasil dihapus.")
    return redirect("news:show_news")


# Khusus API untuk via mobile app
@csrf_exempt
def login_api(request):
    if request.method != 'POST':
        return JsonResponse({"status": False, "message": "Metode tidak diizinkan, gunakan POST"}, status=405)

    username = ""
    password = ""

    # --- PERBAIKAN DI SINI ---

    # Prioritas 1: Cek apakah data dikirim sebagai Form Data standar (request.POST)
    # Ini adalah cara default pbp_django_auth mengirim data.
    if request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')
    
    # Prioritas 2: Jika request.POST kosong, coba baca sebagai JSON Body
    # Ini sebagai fallback jika cara pengiriman di Flutter diubah menjadi JSON eksplisit di masa depan.
    else:
        try:
            # Cek apakah body tidak kosong sebelum mencoba loads
            if request.body:
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
            else:
                 return JsonResponse({"status": False, "message": "Data login tidak ditemukan"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"status": False, "message": "Format data tidak valid (Gunakan Form Data atau JSON)"}, status=400)

    # --- AKHIR PERBAIKAN ---


    # Coba autentikasi user
    user = authenticate(request, username=username, password=password)

    if user is not None:
        # --- PERBAIKAN DI SINI ---
        # Selalu lakukan login() agar session lama (jika ada) diganti dengan yang baru
        login(request, user) 
        # -------------------------

        if user.is_superuser:
            role_str = "admin"
        else:
            profile = getattr(user, "profile", None)
            role_str = profile.role if profile else "registered"
        
        profile = getattr(user, "profile", None)
        avatar_url = profile.avatar_url if profile else ""

        return JsonResponse({
            "status": True,
            "message": "Login Berhasil!",
            "username": user.username,
             "role": role_str,
             "avatar_url": avatar_url,
        }, status=200)
    else:
        return JsonResponse({
            "status": False,
            "message": "Username atau password salah."
        }, status=401)
    

@csrf_exempt
def register_api(request):
    if request.method != 'POST':
         return JsonResponse({"status": False, "message": "Metode tidak diizinkan, gunakan POST"}, status=405)

    try:
        # --- PERBAIKAN DI SINI: Prioritaskan request.POST (Form Data) ---
        if request.POST:
            data = request.POST
        elif request.body:
             # Fallback ke JSON jika perlu
            data = json.loads(request.body)
        else:
             return JsonResponse({"status": False, "message": "Data registrasi tidak ditemukan"}, status=400)
        # ----------------------------------------------------------------

        # Ambil data menggunakan .get() dari dictionary 'data'
        username = data.get('username', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirmPassword', '')
        role_input = data.get('role', 'registered').strip().lower() # 'content_staff' atau 'registered'

        # --- SISA LOGIKA SAMA SEPERTI SEBELUMNYA ---
        
        # 2. Validasi Input Dasar
        if not username or not password:
            return JsonResponse({"status": False, "message": "Username dan password wajib diisi."}, status=400)

        if password != confirm_password:
            return JsonResponse({"status": False, "message": "Password dan konfirmasi password tidak cocok."}, status=400)

        # 3. Cek apakah username sudah ada
        if User.objects.filter(username=username).exists():
            return JsonResponse({"status": False, "message": "Username sudah digunakan."}, status=409)

        # 4. Validasi kekuatan password (Opsional tapi disarankan)
        # try: validate_password(password) ...

        # 5. Proses Pembuatan Akun
        user = User.objects.create_user(username=username, password=password)
        
        # Tentukan role final
        final_role = 'content_staff' if role_input == 'content_staff' else 'registered'
        
        # Buat/Update Profile
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = final_role
        profile.save(update_fields=["role"])

        # Atur Grup Content Staff
        content_staff_group, _ = Group.objects.get_or_create(name="Content Staff")
        if final_role == "content_staff":
            content_staff_group.user_set.add(user)
        else:
            content_staff_group.user_set.remove(user) # Hapus jika ada

        # 6. Berhasil
        return JsonResponse({
            "status": True,
            "message": "Registrasi berhasil! Silakan login.",
            "username": user.username,
            "role": final_role
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"status": False, "message": "Format data tidak valid."}, status=400)
    except IntegrityError:
         return JsonResponse({"status": False, "message": "Terjadi kesalahan database."}, status=409)
    except Exception as e:
        print(f"Register API Error: {e}")
        return JsonResponse({"status": False, "message": f"Error server: {str(e)}"}, status=500)

@csrf_exempt
def logout_api(request):
    logout(request)
    response = JsonResponse({
        "status": True,
        "message": "Logout berhasil."
    }, status=200)

    response.delete_cookie('last_login')
    return response


@login_required
def user_profile_api_json(request):
    """
    API Khusus untuk mengambil data profil user yang sedang login dalam format JSON.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.user.is_superuser:
        role_label = "admin"
    else:
        role_label = profile.role

    return JsonResponse({
        "username": request.user.username,
        "display_name": profile.display_name or "",
        "favourite_team": profile.favorite_team or "",
        "avatar_url": profile.avatar_url or "",
        "bio": profile.bio or "",
        "role": role_label,
    })

@csrf_exempt
def edit_profile_api(request):
    """
    API khusus untuk Flutter melakukan update profile.
    Pasti mengembalikan JSON.
    """
    if request.method != 'POST':
        return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)

    try:
        profile = request.user.profile
        
        # 1. Ambil data (support Form Data & JSON)
        data = request.POST
        if not data and request.body:
            import json
            data = json.loads(request.body)

        # 2. Update Field
        display_name = data.get('display_name')
        favorite_team = data.get('favourite_team') # Perhatikan ejaan variabel di Flutter kamu 'favourite_team'
        avatar_url = data.get('avatar_url')
        bio = data.get('bio')

        if display_name is not None:
            profile.display_name = display_name
        if favorite_team is not None:
            profile.favorite_team = favorite_team
        if avatar_url is not None:
            profile.avatar_url = avatar_url
        if bio is not None:
            profile.bio = bio
            
        profile.save()

        return JsonResponse({
            "status": True,
            "message": "Profile berhasil diupdate!",
            "username": request.user.username
        }, status=200)

    except Exception as e:
        return JsonResponse({"status": False, "message": f"Error: {str(e)}"}, status=500)
    
@csrf_exempt
def admin_dashboard_api(request):
    """
    API untuk Admin Dashboard di Flutter.
    Mengembalikan statistik dan daftar user dalam format JSON.
    Juga menangani aksi (POST) seperti set_role, toggle_active, delete.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Unauthorized"}, status=401)
    
    if not (request.user.is_superuser or request.user.username == os.getenv("ARENA_ADMIN_USER", "arena_admin")):
        return JsonResponse({"status": False, "message": "Forbidden. Admin only"}, status=403)
    
    if request.method == "POST":
        try:
            data = request.POST
            if not data and request.body:
                data = json.loads(request.body)

            op = data.get("op", "")
<<<<<<< HEAD

            if op == "set_role":
=======
            
            # === LOGIKA BARU: CREATE USER ===
            if op == "create_user":
                username = data.get("username", "").strip()
                password = data.get("password", "").strip()
                role = data.get("role", "registered").strip().lower()

                # 1. Validasi Input
                if not username or not password:
                    return JsonResponse({"status": False, "message": "Username dan Password wajib diisi."})
                
                if User.objects.filter(username=username).exists():
                    return JsonResponse({"status": False, "message": "Username sudah digunakan."})

                # 2. Buat User Baru
                new_user = User.objects.create_user(username=username, password=password)
                
                # 3. Set Role Awal
                content_group, _ = Group.objects.get_or_create(name="Content Staff")
                
                # Inisialisasi profile (jika belum otomatis dibuat oleh signals)
                profile, _ = Profile.objects.get_or_create(user=new_user)

                if role == "admin":
                    # Hanya admin induk yang boleh bikin admin lain (Opsional, tapi aman)
                    if request.user.username != os.getenv("ARENA_ADMIN_USER", "arena_admin"):
                         new_user.delete() # Batalkan pembuatan
                         return JsonResponse({"status": False, "message": "Hanya Super Admin yang bisa membuat Admin baru."})

                    new_user.is_superuser = True
                    new_user.is_staff = True
                    new_user.save()
                
                elif role == "content_staff":
                    profile.role = "content_staff"
                    profile.save()
                    new_user.groups.add(content_group)
                
                else: # Registered
                    profile.role = "registered"
                    profile.save()
                    # Pastikan tidak masuk grup content
                    new_user.groups.remove(content_group)

                return JsonResponse({"status": True, "message": f"User {username} berhasil dibuat!"}, status=201)

            elif op == "set_role":
>>>>>>> 78e87214cee4585316763161008a30d03911abb5
                uid = int(data.get("user_id"))
                new_role = data.get("role", "registered").strip().lower()

                target_user = User.objects.select_related('profile').get(pk=uid)

                if target_user.is_superuser:
                    return JsonResponse({
                        "status": False,
                        "message": f"Tidak diizinkan. {target_user.username} adalah Admin."
                    })
                # DEBUG PRINT (Cek terminal kita saat klik tombol di HP)
                print(f"DEBUG: Mengubah {target_user.username} menjadi {new_role}")

                # Siapkan Grup Content Staff (Ambil objeknya)
                content_group, _ = Group.objects.get_or_create(name="Content Staff")

                if new_role == "admin":
                    target_user.is_superuser = True
                    target_user.is_staff = False
                    target_user.save()
                    target_user.groups.remove(content_group)

                elif new_role == "content_staff":
                    if target_user.is_superuser:
                        target_user.is_superuser = False
                        target_user.is_staff = False
                        target_user.save()

                    p = target_user.profile
                    p.role = "content_staff"
                    p.save()

                    target_user.groups.add(content_group)                    
                
                else: # registered
                    if target_user.is_superuser:
                        target_user.is_superuser = False
                        target_user.is_staff = False
                        target_user.save()

                    p = target_user.profile
                    p.role = "registered"
                    p.save()
                    target_user.groups.remove(content_group)

                return JsonResponse({"status": True, "message": f"Role {target_user.username.capitalize()} diubah ke {new_role.replace('_', ' ').title()}"}, status=200)

            # --- Aksi: Toggle Active ---
            elif op == "toggle_active":
                uid = int(data.get("user_id"))
                target_user = User.objects.get(pk=uid)
                # Jangan nonaktifkan admin
                if target_user.is_superuser:
                     return JsonResponse({"status": False, "message": "Tidak bisa menonaktifkan Admin."})

                target_user.is_active = not target_user.is_active
                target_user.save()
                status = "Aktif" if target_user.is_active else "Non-aktif"
                return JsonResponse({"status": True, "message": f"User {target_user.username} sekarang {status}"})
            
            # --- Aksi: Delete User ---
            elif op == "delete_user":
                uid = int(data.get("user_id"))
                target_user = User.objects.get(pk=uid)
                if target_user.is_superuser:
                     return JsonResponse({"status": False, "message": "Tidak bisa menghapus Admin."})
                
                target_user.delete()
                return JsonResponse({"status": True, "message": "User berhasil dihapus"})

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, status=500)
        
    
    admin_username = os.getenv("ARENA_ADMIN_USER", "arena_admin")
    counts = {
        "total": User.objects.count(),
        "registered": Profile.objects.filter(role="registered").exclude(user__username=admin_username).count(),
        "content_staff": Profile.objects.filter(role="content_staff").count(),
    }

    # Ambil List User
    users_qs = User.objects.select_related("profile").all().order_by("username")
    
    # Serialisasi manual ke List of Dict agar bisa jadi JSON
    users_data = []
    for u in users_qs:
        # Tentukan role label untuk dikirim ke flutter
        role_str = "registered"
        if u.is_superuser: 
            role_str = "admin"
        elif hasattr(u, 'profile') and u.profile.role == "content_staff": 
            role_str = "content_staff"

        users_data.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.profile.display_name if hasattr(u, 'profile') else "-",
            "role": role_str,
            "is_active": u.is_active,
            "avatar_url": u.profile.avatar_url if hasattr(u, 'profile') else "",
        })

    return JsonResponse({
        "status": True,
        "counts": counts,
        "users": users_data
    })

@csrf_exempt
def delete_account_api(request):
    """
    API untuk user menghapus akunnya sendiri via mobile app.
    """
    if request.method != 'POST':
        return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)
    
    try:
        user = request.user
        # Simpan username untuk pesan sukses sebelum dihapus
        username = user.username

        # Hapus user dari database
        user.delete()

        # Logout (Hapus session)
        logout(request)

        return JsonResponse({
            "status": True,
            "message": f"Akun {username} berhasil dihapus."
        }, status=200)

    except Exception as e:
        return JsonResponse({"status": False, "message": f"Gagal menghapus akun: {str(e)}"}, status=500)
    