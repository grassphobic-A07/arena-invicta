from django import forms
from .models import Match, Team

class MatchUpdateForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ["home_score", "away_score", "status"]

    def clean_home_score(self):
        v = self.cleaned_data["home_score"]
        if v is None or v < 0:
            raise forms.ValidationError("Skor home tidak boleh negatif.")
        return v

    def clean_away_score(self):
        v = self.cleaned_data["away_score"]
        if v is None or v < 0:
            raise forms.ValidationError("Skor away tidak boleh negatif.")
        return v

    def clean(self):
        cleaned = super().clean()
        # contoh validasi tambahan (opsional):
        # jika status FINISHED, skor boleh 0-99 saja
        for k in ("home_score", "away_score"):
            if cleaned.get(k) is not None and cleaned[k] > 99:
                self.add_error(k, "Skor terlalu besar (maksimal 99).")
        return cleaned

class MatchCreateForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ["season", "date", "home_team", "away_team", "home_score", "away_score", "status"]

    def __init__(self, *args, **kwargs):
        league = kwargs.pop("league", None)
        super().__init__(*args, **kwargs)
        # filter pilihan tim agar satu liga
        if league is not None:
            self.fields["home_team"].queryset = Team.objects.filter(league=league).order_by("name")
            self.fields["away_team"].queryset = Team.objects.filter(league=league).order_by("name")

    def clean(self):
        cleaned = super().clean()
        ht = cleaned.get("home_team")
        at = cleaned.get("away_team")
        if ht and at:
            if ht == at:
                self.add_error("away_team", "Tim kandang dan tamu tidak boleh sama.")
            if ht.league_id != at.league_id:
                self.add_error("away_team", "Kedua tim harus berasal dari liga yang sama.")
        return cleaned