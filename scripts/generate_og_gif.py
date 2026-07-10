import math
import os
from PIL import Image, ImageDraw

def make_og_gif():
    # 400x210 design resolution (will be scaled up 3x to 1200x630 with nearest neighbor)
    w, h = 400, 210
    frames = []
    
    # 24 frame loop for smoother sweep animation
    total_frames = 24
    
    cx, cy = 200, 105 # Exactly centered
    r_outer = 54
    
    # Generate rotating angles
    for frame_idx in range(total_frames):
        # Create an 8-bit grayscale image
        img = Image.new('L', (w, h), 0)
        draw = ImageDraw.Draw(img)
        
        # 1. Draw a smooth radial gradient centered around the knob to trigger Floyd-Steinberg dithering
        for y in range(h):
            for x in range(w):
                dist_to_center = math.sqrt((x - cx)**2 + (y - cy)**2)
                # Base gradient + radial drop-off
                val = int(140 - dist_to_center * 0.7 - (y / h) * 30 + (x / w) * 20)
                val = max(10, min(240, val))
                img.putpixel((x, y), val)
                
        # 2. Draw a clean retro grid pattern (darks)
        for x in range(0, w, 16):
            draw.line([(x, 0), (x, h)], fill=25, width=1)
        for y in range(0, h, 16):
            draw.line([(0, y), (w, y)], fill=25, width=1)
            
        # 3. Draw Knob Base/Shadow
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=15, outline=60, width=3)
        draw.ellipse([cx - r_outer + 4, cy - r_outer + 4, cx + r_outer - 4, cy + r_outer - 4], fill=45, outline=100, width=2)
        
        # Draw Knob tick marks (270 degrees sweep)
        num_ticks = 11
        for i in range(num_ticks):
            angle_deg = 135 + (i * (270 / (num_ticks - 1)))
            angle_rad = math.radians(angle_deg)
            tx1 = cx + (r_outer + 6) * math.cos(angle_rad)
            ty1 = cy + (r_outer + 6) * math.sin(angle_rad)
            tx2 = cx + (r_outer + 12) * math.cos(angle_rad)
            ty2 = cy + (r_outer + 12) * math.sin(angle_rad)
            draw.line([(tx1, ty1), (tx2, ty2)], fill=180, width=2)

        # 4. Calculate current rotation angle
        # Starts at -135deg (7 o'clock), sweeps to +135deg (5 o'clock) and back
        cycle = frame_idx / total_frames
        # Smooth back-and-forth cosine interpolation
        factor = (1.0 - math.cos(cycle * 2 * math.pi)) / 2.0
        angle_deg = -135 + factor * 270
        angle_rad = math.radians(angle_deg - 90) # Adjust by 90deg offset
        
        # Draw indicator line & dot
        ix = cx + 38 * math.cos(angle_rad)
        iy = cy + 38 * math.sin(angle_rad)
        
        # Indicator line on knob cap
        draw.line([(cx, cy), (ix, iy)], fill=255, width=4)
        draw.ellipse([ix - 5, iy - 5, ix + 5, iy + 5], fill=255)
        
        # Center cap circle
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=20, outline=120, width=2)

        # 5. Apply Floyd-Steinberg 1-bit dithering
        dithered_frame = img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        
        # 6. Scale up to 1200x630 using Nearest Neighbor to keep retro pixel crunch
        final_frame = dithered_frame.resize((1200, 630), Image.Resampling.NEAREST)
        
        # Convert to RGB
        frames.append(final_frame.convert('RGB'))

    # Save animated GIF
    static_dir = "d:/crew/experiment/static/images"
    os.makedirs(static_dir, exist_ok=True)
    gif_path = os.path.join(static_dir, "dithered_knob_og.gif")
    
    # Save frame sequence
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=60, # ~16 FPS
        loop=0
    )
    print(f"Successfully generated unbranded animated dithered OG image at: {gif_path}")

if __name__ == "__main__":
    make_og_gif()
