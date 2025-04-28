from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
class Profile(models.Model):
    USER_ROLES = [
        ('client', 'Клиент'),
        ('support', 'Поддержка'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=18, blank=True, null=True, verbose_name="Телефон")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес")
    role = models.CharField(max_length=20, choices=USER_ROLES, default='client', verbose_name="Роль")

    def __str__(self):
        return f"Профиль {self.user.username}"

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    @property
    def is_support(self):
        return self.role == 'support'

    @property
    def is_client(self):
        return self.role == 'client'

    def make_support(self):
        self.role = 'support'
        self.save()

    def make_client(self):
        self.role = 'client'
        self.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Создает профиль пользователя и добавляет его в группу клиентов при первом создании
    """
    if created:
        with transaction.atomic():
            # Создаем профиль
            Profile.objects.create(user=instance)

            # Добавляем в группу клиентов только если это не пользователь поддержки
            if not hasattr(instance, 'profile') or instance.profile.role != 'support':
                client_group, _ = Group.objects.get_or_create(name='Clients')
                instance.groups.add(client_group)

@receiver(post_save, sender=Profile)
def handle_user_roles(sender, instance, **kwargs):
    """
    Управляет группами пользователя в зависимости от его роли
    """
    if not hasattr(handle_user_roles, 'is_running'):
        handle_user_roles.is_running = True
        try:
            with transaction.atomic():
                # Получаем или создаем группы
                support_group, _ = Group.objects.get_or_create(name='Support')
                client_group, _ = Group.objects.get_or_create(name='Clients')

                # Управляем группами и правами
                if instance.role == 'support':
                    # Очищаем все группы перед добавлением
                    instance.user.groups.clear()
                    instance.user.groups.add(support_group)
                    instance.user.is_staff = True
                else:
                    # Очищаем все группы перед добавлением
                    instance.user.groups.clear()
                    instance.user.groups.add(client_group)
                    instance.user.is_staff = False

                instance.user.save()
        finally:
            handle_user_roles.is_running = False

class ServiceType(models.Model):
    CATEGORIES = [
        ('Диагностика', 'Диагностика'),
        ('Ремонт', 'Ремонт'),
        ('ТО', 'ТО'),
    ]

    name = models.CharField(max_length=100, verbose_name="Название услуги")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    category = models.CharField(max_length=50, choices=CATEGORIES, verbose_name="Категория")
    image = models.ImageField(upload_to='services/', null=True, blank=True, verbose_name="Изображение")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Оригинальная цена")

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category} - {self.name}"

    def get_discount_offer(self):
        today = timezone.now().date()
        return self.special_offers.filter(
            is_active=True,
            end_date__gte=today
        ).order_by('-discount_percent').first()

    @property
    def discounted_price(self):
        offer = self.get_discount_offer()
        if offer and offer.discount_percent:
            discount = Decimal(offer.discount_percent) / Decimal('100')
            discounted = self.price * (Decimal('1') - discount)
            return discounted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return None

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('confirmed', 'Подтверждено'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    service_type = models.ManyToManyField(ServiceType, verbose_name="Типы услуг")
    date = models.DateField(verbose_name="Дата")
    time = models.TimeField(verbose_name="Время")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    notes = models.TextField(blank=True, null=True, verbose_name="Примечания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    def __str__(self):
        return f"Запись {self.user.username} на {self.date}"

    class Meta:
        verbose_name = "Запись на приём"
        verbose_name_plural = "Записи на приём"
        ordering = ['-date', '-time']


class Image(models.Model):
    image = models.ImageField(upload_to='images/')


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name="Запись на приём"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оценка"
    )
    comment = models.TextField(verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв от {self.user.username} - {self.rating}★"

class SupportUserManager:
    @staticmethod
    def create_support_user(username, email, password, **extra_fields):

        with transaction.atomic():
            # Create base user with is_staff=True
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                **extra_fields
            )

            # Очищаем все группы (на всякий случай)
            user.groups.clear()

            # Создаем или получаем группу Support
            support_group, _ = Group.objects.get_or_create(name='Support')

            # Добавляем пользователя в группу Support
            user.groups.add(support_group)

            # Обновляем роль профиля
            profile = user.profile
            profile.role = 'support'
            profile.save()

            # Повторно сохраняем пользователя, чтобы убедиться, что is_staff установлен
            user.is_staff = True
            user.save()

            return user

class News(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержание")
    image = models.ImageField(upload_to='news/', verbose_name="Изображение")
    date = models.DateField(auto_now_add=True, verbose_name="Дата публикации")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ['-date']

    def __str__(self):
        return self.title

class SpecialOffer(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержание")
    image = models.ImageField(upload_to='offers/', verbose_name="Изображение")
    end_date = models.DateField(verbose_name="Дата окончания акции", null=True, blank=True)
    is_one_time = models.BooleanField(default=False, verbose_name="Одноразовое предложение")
    discount_percent = models.PositiveIntegerField("Скидка (%)", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True)
    services = models.ManyToManyField(
        ServiceType,
        through='ServiceSpecialOffer',
        related_name='special_offers',
        verbose_name="Связанные услуги"
    )

    class Meta:
        verbose_name = "Спецпредложение"
        verbose_name_plural = "Спецпредложения"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def period_display(self):
        if self.is_one_time:
            return "Одноразовое предложение"
        elif self.end_date:
            return f"До {self.end_date.strftime('%d %B')}"
        return "Бессрочная акция"

    def deactivate(self):
        self.is_active = False
        self.save()
        service_offers = ServiceSpecialOffer.objects.filter(special_offer=self)
        for service_offer in service_offers:
            service = service_offer.service
            if service.original_price:
                service.price = service.original_price
                service.original_price = None
                service.save()

class ServiceSpecialOffer(models.Model):
    """Промежуточная модель для связи услуг и акций"""
    service = models.ForeignKey(ServiceType, on_delete=models.CASCADE, verbose_name="Услуга")
    special_offer = models.ForeignKey(SpecialOffer, on_delete=models.CASCADE, verbose_name="Акция")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Связь услуги и акции"
        verbose_name_plural = "Связи услуг и акций"
        unique_together = ('service', 'special_offer')

    def __str__(self):
        return f"{self.service} - {self.special_offer}"
