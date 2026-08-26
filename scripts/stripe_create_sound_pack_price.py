#!/usr/bin/env python3
"""Create a $9 Stripe Price for shop sound packs. Run once, then set the env var in Vercel."""

import os
import sys

import stripe

PACK_PRICE_CENTS = 900


def main() -> None:
    secret = os.environ.get("STRIPE_SECRET_KEY")
    if not secret:
        print("Set STRIPE_SECRET_KEY in your environment first.", file=sys.stderr)
        sys.exit(1)

    stripe.api_key = secret
    product = stripe.Product.create(
        name="knob.monster Sound Pack",
        description="Digital SysEx sound expansion — instant vault delivery.",
        tax_code="txcd_10000000",
        metadata={"type": "sound_pack"},
    )
    price = stripe.Price.create(
        product=product.id,
        unit_amount=PACK_PRICE_CENTS,
        currency="usd",
        metadata={"type": "sound_pack"},
    )
    print("Created Stripe product + price for shop packs.")
    print(f"Product ID: {product.id}")
    print(f"Price ID:   {price.id}")
    print()
    print("Add this to Vercel (and redeploy):")
    print(f"STRIPE_PRICE_ID_SOUND_PACK={price.id}")


if __name__ == "__main__":
    main()
