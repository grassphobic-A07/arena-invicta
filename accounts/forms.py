# accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.forms.forms import NON_FIELD_ERRORS

from .models import Profile

User = get_user_model()

ROLE_CHOICES = [
    ('registered', 'Registered (Can Comment & Create Profiles)'),
    ('writer',     'Writer (Creator of News Articles)'),
    # 'editor' dan 'admin' sengaja tidak ditampilkan untuk keamanan
]

BASE_INPUT_CLS = (
    "w-full rounded-xl border border-surface/30 "
    "focus:border-sea/60 focus:ring-2 focus:ring-sea/20 "
    "px-4 py-3 text-base outline-none bg-white"
)

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": BASE_INPUT_CLS, "placeholder": "Your Username", "autofocus": True
        })
        self.fields["password"].widget.attrs.update({
            "class": BASE_INPUT_CLS + "pr-10", # Kasih ruang untuk icon mata
            "placeholder": "Password"
        })

    # Tambah class merah ke field yang error (dipanggil dari view)
    def add_error_styles(self):
        # 1) Jika ada non-field errors (mis. kredensial salah), highlight kedua field
        if self.errors.get(NON_FIELD_ERRORS):
            for name in ("username", "password"):
                if name in self.fields:
                    w = self.fields[name].widget
                    w.attrs["class"] = (w.attrs.get("class", "") + " border-red-500 ring-2 ring-red-200").strip()

        # 2) Untuk semua field yang memang error, tambahkan highlight juga
        for name in self.errors:
            if name == NON_FIELD_ERRORS:
                continue
            field = self.fields.get(name)
            if not field:
                continue
            w = field.widget
            w.attrs["class"] = (w.attrs.get("class", "") + " border-red-500 ring-2 ring-red-200").strip()

class RegisterWithRoleForm(UserCreationForm):
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Pilih Peran Anda")
    class Meta:
        model = User
        fields = ("username", "password1", "password2", "role")  # password1 & password2 sudah ada dari UserCreationForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": BASE_INPUT_CLS, "placeholder": "Your Username", "autofocus": True
        })
        self.fields["password1"].widget.attrs.update({
            "class": BASE_INPUT_CLS + "pr-10", 
            "placeholder": "Must be 8 Characters"
        })
        self.fields["password2"].widget.attrs.update({
            "class": BASE_INPUT_CLS + "pr-10", 
            "placeholder": "Repeat Password"
        })
        self.fields["role"].widget.attrs.update({
            "class": BASE_INPUT_CLS.replace("py-3", "py-2.5")
        })
    
    def add_error_styles(self):
        for name in self.errors:
            if name == NON_FIELD_ERRORS:
                continue
            field = self.fields.get(name)
            if not field:
                continue
            w = field.widget
            w.attrs["class"] = (w.attrs.get("class", "") + " border-red-500 ring-2 ring-red-200").strip()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("display_name", "favorite_team", "avatar_url", "bio")
        widgets = {
            "display_name": forms.TextInput(attrs={"class": BASE_INPUT_CLS, "placeholder": "Nama tampilan"}),
            "favorite_team": forms.TextInput(attrs={"class": BASE_INPUT_CLS, "placeholder": "Tim favorit"}),
            "avatar_url": forms.URLInput(attrs={"class": BASE_INPUT_CLS, "placeholder": "https://..."}),
            "bio": forms.Textarea(attrs={"class": BASE_INPUT_CLS, "rows": 4, "placeholder": "Tulis bio singkat"}),
        }