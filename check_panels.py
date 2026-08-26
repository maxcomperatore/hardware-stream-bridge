import os
from PIL import Image

output_file = "d:/crew/experiment/panel_dimensions.txt"
panels_dir = "d:/crew/experiment/static/panels"

lines = []
for root, dirs, files in os.walk(panels_dir):
    for f in files:
        if f.endswith('.png'):
            path = os.path.join(root, f)
            try:
                with Image.open(path) as img:
                    rel_path = os.path.relpath(path, panels_dir)
                    lines.append(f"{rel_path}: size={img.size}, mode={img.mode}")
            except Exception as e:
                lines.append(f"{f}: error {e}")

with open(output_file, "w") as out:
    out.write("\n".join(lines))
print("Wrote panel_dimensions.txt")
