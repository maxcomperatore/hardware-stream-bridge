import math
import os
from PIL import Image, ImageDraw

def make_og_gif():
    # 400x210 design resolution (will be scaled up 3x to 1200x630 with nearest neighbor)
    w, h = 400, 210
    frames = []
    
    # 32 frame loop for ultra-smooth animation
    total_frames = 32
    
    cx, cy = 200, 105 # Centered
    r_outer = 56
    
    # Generate rotating angles
    for frame_idx in range(total_frames):
        # Create an 8-bit grayscale image
        img = Image.new('L', (w, h), 0)
        draw = ImageDraw.Draw(img)
        
        # Calculate current rotation angle
        # Starts at -135deg (7 o'clock), sweeps to +135deg (5 o'clock) and back
        cycle = frame_idx / total_frames
        factor = (1.0 - math.cos(cycle * 2 * math.pi)) / 2.0
        angle_deg = -135 + factor * 270
        angle_rad = math.radians(angle_deg - 90) # 90deg offset
        
        # 1. Draw a smooth radial gradient centered around the knob to trigger Floyd-Steinberg dithering
        # We animate the brightness/glow in sync with the knob position to make the light "pulse"!
        glow_pulse = int(factor * 30)
        for y in range(h):
            for x in range(w):
                dist_to_center = math.sqrt((x - cx)**2 + (y - cy)**2)
                # Pulse the background gradient based on knob value
                val = int(135 + glow_pulse - dist_to_center * 0.65 - (y / h) * 20 + (x / w) * 15)
                val = max(10, min(245, val))
                img.putpixel((x, y), val)
                
        # 2. Draw a clean retro grid pattern (darks)
        for x in range(0, w, 16):
            draw.line([(x, 0), (x, h)], fill=25, width=1)
        for y in range(0, h, 16):
            draw.line([(0, y), (w, y)], fill=25, width=1)

        # 3. Draw an animated Oscilloscope Waveform reacting to the knob position!
        # The wave morphs from a Sine wave -> Triangle -> Sawtooth -> Square wave as the knob turns.
        wave_pts = []
        for wx in range(10, w - 10, 2):
            # Phase shifts continuously over frames to create a scrolling wave effect
            phase = cycle * 2 * math.pi * 2 + (wx * 0.05)
            
            # Knob factor dictates the mix of wave shapes
            # Lower factor = Sine wave; Higher factor = Complex square/saw harmonics
            if factor < 0.35:
                # Morph: Flat line to pure Sine
                amp = factor * 40
                wy = cy + amp * math.sin(phase)
            elif factor < 0.7:
                # Morph: Sine to Sawtooth
                amp = factor * 40
                t = (phase / (2 * math.pi)) % 1.0
                saw = 2.0 * (t - 0.5)
                # Blend sine and saw
                blend = (factor - 0.35) / 0.35
                wy = cy + amp * ((1 - blend) * math.sin(phase) + blend * saw)
            else:
                # Morph: Sawtooth to Square wave
                amp = factor * 40
                square = 1.0 if math.sin(phase) >= 0 else -1.0
                blend = (factor - 0.7) / 0.3
                wy = cy + amp * ((1 - blend) * math.sin(phase * 1.5) + blend * square)
                
            # Make the waveform dip/attenuate near the physical knob so it looks like it runs "under" it
            dist_to_knob = abs(wx - cx)
            if dist_to_knob < r_outer + 30:
                attenuation = max(0.0, min(1.0, (dist_to_knob - r_outer - 5) / 25.0))
                wy = cy + (wy - cy) * attenuation
                
            wave_pts.append((wx, wy))
            
        # Draw the oscilloscope wave with a thick bright line
        for i in range(len(wave_pts) - 1):
            draw.line([wave_pts[i], wave_pts[i+1]], fill=220, width=2)
            
        # 4. Draw Knob Shadow & Outer ring
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=15, outline=70, width=3)
        draw.ellipse([cx - r_outer + 4, cy - r_outer + 4, cx + r_outer - 4, cy + r_outer - 4], fill=50, outline=110, width=2)
        
        # 5. Draw 3D Ribs/Grooves on the knob perimeter that rotate with the angle!
        # This makes the knob rotation feel physical and tangible.
        num_ribs = 36
        for r_idx in range(num_ribs):
            rib_angle_deg = (r_idx * (360 / num_ribs)) + angle_deg
            rib_angle_rad = math.radians(rib_angle_deg)
            # Only draw ribs that are on the front/sides to give 3D depth shading
            cos_val = math.cos(rib_angle_rad - math.radians(90))
            rx = cx + (r_outer - 1) * math.cos(rib_angle_rad)
            ry = cy + (r_outer - 1) * math.sin(rib_angle_rad)
            rx2 = cx + (r_outer - 4) * math.cos(rib_angle_rad)
            ry2 = cy + (r_outer - 4) * math.sin(rib_angle_rad)
            
            # Shadow ribs vs highlight ribs based on angle to lightsource (top-left)
            rib_fill = 255 if cos_val > 0.3 else 30
            draw.line([(rx, ry), (rx2, ry2)], fill=rib_fill, width=1)

        # 6. Draw Knob tick marks (270 degrees sweep)
        num_ticks = 11
        for i in range(num_ticks):
            tick_angle_deg = 135 + (i * (270 / (num_ticks - 1)))
            tick_angle_rad = math.radians(tick_angle_deg)
            tx1 = cx + (r_outer + 6) * math.cos(tick_angle_rad)
            ty1 = cy + (r_outer + 6) * math.sin(tick_angle_rad)
            tx2 = cx + (r_outer + 12) * math.cos(tick_angle_rad)
            ty2 = cy + (r_outer + 12) * math.sin(tick_angle_rad)
            draw.line([(tx1, ty1), (tx2, ty2)], fill=180, width=2)

        # 7. Draw indicator line & dot
        ix = cx + 38 * math.cos(angle_rad)
        iy = cy + 38 * math.sin(angle_rad)
        
        # Indicator line on knob cap
        draw.line([(cx, cy), (ix, iy)], fill=255, width=4)
        draw.ellipse([ix - 5, iy - 5, ix + 5, iy + 5], fill=255)
        
        # Center cap circle (3D bevel)
        draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=20, outline=130, width=2)
        draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=45, outline=90, width=1)

        # 8. Apply Floyd-Steinberg 1-bit dithering
        dithered_frame = img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        
        # 9. Scale up to 1200x630 using Nearest Neighbor to keep retro pixel crunch
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
        duration=50, # ~20 FPS for silky-smooth animation
        loop=0
    )
    print(f"Successfully generated UPGRADED animated dithered OG image at: {gif_path}")

if __name__ == "__main__":
    make_og_gif()
