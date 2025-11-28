import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.views import MainView
from logic.ws_client import WSListener
from logic.config import SERVER_HOST, SERVER_PORT

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ws_listener: WSListener | None = None

    def closeEvent(self, event):
        if self.ws_listener is not None:
            try:
                self.ws_listener.stop()
            except Exception:
                pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Rejestr zasobów")
    window.setFixedSize(800, 430)

    main_view = MainView(parent=window)
    window.setCentralWidget(main_view)

    def on_reload():
        main_view.reload_signal.emit()
    ws = WSListener(on_reload_callback=on_reload)
    ws.start()
    window.ws_listener = ws

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()