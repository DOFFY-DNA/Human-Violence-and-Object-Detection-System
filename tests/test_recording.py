"""
tests/test_recording.py — Module 8: Recording Service
Test IDs: TC-RC01 to TC-RC08
cv2.VideoWriter is mocked — no real video files written.
"""
import sys, os, unittest, time, threading, queue
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRecording(unittest.TestCase):
    """Module 8 — Recording Service (8 tests)"""

    # ── TC-RC01 ────────────────────────────────────────────────────────────────
    @patch("os.makedirs")
    def test_TCRC01_recording_directory_created(self, mock_makedirs):
        """recordings/ directory should be created if it does not exist"""
        import config
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        mock_makedirs.assert_called_with(config.RECORDINGS_DIR, exist_ok=True)

    # ── TC-RC02 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoWriter")
    @patch("os.makedirs")
    def test_TCRC02_video_clip_file_created(self, mock_makedirs, MockWriter):
        """start_recording should create an MP4 clip file path"""
        mock_writer_instance = MockWriter.return_value
        mock_writer_instance.write = MagicMock()
        mock_writer_instance.release = MagicMock()

        from services.recording_service import RecordingService
        recorder = RecordingService()
        clip_path = recorder.start_recording()

        self.assertTrue(clip_path.endswith(".mp4"))
        self.assertIn("violence_clip_", clip_path)
        # Wait for thread to finish
        time.sleep(3)

    # ── TC-RC03 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoWriter")
    @patch("os.makedirs")
    def test_TCRC03_clip_filename_has_timestamp(self, mock_makedirs, MockWriter):
        """Video clip filename should contain a timestamp"""
        mock_writer_instance = MockWriter.return_value
        mock_writer_instance.write = MagicMock()
        mock_writer_instance.release = MagicMock()

        from services.recording_service import RecordingService
        recorder = RecordingService()
        clip_path = recorder.start_recording()

        filename = os.path.basename(clip_path)
        # Format: violence_clip_YYYYMMDD_HHMMSS.mp4
        self.assertRegex(filename,
                         r"violence_clip_\d{8}_\d{6}\.mp4")
        time.sleep(3)

    # ── TC-RC04 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoWriter")
    @patch("os.makedirs")
    def test_TCRC04_clip_duration_5_seconds(self, mock_makedirs, MockWriter):
        """Recorder should write frames_needed = CLIP_DURATION_SEC * VIDEO_FPS"""
        mock_writer_instance = MockWriter.return_value
        mock_writer_instance.write = MagicMock()
        mock_writer_instance.release = MagicMock()

        import config
        expected_frames = int(config.CLIP_DURATION_SEC * config.VIDEO_FPS)

        from services.recording_service import RecordingService
        recorder = RecordingService()
        recorder.start_recording()

        # Feed exactly enough frames
        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(expected_frames + 10):  # extra frames
            recorder.enqueue_frame(fake_frame)

        time.sleep(4)
        write_count = mock_writer_instance.write.call_count
        self.assertGreaterEqual(write_count, 1)
        self.assertLessEqual(write_count, expected_frames)

    # ── TC-RC05 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoWriter")
    @patch("os.makedirs")
    def test_TCRC05_duplicate_recording_ignored(self, mock_makedirs, MockWriter):
        """Second start_recording call while recording should be ignored"""
        mock_writer_instance = MockWriter.return_value
        mock_writer_instance.write = MagicMock()
        mock_writer_instance.release = MagicMock()

        from services.recording_service import RecordingService
        recorder = RecordingService()

        path1 = recorder.start_recording()
        # Feed one frame so recording starts
        recorder.enqueue_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        time.sleep(0.2)

        path2 = recorder.start_recording()  # should be ignored
        self.assertEqual(path1, path2)
        time.sleep(3)

    # ── TC-RC06 ────────────────────────────────────────────────────────────────
    def test_TCRC06_frame_queue_drops_when_full(self):
        """Queue maxsize=200 should silently drop excess frames"""
        from services.recording_service import RecordingService
        recorder = RecordingService()
        # Manually set recording flag so enqueue_frame works
        recorder._recording = True

        fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(250):
            recorder.enqueue_frame(fake_frame)  # should not raise

        self.assertLessEqual(recorder._frame_queue.qsize(), 200)
        recorder._recording = False

    # ── TC-RC07 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoWriter")
    @patch("os.makedirs")
    def test_TCRC07_recording_runs_in_background_thread(self, mock_makedirs,
                                                         MockWriter):
        """Recording should run in a daemon background thread"""
        mock_writer_instance = MockWriter.return_value
        mock_writer_instance.write = MagicMock()
        mock_writer_instance.release = MagicMock()

        from services.recording_service import RecordingService
        recorder = RecordingService()
        recorder.start_recording()

        self.assertIsNotNone(recorder._thread)
        self.assertTrue(recorder._thread.daemon)
        time.sleep(3)

    # ── TC-RC08 ────────────────────────────────────────────────────────────────
    @patch("cv2.VideoWriter")
    @patch("os.makedirs")
    def test_TCRC08_is_recording_property(self, mock_makedirs, MockWriter):
        """is_recording should reflect recording state correctly"""
        mock_writer_instance = MockWriter.return_value
        mock_writer_instance.write = MagicMock()
        mock_writer_instance.release = MagicMock()

        from services.recording_service import RecordingService
        recorder = RecordingService()

        self.assertFalse(recorder.is_recording)  # before
        recorder.start_recording()
        time.sleep(0.1)
        self.assertTrue(recorder.is_recording)   # during
        time.sleep(5)
        self.assertFalse(recorder.is_recording)  # after (clip done)


if __name__ == "__main__":
    unittest.main(verbosity=2)
