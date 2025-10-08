from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
