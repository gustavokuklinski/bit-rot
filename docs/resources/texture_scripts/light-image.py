import os
from PIL import Image, ImageDraw

def create_soft_light_texture(size=128, file_name="light.png", asset_path="./"):
    """
    Generates a soft-edged radial gradient image (white center, fading to black).
    """
    # Create a new black image in "L" (luminance/grayscale) mode
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)

    center_x = size // 2
    center_y = size // 2
    max_radius = size // 2

    # Draw concentric circles with decreasing brightness
    for radius in range(max_radius, 0, -1):
        # Calculate the brightness (alpha) based on the radius
        # This creates a smooth falloff (cosine curve)
        brightness = int(255 * (0.5 * (1 + (radius / max_radius) ** 0.5 * -1 + 1)))
        
        # Use a slightly softer curve for a better fade
        # (radius / max_radius) -> 1.0 (edge) to 0.0 (center)
        falloff = (radius / max_radius)
        # Apply an ease-out curve (x^2)
        brightness = int(255 * (1.0 - falloff**2))
        
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            fill=brightness
        )

    # Ensure the full path exists
    full_path = os.path.join(asset_path, file_name)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Save the final image
    # We save as "L" (grayscale) but Pygame will load it fine.
    # If you want transparency, change mode to "RGBA" and (brightness, brightness, brightness, brightness)
    image.save(full_path)
    
    print(f"Successfully generated '{full_path}' ({size}x{size})")

# --- Run the function ---
if __name__ == "__main__":
    # Make sure this path matches where your game expects 'ui/light.png'
    # Based on your assets file, it seems to be 'game/sprites/ui/'
    SPRITE_PATH = "./" 
    create_soft_light_texture(file_name="light.png", asset_path=os.path.join(SPRITE_PATH, "ui"))
