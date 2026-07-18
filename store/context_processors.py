# store/context_processors.py
from .models import StoreContact, Cart, WishList, RecentlyViewed 
from .utils import get_client_ip
from .models import PartnerProfile


def user_roles(request):
    is_partner = False
    partner_profile = None

    if request.user.is_authenticated:
        try:
            partner_profile = request.user.partner_profile
            is_partner = partner_profile.is_active
        except PartnerProfile.DoesNotExist:
            pass

    return {
        "is_partner": is_partner,
        "partner_profile": partner_profile,
        "is_main_admin": request.user.is_authenticated and request.user.is_superuser,
    }


def global_store_data(request):
    ip = get_client_ip(request)
    
    contact_data = StoreContact.objects.last()
    cart = Cart.objects.filter(ip_address=ip).prefetch_related('items__product').first()
    wishlist = WishList.objects.filter(ip_address=ip).prefetch_related('items__product').first()
    history = RecentlyViewed.objects.filter(ip_address=ip).select_related('product__details').order_by('-viewed_at')[:10]
    
    # Подсчитываем сумму поля quantity для всех позиций в корзине гостя
    cart_total_quantity = 0
    if cart:
        cart_total_quantity = sum(item.quantity for item in cart.items.all())
    
    return {
        'footer_contact_data': contact_data,
        'global_cart': cart,
        'global_wishlist': wishlist,
        'global_history': history,
        'cart_total_quantity': cart_total_quantity  # <-- Отдаем готовую сумму штук товаров!
    }


def footer_contact(request):
    contact_data = StoreContact.objects.last()

    return {
        'footer_contact_data': contact_data
    }
