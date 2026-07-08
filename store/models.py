from datetime import timedelta
from django.utils import timezone

import secrets
import string
from django.core.validators import MinLengthValidator  
from django.db import models
from django.contrib.auth.models import User



# Профиль администратора для контроля спец-доступов
class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    can_change_prices = models.BooleanField(default=False, verbose_name="Разрешено менять цены")

    def __str__(self):
        return f"Права админа для: {self.user.username}"



class TagProposal(models.Model):

    name = models.CharField(max_length=50, verbose_name="Предложенный тег")


    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="К какому товару привязать")
    proposed_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Кто предложил")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Тег '{self.name}' для {self.product.name}"


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True,verbose_name='Названия категорий')


    class Meta:
        verbose_name ='Категория'
        verbose_name_plural = 'Категоии'

    def __str__(self) -> str: 
        return self.name



class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Тег")


    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Теперь timezone берется из django.utils и метод .now() отработает идеально!
        now = timezone.now()
        if self.pk and self.created_at < now - timedelta(days=1):
            self.items.all().delete()
            self.created_at = now
        super().save(*args, **kwargs)



'''Класс таблицы товаров. Внимание теги, категорий, цены и количество вынесенны в отдельную таблицу! '''
class Product(models.Model):
    name = models.CharField(
        max_length=40, 
        validators=[MinLengthValidator(1)], 
        verbose_name="Название товара"
    )
    # Обязательный параметры
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name="products", 
        verbose_name="Категория"
    )
    # Необзятельные парметры
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name="products", 
        verbose_name="Теги товара"
    )
    # Автоматически заполняемые поля
    created_at = models.DateField(
        auto_now_add=True, 
        verbose_name="Дата добавления"
    )
    
    # Поля для модели фото
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True, 
        verbose_name="Изображение товара"
    )



    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name



class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="Товар")
    ip_address = models.GenericIPAddressField(verbose_name="IP гостя")
    comment = models.TextField(verbose_name="Текстовый отзыв", blank=True, null=True)
    
    # Вопросы анкеты (Используем BooleanField: True = Да / Положительно, False = Нет / Отрицательно)
    is_size_matched = models.BooleanField(verbose_name="Размер подошел?")
    is_packaging_intact = models.BooleanField(verbose_name="Упаковка была целой?")
    is_delivery_fast = models.BooleanField(verbose_name="Доставка была быстрой?")
    is_quality_good = models.BooleanField(verbose_name="Качество устроило?")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отзыва")


    class Meta:
        verbose_name = "Отзыв о товаре"
        verbose_name_plural = "Отзывы о товаре"
        # Один гость может оставить только один отзыв на конкретный товар
        unique_together = ('product', 'ip_address')

    def __str__(self):
        return f"Отзыв на {self.product.name} от {self.ip_address}"

    @property
    def calculated_score(self):
        questions = [self.is_size_matched, self.is_packaging_intact, self.is_delivery_fast, self.is_quality_good]
        positive_answers = sum(1 for q in questions if q is True)
        return int((positive_answers / len(questions)) * 100)




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
    ip_address = models.GenericIPAddressField(unique=True, db_index=True, verbose_name="IP-адрес гостя")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Корзина для IP: {self.ip_address}"

    def save(self, *args, **kwargs):
        now = timezone.now()
        if self.pk and self.created_at < now - timedelta(days=1):
            self.items.all().delete()
            self.created_at = now
        super().save(*args, **kwargs)




class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    is_checked = models.BooleanField(default=True, verbose_name="Выбран для покупки")


    class Meta:
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



# --- НОВАЯ СИСТЕМА ДЛЯ ОТМЕЧЕННОГО (ИЗБРАННОГО) С ТАЙМЕРОМ НА СУТКИ ---
class WishList(models.Model):
    ip_address = models.GenericIPAddressField(unique=True, db_index=True, verbose_name='IP-адрес гостя')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Список желаний для IP: {self.ip_address}"



class WishlistItem(models.Model):
    wishlist = models.ForeignKey(WishList, on_delete=models.CASCADE, related_name='items', verbose_name='Избранное')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')


    class Meta:
        unique_together = ('wishlist', 'product')

    def __str__(self):
        return f'{self.product.name} в избранном у {self.wishlist.ip_address}'


# --- НОВАЯ СИСТЕМА ПРОСМОТРЕННОГО (ЛИМИТ 100 СТРОК) ---
class RecentlyViewed(models.Model):
    ip_address = models.GenericIPAddressField(db_index=True, verbose_name='IP-адрес')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар') # Исправлено: ForeignKey
    viewed_at = models.DateTimeField(auto_now=True, verbose_name='Дата просмотра') # Названо viewed_at для работы сортировки


    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('ip_address', 'product')

    def __str__(self):
        return f'{self.ip_address} - {self.product.name}'



# --- МОДЕЛЬ ГАЛЕРЕИ ДОПОЛНИТЕЛЬНЫХ ФОТО (ДО 10 ШТУК) ---
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name="images", 
        verbose_name="Товар"
    )
    image = models.ImageField(
        upload_to='products/gallery/', 
        verbose_name="Дополнительное фото"
    )
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = "Фотография галереи"
        verbose_name_plural = "Галерея фотографий"

    def __str__(self):
        return f"Фото для {self.product.name} (ID: {self.id})"
