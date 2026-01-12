from datetime import datetime, timedelta, time
from django.utils import timezone
from django.db.models import Count, Avg, Q
from collections import defaultdict
import calendar

from website.models import (
    Appointment,
    DependentAppointment,
    DoctorAvailability,
    CustomDoctorAvailability,
    PatientInfo,
    DependentPatient,
    DoctorInfo,
    MedicalRecord
)


class AppointmentRecommender:
    def __init__(self, patient, doctor, patient_type='self'):
        self.patient = patient
        self.doctor = doctor
        self.patient_type = patient_type
        self.today = timezone.now().date()
        self.now = timezone.now()
    
    def get_recommendations(self):
        recommendations = {
            'recommended_times': [],
            'urgency_score': 0,
            'reasoning': [],
            'avoid_times': [],
            'next_7_days': []
        }
        
        # Calculate urgency score
        recommendations['urgency_score'] = self._calculate_urgency()
        
        # Get patient's preferred times based on history
        preferred_times = self._analyze_appointment_history()
        
        # Get doctor's busiest times to avoid
        busy_times = self._analyze_doctor_schedule()
        
        # Analyze medical history for timing recommendations
        medical_insights = self._analyze_medical_history()
        
        # Get available slots for next 7 days
        available_slots = self._get_available_slots(days=7)
        
        # Score and rank available slots
        scored_slots = self._score_slots(
            available_slots,
            preferred_times,
            busy_times,
            medical_insights
        )
        
        # Build recommendations
        recommendations['recommended_times'] = scored_slots[:5]  # Top 5
        recommendations['avoid_times'] = busy_times
        recommendations['next_7_days'] = available_slots
        
        # Generate reasoning
        recommendations['reasoning'] = self._generate_reasoning(
            recommendations['urgency_score'],
            preferred_times,
            medical_insights
        )
        
        return recommendations
    
    def _calculate_urgency(self):
        score = 0
        
        # Check last visit date
        last_visit = self._get_last_visit_date()
        if last_visit:
            days_since = (self.today - last_visit).days
            if days_since > 365:
                score += 40  # Haven't visited in over a year
            elif days_since > 180:
                score += 25  # Haven't visited in 6+ months
            elif days_since > 90:
                score += 15  # Haven't visited in 3+ months
        else:
            score += 30  # New patient
        
        # Check medical history
        if self.patient_type == 'self':
            recent_records = MedicalRecord.objects.filter(
                patient=self.patient,
                created_at__gte=timezone.now() - timedelta(days=90)
            )
        else:
            recent_records = MedicalRecord.objects.filter(
                dependent_patient=self.patient,
                created_at__gte=timezone.now() - timedelta(days=90)
            )
        
        # Multiple recent visits indicate ongoing treatment
        if recent_records.count() >= 3:
            score += 25
        elif recent_records.count() >= 2:
            score += 15
        
        # Check for chronic conditions (allergies, medications)
        if hasattr(self.patient, 'allergies') and self.patient.allergies.count() > 0:
            score += 10
        
        if hasattr(self.patient, 'medications') and self.patient.medications.count() > 2:
            score += 15
        
        # Check pending appointments
        if self.patient_type == 'self':
            pending = Appointment.objects.filter(
                patient=self.patient.user,
                status='pending',
                start_time__gte=self.now
            ).exists()
        else:
            pending = DependentAppointment.objects.filter(
                dependent_patient=self.patient,
                status='pending',
                start_time__gte=self.now
            ).exists()
        
        if pending:
            score = max(0, score - 30)  # Reduce urgency if already has pending
        
        return min(100, score)
    
    def _analyze_appointment_history(self):
        """Analyze patient's past appointments to find preferred times"""
        preferred = {
            'days': defaultdict(int),  # Monday=0, Sunday=6
            'times': defaultdict(int),  # Morning, Afternoon, Evening
            'frequency': 0
        }
        
        # Get past appointments
        if self.patient_type == 'self':
            past_appointments = Appointment.objects.filter(
                patient=self.patient.user,
                status__in=['completed', 'approved'],
                start_time__lt=self.now
            )
        else:
            past_appointments = DependentAppointment.objects.filter(
                dependent_patient=self.patient,
                status__in=['completed', 'approved'],
                start_time__lt=self.now
            )
        
        
        
        preferred['frequency'] = past_appointments.count()
        
        for appt in past_appointments:
            # Track preferred days
            weekday = appt.start_time.weekday()
            preferred['days'][weekday] += 1
            
            # Track preferred times
            hour = appt.start_time.hour
            if hour < 12:
                preferred['times']['morning'] += 1
            elif hour < 17:
                preferred['times']['afternoon'] += 1
            else:
                preferred['times']['evening'] += 1
        
        return preferred
    
    def _analyze_doctor_schedule(self):
        """Identify doctor's busiest times"""
        busy_times = []
        
        # Check approved appointments in next 14 days
        upcoming = Appointment.objects.filter(
            doctor=self.doctor,
            status='approved',
            start_time__gte=self.now,
            start_time__lte=self.now + timedelta(days=14)
        ).values('start_time__date', 'start_time__hour').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Mark times with 3+ appointments as busy
        for item in upcoming:
            if item['count'] >= 3:
                busy_times.append({
                    'date': item['start_time__date'],
                    'hour': item['start_time__hour']
                })
        
        return busy_times
    
    def _analyze_medical_history(self):
        """Extract timing insights from medical history"""
        insights = {
            'follow_up_needed': False,
            'recommended_interval': None,
            'condition_notes': []
        }
        
        # Get recent medical records
        if self.patient_type == 'self':
            recent_records = MedicalRecord.objects.filter(
                patient=self.patient,
                created_at__gte=timezone.now() - timedelta(days=180)
            ).order_by('-created_at')[:5]
        else:
            recent_records = MedicalRecord.objects.filter(
                dependent_patient=self.patient,
                created_at__gte=timezone.now() - timedelta(days=180)
            ).order_by('-created_at')[:5]
        
        # Check for follow-up patterns
        if recent_records.count() >= 2:
            dates = [r.created_at.date() for r in recent_records]
            if len(dates) >= 2:
                intervals = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    insights['recommended_interval'] = int(avg_interval)
                    
                    # Check if follow-up is due
                    last_visit = dates[0]
                    days_since = (self.today - last_visit).days
                    if days_since >= avg_interval * 0.8:
                        insights['follow_up_needed'] = True
        
        # Check medications for chronic care
        if hasattr(self.patient, 'medications'):
            med_count = self.patient.medications.count()
            if med_count > 2:
                insights['condition_notes'].append('Multiple medications - regular monitoring recommended')
        
        return insights
    
    def _get_available_slots(self, days=7):
        """Get all available time slots for next N days"""
        slots = []
        
        for day_offset in range(days):
            check_date = self.today + timedelta(days=day_offset)
            
            # Skip past dates
            if check_date < self.today:
                continue
            
            # For today, skip if past noon
            if check_date == self.today and self.now.hour >= 12:
                continue
            
            weekday = check_date.weekday()
            
            # Check for custom availability
            custom_avail = CustomDoctorAvailability.objects.filter(
                doctor=self.doctor,
                date=check_date
            ).first()
            
            if custom_avail:
                availabilities = [custom_avail]
            else:
                availabilities = DoctorAvailability.objects.filter(
                    doctor=self.doctor,
                    weekday=weekday
                )
            
            if not availabilities:
                continue
            
            # Get booked times for this day
            booked_times = self._get_booked_times(check_date)
            
            # Generate 30-minute slots
            for avail in availabilities:
                start_dt = datetime.combine(check_date, avail.start_time)
                end_dt = datetime.combine(check_date, avail.end_time)
                
                # For today, skip past times
                if check_date == self.today:
                    min_time = (self.now + timedelta(hours=1)).time()
                    if avail.start_time < min_time:
                        start_dt = datetime.combine(check_date, min_time)
                
                current = start_dt
                while current + timedelta(minutes=30) <= end_dt:
                    slot_end = current + timedelta(minutes=30)
                    
                    # Check if slot is booked
                    is_booked = any(
                        current.time() >= b_start and current.time() < b_end
                        for b_start, b_end in booked_times
                    )
                    
                    if not is_booked:
                        slots.append({
                            'datetime': current,
                            'date': check_date,
                            'time': current.time(),
                            'weekday': weekday,
                            'hour': current.hour
                        })
                    
                    current = slot_end
        
        return slots
    
    def _get_booked_times(self, date):
        """Get all booked time ranges for a date"""
        booked = []
        
        # Self appointments
        self_appts = Appointment.objects.filter(
            doctor=self.doctor,
            start_time__date=date,
            status='approved'
        )
        
        for appt in self_appts:
            booked.append((appt.start_time.time(), appt.end_time.time()))
        
        # Dependent appointments
        dep_appts = DependentAppointment.objects.filter(
            doctor=self.doctor,
            start_time__date=date,
            status='approved'
        )
        
        for appt in dep_appts:
            booked.append((appt.start_time.time(), appt.end_time.time()))
        
        return booked
    
    def _score_slots(self, slots, preferred_times, busy_times, medical_insights):
        """Score each slot based on patient preferences and medical needs"""
        scored_slots = []
        
        for slot in slots:
            score = 50  # Base score
            reasons = []
            
            # Prefer patient's historical preferred days
            if preferred_times['days']:
                most_preferred_day = max(preferred_times['days'], key=preferred_times['days'].get)
                if slot['weekday'] == most_preferred_day:
                    score += 15
                    reasons.append("Your preferred day")
            
            # Prefer patient's historical preferred times
            hour = slot['hour']
            if hour < 12 and preferred_times['times'].get('morning', 0) > 0:
                score += 10
                reasons.append("Your usual morning time")
            elif 12 <= hour < 17 and preferred_times['times'].get('afternoon', 0) > 0:
                score += 10
                reasons.append("Your usual afternoon time")
            elif hour >= 17 and preferred_times['times'].get('evening', 0) > 0:
                score += 10
                reasons.append("Your usual evening time")
            
            # Avoid busy times
            is_busy = any(
                slot['date'] == bt['date'] and slot['hour'] == bt['hour']
                for bt in busy_times
            )
            if is_busy:
                score -= 15
                reasons.append("Doctor's busy time")
            
            # Prefer sooner if follow-up needed
            if medical_insights.get('follow_up_needed'):
                days_away = (slot['date'] - self.today).days
                if days_away <= 3:
                    score += 20
                    reasons.append("Follow-up recommended soon")
            
            # Prefer mid-week for routine visits
            if slot['weekday'] in [1, 2, 3]:  # Tue-Thu
                score += 5
            
            # Prefer morning slots slightly (generally better for medical visits)
            if 8 <= hour < 11:
                score += 5
            
            scored_slots.append({
                'slot': slot,
                'score': score,
                'reasons': reasons
            })
        
        # Sort by score descending
        scored_slots.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_slots
    
    def _generate_reasoning(self, urgency_score, preferred_times, medical_insights):
        """Generate human-readable reasoning for recommendations"""
        reasons = []
        
        # Urgency explanation
        if urgency_score >= 75:
            reasons.append("High priority: You should schedule an appointment soon.")
        elif urgency_score >= 50:
            reasons.append("Moderate priority: Consider scheduling in the next few weeks.")
        elif urgency_score >= 25:
            reasons.append("Low priority: Schedule when convenient.")
        else:
            reasons.append("You have a recent pending appointment.")
        
        # History-based recommendations
        if preferred_times['frequency'] > 0:
            most_common_day = max(preferred_times['days'], key=preferred_times['days'].get) if preferred_times['days'] else None
            if most_common_day is not None:
                day_name = calendar.day_name[most_common_day]
                reasons.append(f"Based on your history, you typically prefer {day_name}s.")
            
            most_common_time = max(preferred_times['times'], key=preferred_times['times'].get) if preferred_times['times'] else None
            if most_common_time:
                reasons.append(f"You usually book {most_common_time} appointments.")
        
        # Medical insights
        if medical_insights.get('follow_up_needed'):
            reasons.append("Follow-up visit may be due based on your treatment schedule.")
        
        if medical_insights.get('recommended_interval'):
            interval = medical_insights['recommended_interval']
            reasons.append(f"Your typical visit interval is every {interval} days.")
        
        for note in medical_insights.get('condition_notes', []):
            reasons.append(note)
        
        return reasons
    
    def _get_last_visit_date(self):
        """Get the date of the patient's last completed appointment"""
        if self.patient_type == 'self':
            last_appt = Appointment.objects.filter(
                patient=self.patient.user,
                status='completed'
            ).order_by('-start_time').first()
        else:
            last_appt = DependentAppointment.objects.filter(
                dependent_patient=self.patient,
                status='completed'
            ).order_by('-start_time').first()
        
        if last_appt:
            return last_appt.start_time.date()
        return None


def get_appointment_recommendations(patient, doctor, patient_type='self'):
    """
    Convenience function to get appointment recommendations
    
    Args:
        patient: PatientInfo or DependentPatient instance
        doctor: DoctorInfo instance
        patient_type: 'self' or 'dependent'
    
    Returns:
        dict with recommendations
    """
    recommender = AppointmentRecommender(patient, doctor, patient_type)
    return recommender.get_recommendations()