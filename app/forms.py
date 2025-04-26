from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from .models import Profile, Appointment, ServiceType, Review, News, SpecialOffer
from datetime import datetime, time
from django.core.exceptions import ValidationError
from django.utils import timezone


class AppointmentForm(forms.ModelForm):
    service_type = forms.ModelMultipleChoiceField(
        queryset=ServiceType.objects.all(),
        required=True,
        widget=forms.MultipleHiddenInput(),
        error_messages={
            'required': 'Пожалуйста, выберите услугу',
        }
    )
    
    phone = forms.CharField(
        max_length=18, 
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер телефона',
            }
        ),
        label='Телефон'
    )

    def __init__(self, *args, user=None, selected_service=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Если передана выбранная услуга, устанавливаем её как начальное значение
        if selected_service:
            self.initial['service_type'] = [selected_service.id]
            self.fields['service_type'].initial = [selected_service.id]
        
        # Получаем текущую дату и время
        now = timezone.localtime()
        current_date = now.date()
        current_hour = now.hour
        
        # Определяем рабочие часы в зависимости от дня недели
        def get_working_hours(date):
            weekday = date.weekday()
            if weekday >= 5:
                return range(8, 19)  # До 19:00 в выходные
            return range(8, 21)  # До 21:00 в будние дни
        
        # Получаем выбранную дату из формы или используем текущую
        selected_date = None
        if self.data.get('date'):
            try:
                selected_date = datetime.strptime(self.data['date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                selected_date = current_date
        else:
            selected_date = current_date
        
        # Создаем список всех возможных времен в зависимости от дня недели
        working_hours = get_working_hours(selected_date)
        
        # Если дата сегодняшняя, исключаем текущий и прошедшие часы
        if selected_date == current_date:
            working_hours = [h for h in working_hours if h > current_hour]
        
        all_times = [(f'{i:02d}:00', f'{i:02d}:00') for i in working_hours]
        
        # Получаем занятые времена
        try:
            booked_times = Appointment.objects.filter(
                date=selected_date,
                status__in=['pending', 'confirmed']
            ).values_list('time', flat=True)
            
            # Преобразуем занятые времена в строковый формат
            booked_times_str = [t.strftime('%H:00') for t in booked_times]
            
            # Фильтруем доступные времена
            available_times = [(t, label) for t, label in all_times 
                            if t not in booked_times_str]
        except:
            available_times = all_times

        # Добавляем пустой выбор в начало списка
        available_times = [('', 'Выберите время')] + available_times

        self.fields['time'] = forms.ChoiceField(
            choices=available_times,
            widget=forms.Select(
                attrs={
                    'class': 'form-control time-select',
                }
            ),
            label='Время'
        )

        # Устанавливаем телефон пользователя, если он есть
        if user and user.profile.phone:
            self.fields['phone'].initial = user.profile.phone
            self.fields['phone'].widget.attrs['readonly'] = True

    class Meta:
        model = Appointment
        fields = ['service_type', 'phone', 'date', 'time', 'notes']
        widgets = {
            'date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                    'min': timezone.localdate().strftime('%Y-%m-%d')
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control notes-input',
                    'rows': 4,
                    'placeholder': 'Дополнительная информация...'
                }
            )
        }
        error_messages = {
            'service_type': {
                'required': 'Пожалуйста, выберите услугу',
            },
            'time': {
                'required': 'Пожалуйста, выберите время',
            }
        }

    def clean_time(self):
        time_str = self.cleaned_data.get('time')
        date = self.cleaned_data.get('date')
        
        if not time_str:
            raise ValidationError('Выберите время записи')

        try:
            # Преобразуем строку времени в объект time
            hour = int(time_str.split(':')[0])
            appointment_time = time(hour=hour)
            
            if date:
                # Проверяем существующие записи
                existing_appointment = Appointment.objects.filter(
                    date=date,
                    time=appointment_time,
                    status__in=['pending', 'confirmed']
                ).exists()
                
                if existing_appointment:
                    raise ValidationError(
                        'Это время уже занято. Пожалуйста, выберите другое время.'
                    )
                
                # Проверяем текущее время
                now = timezone.localtime()
                
                if date == now.date():
                    # Если выбранный час совпадает с текущим или меньше текущего
                    if hour <= now.hour:
                        raise ValidationError(
                            'На этот час уже нельзя записаться. Пожалуйста, выберите время на следующий час или позже.'
                        )
            
            return appointment_time
        
        except ValueError:
            raise ValidationError('Неверный формат времени')

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('service_type'):
            raise ValidationError({'service_type': 'Пожалуйста, выберите услугу'})
        return cleaned_data

    
    
class RegisterForm(UserCreationForm):
        username = forms.CharField(
            widget=forms.TextInput(
                attrs={
                    'autocomplete': 'text',
                    'placeholder': 'Введите логин'
                }
            ),
            required=False,
            label='',
            validators=[RegexValidator(r'[0-9a-яА-ЯёЁ]', "Введите логин латиницой")],
        )
        email = forms.EmailField(
            widget=forms.EmailInput(
                attrs={
                    'autocomplete': 'email',
                    'placeholder': 'Введите email',
                }
            ),
            required=False,
            label=''
        )
        password1 = forms.CharField(
            widget=forms.PasswordInput(
                attrs={
                    'placeholder': 'Введите пароль',
                }
            ),
            required=False,
            label=''
        )
        password2 = forms.CharField(
            widget=forms.PasswordInput(
                attrs={
                    'placeholder': 'Повторите пароль',
                }
            ),
            required=False,
            label=''
        )

        def clean_password1(self):
            password = self.cleaned_data['password1']
            if password == '':
                raise forms.ValidationError('Пароль не может быть пустым',  code='invalid')
            return password

        def clean_username(self):
            username = self.cleaned_data['username']
            if username == '':
                raise forms.ValidationError('Логин не может быть пустым', code='invalid')
            return username
        
        def clean_email(self):
            email = self.cleaned_data['email']
            if email == '':
                raise forms.ValidationError('Email не может быть пустым', code='invalid')
            return email
        
        class Meta(UserCreationForm.Meta):
            fields = ("username", "email",  "password1", "password2",)

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(
            attrs={
                'autocomplete': 'text',
                'placeholder': 'Логин',
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'autocomplete': 'current-password',
                'placeholder': 'Пароль',
                }
            ),
    )
    error_messages = {
        "invalid_login": "Неправильный логин или пароль", 
    }
    
    def clean_password(self):
        password = self.cleaned_data['password']
        if password == '':
            raise forms.ValidationError('Введите пароль', code='invalid')
        return password
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if username == '':
            raise forms.ValidationError('Введите логин',  code='invalid')
        if not User.objects.filter(username=username):
            raise forms.ValidationError('Такого пользователя не существует', code='invalid')
        return username
    
    
