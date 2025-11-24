import json
import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from news.models import News

from .models import DiscussionThread, DiscussionComment, DiscussionThreadUpvote


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
        self.assertIn('views_count', data['threads'][0])
        self.assertIn('upvote_count', data['threads'][0])
        self.assertIn('summary', data['threads'][0]['news'])
        self.assertTrue(data['threads'][0]['news']['summary'])

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
        self.assertEqual(data['thread']['upvote_count'], 0)
        self.assertEqual(data['thread']['views_count'], 0)
        self.assertIn('summary', data['thread']['news'])
        self.assertTrue(data['thread']['news']['summary'])

    def test_list_api_can_return_xml_via_query_param(self):
        url = reverse('discussions:thread-list-api')
        response = self.client.get(url, {'format': 'xml'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('application/xml'))
        root = ET.fromstring(response.content)
        threads = {elem.find('id').text: elem for elem in root.findall('thread')}
        target = threads.get(str(self.thread.id))
        self.assertIsNotNone(target)
        self.assertEqual(target.find('title').text, self.thread.title)
        author = target.find('author')
        self.assertIsNotNone(author)
        self.assertEqual(author.find('username').text, self.user.username)

    def test_list_api_respects_accept_header_for_xml(self):
        url = reverse('discussions:thread-list-api')
        response = self.client.get(url, HTTP_ACCEPT='application/xml')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('application/xml'))
        root = ET.fromstring(response.content)
        self.assertGreaterEqual(len(root.findall('thread')), 1)


class DiscussionViewIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.author = User.objects.create_user(username='thread_owner', password='password123')
        cls.other_user = User.objects.create_user(username='other_user', password='password123')
        cls.staff_user = User.objects.create_user(username='staff_user', password='password123', is_staff=True)

        cls.news = News.objects.create(
            title='Derby Day',
            content='Preview content',
            category='update',
            sports='football',
        )
        cls.other_news = News.objects.create(
            title='Training Camp',
            content='Training updates',
            category='analysis',
            sports='basketball',
        )

        cls.thread = DiscussionThread.objects.create(
            title='Opening Thoughts',
            body='Initial analysis.',
            author=cls.author,
            news=cls.news,
        )
        cls.other_thread = DiscussionThread.objects.create(
            title='Secondary Thread',
            body='Different topic.',
            author=cls.author,
            news=cls.other_news,
        )
        cls.thread_without_news = DiscussionThread.objects.create(
            title='General Chat',
            body='No news attached.',
            author=cls.author,
        )
        cls.comment = DiscussionComment.objects.create(
            thread=cls.thread,
            author=cls.author,
            content='First comment.',
        )

    def test_thread_list_filters_by_news_query(self):
        url = reverse('discussions:thread-list')
        response = self.client.get(url, {'q': 'Derby'})
        self.assertEqual(response.status_code, 200)
        threads = list(response.context['threads'])
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0].pk, self.thread.pk)
        self.assertIn('thread_form', response.context)

    def test_thread_detail_includes_comments_and_form(self):
        response = self.client.get(reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.comment, response.context['comments'])
        self.assertIn('comment_form', response.context)
        comment_context = response.context['comments'][0]
        self.assertTrue(hasattr(comment_context, 'author_display'))
        self.assertIn('upvote_count', response.context)
        self.assertEqual(response.context['upvote_count'], 0)

    def test_thread_create_get_and_invalid_post(self):
        self.client.force_login(self.author)
        get_response = self.client.get(reverse('discussions:thread-create'))
        self.assertEqual(get_response.status_code, 200)

        post_response = self.client.post(reverse('discussions:thread-create'), {
            'news': self.news.pk,
            'title': '',
            'body': 'Missing title should fail',
        })
        self.assertEqual(post_response.status_code, 200)
        form = post_response.context['form']
        self.assertFormError(form, 'title', 'This field is required.')

    def test_thread_create_successful_post(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse('discussions:thread-create'),
            {
                'news': self.news.pk,
                'title': 'New Thread',
                'body': "Let's discuss!",
            },
        )
        latest_thread = DiscussionThread.objects.order_by('-id').first()
        self.assertRedirects(response, reverse('discussions:thread-detail', args=[latest_thread.pk]))
        self.assertEqual(latest_thread.views_count, 0)
        self.assertEqual(latest_thread.upvotes.count(), 0)

    def test_thread_edit_requires_owner_or_staff(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('discussions:thread-edit', args=[self.thread.pk]), {
            'news': self.news.pk,
            'title': 'Attempted Update',
            'body': 'Should be blocked.',
        })
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('discussions:thread-edit', args=[self.thread.pk]), {
            'news': self.news.pk,
            'title': 'Staff Update',
            'body': 'Updated by staff.',
        })
        self.assertRedirects(response, reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.title, 'Staff Update')

    def test_thread_edit_owner_updates_thread(self):
        self.client.force_login(self.author)
        response = self.client.post(reverse('discussions:thread-edit', args=[self.other_thread.pk]), {
            'news': self.other_news.pk,
            'title': 'Edited Title',
            'body': 'Updated body.',
        })
        self.assertRedirects(response, reverse('discussions:thread-detail', args=[self.other_thread.pk]))
        self.other_thread.refresh_from_db()
        self.assertEqual(self.other_thread.title, 'Edited Title')

    def test_thread_delete_flow(self):
        self.client.force_login(self.author)
        get_response = self.client.get(reverse('discussions:thread-delete', args=[self.other_thread.pk]))
        self.assertEqual(get_response.status_code, 200)

        post_response = self.client.post(reverse('discussions:thread-delete', args=[self.other_thread.pk]))
        self.assertRedirects(post_response, reverse('discussions:thread-list'))
        self.assertFalse(DiscussionThread.objects.filter(pk=self.other_thread.pk).exists())

    def test_thread_delete_forbidden_for_other_user(self):
        thread = DiscussionThread.objects.create(
            title='To Delete',
            body='Thread to be deleted',
            author=self.author,
            news=self.news,
        )
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('discussions:thread-delete', args=[thread.pk]))
        self.assertEqual(response.status_code, 403)

    def test_thread_detail_increments_views(self):
        self.assertEqual(self.thread.views_count, 0)
        self.client.get(reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.views_count, 1)
        self.client.get(reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.views_count, 2)

    def test_thread_create_api_handles_invalid_payloads(self):
        self.client.force_login(self.author)
        url = reverse('discussions:thread-create-api')

        invalid_json = self.client.post(url, data='{"title":', content_type='application/json')
        self.assertEqual(invalid_json.status_code, 400)
        self.assertFalse(invalid_json.json().get('ok', True))

        invalid_form = self.client.post(url, data=json.dumps({'title': ''}), content_type='application/json')
        self.assertEqual(invalid_form.status_code, 400)
        self.assertIn('errors', invalid_form.json())

        form_response = self.client.post(url, data={
            'news': self.news.pk,
            'title': 'Form Encoded Thread',
            'body': 'Created via form data.',
        })
        self.assertEqual(form_response.status_code, 201)
        self.assertTrue(DiscussionThread.objects.filter(title='Form Encoded Thread').exists())

    def test_thread_list_api_handles_threads_without_news(self):
        response = self.client.get(reverse('discussions:thread-list-api'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()['threads']
        thread_data = next(item for item in payload if item['id'] == self.thread_without_news.pk)
        self.assertIsNone(thread_data['news'])
        self.assertIn('views_count', thread_data)

    def test_comment_create_flow(self):
        self.client.force_login(self.other_user)
        url = reverse('discussions:comment-create', args=[self.thread.pk])
        response = self.client.post(url, {'content': 'A new comment'})
        self.assertRedirects(response, reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.assertTrue(DiscussionComment.objects.filter(content='A new comment').exists())

    def test_comment_create_with_parent_and_invalid_data(self):
        parent = DiscussionComment.objects.create(
            thread=self.thread,
            author=self.author,
            content='Parent comment',
        )
        self.client.force_login(self.other_user)
        url = reverse('discussions:comment-create', args=[self.thread.pk])
        response = self.client.post(url, {'content': 'Reply', 'parent': parent.pk})
        self.assertRedirects(response, reverse('discussions:thread-detail', args=[self.thread.pk]))
        reply = DiscussionComment.objects.get(content='Reply')
        self.assertEqual(reply.parent, parent)

        invalid_response = self.client.post(url, {'content': ''})
        self.assertEqual(invalid_response.status_code, 200)
        self.assertTemplateUsed(invalid_response, 'discussions/comment_form.html')

    def test_comment_edit_permissions_and_updates(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse('discussions:comment-edit', args=[self.comment.pk]))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.author)
        response = self.client.post(reverse('discussions:comment-edit', args=[self.comment.pk]), {'content': 'Updated comment'})
        self.assertRedirects(response, reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Updated comment')

    def test_comment_edit_ajax_updates_content(self):
        self.client.force_login(self.author)
        url = reverse('discussions:comment-edit', args=[self.comment.pk])
        response = self.client.post(url, {'content': 'Ajax updated comment'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data['content'], 'Ajax updated comment')
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Ajax updated comment')

    def test_comment_delete_access(self):
        comment = DiscussionComment.objects.create(
            thread=self.thread,
            author=self.other_user,
            content='To be removed',
        )

        self.client.force_login(self.staff_user)
        get_response = self.client.get(reverse('discussions:comment-delete', args=[comment.pk]))
        self.assertEqual(get_response.status_code, 200)

        post_response = self.client.post(reverse('discussions:comment-delete', args=[comment.pk]))
        self.assertRedirects(post_response, reverse('discussions:thread-detail', args=[self.thread.pk]))
        self.assertFalse(DiscussionComment.objects.filter(pk=comment.pk).exists())

    def test_comment_delete_forbidden_for_unrelated_user(self):
        comment = DiscussionComment.objects.create(
            thread=self.thread,
            author=self.author,
            content='Protected comment',
        )
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('discussions:comment-delete', args=[comment.pk]))
        self.assertEqual(response.status_code, 403)

    def test_thread_upvote_toggle_adds_and_removes(self):
        self.client.force_login(self.other_user)
        url = reverse('discussions:thread-upvote', args=[self.thread.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['state'], 'added')
        self.assertEqual(data['upvote_count'], 1)
        self.assertTrue(DiscussionThreadUpvote.objects.filter(thread=self.thread, user=self.other_user).exists())

        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['state'], 'removed')
        self.assertEqual(data['upvote_count'], 0)
        self.assertFalse(DiscussionThreadUpvote.objects.filter(thread=self.thread, user=self.other_user).exists())

    def test_thread_upvote_requires_login(self):
        url = reverse('discussions:thread-upvote', args=[self.thread.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))
