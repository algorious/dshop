from django.views import generic
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import ListView, DetailView, View
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile, OrderItems
from django.contrib.auth.models import User
from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm, UserProfileForm, ChangeUserFnameLname, ChangeUserAddressForm, UserBillingAddressChangeForm
from .filters import ItemFilter
from django.db.models import Q
from allauth.account.views import PasswordChangeView

import random
import string
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


class CustomPasswordChangeView(PasswordChangeView):
    success_url = '/accounts/password/change/'


@login_required
def name_change_form(request):
    if request.method == "POST":
        user = User.objects.get(username=request.user)
        form = ChangeUserFnameLname(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            messages.success(request, "Your name was successfully changed")
    else:
        form = ChangeUserFnameLname()
    return render(request, 'user_name_change.html', {'form': form})


@login_required
def image_upload(request):
    if request.method == 'POST':
        user_profile = UserProfile.objects.get(user=request.user)
        form = UserProfileForm(
            request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            user_profile.image = form.cleaned_data['image']
            user_profile.save()

            img_obj = form.instance
            return render(request, 'image_upload.html', {'form': form, 'img_obj': img_obj})
    else:
        form = UserProfileForm()
    return render(request, 'image_upload.html', {'form': form})


@login_required
def user_profile(request):
    shipping_address_qs = Address.objects.filter(
        user=request.user, default=True, address_type='S').order_by('-id').last()
    billing_address_qs = Address.objects.filter(
        user=request.user, default=True, address_type='B').order_by('-id').last()

    context = {
        'shipping_address': shipping_address_qs,
        'billing_address': billing_address_qs
    }

    return render(request, "profile.html", context)


@login_required
def billing_address_change_form(request):
    form = UserBillingAddressChangeForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            street_address = form.cleaned_data['street_address']
            apartment_address = form.cleaned_data['apartment_address']
            city = form.cleaned_data['city']
            country = form.cleaned_data['country']
            country_zip = form.cleaned_data['zip']
            billing_address = Address(
                user=request.user,
                street_address=street_address,
                apartment_address=apartment_address,
                city=city,
                country=country,
                zip=country_zip,
                address_type='B',
                default=True)

            billing_address.save()
            messages.success(
                request, "Your billing address was successfully changed")
        else:
            messages.info(
                self.request, "Please fill in the required billing address fields")
            form = UserBillingAddressChangeForm()
    return render(request, 'user_billing_address_change.html', {'form': form})


class ShippingAddressChangeView(View):
    def get(self, *args, **kwargs):
        form = ChangeUserAddressForm()
        context = {
            'form': form
        }
        return render(self.request, "user_shipping_address_change.html", context)

    def post(self, *args, **kwargs):
        form = ChangeUserAddressForm(self.request.POST or None)
        if form.is_valid():
            shipping_address1 = form.cleaned_data.get('address1')
            shipping_address2 = form.cleaned_data.get(
                'address2')
            shipping_city = form.cleaned_data.get(
                'city')
            shipping_country = form.cleaned_data.get(
                'country')
            shipping_zip = form.cleaned_data.get('country_zip')

            if is_valid_form([shipping_address1, shipping_city, shipping_country, shipping_zip]):
                shipping_address = Address(
                    user=self.request.user,
                    street_address=shipping_address1,
                    apartment_address=shipping_address2,
                    city=shipping_city,
                    country=shipping_country,
                    zip=shipping_zip,
                    address_type='S',
                    default=True
                )
                shipping_address.save()

                messages.success(
                    self.request, "Your default shipping address was successfully changed")
                return render(self.request, "user_shipping_address_change.html", {'form': form})
            else:
                messages.info(
                    self.request, "Please fill in the required shipping address fields")
                form = ChangeUserAddressForm()

            return render(self.request, "user_shipping_address_change.html", {'form': form})

        return redirect("core:shipping-address-change")


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs.order_by('-id')[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs.order_by('id').last()})

            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the last default shipping address provided")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs.order_by('-id')[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_city = form.cleaned_data.get(
                        'shipping_city')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_city, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            city=shipping_city,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the default billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs.order_by('-id')[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_city = form.cleaned_data.get(
                        'billing_city')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_city, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            city=billing_city,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an active order")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        # stripeToken is token id from the form (scripts)
        # token = self.request.POST.get('stripeToken')
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

        amount = int(order.get_total() * 100)  # cents

        try:

            if use_default:  # or save:
                # charge the customer because we cannot charge the token more than once
                charge = stripe.Charge.create(
                    amount=amount,  # cents
                    currency="usd",
                    customer=userprofile.stripe_customer_id
                )
            else:
                # charge once off on the token
                # `source` is obtained with Stripe.js; see https://stripe.com/docs/payments/accept-a-payment-charges#web-create-token
                charge = stripe.Charge.create(
                    amount=amount,  # cents
                    currency="usd",
                    source=token
                )

            # create the payment
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            # assign the payment to the order
            order.ordered = True
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request, "Your order was successful!")
            return redirect("/")

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request, "Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            print(e)
            messages.warning(self.request, "Invalid parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request, "Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request, "Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(
                self.request, "Something went wrong. You were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            # send an email to ourselves
            messages.warning(
                self.request, "A serious error occurred. We have been notifed.")
            return redirect("/")


class HomeView(ListView):
    model = Item
    paginate_by = 2
    template_name = "home.html"


class ShirtsView(ListView):
    model = Item
    template_name = 'shirts.html'

    def get_queryset(self):
        return Item.objects.filter(category__exact='S')


class SportWearView(ListView):
    model = Item
    template_name = 'sportwear.html'

    def get_queryset(self):
        return Item.objects.filter(category__exact='SW')


class OutWearView(ListView):
    model = Item
    template_name = 'outwear.html'

    def get_queryset(self):
        return Item.objects.filter(category__exact='OW')


class ItemSearchView(ListView):
    model = Item
    paginate_by = 10
    template_name = "search_results.html"

    def get_queryset(self):
        query = self.request.GET.get('search')
        object_list = Item.objects.filter(
            Q(title__icontains=query) | Q(price__icontains=query) | Q(
                discount_price__icontains=query)
        )
        return object_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = ItemFilter(
            self.request.GET, queryset=self.get_queryset())
        return context


class ShirtsSearchView(ListView):
    model = Item
    paginate_by = 10
    template_name = "shirts_search_results.html"

    def get_queryset(self):
        query = self.request.GET.get('ssearch')
        object_list = Item.objects.filter(
            Q(title__icontains=query) | Q(price__icontains=query) | Q(
                discount_price__icontains=query), Q(category__exact="S")
        )
        return object_list


class SportWearSearchView(ListView):
    model = Item
    paginate_by = 10
    template_name = "sportwear_search_results.html"

    def get_queryset(self):
        query = self.request.GET.get('swsearch')
        object_list = Item.objects.filter(
            Q(title__icontains=query) | Q(price__icontains=query) | Q(
                discount_price__icontains=query), Q(category__exact="SW")
        )
        return object_list


class OutWearSearchView(ListView):
    model = Item
    paginate_by = 10
    template_name = "outwear_search_results.html"

    def get_queryset(self):
        query = self.request.GET.get('owsearch')
        object_list = Item.objects.filter(
            Q(title__icontains=query) | Q(price__icontains=query) | Q(
                discount_price__icontains=query), Q(category__exact="OW")
        )
        return object_list


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You don't have an active order")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )  # item comes from line above
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            # was ("core:product", slug=slug)
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        # redirect back to the slug of the item
    return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        # add a message saying the user doesnt have an order
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            # to handle 0 value in decrement button
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
                messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        # add a message saying the user doesnt have an order
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")


class OrdersByUserListView(LoginRequiredMixin, ListView):
    """Generic class-based view listing orders for current user."""
    model = Order
    template_name = 'orders_list_by_user.html'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-ordered_date')


class OrdersByUserDetailView(LoginRequiredMixin, DetailView):
    """Generic class-based view listing items for current order of current user."""
    model = Order
    template_name = 'order_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uid = self.request.user
        ordid = self.object.pk
        context['orderitems'] = OrderItems.objects.filter(
            orderitem__order__user=self.request.user, order_id=ordid)
        return context


class OrdersCurrentUserView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders.html'
    # paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, ordered=True).order_by('-ordered_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # OrdersCurrentUserView,self
        uid = self.request.user
        context['payment'] = Payment.objects.filter(
            user_id=uid).order_by('-timestamp')
        context['orderitems'] = OrderItems.objects.filter(
            orderitem__order__user=self.request.user).order_by('-order_id')
        return context
