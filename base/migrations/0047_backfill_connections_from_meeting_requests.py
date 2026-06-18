# Backfill the new Connection model from existing MeetingRequest rows.

from django.db import migrations


STATUS_MAP = {"accepted": "active", "pending": "pending", "rejected": "declined"}
PRIORITY = {"active": 3, "pending": 2, "declined": 1}


def backfill(apps, schema_editor):
    MeetingRequest = apps.get_model("base", "MeetingRequest")
    Connection = apps.get_model("base", "Connection")

    best = {}  # (low_id, high_id) -> chosen row data
    for mr in MeetingRequest.objects.all().order_by("updated_at"):
        if not mr.requester_id or not mr.requestee_id:
            continue
        a, b = sorted([mr.requester_id, mr.requestee_id])
        status = STATUS_MAP.get(mr.status, "declined")
        cand = {
            "user_a_id": a,
            "user_b_id": b,
            "initiator_id": mr.requester_id,
            "status": status,
            "message": mr.message,
        }
        current = best.get((a, b))
        # Higher priority wins; on a tie the later row (rows are time-ordered) wins.
        if current is None or PRIORITY[status] >= PRIORITY[current["status"]]:
            best[(a, b)] = cand

    Connection.objects.bulk_create([Connection(**data) for data in best.values()])


def unbackfill(apps, schema_editor):
    apps.get_model("base", "Connection").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0046_connection_connection_uniq_connection_pair"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
