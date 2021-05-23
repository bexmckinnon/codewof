import datetime

import pytz
from django.test import TestCase
from django.utils.timezone import make_aware
from users.management.commands.send_email_reminders import Command
from codewof.tests.codewof_test_data_generator import generate_users_with_notifications, generate_users, generate_questions
from codewof.tests.conftest import user
from django.contrib.auth import get_user_model
from utils.Weekday import Weekday
from programming.models import Attempt, Question
from django.utils import timezone
from django.http import HttpResponse
from unittest.mock import patch

User = get_user_model()


class GetUsersToEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # never modify this object in tests - read only
        generate_users_with_notifications(user)

    def setUp(self):
        self.john = User.objects.get(id=1)
        self.sally = User.objects.get(id=2)
        self.jane = User.objects.get(id=3)
        self.lazy = User.objects.get(id=4)
        self.brown = User.objects.get(id=5)

    def test_monday_returns_three_users(self):
        result = Command().get_users_to_email(Weekday.MONDAY)
        self.assertEqual({self.john, self.sally, self.brown}, set(result))

    def test_tuesday_returns_one_user(self):
        result = Command().get_users_to_email(Weekday.TUESDAY)
        self.assertEqual({self.brown}, set(result))

    def test_wednesday_returns_two_users(self):
        result = Command().get_users_to_email(Weekday.WEDNESDAY)
        self.assertEqual({self.sally, self.brown}, set(result))

    def test_thursday_returns_two_users(self):
        result = Command().get_users_to_email(Weekday.THURSDAY)
        self.assertEqual({self.john, self.brown}, set(result))

    def test_friday_returns_two_users(self):
        result = Command().get_users_to_email(Weekday.FRIDAY)
        self.assertEqual({self.sally, self.brown}, set(result))

    def test_saturday_returns_two_users(self):
        result = Command().get_users_to_email(Weekday.SATURDAY)
        self.assertEqual({self.jane, self.brown}, set(result))

    def test_sunday_returns_no_users(self):
        result = Command().get_users_to_email(Weekday.SUNDAY)
        self.assertEqual(set(), set(result))


class GetDaysSinceLastAttemptTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # never modify this object in tests - read only
        generate_users(user)
        generate_questions()

    def setUp(self):
        self.user = User.objects.get(id=1)
        self.question = Question.objects.get(slug='question-1')
        self.current_date = datetime.datetime(2020, 10, 21, tzinfo=timezone.get_current_timezone())

    def test_same_day_is_zero(self):
        attempt_date = datetime.datetime(2020, 10, 21, tzinfo=timezone.get_current_timezone())
        Attempt.objects.create(profile=self.user.profile, question=self.question, passed_tests=True,
                               datetime=attempt_date)
        days = Command().get_days_since_last_attempt(self.current_date, self.user)
        self.assertEqual(days, 0)

    def test_one_week_later_is_seven(self):
        attempt_date = datetime.datetime(2020, 10, 14, tzinfo=timezone.get_current_timezone())
        Attempt.objects.create(profile=self.user.profile, question=self.question, passed_tests=True,
                               datetime=attempt_date)
        days = Command().get_days_since_last_attempt(self.current_date, self.user)
        self.assertEqual(days, 7)

    def test_one_year_later_is_366(self):
        attempt_date = datetime.datetime(2019, 10, 21, tzinfo=timezone.get_current_timezone())
        Attempt.objects.create(profile=self.user.profile, question=self.question, passed_tests=True,
                               datetime=attempt_date)
        days = Command().get_days_since_last_attempt(self.current_date, self.user)
        self.assertEqual(days, 366)

    def test_current_date_before_attempt_date_is_invalid(self):
        attempt_date = datetime.datetime(2020, 10, 22, tzinfo=timezone.get_current_timezone())
        Attempt.objects.create(profile=self.user.profile, question=self.question, passed_tests=True,
                               datetime=attempt_date)
        self.assertRaises(ValueError, Command().get_days_since_last_attempt, self.current_date, self.user)

    def test_no_attempts_is_none(self):
        days = Command().get_days_since_last_attempt(self.current_date, self.user)
        self.assertIsNone(days)


class CreateMessageTests(TestCase):
    def test_zero_days_is_recent(self):
        message = Command().create_message(0)
        self.assertEqual(message, "You've been practicing recently. Keep it up!")

    def test_week_is_recent(self):
        message = Command().create_message(7)
        self.assertEqual(message, "You've been practicing recently. Keep it up!")

    def test_eight_days_is_awhile(self):
        message = Command().create_message(8)
        self.assertEqual(message, "It's been awhile since your last attempt. "
                                  "Remember to use CodeWOF regularly to keep your coding skills sharp.")

    def test_two_weeks_is_awhile(self):
        message = Command().create_message(14)
        self.assertEqual(message, "It's been awhile since your last attempt. "
                                  "Remember to use CodeWOF regularly to keep your coding skills sharp.")

    def test_fifteen_days_is_long_time(self):
        message = Command().create_message(15)
        self.assertEqual(message, "You haven't attempted a question in a long time. "
                                  "Try to use CodeWOF regularly to keep your coding skills sharp. "
                                  "If you don't want to use CodeWOF anymore, "
                                  "then click the link at the bottom of this email to stop getting reminders.")

    def test_no_attempts(self):
        message = Command().create_message(None)
        self.assertEqual(message, "You haven't attempted a question yet! "
                                  "Use CodeWOF regularly to keep your coding skills sharp."
                                  "If you don't want to use CodeWOF, "
                                  "then click the link at the bottom of this email to stop getting reminders.")


class BuildEmailTests(TestCase):
    def setUp(self):
        self.username = "User123"
        self.message = "A cool message"
        self.html = Command().build_email(self.username, self.message)
        self.response = HttpResponse(self.html)

    def test_html_contains_username(self):
        self.assertContains(self.response, "<p>Hi {},</p>".format(self.username), html=True)

    def test_html_contains_password(self):
        self.assertContains(self.response, "<p>{}</p>".format(self.message), html=True)
