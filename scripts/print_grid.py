from PIL import Image
import cairosvg, io

svg_path = 'M10 9h1V7H9V6h2V4h-1v1H8v1H7v1h1v1h2Zm-9 2h1v-1H1Zm1-1h1V9H2Zm1 2h2v-2h1v2h2v-1H7V9H4v2H3Zm0-3h1V8H3ZM0 9h1V8h2V7h1V6H3V5H1V4H0v2h2v1H0Zm5-1h1V7H5Zm2 1h1V8H7ZM3 5h1V4H3ZM2 4h1V3H2ZM1 3h1V2H1Zm7 7h1V9H8Zm1 1h1v-1H9ZM5 6h1V5H5ZM4 4h3V2h1V1H6v2H5V1H3v1h1Zm3 1h1V4H7Zm1-1h1V3H8Zm1-1h1V2H9Zm0 0'

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">
<path fill="#ffffff" d="{svg_path}"/>
</svg>'''
png = cairosvg.svg2png(bytestring=svg.encode('utf-8'), output_width=12, output_height=12)
img = Image.open(io.BytesIO(png)).convert('L')

print("Grid (12x12 with viewBox 0 0 12 12):")
print("    012345678901")
for y in range(12):
    row = ""
    for x in range(12):
        val = img.getpixel((x, y))
        row += "#" if val > 128 else "."
    print(f"{y:2d}: {row}")
