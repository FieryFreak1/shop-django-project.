from .models import StoreContact

def footer_contact(request):
    # Берем самую последнюю запись из таблицы контактов
    contact_data = StoreContact.objects.last()
    
    # Возвращаем словарь с данными. Если в базе пока пусто, вернем None
    return {
        'footer_contact_data': contact_data
    }
