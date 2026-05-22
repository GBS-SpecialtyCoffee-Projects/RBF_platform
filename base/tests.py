from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from base.models import Conversation, Farmer, MeetingRequest, Message, Roaster
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
        proposed = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        return self.client.post(
            reverse('connection_farmers'),
            {
                'user_id': self.farmer_user.id,
                'proposed_date': proposed,
                'message': 'Hi',
            },
        )

    def test_roaster_cannot_send_duplicate_active_request(self):
        self.client.login(email='roaster@example.com', password='pw')
        MeetingRequest.objects.create(
            requester=self.roaster_user,
            requestee=self.farmer_user,
            proposed_date=timezone.now() + timedelta(days=1),
            status='pending',
        )
        self._send_connect()
        self.assertEqual(
            MeetingRequest.objects.filter(
                requester=self.roaster_user, requestee=self.farmer_user
            ).count(),
            1,
        )

    def test_roaster_can_send_request_after_previous_rejected(self):
        self.client.login(email='roaster@example.com', password='pw')
        MeetingRequest.objects.create(
            requester=self.roaster_user,
            requestee=self.farmer_user,
            proposed_date=timezone.now() + timedelta(days=1),
            status='rejected',
        )
        self._send_connect()
        self.assertEqual(
            MeetingRequest.objects.filter(
                requester=self.roaster_user,
                requestee=self.farmer_user,
                status='pending',
            ).count(),
            1,
        )

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
        self.meeting_request = MeetingRequest.objects.create(
            requester=self.roaster_user,
            requestee=self.farmer_user,
            proposed_date=timezone.now() + timedelta(days=2),
            status='pending',
        )

    def _url(self, action):
        return reverse('manage_connection_request', args=[self.meeting_request.id, action])

    def test_accept_sets_status_and_redirects_to_referer(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(
            self._url('accept'), HTTP_REFERER='http://testserver/farmer_connections/'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'http://testserver/farmer_connections/')
        self.meeting_request.refresh_from_db()
        self.assertEqual(self.meeting_request.status, 'accepted')

    def test_reject_sets_status(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(self._url('reject'))
        self.assertEqual(response.status_code, 302)
        self.meeting_request.refresh_from_db()
        self.assertEqual(self.meeting_request.status, 'rejected')

    def test_get_not_allowed(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.get(self._url('accept'))
        self.assertEqual(response.status_code, 405)

    def test_invalid_action_rejected(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(
            reverse('manage_connection_request', args=[self.meeting_request.id, 'bogus'])
        )
        self.assertEqual(response.status_code, 400)
        self.meeting_request.refresh_from_db()
        self.assertEqual(self.meeting_request.status, 'pending')

    def test_roaster_blocked_from_endpoint(self):
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.post(self._url('accept'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('roaster_dashboard'))
        self.meeting_request.refresh_from_db()
        self.assertEqual(self.meeting_request.status, 'pending')

    def test_non_requestee_farmer_gets_404(self):
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

    def test_external_referer_falls_back_to_connections(self):
        self.client.login(email='farmer@example.com', password='pw')
        response = self.client.post(
            self._url('accept'), HTTP_REFERER='http://evil.example.com/x'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('farmer_connections'))


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
        return MeetingRequest.objects.create(
            requester=self.roaster_user,
            requestee=self.farmer_user,
            status='accepted',
        )

    def test_thread_forbidden_without_accepted_connection(self):
        self.client.login(email='roaster@example.com', password='pw')
        response = self.client.get(reverse('chat_thread', args=[self.farmer_user.id]))
        self.assertEqual(response.status_code, 403)

    def test_thread_forbidden_with_only_pending_connection(self):
        MeetingRequest.objects.create(
            requester=self.roaster_user, requestee=self.farmer_user, status='pending',
        )
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
