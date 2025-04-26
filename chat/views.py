
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from .models import Message 
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import MessageForm

def is_support(user):
    return hasattr(user, 'profile') and user.profile.role == 'support'

@login_required
def chat_view(request):
    """
    Основной обработчик чата
    """
    if request.method == 'POST':
        message_content = request.POST.get('message', '').strip()
        
        if not message_content:
            return JsonResponse({
                'status': 'error',
                'message': 'Необходимо указать сообщение'
            })

        try:
            if is_support(request.user):
                # Для поддержки требуется client_id
                client_id = request.POST.get('client_id')
                if not client_id:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Необходимо указать ID клиента'
                    })
                receiver = User.objects.get(id=client_id)
            else:
                # Для обычного пользователя находим первого доступного оператора поддержки
                receiver = User.objects.filter(profile__role='support').first()
                if not receiver:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Support not available'
                    })

            # Создаем сообщение
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=message_content
            )

            return JsonResponse({
                'status': 'success',
                'message_id': message.id,
                'timestamp': timezone.localtime(message.timestamp).strftime('%H:%M'),
                'content': message.content,
                'is_sender': True
            })

        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'User not found'
            })

    template = 'chat/support_chat.html' if is_support(request.user) else 'chat/chat_panel.html'
    return render(request, template, {'is_support': is_support(request.user)})

@login_required
def get_chat_list(request):
    """
    Возвращает список активных чатов для операторов поддержки
    """
    if not is_support(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)

    # Получаем уникальные чаты
    chats = Message.objects.filter(
        Q(receiver=request.user) | Q(sender=request.user)
    ).values('sender', 'receiver').distinct()

    chat_list = []
    processed_users = set()

    for chat in chats:
        client_id = chat['sender'] if chat['sender'] != request.user.id else chat['receiver']
        
        if client_id not in processed_users:
            try:
                client = User.objects.get(id=client_id)
                
                # Пропускаем других операторов поддержки
                if hasattr(client, 'profile') and client.profile.role == 'support':
                    continue

                # Получаем последнее сообщение
                last_message = Message.objects.filter(
                    Q(sender=client, receiver=request.user) |
                    Q(sender=request.user, receiver=client)
                ).order_by('-timestamp').first()

                if last_message:
                    chat_list.append({
                        'client_id': client.id,
                        'client_name': client.username,
                        'last_message': last_message.content,
                        'last_time': timezone.localtime(last_message.timestamp).strftime('%H:%M'),
                        'unread_count': Message.objects.filter(
                            sender=client,
                            receiver=request.user,
                            is_read=False
                        ).count()
                    })
                    processed_users.add(client_id)

            except User.DoesNotExist:
                continue

    return JsonResponse({'chats': chat_list})

@login_required
def get_messages(request):
    """
    Получает сообщения для конкретного чата
    """
    messages_query = None
    
    if is_support(request.user):
        client_id = request.GET.get('client_id')
        if client_id:
            try:
                client = User.objects.get(id=client_id)
                messages_query = Message.objects.filter(
                    Q(sender=client, receiver=request.user) |
                    Q(sender=request.user, receiver=client)
                )
            except User.DoesNotExist:
                return JsonResponse({'messages': []})
    else:
        support_user = User.objects.filter(profile__role='support').first()
        if support_user:
            messages_query = Message.objects.filter(
                Q(sender=request.user, receiver=support_user) |
                Q(sender=support_user, receiver=request.user)
            )

    if not messages_query:
        return JsonResponse({'messages': []})

    # Отмечаем сообщения как прочитанные
    messages_query.filter(receiver=request.user, is_read=False).update(is_read=True)

    # Формируем данные сообщений с правильным определением отправителя
    messages_data = []
    for msg in messages_query.order_by('timestamp'):
        is_sender = msg.sender.id == request.user.id  # Проверяем, является ли текущий пользователь отправителем
        messages_data.append({
            'id': msg.id,
            'content': msg.content,
            'timestamp': timezone.localtime(msg.timestamp).strftime('%H:%M'),
            'is_sender': is_sender,  # Правильное определение отправителя
            'is_read': msg.is_read,
            'sender_name': msg.sender.username
        })

    print(f"Отправитель сообщений (user_id={request.user.id}):")
    for msg in messages_data:
        print(f"Сообщение ID={msg['id']}: is_sender={msg['is_sender']}, content={msg['content']}")

    return JsonResponse({'messages': messages_data})

@login_required
def mark_messages_read(request):
    """
    Отмечает все сообщения как прочитанные
    """
    Message.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})
