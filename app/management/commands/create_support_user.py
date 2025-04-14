from django.core.management.base import BaseCommand
from app.models import SupportUserManager

class Command(BaseCommand):
    help = 'Creates a new support user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('email', type=str)
        parser.add_argument('password', type=str)

    def handle(self, *args, **options):
        try:
            user = SupportUserManager.create_support_user(
                username=options['username'],
                email=options['email'],
                password=options['password']
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created support user "{user.username}"')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create support user: {str(e)}')
            )