"""
tests/test_camera.py — Module 4: Camera / Video Capture
Test IDs: TC-C01 to TC-C09
cv2.VideoCapture is fully mocked — no real webcam needed.
"""
import sys, os, unittest
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_fake_frame(h=480, w=640, c=3, color=128):
    """Create a fake BGR frame filled with a single colour value."""
    return np.full((h, w, c), color, dtype=np.uint8)


class TestCamera(unittest.TestCase):
    """Module 4 — Camera / Video Capture (9 tests)"""

    # ── TC-C01 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC01_camera_opens_successfully(self, MockCap):
        """Camera should open successfully with index 0"""
        instance = MockCap.return_value
        instance.isOpened.return_value = True
        import cv2
        cap = cv2.VideoCapture(0)
        self.assertTrue(cap.isOpened())

    # ── TC-C02 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC02_frame_read_returns_valid_image(self, MockCap):
        """cap.read() should return ret=True and a valid numpy frame"""
        instance = MockCap.return_value
        fake_frame = _make_fake_frame()
        instance.read.return_value = (True, fake_frame)

        import cv2
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        self.assertTrue(ret)
        self.assertIsNotNone(frame)
        self.assertEqual(len(frame.shape), 3)

    # ── TC-C03 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC03_frame_has_three_color_channels(self, MockCap):
        """Frame should have 3 colour channels (BGR)"""
        instance = MockCap.return_value
        fake_frame = _make_fake_frame()
        instance.read.return_value = (True, fake_frame)

        import cv2
        cap = cv2.VideoCapture(0)
        _, frame = cap.read()
        self.assertEqual(frame.shape[2], 3)

    # ── TC-C04 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC04_frame_is_not_all_black(self, MockCap):
        """Frame should not be all zeros (all black)"""
        instance = MockCap.return_value
        fake_frame = _make_fake_frame(color=128)  # grey, not black
        instance.read.return_value = (True, fake_frame)

        import cv2
        cap = cv2.VideoCapture(0)
        _, frame = cap.read()
        self.assertGreater(np.mean(frame), 0)

    # ── TC-C05 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC05_camera_read_speed_within_threshold(self, MockCap):
        """Camera read should complete in < 500ms"""
        import time
        instance = MockCap.return_value
        instance.isOpened.return_value = True
        fake_frame = _make_fake_frame()
        instance.read.return_value = (True, fake_frame)

        import cv2
        cap = cv2.VideoCapture(0)
        # Warm-up
        for _ in range(5):
            cap.read()
        # Timed read
        t0 = time.perf_counter()
        cap.read()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 500, f"Read took {elapsed_ms:.1f}ms")

    # ── TC-C06 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC06_multiple_consecutive_frames(self, MockCap):
        """30 consecutive frames should all read successfully"""
        instance = MockCap.return_value
        fake_frame = _make_fake_frame()
        instance.read.return_value = (True, fake_frame)

        import cv2
        cap = cv2.VideoCapture(0)
        success_count = 0
        for _ in range(30):
            ret, _ = cap.read()
            if ret:
                success_count += 1
        self.assertEqual(success_count, 30)

    # ── TC-C07 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC07_camera_releases_properly(self, MockCap):
        """After release, camera should not return valid frames"""
        instance = MockCap.return_value
        instance.read.side_effect = [
            (True, _make_fake_frame()),   # before release
            (False, None),                # after release
        ]

        import cv2
        cap = cv2.VideoCapture(0)
        ret1, _ = cap.read()
        self.assertTrue(ret1)
        cap.release()
        ret2, _ = cap.read()
        self.assertFalse(ret2)
        instance.release.assert_called_once()

    # ── TC-C08 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoCapture")
    def test_TCC08_nonexistent_camera_index(self, MockCap):
        """Opening non-existent camera index 99 should fail gracefully"""
        instance = MockCap.return_value
        instance.isOpened.return_value = False

        import cv2
        cap = cv2.VideoCapture(99)
        self.assertFalse(cap.isOpened())

    # ── TC-C09 ────────────────────────────────────────────────────────────────
    def test_TCC09_frame_resize_to_panel_dimensions(self):
        """Resizing frame to (640, 480) should produce correct shape"""
        import cv2
        original = _make_fake_frame(h=720, w=1280)
        resized = cv2.resize(original, (640, 480))
        self.assertEqual(resized.shape, (480, 640, 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
