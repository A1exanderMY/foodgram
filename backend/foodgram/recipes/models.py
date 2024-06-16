from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from users.models import User


class Tag(models.Model):
    """Класс тэгов."""

    name = models.CharField(verbose_name='Название', max_length=32)
    slug = models.SlugField(
        verbose_name='Идентификатор', unique=True, max_length=32,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Класс ингридиентов."""

    name = models.CharField(verbose_name='Название', max_length=128)
    measurement_unit = models.CharField(
        verbose_name='Ед. измерения', max_length=64, default=False
    )

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'ингридиенты'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Класс рецептов."""

    name = models.CharField(verbose_name='Название', max_length=256)
    author = models.ForeignKey(
        User, verbose_name='Автор', related_name='recipes',
        on_delete=models.CASCADE
    )
    image = models.ImageField(
        upload_to='recipes/',
        null=True,
        default=None
    )
    text = models.TextField(verbose_name='Описание')
    ingredients = models.ManyToManyField(
        Ingredient, verbose_name='Ингридиенты',
        related_name='recipes', through='RecipeIngredient'
    )
    tags = models.ManyToManyField(
        Tag, blank=False, verbose_name='Тэги', related_name='recipes')
    cooking_time = models.IntegerField(
        verbose_name='Время приготовления',
        validators=(MinValueValidator(1),)
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'рецепты'
        ordering = ['-id']

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Вспомогательная модель для рецептов и ингридиентов."""

    recipe = models.ForeignKey(
        Recipe, related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient, related_name='recipe_ingredients',
        on_delete=models.CASCADE
    )
    amount = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Количество',
        validators=(
            MinValueValidator(1),
            MaxValueValidator(1000)
        )
    )

    def __str__(self):
        return f'{self.recipe} {self.ingredient}'


class ShoppingCart(models.Model):
    """Модель корзины."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт для приготовления',
        on_delete=models.CASCADE,
        null=True)

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        default_related_name = 'shopping_cart'

    def __str__(self):
        return f'{self.recipe}'


class Favorite(models.Model):
    """Модель избранного."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепты')

    class Meta:
        verbose_name = 'Избранные рецепты'
        verbose_name_plural = 'Избранные рецепты'
        default_related_name = 'favorite'

    def __str__(self):
        return f'{self.recipe}'