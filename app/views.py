from django.contrib.auth import login, logout
from django.db.models import Avg, Q
from .forms import RegisterForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProfileForm, AppointmentForm, ReviewForm, SpecialOfferForm, NewsForm
from .models import Profile, ServiceType, ServiceRecord, Appointment, Review, SpecialOffer, News
from django.utils import timezone
from datetime import datetime, date, time
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
    
@login_required
def get_available_times(request):
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Date is required'}, status=400)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        now = timezone.localtime()
        
        # Определяем рабочие часы в зависимости от дня недели
        weekday = selected_date.weekday()
        if weekday >= 5:  
            working_hours = range(8, 19) 
        else: 
            working_hours = range(8, 21) 
        
        all_times = [f'{i:02d}:00' for i in working_hours]

        booked_times = Appointment.objects.filter(
            date=selected_date,
            status__in=['pending', 'confirmed'] 
        ).values_list('time', flat=True)
        
        booked_times_str = [t.strftime('%H:00') for t in booked_times]

        available_times = [t for t in all_times if t not in booked_times_str]
        
        if selected_date == now.date():
            current_hour = now.hour
            available_times = [t for t in available_times 
                             if int(t.split(':')[0]) > current_hour]
        
        return JsonResponse({
            'available_times': available_times,
            'is_weekend': weekday >= 5 
        })
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
@login_required
def make_appointment(request):
    service_id = request.GET.get('service_id')
    selected_service = None
    
    if service_id:
        try:
            selected_service = ServiceType.objects.get(id=service_id)
        except ServiceType.DoesNotExist:
            messages.error(request, 'Выбранная услуга не найдена')
            return redirect('services')

    if request.method == 'POST':
        form = AppointmentForm(
            request.POST, 
            user=request.user,
            selected_service=selected_service
        )
        
        if form.is_valid():
            try:
                appointment = form.save(commit=False)
                appointment.user = request.user
                appointment.status = 'pending'
                
                # Обновляем телефон в профиле если указан
                phone = form.cleaned_data.get('phone')
                if phone and not request.user.profile.phone:
                    profile = request.user.profile
                    profile.phone = phone
                    profile.save()
                
                appointment.save()
                
                # Сохраняем связь с услугой
                if selected_service:
                    appointment.service_type.add(selected_service)
                
                messages.success(request, 'Запись успешно создана')
                return redirect('appointment_success')

            except Exception as e:
                messages.error(request, f'Ошибка при создании записи: {str(e)}')
        else:
            # Выводим ошибки формы
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = AppointmentForm(
            user=request.user,
            selected_service=selected_service,
            initial={'date': timezone.localdate()}
        )

    context = {
        'form': form,
        'selected_service': selected_service,
        'title': 'Запись на обслуживание',
        'show_phone_field': not request.user.profile.phone
    }
    
    return render(request, 'appointments/make_appointment.html', context)

    
@csrf_exempt  
def auth_view(request):
    if 'HTTP_AUTHORIZATION' in request.META:  
        auth_header = request.META['HTTP_AUTHORIZATION']
        if auth_header == 'Token token':  
            return JsonResponse({'message': 'Авторизация через header успешна!'})
        else:
            return HttpResponse('Неверный токен', status=401)
    elif 'token' in request.GET:  
        token = request.GET.get('token')
        if token == 'token': 
            return JsonResponse({'message': 'Авторизация через параметр URL успешна!'})
        else:
            return HttpResponse('Неверный токен в URL', status=401)
    else:
        return HttpResponse('Требуется авторизация', status=401)

def home(request):
    # Получаем активные новости и спецпредложения
    special_offers = SpecialOffer.objects.filter(is_active=True).order_by('-created_at')
    news = News.objects.filter(is_active=True).order_by('-date')
    
    # Получаем последние отзывы с информацией о ценах
    reviews = Review.objects.select_related(
        'user',
        'appointment'
    ).prefetch_related(
        'appointment__service_type',
        'appointment__service_type__special_offers'
    ).all()[:5]

    for review in reviews:
        # Добавляем информацию о ценах для каждой услуги в отзыве
        for service in review.appointment.service_type.all():
            service.current_price = service.get_actual_price()
            if hasattr(service, 'original_price') and service.original_price:
                service.has_discount = True
            else:
                service.has_discount = False
    
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    context = {
        'special_offers': special_offers,
        'news': news,
        'reviews': reviews,
        'average_rating': average_rating,
        'title': 'Главная'
    }
    
    return render(request, 'home.html', context)  

