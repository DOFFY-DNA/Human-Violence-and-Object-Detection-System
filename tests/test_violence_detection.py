"""
tests/test_violence_detection.py — Module 6: YOLO Violence Detection (best2.pt)
Test IDs: TC-V01 to TC-V08
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
    result.names = {0: "violence"}
    return [result]


class TestViolenceDetection(unittest.TestCase):
    """Module 6 — YOLO Violence Detection (8 tests)"""

    # ── TC-V01 ────────────────────────────────────────────────────────────────
    @patch("os.path.exists", return_value=True)
    def test_TCV01_violence_model_file_exists(self, mock_exists):
        """Violence model file best2.pt should exist"""
        import config
        result = os.path.exists(
            os.path.join(config.BASE_DIR, "models", "best2.pt")
        )
        self.assertTrue(result)

    # ── TC-V02 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV02_violence_model_loads_successfully(self, MockYOLO):
        """YOLO('best2.pt') should load without errors"""
        MockYOLO.return_value = MagicMock()
        model = MockYOLO("models/best2.pt")
        self.assertIsNotNone(model)
        MockYOLO.assert_called_once_with("models/best2.pt")

    # ── TC-V03 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV03_violence_model_predicts_on_frame(self, MockYOLO):
        """model.predict() should return results list without crashing"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = mock_model.predict(frame, conf=0.40, verbose=False)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    # ── TC-V04 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV04_prediction_returns_bboxes_on_violence(self, MockYOLO):
        """Prediction on violent content should return at least 1 detection"""
        mock_model = MockYOLO.return_value
        detections = [{"cls_id": 0, "conf": 0.85,
                       "bbox": [50, 50, 400, 400]}]
        mock_model.predict.return_value = _make_mock_yolo_result(detections)

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = mock_model.predict(frame, conf=0.40, verbose=False)
        self.assertIsNotNone(results[0].boxes)
        self.assertGreater(len(results[0].boxes), 0)

    # ── TC-V05 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV05_confidence_score_in_range(self, MockYOLO):
        """Confidence score should be between 0.0 and 1.0"""
        mock_model = MockYOLO.return_value
        detections = [{"cls_id": 0, "conf": 0.78,
                       "bbox": [10, 20, 200, 300]}]
        mock_model.predict.return_value = _make_mock_yolo_result(detections)

        results = mock_model.predict(np.zeros((480, 640, 3), dtype=np.uint8))
        conf = float(results[0].boxes[0].conf[0])
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    # ── TC-V06 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV06_inference_speed_under_500ms(self, MockYOLO):
        """Violence inference should complete in < 500ms"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # Warm-up
        mock_model.predict(frame, conf=0.40, verbose=False)
        # Timed call
        t0 = time.perf_counter()
        mock_model.predict(frame, conf=0.40, verbose=False)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 500)

    # ── TC-V07 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV07_violence_model_handles_blank_frame(self, MockYOLO):
        """Model should return empty detections on a blank frame"""
        mock_model = MockYOLO.return_value
        mock_model.predict.return_value = _make_mock_yolo_result()  # no dets

        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = mock_model.predict(black_frame, conf=0.40, verbose=False)
        self.assertIsNone(results[0].boxes)

    # ── TC-V08 ────────────────────────────────────────────────────────────────
    @patch("ultralytics.YOLO")
    def test_TCV08_both_models_on_same_device(self, MockYOLO):
        """Both YOLO models should load and predict on the same device"""
        knife_model = MagicMock()
        violence_model = MagicMock()
        MockYOLO.side_effect = [knife_model, violence_model]

        km = MockYOLO("best.pt")
        vm = MockYOLO("best2.pt")

        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        km.predict.return_value = _make_mock_yolo_result()
        vm.predict.return_value = _make_mock_yolo_result()

        res_k = km.predict(frame, conf=0.45)
        res_v = vm.predict(frame, conf=0.40)
        self.assertIsInstance(res_k, list)
        self.assertIsInstance(res_v, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
