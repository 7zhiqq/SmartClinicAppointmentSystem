from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from website.models import Appointment, DependentAppointment, MedicalRecord

class Command(BaseCommand):
    help = 'Archive old completed appointments and medical records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Number of days old (default: 365)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be archived without making changes'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Archive old completed appointments
        old_appointments = Appointment.objects.filter(
            status='completed',
            start_time__lt=cutoff_date,
            is_archived=False
        )
        
        old_dependent_appointments = DependentAppointment.objects.filter(
            status='completed',
            start_time__lt=cutoff_date,
            is_archived=False
        )
        
        # Archive old rejected appointments
        rejected_appointments = Appointment.objects.filter(
            status='rejected',
            start_time__lt=cutoff_date,
            is_archived=False
        )
        
        rejected_dependent = DependentAppointment.objects.filter(
            status='rejected',
            start_time__lt=cutoff_date,
            is_archived=False
        )
        
        # Archive old medical records (older than 2 years)
        old_records = MedicalRecord.objects.filter(
            created_at__lt=cutoff_date,
            is_archived=False
        )
        
        total_count = (
            old_appointments.count() +
            old_dependent_appointments.count() +
            rejected_appointments.count() +
            rejected_dependent.count() +
            old_records.count()
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would archive {total_count} records'
                )
            )
            self.stdout.write(f'  - {old_appointments.count()} completed appointments')
            self.stdout.write(f'  - {old_dependent_appointments.count()} completed dependent appointments')
            self.stdout.write(f'  - {rejected_appointments.count()} rejected appointments')
            self.stdout.write(f'  - {rejected_dependent.count()} rejected dependent appointments')
            self.stdout.write(f'  - {old_records.count()} old medical records')
            return
        
        # Archive completed appointments
        for appointment in old_appointments:
            appointment.archive()
        
        for appointment in old_dependent_appointments:
            appointment.archive()
        
        # Archive rejected appointments
        for appointment in rejected_appointments:
            appointment.archive()
        
        for appointment in rejected_dependent:
            appointment.archive()
        
        # Archive old medical records
        for record in old_records:
            record.archive()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully archived {total_count} records'
            )
        )
