"""
Watermark utility for adding Halal Korea branding to images.

This module provides functionality to apply diagonal tiled watermarks
combining logo and text to images.
"""

import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from django.conf import settings


def create_watermark_tile(size=(300, 100), opacity=128, watermark_width=None):
    """
    Create a watermark tile with logo and text.
    
    First tries to use custom watermark.png if available.
    Falls back to generating watermark from logo + text.
    
    Args:
        size: Tuple of (width, height) for the tile (used for generated watermark fallback)
        opacity: Alpha value for watermark (0-255)
        watermark_width: Width to resize watermark.png to (maintains aspect ratio), None = use original size
    
    Returns:
        PIL Image object with transparent background
    """
    # First, try to use custom watermark.png if it exists
    watermark_png_path = settings.BASE_DIR / 'static' / 'images' / 'watermark.png'
    
    if watermark_png_path.exists():
        try:
            # Load the custom watermark
            watermark = Image.open(watermark_png_path).convert('RGBA')
            
            # Resize if watermark_width is specified
            if watermark_width and watermark_width > 0:
                # Calculate height maintaining aspect ratio
                aspect_ratio = watermark.size[1] / watermark.size[0]
                new_height = int(watermark_width * aspect_ratio)
                watermark = watermark.resize((watermark_width, new_height), Image.Resampling.LANCZOS)
            
            # Apply opacity to the watermark
            # Split into RGBA channels
            r, g, b, a = watermark.split()
            
            # Adjust alpha channel with the specified opacity
            a = a.point(lambda p: int(p * opacity / 255))
            
            # Merge back
            watermark.putalpha(a)
            
            return watermark
        except Exception as e:
            print(f"Error loading watermark.png, falling back to generated watermark: {e}")
    
    # Fallback: Generate watermark from logo + text
    # Create transparent image
    tile = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    
    # Logo path (we'll use a PNG version or convert SVG)
    logo_path = settings.BASE_DIR / 'static' / 'images' / 'logo-square.svg'
    logo_png_path = settings.BASE_DIR / 'static' / 'images' / 'logo-square.png'
    
    # Check if PNG version exists, otherwise we'll work without logo for now
    logo = None
    if logo_png_path.exists():
        try:
            logo = Image.open(logo_png_path).convert('RGBA')
            # Resize logo to fit tile
            logo_size = (80, 80)
            logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
            # Apply opacity to logo
            logo_alpha = logo.split()[3]
            logo_alpha = ImageOps.autocontrast(logo_alpha)
            logo_alpha = logo_alpha.point(lambda p: int(p * opacity / 255))
            logo.putalpha(logo_alpha)
        except Exception as e:
            print(f"Error loading logo: {e}")
            logo = None
    
    # Add text
    text = "Halal Korea"
    
    # Try to use a nice font, fall back to default
    try:
        # Try common Korean-supporting fonts
        font_size = 32
        font = None
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            'C:\\Windows\\Fonts\\Arial.ttf',
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
                break
        
        if font is None:
            font = ImageFont.load_default()
    except Exception as e:
        print(f"Error loading font: {e}")
        font = ImageFont.load_default()
    
    # Get text bounding box
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback for older Pillow versions
        text_width, text_height = draw.textsize(text, font=font)
    
    # Position elements in tile
    x_offset = 10
    y_center = size[1] // 2
    
    # Paste logo if available
    if logo:
        logo_y = y_center - logo.size[1] // 2
        tile.paste(logo, (x_offset, logo_y), logo)
        x_offset += logo.size[0] + 10
    
    # Draw text with opacity
    text_y = y_center - text_height // 2
    text_color = (255, 255, 255, opacity)  # White with opacity
    draw.text((x_offset, text_y), text, fill=text_color, font=font)
    
    return tile


