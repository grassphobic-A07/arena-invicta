# news/management/commands/populate_news.py
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from news.models import News  # Sesuaikan path impor jika perlu
from faker import Faker

class Command(BaseCommand):
    help = 'Populates the database with dummy news articles'

    def add_arguments(self, parser):
        # Argumen untuk jumlah berita yang akan dibuat
        parser.add_argument('count', type=int, help='Number of news articles to create')

    def handle(self, *args, **options):
        fake = Faker() # Inisialisasi Faker untuk data palsu
        count = options['count'] # Ambil jumlah dari argumen command line

        # --- Cari User Author ---
        author = None
        # Prioritas 1: User pertama dengan role 'content_staff'
        author = User.objects.filter(profile__role='content_staff').first() 
        
        # Prioritas 2: Jika tidak ada staff, cari superuser pertama
        if not author:
            author = User.objects.filter(is_superuser=True).first()
            
        # Prioritas 3: Jika tidak ada superuser, ambil user pertama yang ada
        if not author:
            author = User.objects.first()

        # Jika tidak ada user sama sekali, hentikan command
        if not author:
            self.stdout.write(self.style.ERROR(
                'No suitable author user found. '
                'Please create a superuser or a user with profile role "content_staff".'
            ))
            return
        else:
             self.stdout.write(f'Using author: {author.username}')

        # Ambil daftar pilihan valid dari model News
        categories = [choice[0] for choice in News.CATEGORY_CHOICES]
        sports = [choice[0] for choice in News.SPORTS_CHOICES]

        # Loop untuk membuat berita sejumlah 'count'
        created_count = 0
        for i in range(count):
            title = fake.sentence(nb_words=random.randint(5, 10)) # Judul acak
            content = "\n\n".join(fake.paragraphs(nb=random.randint(3, 7))) # Konten acak (3-7 paragraf)
            category = random.choice(categories) # Pilih kategori acak
            sport = random.choice(sports)         # Pilih sport acak
            thumbnail = f"https://picsum.photos/seed/{fake.uuid4()}/800/400" # URL gambar placeholder acak
            is_featured = random.choice([True, False, False]) # 1/3 kemungkinan jadi featured
            news_views = random.randint(0, 150) # Jumlah views acak

            try:
                News.objects.create(
                    title=title,
                    content=content,
                    category=category,
                    sports=sport,
                    thumbnail=thumbnail,
                    is_featured=is_featured,
                    news_views=news_views, # Set views acak
                    author=author # Set author yang ditemukan
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to create news article {i+1}: {e}'))


        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} news articles'))

# pip install Faker
# python manage.py populate_news 100