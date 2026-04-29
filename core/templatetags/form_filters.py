from django import template

register = template.Library()

@register.filter
def is_checkboxselectmultiple(field):
    return field.field.widget.__class__.__name__ == "CheckboxSelectMultiple"
 
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
