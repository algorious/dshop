from django import forms
from allauth.account.forms import SignupForm
from allauth.account.forms import ChangePasswordForm
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import UserProfile, Address
from django.contrib.auth.models import User


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, label='First Name')
    last_name = forms.CharField(max_length=30, label='Last Name')

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user


class CustomChangePasswordForm(ChangePasswordForm):

    def save(self):

        # Ensure you call the parent class's save.
        # .save() does not return anything
        super(CustomChangePasswordForm, self).save()

        # Add your own processing here.


class ChangeUserFnameLname(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        labels = {'first_name': 'First name', 'last_name': 'Last name'}


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['image']


class ChangeUserAddressForm(forms.Form):
    address1 = forms.CharField(required=False)
    address2 = forms.CharField(required=False)
    city = forms.CharField(required=False)
    country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100'
        }))
    country_zip = forms.CharField(required=False)


class UserBillingAddressChangeForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['street_address', 'apartment_address',
                  'city',
                  'country', 'zip']
        widgets = {
            'country': CountrySelectWidget(attrs={'class': 'custom-select d-block w-50'}),
        }
        labels = {'street_address': 'Street address', 'apartment_address': 'Apartment address',
                  'city': 'City', 'country': 'Select country', 'zip': 'Zip'}


PAYMENT_CHOICES = (
    ('S', 'Stripe'),
    ('P', 'PayPal')
)


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(required=False)
    shipping_address2 = forms.CharField(required=False)
    shipping_city = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100'
        }))
    shipping_zip = forms.CharField(required=False)

    billing_address = forms.CharField(required=False)
    billing_address2 = forms.CharField(required=False)
    billing_city = forms.CharField(required=False)
    billing_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100'
        }))
    billing_zip = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(required=False)
    set_default_shipping = forms.BooleanField(required=False)
    use_default_shipping = forms.BooleanField(required=False)
    set_default_billing = forms.BooleanField(required=False)
    use_default_billing = forms.BooleanField(required=False)

    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)


class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code',
        'aria-label': 'Recipient\'s username',
        'aria-describedby': 'basic-addon2'
    }))


class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4   # makes visible 4 rows in TextArea
    }))
    email = forms.EmailField()


class PaymentForm(forms.Form):
    stripeToken = forms.CharField(required=False)
    save = forms.BooleanField(required=False)
    use_default = forms.BooleanField(required=False)
