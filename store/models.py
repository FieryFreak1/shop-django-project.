import secrets
import string
from django.core.validators import MinLengthValidator  
from django.db import models

class Product(models.Model):
    name = models.CharField(
        max_length=40, 
        validators=[MinLengthValidator(1)], 
        verbose_name="Название товара"
    )
    # Используем DateField вместо DateTimeField (сохраняет только дату)
    created_at = models.DateField(
        auto_now_add=True, 
        verbose_name="Дата добавления"
    )

    def __str__(self):
        return self.name


class ProductDetails(models.Model):
    # Связь по ID с таблицей Product. При удалении товара удалятся и его детали (on_delete=models.CASCADE)
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        primary_key=True, # ID этой таблицы будет равен ID товара
        related_name="details"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    stock = models.IntegerField(default=0, verbose_name="Остаток на складе")
    sales_count = models.PositiveIntegerField(default=0, verbose_name="Количество продаж")

    def __str__(self):
        return f"Детали для {self.product.name}"


class StoreContact(models.Model):
    phone = models.CharField(max_length=20, verbose_name="Номер телефона")
    email = models.EmailField(verbose_name="Электронная почта")
    address = models.CharField(max_length=255, verbose_name="Адрес магазина")

    class Meta:
        verbose_name = "Контакты магазина"
        verbose_name_plural = "Контакты магазина"

    def __str__(self):
        return f"Контакты: {self.phone} | {self.email}"


# --- ЛОГИКА ДЛЯ ГОРЯЧЕЙ КОРЗИНЫ ГОСТЕЙ ---

class Cart(models.Model):
    # Привязываем корзину к IP-адресу гостя
    ip_address = models.GenericIPAddressField(unique=True, db_index=True, verbose_name="IP-адрес гостя")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Корзина для IP: {self.ip_address}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    class Meta:
        # Исключаем дублирование одного товара в одной корзине
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


# --- ЛОГИКА ДЛЯ ОФОРМЛЕННЫХ ЗАКАЗОВ ---

def generate_order_code():
    """Генерирует случайный уникальный код заказа формата XXXX-XXXX"""
    letters_and_digits = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(letters_and_digits) for _ in range(4))
    part2 = ''.join(secrets.choice(letters_and_digits) for _ in range(4))
    return f"{part1}-{part2}"


class Order(models.Model):
    unique_code = models.CharField(
        max_length=20, 
        unique=True, 
        default=generate_order_code, 
        db_index=True, 
        verbose_name="Уникальный код"
    )
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес гостя")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Итоговая стоимость")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата оплаты")
    is_paid = models.BooleanField(default=True, verbose_name="Статус оплаты")

    def __str__(self):
        return f"Заказ {self.unique_code} от IP {self.ip_address}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ")
    product_name = models.CharField(max_length=255, verbose_name="Название товара на момент покупки")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент покупки")
    quantity = models.PositiveIntegerField(verbose_name="Количество")

    def __str__(self):
        return f"{self.product_name} x {self.quantity} в заказе {self.order.unique_code}"
