import os
import time
from PySide6.QtCore import (
    QObject, Signal, Slot, QThread, QTimer,
    QUrl
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# ---------------------------------------------------------------------------
# TileDownloader: lives entirely in its own QThread
# ---------------------------------------------------------------------------

class TileDownloader(QObject):
    '''TMS caching tile retreiver 

    Remarks
    -------
    - Listens for current aimpoint (tile index)
    - Sorts pending tiles by distnce from current aimpoint
    - Uses an on-disk cache of tiles
    - Emits tileReady when a tile is loaded
    '''

    tileReady = Signal(int, int, int, bytes)

    def __init__(self, cache_dir:str = "cache", url_template:str='', parent=None):
        '''
        Parameters
        ----------
        cache_dir : str 
            Path to a directory for tile storage
        '''
        super().__init__(parent)
        self.cache_dir = cache_dir
        self.url_template = url_template
        os.makedirs(self.cache_dir, exist_ok=True)
        self.pending = []
        self.active = {}
        self.requested = set()
        self.aimpoint = (0, 0, 0)
        self.running = False

        self.timer = None
        self.nam = None

        self.user_agent = b"Mozilla/5.0 (TileDownloader PyQt Example)"

    @Slot()
    def start(self)->None:
        '''Initializes child objects, including dispatch timer and NetworkAccessManager'''
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._dispatch_next)
        self.timer.start(50)  # regulate requests
        self.nam = QNetworkAccessManager()
        self.running = True

    @Slot()
    def shutdown(self)->None:
        """Cleanly stop timers and pending operations."""
        self.timer.stop()
        for reply in list(self.active.values()):
            reply.abort()
        self.active.clear()
        self.pending.clear()
        self.requested.clear()
        self.running = False

    @Slot(int, int, int)
    def setAimpoint(self, zoom:int, x:int, y:int) -> None:
        """Set the current aimpoint (center tile) for download prioritization.

        Parameters
        ----------
        zoom : int
            TMS Zoom level
        x : int
            TMS x
        y : int
            TMS y

        """
        self.aimpoint = (zoom, x, y)
        # reprioritize queue
        self.pending.sort(key=lambda item: self._tile_distance(item, self.aimpoint))

    @Slot()
    def reset(self):
        """Clear pending and active requests."""
        for reply in list(self.active.values()):
            reply.abort()
        self.pending.clear()
        self.active.clear()
        self.requested.clear()

    @Slot(int, int, int)
    def request_tile(self, z:int, x:int, y:int) -> None:
        """Queue or start a tile request.

        Parameters
        ----------
        z : int
            TMS z
        x : int
            TMS x
        y : int
            TMS y
        url_template : str
            URL to download tiles from
        """
        cache_path = os.path.join(self.cache_dir, str(z), str(x), f"{y}.png")

        # already on disk?
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                data = f.read()
            self.tileReady.emit(z, x, y, data)
            return

        if (z, x, y) in self.requested:
            return


        self.requested.add((z, x, y))
        self.pending.append((z, x, y, self.url_template))
        self.pending.sort(key=lambda item: self._tile_distance(item, self.aimpoint))

    # ------------------------ private helpers ------------------------

    def _tile_distance(self, tile:tuple[int,int,int,int], aim: tuple[int,int,int])->int:
        '''Calculate distance from an aimpoint tile to current tile (for sorting)

        Parameters
        ----------
            tile: tuple[int,int,int,int]
                Tile in to test : [TMS Z, X, Y, template]
            aim : tuple[int,int,int]
                Current aimpoint [ TMS Z, X, Y ]

        Returns
        -------
            distance : int
                Distance from tile to aim
        '''
        z, x, y, _ = tile
        az, ax, ay = aim
        return abs(ax - x) + abs(ay - y) + (abs(az - z) * 4)

    @Slot()
    def _dispatch_next(self)->None:
        """If any downloaders are available, start a download"""
        if len(self.active) >= 4 or not self.pending:
            return

        z, x, y, url_template = self.pending.pop(0)
        url = url_template.format(z=z, x=x, y=y)
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", self.user_agent)
        # This line
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self._on_finished(reply, z, x, y))
        self.active[(z, x, y)] = reply

    def _on_finished(self, reply: QNetworkReply, z:int, x:int, y:int)->None:
        """Handle a response from tile server - cache the tile, emit tileReady

        Parameters
        ----------
        reply : QNetworkReply
            Object containing response to web request
        z : int
            TMS Z of requested tile
        x : int
            TMS X of requested tile
        y : int
            TMS y of requested tile
        """
        self.active.pop((z, x, y), None)

        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data()
            cache_path = os.path.join(self.cache_dir, str(z), str(x))
            os.makedirs(cache_path, exist_ok=True)
            with open(os.path.join(cache_path, f"{y}.png"), "wb") as f:
                f.write(data)
            self.tileReady.emit(z, x, y, data)
        else:
            print(f"Tile {z}/{x}/{y} failed:", reply.errorString())
        reply.deleteLater()


