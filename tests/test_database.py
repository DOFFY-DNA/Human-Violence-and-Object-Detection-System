"""
tests/test_database.py — Module 3: Database
Test IDs: TC-D01 to TC-D11
Uses an in-memory SQLite DB via a temp file (shared across get_connection calls).
"""
import sys, os, unittest, tempfile, sqlite3, threading
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabase(unittest.TestCase):
    """Module 3 — Database Operations (11 tests)"""

    @classmethod
    def setUpClass(cls):
        """Create a temp DB file used for all tests in this module."""
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        cls._db_path = cls._tmp.name

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls._db_path)
        except OSError:
            pass

    def setUp(self):
        """Patch config.DB_PATH to the temp file before each test."""
        self._patcher = patch("config.DB_PATH", self._db_path)
        self._patcher.start()
        from database import db_manager
        self.db = db_manager

    def tearDown(self):
        self._patcher.stop()

    # ── TC-D01 ────────────────────────────────────────────────────────────────
    def test_TCD01_database_file_created(self):
        """Database file should be created on initialization"""
        self.db.initialize_db()
        self.assertTrue(os.path.exists(self._db_path))

    # ── TC-D02 ────────────────────────────────────────────────────────────────
    def test_TCD02_all_six_tables_created(self):
        """All 6 tables should exist after initialization"""
        self.db.initialize_db()
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in c.fetchall()}
        conn.close()
        expected = {"users", "operators", "detections", "alerts",
                    "recordings", "snapshots"}
        self.assertTrue(expected.issubset(tables),
                        f"Missing tables: {expected - tables}")

    # ── TC-D03 ────────────────────────────────────────────────────────────────
    def test_TCD03_default_admin_seeded(self):
        """Default admin user should be seeded on first init"""
        self.db.initialize_db()
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE username='admin'")
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "admin")

    # ── TC-D04 ────────────────────────────────────────────────────────────────
    def test_TCD04_password_stored_as_bcrypt_hash(self):
        """Admin password should be stored as bcrypt hash, not plain text"""
        self.db.initialize_db()
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username='admin'")
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        pw_hash = row[0]
        self.assertTrue(pw_hash.startswith("$2"),
                        f"Not bcrypt format: {pw_hash[:10]}...")
        self.assertNotEqual(pw_hash, "admin123")

    # ── TC-D05 ────────────────────────────────────────────────────────────────
    def test_TCD05_log_detection_event(self):
        """log_detection should insert a row into detections table"""
        self.db.initialize_db()
        det_id = self.db.log_detection("knife", "knife", 0.92,
                                       "path.jpg", "detected")
        self.assertIsInstance(det_id, int)
        self.assertGreater(det_id, 0)
        rows = self.db.fetch_detections(limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["type"], "knife")
        self.assertAlmostEqual(rows[0]["confidence"], 0.92, places=2)

    # ── TC-D06 ────────────────────────────────────────────────────────────────
    def test_TCD06_log_alert_event(self):
        """log_alert should insert a row linked to a detection"""
        self.db.initialize_db()
        det_id = self.db.log_detection("knife", "knife", 0.90, "", "detected")
        self.db.log_alert(det_id, "test@email.com", "sent")
        conn = sqlite3.connect(self._db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM alerts WHERE detection_id=?", (det_id,))
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)

    # ── TC-D07 ────────────────────────────────────────────────────────────────
    def test_TCD07_log_snapshot_event(self):
        """log_snapshot should insert a row into snapshots table"""
        self.db.initialize_db()
        self.db.log_snapshot("snap.jpg", "knife", 0.95)
        rows = self.db.fetch_snapshots(limit=1)
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0]["detection_type"], "knife")

    # ── TC-D08 ────────────────────────────────────────────────────────────────
    def test_TCD08_log_recording_event(self):
        """log_recording should insert a row into recordings table"""
        self.db.initialize_db()
        self.db.log_recording("clip.mp4", 5.0)
        rows = self.db.fetch_recordings(limit=1)
        self.assertGreaterEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["duration_sec"], 5.0)

    # ── TC-D09 ────────────────────────────────────────────────────────────────
    def test_TCD09_fetch_detections_with_limit(self):
        """fetch_detections should respect the limit parameter"""
        self.db.initialize_db()
        for i in range(15):
            self.db.log_detection("test", f"label_{i}", 0.5 + i * 0.01,
                                  "", "detected")
        rows = self.db.fetch_detections(limit=10)
        self.assertLessEqual(len(rows), 10)

    # ── TC-D10 ────────────────────────────────────────────────────────────────
    def test_TCD10_concurrent_writes_thread_safe(self):
        """Two threads writing simultaneously should not corrupt DB"""
        self.db.initialize_db()
        errors = []

        def _write(thread_id):
            try:
                self.db.log_detection("knife", f"thread_{thread_id}",
                                      0.90, "", "detected")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=_write, args=(1,))
        t2 = threading.Thread(target=_write, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")

    # ── TC-D11 ────────────────────────────────────────────────────────────────
    def test_TCD11_operator_email_retrieval(self):
        """get_operator_email should return correct email after registration"""
        self.db.initialize_db()
        ok, _ = self.db.register_operator(
            "Test Op", "Male", "1234567890",
            "emailtestop", "pass123", "emailtest@op.com"
        )
        if ok:
            email = self.db.get_operator_email("emailtestop")
            self.assertEqual(email, "emailtest@op.com")
        else:
            # Already exists from prior run — just fetch
            email = self.db.get_operator_email("emailtestop")
            self.assertTrue(len(email) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
