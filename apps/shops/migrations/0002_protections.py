from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shops", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                fields=("shop", "id"),
                name="uq_membership_shop_id",
            ),
        ),
    ]
