from django.contrib import admin

from .models import Item, OrderItem, Order, Payment, Coupon, Refund, Address, UserProfile, OrderItems


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


make_refund_accepted.short_description = 'Update orders to refund granted'


class OrderItemsInline(admin.TabularInline):
    model = OrderItems
    extra = 0


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['user',
                    'ref_code',
                    'ordered',
                    'being_delivered',
                    'received',
                    'refund_requested',
                    'refund_granted',
                    'billing_address',
                    'shipping_address',
                    'payment',
                    'coupon']
    list_display_links = ['user',
                          'shipping_address',
                          'billing_address',
                          'payment',
                          'coupon']
    list_filter = ['ordered',
                   'being_delivered',
                   'received',
                   'refund_requested',
                   'refund_granted']
    # we refer to username by __
    search_fields = ['user__username',
                     'ref_code']
    # actions to be taken in admin console
    actions = [make_refund_accepted]
    inlines = (OrderItemsInline, RefundInline,)


class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'street_address',
        'apartment_address',
        'city',
        'country',
        'zip',
        'address_type',
        'default'
    ]
    list_filter = ['default', 'address_type', 'country']
    search_fields = ['user', 'street_address',
                     'apartment_address', 'city', 'zip']


class OrderItemAdmin(admin.ModelAdmin):
    inlines = (OrderItemsInline,)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'stripe_customer_id',
        'one_click_purchasing',
        'image'
    ]
    list_filter = ['user']
    search_fields = ['user']


class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'order',
        'reason',
        'accepted',
        'email'
    ]
    list_display_links = ['order']
    list_filter = ['order']
    search_fields = ['order']


admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Address, AddressAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(OrderItems)
admin.site.register(Refund, RefundAdmin)
