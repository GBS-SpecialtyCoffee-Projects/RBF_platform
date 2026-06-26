from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError

from base.models import (
    Connection, Conversation, Farmer, Forum, ForumMeeting, ForumSignup,
    ForumWindow, MeetingRequest, Message, Roaster,
)
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
