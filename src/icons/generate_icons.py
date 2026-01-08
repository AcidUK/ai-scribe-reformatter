"""Generate placeholder medical-themed system tray icons."""
from PIL import Image, ImageDraw
import os

def create_medical_cross_icon(size=64):
    """Create a medical cross icon with transparent background."""
    # Create image with transparent background
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Darker blue circular background for better contrast with badges
    margin = 4
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=(0, 70, 150, 255), outline=(0, 50, 120, 255), width=2)

    # White medical cross - made larger for better visibility
    cross_width = size // 2.5  # Increased from size // 3
    cross_thickness = size // 5  # Increased from size // 6
    center = size // 2

    # Horizontal bar
    draw.rectangle([center - cross_width // 2, center - cross_thickness // 2,
                    center + cross_width // 2, center + cross_thickness // 2],
                   fill=(255, 255, 255, 255))

    # Vertical bar
    draw.rectangle([center - cross_thickness // 2, center - cross_width // 2,
                    center + cross_thickness // 2, center + cross_width // 2],
                   fill=(255, 255, 255, 255))

    return image


def create_checkmark_badge(size=32):
    """Create a green checkmark badge overlay with black outline for visibility."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Black outer circle for contrast against blue background
    margin = 0
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=(0, 0, 0, 255))

    # Bright green inner circle - lighter shade for better contrast
    margin = 3
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=(50, 255, 50, 255), outline=(30, 200, 30, 255), width=2)

    # White checkmark
    padding = 8
    # Checkmark points
    points = [
        (padding, size // 2),
        (size // 3, size - padding - 2),
        (size - padding, padding)
    ]
    draw.line(points, fill=(255, 255, 255, 255), width=3)

    return image


def create_clock_badge(size=32):
    """Create a clock/timer badge overlay."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Orange circular background
    margin = 2
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=(255, 165, 0, 230), outline=(200, 120, 0, 255), width=2)

    # White clock hands
    center = size // 2
    # Hour hand (pointing to 2 o'clock)
    draw.line([center, center, center + 6, center - 8], fill=(255, 255, 255, 255), width=2)
    # Minute hand (pointing to 12)
    draw.line([center, center, center, center - 10], fill=(255, 255, 255, 255), width=2)
    # Center dot
    draw.ellipse([center-2, center-2, center+2, center+2], fill=(255, 255, 255, 255))

    return image


def create_error_badge(size=32):
    """Create a red error badge overlay."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Red circular background
    margin = 2
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=(220, 0, 0, 230), outline=(180, 0, 0, 255), width=2)

    # White X
    padding = 8
    draw.line([padding, padding, size - padding, size - padding],
              fill=(255, 255, 255, 255), width=3)
    draw.line([size - padding, padding, padding, size - padding],
              fill=(255, 255, 255, 255), width=3)

    return image


if __name__ == "__main__":
    # Get the directory where this script is located
    icons_dir = os.path.dirname(os.path.abspath(__file__))

    # Create icons
    print(f"Creating icons in {icons_dir}...")

    # Main medical cross icon
    main_icon = create_medical_cross_icon(64)
    main_icon.save(os.path.join(icons_dir, "main.png"))
    print("Created main.png (medical cross)")

    # Badge overlays
    badges = [
        ("badge_ready.png", create_checkmark_badge, "green checkmark"),
        ("badge_plan.png", create_clock_badge, "clock"),
        ("badge_error.png", create_error_badge, "red X"),
    ]

    for filename, create_func, description in badges:
        badge = create_func(32)
        badge.save(os.path.join(icons_dir, filename))
        print(f"Created {filename} ({description})")

    print("\nAll icons created successfully!")
    print("You can now replace these with custom designed icons if desired.")
