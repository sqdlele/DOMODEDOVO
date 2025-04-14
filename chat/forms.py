from django import forms

class MessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'message-input',
            'placeholder': 'Введите сообщение...',
            'id': 'messageInput'
        }),
        required=True,
        max_length=1000
    )
    client_id = forms.IntegerField(
        widget=forms.HiddenInput(attrs={'id': 'currentClientId'}),
        required=True
    )
