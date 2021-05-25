from .models import Item
import django_filters
from django_filters.filters import RangeFilter

# Creating items filters


class ItemFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    price = RangeFilter()

    class Meta:
        model = Item
        fields = ['title', 'price']
        fields = ['title']
