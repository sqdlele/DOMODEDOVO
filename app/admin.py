from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, ServiceType, Appointment, Image, Review, SpecialOffer, News


admin.site.site_title = "Администрирование DOMODEDOVO"
admin.site.site_header = "Администрирование сайта DOMODEDOVO"
admin.site.index_title = "Панель управления DOMODEDOVO"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_appointment_info', 'rating', 'short_comment', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'comment', 'appointment__service_type__name')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user', 'appointment')

    def short_comment(self, obj):
        """Возвращает сокращенную версию комментария"""
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    short_comment.short_description = 'Комментарий'

    def get_appointment_info(self, obj):
        """Возвращает информацию о записи"""
        services = ", ".join([service.name for service in obj.appointment.service_type.all()])
        return f"{obj.appointment.date} - {services}"
    get_appointment_info.short_description = 'Запись'

    def get_queryset(self, request):
        """Оптимизация запросов с предварительной загрузкой связанных данных"""
        return super().get_queryset(request).select_related(
            'user',
            'appointment'
        ).prefetch_related('appointment__service_type')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'appointment', 'rating')
        }),
        ('Детали отзыва', {
            'fields': ('comment', 'created_at')
        }),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')
    search_fields = ('user__username', 'phone')
    list_filter = ('user__is_active',)

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'get_description')
    search_fields = ('name', 'description')
    list_filter = ('category', 'price')

    def get_description(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    get_description.short_description = 'Описание'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_services', 'date', 'time', 'status', 'created_at')
    list_filter = ('status', 'date', 'service_type')
    search_fields = ('user__username', 'notes')
    date_hierarchy = 'date'
    filter_horizontal = ('service_type',)

    fieldsets = (
        ('Клиент', {
            'fields': ('user',)
        }),
        ('Информация о записи', {
            'fields': ('service_type', 'date', 'time', 'status')
        }),
        ('Дополнительно', {
            'fields': ('notes',)
        }),
    )

    def get_services(self, obj):
        return ", ".join([service.name for service in obj.service_type.all()])
    get_services.short_description = 'Услуги'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('created_at',)
        return ()

@admin.register(Image)
class AdminImage(admin.ModelAdmin):
    list_display = ('id', 'image_preview')

    def image_preview(self, obj):
        return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
    image_preview.short_description = 'Предпросмотр'

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'is_active')
    list_filter = ('is_active', 'date')
    search_fields = ('title', 'content')
    date_hierarchy = 'date'
    ordering = ('-date',)

@admin.register(SpecialOffer)
class SpecialOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'end_date', 'is_one_time', 'is_active', 'discount_percent')
    list_filter = ('is_active', 'is_one_time', 'created_at')
    search_fields = ('title', 'content')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)