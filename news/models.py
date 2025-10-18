import uuid
from django.db import models

class News(models.Model):
    SPORTS_CHOICES = [
        ('football', 'Football'),
        ('basketball', 'Basketball'),
        ('tennis', 'Tennis'),
        ('volleyball', 'Volleyball'),
        ('motogp', 'Motogp')
    ]

    CATEGORY_CHOICES = [
        ('update', 'Update'),
        ('analysis', 'Analysis'),
        ('exclusive', 'Exclusive'),
        ('rumor', 'Rumor'),
        ('match', 'Match')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    sports = models.CharField(max_length=20, choices=SPORTS_CHOICES)
    thumbnail = models.URLField(blank=True, null=True)
    news_views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @property
    def is_news_hot(self):
        return self.news_views > 20

    def increment_views(self):
        self.news_views += 1
        self.save()