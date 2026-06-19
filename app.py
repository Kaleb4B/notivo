import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from ui.splash_screen import SplashScreen
from PySide6.QtCore import QTimer
from utils.logger import logger
from utils.config import config, get_resource_path

SETUP_MARKER = Path.home() / ".notivo" / "setup_complete"


def main():
    logger.info("Starting Notivo application...")
    app = QApplication(sys.argv)
    app.setApplicationName("Notivo")
    app.setApplicationDisplayName("Notivo")
    icon_path = get_resource_path("assets/logo.png")
    app.setWindowIcon(QIcon(icon_path))

    # ── First-run check ────────────────────────────────────────
    if not SETUP_MARKER.exists():
        logger.info("First run detected — showing Setup Wizard.")
        from ui.setup_wizard import SetupWizard
        wizard = SetupWizard()
        result = wizard.exec()
        # If user closed wizard without finishing, exit gracefully
        if not SETUP_MARKER.exists():
            logger.info("Setup wizard closed before completion. Exiting.")
            sys.exit(0)

    # ── Normal launch: splash → main window ───────────────────
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    splash.showMessage("Initializing configuration...")

    # We need a reference to main_window that persists
    main_window_ref = []
    launched = [False]

    def launch_app():
        if launched[0]:
            return
        launched[0] = True
        main_window = MainWindow()
        main_window_ref.append(main_window)
        main_window.show()
        splash.close()

    splash.skip_clicked.connect(launch_app)

    def update_splash(i):
        splash.progress.setValue(i)
        if i == 50:
            splash.showMessage("Loading UI components...")

        if i < 100:
            # 15ms * 100 = 1.5 seconds
            QTimer.singleShot(15, lambda: update_splash(i + 1))
        else:
            splash.showMessage("Application ready!")
            splash.progress.hide()
            launch_app()

    # Start the async splash screen update
    update_splash(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
