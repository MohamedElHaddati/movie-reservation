from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="movie",
            name="poster_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
    ]
