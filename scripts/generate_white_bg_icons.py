import os
from PIL import Image
import cairosvg, io

def generate_white_bg_icons():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    
    # Microbe 11x11 path
    svg_path = (
        "M10 9h1V7H9V6h2V4h-1v1H8v1H7v1h1v1h2Zm-9 2h1v-1H1Zm1-1h1V9H2Zm1 2h2v-2h1v2h2v-1H7V9H4v2H3Zm0-3h1V8H3Z"
        "M0 9h1V8h2V7h1V6H3V5H1V4H0v2h2v1H0Zm5-1h1V7H5Zm2 1h1V8H7ZM3 5h1V4H3ZM2 4h1V3H2ZM1 3h1V2H1Zm7 7h1V9H8Z"
        "m1 1h1v-1H9ZM5 6h1V5H5ZM4 4h3V2h1V1H6v2H5V1H3v1h1Zm3 1h1V4H7Zm1-1h1V3H8Zm1-1h1V2H9Zm0 0"
    )
    
    WHITE_BG = (255, 255, 255, 255) # #FFFFFF

    def make_black_sprite(size):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 1 11 11"><path fill="#000000" d="{svg_path}"/></svg>'
        b = cairosvg.svg2png(bytestring=svg.encode('utf-8'), output_width=size, output_height=size)
        return Image.open(io.BytesIO(b)).convert('RGBA')

    # 1. 512x512 standard PWA icon (like avatar_512.svg: white background, black icon)
    pwa512 = Image.new('RGB', (512, 512), WHITE_BG[:3])
    sprite242 = make_black_sprite(242)
    pwa512.paste(sprite242, (135, 135), mask=sprite242)
    pwa512.save(os.path.join(static_dir, 'icon-512x512.png'), 'PNG')
    print("Generated icon-512x512.png (White BG, Black Icon, like avatar_512)")

    # 2. 512x512 maskable PWA icon (white background, black icon within 80% safe zone)
    mask512 = Image.new('RGB', (512, 512), WHITE_BG[:3])
    mask512.paste(sprite242, (135, 135), mask=sprite242)
    mask512.save(os.path.join(static_dir, 'icon-maskable-512x512.png'), 'PNG')
    print("Generated icon-maskable-512x512.png (White BG, Black Icon)")

    # 3. 192x192 standard PWA icon (white background, black icon)
    # 11 * 10 = 110px. Margins: (192 - 110) / 2 = 41px on all sides
    pwa192 = Image.new('RGB', (192, 192), WHITE_BG[:3])
    sprite110 = make_black_sprite(110)
    pwa192.paste(sprite110, (41, 41), mask=sprite110)
    pwa192.save(os.path.join(static_dir, 'icon-192x192.png'), 'PNG')
    print("Generated icon-192x192.png (White BG, Black Icon)")

    # 4. 192x192 maskable PWA icon (white background, black icon)
    mask192 = Image.new('RGB', (192, 192), WHITE_BG[:3])
    mask192.paste(sprite110, (41, 41), mask=sprite110)
    mask192.save(os.path.join(static_dir, 'icon-maskable-192x192.png'), 'PNG')
    print("Generated icon-maskable-192x192.png (White BG, Black Icon)")

    # 5. Apple Touch Icon 180x180 (White background, black icon)
    # 11 * 10 = 110px. Margins: (180 - 110) / 2 = 35px on all sides
    apple180 = Image.new('RGB', (180, 180), WHITE_BG[:3])
    apple180.paste(sprite110, (35, 35), mask=sprite110)
    apple180.save(os.path.join(static_dir, 'apple-touch-icon.png'), 'PNG')
    print("Generated apple-touch-icon.png (White BG, Black Icon)")

    # 6. Favicon 32x32 (White background, black icon)
    # 11 * 2 = 22px. Margins: (32 - 22) / 2 = 5px on all sides
    fav32 = Image.new('RGB', (32, 32), WHITE_BG[:3])
    sprite22 = make_black_sprite(22)
    fav32.paste(sprite22, (5, 5), mask=sprite22)
    fav32.save(os.path.join(static_dir, 'favicon-32x32.png'), 'PNG')
    print("Generated favicon-32x32.png (White BG, Black Icon)")

    # 7. Favicon 16x16 (White background, black icon)
    fav16 = Image.new('RGB', (16, 16), WHITE_BG[:3])
    sprite11 = make_black_sprite(11)
    fav16.paste(sprite11, (2, 2), mask=sprite11)
    fav16.save(os.path.join(static_dir, 'favicon-16x16.png'), 'PNG')
    print("Generated favicon-16x16.png (White BG, Black Icon)")

    # 8. Favicon.ico (White background, black icon multi-res: 16, 32, 48)
    fav48 = Image.new('RGB', (48, 48), WHITE_BG[:3])
    sprite44 = make_black_sprite(44)
    fav48.paste(sprite44, (2, 2), mask=sprite44)
    fav48.save(
        os.path.join(static_dir, 'favicon.ico'),
        format='ICO',
        sizes=[(16, 16), (32, 32), (48, 48)]
    )
    print("Generated favicon.ico (White BG, Black Icon)")

if __name__ == '__main__':
    generate_white_bg_icons()
