from pathlib import Path
from django.test import SimpleTestCase


class IconUtilityOrderTests(SimpleTestCase):
    def test_icon_defaults_precede_tailwind_display_utilities(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / 'places/templates/places/base.html').read_text()
        self.assertLess(source.index("css/fontawesome-subset.css"), source.index("css/tailwind.build.css"))
