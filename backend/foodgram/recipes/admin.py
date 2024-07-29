from django.contrib import admin

from .models import (
    Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag
)

admin.site.disable_action("delete_selected")


@admin.action(description='Удалить %(verbose_name)s')
def delete(modeladmin, request, obj):
    obj.delete()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    actions = [delete]


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    list_filter = ('name',)
    actions = [delete]


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 0


class RecipeAdmin(admin.ModelAdmin):
    inlines = [RecipeIngredientInline]
    list_display = ('name', 'author', 'favorites_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    exclude = ('ingredients',)
    actions = [delete]

    def favorites_count(self, obj):
        return obj.favorite.count()


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Favorite)
admin.site.register(ShoppingCart)
