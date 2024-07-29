import base64

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import (
    MaxLengthValidator,
    MinValueValidator,
    RegexValidator
)
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient, ShortLink, Tag
)
from users.models import User


class TagSerializer(serializers.ModelSerializer):
    """Получение тэгов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Получение ингридиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class Base64ImageField(serializers.ImageField):
    """Вспомогательный сериализатор для загрузки изображений."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
    """Просмотр информации о пользователе."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, object):
        request = self.context['request']
        if request.user.is_anonymous:
            return False
        return object.following.filter(
            user=request.user, author=object
        ).exists()


class AvatarUserSerializer(serializers.ModelSerializer):
    """Добавление/удаление аватара."""

    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(UserCreateSerializer):
    """Регистрация нового пользователя."""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        validators=[
            MaxLengthValidator(
                settings.USERNAME_MAX_LENGTH,
                'Имя пользователя не должно быть длинее 150 символов'
            ),
            UniqueValidator(
                queryset=User.objects.all(),
                message='Это имя пользователя уже занято'
            ),
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Имя пользователя'
                        'содержит недопустимые символы',
            ),
        ]
    )
    email = serializers.EmailField(
        validators=[
            MaxLengthValidator(
                settings.EMAIL_MAX_LENGTH,
                'Email не должен превышать 254 символа'
            ),
            UniqueValidator(
                queryset=User.objects.all(),
                message='Эта почта уже занята'
            ),
        ]
    )
    first_name = serializers.CharField(
        validators=[
            MaxLengthValidator(
                settings.USERNAME_MAX_LENGTH,
                'Имя не должно быть длинее 150 символов'
            ),
        ]
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'password'
        )


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Вывод короткой информации о рецепте."""

    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(CustomUserSerializer):
    """Получение подписок пользователя."""

    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, object):
        request = self.context['request']
        limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=object)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, object):
        return object.recipes.count()


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Получение ингредиентов в рецепте."""

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeGetSerializer(serializers.ModelSerializer):
    """Получение рецепта."""

    author = CustomUserSerializer(default=serializers.CurrentUserDefault())
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('author', 'tags', 'ingredients')

    def get_is_favorited(self, object):
        request = self.context['request']
        if request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, object):
        request = self.context['request']
        if request.user.is_anonymous:
            return False
        return object.shopping_cart.filter(user=request.user).exists()


class IngredientCreateSerializer(serializers.ModelSerializer):
    """Проверка ингридиента при создании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(write_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amout(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Количество должно быть больше 0'
            )
        return value


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Создание и обновление рецептов."""

    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )
    ingredients = IngredientCreateSerializer(
        write_only=True, many=True
    )
    image = Base64ImageField()
    name = serializers.CharField()
    text = serializers.CharField()
    cooking_time = serializers.IntegerField(
        validators=[MinValueValidator(
            1, 'Время приготовления должно быть больше 0'),]
    )

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time'
        )

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            amount = ingredient['amount']
            ingredient = ingredient['id']
            ingredients, _ = RecipeIngredient.objects.get_or_create(
                recipe=recipe, ingredient=ingredient, amount=amount
            )

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        recipe.save()
        self.create_ingredients(ingredients, recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        self.create_ingredients(ingredients, instance)
        instance.tags.clear()
        instance.tags.set(tags)
        return super().update(instance, validated_data)


class ShortLinkSerializer(serializers.ModelSerializer):
    """Создание короткой ссылки."""

    short_link = serializers.CharField(source='surl')

    class Meta:
        model = ShortLink
        fields = ('short_link',)
