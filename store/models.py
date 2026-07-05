from django.core.validators import MinLengthValidator  # Импортируем валидатор
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
    # Поле для телефона (максимум 20 символов)
    phone = models.CharField(max_length=20, verbose_name="Номер телефона")
    
    # Поле для электронной почты
    email = models.EmailField(verbose_name="Электронная почта")
    
    # Поле для физического адреса
    address = models.CharField(max_length=255, verbose_name="Адрес магазина")

    class Meta:
        verbose_name = "Контакты магазина"
        verbose_name_plural = "Контакты магазина"

    def __str__(self):
        return f"Контакты: {self.phone} | {self.email}"
