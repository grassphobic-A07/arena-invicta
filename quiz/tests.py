from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from .models import Quiz, Question, Score
from .forms import QuizForm, QuestionForm

# =======================================================================
#  BASECASE
# =======================================================================


class BaseQuizTestCase(TestCase):
    """
    Base case for creating users, groups, and quizzes.
    That will be used across all tests.
    """
    def setUp(self):
        # Create Group
        self.staff_group, _ = Group.objects.get_or_create(name="Content Staff")

        # Create Users
        self.user_staff = User.objects.create_user(username='staff_user', password='password123')
        self.user_staff.groups.add(self.staff_group)
        self.user_staff.save()

        self.user_regular = User.objects.create_user(username='regular_user', password='password123')
        self.user_other_staff = User.objects.create_user(username='other_staff', password='password123')

        # Create Quizzes
        self.quiz_staff_published = Quiz.objects.create(
            user=self.user_staff,
            title="Kuis Staff (Published)",
            description="Kuis oleh staff.",
            is_published=True
        )
        self.quiz_staff_draft = Quiz.objects.create(
            user=self.user_staff,
            title="Kuis Staff (Draft)",
            description="Kuis draft oleh staff.",
            is_published=False
        )

        # Actually possible through shell or sum, 
        self.quiz_other_published = Quiz.objects.create(
            user=self.user_other_staff,
            title="Kuis Lain (Published)",
            description="Kuis oleh user lain.",
            is_published=True
        )

        # Create Questions
        self.question1 = Question.objects.create(
            quiz=self.quiz_staff_published,
            text="Apa ibukota Indonesia?",
            option_a="Jakarta",
            option_b="Bandung",
            option_c="Surabaya",
            option_d="Medan",
            correct_answer="A"
        )
        self.question2 = Question.objects.create(
            quiz=self.quiz_staff_published,
            text="Berapa 2+2?",
            option_a="3",
            option_b="4",
            option_c="5",
            option_d="6",
            correct_answer="B"
        )

        # Create Scores
        self.score_regular = Score.objects.create(
            user=self.user_regular,
            quiz=self.quiz_staff_published,
            score=1
        )

        # Initial client
        self.client = Client()
        
        # AJAX Header
        self.ajax_header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

# =======================================================================
#  TEST FOR VIEWS
# =======================================================================

class MainViewTests(BaseQuizTestCase):
    
    def test_show_main_anonymous_user(self):
        """
        Anonymous user (Visitor) should be redirected to the login page.
        """
        response = self.client.get(reverse('quiz:show_main'))
        
        self.assertEqual(response.status_code, 302)
        expected_redirect_url = f"{reverse('accounts:login')}?next={reverse('quiz:show_main')}"
        self.assertRedirects(response, expected_redirect_url) 

    def test_show_main_regular_user(self):
        """
        Regular User (Registered) only can see the quiz where 'is_published=True'
        """
        self.client.login(username='regular_user', password='password123')
        response = self.client.get(reverse('quiz:show_main'))
        self.assertEqual(response.status_code, 200)
        
        self.assertIn(self.quiz_staff_published, response.context['quizzes'])
        self.assertIn(self.quiz_other_published, response.context['quizzes'])
        self.assertNotIn(self.quiz_staff_draft, response.context['quizzes'])
        self.assertFalse(response.context['authorized'])

    def test_show_main_content_staff_user(self):
        """
        Content Staff User only can see their own quiz (Published & Private)
        """
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(reverse('quiz:show_main'))
        self.assertEqual(response.status_code, 200)
        
        # Published
        self.assertIn(self.quiz_staff_published, response.context['quizzes'])

        # Private (Draft)
        self.assertIn(self.quiz_staff_draft, response.context['quizzes'])

        # Other people quizzes
        self.assertNotIn(self.quiz_other_published, response.context['quizzes'])
        
        self.assertTrue(response.context['authorized'])
        self.assertEqual(response.context['role'], "Content Staff")


