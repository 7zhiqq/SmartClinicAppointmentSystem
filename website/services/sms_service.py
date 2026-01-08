"""
SMS Service using Vonage (Nexmo) - FREE and Easy Setup
Get your API credentials from: https://dashboard.nexmo.com/
"""
import requests
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('website')


class VonageSMS:
    """Vonage (Nexmo) SMS Gateway - Simple and Free"""
    
    API_URL = "https://rest.nexmo.com/sms/json"
    
    @classmethod
    def send_sms(cls, phone_number, message):
        """
        Send SMS via Vonage
        
        Args:
            phone_number (str): PH phone number (09xxxxxxxxx or +639xxxxxxxxx)
            message (str): SMS message content (max 160 chars per SMS)
            
        Returns:
            tuple: (success: bool, response: dict)
        """
        if not getattr(settings, 'SMS_ENABLED', False):
            logger.info(f"SMS disabled. Would send to {phone_number}: {message}")
            return True, {"status": "disabled", "message": message}
        
        api_key = getattr(settings, 'VONAGE_API_KEY', '')
        api_secret = getattr(settings, 'VONAGE_API_SECRET', '')
        from_number = getattr(settings, 'VONAGE_FROM_NUMBER', 'WestPoint')
        
        if not api_key or not api_secret:
            logger.error("Vonage API credentials not configured")
            return False, {"error": "API credentials missing"}
        
        # Normalize phone number to international format
        phone = cls._normalize_phone(phone_number)
        if not phone:
            logger.error(f"Invalid phone number: {phone_number}")
            return False, {"error": "Invalid phone number"}
        
        # Prepare payload
        payload = {
            'api_key': api_key,
            'api_secret': api_secret,
            'to': phone,
            'from': from_number,
            'text': message
        }
        
        try:
            response = requests.post(cls.API_URL, data=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            # Check if message was sent successfully
            if result.get('messages'):
                msg = result['messages'][0]
                if msg.get('status') == '0':
                    logger.info(f"SMS sent successfully to {phone}")
                    return True, {
                        'status': 'sent',
                        'message_id': msg.get('message-id'),
                        'message': message,
                        'to': phone
                    }
                else:
                    error_text = msg.get('error-text', 'Unknown error')
                    logger.error(f"SMS failed: {error_text}")
                    return False, {
                        'error': error_text,
                        'status': msg.get('status')
                    }
            
            logger.error(f"Unexpected response: {result}")
            return False, {"error": "Unexpected response format"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send SMS to {phone}: {str(e)}")
            return False, {"error": str(e)}
    
    @staticmethod
    def _normalize_phone(phone):
        """
        Normalize phone number to international format for Vonage
        Vonage requires: 639xxxxxxxxx (no + symbol)
        
        Args:
            phone (str): Phone number in any format
            
        Returns:
            str: Normalized phone number or None if invalid
        """
        if not phone:
            return None
        
        # Remove all non-digit characters
        phone = ''.join(filter(str.isdigit, str(phone)))
        
        # Convert to 639xxxxxxxxx format
        if phone.startswith('09') and len(phone) == 11:
            # 09xxxxxxxxx → 639xxxxxxxxx
            phone = '63' + phone[1:]
        elif phone.startswith('639') and len(phone) == 12:
            # Already correct format
            pass
        elif phone.startswith('9') and len(phone) == 10:
            # 9xxxxxxxxx → 639xxxxxxxxx
            phone = '63' + phone
        else:
            return None
        
        # Validate final format
        if not (phone.startswith('639') and len(phone) == 12):
            return None
        
        return phone
    
    @classmethod
    def check_balance(cls):
        """
        Check remaining SMS balance (optional)
        Returns remaining balance in EUR
        """
        api_key = getattr(settings, 'VONAGE_API_KEY', '')
        api_secret = getattr(settings, 'VONAGE_API_SECRET', '')
        
        if not api_key or not api_secret:
            return None
        
        try:
            url = f"https://rest.nexmo.com/account/get-balance?api_key={api_key}&api_secret={api_secret}"
            response = requests.get(url, timeout=10)
            result = response.json()
            
            balance = result.get('value', 0)
            logger.info(f"Vonage balance: €{balance}")
            return float(balance)
            
        except Exception as e:
            logger.error(f"Failed to check balance: {str(e)}")
            return None


class AppointmentSMS:
    """SMS notification templates for appointments"""
    
    @classmethod
    def send_booking_confirmation(cls, appointment, phone_number):
        """Send SMS when appointment is booked"""
        patient_name = cls._get_patient_name(appointment)
        doctor_name = appointment.doctor.user.get_full_name()
        date = appointment.start_time.strftime('%b %d, %Y')
        time = appointment.start_time.strftime('%I:%M %p')
        
        message = (
            f"Hi {patient_name}! Your appointment with Dr. {doctor_name} "
            f"is PENDING approval.\n"
            f"Date: {date}\n"
            f"Time: {time}\n"
            f"We'll notify you once confirmed.\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_approval_notification(cls, appointment, phone_number):
        """Send SMS when appointment is approved"""
        patient_name = cls._get_patient_name(appointment)
        doctor_name = appointment.doctor.user.get_full_name()
        date = appointment.start_time.strftime('%b %d, %Y')
        time = appointment.start_time.strftime('%I:%M %p')
        
        message = (
            f"CONFIRMED! {patient_name}, your appointment with Dr. {doctor_name} "
            f"is approved.\n"
            f"Date: {date}\n"
            f"Time: {time}\n"
            f"Please arrive 15 mins early.\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_rejection_notification(cls, appointment, phone_number):
        """Send SMS when appointment is rejected"""
        patient_name = cls._get_patient_name(appointment)
        
        message = (
            f"Sorry {patient_name}, your appointment request could not be confirmed. "
            f"Please call us to reschedule or book another time slot.\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_reschedule_notification(cls, appointment, phone_number, old_date, old_time):
        """Send SMS when appointment is rescheduled"""
        patient_name = cls._get_patient_name(appointment)
        doctor_name = appointment.doctor.user.get_full_name()
        new_date = appointment.start_time.strftime('%b %d, %Y')
        new_time = appointment.start_time.strftime('%I:%M %p')
        
        message = (
            f"RESCHEDULED! {patient_name}, your appointment with Dr. {doctor_name} "
            f"has been moved.\n"
            f"NEW: {new_date} at {new_time}\n"
            f"(Was: {old_date} at {old_time})\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_cancellation_notification(cls, appointment, phone_number):
        """Send SMS when appointment is cancelled"""
        patient_name = cls._get_patient_name(appointment)
        
        message = (
            f"CANCELLED! {patient_name}, your appointment has been cancelled. "
            f"Please visit our website or call to rebook.\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_reminder_2days(cls, appointment, phone_number):
        """Send 2-day reminder"""
        patient_name = cls._get_patient_name(appointment)
        doctor_name = appointment.doctor.user.get_full_name()
        date = appointment.start_time.strftime('%b %d, %Y')
        time = appointment.start_time.strftime('%I:%M %p')
        
        message = (
            f"REMINDER: {patient_name}, you have an appointment with Dr. {doctor_name} "
            f"in 2 DAYS.\n"
            f"Date: {date}\n"
            f"Time: {time}\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_reminder_1day(cls, appointment, phone_number):
        """Send 1-day reminder"""
        patient_name = cls._get_patient_name(appointment)
        doctor_name = appointment.doctor.user.get_full_name()
        date = appointment.start_time.strftime('%b %d, %Y')
        time = appointment.start_time.strftime('%I:%M %p')
        
        message = (
            f"REMINDER: {patient_name}, your appointment with Dr. {doctor_name} "
            f"is TOMORROW!\n"
            f"Date: {date}\n"
            f"Time: {time}\n"
            f"See you soon!\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @classmethod
    def send_reminder_today(cls, appointment, phone_number):
        """Send same-day reminder"""
        patient_name = cls._get_patient_name(appointment)
        doctor_name = appointment.doctor.user.get_full_name()
        time = appointment.start_time.strftime('%I:%M %p')
        
        message = (
            f"TODAY! {patient_name}, your appointment with Dr. {doctor_name} "
            f"is at {time}.\n"
            f"Please arrive 15 mins early.\n"
            f"- WestPoint Clinic"
        )
        
        return VonageSMS.send_sms(phone_number, message)
    
    @staticmethod
    def _get_patient_name(appointment):
        """Get patient name from appointment"""
        if hasattr(appointment, 'patient'):
            return appointment.patient.first_name
        elif hasattr(appointment, 'dependent_patient'):
            return appointment.dependent_patient.first_name
        return "Patient"
    
    @staticmethod
    def _get_patient_phone(appointment):
        """Get patient phone number"""
        try:
            if hasattr(appointment, 'patient'):
                phone_obj = appointment.patient.phone
                return phone_obj.number if hasattr(phone_obj, 'number') else None
            elif hasattr(appointment, 'dependent_patient'):
                dependent = appointment.dependent_patient
                if dependent.phone:
                    return dependent.phone
                guardian_phone = dependent.guardian.phone
                return guardian_phone.number if hasattr(guardian_phone, 'number') else None
        except Exception as e:
            logger.error(f"Error getting phone for appointment {appointment.id}: {str(e)}")
            return None