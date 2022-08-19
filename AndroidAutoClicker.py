from adbutils import adb, AdbDevice
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QImage, QPixmap, Qt
from PySide6.QtCore import QTimer
import scrcpy

from ui_mainwindow import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.showMaximized()
        self.device: AdbDevice = None
        self.client: scrcpy.Client = None

        # button click events
        self.RefreshBtn.clicked.connect(self.RefreshDeviceList)
        self.ConnectBtn.clicked.connect(self.ConnectDevice)
        self.DisconnectBtn.clicked.connect(self.DisconnectDevice)

        self.RefreshDeviceList()

    def RefreshDeviceList(self):
        self.DeviceList.clear()
        self.DeviceList.setCurrentIndex(-1)

        for i, device in enumerate(adb.iter_device()):
            self.DeviceList.addItem(
                f"{device.prop.model} ({device.serial})", device)

            if(self.device and device.serial == self.device.serial):
                self.DeviceList.setCurrentIndex(i)

    def ConnectDevice(self):
        device: AdbDevice = self.DeviceList.currentData()
        try:
            if(not device):
                raise(ValueError("No device selected"))
            if(device.get_state() == "offline"):
                raise(ConnectionAbortedError("Device is offline!"))
        except BaseException as err:
            self.LogStatus(
                f"An error has occured! {type(err).__name__} : {err.args[0]}")
            self.RefreshDeviceList()
            return

        self.DisconnectDevice()
        self.device = device
        self.LogStatus(
            f"Connecting to {self.device.prop.model} ({self.device.serial})...")
        self.client = scrcpy.Client(device=self.device, stay_awake=True)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.on_frame)
        self.client.add_listener(scrcpy.EVENT_INIT, self.on_init)
        ## connecting status doesnt show up without a 5ms delay
        QTimer.singleShot(5, lambda: self.client.start(threaded=False))

    def on_init(self):
        self.LogStatus(
            f"Connected to {self.device.prop.model} ({self.device.serial})")

    def on_frame(self, frame):
        if frame is not None and self.client.alive:
            QImage()
            image = QImage(
                frame,
                frame.shape[1],
                frame.shape[0],
                frame.shape[1] * 3,
                QImage.Format_BGR888,
            )
            pix = QPixmap(image).scaled(self.DeviceView.size(),
                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.DeviceView.setPixmap(pix)

    def DisconnectDevice(self):
        if(self.client):
            self.client.stop()
        if(self.device):
            self.LogStatus(
                f"Disconneted from {self.device.prop.model} ({self.device.serial})")
            self.device = None
        self.DeviceView.clear()
        self.DeviceView.setText("NO DEVICE CONNECTED")

    def closeEvent(self, event):
        if(self.device):
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