class TileManager(QObject):
    """
    Wrapper for TileDownloader and a thread it lives in.  This is the class that the main thread should interact with,

    Remarks
    -------
    - Methods callable by the main thread
    - Sends signals to the tile downloader inside a thread
    - Safelly initializes the tile downloader child objects within the threads using signals

    Signals
    -------
    tileReady : int, int, int, bytes
        Sends a tile to the main app
    sigSetAimpoint: int, int, int
        Tell the tile downloader that what the current aimpoint is
    sigReset: 
        Tell the file downloader to reset itself
    sigRequestTile: int, int, int
        Tell the tile downloader to fetch a tile (z, x, y)
    sigStartDownloader: 
        Tell the tile downloader to initialize child objects
    sigShutdown:
        Tell the tile downloader to shutdown
    """
    tileReady = Signal(int, int, int, bytes)
    sigSetAimpoint = Signal(int, int, int)
    sigReset = Signal()
    sigRequestTile = Signal(int, int, int)
    sigStartDownloader = Signal()
    sigShutdown = Signal()

    def __init__(self, cache_dir : str = '', url_template : str = ''):
        super().__init__()
        self._thread = None
        self._downloader = None

        self.set_downloader(cache_dir, url_template)


    def set_downloader(self, cache_dir:str, url_template:str) -> None:
        '''Set a tile source

        Parameters
        ----------
        cache_dir : str
            root directory for caching
        url_template : str
            template for downloads, must include {z}, {x}, and {y}
        '''
        if self._thread is not None:
            return

        # Thread and worker
        self._thread = QThread(self)

        self._downloader = TileDownloader(cache_dir=cache_dir, url_template=url_template)


        # Move worker to thread (it will live in that thread after the thread starts)
        self._downloader.moveToThread(self._thread)

        # Tile Ready Signal
        self._downloader.tileReady.connect(self.tileReady)

        # Tile Request Signals
        self.sigSetAimpoint.connect(self._downloader.setAimpoint)
        self.sigReset.connect(self._downloader.reset)
        self.sigRequestTile.connect(self._downloader.request_tile)

        # START AND STOP SIGNALS
        self.sigStartDownloader.connect(self._downloader.start)
        self.sigShutdown.connect(self._downloader.shutdown)

        # Thread lifecycle wiring
        self._thread.started.connect(self._on_thread_started)
        self._thread.finished.connect(self._on_thread_finished)


    @Slot()
    def _on_thread_started(self) -> None:
        """
        After the thread has started, singnal the tile downloader to initialize child objects
        """
        self.sigStartDownloader.emit()

    @Slot()
    def _on_thread_finished(self) -> None:
        """
        Cleanup when thread finished.
        """
        self._downloader.deleteLater()

    # Public API
    def start(self) -> None:
        """Start the thread and initialize the worker."""
        if not self._thread.isRunning():
            self._thread.start()

    def stop(self) -> None:
        """Stop the thread cleanly and wait for it to finish."""
        self.sigShutdown.emit()

        # Wait for downloader to stop running before stopping the thread
        now = time.time() 
        while self._downloader is not None and self._downloader.running:
            time.sleep(0.1)
            if time.time() - now > 1:
                break

        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    def sendReset(self) -> None:
        '''Send reset signal to downloader'''
        self.sigReset.emit()

    def setAimpoint(self, zoom:int, x:int, y:int)->None:
        '''Send set aimpoint to downloader.  Used for prioritization
        
        Parameters
        ----------
        zoom : int
            TMS zoom level
        x : int
            TMS x
        y : int
            TMS y
        '''
        self.sigSetAimpoint.emit(zoom, x, y)

    def request_tile(self, zoom:int, x:int, y:int)->None:
        '''Send tile request to downloader
        
        Parameters
        ----------
        zoom : int
            TMS zoom level
        x : int
            TMS x
        y : int
            TMS y
        '''
        self.sigRequestTile.emit(zoom, x, y)