class QuizDetailViewTests(BaseQuizTestCase):

    def test_quiz_detail_view_success(self):
        """
        Test whether the user able to see the valid quiz detail.
        """
        url = reverse('quiz:quiz_detail', args=[self.quiz_staff_published.id])
        response = self.client.get(url)
        
        # The context
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/quiz_detail.html')
        self.assertEqual(response.context['quiz'], self.quiz_staff_published)
        self.assertEqual(response.context['total_questions'], 2)
        self.assertIn(self.score_regular, response.context['leaderboard'])

    def test_quiz_detail_view_not_found(self):
        """
        Test 404 if the ID is not available.
        """
        url = reverse('quiz:quiz_detail', args=[999]) # Invalid ID
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class CreateQuizViewTests(BaseQuizTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('quiz:create_quiz')
        self.valid_form_data = {
            'title': 'My Quiz',
            'description': 'My Description',
            'is_published': 'on',

            # Formset Management
            'questions-TOTAL_FORMS': '1',
            'questions-INITIAL_FORMS': '0',
            'questions-MIN_NUM_FORMS': '0',
            'questions-MAX_NUM_FORMS': '1000',
            
            # Formset Form 0
            'questions-0-text': 'Question?',
            'questions-0-option_a': 'A',
            'questions-0-option_b': 'B',
            'questions-0-option_c': 'C',
            'questions-0-option_d': 'D',
            'questions-0-correct_answer': 'A',
        }
        self.invalid_form_data = {
            'title': '', # Empty title, Invalid form
            'questions-TOTAL_FORMS': '0',
            'questions-INITIAL_FORMS': '0',
        }

    def test_create_quiz_get_anonymous_redirects(self):
        """GET: Anonymous user should be redirected to login page."""
        response = self.client.get(self.url)
        redirect_url = f"{reverse('accounts:login')}?next={self.url}"
        self.assertRedirects(response, redirect_url)

    def test_create_quiz_get_authenticated_non_ajax(self):
        """GET (non-AJAX): Authenticated user get full page."""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/create_quiz.html')
        self.assertIsInstance(response.context['quiz_form'], QuizForm)

    def test_create_quiz_get_authenticated_ajax(self):
        """GET (AJAX): Authenthicated user get partial form."""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url, **self.ajax_header)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/_quiz_form_partial.html')

    def test_create_quiz_post_anonymous_redirects(self):
        """POST: Anonymous user should be redirected to login page."""
        response = self.client.post(self.url, self.valid_form_data)
        redirect_url = f"{reverse('accounts:login')}?next={self.url}"
        self.assertRedirects(response, redirect_url)

    def test_create_quiz_post_authenticated_non_ajax_success(self):
        """POST (non-AJAX): Success creating quiz and redirect to it's detail page"""
        self.client.login(username='staff_user', password='password123')
        quiz_count = Quiz.objects.count()
        question_count = Question.objects.count()
        
        response = self.client.post(self.url, self.valid_form_data)
        
        # Cek database
        self.assertEqual(Quiz.objects.count(), quiz_count + 1)
        self.assertEqual(Question.objects.count(), question_count + 1)
        new_quiz = Quiz.objects.latest('id')
        self.assertEqual(new_quiz.title, 'My Quiz')
        self.assertEqual(new_quiz.user, self.user_staff)
        
        # Cek redirect
        redirect_url = reverse('quiz:quiz_detail', args=[new_quiz.id])
        self.assertRedirects(response, redirect_url)

    def test_create_quiz_post_authenticated_ajax_success(self):
        """POST (AJAX): Success creating quiz and return JSON"""
        self.client.login(username='staff_user', password='password123')
        
        response = self.client.post(self.url, self.valid_form_data, **self.ajax_header)
        
        self.assertEqual(response.status_code, 200)
        new_quiz = Quiz.objects.latest('id')
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        self.assertEqual(data['redirect_url'], reverse('quiz:quiz_detail', args=[new_quiz.id]))

    def test_create_quiz_post_authenticated_non_ajax_invalid(self):
        """POST (non-AJAX): Validation error. Re-Rendering full page with error."""
        self.client.login(username='staff_user', password='password123')
        quiz_count = Quiz.objects.count()

        response = self.client.post(self.url, self.invalid_form_data)
        
        self.assertEqual(response.status_code, 200) # Re-render
        self.assertTemplateUsed(response, 'quiz/create_quiz.html')
        self.assertFalse(response.context['quiz_form'].is_valid())
        self.assertIn('title', response.context['quiz_form'].errors)
        self.assertEqual(Quiz.objects.count(), quiz_count) # New quiz doesn't occur

    def test_create_quiz_post_authenticated_ajax_invalid(self):
        """POST (AJAX): Validation fail. Return JSON (status 4000) with partial HTML"""
        self.client.login(username='staff_user', password='password123')

        response = self.client.post(self.url, self.invalid_form_data, **self.ajax_header)
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('html', data) # Is partial HTML exist
        self.assertIn('message', data) # Is error message exist
        self.assertIn('This field is required', data['html']) # HTML contains error message


