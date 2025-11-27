import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.views import MainView
from logic.ws_client import WSListener


def main():
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Rejestr zasobów")
    window.setFixedSize(800, 430)

    main_view = MainView(parent=window)
    window.setCentralWidget(main_view)

    window.show()

    def on_reload():
        main_view.reload_signal.emit()
    ws = WSListener(on_reload_callback=on_reload, uri="ws://127.0.0.1:8000/ws")
    ws.start()
    window.ws_listener = ws

    sys.exit(app.exec())


if __name__ == "__main__":
    main()