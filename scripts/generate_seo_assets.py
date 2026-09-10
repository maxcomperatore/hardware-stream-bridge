"""
Generates production SEO and PWA assets for bipluk.com:
- static/favicon-16x16.png
- static/favicon-32x32.png
- static/apple-touch-icon.png (180x180)
- static/favicon.ico (multi-size: 16x16, 32x32, 48x48)
- static/og_image.png (1200x630)
- static/icon-192x192.png (Android PWA standard)
- static/icon-512x512.png (Android PWA standard)
- static/icon-maskable-192x192.png (Android PWA adaptive/maskable)
- static/icon-maskable-512x512.png (Android PWA adaptive/maskable)
"""
import os
from PIL import Image

def generate_assets():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    logo_path = os.path.join(static_dir, 'logo.png')
    
    # Base logo (white pixel sprite on transparent background)
    img = Image.open(logo_path).convert('RGBA')
    DARK_BG = (9, 9, 11, 255) # #09090b
    
    # 1. Favicon 16x16
    fav16 = img.resize((16, 16), Image.Resampling.NEAREST)
    fav16.save(os.path.join(static_dir, 'favicon-16x16.png'), 'PNG')
    print("Generated favicon-16x16.png")
    
    # 2. Favicon 32x32
    fav32 = img.resize((32, 32), Image.Resampling.NEAREST)
    fav32.save(os.path.join(static_dir, 'favicon-32x32.png'), 'PNG')
    print("Generated favicon-32x32.png")
    
    # 3. Apple Touch Icon 180x180 (iOS standard with dark canvas background)
    apple_bg = Image.new('RGBA', (180, 180), DARK_BG)
    logo_for_apple = img.resize((110, 110), Image.Resampling.NEAREST)
    apple_bg.paste(logo_for_apple, (35, 35), mask=logo_for_apple)
    apple_bg.convert('RGB').save(os.path.join(static_dir, 'apple-touch-icon.png'), 'PNG')
    print("Generated apple-touch-icon.png")
    
    # 4. Multi-resolution favicon.ico
    fav48 = img.resize((48, 48), Image.Resampling.NEAREST)
    fav32.save(
        os.path.join(static_dir, 'favicon.ico'),
        format='ICO',
        sizes=[(16, 16), (32, 32), (48, 48)]
    )
    print("Generated favicon.ico")
    
    # 5. Android PWA Standard 192x192 (Solid dark background so Android never falls back to white)
    pwa192 = Image.new('RGBA', (192, 192), DARK_BG)
    logo192 = img.resize((128, 128), Image.Resampling.NEAREST)
    pwa192.paste(logo192, (32, 32), mask=logo192)
    pwa192.convert('RGB').save(os.path.join(static_dir, 'icon-192x192.png'), 'PNG')
    print("Generated icon-192x192.png")
    
    # 6. Android PWA Standard 512x512
    pwa512 = Image.new('RGBA', (512, 512), DARK_BG)
    logo512 = img.resize((352, 352), Image.Resampling.NEAREST)
    pwa512.paste(logo512, (80, 80), mask=logo512)
    pwa512.convert('RGB').save(os.path.join(static_dir, 'icon-512x512.png'), 'PNG')
    print("Generated icon-512x512.png")

    # 7. Android PWA Maskable 192x192 (80% safe zone to prevent squircle clipping)
    mask192 = Image.new('RGBA', (192, 192), DARK_BG)
    logomask192 = img.resize((110, 110), Image.Resampling.NEAREST)
    mask192.paste(logomask192, (41, 41), mask=logomask192)
    mask192.convert('RGB').save(os.path.join(static_dir, 'icon-maskable-192x192.png'), 'PNG')
    print("Generated icon-maskable-192x192.png")

    # 8. Android PWA Maskable 512x512 (80% safe zone: 300px logo inside 512px canvas)
    mask512 = Image.new('RGBA', (512, 512), DARK_BG)
    logomask512 = img.resize((300, 300), Image.Resampling.NEAREST)
    mask512.paste(logomask512, (106, 106), mask=logomask512)
    mask512.convert('RGB').save(os.path.join(static_dir, 'icon-maskable-512x512.png'), 'PNG')
    print("Generated icon-maskable-512x512.png")
    
    # 9. OG Image 1200x630
    og_svg_path = os.path.join(static_dir, 'og_image.svg')
    og_png_path = os.path.join(static_dir, 'og_image.png')
    
    rendered = False
    try:
        import cairosvg
        cairosvg.svg2png(url=og_svg_path, write_to=og_png_path, output_width=1200, output_height=630)
        print("Generated og_image.png via CairoSVG")
        rendered = True
    except Exception as e:
        print(f"CairoSVG note: {e}")
        
    if not rendered:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 1200, 'height': 630})
                page.goto('file:///' + og_svg_path.replace('\\', '/'))
                page.screenshot(path=og_png_path, type='png')
                browser.close()
            print("Generated og_image.png via Playwright")
            rendered = True
        except Exception as e:
            print(f"Playwright note: {e}")

if __name__ == '__main__':
    generate_assets()