class EditQuizViewTests(BaseQuizTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('quiz:edit_quiz', args=[self.quiz_staff_published.id])
        self.valid_edit_data = {
            'title': 'Quiz Title Updated', # Title Changed
            'description': self.quiz_staff_published.description,
            'is_published': 'on',

            # Formset Management
            'questions-TOTAL_FORMS': '2',
            'questions-INITIAL_FORMS': '2', # 2 Initial Question
            'questions-MIN_NUM_FORMS': '0',
            'questions-MAX_NUM_FORMS': '1000',

            # Formset Form 0 (existing, no change)
            'questions-0-id': self.question1.id,
            'questions-0-text': self.question1.text,
            'questions-0-option_a': self.question1.option_a,
            'questions-0-option_b': self.question1.option_b,
            'questions-0-option_c': self.question1.option_c,
            'questions-0-option_d': self.question1.option_d,
            'questions-0-correct_answer': self.question1.correct_answer,

            # Formset Form 1 (existing, DELETE)
            'questions-1-id': self.question2.id,
            'questions-1-text': self.question2.text,
            'questions-1-option_a': self.question2.option_a,
            'questions-1-option_b': self.question2.option_b,
            'questions-1-option_c': self.question2.option_c,
            'questions-1-option_d': self.question2.option_d,
            'questions-1-correct_answer': self.question2.correct_answer,
            'questions-1-DELETE': 'on', # <-- Delete this question
        }
        self.invalid_edit_data = self.valid_edit_data.copy()
        self.invalid_edit_data['title'] = '' # Empty title

    def test_edit_quiz_get_anonymous_redirects(self):
        """GET: Anonymous user redirected to login page"""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_edit_quiz_get_not_owner(self):
        """GET: User that not own the quiz is redirected (non-AJAX)."""
        self.client.login(username='regular_user', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('quiz:quiz_detail', args=[self.quiz_staff_published.id]))

    def test_edit_quiz_get_not_owner_ajax(self):
        """GET (AJAX): User that not own the quiz get JSON error 403."""
        self.client.login(username='regular_user', password='password123')
        response = self.client.get(self.url, **self.ajax_header)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])

    def test_edit_quiz_get_owner_non_ajax(self):
        """GET (non-AJAX): Owner get a full page."""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/create_quiz.html')
        self.assertEqual(response.context['quiz_form'].instance, self.quiz_staff_published)

    def test_edit_quiz_get_owner_ajax(self):
        """GET (AJAX): Owner get a partial form."""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url, **self.ajax_header)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/_quiz_form_partial.html')

    def test_edit_quiz_post_owner_non_ajax_success(self):
        """POST (non-AJAX): Success on updating quiz and redirect."""
        self.client.login(username='staff_user', password='password123')
        question_count = Question.objects.count() # Initial : 2

        response = self.client.post(self.url, self.valid_edit_data)
        
        # Check Database
        self.quiz_staff_published.refresh_from_db()
        self.assertEqual(self.quiz_staff_published.title, 'Quiz Title Updated')
        self.assertEqual(Question.objects.count(), question_count - 1) # Min 1
        self.assertFalse(Question.objects.filter(id=self.question2.id).exists()) # Q2 deleted
        
        # Check redirect
        self.assertRedirects(response, reverse('quiz:quiz_detail', args=[self.quiz_staff_published.id]))

    def test_edit_quiz_post_owner_ajax_success(self):
        """POST (AJAX): Success updating quiz and return JSON"""
        self.client.login(username='staff_user', password='password123')
        
        response = self.client.post(self.url, self.valid_edit_data, **self.ajax_header)
        
        self.assertEqual(response.status_code, 200)
        self.quiz_staff_published.refresh_from_db()
        self.assertEqual(self.quiz_staff_published.title, 'Quiz Title Updated')
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        self.assertEqual(data['redirect_url'], reverse('quiz:quiz_detail', args=[self.quiz_staff_published.id]))
        
    def test_edit_quiz_post_owner_ajax_invalid(self):
        """POST (AJAX): Validation failed, return JSON 4000 with partial HTML"""
        self.client.login(username='staff_user', password='password123')
        original_title = self.quiz_staff_published.title

        response = self.client.post(self.url, self.invalid_edit_data, **self.ajax_header)
        
        self.assertEqual(response.status_code, 400)
        self.quiz_staff_published.refresh_from_db()
        self.assertEqual(self.quiz_staff_published.title, original_title) # Title not changed
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('html', data)
        self.assertIn('message', data)


