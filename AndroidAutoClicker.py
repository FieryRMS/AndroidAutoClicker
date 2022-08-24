from adbutils import adb, AdbDevice
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene
from PySide6.QtGui import QImage, QPixmap, Qt
from PySide6.QtCore import QTimer, QObject, Signal, QMargins
import scrcpy

from ui_mainwindow import Ui_MainWindow


class DeviceStream(QObject):
    init = Signal(AdbDevice, name="init")
    frame = Signal(QPixmap, name="frame")
    device: AdbDevice = None
    client: scrcpy.Client = None

    def __init__(self) -> None:
        super().__init__()

    def isConnected(self):
        if(self.device):
            return True
        return False

    def ConnectDevice(self, device: AdbDevice):
        if(not device):
            raise(ValueError("No device selected"))
        if(device.get_state() == "offline"):
            raise(ConnectionAbortedError("Device is offline!"))

        self.device = device
        self.client = scrcpy.Client(device=self.device, stay_awake=True)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.on_frame)
        self.client.add_listener(scrcpy.EVENT_INIT, self.on_init)

    def StartStream(self):
        # connecting status doesnt show up without a 5ms delay
        QTimer.singleShot(5, lambda: self.client.start(threaded=True))

    def on_init(self):
        self.init.emit(self.device)

    def on_frame(self, frame):
        if frame is not None and self.client.alive:
            image = QImage(
                frame,
                frame.shape[1],
                frame.shape[0],
                frame.shape[1] * 3,
                QImage.Format_BGR888,
            )
            pix = QPixmap(image)
            self.frame.emit(pix)

    def DisconnectDevice(self):
        if(self.client):
            self.client.stop()
            self.client = None
        if(self.device):
            self.device = None

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # self.showMaximized()
        self.stream = DeviceStream()
        self.currFrame = None

        # event connections
        self.RefreshBtn.clicked.connect(self.RefreshDeviceList)
        self.ConnectBtn.clicked.connect(self.ConnectDevice)
        self.DisconnectBtn.clicked.connect(self.DisconnectDevice)
        self.stream.init.connect(self.on_init)
        self.stream.frame.connect(self.on_frame)

        self.DeviceScene = QGraphicsScene(self.GraphicsView)
        self.DefaultScene = QGraphicsScene(self.GraphicsView)
        self.DefaultScene.addText("DEVICE NOT CONNECTED")
        self.GraphicsView.setScene(self.DefaultScene)
        self.RefreshDeviceList()

    def RefreshDeviceList(self):
        self.DeviceList.clear()
        self.DeviceList.setCurrentIndex(-1)

        for i, device in enumerate(adb.iter_device()):
            self.DeviceList.addItem(
                f"{device.prop.model} ({device.serial})", device)

            if(self.stream.isConnected() and device.serial == self.stream.device.serial):
                self.DeviceList.setCurrentIndex(i)
        self.DeviceList.setPlaceholderText(f"None ({self.DeviceList.count()})")

    def ConnectDevice(self):
        if(self.stream.isConnected()):
            self.DisconnectDevice()

        device: AdbDevice = self.DeviceList.currentData()
        try:
            self.stream.ConnectDevice(device)
        except BaseException as err:
            self.LogStatus(
                f"An error has occured! {type(err).__name__} : {err.args[0]}")
            self.RefreshDeviceList()
            return

        self.LogStatus(
            f"Connecting to {device.prop.model} ({device.serial})...")
        self.stream.StartStream()

    def on_init(self, device: AdbDevice):
        self.LogStatus(
            f"Connected to {device.prop.model} ({device.serial})")
        self.DeviceScene.clear()
        self.GraphicsView.setScene(self.DeviceScene)

    def on_frame(self, frame: QPixmap):
        self.currFrame = frame
        self.ShowFrame()

    def ShowFrame(self):
        self.DeviceScene.clear()
        size = self.GraphicsView.size()
        px = self.currFrame.scaled(
            size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ImageItem = self.DeviceScene.addPixmap(px)
        self.DeviceScene.setSceneRect(ImageItem.boundingRect())

    def resizeEvent(self, event) -> None:
        if(self.currFrame):
            self.ShowFrame()

        return super().resizeEvent(event)

    def DisconnectDevice(self):
        if(self.stream.isConnected()):
            self.LogStatus(
                f"Disconneted from {self.stream.device.prop.model} ({self.stream.device.serial})")
        self.stream.DisconnectDevice()
        self.GraphicsView.setScene(self.DefaultScene)

    def closeEvent(self, event):
        self.DisconnectDevice()
        super().closeEvent(event)

    def LogStatus(self, msg: str):
        self.statusBar().showMessage(msg)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # app.setOrganizationName("FieryRMS")
    # app.setOrganizationDomain("https://github.com/FieryRMS/AndroidAutoClicker")
    app.setApplicationName("AndroidAutoClicker")
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())
