from .views import is_support

def support_status(request):
    """
    Добавляет информацию о роли поддержки в контекст шаблонов
    """
    if request.user.is_authenticated:
        return {
            'is_support_user': is_support(request.user),
            'support_unread_count': 0  
        }
    return {
        'is_support_user': False,
        'support_unread_count': 0
    }
