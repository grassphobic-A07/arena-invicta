import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from accounts.models import Profile 
from news.models import News 
import uuid

# Helper function to create users with profiles easily
def create_user_with_profile(username, password, role='registered'):
    user = User.objects.create_user(username=username, password=password)
    # Pastikan Profile terbuat saat User dibuat (jika pakai signals)
    # atau buat manual
    profile, created = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.save()
    # Jika pakai Group juga, tambahkan user ke group 'Content Staff'
    if role == 'content_staff':
        staff_group, _ = Group.objects.get_or_create(name='Content Staff')
        user.groups.add(staff_group)
    return user

class NewsViewTests(TestCase):
    """Setup data awal untuk semua tes di class ini."""
    def setUp(self):
        self.client = Client() # Test client untuk simulasi request

        # Buat user biasa dan user content staff
        self.user_reg = create_user_with_profile('testuser', 'password123', 'registered')
        self.user_staff = create_user_with_profile('staffuser', 'password123', 'content_staff')

        # Buat beberapa data berita awal
        self.news1 = News.objects.create(
            title='News 1 Football Update', 
            content='Content 1', 
            category='update', 
            sports='football', 
            author=self.user_staff
        )
        self.news2 = News.objects.create(
            title='News 2 Basketball Analysis', 
            content='Content 2', 
            category='analysis', 
            sports='basketball', 
            author=self.user_staff,
            news_views=30 # Untuk tes featured/hot news
        )
        self.news_other_author = News.objects.create(
            title='News by Regular User', 
            content='Content 3', 
            category='rumor', 
            sports='tennis', 
            author=self.user_reg # Penulis user biasa
        )

    # --- Tes untuk show_news ---
    def test_show_news_view_loads(self):
        response = self.client.get(reverse('news:show_news'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'news.html') # Cek template yang dipakai
        self.assertIn('news_list', response.context) # Cek context ada news_list
        self.assertIn('featured_news', response.context) # Cek context ada featured_news
        self.assertIn('news_form', response.context) # Cek context ada news_form (untuk modal)

    def test_show_news_filtering(self):
        # Akses dengan filter football
        response = self.client.get(reverse('news:show_news'), {'filter': 'football'})
        self.assertEqual(response.status_code, 200)
        news_list = response.context['news_list']
        self.assertEqual(len(news_list), 1) # Harusnya hanya 1 berita football
        self.assertEqual(news_list[0], self.news1)
        self.assertEqual(response.context['current_filter'], 'football')

        # Akses tanpa filter (all)
        response = self.client.get(reverse('news:show_news'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['news_list']), 3) # Harusnya ada 3 berita total
        self.assertEqual(response.context['current_filter'], 'all')

    # --- Tes untuk detail_news ---
    def test_detail_news_view_loads(self):
        initial_views = self.news1.news_views
        url = reverse('news:detail_news', args=[self.news1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'detail_news.html')
        self.assertEqual(response.context['news'], self.news1)
        self.assertIn('news_form', response.context) # Cek form untuk modal ada

        # Cek apakah views bertambah
        self.news1.refresh_from_db() # Ambil data terbaru dari DB
        self.assertEqual(self.news1.news_views, initial_views + 1)

    def test_detail_news_not_found(self):
        non_existent_id = uuid.uuid4() # Buat UUID acak
        url = reverse('news:detail_news', args=[non_existent_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # --- Tes untuk add_news_ajax ---
    def test_add_news_ajax_staff_success(self):
        self.client.login(username='staffuser', password='password123')
        url = reverse('news:add_news_ajax')
        data = {
            'title': 'AJAX Test Title',
            'content': 'AJAX Test Content',
            'category': 'update',
            'sports': 'tennis',
            'thumbnail': 'http://example.com/img.jpg',
            'is_featured': 'on', # Cara checkbox mengirim data
        }
        # Kirim POST request dengan header AJAX
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest') 
        
        self.assertEqual(response.status_code, 201) # Cek status CREATED
        self.assertTrue(News.objects.filter(title='AJAX Test Title').exists()) # Cek berita terbuat
        new_news = News.objects.get(title='AJAX Test Title')
        self.assertEqual(new_news.author, self.user_staff) # Cek author benar
        self.assertEqual(new_news.sports, 'tennis')
        self.assertTrue(new_news.is_featured)

    def test_add_news_ajax_regular_user_forbidden(self):
        self.client.login(username='testuser', password='password123') # Login user biasa
        url = reverse('news:add_news_ajax')
        data = {'title': 'Fail', 'content': 'Fail', 'category': 'update', 'sports': 'football'}
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 403) # Cek Forbidden

    def test_add_news_ajax_missing_data_bad_request(self):
        self.client.login(username='staffuser', password='password123')
        url = reverse('news:add_news_ajax')
        data = {'title': 'Valid Title', 'content': ''} # Content kosong
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400) # Cek Bad Request

    def test_add_news_ajax_get_not_allowed(self):
        self.client.login(username='staffuser', password='password123')
        url = reverse('news:add_news_ajax')
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 405) # Cek Method Not Allowed

    # --- Tes untuk edit_news_ajax ---
    def test_edit_news_ajax_author_success(self):
        self.client.login(username='staffuser', password='password123') # Login sebagai author news1
        url = reverse('news:edit_news_ajax', args=[self.news1.id])
        new_title = "Updated Title AJAX"
        data = {
            'title': new_title,
            'content': self.news1.content, # Kirim data lengkap
            'category': self.news1.category,
            'sports': 'tennis', # Ubah sport
            'thumbnail': self.news1.thumbnail or "",
            'is_featured': '', # Tidak dicentang
        }
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200) # Cek OK
        json_response = response.json()
        self.assertTrue(json_response['ok']) # Cek flag 'ok'
        self.assertIn('updated successfully', json_response['message'])
        
        self.news1.refresh_from_db() # Reload data dari DB
        self.assertEqual(self.news1.title, new_title) # Cek title berubah
        self.assertEqual(self.news1.sports, 'tennis') # Cek sport berubah
        self.assertFalse(self.news1.is_featured) # Cek is_featured berubah

    def test_edit_news_ajax_non_author_forbidden(self):
        self.client.login(username='testuser', password='password123') # Login user lain
        url = reverse('news:edit_news_ajax', args=[self.news1.id]) # Coba edit news1 (milik staff)
        data = {'title': 'Hacked', 'content': 'Hacked', 'category': 'update', 'sports': 'football'}
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 403) # Cek Forbidden

    def test_edit_news_ajax_invalid_data_bad_request(self):
        self.client.login(username='staffuser', password='password123')
        url = reverse('news:edit_news_ajax', args=[self.news1.id])
        data = {
            'title': '', # Title kosong (tidak valid)
            'content': self.news1.content,
            'category': 'invalid-category', # Kategori tidak valid
            'sports': self.news1.sports,
        }
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400) # Cek Bad Request
        json_response = response.json()
        self.assertFalse(json_response['ok'])
        self.assertIn('errors', json_response) # Cek ada key 'errors'
        self.assertIn('title', json_response['errors']) # Cek ada error untuk title
        self.assertIn('category', json_response['errors']) # Cek ada error untuk category

    # --- Tes untuk delete_news_ajax ---
    def test_delete_news_ajax_author_success(self):
        """Tes author bisa menghapus berita via AJAX."""
        news_to_delete_id = self.news1.id
        self.client.login(username='staffuser', password='password123') # Login sebagai author
        url = reverse('news:delete_news_ajax', args=[news_to_delete_id])
        
        response = self.client.post(url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # Kirim POST kosong
        
        self.assertEqual(response.status_code, 200) # Cek OK
        json_response = response.json()
        self.assertTrue(json_response['ok'])
        self.assertIn('deleted', json_response['message'])
        self.assertEqual(json_response['redirect_url'], reverse('news:show_news'))

        # Cek apakah berita benar-benar terhapus
        with self.assertRaises(News.DoesNotExist):
            News.objects.get(pk=news_to_delete_id)

    def test_delete_news_ajax_non_author_forbidden(self):
        """Tes user lain tidak bisa menghapus berita (harus 403)."""
        self.client.login(username='testuser', password='password123') # Login user lain
        url = reverse('news:delete_news_ajax', args=[self.news1.id]) # Coba hapus news1
        response = self.client.post(url, {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 403) # Cek Forbidden

        # Pastikan berita tidak terhapus
        self.assertTrue(News.objects.filter(pk=self.news1.id).exists())

    def test_get_news_data_json_success(self):
        url = reverse('news:get_news_data_json', args=[self.news2.id])
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data['title'], self.news2.title)
        self.assertEqual(json_data['category'], self.news2.category)

    def test_get_news_data_json_not_found(self):
        non_existent_id = uuid.uuid4()
        url = reverse('news:get_news_data_json', args=[non_existent_id])
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 404)