def header(request):
    return render(request, 'header.html')

@login_required
def appointment_success(request):
    return render(request, 'appointments/appointment_success.html', {
        'title': 'Запись успешно создана'
    })
        
def services_view(request):
    # Получаем поисковый запрос
    search_query = request.GET.get('search', '').strip()
    services = ServiceType.objects.all()
    
    # Если есть поисковый запрос
    if search_query:
        # Разбиваем запрос на отдельные слова
        search_words = search_query.split()
        # Создаем пустой Q-объект
        query = Q()
        
        # Добавляем условие для каждого слова
        for word in search_words:
            query |= Q(name__icontains=word)
        
        # Применяем фильтр
        services = services.filter(query).distinct()
    
    # Группируем по категориям
    services_by_category = {}
    for service in services.order_by('category'):
        if service.category not in services_by_category:
            services_by_category[service.category] = []
        services_by_category[service.category].append(service)
    
    return render(request, 'services/services.html', {
        'services_by_category': services_by_category,
        'query': search_query,
        'title': f'Поиск: {search_query}' if search_query else 'Наши услуги'
    })

def services_category_view(request, category):
    services = ServiceType.objects.filter(category=category).order_by('name')
    return render(request, 'services/services.html', {
        'services_by_category': {category: services},
        'title': f'Услуги - {category}',
        'current_category': category
    })

def register(request: HttpRequest):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', context={
        'title' : 'Регистрация',
        'form' : form,
    })

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                try:
                    profile = user.profile
                except Profile.DoesNotExist:
                    profile = Profile.objects.create(user=user)
                return redirect('profile')
    else:
        form = LoginForm()
    return render(request, 'login.html', context={
        'title': 'Авторизация',
        'form': form,
    })

@login_required
def logout_view(request):
    logout(request)  
    return redirect('home')

def profile_view(request):
    user = request.user
    
    try:
        google_account = SocialAccount.objects.get(user=request.user, provider='google')
        google_data = google_account.extra_data
    except SocialAccount.DoesNotExist:
        google_data = None
        
    # Получаем активные записи
    appointments = Appointment.objects.filter(
        user=user,
        status__in=['pending', 'confirmed']
    ).order_by('-date', '-time')
    
    # Получаем завершенные записи
    service_records = Appointment.objects.filter(
        user=user,
        status='completed'
    ).prefetch_related(
        'service_type',
        'review'
    ).order_by('-date', '-time')
    
    context = {
        'google_data': google_data,
        'user': user,
        'appointments': appointments,
        'service_records': service_records,
        'title': 'Личный кабинет'
        
    }
    
    return render(request, 'profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        if User.objects.exclude(pk=user.pk).filter(username=username).exists():
            messages.error(request, 'Это имя пользователя уже занято')
            return redirect('edit_profile')
        
        if User.objects.exclude(pk=user.pk).filter(email=email).exists():
            messages.error(request, 'Этот email уже используется')
            return redirect('edit_profile')
        

        user.username = username
        user.email = email
        user.save()

        profile = user.profile
        profile.phone = phone
        profile.address = address
        profile.save()

        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if current_password and new_password and confirm_password:
            if user.check_password(current_password):
                if new_password == confirm_password:
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, 'Пароль успешно изменен')
                    update_session_auth_hash(request, user)
                else:
                    messages.error(request, 'Новые пароли не совпадают')
                    return redirect('edit_profile')
            else:
                messages.error(request, 'Неверный текущий пароль')
                return redirect('edit_profile')
        
        messages.success(request, 'Профиль успешно обновлен')
        return redirect('profile')
        
    return render(request, 'edit_profile.html', {
        'title': 'Редактирование профиля'
    })

def appointment_list(request):
    appointments = Appointment.objects.filter(user=request.user).order_by('-date', '-time')
    return render(request, 'appointments/appointment_list.html', {
        'appointments': appointments,
        'title': 'Мои записи'
    })



@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, user=request.user)
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Запись отменена')
        return redirect('appointment_list')
    return render(request, 'appointments/cancel_appointment.html', {
        'appointment': appointment,
        'title': 'Отмена записи'
    })

@login_required
def service_history(request):
    service_records = ServiceRecord.objects.filter().order_by('-date')
    
    return render(request, 'service/service_history.html', {
        'service_records': service_records,
        'title': 'История обслуживания'
    })

