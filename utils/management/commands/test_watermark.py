"""
Management command to test watermark functionality on images.
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from utils.watermark import apply_diagonal_watermark


class Command(BaseCommand):
    help = 'Test watermark functionality by applying watermark to an image'

    def add_arguments(self, parser):
        parser.add_argument(
            'image_path',
            type=str,
            help='Path to the image file to watermark'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output path for watermarked image (default: media/watermark_test/)',
            default=None
        )
        parser.add_argument(
            '--opacity',
            type=float,
            help='Watermark opacity (0.0 to 1.0)',
            default=None
        )
        parser.add_argument(
            '--angle',
            type=int,
            help='Rotation angle in degrees (negative = clockwise)',
            default=None
        )
        parser.add_argument(
            '--spacing',
            type=int,
            help='Space between tiles in pixels',
            default=None
        )
        parser.add_argument(
            '--size',
            type=int,
            help='Watermark width in pixels (height auto-scales)',
            default=None
        )

    def handle(self, *args, **options):
        """Apply watermark to the specified image"""
        
        image_path = options['image_path']
        output_path = options['output']
        opacity = options['opacity']
        angle = options['angle']
        spacing = options['spacing']
        watermark_size = options['size']
        
        # Validate input file exists
        if not os.path.exists(image_path):
            raise CommandError(f'Image file not found: {image_path}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Testing watermark on: {image_path}')
        )
        
        # Get settings or use defaults
        if opacity is None:
            opacity = settings.WATERMARK_OPACITY
        if angle is None:
            angle = settings.WATERMARK_ANGLE
        if spacing is None:
            spacing = settings.WATERMARK_SPACING
        if watermark_size is None:
            watermark_size = getattr(settings, 'WATERMARK_SIZE', None)
        
        self.stdout.write(f'Settings:')
        self.stdout.write(f'  - Opacity: {opacity}')
        self.stdout.write(f'  - Angle: {angle}°')
        self.stdout.write(f'  - Spacing: {spacing}px')
        if watermark_size:
            self.stdout.write(f'  - Size: {watermark_size}px width')
        
        # Determine output path
        if output_path is None:
            # Create default output directory
            output_dir = settings.MEDIA_ROOT / 'watermark_test'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate output filename
            input_filename = Path(image_path).name
            input_stem = Path(image_path).stem
            input_ext = Path(image_path).suffix
            output_filename = f'{input_stem}_watermarked{input_ext}'
            output_path = output_dir / output_filename
        
        try:
            # Apply watermark
            self.stdout.write('Applying watermark...')
            result_path = apply_diagonal_watermark(
                image_path=image_path,
                output_path=str(output_path),
                opacity=opacity,
                angle=angle,
                spacing=spacing,
                watermark_size=watermark_size
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Watermark applied successfully!')
            )
            self.stdout.write(f'Original: {image_path}')
            self.stdout.write(f'Watermarked: {result_path}')
            
            # Show file sizes
            original_size = os.path.getsize(image_path) / 1024  # KB
            watermarked_size = os.path.getsize(result_path) / 1024  # KB
            
            self.stdout.write(f'\nFile sizes:')
            self.stdout.write(f'  - Original: {original_size:.2f} KB')
            self.stdout.write(f'  - Watermarked: {watermarked_size:.2f} KB')
            
        except Exception as e:
            raise CommandError(f'Error applying watermark: {str(e)}')
        
        self.stdout.write(
            self.style.SUCCESS('\n📝 Configuration:')
        )
        self.stdout.write('  Adjust watermark settings in config/settings.py or .env file:')
        self.stdout.write('  - WATERMARK_ENABLED (default: True)')
        self.stdout.write('  - WATERMARK_OPACITY (default: 0.25)')
        self.stdout.write('  - WATERMARK_ANGLE (default: -45)')
        self.stdout.write('  - WATERMARK_SPACING (default: 50)')
        self.stdout.write('  - WATERMARK_SIZE (default: 200, watermark width in pixels)')

