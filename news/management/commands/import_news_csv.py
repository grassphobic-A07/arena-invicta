# news/management/commands/import_news_csv.py
import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from news.models import News

class Command(BaseCommand):
    help = 'Imports news articles from a specified CSV file.'

    def add_arguments(self, parser):
        # Argumen untuk menentukan path file CSV
        parser.add_argument('csv_file', type=str, help='The path to the CSV file to import.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        if not os.path.exists(csv_file_path):
            raise CommandError(f'File not found at: {csv_file_path}')

        # Cek dan ambil user penulis
        author = User.objects.filter(profile__role='content_staff').first()
        if not author:
            author = User.objects.filter(is_superuser=True).first()
        if not author:
            raise CommandError('No suitable author user found (content_staff or superuser).')

        self.stdout.write(f'Starting import using author: {author.username}')
        
        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                imported_count = 0
                for row in reader:
                    is_featured_val = row.get('is_featured', '').lower() == 'true'
                    views_val = int(row.get('news_views', 0) or 0)
                    thumbnail_val = row.get('thumbnail', '')
                    sports_val = row['sports'].lower() 

                    News.objects.create(
                        title=row['title'],
                        content=row['content'],
                        category=row['category'],
                        sports=sports_val,  # Gunakan variable yang sudah di-lowercase
                        is_featured=is_featured_val,
                        news_views=views_val,
                        thumbnail=thumbnail_val if thumbnail_val else None, 
                        author=author
                    )
                    imported_count += 1
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully imported {imported_count} news articles from {csv_file_path}'
            ))

        except Exception as e:
            raise CommandError(f'Error during import process: {e}')