"""Tests for _is_valid_image upload validation (content verification)."""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from PIL import Image
import io

from .views import _is_valid_image


def make_image(fmt='PNG', size=(64, 64)):
    buffer = io.BytesIO()
    Image.new('RGB', size, (10, 200, 90)).save(buffer, format=fmt)
    buffer.seek(0)
    return buffer.read()


class IsValidImageTest(TestCase):
    def test_real_images_accepted(self):
        for fmt, ct in [('JPEG', 'image/jpeg'), ('PNG', 'image/png'), ('GIF', 'image/gif')]:
            with self.subTest(fmt=fmt):
                f = SimpleUploadedFile('photo.bin', make_image(fmt), content_type=ct)
                self.assertTrue(_is_valid_image(f))

    def test_disguised_html_rejected(self):
        f = SimpleUploadedFile(
            'evil.png', b'<html><script>alert(1)</script></html>',
            content_type='image/png',
        )
        self.assertFalse(_is_valid_image(f))

    def test_truncated_image_rejected(self):
        f = SimpleUploadedFile(
            'broken.png', make_image('PNG')[:40], content_type='image/png',
        )
        self.assertFalse(_is_valid_image(f))

    def test_svg_rejected_even_with_image_content_type(self):
        f = SimpleUploadedFile(
            'vector.png',
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            content_type='image/png',
        )
        self.assertFalse(_is_valid_image(f))

    def test_oversize_rejected(self):
        class FakeFile:
            size = 6 * 1024 * 1024
            content_type = 'image/png'
            name = 'big.png'
            def seek(self, pos):
                pass
        self.assertFalse(_is_valid_image(FakeFile()))

    def test_file_pointer_reset_after_validation(self):
        f = SimpleUploadedFile('photo.png', make_image('PNG'), content_type='image/png')
        self.assertTrue(_is_valid_image(f))
        self.assertEqual(f.read(1), b'\x89')  # PNG magic byte at position 0
