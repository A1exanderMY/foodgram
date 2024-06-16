import base64
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.files.base import ContentFile
from django.db import transaction
from django.core.validators import MaxLengthValidator, MinValueValidator, RegexValidator
from djoser.serializers import UserCreateSerializer, UserSerializer

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag
)
from users.models import Subscriber, User

USERNAME_MAX_LENGTH = 150
TAG_MAX_LENGTH = 32
EMAIL_MAX_LENGTH = 254


class TagSerializer(serializers.ModelSerializer):
    """СПолучение тегов."""

    name = serializers.CharField(
        validators=[
            MaxLengthValidator(
                TAG_MAX_LENGTH,
                'Имя тэга не должно быть больше 32 символов'
            )
        ]
    )
    slug = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r'^[-a-zA-Z0-9_]+$',
                message='Введите корректый идентификатор'
            ),
            UniqueValidator(queryset=Tag.objects.all()),
            MaxLengthValidator(
                TAG_MAX_LENGTH,
                'Слаг тэга не должнен быть больше 32 символов'
            )
        ]
    )

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
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('email', "id", 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscriber.objects.filter(
            user=request.user, author=obj
        ).exists()


class AvatarUserSerializer(serializers.ModelSerializer):
    """Добавление/удаление аватара."""

    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance


class UserSerializer(UserCreateSerializer):
    """Регистрация нового пользователя."""

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(
        validators=[
            MaxLengthValidator(
                USERNAME_MAX_LENGTH,
                'Имя пользователя не должно быть длинее 150 символов'
            ),
            UniqueValidator(
                queryset=User.objects.all(),
                message='Это имя пользователя уже занято'
            ),
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Имя пользователя должно'
                        'содержит недопустимые символы',
            ),
        ]
    )
    email = serializers.EmailField(
        validators=[
            MaxLengthValidator(
                EMAIL_MAX_LENGTH,
                'Email не должен превышать 254 символа'
            ),
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='Адрес электронной почты содержит недопустимые символы',
            ),
        ]
    )
    first_name = serializers.CharField(
        validators=[
            MaxLengthValidator(
                USERNAME_MAX_LENGTH,
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

    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(CustomUserSerializer):
    """Получение подписок пользователя."""

    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True)
        return serializer.data

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = self.context['request'].user
        if not request or not user.is_authenticated:
            return False
        return obj.following.filter(user=user).exists()

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()


class RecipeIngredientGetSerializer(serializers.ModelSerializer):
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
    """Получение списка рецептов."""

    author = CustomUserSerializer(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    tags = TagSerializer(
        many=True,
        read_only=True
    )
    ingredients = RecipeIngredientGetSerializer(
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

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user, recipe=obj
        ).exists()


class IngredientCreateSerializer(serializers.ModelSerializer):
    """Проверка ингридиента при создании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField(
        write_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')
    
    """def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Количество ингридиента должно быть больше 0'
            )
        return value"""
    
    def validate(self, data):
        if data['amount'] <= 0:
            raise serializers.ValidationError(
                f'Количество ингридиента {data["id"]} должно быть больше 0'
            )
        return data


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
            1, 'Время приготовления должно быть больше 0'),
        ]
    )

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time'
        )
    
    def to_representation(self, instance):
        serializer = RecipeGetSerializer(instance)
        return serializer.data

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            amount = ingredient['amount']
            ingredient = ingredient['id']
            ingredients, created = RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
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
    short_link = serializers.SerializerMethodField(
        'get_short_url', read_only=True)

    class Meta:
        model = Recipe
        fields = ('short_link',)

    def get_short_url(self, obj):
        if obj.image:
            return obj.image.url
        return None
