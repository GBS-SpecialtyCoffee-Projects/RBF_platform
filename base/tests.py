from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError

from base.analytics import record_event, record_view
from base import analytics_reports
from base.models import (
    Connection, Conversation, Farmer, FarmerPhoto, Forum, ForumMeeting,
    ForumSignup, ForumWindow, InteractionEvent, InteractionEventType, Language,
    MeetingRequest, Message, ProfileChange, ProfileChangeSource, Roaster, Story,
)
from base.analytics import log_event
from base.notifications import notify_meeting_event


User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_FROM='noreply@coffeecircuit.test',
)
class MeetingNotificationTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser'
        )
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        Farmer.objects.create(
            user=self.farmer_user, firstname='Fiona', lastname='Farmer'
        )
        Roaster.objects.create(
            user=self.roaster_user, firstname='Roni', lastname='Roaster'
        )
        self.meeting_request = MeetingRequest.objects.create(
            requester=self.roaster_user,
            requestee=self.farmer_user,
            proposed_date=timezone.now() + timedelta(days=2),
            message='Looking forward to chatting.',
        )

    def test_created_event_emails_requestee(self):
        notify_meeting_event(self.meeting_request, 'created')
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['farmer@example.com'])
        self.assertIn('Roni Roaster', sent.subject)

    def test_accepted_event_emails_requester(self):
        self.meeting_request.status = 'accepted'
        self.meeting_request.save()
        notify_meeting_event(self.meeting_request, 'accepted')
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['roaster@example.com'])
        self.assertIn('accepted', sent.subject)
        self.assertIn('Fiona Farmer', sent.subject)

    def test_rejected_event_emails_requester(self):
        self.meeting_request.status = 'rejected'
        self.meeting_request.save()
        notify_meeting_event(self.meeting_request, 'rejected')
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['roaster@example.com'])
        self.assertIn('declined', sent.subject)


class RoasterViewTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser'
        )
        self.farmer_user.set_password('pw')
        self.farmer_user.save()
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        self.roaster_user.set_password('pw')
        self.roaster_user.save()
        Farmer.objects.create(
            user=self.farmer_user,
            firstname='Fiona',
            lastname='Farmer',
            is_details_filled=True,
        )
        Roaster.objects.create(
            user=self.roaster_user,
            firstname='Roni',
            lastname='Roaster',
            company_name='Beans & Co',
            is_details_filled=True,
        )

    def test_farmer_can_view_roaster_profile(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.get(
            reverse('roaster_profile', args=[self.roaster_user.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Beans &amp; Co')

    def test_other_roaster_is_redirected_from_roaster_profile(self):
        other_roaster = User.objects.create(
            email='other@example.com', group='roaster', username='other'
        )
        other_roaster.set_password('pw')
        other_roaster.save()
        Roaster.objects.create(
            user=other_roaster,
            firstname='Other',
            lastname='Roaster',
            company_name='Other Co',
            is_details_filled=True,
        )
        self.client.login(email='other@example.com', password='pw')
        response = self.client.get(
            reverse('roaster_profile', args=[self.roaster_user.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('roaster_dashboard'))

    def test_roaster_can_view_own_profile(self):
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.get(
            reverse('roaster_profile', args=[self.roaster_user.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Beans &amp; Co')

    def _send_connect(self):
        return self.client.post(
            reverse('connection_farmers'),
            {'user_id': self.farmer_user.id, 'message': 'Hi'},
        )

    def test_roaster_cannot_send_duplicate_active_request(self):
        self.client.login(email='roaster@example.com', password='pw')
        Connection.request(self.roaster_user, self.farmer_user)
        self._send_connect()
        # Still exactly one Connection row for the pair, still pending.
        conn = Connection.between(self.roaster_user, self.farmer_user)
        self.assertEqual(
            Connection.objects.filter(initiator=self.roaster_user).count(), 1
        )
        self.assertEqual(conn.status, Connection.PENDING)

    def test_roaster_can_send_request_after_previous_rejected(self):
        self.client.login(email='roaster@example.com', password='pw')
        conn = Connection.request(self.roaster_user, self.farmer_user)
        conn.decline()
        self._send_connect()
        conn.refresh_from_db()
        # Same row re-opened to pending (no duplicate).
        self.assertEqual(conn.status, Connection.PENDING)
        self.assertEqual(Connection.objects.count(), 1)

    def test_other_farmer_is_redirected_from_farmer_profile(self):
        other_farmer = User.objects.create(
            email='otherfarmer@example.com', group='farmer', username='otherfarmer'
        )
        other_farmer.set_password('pw')
        other_farmer.save()
        Farmer.objects.create(
            user=other_farmer,
            firstname='Other',
            lastname='Farmer',
            is_details_filled=True,
        )
        self.client.login(email='otherfarmer@example.com', password='pw')
        response = self.client.get(
            reverse('farmer_profile', args=[self.farmer_user.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('farmer_dashboard'))


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_FROM='noreply@coffeecircuit.test',
)
class FarmerManageConnectionTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser'
        )
        self.farmer_user.set_password('pw')
        self.farmer_user.save()
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        self.roaster_user.set_password('pw')
        self.roaster_user.save()
        Farmer.objects.create(
            user=self.farmer_user, firstname='Fiona', lastname='Farmer',
            is_details_filled=True,
        )
        Roaster.objects.create(
            user=self.roaster_user, firstname='Roni', lastname='Roaster',
            company_name='Beans & Co', is_details_filled=True,
        )
        # Roaster initiated a pending connection to the farmer.
        self.connection = Connection.request(self.roaster_user, self.farmer_user)

    def _url(self, action):
        return reverse('manage_connection_request', args=[self.connection.id, action])

    def test_accept_sets_status_and_redirects_to_referer(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(
            self._url('accept'), HTTP_REFERER='http://testserver/farmer_connections/'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'http://testserver/farmer_connections/')
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, Connection.ACTIVE)

    def test_reject_sets_status(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(self._url('reject'))
        self.assertEqual(response.status_code, 302)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, Connection.DECLINED)

    def test_get_not_allowed(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.get(self._url('accept'))
        self.assertEqual(response.status_code, 405)

    def test_invalid_action_is_a_noop(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(
            reverse('manage_connection_request', args=[self.connection.id, 'bogus'])
        )
        self.assertEqual(response.status_code, 302)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, Connection.PENDING)

    def test_initiator_cannot_accept_own_request(self):
        # Roaster is the initiator; accepting is the recipient's action only.
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.post(self._url('accept'))
        self.assertEqual(response.status_code, 302)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, Connection.PENDING)

    def test_uninvolved_user_gets_404(self):
        other_farmer = User.objects.create(
            email='otherfarmer@example.com', group='farmer', username='otherfarmer'
        )
        other_farmer.set_password('pw')
        other_farmer.save()
        Farmer.objects.create(
            user=other_farmer, firstname='Other', lastname='Farmer',
            is_details_filled=True,
        )
        self.client.login(email='otherfarmer@example.com', password='pw')
        response = self.client.post(self._url('accept'))
        self.assertEqual(response.status_code, 404)

    def test_external_referer_falls_back(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(
            self._url('accept'), HTTP_REFERER='http://evil.example.com/x'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('farmer_dashboard'))


class ChatThreadTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser'
        )
        self.farmer_user.set_password('pw')
        self.farmer_user.save()
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        self.roaster_user.set_password('pw')
        self.roaster_user.save()
        Farmer.objects.create(
            user=self.farmer_user, firstname='Fiona', lastname='Farmer', is_details_filled=True
        )
        Roaster.objects.create(
            user=self.roaster_user, firstname='Roni', lastname='Roaster',
            company_name='Beans & Co', is_details_filled=True,
        )

    def _accept_connection(self):
        conn = Connection.request(self.roaster_user, self.farmer_user)
        conn.accept()
        return conn

    def test_thread_forbidden_without_accepted_connection(self):
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.get(reverse('chat_thread', args=[self.farmer_user.id]))
        self.assertEqual(response.status_code, 403)

    def test_thread_forbidden_with_only_pending_connection(self):
        Connection.request(self.roaster_user, self.farmer_user)
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.get(reverse('chat_thread', args=[self.farmer_user.id]))
        self.assertEqual(response.status_code, 403)

    def test_conversation_autocreated_on_first_open(self):
        self._accept_connection()
        self.assertEqual(Conversation.objects.count(), 0)
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.get(reverse('chat_thread', args=[self.farmer_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 1)
        conv = Conversation.objects.get()
        self.assertEqual(conv.roaster, self.roaster_user)
        self.assertEqual(conv.farmer, self.farmer_user)

    def test_either_party_resolves_same_conversation(self):
        self._accept_connection()
        self.client.login(email='roaster@example.com', password='pw')
        self.client.get(reverse('chat_thread', args=[self.farmer_user.id]))
        self.client.logout()
        self.client.login(email='farmer@example.com', password='pw')
        self.client.get(reverse('chat_thread', args=[self.roaster_user.id]))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_thread_marks_other_party_messages_read(self):
        self._accept_connection()
        conv = Conversation.objects.create(roaster=self.roaster_user, farmer=self.farmer_user)
        Message.objects.create(conversation=conv, sender=self.farmer_user, body='hi')
        Message.objects.create(conversation=conv, sender=self.roaster_user, body='hello')
        self.client.login(email='roaster@example.com', password='pw')
        self.client.get(reverse('chat_thread', args=[self.farmer_user.id]))
        farmer_msg = Message.objects.get(sender=self.farmer_user)
        roaster_msg = Message.objects.get(sender=self.roaster_user)
        self.assertIsNotNone(farmer_msg.read_at)
        self.assertIsNone(roaster_msg.read_at)

    def test_chat_list_shows_unread_count(self):
        self._accept_connection()
        conv = Conversation.objects.create(roaster=self.roaster_user, farmer=self.farmer_user)
        Message.objects.create(conversation=conv, sender=self.farmer_user, body='hi')
        Message.objects.create(conversation=conv, sender=self.farmer_user, body='you there?')
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.get(reverse('chat_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['items'][0]['unread_count'], 2)


class IncompleteProfileSignoutTests(TestCase):
    """A roaster mid-onboarding must still be able to sign out.

    Regression: AuthMiddleware redirected incomplete profiles to the details
    page for every non-excluded path, which swallowed the signout POST.
    """

    def setUp(self):
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        Roaster.objects.create(
            user=self.roaster_user, firstname='Roni', lastname='Roaster',
            is_details_filled=False,
        )

    def test_incomplete_roaster_can_sign_out(self):
        self.client.force_login(self.roaster_user)
        response = self.client.post(reverse('signout'))
        self.assertRedirects(response, reverse('signin'), fetch_redirect_response=False)
        # Session is cleared, so a follow-up request is no longer authenticated.
        self.assertNotIn('_auth_user_id', self.client.session)


class ConnectionModelTests(TestCase):
    def setUp(self):
        self.roaster = User.objects.create(
            email='r@example.com', group='roaster', username='r'
        )
        self.farmer = User.objects.create(
            email='f@example.com', group='farmer', username='f'
        )

    def test_request_is_idempotent_while_live(self):
        c1 = Connection.request(self.roaster, self.farmer, message='hi')
        c2 = Connection.request(self.roaster, self.farmer, message='again')
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(Connection.objects.count(), 1)
        self.assertEqual(c2.status, Connection.PENDING)

    def test_one_row_per_pair_regardless_of_direction(self):
        Connection.request(self.roaster, self.farmer)
        # Reverse-direction request resolves to the same row.
        again = Connection.request(self.farmer, self.roaster)
        self.assertEqual(Connection.objects.count(), 1)
        self.assertEqual(again.status, Connection.PENDING)

    def test_status_for_perspective(self):
        conn = Connection.request(self.roaster, self.farmer)
        self.assertEqual(conn.status_for(self.roaster), 'sent')
        self.assertEqual(conn.status_for(self.farmer), 'incoming')
        conn.accept()
        self.assertEqual(conn.status_for(self.roaster), 'connected')
        self.assertEqual(conn.status_for(self.farmer), 'connected')

    def test_re_request_after_decline(self):
        conn = Connection.request(self.roaster, self.farmer)
        conn.decline()
        reopened = Connection.request(self.farmer, self.roaster)
        self.assertEqual(reopened.pk, conn.pk)
        self.assertEqual(reopened.status, Connection.PENDING)
        self.assertEqual(reopened.initiator_id, self.farmer.id)

    def test_status_sets_for(self):
        other_farmer = User.objects.create(
            email='f2@example.com', group='farmer', username='f2'
        )
        active = Connection.request(self.roaster, self.farmer)
        active.accept()
        Connection.request(self.roaster, other_farmer)  # outgoing pending
        connected, sent, incoming = Connection.status_sets_for(self.roaster)
        self.assertEqual(connected, {self.farmer.id})
        self.assertEqual(sent, {other_farmer.id})
        self.assertEqual(incoming, set())

    def test_pending_sent_count(self):
        f2 = User.objects.create(email='f2@example.com', group='farmer', username='f2')
        Connection.request(self.roaster, self.farmer)
        Connection.request(self.roaster, f2)
        self.assertEqual(Connection.pending_sent_count(self.roaster), 2)


class ForumWindowModelTests(TestCase):
    def test_clean_rejects_end_before_start(self):
        forum = Forum.objects.create(title='Spring Forum')
        start = timezone.now()
        window = ForumWindow(forum=forum, starts_at=start, ends_at=start - timedelta(hours=1))
        with self.assertRaises(ValidationError):
            window.full_clean()

    def test_clean_accepts_valid_window(self):
        forum = Forum.objects.create(title='Spring Forum')
        start = timezone.now()
        window = ForumWindow(forum=forum, starts_at=start, ends_at=start + timedelta(hours=2))
        window.full_clean()  # should not raise


class ForumNextUpcomingTests(TestCase):
    def _forum_with_window(self, title, start, status=Forum.PUBLISHED):
        forum = Forum.objects.create(title=title, status=status)
        ForumWindow.objects.create(
            forum=forum, starts_at=start, ends_at=start + timedelta(hours=2),
        )
        return forum

    def test_returns_soonest_future_published_forum(self):
        now = timezone.now()
        self._forum_with_window('Later', now + timedelta(days=10))
        sooner = self._forum_with_window('Sooner', now + timedelta(days=3))
        self.assertEqual(Forum.next_upcoming(), sooner)

    def test_ignores_past_windows(self):
        now = timezone.now()
        self._forum_with_window('Past', now - timedelta(days=1))
        self.assertIsNone(Forum.next_upcoming())

    def test_ignores_unpublished_forums(self):
        now = timezone.now()
        self._forum_with_window('Draft', now + timedelta(days=3), status=Forum.DRAFT)
        self.assertIsNone(Forum.next_upcoming())

    def test_next_window_start_is_soonest_future_window(self):
        now = timezone.now()
        forum = Forum.objects.create(title='Multi', status=Forum.PUBLISHED)
        ForumWindow.objects.create(
            forum=forum, starts_at=now - timedelta(days=1),
            ends_at=now - timedelta(days=1) + timedelta(hours=2),
        )
        future = now + timedelta(days=5)
        ForumWindow.objects.create(
            forum=forum, starts_at=future, ends_at=future + timedelta(hours=2),
        )
        self.assertEqual(forum.next_window_start, future)


class ForumSoonestToJoinTests(TestCase):
    def setUp(self):
        self.viewer = User.objects.create(
            email='viewer@example.com', group='roaster', username='viewer',
        )
        self.other = User.objects.create(
            email='other@example.com', group='farmer', username='other',
        )

    def _forum_with_window(self, title, start, status=Forum.PUBLISHED):
        forum = Forum.objects.create(title=title, status=status)
        ForumWindow.objects.create(
            forum=forum, starts_at=start, ends_at=start + timedelta(hours=2),
        )
        return forum

    def test_returns_soonest_forum_other_joined_and_viewer_did_not(self):
        now = timezone.now()
        later = self._forum_with_window('Later', now + timedelta(days=10))
        sooner = self._forum_with_window('Sooner', now + timedelta(days=3))
        ForumSignup.objects.create(forum=later, user=self.other)
        ForumSignup.objects.create(forum=sooner, user=self.other)
        self.assertEqual(Forum.soonest_to_join(self.viewer, self.other), sooner)

    def test_excludes_forums_viewer_already_joined(self):
        now = timezone.now()
        forum = self._forum_with_window('Shared', now + timedelta(days=3))
        ForumSignup.objects.create(forum=forum, user=self.other)
        ForumSignup.objects.create(forum=forum, user=self.viewer)
        self.assertIsNone(Forum.soonest_to_join(self.viewer, self.other))

    def test_returns_none_when_other_signed_up_for_nothing(self):
        now = timezone.now()
        self._forum_with_window('Open', now + timedelta(days=3))
        self.assertIsNone(Forum.soonest_to_join(self.viewer, self.other))

    def test_ignores_past_and_unpublished_forums(self):
        now = timezone.now()
        past = self._forum_with_window('Past', now - timedelta(days=1))
        draft = self._forum_with_window(
            'Draft', now + timedelta(days=3), status=Forum.DRAFT,
        )
        ForumSignup.objects.create(forum=past, user=self.other)
        ForumSignup.objects.create(forum=draft, user=self.other)
        self.assertIsNone(Forum.soonest_to_join(self.viewer, self.other))


class ForumAdminTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create(
            email='staff@example.com', group='roaster', username='staffuser',
            is_staff=True,
        )
        self.client.force_login(self.staff)

    def _window_post(self, start, total=3):
        data = {
            'windows-TOTAL_FORMS': str(total),
            'windows-INITIAL_FORMS': '0',
            'windows-MIN_NUM_FORMS': '0',
            'windows-MAX_NUM_FORMS': '1000',
            'windows-0-label': 'Morning',
            'windows-0-starts_at': start.strftime('%Y-%m-%dT%H:%M'),
            'windows-0-ends_at': (start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        }
        for i in range(1, total):
            data[f'windows-{i}-label'] = ''
            data[f'windows-{i}-starts_at'] = ''
            data[f'windows-{i}-ends_at'] = ''
        return data

    def test_list_requires_staff(self):
        self.client.logout()
        resp = self.client.get(reverse('admin_forums'))
        self.assertEqual(resp.status_code, 302)

    def test_create_forum_with_windows(self):
        start = timezone.now() + timedelta(days=7)
        data = {
            'title': 'Spring Forum',
            'description': '',
            'format': 'hybrid',
            'location': '',
            'link': '',
            'status': 'published',
        }
        data.update(self._window_post(start))
        resp = self.client.post(reverse('admin_forum_create'), data)
        self.assertEqual(resp.status_code, 302)
        forum = Forum.objects.get(title='Spring Forum')
        self.assertEqual(forum.created_by, self.staff)
        self.assertEqual(forum.windows.count(), 1)

    def test_create_forum_rejects_bad_window(self):
        start = timezone.now() + timedelta(days=7)
        data = {
            'title': 'Bad Forum',
            'description': '',
            'format': 'virtual',
            'location': '',
            'link': '',
            'status': 'draft',
            'windows-TOTAL_FORMS': '1',
            'windows-INITIAL_FORMS': '0',
            'windows-MIN_NUM_FORMS': '0',
            'windows-MAX_NUM_FORMS': '1000',
            'windows-0-label': 'Broken',
            'windows-0-starts_at': start.strftime('%Y-%m-%dT%H:%M'),
            'windows-0-ends_at': (start - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
        }
        resp = self.client.post(reverse('admin_forum_create'), data)
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertFalse(Forum.objects.filter(title='Bad Forum').exists())

    def test_delete_forum(self):
        forum = Forum.objects.create(title='Temp', created_by=self.staff)
        resp = self.client.post(reverse('admin_forum_delete', args=[forum.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Forum.objects.filter(id=forum.id).exists())


class ForumSignupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email='attendee@example.com', group='farmer', username='attendee',
        )
        self.client.force_login(self.user)
        self.forum = Forum.objects.create(title='Spring Forum', status=Forum.PUBLISHED)

    def test_list_shows_only_published_forums(self):
        Forum.objects.create(title='Draft Forum', status=Forum.DRAFT)
        resp = self.client.get(reverse('forum_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Spring Forum')
        self.assertNotContains(resp, 'Draft Forum')

    def test_detail_renders_windows(self):
        start = timezone.now() + timedelta(days=7)
        ForumWindow.objects.create(
            forum=self.forum, label='Morning',
            starts_at=start, ends_at=start + timedelta(hours=2),
        )
        resp = self.client.get(reverse('forum_detail', args=[self.forum.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Morning')

    def test_signup_creates_row(self):
        resp = self.client.post(reverse('forum_signup', args=[self.forum.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            ForumSignup.objects.filter(forum=self.forum, user=self.user).exists()
        )

    def test_duplicate_signup_is_idempotent(self):
        ForumSignup.objects.create(forum=self.forum, user=self.user)
        self.client.post(reverse('forum_signup', args=[self.forum.id]))
        self.assertEqual(
            ForumSignup.objects.filter(forum=self.forum, user=self.user).count(), 1
        )

    def test_signup_blocked_for_unpublished_forum(self):
        draft = Forum.objects.create(title='Draft Forum', status=Forum.DRAFT)
        self.client.post(reverse('forum_signup', args=[draft.id]))
        self.assertFalse(
            ForumSignup.objects.filter(forum=draft, user=self.user).exists()
        )

    def test_cancel_removes_signup(self):
        ForumSignup.objects.create(forum=self.forum, user=self.user)
        resp = self.client.post(reverse('forum_cancel_signup', args=[self.forum.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            ForumSignup.objects.filter(forum=self.forum, user=self.user).exists()
        )


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_FROM='noreply@coffeecircuit.test',
)
class ForumMeetingTests(TestCase):
    def setUp(self):
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        self.farmer = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        Connection.request(self.roaster, self.farmer).accept()
        self.conversation = Conversation.objects.create(
            roaster=self.roaster, farmer=self.farmer,
        )
        self.forum = Forum.objects.create(title='Spring Forum', status=Forum.PUBLISHED)
        start = timezone.now() + timedelta(days=7)
        self.window = ForumWindow.objects.create(
            forum=self.forum, label='Morning',
            starts_at=start, ends_at=start + timedelta(hours=2),
        )
        ForumSignup.objects.create(forum=self.forum, user=self.roaster)
        ForumSignup.objects.create(forum=self.forum, user=self.farmer)

    def _propose(self):
        self.client.force_login(self.roaster)
        return self.client.post(
            reverse('propose_meeting', args=[self.farmer.id]),
            {'window_id': self.window.id},
        )

    def test_propose_creates_meeting_when_both_signed_up(self):
        resp = self._propose()
        self.assertEqual(resp.status_code, 302)
        meeting = ForumMeeting.objects.get(conversation=self.conversation)
        self.assertEqual(meeting.status, ForumMeeting.PROPOSED)
        self.assertEqual(meeting.proposed_by, self.roaster)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.farmer.email])

    def test_propose_blocked_when_invitee_not_signed_up(self):
        ForumSignup.objects.filter(forum=self.forum, user=self.farmer).delete()
        self._propose()
        self.assertFalse(ForumMeeting.objects.exists())

    def test_propose_blocked_for_unpublished_forum(self):
        self.forum.status = Forum.DRAFT
        self.forum.save()
        self._propose()
        self.assertFalse(ForumMeeting.objects.exists())

    def test_proposable_windows_excludes_live_meeting(self):
        self._propose()
        self.assertNotIn(
            self.window, ForumMeeting.proposable_windows(self.conversation)
        )

    def test_invitee_confirms(self):
        self._propose()
        meeting = ForumMeeting.objects.get()
        self.client.force_login(self.farmer)
        resp = self.client.post(reverse('respond_meeting', args=[meeting.id, 'confirm']))
        self.assertEqual(resp.status_code, 302)
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, ForumMeeting.CONFIRMED)

    def test_proposer_cannot_confirm_own(self):
        self._propose()
        meeting = ForumMeeting.objects.get()
        self.client.force_login(self.roaster)
        self.client.post(reverse('respond_meeting', args=[meeting.id, 'confirm']))
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, ForumMeeting.PROPOSED)

    def test_invitee_declines(self):
        self._propose()
        meeting = ForumMeeting.objects.get()
        self.client.force_login(self.farmer)
        self.client.post(reverse('respond_meeting', args=[meeting.id, 'decline']))
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, ForumMeeting.DECLINED)

    def test_proposer_cancels(self):
        self._propose()
        meeting = ForumMeeting.objects.get()
        self.client.force_login(self.roaster)
        self.client.post(reverse('respond_meeting', args=[meeting.id, 'cancel']))
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, ForumMeeting.CANCELLED)


class EndedForumHiddenTests(TestCase):
    def setUp(self):
        self.roaster = User.objects.create(
            email='r@example.com', group='roaster', username='r',
        )
        self.farmer = User.objects.create(
            email='f@example.com', group='farmer', username='f',
        )
        Connection.request(self.roaster, self.farmer).accept()
        self.conversation = Conversation.objects.create(
            roaster=self.roaster, farmer=self.farmer,
        )

    def _forum(self, title, start, status=Forum.PUBLISHED):
        forum = Forum.objects.create(title=title, status=status)
        window = ForumWindow.objects.create(
            forum=forum, starts_at=start, ends_at=start + timedelta(hours=2),
        )
        return forum, window

    def test_is_over_true_only_when_all_windows_passed(self):
        now = timezone.now()
        ended, _ = self._forum('Ended', now - timedelta(days=2))
        live, _ = self._forum('Live', now + timedelta(days=2))
        empty = Forum.objects.create(title='Empty', status=Forum.PUBLISHED)
        self.assertTrue(ended.is_over)
        self.assertFalse(live.is_over)
        self.assertFalse(empty.is_over)

    def test_proposable_windows_excludes_past_windows(self):
        now = timezone.now()
        _, past = self._forum('Past', now - timedelta(days=2))
        ForumSignup.objects.create(forum=past.forum, user=self.roaster)
        ForumSignup.objects.create(forum=past.forum, user=self.farmer)
        self.assertNotIn(
            past, ForumMeeting.proposable_windows(self.conversation)
        )

    def test_for_display_hides_meetings_of_ended_forum(self):
        now = timezone.now()
        _, past = self._forum('Past', now - timedelta(days=2))
        ForumMeeting.objects.create(
            conversation=self.conversation, window=past,
            proposed_by=self.roaster, status=ForumMeeting.CONFIRMED,
        )
        self.assertEqual(ForumMeeting.for_display(self.conversation).count(), 0)

    def test_for_display_keeps_meetings_of_live_forum(self):
        now = timezone.now()
        _, future = self._forum('Live', now + timedelta(days=2))
        meeting = ForumMeeting.objects.create(
            conversation=self.conversation, window=future,
            proposed_by=self.roaster, status=ForumMeeting.DECLINED,
        )
        self.assertIn(meeting, ForumMeeting.for_display(self.conversation))

    def test_forum_list_excludes_ended_forum(self):
        now = timezone.now()
        self._forum('Ended Forum', now - timedelta(days=2))
        self._forum('Live Forum', now + timedelta(days=2))
        self.client.force_login(self.farmer)
        resp = self.client.get(reverse('forum_list'))
        self.assertContains(resp, 'Live Forum')
        self.assertNotContains(resp, 'Ended Forum')

    def test_forum_detail_404_for_ended_forum(self):
        now = timezone.now()
        ended, _ = self._forum('Ended', now - timedelta(days=2))
        self.client.force_login(self.farmer)
        resp = self.client.get(reverse('forum_detail', args=[ended.id]))
        self.assertEqual(resp.status_code, 404)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_FROM='noreply@coffeecircuit.test',
)
class AdminMeetingsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(
            email='admin@example.com', username='admin', is_staff=True,
        )
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        self.farmer = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        self.conversation = Conversation.objects.create(
            roaster=self.roaster, farmer=self.farmer,
        )
        self.forum = Forum.objects.create(title='Spring Forum', status=Forum.PUBLISHED)
        start = timezone.now() + timedelta(days=7)
        self.window = ForumWindow.objects.create(
            forum=self.forum, starts_at=start, ends_at=start + timedelta(hours=2),
        )

    def _meeting(self, status=ForumMeeting.CONFIRMED, window=None):
        return ForumMeeting.objects.create(
            conversation=self.conversation, window=window or self.window,
            proposed_by=self.roaster, status=status,
        )

    def test_list_shows_only_confirmed_upcoming(self):
        confirmed = self._meeting()
        self._meeting(status=ForumMeeting.PROPOSED)
        past_start = timezone.now() - timedelta(days=1)
        past_window = ForumWindow.objects.create(
            forum=self.forum, starts_at=past_start,
            ends_at=past_start + timedelta(hours=2),
        )
        self._meeting(window=past_window)
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('admin_meetings'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context['meetings']), [confirmed])

    def test_send_invite_sets_timestamp_and_emails_both(self):
        meeting = self._meeting()
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('admin_meeting_send_invite', args=[meeting.id]),
            {'meeting_link': 'https://zoom.us/j/123'},
        )
        self.assertEqual(resp.status_code, 302)
        meeting.refresh_from_db()
        self.assertIsNotNone(meeting.invite_sent_at)
        self.assertEqual(meeting.meeting_link, 'https://zoom.us/j/123')
        self.assertEqual(len(mail.outbox), 2)
        recipients = {addr for m in mail.outbox for addr in m.to}
        self.assertEqual(recipients, {self.roaster.email, self.farmer.email})
        attachment = mail.outbox[0].attachments[0]
        self.assertEqual(attachment[0], 'meeting.ics')
        self.assertIn('BEGIN:VCALENDAR', attachment[1])
        self.assertIn('https://zoom.us/j/123', attachment[1])

    def test_send_invite_requires_staff(self):
        meeting = self._meeting()
        self.client.force_login(self.roaster)
        resp = self.client.post(
            reverse('admin_meeting_send_invite', args=[meeting.id])
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('admin_login'), resp.url)
        meeting.refresh_from_db()
        self.assertIsNone(meeting.invite_sent_at)
        self.assertEqual(len(mail.outbox), 0)


class LogEventTests(TestCase):
    def setUp(self):
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        self.farmer = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )

    def test_log_event_records_row_with_metadata(self):
        log_event(
            InteractionEventType.PROFILE_VIEW, user=self.roaster,
            target_user=self.farmer, source='test',
        )
        event = InteractionEvent.objects.get()
        self.assertEqual(event.event_type, InteractionEventType.PROFILE_VIEW)
        self.assertEqual(event.user, self.roaster)
        self.assertEqual(event.target_user, self.farmer)
        self.assertEqual(event.metadata, {'source': 'test'})

    def test_log_event_swallows_errors(self):
        # An over-long event_type violates the column, but logging must never
        # raise into the request flow — it is caught and logged instead.
        with self.assertLogs('base.analytics', level='ERROR'):
            log_event('x' * 100, user=self.roaster)
        self.assertFalse(InteractionEvent.objects.exists())


class AdminInteractionsTests(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create(
            email='super@example.com', username='super',
            is_staff=True, is_superuser=True,
        )
        self.staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True,
        )
        self.viewer = User.objects.create(
            email='viewer@example.com', group='roaster', username='viewer',
        )
        InteractionEvent.objects.create(
            event_type=InteractionEventType.LOGIN, user=self.viewer,
        )
        InteractionEvent.objects.create(
            event_type=InteractionEventType.RESOURCE_VIEW, user=self.viewer,
        )

    def test_staff_admin_sees_events(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('admin_interactions'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['events'].paginator.count, 2)

    def test_event_type_filter(self):
        self.client.force_login(self.staff)
        resp = self.client.get(
            reverse('admin_interactions'),
            {'event_type': InteractionEventType.LOGIN},
        )
        self.assertEqual(resp.context['events'].paginator.count, 1)

    def test_csv_export(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('admin_interactions'), {'export': 'csv'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        body = resp.content.decode()
        self.assertIn('event_type', body)
        self.assertIn(InteractionEventType.LOGIN, body)

    def test_non_staff_redirected(self):
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse('admin_interactions'))
        self.assertEqual(resp.status_code, 302)


class AdminStaffAccessTests(TestCase):
    """Every platform-admin page is open to any staff admin, not just superusers."""

    STAFF_PAGES = [
        'admin_dashboard', 'admin_farmers', 'admin_roasters', 'admin_users',
        'admin_create', 'admin_audit_log', 'admin_pending_requests',
        'admin_interactions', 'admin_resources', 'admin_forums', 'admin_meetings',
    ]

    def setUp(self):
        self.staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True,
        )
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )

    def test_staff_can_open_every_admin_page(self):
        self.client.force_login(self.staff)
        for name in self.STAFF_PAGES:
            with self.subTest(page=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 200)

    def test_non_staff_redirected_from_every_admin_page(self):
        self.client.force_login(self.roaster)
        for name in self.STAFF_PAGES:
            with self.subTest(page=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 302)

    def test_staff_can_toggle_another_admin(self):
        other = User.objects.create(
            email='other@example.com', username='other', is_staff=True,
        )
        self.client.force_login(self.staff)
        self.client.post(reverse('admin_toggle', args=[other.id]))
        other.refresh_from_db()
        self.assertFalse(other.is_staff)

    def test_superuser_accounts_stay_protected_from_toggle(self):
        superuser = User.objects.create(
            email='super@example.com', username='super',
            is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.staff)
        self.client.post(reverse('admin_toggle', args=[superuser.id]))
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_staff)


class AdminPendingRequestsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True,
        )
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )

    def _farmer(self, name):
        return User.objects.create(
            email=f'{name}@example.com', group='farmer', username=name,
        )

    def _page(self):
        self.client.force_login(self.staff)
        return self.client.get(reverse('admin_pending_requests'))

    def test_lists_only_pending_connections(self):
        Connection.request(self.roaster, self._farmer('waiting'))
        Connection.request(self.roaster, self._farmer('accepted')).accept()
        Connection.objects.create(
            user_a=self.roaster, user_b=self._farmer('declined'),
            initiator=self.roaster, status=Connection.DECLINED,
        )

        resp = self._page()
        self.assertEqual(resp.status_code, 200)
        rows = resp.context['connections']
        self.assertEqual(rows.paginator.count, 1)
        self.assertEqual(rows[0].recipient.email, 'waiting@example.com')

    def test_shows_initiator_and_target(self):
        farmer = self._farmer('target')
        connection = Connection.request(farmer, self.roaster)

        row = self._page().context['connections'][0]
        self.assertEqual(row.initiator, farmer)
        self.assertEqual(row.recipient, self.roaster)
        self.assertEqual(row.id, connection.id)

    def test_longest_waiting_listed_first(self):
        newest = Connection.request(self.roaster, self._farmer('newest'))
        oldest = Connection.request(self.roaster, self._farmer('oldest'))
        # created_at is auto_now_add, so rewrite it to age the row.
        Connection.objects.filter(id=oldest.id).update(
            created_at=timezone.now() - timedelta(days=10),
        )

        rows = self._page().context['connections']
        self.assertEqual([row.id for row in rows], [oldest.id, newest.id])

    def test_non_staff_redirected(self):
        self.client.force_login(self.roaster)
        resp = self.client.get(reverse('admin_pending_requests'))
        self.assertEqual(resp.status_code, 302)


class AdminEngagementTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True,
        )
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        Roaster.objects.create(
            user=self.roaster, firstname='Roni', lastname='Roaster',
            company_name='Beans & Co', is_details_filled=True,
        )

    def _farmer(self, name):
        user = User.objects.create(
            email=f'{name}@example.com', group='farmer', username=name,
        )
        Farmer.objects.create(
            user=user, firstname=name.title(), lastname='Farmer',
            is_details_filled=True,
        )
        return user

    def _rows(self, **params):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('admin_engagement'), params)
        self.assertEqual(resp.status_code, 200)
        return {row.email: row for row in resp.context['users']}

    def test_counts_requests_sent_and_received(self):
        farmer = self._farmer('ada')
        Connection.request(self.roaster, farmer)

        rows = self._rows()
        self.assertEqual(rows['roaster@example.com'].requests_sent, 1)
        self.assertEqual(rows['roaster@example.com'].connections_received, 0)
        self.assertEqual(rows['ada@example.com'].connections_received, 1)
        self.assertEqual(rows['ada@example.com'].requests_sent, 0)

    def test_received_counts_both_sides_of_the_pair(self):
        """user_a/user_b ordering is by id, so the recipient may sit on
        either side — both must be counted."""
        low, high = self._farmer('aaa'), self._farmer('zzz')
        Connection.request(low, self.roaster)
        Connection.request(high, self.roaster)

        rows = self._rows()
        self.assertEqual(rows['roaster@example.com'].connections_received, 2)

    def test_unaccepted_excludes_answered_requests(self):
        Connection.request(self.roaster, self._farmer('waiting'))
        Connection.request(self.roaster, self._farmer('accepted')).accept()
        Connection.request(self.roaster, self._farmer('declined')).decline()

        rows = self._rows()
        self.assertEqual(rows['waiting@example.com'].connections_unaccepted, 1)
        self.assertEqual(rows['accepted@example.com'].connections_unaccepted, 0)
        self.assertEqual(rows['declined@example.com'].connections_unaccepted, 0)
        # Answered requests still count as received.
        self.assertEqual(rows['declined@example.com'].connections_received, 1)

    def test_meeting_counts_by_status(self):
        farmer = self._farmer('meeter')
        conversation = Conversation.objects.create(
            roaster=self.roaster, farmer=farmer,
        )
        forum = Forum.objects.create(title='Harvest', status=Forum.PUBLISHED)
        window = ForumWindow.objects.create(
            forum=forum,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1),
        )
        other = ForumWindow.objects.create(
            forum=forum,
            starts_at=timezone.now() + timedelta(days=1, hours=2),
            ends_at=timezone.now() + timedelta(days=1, hours=3),
        )
        ForumMeeting.objects.create(
            conversation=conversation, window=window,
            proposed_by=self.roaster, status=ForumMeeting.CONFIRMED,
        )
        ForumMeeting.objects.create(
            conversation=conversation, window=other,
            proposed_by=self.roaster, status=ForumMeeting.PROPOSED,
        )

        rows = self._rows()
        for email in ('roaster@example.com', 'meeter@example.com'):
            self.assertEqual(rows[email].meetings_scheduled, 1)
            self.assertEqual(rows[email].meetings_pending, 1)

    def test_user_with_no_activity_shows_zeros(self):
        self._farmer('quiet')

        row = self._rows()['quiet@example.com']
        self.assertEqual(row.connections_received, 0)
        self.assertEqual(row.connections_unaccepted, 0)
        self.assertEqual(row.requests_sent, 0)
        self.assertEqual(row.meetings_scheduled, 0)
        self.assertEqual(row.meetings_pending, 0)
        self.assertIsNone(row.last_activity)

    def test_staff_excluded_from_listing(self):
        self.assertNotIn('staff@example.com', self._rows())

    def test_idle_filter_selects_dormant_and_never_active(self):
        active = self._farmer('active')
        stale = self._farmer('stale')
        self._farmer('never')
        log_event(InteractionEventType.LOGIN, user=active)
        log_event(InteractionEventType.LOGIN, user=stale)
        InteractionEvent.objects.filter(user=stale).update(
            created_at=timezone.now() - timedelta(days=60),
        )

        emails = self._rows(idle='30').keys()
        self.assertIn('stale@example.com', emails)
        self.assertIn('never@example.com', emails)
        self.assertNotIn('active@example.com', emails)

    def test_blocking_filter_shows_only_users_sitting_on_requests(self):
        Connection.request(self.roaster, self._farmer('blocking'))
        self._farmer('clear')

        emails = self._rows(blocking='1').keys()
        self.assertEqual(set(emails), {'blocking@example.com'})

    def test_default_sort_puts_never_active_first(self):
        recent = self._farmer('recent')
        self._farmer('nothing')
        log_event(InteractionEventType.LOGIN, user=recent)

        emails = list(self._rows().keys())
        self.assertLess(
            emails.index('nothing@example.com'),
            emails.index('recent@example.com'),
        )

    def test_csv_export_returns_a_row_per_user(self):
        Connection.request(self.roaster, self._farmer('ada'))
        self.client.force_login(self.staff)

        resp = self.client.get(reverse('admin_engagement'), {'export': 'csv'})
        self.assertEqual(resp['Content-Type'], 'text/csv')
        lines = resp.content.decode().strip().splitlines()
        self.assertEqual(lines[0].split(',')[0], 'email')
        self.assertEqual(len(lines), 3)  # header + roaster + farmer

    def test_non_staff_redirected(self):
        self.client.force_login(self.roaster)
        resp = self.client.get(reverse('admin_engagement'))
        self.assertEqual(resp.status_code, 302)


class ProfileHistoryTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        self.farmer = Farmer.objects.create(
            user=self.farmer_user, firstname='Fiona', lastname='Farmer',
            farm_name='Old Farm', is_details_filled=True,
        )
        self.language = Language.objects.create(name='English')
        self.client.force_login(self.farmer_user)

    def _edit_profile(self, **overrides):
        data = {
            'main_form': '1',
            'farm_name': 'New Farm',
            'country': 'Kenya',
            'state': '',
            'city': '',
            'farm_size': '',
            'annual_production': '',
            'cultivars': '',
            'source_of_cup_scores': '',
            'quality_report_link': '',
            'processing_description': '',
            'preferred_communication_method': '',
            'member_organization_name': '',
        }
        data.update(overrides)
        return self.client.post(reverse('edit_farmer_details'), data)

    def test_profile_edit_records_old_and_new(self):
        self._edit_profile()

        change = ProfileChange.objects.get()
        self.assertEqual(change.user, self.farmer_user)
        self.assertEqual(change.changed_by, self.farmer_user)
        self.assertEqual(change.source, ProfileChangeSource.PROFILE_EDIT)
        self.assertEqual(change.changes['farm_name']['old'], 'Old Farm')
        self.assertEqual(change.changes['farm_name']['new'], 'New Farm')

    def test_unchanged_save_records_nothing(self):
        self._edit_profile(
            farm_name='Old Farm', country='United States of America',
        )
        self.assertEqual(ProfileChange.objects.count(), 0)

    def test_story_edit_preserves_previous_text(self):
        story = Story.objects.create(
            user=self.farmer_user, farmer=self.farmer,
            language=self.language, story_text='First version',
        )
        self.client.post(reverse('update_story'), {
            'language': self.language.id, 'story_text': 'Second version',
        })

        change = ProfileChange.objects.get(source=ProfileChangeSource.STORY)
        self.assertEqual(change.changes['story_text']['old'], 'First version')
        self.assertEqual(change.changes['story_text']['new'], 'Second version')
        story.refresh_from_db()
        self.assertEqual(story.story_text, 'Second version')

    def test_long_values_are_truncated(self):
        Story.objects.create(
            user=self.farmer_user, farmer=self.farmer,
            language=self.language, story_text='x',
        )
        self.client.post(reverse('update_story'), {
            'language': self.language.id, 'story_text': 'y' * 12000,
        })

        change = ProfileChange.objects.get(source=ProfileChangeSource.STORY)
        stored = change.changes['story_text']['new']
        self.assertTrue(stored.endswith('…[truncated]'))
        self.assertLess(len(stored), 12000)

    def test_recorder_failure_never_breaks_the_save(self):
        with patch(
            'base.profile_history.ProfileChange.objects.create',
            side_effect=RuntimeError('history table is down'),
        ):
            resp = self._edit_profile()

        self.assertEqual(resp.status_code, 302)
        self.farmer.refresh_from_db()
        self.assertEqual(self.farmer.farm_name, 'New Farm')
        self.assertEqual(ProfileChange.objects.count(), 0)

    def test_photo_delete_records_count_drop(self):
        photo = FarmerPhoto.objects.create(user=self.farmer_user, photo='a.jpg')
        FarmerPhoto.objects.create(user=self.farmer_user, photo='b.jpg')

        resp = self.client.post(
            reverse('delete_farmer_photo', args=[photo.id])
        )

        self.assertEqual(resp.status_code, 302)
        change = ProfileChange.objects.get(source=ProfileChangeSource.PHOTO)
        self.assertEqual(change.changes['photos'], {'old': 2, 'new': 1})

    def test_photo_delete_rejects_get(self):
        photo = FarmerPhoto.objects.create(user=self.farmer_user, photo='a.jpg')

        resp = self.client.get(reverse('delete_farmer_photo', args=[photo.id]))

        self.assertEqual(resp.status_code, 405)
        self.assertTrue(FarmerPhoto.objects.filter(id=photo.id).exists())
        self.assertFalse(ProfileChange.objects.exists())

    def test_admin_edit_attributes_the_staff_user(self):
        staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True,
        )
        Story.objects.create(
            user=self.farmer_user, farmer=self.farmer,
            language=self.language, story_text='Farmer wrote this',
        )
        self.client.force_login(staff)
        self.client.post(reverse('admin_farmer_detail', args=[self.farmer_user.id]), {
            'form_type': 'story',
            'language_id': self.language.id,
            'story_text': 'Admin rewrote this',
        })

        change = ProfileChange.objects.get(source=ProfileChangeSource.ADMIN)
        self.assertEqual(change.user, self.farmer_user)
        self.assertEqual(change.changed_by, staff)
        self.assertEqual(change.changes['story_text']['old'], 'Farmer wrote this')


class AdminProfileHistoryPageTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True,
        )
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        ProfileChange.objects.create(
            user=self.farmer_user, changed_by=self.farmer_user,
            source=ProfileChangeSource.PROFILE_EDIT,
            changes={'farm_name': {'old': 'A', 'new': 'B'},
                     'city': {'old': '', 'new': 'Nyeri'}},
        )
        ProfileChange.objects.create(
            user=self.farmer_user, changed_by=self.farmer_user,
            source=ProfileChangeSource.PHOTO,
            changes={'photos': {'old': 1, 'new': 2}},
        )
        ProfileChange.objects.create(
            user=self.roaster_user, changed_by=self.roaster_user,
            source=ProfileChangeSource.PROFILE_EDIT,
            changes={'company_name': {'old': 'X', 'new': 'Y'}},
        )

    def _page(self, **params):
        self.client.force_login(self.staff)
        return self.client.get(reverse('admin_profile_history'), params)

    def test_lists_farmer_changes_only(self):
        rows = self._page().context['changes']
        self.assertEqual(rows.paginator.count, 2)
        self.assertTrue(all(r.user == self.farmer_user for r in rows))

    def test_source_filter(self):
        rows = self._page(source=ProfileChangeSource.PHOTO).context['changes']
        self.assertEqual(rows.paginator.count, 1)
        self.assertEqual(rows[0].changes['photos'], {'old': 1, 'new': 2})

    def test_csv_flattens_one_row_per_field(self):
        self.client.force_login(self.staff)
        resp = self.client.get(
            reverse('admin_profile_history'), {'export': 'csv'}
        )

        self.assertEqual(resp['Content-Type'], 'text/csv')
        lines = resp.content.decode().strip().splitlines()
        # header + photos + farm_name + city (roaster row excluded)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].split(',')[4], 'field')

    def test_non_staff_redirected(self):
        self.client.force_login(self.farmer_user)
        resp = self.client.get(reverse('admin_profile_history'))
        self.assertEqual(resp.status_code, 302)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_FROM='noreply@coffeecircuit.test',
)
class AdminEmailTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(
            email='admin@example.com', username='admin', is_staff=True,
        )
        self.farmer = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        Farmer.objects.create(
            user=self.farmer, firstname='Fiona', lastname='Farmer',
            is_details_filled=True,
        )
        self.roaster = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        Roaster.objects.create(
            user=self.roaster, firstname='Roni', lastname='Roaster',
            company_name='Roni Coffee', is_details_filled=True,
        )

    def test_pages_render_compose_form(self):
        self.client.force_login(self.admin)
        for url in (
            reverse('admin_emails'),
            reverse('admin_farmer_detail', args=[self.farmer.id]),
            reverse('admin_roaster_detail', args=[self.roaster.id]),
        ):
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, 'name="subject"')
                self.assertContains(resp, 'name="body"')

    def test_roaster_detail_renders_without_company_name(self):
        """company_name is nullable, so the avatar initial must tolerate None."""
        user = User.objects.create(
            email='nocompany@example.com', group='roaster', username='nocompany',
        )
        Roaster.objects.create(
            user=user, firstname='No', lastname='Company', is_details_filled=True,
        )
        self.client.force_login(self.admin)
        resp = self.client.get(reverse('admin_roaster_detail', args=[user.id]))
        self.assertEqual(resp.status_code, 200)

    def test_send_from_farmer_detail(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('admin_farmer_detail', args=[self.farmer.id]),
            {'form_type': 'email', 'subject': 'Welcome', 'body': 'Hello there'},
        )
        self.assertEqual(resp.status_code, 302)
        record = AdminEmail.objects.get()
        self.assertEqual(record.recipient, self.farmer)
        self.assertEqual(record.sent_by, self.admin)
        self.assertTrue(record.delivered)
        self.assertEqual(record.error, '')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.farmer.email])
        self.assertEqual(mail.outbox[0].subject, 'Welcome')
        self.assertIn('Hello there', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].reply_to, [self.admin.email])

    def test_send_from_roaster_detail(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('admin_roaster_detail', args=[self.roaster.id]),
            {'form_type': 'email', 'subject': 'Hi', 'body': 'A message'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(AdminEmail.objects.get().recipient, self.roaster)
        self.assertEqual(mail.outbox[0].to, [self.roaster.email])

    def test_send_from_emails_page(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('admin_emails'),
            {
                'recipient': self.farmer.id,
                'subject': 'Broadcast',
                'body': 'Body text',
            },
        )
        self.assertEqual(resp.status_code, 302)
        record = AdminEmail.objects.get()
        self.assertEqual(record.recipient, self.farmer)
        self.assertTrue(record.delivered)
        self.assertEqual(len(mail.outbox), 1)

    def test_blank_fields_send_nothing(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('admin_farmer_detail', args=[self.farmer.id]),
            {'form_type': 'email', 'subject': '   ', 'body': ''},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AdminEmail.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_does_not_touch_profile(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse('admin_farmer_detail', args=[self.farmer.id]),
            {'form_type': 'email', 'subject': '', 'body': ''},
        )
        farmer = Farmer.objects.get(user=self.farmer)
        self.assertEqual(farmer.firstname, 'Fiona')

    def test_requires_staff(self):
        self.client.force_login(self.farmer)
        resp = self.client.post(
            reverse('admin_emails'),
            {'recipient': self.farmer.id, 'subject': 'Hi', 'body': 'Nope'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('admin_login'), resp.url)
        self.assertFalse(AdminEmail.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_staff_recipients_not_selectable(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse('admin_emails'),
            {'recipient': self.admin.id, 'subject': 'Hi', 'body': 'Nope'},
        )
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(AdminEmail.objects.exists())

    def test_send_failure_is_recorded(self):
        self.client.force_login(self.admin)
        with patch(
            'base.notifications.EmailMultiAlternatives.send',
            side_effect=SMTPException('smtp is down'),
        ):
            resp = self.client.post(
                reverse('admin_farmer_detail', args=[self.farmer.id]),
                {'form_type': 'email', 'subject': 'Oops', 'body': 'Body'},
            )
        self.assertEqual(resp.status_code, 302)
        record = AdminEmail.objects.get()
        self.assertFalse(record.delivered)
        self.assertIn('smtp is down', record.error)


class AnalyticsCaptureTests(TestCase):
    def setUp(self):
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser'
        )

    def test_record_event_stores_roles_and_target(self):
        conn = Connection.request(self.roaster_user, self.farmer_user)
        event = record_event(
            self.roaster_user, InteractionEvent.EventType.REQUEST_CONNECTION,
            target=conn, target_user=self.farmer_user,
        )
        self.assertEqual(event.actor, self.roaster_user)
        self.assertEqual(event.target_user, self.farmer_user)
        self.assertEqual(event.target, conn)
        self.assertEqual(event.metadata['actor_role'], 'roaster')
        self.assertEqual(event.metadata['target_role'], 'farmer')

    def test_record_event_infers_target_user_from_target(self):
        conn = Connection.request(self.roaster_user, self.farmer_user)
        event = record_event(
            self.roaster_user, InteractionEvent.EventType.REQUEST_CONNECTION,
            target=conn,
        )
        # Connection exposes ``recipient``; target_user should be inferred.
        self.assertEqual(event.target_user, self.farmer_user)

    def test_record_view_dedupes_same_day(self):
        first = record_view(
            self.roaster_user, InteractionEvent.EventType.VIEW_PROFILE,
            self.farmer_user,
        )
        second = record_view(
            self.roaster_user, InteractionEvent.EventType.VIEW_PROFILE,
            self.farmer_user,
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(
            InteractionEvent.objects.filter(
                event_type=InteractionEvent.EventType.VIEW_PROFILE
            ).count(),
            1,
        )

    def test_record_view_skips_self_view(self):
        event = record_view(
            self.roaster_user, InteractionEvent.EventType.VIEW_PROFILE,
            self.roaster_user,
        )
        self.assertIsNone(event)
        self.assertFalse(InteractionEvent.objects.exists())

    def test_record_event_never_raises(self):
        # An unsaved target_user can't be used as a FK; the write fails but is
        # swallowed so the caller's request is never broken.
        result = record_event(
            self.roaster_user, InteractionEvent.EventType.SEND_MESSAGE,
            target_user=User(email='ghost@example.com', username='ghost'),
        )
        self.assertIsNone(result)


class AnalyticsReportsTests(TestCase):
    def setUp(self):
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser'
        )
        Roaster.objects.create(user=self.roaster_user, company_name='Acme', country='Kenya')

        self.farmer_with = User.objects.create(
            email='fw@example.com', group='farmer', username='fw'
        )
        fw_profile = Farmer.objects.create(
            user=self.farmer_with, firstname='Ada', lastname='Lima',
            farm_name='Sunrise', country='Colombia',
        )
        Story.objects.create(
            user=self.farmer_with, farmer=fw_profile, story_text='A rich story.'
        )

        self.farmer_without = User.objects.create(
            email='fo@example.com', group='farmer', username='fo'
        )
        Farmer.objects.create(
            user=self.farmer_without, firstname='Bob', lastname='Diaz',
            farm_name='Hilltop', country='Brazil',
        )

        # Roaster views the storied farmer, then connects with them (accepted).
        record_view(
            self.roaster_user, InteractionEvent.EventType.VIEW_PROFILE,
            self.farmer_with,
        )
        active = Connection.request(self.roaster_user, self.farmer_with)
        active.accept()
        # A pending, unaccepted request to the other farmer.
        Connection.request(self.roaster_user, self.farmer_without)

        conv = Conversation.objects.create(
            roaster=self.roaster_user, farmer=self.farmer_with
        )
        Message.objects.create(conversation=conv, sender=self.roaster_user, body='hi')

    def test_funnel_stage_counts(self):
        stages = {s['key']: s['count'] for s in analytics_reports.funnel()['stages']}
        self.assertEqual(stages['profile_views'], 1)
        self.assertEqual(stages['messages'], 1)
        self.assertEqual(stages['requests'], 2)
        self.assertEqual(stages['active'], 1)

    def test_story_impact_separates_groups(self):
        report = analytics_reports.story_impact()
        self.assertEqual(report['with_stories']['farmers'], 1)
        self.assertEqual(report['without_stories']['farmers'], 1)
        # The storied farmer got the view and the active connection.
        self.assertEqual(report['with_stories']['profile_views'], 1)
        self.assertEqual(report['with_stories']['active_connections'], 1)
        self.assertEqual(report['without_stories']['active_connections'], 0)

    def test_match_quality_buckets_by_country(self):
        report = analytics_reports.match_quality()
        self.assertEqual(report['active_total'], 1)
        self.assertEqual(dict(report['by_farmer_country']).get('Colombia'), 1)
        self.assertEqual(dict(report['by_roaster_country']).get('Kenya'), 1)
        self.assertEqual(report['initiation'].get('roaster'), 1)

    def test_engagement_volume_totals(self):
        report = analytics_reports.engagement_volume()
        self.assertEqual(report['connection_requests'], 2)
        self.assertEqual(report['active_connections'], 1)
        self.assertEqual(report['messages'], 1)
        self.assertEqual(
            report['events_by_type'].get(InteractionEvent.EventType.VIEW_PROFILE), 1
        )


class AnalyticsDashboardViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create(
            email='staff@example.com', username='staff', is_staff=True
        )
        self.member = User.objects.create(
            email='member@example.com', username='member', group='farmer'
        )

    def test_staff_can_load_dashboard(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('admin_analytics'))
        self.assertEqual(resp.status_code, 200)
        for key in ('funnel', 'story', 'match', 'volume', 'charts'):
            self.assertIn(key, resp.context)

    def test_range_param_is_validated(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse('admin_analytics'), {'days': 'bogus'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['days'], '30')

    def test_non_staff_redirected(self):
        self.client.force_login(self.member)
        resp = self.client.get(reverse('admin_analytics'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('admin_login'), resp.url)


class CountryCodeChoiceTests(TestCase):
    def test_choice_values_are_unique(self):
        # Duplicate values (all +1 countries sharing '+1') were the root cause
        # of the wrong country showing on edit.
        from base.views.country_codes import COUNTRY_CODE_CHOICES
        values = [value for value, _ in COUNTRY_CODE_CHOICES]
        self.assertEqual(len(values), len(set(values)))

    def test_edit_form_round_trips_selected_country(self):
        from base.views.forms import FarmerForm
        user = User.objects.create(
            email='gt@example.com', group='farmer', username='gtuser',
        )
        farmer = Farmer.objects.create(
            user=user, firstname='Gabe', lastname='Guatemala',
            country_code='Guatemala (+502)',
        )
        rendered = str(FarmerForm(instance=farmer)['country_code'])
        self.assertIn('value="Guatemala (+502)" selected', rendered)
        # The bug symptom: it must NOT default to the first +1 country.
        self.assertNotIn('value="Antigua and Barbuda (+1)" selected', rendered)


class CultivarsWidgetTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(
            email='admin@example.com', username='admin', is_staff=True,
        )
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        # Stored the same way as always: comma-separated in one field.
        Farmer.objects.create(
            user=self.farmer_user, firstname='Fiona', lastname='Farmer',
            cultivars='Caturra,Bourbon,Typica',
        )

    def test_admin_detail_renders_cultivars_widget(self):
        self.client.force_login(self.admin)
        resp = self.client.get(
            reverse('admin_farmer_detail', args=[self.farmer_user.id])
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        # The progressive-enhancement wrapper and its script are wired in.
        self.assertIn('cultivars-widget', html)
        self.assertIn('cultivars-original', html)
        self.assertIn('cultivars_input.js', html)
        # The real comma-separated value is still present for the JS to seed from.
        self.assertIn('Caturra,Bourbon,Typica', html)


class OnboardingBadgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        self.farmer = Farmer.objects.create(
            user=self.user, firstname='Fiona', lastname='Farmer',
            is_details_filled=True,
        )

    def test_pending_count_property(self):
        # All seven tasks start incomplete.
        self.assertEqual(self.farmer.pending_orientation_tasks, 7)
        self.farmer.profile_completed = True
        self.farmer.storytelling_workshop = True
        self.farmer.save()
        self.assertEqual(self.farmer.pending_orientation_tasks, 5)

    def test_badge_shows_pending_count(self):
        self.farmer.profile_completed = True
        self.farmer.storytelling_workshop = True
        self.farmer.video_pricing = True
        self.farmer.save()  # 4 remaining
        self.client.force_login(self.user)
        html = self.client.get(reverse('farmer_dashboard')).content.decode()
        self.assertIn('<span class="badge bg-danger">4</span>', html)

    def test_badge_hidden_when_complete(self):
        for field in Farmer.ORIENTATION_TASK_FIELDS:
            setattr(self.farmer, field, True)
        self.farmer.save()
        self.client.force_login(self.user)
        html = self.client.get(reverse('farmer_dashboard')).content.decode()
        self.assertNotIn('badge bg-danger', html)


class ConnectionMessageBadgeTests(TestCase):
    def setUp(self):
        self.farmer_user = User.objects.create(
            email='farmer@example.com', group='farmer', username='farmeruser',
        )
        self.farmer = Farmer.objects.create(
            user=self.farmer_user, firstname='Fiona', lastname='Farmer',
            is_details_filled=True,
        )
        self.roaster_user = User.objects.create(
            email='roaster@example.com', group='roaster', username='roasteruser',
        )
        Roaster.objects.create(
            user=self.roaster_user, firstname='Roni', lastname='Roaster',
            is_details_filled=True,
        )

    def test_pending_received_counts_only_incoming(self):
        Connection.request(self.roaster_user, self.farmer_user)
        # Recipient sees the pending request; the initiator does not.
        self.assertEqual(self.farmer_user.pending_connections_count, 1)
        self.assertEqual(self.roaster_user.pending_connections_count, 0)

    def test_unread_excludes_own_and_read_messages(self):
        conv = Conversation.objects.create(
            roaster=self.roaster_user, farmer=self.farmer_user,
        )
        Message.objects.create(conversation=conv, sender=self.roaster_user, body='hi')
        Message.objects.create(conversation=conv, sender=self.roaster_user, body='yo')
        # The farmer's own message must not count as unread for the farmer.
        Message.objects.create(conversation=conv, sender=self.farmer_user, body='hey')
        self.assertEqual(self.farmer_user.unread_messages_count, 2)
        self.assertEqual(self.roaster_user.unread_messages_count, 1)

    def test_badges_render_in_navbar(self):
        Connection.request(self.roaster_user, self.farmer_user)
        conv = Conversation.objects.create(
            roaster=self.roaster_user, farmer=self.farmer_user,
        )
        Message.objects.create(conversation=conv, sender=self.roaster_user, body='hi')
        self.client.force_login(self.farmer_user)
        html = self.client.get(reverse('farmer_dashboard')).content.decode()
        self.assertIn('CONNECTIONS\n', html)
        # Both badges present with their counts.
        self.assertEqual(html.count('<span class="badge bg-danger">1</span>'), 2)


class PublicResourceAccessTests(TestCase):
    """Resources are linked from the home page and must be public."""

    def setUp(self):
        self.resource = Resource.objects.create(
            title='Washed Process Basics',
            slug='washed-process-basics',
            body='Body text.',
            is_published=True,
        )

    def test_resource_list_anonymous(self):
        response = self.client.get(reverse('resource_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Washed Process Basics')

    def test_resource_detail_anonymous(self):
        response = self.client.get(
            reverse('resource_detail', args=[self.resource.slug])
        )
        self.assertEqual(response.status_code, 200)

    def test_unpublished_resource_hidden(self):
        draft = Resource.objects.create(
            title='Draft', slug='draft', body='x', is_published=False,
        )
        response = self.client.get(
            reverse('resource_detail', args=[draft.slug])
        )
        self.assertEqual(response.status_code, 404)


class LandingPageCallToActionTests(TestCase):
    """Hero and role buttons on the landing page point somewhere."""

    def test_learn_more_anchors_to_about_section(self):
        html = self.client.get(reverse('landing_page')).content.decode()
        self.assertIn('href="#about"', html)
        self.assertIn('id="about"', html)

    def test_role_buttons_link_to_signup_with_group(self):
        html = self.client.get(reverse('landing_page')).content.decode()
        signup_url = reverse('signup')
        self.assertIn(f'{signup_url}?group=farmer', html)
        self.assertIn(f'{signup_url}?group=roaster', html)

    def test_signup_preselects_group_from_query(self):
        response = self.client.get(reverse('signup'), {'group': 'roaster'})
        self.assertEqual(response.context['form'].initial.get('group'), 'roaster')

    def test_signup_ignores_unknown_group(self):
        response = self.client.get(reverse('signup'), {'group': 'bogus'})
        self.assertIsNone(response.context['form'].initial.get('group'))
