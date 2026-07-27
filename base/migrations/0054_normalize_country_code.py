from django.db import migrations

from base.views.country_codes import COUNTRY_CODE_CHOICES

# Ambiguous dial codes (shared by several countries) default to the most
# common member, since legacy rows never stored which country was picked.
AMBIGUOUS_DEFAULTS = {
    '1': 'United States (+1)',
    '7': 'Russian Federation (+7)',
}


def _digits(value):
    return ''.join(ch for ch in (value or '') if ch.isdigit())


def _build_code_map():
    """Map a bare dial-code digit string -> the new unique 'Name (+code)' value."""
    by_code = {}
    for value, _label in COUNTRY_CODE_CHOICES:
        by_code.setdefault(_digits(value), []).append(value)
    code_map = {}
    for code, values in by_code.items():
        code_map[code] = AMBIGUOUS_DEFAULTS[code] if len(values) > 1 else values[0]
    return code_map


def normalize(apps, schema_editor):
    valid = {value for value, _ in COUNTRY_CODE_CHOICES}
    code_map = _build_code_map()

    for model_name in ('Farmer', 'Roaster'):
        Model = apps.get_model('base', model_name)
        for obj in Model.objects.all().iterator():
            cc = obj.country_code
            # Already a valid new-format value, or empty -> leave untouched.
            if not cc or cc in valid:
                continue
            new_value = code_map.get(_digits(cc))
            if new_value:
                obj.country_code = new_value
                obj.save(update_fields=['country_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0053_alter_farmer_country_code_alter_roaster_country_code'),
    ]

    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
    ]