class DeleteQuizViewTests(BaseQuizTestCase):

    def setUp(self):
        super().setUp()
        # Make new quiz so that it doesn't interfere other quizzes
        self.quiz_to_delete = Quiz.objects.create(user=self.user_staff, title="Delete Quiz")
        self.url = reverse('quiz:delete_quiz', args=[self.quiz_to_delete.id])

    def test_delete_quiz_get_redirects(self):
        """GET: GET is not permitted, need to be redirect"""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url)
        # View leads to detail if isn't POST
        self.assertRedirects(response, reverse('quiz:quiz_detail', args=[self.quiz_to_delete.id]))

    def test_delete_quiz_post_anonymous_redirects(self):
        """POST: Anonymous user redirected to login page"""
        response = self.client.post(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_delete_quiz_post_not_owner_non_ajax(self):
        """POST (non-AJAX): Not owner, redirected with error message"""
        self.client.login(username='regular_user', password='password123')
        response = self.client.post(self.url, follow=True)
        
        self.assertTrue(Quiz.objects.filter(id=self.quiz_to_delete.id).exists()) # Not deleted
        self.assertRedirects(response, reverse('quiz:quiz_detail', args=[self.quiz_to_delete.id]))
        
        # Check Django Messages
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "You do not have permission to delete this quiz.")

    def test_delete_quiz_post_not_owner_ajax(self):
        """POST (AJAX): Not owner, return JSON 403"""
        self.client.login(username='regular_user', password='password123')
        response = self.client.post(self.url, **self.ajax_header)
        
        self.assertTrue(Quiz.objects.filter(id=self.quiz_to_delete.id).exists()) # Not deleted
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        self.assertEqual(response.json()['error'], 'Permission denied.')

    def test_delete_quiz_post_owner_non_ajax_success(self):
        """POST (non-AJAX): Owner successfully delete and redirected"""
        self.client.login(username='staff_user', password='password123')
        response = self.client.post(self.url, follow=True)
        
        self.assertFalse(Quiz.objects.filter(id=self.quiz_to_delete.id).exists()) # Deleted
        self.assertRedirects(response, reverse('quiz:show_main'))
        
        # Check Django Messages
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertTrue("has been successfully deleted" in str(messages[0]))

    def test_delete_quiz_post_owner_ajax_success(self):
        """POST (AJAX): Owner successfully delete and return JSON"""
        self.client.login(username='staff_user', password='password123')
        response = self.client.post(self.url, **self.ajax_header)
        
        self.assertFalse(Quiz.objects.filter(id=self.quiz_to_delete.id).exists()) # Deleted
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], reverse('quiz:show_main'))
        # Your view (based on file) not sending 'message' in JSON for delete
        self.assertNotIn('message', data) 


class TogglePublishViewTests(BaseQuizTestCase):
    
    def setUp(self):
        super().setUp()
        self.url = reverse('quiz:toggle_publish', args=[self.quiz_staff_draft.id])
        self.url_published = reverse('quiz:toggle_publish', args=[self.quiz_staff_published.id])

    def test_toggle_publish_get_returns_error(self):
        """GET: GET is not allowed, return JSON error 405"""
        self.client.login(username='staff_user', password='password123')
        response = self.client.get(self.url, **self.ajax_header)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()['success'])

    def test_toggle_publish_anonymous_redirects(self):
        """POST: Anonymous get redirected (AJAX and non-AJAX)."""
        response = self.client.post(self.url, **self.ajax_header)
        # Django @login_required would redirect, which means status on 302
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))

    def test_toggle_publish_not_owner_ajax(self):
        """POST (AJAX): Not owner, return JSON 403"""
        self.client.login(username='regular_user', password='password123')
        response = self.client.post(self.url, **self.ajax_header)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])

    def test_toggle_publish_from_false_to_true_ajax(self):
        """POST (AJAX): Owner successfullly changed 'False' -> 'True'."""
        self.client.login(username='staff_user', password='password123')
        self.assertFalse(self.quiz_staff_draft.is_published) # Initially False

        response = self.client.post(self.url, **self.ajax_header)
        
        self.assertEqual(response.status_code, 200)
        self.quiz_staff_draft.refresh_from_db()
        self.assertTrue(self.quiz_staff_draft.is_published) # To True
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_published'])
        self.assertIn('published', data['message'])

    def test_toggle_publish_from_true_to_false_ajax(self):
        """POST (AJAX): Owner successfullly changed 'True' -> 'False'."""
        self.client.login(username='staff_user', password='password123')
        self.assertTrue(self.quiz_staff_published.is_published) # Initially True

        response = self.client.post(self.url_published, **self.ajax_header)
        
        self.assertEqual(response.status_code, 200)
        self.quiz_staff_published.refresh_from_db()
        self.assertFalse(self.quiz_staff_published.is_published) # To False
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['is_published'])
        self.assertIn('private', data['message'])


