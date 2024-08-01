import random
from string import ascii_letters

from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShortLink,
    ShoppingCart,
    Tag
)
from users.models import Subscriber, User

from .filters import IngredientFilter, RecipeFilter
from .paginators import LimitPageNumberPaginator
from .permissions import IsAuthorOrAdminOrReadOnly
from .serializers import (
    AvatarUserSerializer,
    CustomUserSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeGetSerializer,
    ShortLinkSerializer,
    ShortRecipeSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserSerializer
)


class TagViewSet(ReadOnlyModelViewSet):
    """Получение тэгов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    """Получение ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    """Создание и получение рецептов."""

    queryset = Recipe.objects.all()
    pagination_class = LimitPageNumberPaginator
    filterset_class = RecipeFilter
    permission_classes = (IsAuthorOrAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeGetSerializer
        if self.action in ('add_to_favorite', 'add_to_shopping_cart'):
            return ShortRecipeSerializer
        return RecipeCreateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='favorite')
    def add_to_favorite(self, request, pk):
        """Добавить рецепт в избранное."""
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            favorite = Favorite.objects.filter(
                user=self.request.user, recipe=recipe
            )
            if favorite:
                raise ValidationError('Рецепт уже добавлен')
            Favorite.objects.create(user=self.request.user, recipe=recipe)
            serializer = self.get_serializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            instance = Favorite.objects.filter(
                user=self.request.user, recipe=recipe
            )
            if not instance:
                raise ValidationError('Рецепт уже удален')
            instance.delete()
            return Response('Рецепт удален', status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def add_to_shopping_cart(self, request, pk):
        """Добавить рецепт в корзину."""
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            shopping_cart = ShoppingCart.objects.filter(
                user=self.request.user, recipe=recipe
            )
            if shopping_cart:
                raise ValidationError('Рецепт уже добавлен')
            ShoppingCart.objects.create(user=self.request.user, recipe=recipe)
            serializer = self.get_serializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            instance = ShoppingCart.objects.filter(
                user=self.request.user, recipe=recipe
            )
            if not instance:
                raise ValidationError('Рецепт уже удален из корзины')
            instance.delete()
            return Response('Рецепт удален', status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        shopping_cart = ShoppingCart.objects.filter(
            user=self.request.user).values('recipe_id')
        if not shopping_cart:
            raise ValidationError('Список покупок пуст')
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=shopping_cart
        ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
            amount=Sum('amount')
        )
        groceries_list = ''
        for item in ingredients:
            groceries_list += (
                f'{item.get("ingredient__name")} - {item.get("amount")}'
                f'{item.get("ingredient__measurement_unit")}.\n')
        file = 'Необходимо купить:\n' + groceries_list
        response = HttpResponse(file, content_type="text/plain")
        response['Content-Disposition'] = (
            'attachment; filename=file.txt'
        )
        return response


@api_view(['GET'])
def short_link(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if ShortLink.objects.filter(lurl=recipe.get_absolute_url()).exists():
        serializer = ShortLinkSerializer(
            ShortLink.objects.get(lurl=recipe.get_absolute_url())
        )
        return Response(serializer.data)
    domain = "http://" + get_current_site(request).name + '/s/'
    surl = domain + (''.join(random.sample(ascii_letters, k=7)))
    link, _ = ShortLink.objects.get_or_create(
        lurl=recipe.get_absolute_url(),
        surl=surl
    )
    serializer = ShortLinkSerializer(link)
    return Response(serializer.data)


def get_full_link(request, short_link):
    domain = 'http://' + get_current_site(request).name + '/s/'
    link = get_object_or_404(ShortLink, surl=domain + short_link)
    link = link.lurl.replace('/api', '', 1)[:-1]
    return redirect(link)


class UserViewSet(ModelViewSet):
    """Работа с пользователями."""

    queryset = User.objects.all()
    pagination_class = LimitPageNumberPaginator
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        if self.action in ('retrieve', 'list', 'create'):
            return (AllowAny(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'user_self_profile'):
            return CustomUserSerializer
        elif self.action == 'user_avatar':
            return AvatarUserSerializer
        elif self.action == 'set_password':
            return SetPasswordSerializer
        elif self.action in ('subscribe', 'subscribtions'):
            return SubscriptionSerializer
        return UserSerializer

    @action(detail=False, url_path='me')
    def user_self_profile(self, request):
        """Просмотр информации о пользователе."""
        user = self.request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['put', 'delete'], detail=False, url_path='me/avatar'
    )
    def user_avatar(self, request):
        """Загрузка и удаление аватара пользователя."""
        user = self.request.user
        if request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            instance = self.request.user
            instance.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post', 'delete'], detail=True)
    def subscribe(self, request, pk=None):
        """Подписка на пользователей."""
        user = self.request.user
        author = User.objects.get(pk=pk)
        if request.method == 'POST':
            if Subscriber.objects.filter(author=author, user=user):
                raise ValidationError('Вы уже подписаны')
            Subscriber.objects.create(user=user, author=author)
            serializer = self.get_serializer(author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            instance = Subscriber.objects.filter(author=author, user=user)
            if not instance:
                raise ValidationError('Вы не подписаны на автора')
            instance.delete()
            return Response(
                'Вы успешно отписались', status=status.HTTP_204_NO_CONTENT
            )

    @action(detail=False)
    def subscriptions(self, request):
        """Просмотр подписок пользователя."""
        user = self.request.user
        subscriptions = User.objects.filter(following__user=user)
        list = self.paginate_queryset(subscriptions)
        serializer = SubscriptionSerializer(
            list, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['post'], detail=False)
    def set_password(self, request, *args, **kwargs):
        """Изменение пароля."""
        user = self.request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.data['new_password'])
        user.save()
        return Response('Пароль успешно изменен.', status=status.HTTP_200_OK)
