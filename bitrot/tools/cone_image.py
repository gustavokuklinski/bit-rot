import os
import math
from PIL import Image

def create_soft_cone_texture(size=512, file_name="cone_light.png", asset_path="./"):
    """
    Generates a soft-edged radial and angular cone gradient image.
    Points to the RIGHT (0 degrees) so Pygame's rotate() works perfectly.
    """
    # Create a new black image in "L" (luminance/grayscale) mode
    image = Image.new("L", (size, size), 0)
    pixels = image.load()

    center_x = size / 2
    center_y = size / 2
    max_radius = size / 2

    # --- Cone Settings ---
    fov_degrees = 110.0           # The solid bright angle in the center
    blur_angle = 45.0             # How many degrees it takes to fade to completely black on the edges
    
    # INCREASED: Changed from 0.15 to 0.25 to make the player's circular vision much larger!
    peripheral_radius = size * 0.25 

    for y in range(size):
        for x in range(size):
            dx = x - center_x
            dy = y - center_y
            distance = math.hypot(dx, dy)

            if distance > max_radius:
                continue # leave black

            # 1. Radial falloff (distance from center)
            # Apply an ease-out curve for a smoother fade
            falloff = distance / max_radius
            radial_mult = max(0.0, 1.0 - (falloff ** 2))

            # 2. Angular falloff (the cone shape)
            angle_deg = abs(math.degrees(math.atan2(dy, dx)))
            
            half_fov = fov_degrees / 2.0
            if angle_deg <= half_fov:
                angle_mult = 1.0
            elif angle_deg <= half_fov + blur_angle:
                # Smooth ease-out fade for the angular edges
                ratio = (angle_deg - half_fov) / blur_angle
                angle_mult = max(0.0, 1.0 - (ratio ** 2))
            else:
                angle_mult = 0.0

            # 3. Peripheral vision (small circle in the center so player isn't completely blind behind)
            if distance < peripheral_radius:
                # Fade out the peripheral vision as it gets further from center
                p_ratio = distance / peripheral_radius
                p_mult = max(0.0, 1.0 - (p_ratio ** 2))
            else:
                p_mult = 0.0

            # Combine cone vision and peripheral vision
            final_mult = max(angle_mult * radial_mult, p_mult * radial_mult)

            # Set pixel (0-255)
            pixels[x, y] = int(255 * final_mult)

    # Ensure the full path exists
    full_path = os.path.join(asset_path, file_name)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    image.save(full_path)
    print(f"Successfully generated '{full_path}' ({size}x{size}) with a larger player sphere!")

# --- Run the function ---
if __name__ == "__main__":
    # Make sure this path matches where your game expects assets
    SPRITE_PATH = "./" 
    create_soft_cone_texture(file_name="cone_light.png", asset_path=os.path.join(SPRITE_PATH))