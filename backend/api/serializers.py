from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer, UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import (Ingredient, Recipe, RecipeIngredient, 
                            Tag)
from users.models import Follow, User


class CustomUserSerializer(UserSerializer):
    """Сериализатор для модели User."""

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        ]


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Cериализатор для модели RecipeIngredient."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit')
    class Meta: 
        model = RecipeIngredient
        fields = ('id','name','measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        source='ingredient_list',
        many=True
    )
    is_favorited = serializers.SerializerMethodField(
        method_name='get_is_favorited')
    is_in_shopping_cart = serializers.SerializerMethodField(
        method_name='get_is_in_shopping_cart')
    author = CustomUserSerializer()

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'name',
            'author',
            'ingredients',
            'image',
            'text',
            'is_favorited',
            'is_in_shopping_cart',
            'cooking_time',
        ]

    @staticmethod
    def get_is_favorited(recipe):
        '''проверка на добавление рецепта в избранное'''
        return recipe.is_favorited.exists()

    @staticmethod
    def get_is_in_shopping_cart(recipe):
        '''проверка на добавление рецепта в список покупок'''
        return recipe.is_in_shopping_cart.exists()


class RecipeShortSerializer(serializers.ModelSerializer):
    """"Сериализатор для добавления в избранное"""

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    '''Сериализатор для добавления ингредиентов в рецепт.'''
    id = serializers.PrimaryKeyRelatedField(source='ingredient', queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = Base64ImageField(required=True)

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True)

    class Meta:
        model = Recipe
        fields = (#'id',
                  'ingredients',
                  'tags',
                  'image',
                  'name',
                  'text',
                  'cooking_time',
                  )


    def create(self, validated_data):

        ingredients = validated_data.pop('ingredients')
        instance = super().create(validated_data)
        ingredient_list = [
            RecipeIngredient(
                recipe=instance,
                ingredient=ingredient_data.get('ingredient'),
                amount=ingredient_data.get('amount')
            )
            for ingredient_data in ingredients
        ]
        instance.ingredient_list.bulk_create(ingredient_list)
        return instance

    def update(self, instance, validated_data):

        ingredients_data = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data.get('ingredient')
            amount = ingredient_data.get('amount')
            instance.ingredient_list.update(
                amount=amount,
                ingredient=ingredient
            )
        return instance


    def to_representation(self, instance):
        return RecipeSerializer(instance).data


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для регистрации новых пользователей."""

    #username = serializers.CharField (source='username')

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        ]


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""

    id = serializers.IntegerField(source='author.id', read_only = True)
    username = serializers.CharField(source='author.username', read_only = True)
    email = serializers.EmailField(source='author.email', read_only = True)
    first_name = serializers.CharField(source='author.first_name', read_only = True)
    last_name = serializers.CharField(source='author.last_name', read_only = True)
    is_subscribed = serializers.SerializerMethodField(
        method_name='get_is_subscribed')
    recipes = RecipeShortSerializer(source='author.recipes', many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()  

    class Meta:
        model = Follow
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        ]

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_is_subscribed(self, obj):
        if obj.user.is_authenticated:
            return obj.user.is_subscribed.filter(
            author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = Recipe.objects.filter(author=obj.author)
        limit = request.GET.get('recipes_limit')

        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeShortSerializer(recipes, many=True)
        return serializer.data


class FollowCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = '__all__'

    def to_representation(self, instance):
        request = self.context.get('request')
        return FollowSerializer(
            instance, context={'request':request}
        ).data
