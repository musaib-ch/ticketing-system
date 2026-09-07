from django.test import TestCase
from django.urls import reverse

from users.models import Branding, Team, User
from .models import Ticket, TicketLog


class TicketWorkflowTests(TestCase):
    def setUp(self):
        profile = {
            'first_name': 'Test', 'last_name': 'User', 'email': 'test@example.com',
            'employee_number': 'E-001', 'location': 'HQ',
        }
        self.admin = User.objects.create_user(username='admin', role='admin', **profile)
        self.requester = User.objects.create_user(username='employee', role='employee', **profile)
        self.rep = User.objects.create_user(username='rep', role='functional_rep', **profile)
        self.team = Team.objects.create(name='People')
        self.rep.teams.add(self.team)
        self.ticket = Ticket.objects.create(
            title='Leave request', description='Need assistance', requester=self.requester
        )
        self.url = reverse('ticket_detail', args=[self.ticket.pk])

    def test_assignment_is_audited_and_closing_requires_a_reply(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {
            'assign_team': '1', 'team_id': self.team.pk, 'assigned_agent_id': self.rep.pk,
        })
        self.assertRedirects(response, self.url)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.team, self.team)
        self.assertEqual(self.ticket.assigned_agent, self.rep)
        self.assertTrue(TicketLog.objects.filter(ticket=self.ticket, action='Assigned').exists())

        response = self.client.post(self.url, {'body': '', 'status': 'closed'})
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertNotEqual(self.ticket.status, 'closed')

        response = self.client.post(self.url, {'body': 'Issue completed.', 'status': 'closed'})
        self.assertRedirects(response, self.url)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'closed')
        self.assertIsNotNone(self.ticket.closed_at)
        self.assertTrue(TicketLog.objects.filter(ticket=self.ticket, action='Status Changed').exists())

    def test_zero_day_window_disables_reopen(self):
        from django.utils import timezone

        self.ticket.status = 'closed'
        self.ticket.closed_at = timezone.now()
        self.ticket.save()
        branding = Branding.get_settings()
        branding.ticket_reopen_window_days = 0
        branding.save()

        self.client.force_login(self.requester)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Reopen Ticket')
        response = self.client.post(self.url, {'reopen_ticket': '1'})
        self.assertRedirects(response, self.url)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'closed')

    def test_admin_can_select_and_switch_portal_views(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('role_selection'))

        response = self.client.get(reverse('role_selection'))
        self.assertContains(response, 'Where would you like to work?')
        self.assertNotContains(response, 'app-layout')

        response = self.client.post(reverse('role_selection'), {'role': 'employee'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard'))
        response = self.client.get(reverse('queue'))
        self.assertContains(response, 'My Queries')
        self.assertContains(response, 'Switch to Agent View')
        self.assertNotContains(response, 'All Queries')

        response = self.client.post(reverse('switch_role', args=['admin']))
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(self.client.session['active_role'], 'admin')
