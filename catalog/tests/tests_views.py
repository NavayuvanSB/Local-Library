from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from django.utils import timezone

from catalog.models import Author, Genre, Language, Book, BookInstance

import datetime
import uuid


class AuthorListViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        number_of_authors = 13

        for author_id in range(number_of_authors):
            Author.objects.create(
                first_name=f'Christian {author_id}',
                last_name=f'Surname {author_id}'
            )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/catalog/authors/')
        self.assertEqual(response.status_code, 200)

    def test_url_accessible_by_name(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/author_list.html')

    def test_pagination_is_ten(self):
        response = self.client.get(reverse('authors'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'] == True)
        self.assertTrue(len(response.context['author_list']) == 10)

    def test_lists_all_authors(self):
        response = self.client.get(reverse('authors') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'] == True)
        self.assertTrue(len(response.context['author_list']) == 3)


class LoanedBookInstanceByUserListViewTest(TestCase):

    def setUp(self):

        # Create Users
        test_user1 = User.objects.create_user(
            username="testuser1", password="password1")
        test_user2 = User.objects.create_user(
            username="testuser2", password="password2")

        test_user1.save()
        test_user2.save()

        # Create a book
        test_author = Author.objects.create(
            first_name="John", last_name="Mathews")
        test_genre = Genre.objects.create(name='fantasy')
        test_language = Language.objects.create(name="English")
        test_book = Book.objects.create(
            title="Book title",
            summary="Book summary",
            isbn="194873498",
            author=test_author,
            language=test_language
        )

        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        # Create book instances
        number_of_book_copies = 30
        for book_copy in range(number_of_book_copies):

            return_date = timezone.localtime() + datetime.timedelta(days=book_copy % 5)
            the_borrower = test_user1 if book_copy % 2 else test_user2
            status = 'm'
            BookInstance.objects.create(
                book=test_book,
                imprint='Unlikely Imprint, 260',
                due_back=return_date,
                borrower=the_borrower,
                status=status
            )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(
            response, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        login = self.client.login(username="testuser1", password="password1")
        response = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_the_list(self):
        login = self.client.login(username="testuser1", password="password1")
        response = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)

        self.assertTrue('bookinstance_list' in response.context)
        self.assertEqual(len(response.context['bookinstance_list']), 0)

        books = BookInstance.objects.all()[:10]
        for book in books:
            book.status = 'o'
            book.save()

        response = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)

        self.assertTrue('bookinstance_list' in response.context)

        for bookitem in response.context['bookinstance_list']:
            self.assertEqual(response.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):

        for book in BookInstance.objects.all():
            book.status = 'o'
            book.save()

        login = self.client.login(username='testuser1', password='password1')
        response = self.client.get(reverse('my-borrowed'))

        self.assertEqual(str(response.context['user']), 'testuser1')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['bookinstance_list']), 10)

        last_date = 0
        for book in response.context['bookinstance_list']:
            if last_date == 0:
                last_date = book.due_back

            else:
                self.assertTrue(last_date <= book.due_back)
                last_date = book.due_back


class RenewBookInstancesViewTest(TestCase):

    def setUp(self):

        # Create Users
        test_user1 = User.objects.create_user(
            username="testuser1", password="password1")
        test_user2 = User.objects.create_user(
            username="testuser2", password="password2")

        test_user1.save()
        test_user2.save()

        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

        # Create a book
        test_author = Author.objects.create(
            first_name="John", last_name="Mathews")
        test_genre = Genre.objects.create(name='fantasy')
        test_language = Language.objects.create(name="English")
        test_book = Book.objects.create(
            title="Book title",
            summary="Book summary",
            isbn="194873498",
            author=test_author,
            language=test_language
        )

        genre_objects_for_book = Genre.objects.all()
        test_book.genre.set(genre_objects_for_book)
        test_book.save()

        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely Imprint, 2016',
            due_back=return_date,
            borrower=test_user1,
            status='o',
        )

        self.test_bookinstance2 = BookInstance.objects.create(
            book=test_book,
            imprint='Unlikely Imprint, 2016',
            due_back=return_date,
            borrower=test_user2,
            status='o',
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_forbidden_if_logged_in_but_not_have_permission(self):
        login = self.client.login(username='testuser1', password='password1')
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        self.assertEqual(response.status_code, 403)

    def test_logged_in_with_permission_borrowed_book(self):
        login = self.client.login(username='testuser2', password='password2')
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance2.pk}))

        self.assertEqual(response.status_code, 200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        login = self.client.login(username='testuser2', password='password2')
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        self.assertEqual(response.status_code, 200)

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        login = self.client.login(username='testuser2', password='password2')

        test_uid = uuid.uuid4()
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': test_uid}))

        self.assertEqual(response.status_code, 404)

    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='password2')
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'catalog/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        login = self.client.login(username='testuser2', password='password2')
        response = self.client.get(
            reverse('renew-book-librarian', kwargs={'pk': self.test_bookinstance1.pk}))

        self.assertEqual(response.status_code, 200)

        date_three_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(
            response.context['form'].initial['renewal_date'], date_three_weeks_in_future)

    def test_redirects_to_all_borrowed_book_list_on_success(self):
        login = self.client.login(username='testuser2', password='password2')
        valid_date_in_future = datetime.date.today() + datetime.timedelta(weeks=2)

        response = self.client.post(reverse('renew-book-librarian', kwargs={
                                    'pk': self.test_bookinstance1.pk}),
                                    {'renewal_date': valid_date_in_future})

        self.assertRedirects(response, reverse('borrowed'))

    def test_form_invalid_renewal_date_past(self):
        login = self.client.login(username='testuser2', password='password2')
        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)
        response = self.client.post(reverse(
            'renew-book-librarian',
            kwargs={'pk': self.test_bookinstance1.pk}),
            {'renewal_date': date_in_past})

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'renewal_date',
                             'Invalid date - renewal in past')

    def test_form_invalid_renewal_date_future(self):
        login = self.client.login(username='testuser2', password='password2')
        date_in_future = datetime.date.today() + datetime.timedelta(weeks=5)
        response = self.client.post(reverse(
            'renew-book-librarian',
            kwargs={'pk': self.test_bookinstance1.pk}),
            {'renewal_date': date_in_future})

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'renewal_date',
                             'Invalid date - renewal more than 4 weeks ahead')