class TakeQuizViewTests(BaseQuizTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('quiz:take_quiz', args=[self.quiz_staff_published.id])
        self.post_data = {
            f'question_{self.question1.id}': 'A', # Correct Answer
            f'question_{self.question2.id}': 'C', # Wrong Answer
        }

    def test_take_quiz_get_anonymous_redirects(self):
        """GET: Anonymous user redirected to login page"""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
        
    def test_take_quiz_get_authenticated(self):
        """GET: Authenticated user get quiz page"""
        self.client.login(username='regular_user', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/take_quiz.html')
        self.assertIn(self.question1, response.context['questions'])

    def test_take_quiz_post_non_ajax_creates_score(self):
        """POST (non-AJAX): New User do the quiz, make new object of score."""
        self.client.login(username='staff_user', password='password123') # This user has not done any
        score_count = Score.objects.count()
        
        response = self.client.post(self.url, self.post_data)
        
        self.assertEqual(Score.objects.count(), score_count + 1)
        new_score = Score.objects.latest('id')
        self.assertEqual(new_score.user, self.user_staff)
        self.assertEqual(new_score.score, 1) # 1 correct, 1 wrong
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/quiz_result.html')
        self.assertEqual(response.context['score'], 1)
        self.assertEqual(response.context['percentage'], 50.0)
        
    def test_take_quiz_post_non_ajax_updates_higher_score(self):
        """POST (non-AJAX): User do it again, skor just get updated if higher score."""
        # 'regular_user' already have score (1)
        self.client.login(username='regular_user', password='password123')
        
        # Try with lower score (0)
        post_data_low = {
            f'question_{self.question1.id}': 'B', # Wrong
            f'question_{self.question2.id}': 'C', # Wrong
        }
        self.client.post(self.url, post_data_low)
        self.score_regular.refresh_from_db()
        self.assertEqual(self.score_regular.score, 1) # Score still 1

        # Try with higher score (2)
        post_data_high = {
            f'question_{self.question1.id}': 'A', # Correct
            f'question_{self.question2.id}': 'B', # Correct
        }
        self.client.post(self.url, post_data_high)
        self.score_regular.refresh_from_db()
        self.assertEqual(self.score_regular.score, 2) # Score updated

    def test_take_quiz_post_ajax_success(self):
        """POST (AJAX): Success submit and return JSON result"""
        self.client.login(username='staff_user', password='password123')
        
        response = self.client.post(self.url, self.post_data, **self.ajax_header)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('html', data)
        self.assertEqual(data['result_url'], reverse('quiz:quiz_result', args=[self.quiz_staff_published.id]))


class DisplayScoreViewTests(BaseQuizTestCase):
    
    def setUp(self):
        super().setUp()
        self.url = reverse('quiz:quiz_result', args=[self.quiz_staff_published.id])
        self.url_draft_quiz = reverse('quiz:quiz_result', args=[self.quiz_staff_draft.id])

    def test_display_score_get_anonymous_redirects(self):
        """GET: Anonymous user redirected to login page"""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_display_score_get_user_has_not_taken_quiz(self):
        """GET: User not do the quiz yet, redirected to take quiz with an error."""
        self.client.login(username='staff_user', password='password123') # User staff haven't taken quiz_staff_published
        response = self.client.get(self.url_draft_quiz, follow=True) # Try accessing other quiz result
        
        self.assertRedirects(response, reverse('quiz:take_quiz', args=[self.quiz_staff_draft.id]))
        
        # Check Django Messages
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertTrue("You must complete this quiz" in str(messages[0]))

    def test_display_score_get_user_has_taken_quiz_success(self):
        """GET: User has done the quiz, successfully access the result page."""
        self.client.login(username='regular_user', password='password123') # Regular user already have score
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quiz/quiz_result.html')
        self.assertEqual(response.context['score'], self.score_regular.score)
        self.assertEqual(response.context['total_questions'], 2)