from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import SpecialOffer

class Command(BaseCommand):
    help = 'Checks and updates special offers and their prices'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Находим все активные акции с истекшей датой
        expired_offers = SpecialOffer.objects.filter(
            is_active=True,
            end_date__lt=today
        )

        # Деактивируем истекшие акции и восстанавливаем цены
        for offer in expired_offers:
            offer.deactivate()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deactivated offer: {offer.title}')
            )