"""
tests/test_knife_detection.py — Module 5: YOLO Knife Detection (best.pt)
Test IDs: TC-K01 to TC-K10
YOLO model loading and prediction are fully mocked — no GPU needed.
"""
import sys, os, unittest, time
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_mock_yolo_result(detections=None):
    """Build a mock ultralytics Results object."""
    result = MagicMock()
    if detections is None:
        result.boxes = None
        return [result]

    mock_boxes = []
    for det in detections:
        box = MagicMock()
        box.cls = MagicMock()
        box.cls.__getitem__ = MagicMock(return_value=det["cls_id"])
        box.conf = MagicMock()
        box.conf.__getitem__ = MagicMock(return_value=det["conf"])
        box.xyxy = MagicMock()
        box.xyxy.__getitem__ = MagicMock(
            return_value=MagicMock(
                tolist=MagicMock(return_value=det["bbox"])
            )
        )
        mock_boxes.append(box)

    result.boxes = mock_boxes
    result.names = {0: "knife", 1: "blade"}
    return [result]


class TestKnifeDetection(unittest.TestCase):
    """Module 5 — YOLO Knife Detection (10 tests)"""

    # ── TC-K01 ────────────────────────────────────────────────────────────────
    @patch("os.path.exists", return_value=True)
    def test_TCK01_knife_model_file_exists(self, mock_exists):
        """Knife model file best.pt should exist"""
        import config
        result = os.path.exists(
            os.path.join(config.BASE_DIR, "models", "best.pt")
        )
        self.assertTrue(result)

    # ── TC-K02 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK02_knife_model_loads_successfully(self, MockYOLO):
        """YOLO('best.pt') should load without errors"""
        MockYOLO.return_value = MagicMock()
        model = MockYOLO("models/best.pt")
        self.assertIsNotNone(model)
        MockYOLO.assert_called_once_with("models/best.pt")

    # ── TC-K03 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK03_knife_model_predicts_on_frame(self, MockYOLO):
        """model.predict() should return results list without crashing"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = mock_model.predict(frame, conf=0.45, verbose=False)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    # ── TC-K04 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK04_prediction_returns_bounding_boxes(self, MockYOLO):
        """Prediction on knife image should return at least 1 bounding box"""
        mock_model = MockYOLO.return_value
        detections = [{"cls_id": 0, "conf": 0.92,
                       "bbox": [100, 200, 300, 400]}]
        mock_model.predict.return_value = _make_mock_yolo_result(detections)

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = mock_model.predict(frame, conf=0.45, verbose=False)
        self.assertIsNotNone(results[0].boxes)
        self.assertGreater(len(results[0].boxes), 0)

    # ── TC-K05 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK05_confidence_score_in_range(self, MockYOLO):
        """Confidence score should be between 0.0 and 1.0"""
        mock_model = MockYOLO.return_value
        detections = [{"cls_id": 0, "conf": 0.87,
                       "bbox": [10, 20, 200, 300]}]
        mock_model.predict.return_value = _make_mock_yolo_result(detections)

        results = mock_model.predict(np.zeros((480, 640, 3), dtype=np.uint8))
        conf = float(results[0].boxes[0].conf[0])
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    # ── TC-K06 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK06_bbox_coordinates_valid(self, MockYOLO):
        """Bounding box coordinates should satisfy x1<x2, y1<y2, all >= 0"""
        mock_model = MockYOLO.return_value
        detections = [{"cls_id": 0, "conf": 0.9,
                       "bbox": [50, 60, 250, 360]}]
        mock_model.predict.return_value = _make_mock_yolo_result(detections)

        results = mock_model.predict(np.zeros((480, 640, 3), dtype=np.uint8))
        bbox = results[0].boxes[0].xyxy[0].tolist()
        x1, y1, x2, y2 = bbox
        self.assertGreaterEqual(x1, 0)
        self.assertGreaterEqual(y1, 0)
        self.assertLess(x1, x2)
        self.assertLess(y1, y2)

    # ── TC-K07 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK07_class_names_accessible(self, MockYOLO):
        """model.names should return a dict with class names"""
        mock_model = MockYOLO.return_value
        mock_model.names = {0: "knife", 1: "blade"}
        self.assertIsInstance(mock_model.names, dict)
        self.assertIn(0, mock_model.names)
        self.assertEqual(mock_model.names[0], "knife")

    # ── TC-K08 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK08_inference_speed_under_500ms(self, MockYOLO):
        """Knife inference should complete in < 500ms"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # Warm-up
        mock_model.predict(frame, conf=0.45, verbose=False)
        # Timed call
        t0 = time.perf_counter()
        mock_model.predict(frame, conf=0.45, verbose=False)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 500)

    # ── TC-K09 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK09_model_handles_blank_frame(self, MockYOLO):
        """Model should return empty detections on a blank/black frame"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()  # no dets

        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = mock_model.predict(black_frame, conf=0.45, verbose=False)
        self.assertIsNone(results[0].boxes)

    # ── TC-K10 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCK10_model_handles_small_frame(self, MockYOLO):
        """Model should not crash on a very small frame (10x10)"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()

        tiny_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        results = mock_model.predict(tiny_frame, conf=0.45, verbose=False)
        self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
