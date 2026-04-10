import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QPushButton
from PySide6.QtCore import QPointF

from canvas import NodeGraphScene, NodeGraphView
from nodes.base_node import BaseNode
from nodes.swatch_node import SwatchNode

HERE = Path(__file__).parent


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Idiograph — Color Designer")
        self.setMinimumSize(900, 600)
        self.resize(1280, 800)

        self._scene = NodeGraphScene()
        self._view = NodeGraphView(self._scene)
        self.setCentralWidget(self._view)

        self._build_toolbar()
        self._seed_nodes()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        add_btn = QPushButton("+ Node")
        add_btn.clicked.connect(self._add_node)
        toolbar.addWidget(add_btn)

    def _seed_nodes(self) -> None:
        swatches = [
            SwatchNode("#7eb8f7", "node.selected", QPointF(0, 0)),
            SwatchNode("#2e2e3a", "node.default", QPointF(240, 0)),
            SwatchNode("#f7c948", "semantic.alert", QPointF(480, 0)),
        ]
        for node in swatches:
            self._scene.addItem(node)
        self._node_counter = 0

    def _add_node(self) -> None:
        self._node_counter += 1
        node = BaseNode(
            f"Node {self._node_counter}",
            QPointF(
                self._node_counter * 40 - 1000,
                self._node_counter * 20 - 400,
            ),
        )
        self._scene.addItem(node)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1a1a1f;
            color: #ccccdd;
        }
        QToolBar {
            background-color: #24242c;
            border-bottom: 1px solid #3a3a4a;
            padding: 4px;
            spacing: 4px;
        }
        QPushButton {
            background-color: #2e2e3a;
            color: #ccccdd;
            border: 1px solid #3a3a4a;
            border-radius: 3px;
            padding: 4px 12px;
        }
        QPushButton:hover {
            background-color: #3a3a4a;
        }
        QGraphicsView {
            border: none;
            background-color: #1a1a1f;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
