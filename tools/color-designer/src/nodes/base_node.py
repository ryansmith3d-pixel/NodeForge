from PySide6.QtWidgets import QGraphicsItem, QGraphicsSceneMouseEvent
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath

NODE_WIDTH = 180
HEADER_HEIGHT = 32
BODY_HEIGHT = 80
CORNER_RADIUS = 6

COLOR_BODY = QColor("#2e2e3a")
COLOR_HEADER = QColor("#3a3a4a")
COLOR_BORDER = QColor("#4a4a5a")
COLOR_BORDER_SELECTED = QColor("#7eb8f7")
COLOR_TITLE = QColor("#ccccdd")


class BaseNode(QGraphicsItem):
    """
    Phase A — empty node chrome.
    Drag from anywhere on the node (header-only drag wired in Phase B).
    """

    def __init__(self, title: str = "Node", pos: QPointF = QPointF(0.0, 0.0)):
        super().__init__()
        self.title = title

        self.setPos(pos)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

        self._width = NODE_WIDTH
        self._header_h = HEADER_HEIGHT
        self._body_h = BODY_HEIGHT

    # ── geometry ──────────────────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._header_h + self._body_h)

    def _node_path(self) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), CORNER_RADIUS, CORNER_RADIUS)
        return path

    def _header_path(self) -> QPainterPath:
        """Top-rounded, bottom-square header shape."""
        r = CORNER_RADIUS
        w = self._width
        h = self._header_h
        path = QPainterPath()
        path.moveTo(0, h)
        path.lineTo(0, r)
        path.arcTo(QRectF(0, 0, 2 * r, 2 * r), 180, -90)
        path.lineTo(w - r, 0)
        path.arcTo(QRectF(w - 2 * r, 0, 2 * r, 2 * r), 90, -90)
        path.lineTo(w, h)
        path.closeSubpath()
        return path

    # ── paint ─────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option, widget=None) -> None:
        selected = self.isSelected()

        # Body
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillPath(self._node_path(), QBrush(COLOR_BODY))

        # Header
        painter.fillPath(self._header_path(), QBrush(COLOR_HEADER))

        # Border
        border_color = COLOR_BORDER_SELECTED if selected else COLOR_BORDER
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self._node_path())

        # Title
        painter.setPen(QPen(COLOR_TITLE))
        font = QFont()
        font.setFamily("monospace")
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            QRectF(10, 0, self._width - 20, self._header_h),
            Qt.AlignVCenter | Qt.AlignLeft,
            self.title,
        )

    # ── interaction ───────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # Bring clicked node to front within its Z layer
        self.setZValue(1.0)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.setZValue(0.0)
        super().mouseReleaseEvent(event)
