from adbutils import adb, AdbDevice
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QImage, QPixmap, Qt
import scrcpy

from ui_mainwindow import Ui_MainWindow

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.showMaximized()
        self.device: AdbDevice = None
        self.client: scrcpy.Client = None

        self.RefreshBtn.clicked.connect(self.RefreshDeviceList)
        self.ConnectBtn.clicked.connect(self.ConnectDevice)

        self.RefreshDeviceList()

    def RefreshDeviceList(self):
        self.DeviceList.clear()
        self.DeviceList.setCurrentIndex(-1)

        for i, device in enumerate(adb.iter_device()):
            self.DeviceList.addItem(
                f"{device.prop.model} ({device.get_serialno()})", device)

            if(self.device and device.serial == self.device.serial):
                self.DeviceList.setCurrentIndex(i)

    def ConnectDevice(self):
        dev: AdbDevice = self.DeviceList.currentData()
        if(not dev):
            raise(ValueError("No device selected"))
        if(self.client):
            self.client.stop()
        self.device = dev
        self.client = scrcpy.Client(device=self.device, stay_awake=True)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.on_frame)
        self.client.start(threaded=True)

    def on_frame(self, frame):
        if frame is not None:
            QImage()
            image = QImage(
                frame,
                frame.shape[1],
                frame.shape[0],
                frame.shape[1] * 3,
                QImage.Format_BGR888,
            )
            pix = QPixmap(image).scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(pix)

    def closeEvent(self, event):
        if(self.client):
            self.client.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # app.setOrganizationName("FieryRMS")
    # app.setOrganizationDomain("https://github.com/FieryRMS/AndroidAutoClicker")
    app.setApplicationName("AndroidAutoClicker")
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())
