import os
from PIL import Image
import cairosvg, io

def recenter_and_generate():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    
    # Microbe 11x11 path
    svg_path = (
        "M10 9h1V7H9V6h2V4h-1v1H8v1H7v1h1v1h2Zm-9 2h1v-1H1Zm1-1h1V9H2Zm1 2h2v-2h1v2h2v-1H7V9H4v2H3Zm0-3h1V8H3Z"
        "M0 9h1V8h2V7h1V6H3V5H1V4H0v2h2v1H0Zm5-1h1V7H5Zm2 1h1V8H7ZM3 5h1V4H3ZM2 4h1V3H2ZM1 3h1V2H1Zm7 7h1V9H8Z"
        "m1 1h1v-1H9ZM5 6h1V5H5ZM4 4h3V2h1V1H6v2H5V1H3v1h1Zm3 1h1V4H7Zm1-1h1V3H8Zm1-1h1V2H9Zm0 0"
    )
    
    # 1. Update static/logo.svg and static/logo_clean.svg to tight 11x11
    # viewBox="0 1 11 11" exactly captures the 11x11 sprite (x: 0..11, y: 1..12) with zero extra padding
    svg_11x11_white = f'<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    with open(os.path.join(static_dir, 'logo.svg'), 'w', encoding='utf-8') as f:
        f.write(svg_11x11_white)
    print("Updated static/logo.svg to 44x44 (11x11 viewBox)")

    svg_11x11_black = f'<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 1 11 11"><path fill="#000000" d="{svg_path}"/></svg>'
    with open(os.path.join(static_dir, 'logo_clean.svg'), 'w', encoding='utf-8') as f:
        f.write(svg_11x11_black)
    with open(os.path.join(static_dir, 'logo_inverted.svg'), 'w', encoding='utf-8') as f:
        f.write(svg_11x11_black)
    print("Updated static/logo_clean.svg and logo_inverted.svg")

    # 2. Render tight 11x11 raw sprite at 110x110 (10x scaling, nearest neighbor)
    svg_tight_110 = f'<svg xmlns="http://www.w3.org/2000/svg" width="110" height="110" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    png_bytes = cairosvg.svg2png(bytestring=svg_tight_110.encode('utf-8'), output_width=110, output_height=110)
    sprite_110 = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
    
    # Verify bounding box of sprite_110 is (0, 0, 110, 110)
    print("Tight sprite 110x110 bbox:", sprite_110.getbbox())

    # 3. Create static/logo.png (128x128) with perfectly centered 110x110 sprite (9px padding on all 4 sides)
    logo_128 = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    logo_128.paste(sprite_110, (9, 9), mask=sprite_110)
    logo_128.save(os.path.join(static_dir, 'logo.png'), 'PNG')
    print("Generated perfectly centered static/logo.png (128x128), bbox:", logo_128.getbbox())

    # Dark obsidian background for PWA icons
    DARK_BG = (9, 9, 11, 255) # #09090b

    # 4. Favicon 16x16: render tight 11x11 inside 16x16 with (2, 2) margin (11x11 sprite + 2 left + 3 right -> or 16x16 canvas)
    # Actually for favicon 16x16: 11x11 at (2, 2) has 2 left, 3 right, 2 top, 3 bottom.
    fav16 = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    svg_fav11 = f'<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    fav11_bytes = cairosvg.svg2png(bytestring=svg_fav11.encode('utf-8'), output_width=11, output_height=11)
    sprite_11 = Image.open(io.BytesIO(fav11_bytes)).convert('RGBA')
    fav16.paste(sprite_11, (2, 2), mask=sprite_11)
    fav16.save(os.path.join(static_dir, 'favicon-16x16.png'), 'PNG')
    print("Generated favicon-16x16.png, bbox:", fav16.getbbox())

    # 5. Favicon 32x32: 11x11 * 2 = 22x22. Margins: (32 - 22) / 2 = 5px on all 4 sides!
    fav32 = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    svg_fav22 = f'<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    fav22_bytes = cairosvg.svg2png(bytestring=svg_fav22.encode('utf-8'), output_width=22, output_height=22)
    sprite_22 = Image.open(io.BytesIO(fav22_bytes)).convert('RGBA')
    fav32.paste(sprite_22, (5, 5), mask=sprite_22)
    fav32.save(os.path.join(static_dir, 'favicon-32x32.png'), 'PNG')
    print("Generated favicon-32x32.png, bbox:", fav32.getbbox())

    # 6. Apple Touch Icon (180x180): 11 * 12 = 132px. Margins: (180 - 132) / 2 = 24px on all 4 sides!
    apple_180 = Image.new('RGBA', (180, 180), DARK_BG)
    svg_132 = f'<svg xmlns="http://www.w3.org/2000/svg" width="132" height="132" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    bytes_132 = cairosvg.svg2png(bytestring=svg_132.encode('utf-8'), output_width=132, output_height=132)
    sprite_132 = Image.open(io.BytesIO(bytes_132)).convert('RGBA')
    apple_180.paste(sprite_132, (24, 24), mask=sprite_132)
    apple_180.convert('RGB').save(os.path.join(static_dir, 'apple-touch-icon.png'), 'PNG')
    print("Generated apple-touch-icon.png (180x180), bbox:", apple_180.getbbox())

    # 7. Favicon.ico multi-resolution:
    fav48 = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    # 11 * 4 = 44px. Margins: (48 - 44) / 2 = 2px on all 4 sides!
    svg_44 = f'<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    bytes_44 = cairosvg.svg2png(bytestring=svg_44.encode('utf-8'), output_width=44, output_height=44)
    sprite_44 = Image.open(io.BytesIO(bytes_44)).convert('RGBA')
    fav48.paste(sprite_44, (2, 2), mask=sprite_44)
    fav48.save(
        os.path.join(static_dir, 'favicon.ico'),
        format='ICO',
        sizes=[(16, 16), (32, 32), (48, 48)]
    )
    print("Generated favicon.ico (multi-res 16/32/48)")

    # 8. Android PWA Standard 192x192: 11 * 14 = 154px. Margins: (192 - 154) / 2 = 19px on all 4 sides!
    pwa_192 = Image.new('RGBA', (192, 192), DARK_BG)
    svg_154 = f'<svg xmlns="http://www.w3.org/2000/svg" width="154" height="154" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    bytes_154 = cairosvg.svg2png(bytestring=svg_154.encode('utf-8'), output_width=154, output_height=154)
    sprite_154 = Image.open(io.BytesIO(bytes_154)).convert('RGBA')
    pwa_192.paste(sprite_154, (19, 19), mask=sprite_154)
    pwa_192.convert('RGB').save(os.path.join(static_dir, 'icon-192x192.png'), 'PNG')
    print("Generated icon-192x192.png (192x192), bbox:", pwa_192.getbbox())

    # 9. Android PWA Standard 512x512: 11 * 36 = 396px. Margins: (512 - 396) / 2 = 58px on all 4 sides!
    pwa_512 = Image.new('RGBA', (512, 512), DARK_BG)
    svg_396 = f'<svg xmlns="http://www.w3.org/2000/svg" width="396" height="396" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    bytes_396 = cairosvg.svg2png(bytestring=svg_396.encode('utf-8'), output_width=396, output_height=396)
    sprite_396 = Image.open(io.BytesIO(bytes_396)).convert('RGBA')
    pwa_512.paste(sprite_396, (58, 58), mask=sprite_396)
    pwa_512.convert('RGB').save(os.path.join(static_dir, 'icon-512x512.png'), 'PNG')
    print("Generated icon-512x512.png (512x512), bbox:", pwa_512.getbbox())

    # 10. Android PWA Maskable 192x192: safe zone 80% circle (diameter 153px). 11 * 10 = 110px. Margins: (192 - 110) / 2 = 41px on all 4 sides!
    mask_192 = Image.new('RGBA', (192, 192), DARK_BG)
    mask_192.paste(sprite_110, (41, 41), mask=sprite_110)
    mask_192.convert('RGB').save(os.path.join(static_dir, 'icon-maskable-192x192.png'), 'PNG')
    print("Generated icon-maskable-192x192.png, bbox:", mask_192.getbbox())

    # 11. Android PWA Maskable 512x512: safe zone 80% circle (diameter 409px). 11 * 26 = 286px. Margins: (512 - 286) / 2 = 113px on all 4 sides!
    mask_512 = Image.new('RGBA', (512, 512), DARK_BG)
    svg_286 = f'<svg xmlns="http://www.w3.org/2000/svg" width="286" height="286" viewBox="0 1 11 11"><path fill="#ffffff" d="{svg_path}"/></svg>'
    bytes_286 = cairosvg.svg2png(bytestring=svg_286.encode('utf-8'), output_width=286, output_height=286)
    sprite_286 = Image.open(io.BytesIO(bytes_286)).convert('RGBA')
    mask_512.paste(sprite_286, (113, 113), mask=sprite_286)
    mask_512.convert('RGB').save(os.path.join(static_dir, 'icon-maskable-512x512.png'), 'PNG')
    print("Generated icon-maskable-512x512.png, bbox:", mask_512.getbbox())

if __name__ == '__main__':
    recenter_and_generate()
