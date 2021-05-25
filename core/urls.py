from django.urls import path
from .views import (
    ItemDetailView,
    HomeView,
    OrderSummaryView,
    add_to_cart,
    remove_from_cart,
    remove_single_item_from_cart,
    CheckoutView,
    PaymentView,
    AddCouponView,
    RequestRefundView,
    user_profile,
    OrdersCurrentUserView,
    image_upload,
    name_change_form,
    ItemSearchView,
    ShirtsView,
    ShirtsSearchView,
    SportWearView,
    SportWearSearchView,
    OutWearView,
    OutWearSearchView,
    CustomPasswordChangeView,
    OrdersByUserListView,
    OrdersByUserDetailView,
    ShippingAddressChangeView,
    billing_address_change_form
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<slug>', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    path('accounts/profile/', user_profile, name='account-profile'),
    path('upload/', image_upload, name='image-upload'),
    path('accounts/profile/name-change/', name_change_form, name='name-change'),
    path('search-results/', ItemSearchView.as_view(), name='search-results'),
    path('shirts/', ShirtsView.as_view(), name='shirts'),
    path('shirt-search-results/', ShirtsSearchView.as_view(),
         name='shirt-search-results'),
    path('sportwear/', SportWearView.as_view(), name='sportwear'),
    path('sportwear-search-results/', SportWearSearchView.as_view(),
         name='sportwear-search-results'),
    path('outwear/', OutWearView.as_view(), name='outwear'),
    path('outwear-search-results/', OutWearSearchView.as_view(),
         name='outwear-search-results'),
    path('accounts/password/change/',
         CustomPasswordChangeView.as_view(), name='password-change'),
    path('accounts/profile/orders/',
         OrdersCurrentUserView.as_view(), name='orders'),
    path('accounts/profile/orders-list/',
         OrdersByUserListView.as_view(), name='orders-list'),
    path('accounts/profile/order/<int:pk>',
         OrdersByUserDetailView.as_view(), name='order-detail'),
    path('accounts/profile/shipping-address-change/',
         ShippingAddressChangeView.as_view(), name='shipping-address-change'),
    path('accounts/profile/billing-address-change/',
         billing_address_change_form, name='billing-address-change'),
]
