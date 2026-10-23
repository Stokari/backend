from django.db import migrations

FORWARD_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_offline_lease_membership_shop'
          AND conrelid = 'offline_lease'::regclass
    ) THEN
        ALTER TABLE offline_lease
        ADD CONSTRAINT fk_offline_lease_membership_shop
        FOREIGN KEY (shop_id, membership_id)
        REFERENCES membership (shop_id, id)
        ON DELETE RESTRICT;
    END IF;
END
$$;
"""

REVERSE_SQL = """
ALTER TABLE offline_lease
DROP CONSTRAINT IF EXISTS fk_offline_lease_membership_shop;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0003_alter_offlinelease_renewed_from_and_more"),
        ("shops", "0002_protections"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
