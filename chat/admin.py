from django.contrib import admin
from django.db.models import Q
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp', 'sender', 'receiver')
    search_fields = ('content', 'sender__username', 'receiver__username')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(Q(sender=request.user) | Q(receiver=request.user))
