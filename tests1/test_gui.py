"""
tests/test_gui.py
GUI smoke tests — import checks, config validation, module-level tests.
─────────────────────────────────────────────────────────────────────────────
IMPORTANT: Tkinter is NOT thread-safe.
  All Tk window creation must happen on the MAIN thread only.
  These tests do NOT create windows in background threads to avoid the
  "Tcl_AsyncDelete: async handler deleted by the wrong thread" crash.
  Window-creation tests only run when called from the main thread directly.
─────────────────────────────────────────────────────────────────────────────
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import config

_is_main_thread = (threading := __import__("threading")).current_thread() is threading.main_thread


# ── Pytest-style tests ────────────────────────────────────────────────────────

def test_tkinter_importable():
    import tkinter as tk
    assert tk is not None

def test_pil_importable():
    try:
        from PIL import Image, ImageTk
        assert Image is not None
    except ImportError:
        pytest.skip("Pillow not installed — run: pip install pillow")

def test_theme_bg_is_hex():
    assert config.THEME_BG.startswith("#"), f"THEME_BG not a hex: {config.THEME_BG}"
    assert len(config.THEME_BG) == 7

def test_accent_is_hex():
    assert config.ACCENT.startswith("#")
    assert len(config.ACCENT) == 7

def test_accent2_is_hex():
    assert config.ACCENT2.startswith("#")
    assert len(config.ACCENT2) == 7

def test_font_main_is_tuple():
    assert isinstance(config.FONT_MAIN, tuple)
    assert len(config.FONT_MAIN) >= 2

def test_font_title_is_tuple():
    assert isinstance(config.FONT_TITLE, tuple)
    assert len(config.FONT_TITLE) >= 2

def test_font_mono_is_tuple():
    assert isinstance(config.FONT_MONO, tuple)
    assert len(config.FONT_MONO) >= 2

def test_login_window_module_importable():
    from gui import login_window
    assert hasattr(login_window, "LoginWindow")

def test_register_window_module_importable():
    from gui import register_window
    assert hasattr(register_window, "RegistrationWindow")

def test_admin_dashboard_module_importable():
    from gui import admin_dashboard
    assert hasattr(admin_dashboard, "AdminDashboard")

def test_widgets_module_importable():
    from gui import widgets
    assert hasattr(widgets, "styled_button")
    assert hasattr(widgets, "AlertBanner")

def test_integration_module_importable():
    from gui import Integration
    assert hasattr(Integration, "IntegrationWindow")

def test_pyautogui_importable():
    try:
        import pyautogui
        w, h = pyautogui.size()
        assert w > 0 and h > 0
    except ImportError:
        pytest.skip("pyautogui not installed — run: pip install pyautogui")

def test_app_title_defined():
    assert isinstance(config.APP_TITLE, str)
    assert len(config.APP_TITLE) > 0

def test_panel_dimensions_positive():
    assert config.PANEL_W > 0
    assert config.PANEL_H > 0

def test_login_window_builds_main_thread():
    """Only runs correctly on the main thread — safe to call from test_runner."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        from gui.login_window import LoginWindow
        lw = LoginWindow(root, on_success=lambda *a: None)
        assert lw is not None
    finally:
        root.destroy()

def test_register_window_builds_main_thread():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        from gui.register_window import RegistrationWindow
        rw = RegistrationWindow(root)
        assert rw is not None
    finally:
        root.destroy()

def test_alert_banner_builds_main_thread():
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    try:
        from gui.widgets import AlertBanner
        banner = AlertBanner(root)
        banner.show()
        banner.hide()
    finally:
        root.destroy()


# ── Manual runner ─────────────────────────────────────────────────────────────
def run_tests() -> list:
    """
    Safe manual runner: window-creation tests run ONLY if called
    from the main thread (e.g., via test_runner.py directly).
    When called from a background thread (dashboard), they are skipped.
    """
    import threading as _th
    on_main = _th.current_thread() is _th.main_thread()

    non_threaded = [
        ("Tkinter Importable",         test_tkinter_importable),
        ("Pillow Importable",          test_pil_importable),
        ("Theme BG Hex",               test_theme_bg_is_hex),
        ("Accent Color Hex",           test_accent_is_hex),
        ("Accent2 Color Hex",          test_accent2_is_hex),
        ("Font Main Tuple",            test_font_main_is_tuple),
        ("Font Title Tuple",           test_font_title_is_tuple),
        ("Font Mono Tuple",            test_font_mono_is_tuple),
        ("LoginWindow Importable",     test_login_window_module_importable),
        ("RegisterWindow Importable",  test_register_window_module_importable),
        ("AdminDashboard Importable",  test_admin_dashboard_module_importable),
        ("Widgets Importable",         test_widgets_module_importable),
        ("Integration Importable",     test_integration_module_importable),
        ("PyAutoGUI Importable",       test_pyautogui_importable),
        ("App Title Defined",          test_app_title_defined),
        ("Panel Dimensions > 0",       test_panel_dimensions_positive),
    ]

    # These create Tk windows — only safe on main thread
    main_thread_only = [
        ("LoginWindow Builds",         test_login_window_builds_main_thread),
        ("RegisterWindow Builds",      test_register_window_builds_main_thread),
        ("AlertBanner Builds",         test_alert_banner_builds_main_thread),
    ]

    results = []
    for name, fn in non_threaded:
        t0 = time.perf_counter()
        try:
            fn()
            status = "PASS"
        except pytest.skip.Exception as e:
            status = f"SKIP: {e}"
        except Exception as e:
            status = f"FAIL: {e}"
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        results.append((name, status, elapsed))

    for name, fn in main_thread_only:
        if not on_main:
            results.append((name, "SKIP: must run on main thread", 0.0))
            continue
        t0 = time.perf_counter()
        try:
            fn()
            status = "PASS"
        except Exception as e:
            status = f"FAIL: {e}"
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        results.append((name, status, elapsed))

    return results


if __name__ == "__main__":
    for name, status, ms in run_tests():
        print(f"[{status}] {name} ({ms}ms)")
