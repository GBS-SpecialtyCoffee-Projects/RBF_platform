from django.db import migrations

TABLE = "base_interactionevent"
EXPECTED_COLUMNS = {"user_id", "path", "session_key"}


def repair_interaction_event(apps, schema_editor):
    """Rebuild ``base_interactionevent`` when it predates the 0052 rewrite.

    ``0052_interactionevent`` was edited after it had already been applied.
    Django tracks migrations by name, so a database that ran the original
    version never picks up the new definition, and ``0056`` cannot convert a
    table whose columns it does not recognise. The result is a table in the
    old shape, where every ``log_event`` insert fails and is swallowed.

    Databases already carrying the expected columns are left untouched, so
    this is a no-op on healthy environments and never discards their rows.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        if TABLE in connection.introspection.table_names(cursor):
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, TABLE
                )
            }
            if EXPECTED_COLUMNS <= columns:
                return

    cascade = " CASCADE" if connection.vendor == "postgresql" else ""
    schema_editor.execute(f"DROP TABLE IF EXISTS {TABLE}{cascade}")
    schema_editor.create_model(apps.get_model("base", "InteractionEvent"))


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0056_profilechange_and_more"),
    ]

    operations = [
        migrations.RunPython(repair_interaction_event, migrations.RunPython.noop),
    ]