# ---------------------------------------------------------------------------
# DEMO GUI FOR TEST
# ---------------------------------------------------------------------------
class TileViewer(QWidget):
    request_tile = Signal(int, int, int)
    setAimpoint = Signal(int, int, int)
    resetDownloader = Signal()

    def __init__(self, cache_dir, url_template):
        super().__init__()
        self.setWindowTitle("TileDownloader Demo")
        self.tile_manager = None
        layout = QVBoxLayout(self)
        self.label = QLabel("No tile yet")
        self.button = QPushButton('request tiles')
        self.map_combo = QComboBox()
        self.map_combo.addItems(
            ["OSM", "Blue Marble" ]
        )
        self.map_combo.currentIndexChanged.connect(self.on_map_combo)

        layout.addWidget(self.label)
        layout.addWidget(self.button)
        layout.addWidget(self.map_combo)


        # Set up the tile manager
        self.init_tile_manager(cache_dir, url_template)

        self.zoom = 3
        self.tile_x = 2
        self.tile_y = 3

        self.button.clicked.connect(self.change_aimpoint)

    def on_map_combo(self):
        txt = self.map_combo.currentText()
        if txt == 'OSM':
            cache_dir = 'osm'
            url_template = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        else:
            cache_dir = 'bluemarble'
            url_template = "http://s3.amazonaws.com/com.modestmaps.bluemarble/{z}-r{y}-c{x}.jpg"
        self.init_tile_manager(cache_dir, url_template)

    def init_tile_manager(self, cache_dir, url_template):
        if self.tile_manager is not None:
            self.tile_manager.stop()
            del self.tile_manager

        self.tile_manager = TileManager(cache_dir, url_template)
        self.tile_manager.tileReady.connect(self.on_tile_ready)
        self.tile_manager.start()

    def change_aimpoint(self):
        """Simulate moving to a different tile center."""
        self.tile_x += 1
        self.tile_y += 1
        self.tile_manager.sendReset()
        self.tile_manager.setAimpoint(self.zoom, self.tile_x, self.tile_y)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                self.tile_manager.request_tile(
                    self.zoom,
                    self.tile_x + dx,
                    self.tile_y + dy
                )

    @Slot(int, int, int, bytes)
    def on_tile_ready(self, z, x, y, data):
        pix = QPixmap()
        pix.loadFromData(data)
        self.label.setPixmap(pix.scaled(256, 256))

    def closeEvent(self, evt):
        self.tile_manager.stop()


def main():
    app = QApplication([])

    # Create GUI
    url_template = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    cache_dir = 'cache'
    viewer = TileViewer(cache_dir, url_template)
    viewer.resize(300, 350)
    viewer.show()

    app.exec()

if __name__ == "__main__":
    main()
