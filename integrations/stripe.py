import stripe

stripe.api_key = "YOUR_SECRET_KEY"

def create_checkout_session(user_email):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price": "price_xxxxx",
            "quantity": 1,
        }],
        success_url="https://yourapp.com/success",
        cancel_url="https://yourapp.com/cancel",
        customer_email=user_email
    )
    return session.url
