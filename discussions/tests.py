import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from news.models import News

from .models import DiscussionThread, DiscussionComment


class DiscussionThreadModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='thread_author',
            password='password123',
        )

    def test_str_returns_title(self):
        thread = DiscussionThread.objects.create(title='Big Match Analysis', author=self.user)
        self.assertEqual(str(thread), 'Big Match Analysis')


class DiscussionCommentModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='commenter',
            password='password123',
        )
        self.thread = DiscussionThread.objects.create(title='Weekly Discussion', author=self.user)

    def test_str_includes_author_identifier(self):
        comment = DiscussionComment.objects.create(
            thread=self.thread,
            author=self.user,
            content='Great insights!'
        )
        self.assertIn('commenter', str(comment))


class DiscussionThreadListViewTests(TestCase):
    def test_thread_list_endpoint_renders(self):
        response = self.client.get(reverse('discussions:thread-list'))
        self.assertEqual(response.status_code, 200)


class DiscussionAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='api-user',
            password='supersecret',
        )
        self.news = News.objects.create(
            title='Derby Finals',
            content='Match preview',
            category='update',
            sports='football',
        )
        self.thread = DiscussionThread.objects.create(
            title='Tactical Breakdown',
            body='Let us discuss the formations.',
            author=self.user,
            news=self.news,
        )

    def test_list_api_filters_by_news_title(self):
        url = reverse('discussions:thread-list-api')
        response = self.client.get(url, {'q': 'Derby'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data.get('threads', [])), 1)
        self.assertEqual(data['threads'][0]['news']['uuid'], str(self.news.id))

    def test_list_api_filters_by_news_uuid(self):
        url = reverse('discussions:thread-list-api')
        response = self.client.get(url, {'q': str(self.news.id)})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data.get('threads', [])), 1)
        self.assertEqual(data['threads'][0]['title'], self.thread.title)

    def test_create_api_requires_login(self):
        url = reverse('discussions:thread-create-api')
        response = self.client.post(url, data=json.dumps({
            'news': str(self.news.id),
            'title': 'Unauthorized',
            'body': 'Should fail',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_create_api_creates_thread(self):
        self.client.login(username='api-user', password='supersecret')
        url = reverse('discussions:thread-create-api')
        payload = {
            'news': str(self.news.id),
            'title': 'Match MVP Predictions',
            'body': 'Who will shine the brightest?',
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data['thread']['news']['uuid'], str(self.news.id))
        self.assertTrue(DiscussionThread.objects.filter(title='Match MVP Predictions').exists())