def apply_diagonal_watermark(
    image_path,
    output_path=None,
    tile_size=(300, 100),
    opacity=0.25,
    angle=-45,
    spacing=50,
    watermark_size=None
):
    """
    Apply diagonal tiled watermark to an image.
    
    Args:
        image_path: Path to input image
        output_path: Path to save watermarked image (None = overwrite)
        tile_size: Size of each watermark tile (width, height) - for generated watermark fallback
        opacity: Opacity of watermark (0.0 to 1.0)
        angle: Rotation angle in degrees (negative = clockwise)
        spacing: Space between tiles in pixels
        watermark_size: Width to resize watermark.png to (None = use setting or original size)
    
    Returns:
        Path to output image
    """
    # Convert opacity to 0-255 range
    alpha_value = int(opacity * 255)
    
    # Open source image
    img = Image.open(image_path).convert('RGBA')
    width, height = img.size
    
    # Get watermark size from settings if not specified
    if watermark_size is None:
        watermark_size = getattr(settings, 'WATERMARK_SIZE', None)
    
    # Create watermark tile
    watermark_tile = create_watermark_tile(size=tile_size, opacity=alpha_value, watermark_width=watermark_size)
    
    # Rotate the tile
    watermark_tile = watermark_tile.rotate(angle, expand=True)
    tile_width, tile_height = watermark_tile.size
    
    # Calculate how many tiles we need to cover the entire image
    # We need to cover the diagonal dimension
    diagonal = int(math.sqrt(width**2 + height**2))
    
    # Create overlay layer
    overlay = Image.new('RGBA', (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    
    # Tile the watermark across the overlay
    for y in range(0, diagonal * 2, tile_height + spacing):
        for x in range(0, diagonal * 2, tile_width + spacing):
            overlay.paste(watermark_tile, (x, y), watermark_tile)
    
    # Calculate offset to center the pattern
    offset_x = (overlay.size[0] - width) // 2
    offset_y = (overlay.size[1] - height) // 2
    
    # Crop overlay to match original image size
    overlay = overlay.crop((offset_x, offset_y, offset_x + width, offset_y + height))
    
    # Composite watermark onto original image
    watermarked = Image.alpha_composite(img, overlay)
    
    # Convert back to RGB if saving as JPEG
    if output_path is None:
        output_path = image_path
    
    output_ext = Path(output_path).suffix.lower()
    if output_ext in ['.jpg', '.jpeg']:
        watermarked = watermarked.convert('RGB')
    
    # Save result
    watermarked.save(output_path, quality=95)
    
    return output_path


def apply_watermark_to_uploaded_file(uploaded_file, opacity=None, angle=None, spacing=None, watermark_size=None):
    """
    Apply watermark to a Django UploadedFile.
    
    Args:
        uploaded_file: Django UploadedFile object
        opacity: Watermark opacity (uses settings default if None)
        angle: Rotation angle (uses settings default if None)
        spacing: Tile spacing (uses settings default if None)
        watermark_size: Width to resize watermark.png to (uses settings default if None)
    
    Returns:
        Watermarked image as PIL Image object
    """
    # Get settings with defaults
    if opacity is None:
        opacity = getattr(settings, 'WATERMARK_OPACITY', 0.25)
    if angle is None:
        angle = getattr(settings, 'WATERMARK_ANGLE', -45)
    if spacing is None:
        spacing = getattr(settings, 'WATERMARK_SPACING', 50)
    if watermark_size is None:
        watermark_size = getattr(settings, 'WATERMARK_SIZE', None)
    
    tile_size = getattr(settings, 'WATERMARK_TILE_SIZE', (300, 100))
    
    # Convert uploaded file to PIL Image
    img = Image.open(uploaded_file).convert('RGBA')
    width, height = img.size
    
    # Convert opacity to 0-255 range
    alpha_value = int(opacity * 255)
    
    # Create watermark tile
    watermark_tile = create_watermark_tile(size=tile_size, opacity=alpha_value, watermark_width=watermark_size)
    
    # Rotate the tile
    watermark_tile = watermark_tile.rotate(angle, expand=True)
    tile_width, tile_height = watermark_tile.size
    
    # Calculate how many tiles we need
    diagonal = int(math.sqrt(width**2 + height**2))
    
    # Create overlay layer
    overlay = Image.new('RGBA', (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    
    # Tile the watermark
    for y in range(0, diagonal * 2, tile_height + spacing):
        for x in range(0, diagonal * 2, tile_width + spacing):
            overlay.paste(watermark_tile, (x, y), watermark_tile)
    
    # Center and crop overlay
    offset_x = (overlay.size[0] - width) // 2
    offset_y = (overlay.size[1] - height) // 2
    overlay = overlay.crop((offset_x, offset_y, offset_x + width, offset_y + height))
    
    # Composite watermark onto original image
    watermarked = Image.alpha_composite(img, overlay)
    
    return watermarked

