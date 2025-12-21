from django.db import migrations, models
import django.conf

def create_doctorprofile_table(apps, schema_editor):
    DoctorProfile = apps.get_model('accounts', 'DoctorProfile')
    # No data creation needed; this just ensures table exists
    # If using MySQL/Postgres, Django will handle table creation via migration

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DoctorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(max_length=150)),
                ('specialization', models.CharField(max_length=100, choices=[
                    ('General Practitioner', 'General Practitioner'),
                    ('Pediatrician', 'Pediatrician'),
                    ('Psychiatrist', 'Psychiatrist'),
                    ('Opthalmologist', 'Ophthalmologist'),
                ])),
                ('doctor_id', models.CharField(max_length=20, unique=True, blank=True)),
                ('user', models.OneToOneField(on_delete=models.CASCADE, to=django.conf.settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
