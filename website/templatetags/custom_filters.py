from django import template

register = template.Library()

@register.filter
def gender_full(value):
    if not value:
        return "N/A"
    value = value.lower()
    if value == "f":
        return "Female"
    elif value == "m":
        return "Male"
    return value.capitalize()
