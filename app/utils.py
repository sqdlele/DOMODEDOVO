from datetime import datetime

def get_russian_month(month):
    """Возвращает название месяца на русском"""
    months = {
        1: 'января',
        2: 'февраля',
        3: 'марта',
        4: 'апреля',
        5: 'мая',
        6: 'июня',
        7: 'июля',
        8: 'августа',
        9: 'сентября',
        10: 'октября',
        11: 'ноября',
        12: 'декабря'
    }
    return months.get(month, '')

def format_date_russian(date):
    """Форматирует дату в формате '1 января 2024'"""
    if not date:
        return ''
    return f"{date.day} {get_russian_month(date.month)} {date.year}"

def format_time_russian(time):
    """Форматирует время в 24-часовом формате"""
    if not time:
        return ''
    if isinstance(time, str):
        try:
            time = datetime.strptime(time, '%H:%M').time()
        except ValueError:
            return time
    return f"{time.hour:02d}:{time.minute:02d}"