class ProfileForm(forms.ModelForm):

    phone = forms.CharField(
        max_length=18,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер телефона',
            }
        )
    )

    class Meta:
        model = Profile
        fields = ['phone', 'address']
        widgets = {
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите адрес'
            })
        }

class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
        error_messages={
            'required': 'Пожалуйста, поставьте оценку',
            'min_value': 'Оценка должна быть от 1 до 5',
            'max_value': 'Оценка должна быть от 1 до 5',
        }
    )
    
    comment = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Напишите ваш отзыв...'
            }
        ),
        error_messages={
            'required': 'Пожалуйста, напишите отзыв'
        }
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if not rating:
            raise forms.ValidationError('Пожалуйста, поставьте оценку')
        if rating < 1 or rating > 5:
            raise forms.ValidationError('Оценка должна быть от 1 до 5')
        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        if not comment:
            raise forms.ValidationError('Пожалуйста, напишите отзыв')
        return comment
        
class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'content', 'image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SpecialOfferForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=ServiceType.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Выберите услуги для акции",
        required=False  # Делаем необязательным для обратной совместимости
    )

    class Meta:
        model = SpecialOffer
        fields = ['title', 'content', 'image', 'end_date', 'is_one_time', 'price', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_one_time': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_one_time = cleaned_data.get('is_one_time')
        end_date = cleaned_data.get('end_date')
        services = cleaned_data.get('services', [])

        if not is_one_time and not end_date:
            raise forms.ValidationError(
                "Необходимо указать дату окончания акции для неодноразового предложения"
            )
        
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Если редактируем существующее предложение, отметим выбранные услуги
        if instance:
            self.fields['services'].initial = instance.services.all()

    def save(self, commit=True):
        special_offer = super().save(commit=commit)
        
        if commit:
            # Сначала очищаем все связи
            special_offer.services.clear()
            
            # Затем добавляем выбранные услуги
            services = self.cleaned_data.get('services', [])
            for service in services:
                # Используем промежуточную модель для добавления связи
                from .models import ServiceSpecialOffer
                ServiceSpecialOffer.objects.create(
                    service=service,
                    special_offer=special_offer,
                    is_active=special_offer.is_active
                )
                
                # Обновляем цены, если акция активна
                if special_offer.is_active and special_offer.price:
                    if not service.original_price:
                        service.original_price = service.price
                    service.price = special_offer.price
                    service.save()
        
        return special_offer
