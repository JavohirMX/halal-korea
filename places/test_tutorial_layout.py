"""Guard the viewport positioning contract used by the mobile tutorial."""
from pathlib import Path
from django.test import SimpleTestCase


class TutorialLayoutTests(SimpleTestCase):
    def test_popover_uses_viewport_coordinates(self):
        source = (Path(__file__).parent / 'templates/places/explore.html').read_text()
        css = source.split('#tutorial-popover {', 1)[1].split('}', 1)[0]
        self.assertIn('position: fixed;', css)
        self.assertIn('this.popover.style.top = `${popoverTop}px`;', source)
        self.assertNotIn('`${popoverTop + window.scrollY}px`', source)

    def test_vertical_position_is_clamped(self):
        source = (Path(__file__).parent / 'templates/places/explore.html').read_text()
        self.assertIn('popoverTop = Math.max(margin, Math.min(', source)
        self.assertIn('window.innerHeight - popoverRect.height - margin', source)
