import frappe
import stripe
from erpnext.accounts.doctype.payment_request.payment_request import PaymentRequest


@frappe.whitelist(allow_guest=True)
def creat_checkout_session():
    stripe_settings = frappe.get_last_doc('Stripe Settings')
    stripe.api_key = stripe_settings.get_password('secret_key')
    subscription_plan_name = \
        frappe.form_dict.get('subscription_plan_name')
    subscription_plan = frappe.get_doc('Subscription Plan',
                                       subscription_plan_name)
    mode = 'payment'
    cost = subscription_plan.cost
    if subscription_plan.product_price_id:
        mode = 'subscription'
        cost = subscription_plan.product_price_id
    success_url = frappe.form_dict.get('success_url')
    cancel_url = frappe.form_dict.get('cancel_url')
    try:
        checkout_session = \
            stripe.checkout.Session.create(line_items=[{'price': cost,
                                                        'quantity': 1}], mode=mode, cancel_url=cancel_url,
                                           success_url=success_url)
        frappe.response['message'] = checkout_session.url
    except Exception(e):
        frappe.response['message'] = str(e)


def subscription_plan_insert(doc, method=None):
    stripe_settings = frappe.get_last_doc('Stripe Settings')
    stripe.api_key = stripe_settings.get_password('secret_key')
    subscription_plan = doc
    try:
        result = stripe.Product.create(
            name=subscription_plan.name,
            default_price_data={
                "unit_amount": subscription_plan.cost * 100,
                "currency": "eur",
                "recurring": {"interval": subscription_plan.billing_interval.lower(), "interval_count": subscription_plan.billing_interval_count},
            },
            expand=["default_price"],
        )
        subscription_plan.product_price_id = result.default_price.id
    except Exception as e:
        # Handle the exception here, e.g., log it or perform error handling.
        frappe.log_error(frappe.get_traceback(), 'payment failed')


def fill_stripe_coupon_id(doc, method=None):
    stripe_settings = frappe.get_last_doc('Stripe Settings')
    stripe.api_key = stripe_settings.get_password('secret_key')
    coupon = doc
    try:
        if coupon.type_of_discount == "Amount":
            result = stripe.Coupon.create(
                amount_off=coupon.amount_off,
                duration=coupon.duration.lower(),
                currency='eur',
                name=coupon.coupon_name
            )
            coupon.stripe_id = result.id
        elif coupon.type_of_discount == "Percent":
            result = stripe.Coupon.create(
                percent_off=coupon.percent_off,
                duration=coupon.duration.lower(),
                name=coupon.coupon_name
            )
            coupon.stripe_id = result.id
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         'coupon failed to register on stripe')


def apply_coupon(doc, method=None):
    if doc.coupon:
        doc.apply_additional_discount = "Grand Total"
        coupon_doc = frappe.get_doc("Subscription Coupon", doc.coupon)
        doc.additional_discount_percentage = coupon_doc.percent_off
        doc.additional_discount_amount = coupon_doc.amount_off


@frappe.whitelist()
def translated_text(doc):
    return "Helloo"
    # get all document fields which are translatable, and return the translated text
    # the response should be like "{"en":{"field1":"translation"}}"
    # get language from user settings
    lang_code = frappe.local.lang or "en"
    # get all the translatable fields
    meta = frappe.get_meta(doc.doctype)
    translatable_fields = meta.get_translatable_fields()
    translated_text = {}
    for field in translatable_fields:
        # get translation for field
        try:
            translated_field_value = frappe.get_last_doc("Translation", filters=[
                                                         ["source_text", "=", doc.get(field)], ["language", "=", lang_code]])
            # check for null safety to return the source text if translation is not found
            translated_text[field] = translated_field_value and translated_field_value.translated_text or doc.get(
                field)
        except Exception as e:
            translated_text[field] = doc.get(field)
    return translated_text
