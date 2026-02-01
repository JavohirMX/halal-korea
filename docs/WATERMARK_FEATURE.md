# Halal Korea Watermark Feature

## Overview

The watermark feature automatically applies a diagonal tiled "Halal Korea" branding watermark to all uploaded place images. This protects your content and maintains brand identity across all user-submitted photos.

## Features

### 1. Automatic Watermarking
- All new image uploads to `PlaceImageSuggestion` are automatically watermarked
- Original images are preserved in the `original_image` field
- Watermarked versions are stored in the `image` field

### 2. Admin Controls
- **Before/After Preview**: Side-by-side comparison of original and watermarked images
- **Watermark Status Indicator**: Shows which images have been watermarked
- **Bulk Actions**:
  - Apply watermark to existing images (for images uploaded before this feature)
  - Reapply watermark with current settings (to update watermark style)

### 3. Customizable Settings
Configure watermark appearance in `config/settings.py` or `.env`:

```python
WATERMARK_ENABLED = True          # Enable/disable watermarking
WATERMARK_OPACITY = 0.25          # 0.0 to 1.0 (25% opacity)
WATERMARK_ANGLE = -45             # Rotation angle (negative = clockwise)
WATERMARK_SPACING = 50            # Pixels between tiles
WATERMARK_TEXT = "Halal Korea"    # Watermark text
WATERMARK_TEXT_SIZE = 32          # Font size
```

## Testing the Watermark Feature

### Step 1: Test with Command Line Tool

The easiest way to test the watermark is using the management command:

```bash
# Activate virtual environment
source .venv/bin/activate

# Test on a sample image
python manage.py test_watermark path/to/your/image.jpg

# Test with custom settings
python manage.py test_watermark path/to/image.jpg --opacity 0.3 --angle -45 --spacing 40
```

**Output**: Watermarked images will be saved to `media/watermark_test/` directory.

### Step 2: Apply Migration

Before using the feature with the admin interface:

```bash
source .venv/bin/activate
python manage.py migrate places
```

This adds the `original_image` field to store non-watermarked versions.

### Step 3: Test with Admin Interface

1. **Upload a new image suggestion**:
   - Navigate to Django Admin → Places → Place Image Suggestions
   - Click "Add Place Image Suggestion"
   - Upload an image
   - The watermark will be applied automatically on save

2. **View watermark comparison**:
   - Open any Place Image Suggestion in the admin
   - Scroll to the "Images" section
   - You'll see a side-by-side comparison of original and watermarked images

3. **Apply watermark to existing images**:
   - Go to Place Image Suggestions list
   - Select images without watermarks (marked with ⚠ No watermark)
   - From Actions dropdown, select "💧 Apply watermark to selected images"
   - Click "Go"

4. **Reapply watermark** (to update watermark style after changing settings):
   - Select watermarked images
   - From Actions dropdown, select "🔄 Reapply watermark with current settings"
   - Click "Go"

### Step 4: Test Different Watermark Styles

You can experiment with different watermark appearances:

**Light watermark (more subtle)**:
```python
WATERMARK_OPACITY = 0.15
WATERMARK_SPACING = 80
```

**Strong watermark (more visible)**:
```python
WATERMARK_OPACITY = 0.4
WATERMARK_SPACING = 30
```

**Diagonal pattern**:
```python
WATERMARK_ANGLE = -45  # Default
```

**Horizontal pattern**:
```python
WATERMARK_ANGLE = 0
```

After changing settings, use the "Reapply watermark" action to update existing images.

## How It Works

### Architecture

1. **Upload Flow**:
   ```
   User uploads image → PlaceImageSuggestion.save()
   → Save original to original_image field
   → Apply watermark using utils/watermark.py
   → Save watermarked version to image field
   ```

2. **Watermark Application**:
   - Creates a tile with logo + "Halal Korea" text
   - Rotates the tile to specified angle
   - Tiles it diagonally across the entire image
   - Composites with specified opacity

### File Structure

```
places/
├── models.py                  # PlaceImageSuggestion with auto-watermarking
└── admin.py                   # Admin interface with preview and actions

utils/
├── watermark.py              # Core watermarking functions
└── management/commands/
    └── test_watermark.py     # Testing command

config/
└── settings.py               # Watermark configuration

media/
├── place_suggestions/        # Watermarked images
│   └── originals/           # Original images (backup)
└── watermark_test/          # Test outputs
```

## Customization

### Using a Different Logo

The watermark uses `static/images/logo-square.png`. To use a different logo:

1. Replace the file at `static/images/logo-square.png`
2. Or modify `utils/watermark.py` to point to your logo:
   ```python
   logo_png_path = settings.BASE_DIR / 'path' / 'to' / 'your' / 'logo.png'
   ```

### Custom Watermark Function

For advanced customization, modify the `create_watermark_tile()` function in `utils/watermark.py`:

- Change text positioning
- Add additional text elements
- Adjust colors
- Modify logo size or position

## Troubleshooting

### Watermark not appearing
- Check that `WATERMARK_ENABLED = True` in settings
- Verify the logo file exists at `static/images/logo-square.png`
- Check logs for any errors during watermark application

### Images not uploading
- Check that the `media/place_suggestions/` directory exists and is writable
- Verify Pillow is installed: `pip list | grep Pillow`
- Check Django logs for detailed error messages

### Testing shows errors
- Ensure you've activated the virtual environment: `source .venv/bin/activate`
- Run migrations: `python manage.py migrate`
- Check that all dependencies are installed: `pip install -r requirements.txt`

## Performance Notes

- Watermarking happens during image upload (one-time processing)
- Original images are preserved for potential re-watermarking
- Processing time depends on image size (typically < 1 second per image)
- Watermarked images are slightly larger than originals due to PNG transparency

## Future Enhancements

Potential improvements for future versions:

1. **Batch Processing**: Background task queue for bulk watermarking
2. **Advanced Settings UI**: Admin interface to preview and adjust settings
3. **Multiple Watermark Styles**: Presets for different use cases
4. **Position Control**: Choose corner, center, or custom positioning
5. **Conditional Watermarking**: Apply different watermarks based on category

## Security Considerations

- Original images are stored separately to allow re-processing if needed
- Only authenticated admin users can reapply or remove watermarks
- Watermarked images are public but branded, protecting your content

## Related Files

- Core implementation: `utils/watermark.py`
- Model integration: `places/models.py` (PlaceImageSuggestion)
- Admin interface: `places/admin.py` (PlaceImageSuggestionAdmin)
- Settings: `config/settings.py` (WATERMARK_* settings)
- Testing command: `utils/management/commands/test_watermark.py`
- Migration: `places/migrations/0005_placeimagesuggestion_original_image_and_more.py`

