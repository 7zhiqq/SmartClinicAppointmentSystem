import re
from django.core.exceptions import ValidationError

def validate_ph_phone_number(value):
    """
    Validates Philippine phone numbers.
    Accepts formats:
    - 09xxxxxxxxx (11 digits)
    - +639xxxxxxxxx (13 digits with +63)
    - 639xxxxxxxxx (12 digits)
    """
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', value)
    
    # Check if it starts with +63 or 63 or 09
    if cleaned.startswith('+63'):
        cleaned = '0' + cleaned[3:]  # Convert +639xxx to 09xxx
    elif cleaned.startswith('63'):
        cleaned = '0' + cleaned[2:]  # Convert 639xxx to 09xxx
    
    # Validate the format
    if not re.match(r'^09\d{9}$', cleaned):
        raise ValidationError(
            'Please enter a valid Philippine phone number. '
            'Format: 09xxxxxxxxx, +639xxxxxxxxx, or 639xxxxxxxxx'
        )

def normalize_ph_phone_number(value):
    """
    Normalizes Philippine phone number to standard format: 09xxxxxxxxx
    """
    cleaned = re.sub(r'[^\d+]', '', value)
    
    if cleaned.startswith('+63'):
        cleaned = '0' + cleaned[3:]
    elif cleaned.startswith('63'):
        cleaned = '0' + cleaned[2:]
    
    return cleaned if re.match(r'^09\d{9}$', cleaned) else None