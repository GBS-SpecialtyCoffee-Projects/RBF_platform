from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from base.models import Farmer, MeetingRequest, Roaster
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
