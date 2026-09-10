import asyncio
from ppp_pricing import get_ppp_display_price

async def test_engine():
    # A mix of rich, emerging, and high-inflation markets
    test_countries = ["US", "AR", "BR", "IN", "JP", "ZA", "ES"]
    
    print(f"{'Country':<8} | {'Display Price':<15} | {'USD PPP':<10} | {'Discount':<10} | {'Stripe Cents':<15}")
    print("-" * 75)
    
    for code in test_countries:
        res = await get_ppp_display_price(code)
        
        country   = code
        display   = res['display']
        ppp_usd   = f"${res['ppp_usd']:.2f}"
        discount  = f"{res['discount_pct']}%"
        stripe    = res['unit_amount_cents']
        
        print(f"{country:<8} | {display:<15} | {ppp_usd:<10} | {discount:<10} | {stripe:<15}")

if __name__ == "__main__":
    asyncio.run(test_engine())