@login_required
def create_review(request, appointment_id):  
    appointment = get_object_or_404(Appointment, id=appointment_id, user=request.user)
    
    if appointment.status != 'completed':
        messages.error(request, 'Отзыв можно оставить только для завершенной услуги')
        return redirect('profile')
    
    # Проверяем, существует ли уже отзыв
    if Review.objects.filter(appointment=appointment).exists():
        messages.error(request, 'Вы уже оставили отзыв для этой услуги')
        return redirect('profile')
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.user = request.user
                review.appointment = appointment
                review.save()
                
                messages.success(request, 'Спасибо за ваш отзыв!')
                return redirect('profile')
            except Exception as e:
                messages.error(request, f'Ошибка при сохраненми отзыва: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'appointment': appointment,
        'title': 'Оставить отзыв'
    }
    return render(request, 'reviews/create_review.html', context)

def get_reviews(request):
    reviews = Review.objects.select_related(
        'user',
        'appointment'
    ).prefetch_related(
        'appointment__service_type',
        'appointment__service_type__special_offers'
    ).all()

    for review in reviews:
        # Добавляем информацию о ценах для каждой услуги в отзыве
        for service in review.appointment.service_type.all():
            service.current_price = service.get_actual_price()
            if hasattr(service, 'original_price') and service.original_price:
                service.has_discount = True
            else:
                service.has_discount = False

    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    
    context = {
        'reviews': reviews,
        'average_rating': average_rating,
        'title': 'Отзывы клиентов'
    }
    return render(request, 'reviews/reviews.html', context)

@login_required
def manage_news(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Новость успешно добавлена')
            return redirect('manage_news')
    else:
        form = NewsForm()
    
    news_list = News.objects.all()
    return render(request, 'news/manage_news.html', {
        'form': form,
        'news_list': news_list,
        'title': 'Управление новостями'
    })

@login_required
def manage_special_offers(request):
    if request.method == 'POST':
        form = SpecialOfferForm(request.POST, request.FILES)
        if form.is_valid():
            special_offer = form.save()
            messages.success(request, 'Спецпредложение успешно добавлено')
            return redirect('manage_special_offers')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = SpecialOfferForm()
    
    # Получаем все акции с информацией о связанных услугах
    offers = SpecialOffer.objects.prefetch_related('services').all()
    
    # Готовим данные для отображения
    offers_data = []
    for offer in offers:
        services_info = [
            {
                'name': service.name,
                'original_price': service.original_price or service.price,
                'current_price': service.price
            }
            for service in offer.services.all()
        ]
        
        offers_data.append({
            'offer': offer,
            'services': services_info
        })
    
    return render(request, 'news/manage_special_offers.html', {
        'form': form,
        'offers_data': offers_data,
        'title': 'Управление спецпредложениями'
    })

def news_and_offers(request):
    special_offers = SpecialOffer.objects.filter(is_active=True)
    news = News.objects.filter(is_active=True)
    
    context = {
        'special_offers': special_offers,
        'news': news,
        'title': 'Новости и спецпредложения'
    }
    return render(request, 'home.html', context)

@login_required
def edit_news(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news_item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Новость успешно обновлена')
            return redirect('manage_news')
    else:
        form = NewsForm(instance=news_item)
    
    return render(request, 'news/edit_news.html', {
        'form': form,
        'news_item': news_item,
        'title': 'Редактирование новости'
    })

@login_required
def delete_news(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    if request.method == 'POST':
        news_item.delete()
        messages.success(request, 'Новость успешно удалена')
        return redirect('manage_news')
    
    return render(request, 'news/delete_news.html', {
        'news_item': news_item,
        'title': 'Удаление новости'
    })

@login_required
def edit_special_offer(request, offer_id):
    offer = get_object_or_404(SpecialOffer, id=offer_id)
    if request.method == 'POST':
        form = SpecialOfferForm(request.POST, request.FILES, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Спецпредложение успешно обновлено')
            return redirect('manage_special_offers')
    else:
        form = SpecialOfferForm(instance=offer)
    
    return render(request, 'news/edit_special_offer.html', {
        'form': form,
        'offer': offer,
        'title': 'Редактирование спецпредложения'
    })

@login_required
def delete_special_offer(request, offer_id):
    offer = get_object_or_404(SpecialOffer, id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Спецпредложение успешно удалено')
        return redirect('manage_special_offers')
    
    return render(request, 'news/delete_special_offer.html', {
        'offer': offer,
        'title': 'Удаление спецпредложения'
    })
