"""
Management command to send appointment reminders
Run this via cron job or task scheduler

Usage:
    python manage.py send_appointment_reminders
    python manage.py send_appointment_reminders --type=today
    python manage.py send_appointment_reminders --type=1day
    python manage.py send_appointment_reminders --type=2days
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from website.models import Appointment, DependentAppointment, SMSNotification
from website.services.sms_service import AppointmentSMS
import logging

logger = logging.getLogger('website')


class Command(BaseCommand):
    help = 'Send appointment reminders via SMS'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            choices=['all', 'today', '1day', '2days'],
            help='Type of reminder to send (default: all)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )
    
    def handle(self, *args, **options):
        reminder_type = options['type']
        dry_run = options['dry_run']
        
        now = timezone.now()
        today = now.date()
        
        total_sent = 0
        total_failed = 0
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No SMS will be sent'))
        
        # Send today's reminders
        if reminder_type in ['all', 'today']:
            sent, failed = self._send_today_reminders(today, dry_run)
            total_sent += sent
            total_failed += failed
        
        # Send 1-day reminders
        if reminder_type in ['all', '1day']:
            sent, failed = self._send_1day_reminders(today, dry_run)
            total_sent += sent
            total_failed += failed
        
        # Send 2-day reminders
        if reminder_type in ['all', '2days']:
            sent, failed = self._send_2days_reminders(today, dry_run)
            total_sent += sent
            total_failed += failed
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {total_sent} sent, {total_failed} failed'
            )
        )
    
    def _send_today_reminders(self, today, dry_run):
        """Send reminders for appointments happening today"""
        self.stdout.write('\n=== TODAY\'S REMINDERS ===')
        
        sent = 0
        failed = 0
        
        # Get approved appointments for today
        appointments = Appointment.objects.filter(
            start_time__date=today,
            status='approved'
        ).select_related('patient', 'doctor')
        
        dependent_appointments = DependentAppointment.objects.filter(
            start_time__date=today,
            status='approved'
        ).select_related('dependent_patient', 'doctor')
        
        # Process self appointments
        for appt in appointments:
            if self._already_sent(appt, 'reminder_today'):
                continue
            
            phone = self._get_phone(appt)
            if not phone:
                self.stdout.write(
                    self.style.ERROR(f'No phone for appointment {appt.id}')
                )
                failed += 1
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would send TODAY reminder to {phone} for appointment {appt.id}'
                    )
                )
                sent += 1
            else:
                success = self._send_and_log(appt, phone, 'reminder_today', None)
                if success:
                    sent += 1
                else:
                    failed += 1
        
        # Process dependent appointments
        for appt in dependent_appointments:
            if self._already_sent(None, 'reminder_today', appt):
                continue
            
            phone = self._get_phone(appt)
            if not phone:
                self.stdout.write(
                    self.style.ERROR(f'No phone for dependent appointment {appt.id}')
                )
                failed += 1
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would send TODAY reminder to {phone} for dependent appointment {appt.id}'
                    )
                )
                sent += 1
            else:
                success = self._send_and_log(None, phone, 'reminder_today', appt)
                if success:
                    sent += 1
                else:
                    failed += 1
        
        self.stdout.write(f'Today reminders: {sent} sent, {failed} failed')
        return sent, failed
    
    def _send_1day_reminders(self, today, dry_run):
        """Send reminders for appointments happening tomorrow"""
        self.stdout.write('\n=== 1-DAY REMINDERS ===')
        
        sent = 0
        failed = 0
        tomorrow = today + timedelta(days=1)
        
        # Get approved appointments for tomorrow
        appointments = Appointment.objects.filter(
            start_time__date=tomorrow,
            status='approved'
        ).select_related('patient', 'doctor')
        
        dependent_appointments = DependentAppointment.objects.filter(
            start_time__date=tomorrow,
            status='approved'
        ).select_related('dependent_patient', 'doctor')
        
        # Process self appointments
        for appt in appointments:
            if self._already_sent(appt, 'reminder_1day'):
                continue
            
            phone = self._get_phone(appt)
            if not phone:
                failed += 1
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would send 1-DAY reminder to {phone} for appointment {appt.id}'
                    )
                )
                sent += 1
            else:
                success = self._send_and_log(appt, phone, 'reminder_1day', None)
                if success:
                    sent += 1
                else:
                    failed += 1
        
        # Process dependent appointments
        for appt in dependent_appointments:
            if self._already_sent(None, 'reminder_1day', appt):
                continue
            
            phone = self._get_phone(appt)
            if not phone:
                failed += 1
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would send 1-DAY reminder to {phone} for dependent appointment {appt.id}'
                    )
                )
                sent += 1
            else:
                success = self._send_and_log(None, phone, 'reminder_1day', appt)
                if success:
                    sent += 1
                else:
                    failed += 1
        
        self.stdout.write(f'1-day reminders: {sent} sent, {failed} failed')
        return sent, failed
    
    def _send_2days_reminders(self, today, dry_run):
        """Send reminders for appointments happening in 2 days"""
        self.stdout.write('\n=== 2-DAY REMINDERS ===')
        
        sent = 0
        failed = 0
        two_days = today + timedelta(days=2)
        
        # Get approved appointments for 2 days from now
        appointments = Appointment.objects.filter(
            start_time__date=two_days,
            status='approved'
        ).select_related('patient', 'doctor')
        
        dependent_appointments = DependentAppointment.objects.filter(
            start_time__date=two_days,
            status='approved'
        ).select_related('dependent_patient', 'doctor')
        
        # Process self appointments
        for appt in appointments:
            if self._already_sent(appt, 'reminder_2days'):
                continue
            
            phone = self._get_phone(appt)
            if not phone:
                failed += 1
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would send 2-DAY reminder to {phone} for appointment {appt.id}'
                    )
                )
                sent += 1
            else:
                success = self._send_and_log(appt, phone, 'reminder_2days', None)
                if success:
                    sent += 1
                else:
                    failed += 1
        
        # Process dependent appointments
        for appt in dependent_appointments:
            if self._already_sent(None, 'reminder_2days', appt):
                continue
            
            phone = self._get_phone(appt)
            if not phone:
                failed += 1
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'Would send 2-DAY reminder to {phone} for dependent appointment {appt.id}'
                    )
                )
                sent += 1
            else:
                success = self._send_and_log(None, phone, 'reminder_2days', appt)
                if success:
                    sent += 1
                else:
                    failed += 1
        
        self.stdout.write(f'2-day reminders: {sent} sent, {failed} failed')
        return sent, failed
    
    def _already_sent(self, appointment=None, notification_type='', dependent_appointment=None):
        """Check if reminder was already sent"""
        if appointment:
            return SMSNotification.objects.filter(
                appointment=appointment,
                notification_type=notification_type,
                status='sent'
            ).exists()
        elif dependent_appointment:
            return SMSNotification.objects.filter(
                dependent_appointment=dependent_appointment,
                notification_type=notification_type,
                status='sent'
            ).exists()
        return False
    
    def _get_phone(self, appointment):
        """Get phone number from appointment"""
        return AppointmentSMS._get_patient_phone(appointment)
    
    def _send_and_log(self, appointment, phone, notification_type, dependent_appointment):
        """Send SMS and log to database"""
        # Send SMS
        if notification_type == 'reminder_today':
            success, response = AppointmentSMS.send_reminder_today(
                appointment or dependent_appointment, phone
            )
        elif notification_type == 'reminder_1day':
            success, response = AppointmentSMS.send_reminder_1day(
                appointment or dependent_appointment, phone
            )
        elif notification_type == 'reminder_2days':
            success, response = AppointmentSMS.send_reminder_2days(
                appointment or dependent_appointment, phone
            )
        else:
            return False
        
        # Create notification record
        notification = SMSNotification(
            appointment=appointment,
            dependent_appointment=dependent_appointment,
            notification_type=notification_type,
            phone_number=phone,
            message=response.get('message', ''),
            status='sent' if success else 'failed',
            sent_at=timezone.now() if success else None,
            error_message=response.get('error') if not success else None,
            semaphore_response=response
        )
        notification.save()
        
        appt_id = appointment.id if appointment else dependent_appointment.id
        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sent {notification_type} to {phone} for appointment {appt_id}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to send {notification_type} to {phone}: {response.get("error")}'
                )
            )
        
        return success