class AuthorCreateViewTest(TestCase):

    def setUp(self):

        testuser1 = User.objects.create_user(
            username="testuser1", password="password1")
        testuser2 = User.objects.create_user(
            username="testuser2", password="password2")

        testuser1.save()
        testuser2.save()

        can_mark_returned_permission = Permission.objects.get(
            codename='can_mark_returned')

        testuser2.user_permissions.add(can_mark_returned_permission)
        testuser2.save()

    def test_redirect_if_not_logged_in(self):

        response = self.client.get(reverse('author-create'))

        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(
            response, '/accounts/login/?next=/catalog/author/create/')

    def test_block_user_logged_in_without_permission(self):

        login = self.client.login(username="testuser1", password="password1")

        response = self.client.get(reverse('author-create'))
        self.assertEqual(response.status_code, 403)

    def test_allow_user_logged_in_with_permission(self):

        login = self.client.login(username="testuser2", password="password2")

        response = self.client.get(reverse('author-create'))
        self.assertEqual(response.status_code, 200)

    def test_default_date_of_death_is_rendered(self):

        login = self.client.login(username="testuser2", password="password2")
        response = self.client.get(reverse('author-create'))

        self.assertEqual(
            response.context['form'].initial['date_of_death'], '11/06/2020')

    def test_display_correct_template(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.get(reverse('author-create'))

        self.assertTemplateUsed(response, 'catalog/author_form.html')

    def test_invalid_date_validation_works(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.post(reverse('author-create'), {
            'pk': '1',
            'first_name': 'Mathew',
            'last_name': 'Williams',
            'date_of_birth': '11/06/2000',
            'date_of_death': '11/06.2021'
        })

        self.assertNotEqual(response.status_code, 302)

    def test_last_name_missed_validation_works(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.post(reverse('author-create'), {
            'pk': '1',
            'first_name': 'Mathew',
            'date_of_birth': '11/06/2000',
            'date_of_death': '11/06/2021'
        })

        self.assertNotEqual(response.status_code, 302)

    def test_first_name_missed_validation_works(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.post(reverse('author-create'), {
            'pk': '1',
            'last_name': 'Mathew',
            'date_of_birth': '11/06/2000',
            'date_of_death': '11/06/2021'
        })

        self.assertNotEqual(response.status_code, 302)

    def test_date_of_birth_missed_validation_works(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.post(reverse('author-create'), {
            'pk': '1',
            'first_name': 'Mathew',
            'last_name': 'Williams',
            'date_of_death': '11/06.2021'
        })

        self.assertNotEqual(response.status_code, 302)

    def test_date_of_death_missed_validation_works(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.post(reverse('author-create'), {
            'pk': '1',
            'first_name': 'Mathew',
            'last_name': 'Williams',
            'date_of_birth': '11/06/2021'
        })

        self.assertEqual(response.status_code, 302)

    def test_redirect_user_to_all_authors_on_correct_submission(self):
        login = self.client.login(username="testuser2", password="password2")
        response = self.client.post(reverse('author-create'), {
            'pk': '1',
            'first_name': 'Mathew',
            'last_name': 'Williams',
            'date_of_birth': '11/06/2000',
            'date_of_death': '11/06/2021'
        })

        self.assertRedirects(response, reverse(
            'author-detail', kwargs={'pk': 1}))
