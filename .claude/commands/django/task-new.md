---
description: Create a new Django management command or Celery task
model: opus
---

Create a new Django management command or Celery async task.

## Task Specification

$ARGUMENTS

## Django Background Tasks Overview

Two main options for background/scheduled work:
- **Management Commands** - CLI scripts for one-off or cron-scheduled tasks
- **Celery Tasks** - Async task queue for background processing

## Create Management Command

### 1. **Initialize Command**

```bash
# Create management command structure
mkdir -p myapp/management/commands
touch myapp/management/__init__.py
touch myapp/management/commands/__init__.py
```

### 2. **Command Structure**

```python
# myapp/management/commands/my_command.py
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = 'Description of what this command does'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
        parser.add_argument('--limit', type=int, default=100, help='Limit records processed')

    def handle(self, *args, **options):
        try:
            dry_run = options['dry_run']
            limit = options['limit']

            # Business logic here
            records = self.process_records(limit, dry_run)

            self.stdout.write(
                self.style.SUCCESS(f'Successfully processed {records} records')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            raise

    def process_records(self, limit, dry_run):
        # Implementation
        pass
```

### 3. **Common Use Cases**

**Data Cleanup**
```python
class Command(BaseCommand):
    help = 'Clean up old records'

    def handle(self, *args, **options):
        from datetime import timedelta
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(days=30)
        deleted, _ = OldRecord.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(f'Deleted {deleted} old records')
```

**Data Import**
```python
class Command(BaseCommand):
    help = 'Import data from CSV'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        import csv
        with open(options['file']) as f:
            reader = csv.DictReader(f)
            for row in reader:
                MyModel.objects.create(**row)
```

**Send Notifications**
```python
class Command(BaseCommand):
    help = 'Send pending notifications'

    def handle(self, *args, **options):
        pending = Notification.objects.filter(sent=False)
        for notification in pending:
            send_email(notification)
            notification.sent = True
            notification.save()
```

## Create Celery Task

### 1. **Setup Celery**

```python
# myproject/celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 2. **Task Structure**

```python
# myapp/tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task(bind=True, max_retries=3)
def send_notification_email(self, user_id, subject, message):
    try:
        from .models import User
        user = User.objects.get(id=user_id)
        send_mail(subject, message, 'noreply@example.com', [user.email])
        return {'status': 'sent', 'user_id': user_id}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)

@shared_task
def cleanup_old_records():
    from datetime import timedelta
    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = OldRecord.objects.filter(created_at__lt=cutoff).delete()
    return {'deleted': deleted}

@shared_task(bind=True)
def process_large_file(self, file_path):
    # Long-running task with progress updates
    total = count_lines(file_path)
    for i, line in enumerate(read_file(file_path)):
        process_line(line)
        self.update_state(state='PROGRESS', meta={'current': i, 'total': total})
    return {'status': 'complete'}
```

### 3. **Calling Tasks**

```python
# Async call (returns immediately)
send_notification_email.delay(user_id, 'Subject', 'Message')

# With countdown (delay execution)
send_notification_email.apply_async(args=[user_id, 'Subject', 'Message'], countdown=60)

# Scheduled task
from celery.schedules import crontab

app.conf.beat_schedule = {
    'cleanup-every-night': {
        'task': 'myapp.tasks.cleanup_old_records',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

### 4. **Running Celery**

```bash
# Start worker
celery -A myproject worker -l info

# Start beat (scheduler)
celery -A myproject beat -l info

# Both together (dev only)
celery -A myproject worker -B -l info
```

## Best Practices

**Management Commands**
-  Use transactions for data modifications
-  Add --dry-run option for safety
-  Log progress for long-running commands
-  Handle interruptions gracefully
-  Add proper help text

**Celery Tasks**
-  Make tasks idempotent (safe to retry)
-  Use bind=True for access to self
-  Set reasonable max_retries
-  Use countdown for retry delays
-  Monitor with Flower or similar

**Error Handling**
-  Proper logging
-  Graceful degradation
-  Retry logic for transient failures
-  Don't expose sensitive info in errors

**Testing**
```python
# Test management command
from django.core.management import call_command
from io import StringIO

def test_my_command():
    out = StringIO()
    call_command('my_command', '--dry-run', stdout=out)
    assert 'Success' in out.getvalue()

# Test Celery task
def test_send_notification(self):
    result = send_notification_email.delay(user_id, 'Test', 'Message')
    assert result.get(timeout=10)['status'] == 'sent'
```

Generate production-ready Django commands and Celery tasks with proper error handling and logging.
