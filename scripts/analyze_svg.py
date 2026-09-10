from PIL import Image
import cairosvg, io

svg_path = 'M10 9h1V7H9V6h2V4h-1v1H8v1H7v1h1v1h2Zm-9 2h1v-1H1Zm1-1h1V9H2Zm1 2h2v-2h1v2h2v-1H7V9H4v2H3Zm0-3h1V8H3ZM0 9h1V8h2V7h1V6H3V5H1V4H0v2h2v1H0Zm5-1h1V7H5Zm2 1h1V8H7ZM3 5h1V4H3ZM2 4h1V3H2ZM1 3h1V2H1Zm7 7h1V9H8Zm1 1h1v-1H9ZM5 6h1V5H5ZM4 4h3V2h1V1H6v2H5V1H3v1h1Zm3 1h1V4H7Zm1-1h1V3H8Zm1-1h1V2H9Zm0 0'

for vb in ['0 0 12 12', '0 1 11 11', '0 0 11 11', '0 1 12 12', '0 0 11 12']:
    test_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="{vb}"><path fill="#ffffff" d="{svg_path}"/></svg>'
    png_bytes = cairosvg.svg2png(bytestring=test_svg.encode('utf-8'))
    img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
    bbox = img.getbbox()
    print(f"viewBox: {vb:10} -> bbox in 120x120: {bbox}, width={bbox[2]-bbox[0]}, height={bbox[3]-bbox[1]}, left_pad={bbox[0]}, right_pad={120-bbox[2]}, top_pad={bbox[1]}, bot_pad={120-bbox[3]}")

logo_img = Image.open('static/logo.png')
print(f"static/logo.png size: {logo_img.size}, bbox: {logo_img.getbbox()}")
