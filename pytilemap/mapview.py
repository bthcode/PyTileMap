from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QGraphicsView

from pytilemap.mapscene import MapGraphicsScene
from pytilemap.qtsupport import wheelAngleDelta

from pytilemap.maptilesources.maptilesourceosm import MapTileSourceOSM

class MapGraphicsView(QGraphicsView):
    """Graphics view for showing a slippy map.
    """
    #request_tile = Signal(int, int, int, str)
    #setAimpoint = Signal(int, int, int)


    def __init__(self, 
                 tile_cache_dir:str = 'cache', 
                 tile_url_template:str="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                 parent=None):
        """Constructor.

        Args:
            tileSource(MapTileSource): Source for the tiles, default `MapTileSourceOSM`.
            parent(QObject): Parent object, default `None`
        """
        QGraphicsView.__init__(self, parent=parent)
        tileSource = MapTileSourceOSM()
        
        scene = MapGraphicsScene(tileSource)
        self.setScene(scene)
        self._lastMousePos = None

    @Slot()
    def close(self):
        self.scene().close()
        QGraphicsView.close(self)

    def resizeEvent(self, event):
        """Resize the widget. Reimplemented from `QGraphicsView`.

        Resize the `MapGraphicsScene`.

        Args:
            event(QResizeEvent): Resize event.
        """
        QGraphicsView.resizeEvent(self, event)
        size = event.size()
        self.scene().setSize(size.width(), size.height())

    def mousePressEvent(self, event):
        """Manage the mouse pressing.

        Args:
            event(QMouseEvent): Mouse event.
        """
        QGraphicsView.mousePressEvent(self, event)
        if event.buttons() == Qt.LeftButton:
            self._lastMousePos = event.pos()

    def mouseMoveEvent(self, event):
        """Manage the mouse movement while it is pressed.

        Args:
            event(QMouseEvent): Mouse event.
        """
        QGraphicsView.mouseMoveEvent(self, event)
        if event.buttons() == Qt.LeftButton:
            delta = self._lastMousePos - event.pos()
            self._lastMousePos = event.pos()
            self.scene().translate(delta.x(), delta.y())

    def mouseReleaseEvent(self, event):
        """Manage the mouse releasing.

        Args:
            event(QMouseEvent): Mouse event.
        """
        QGraphicsView.mouseReleaseEvent(self, event)

    def wheelEvent(self, event):
        """Manage the mouse wheel rotation.

        Change the zoom on the map. If the delta is positive, zoom in, if the
        delta is negative, zoom out.

        Args:
            event(QWheelEvent): Mouse wheel event.
        """
        event.accept()
        delta = wheelAngleDelta(event)
        if delta > 0:
            self.scene().zoomIn(event.pos())
        elif delta < 0:
            self.scene().zoomOut(event.pos())
