from time import perf_counter

import scrcpy
from adbutils import AdbDevice, adb
from PySide6.QtCore import (QEvent, QLineF, QObject, QPointF, QPointFList,
                            QRectF, QSizeF, QTimer, Signal)
from PySide6.QtGui import QBrush, QColor, QImage, QPen, QPixmap, Qt
from PySide6.QtWidgets import (QApplication, QGraphicsItemGroup,
                               QGraphicsScene, QGraphicsSceneMouseEvent,
                               QListWidget, QListWidgetItem, QMainWindow)

from ui_mainwindow import Ui_MainWindow


class DeviceStream(QObject):
    init = Signal(AdbDevice, BaseException, name="init")
    frame = Signal(QPixmap, name="frame")
    disconnected = Signal(name="disconnected")

    def __init__(self) -> None:
        super().__init__()
        self.device: AdbDevice = None
        self.client: scrcpy.Client = None

    def isConnected(self):
        if (self.device):
            return True
        return False

    def ConnectDevice(self, device: AdbDevice):
        if (not device):
            raise (ValueError("No device selected"))
        if (device.get_state() == "offline"):
            raise (ConnectionAbortedError("Device is offline!"))

        self.device = device
        self.client = scrcpy.Client(device=self.device, stay_awake=True)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.on_frame)
        self.client.add_listener(scrcpy.EVENT_INIT, self.on_init)
        self.client.add_listener(scrcpy.EVENT_DISCONNECT, self.disconnected.emit)
        self.client.add_listener(scrcpy.EVENT_DISCONNECT, self.DisconnectDevice)

    def StartStream(self):
        # connecting status doesnt show up without a 5ms delay
        QTimer.singleShot(5, self._startStream)

    def _startStream(self):
        try:
            self.client.start(threaded=True)
        except BaseException as err:
            self.init.emit(None, err)

    def on_init(self):
        self.init.emit(self.device, None)

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
        if (self.client):
            self.client.stop()
            self.client = None
        if (self.device):
            self.device = None


class DeviceAction(QListWidgetItem):
    SwipeSpeed = 50

    def __init__(self, ActionList: QListWidget) -> None:
        super().__init__()
        self.MousePathPoints = QPointFList()
        self.PointDelays: list[float] = []
        self.ActionList = ActionList
        self.TimeSinceLastCall = None
        self.isPath = False
        self.isSwipe = False
        self.isClick = False
        self.isDelay = False
        self.OriginalBg = self.background()
        self.setText("init")
        self.ActionList.addItem(self)

    def StartAction(self, point: QPointF = None):
        self.setBackground(QColor(255, 0, 0, 125))

        if (not self.isDelay):
            self.TimeSinceLastCall = perf_counter()
        if (point):
            self.MousePathPoints.append(point)
            self.setText("Waiting for action...")
        else:
            self.isDelay = True
            self.setText("Delay Action")

    def AddPathPoint(self, point: QPointF):
        if (len(self.MousePathPoints) == 0):
            raise (ValueError("Action was never started with a point!"))

        self.MousePathPoints.append(point)
        CurrCall = perf_counter()
        delay = CurrCall - self.TimeSinceLastCall
        self.PointDelays.append(delay)
        self.TimeSinceLastCall = CurrCall
        self.isPath = True
        self.setText("Drag Action")

    def SwipeTo(self, point: QPointF):
        if (not self.isSwipe):
            self.isSwipe = True
            self.setText("Swipe Action")
            self.MousePathPoints.append(point)
            self.PointDelays.append(point.manhattanLength()/self.SwipeSpeed)
        else:
            self.setText("Swipe Action")

            self.MousePathPoints[1] = point
            self.PointDelays[0] = point.manhattanLength()/self.SwipeSpeed

    def StopAction(self, point: QPointF = None):
        self.setBackground(self.OriginalBg)
        if (len(self.MousePathPoints) == 0 and not self.isDelay):
            raise (ValueError("Action was never started with a point!"))

        if (self.isDelay):
            CurrCall = perf_counter()
            delay = CurrCall - self.TimeSinceLastCall
            if (len(self.PointDelays)):
                self.PointDelays[0] = delay
            else:
                self.PointDelays.append(delay)
            self.setText("Delay Action: " + str(round(delay, 2)) + "s")
        elif (self.isPath):
            self.AddPathPoint(point)
        elif (point == self.MousePathPoints[0]):
            self.isClick = True
            self.setText("Click Action")
        else:
            self.SwipeTo(point)

    def remove(self):
        self.ActionList.takeItem(self.ActionList.row(self))


class MainWindow(QMainWindow, Ui_MainWindow):
    Color = QColor(255, 0, 0, 180)
    Brush = QBrush(Color)
    PathPen = QPen(Color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    ClickSize = QSizeF(8, 8)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # self.showMaximized()
        self.stream = DeviceStream()
        self.currAction = None
        self.currDelayAction = None
        self.currFrame = None
        self.currPixmapItem = None
        self.SceneToDeviceRatio = 1.00
        self.currPathGroup: QGraphicsItemGroup = None
        self.isDrawing = False
        self.currSceneAction = None
        self.isRecording = False

        # event connections
        self.RefreshBtn.clicked.connect(self.RefreshDeviceList)
        self.RecordButton.clicked.connect(self.ToggleRecord)
        self.ConnectBtn.clicked.connect(self.ConnectDevice)
        self.DisconnectBtn.clicked.connect(self.DisconnectDevice)
        self.stream.init.connect(self.on_init)
        self.stream.frame.connect(self.on_frame)
        self.stream.disconnected.connect(self.DisconnectDevice)

        self.DeviceScene = QGraphicsScene(self.GraphicsView)
        self.DefaultScene = QGraphicsScene(self.GraphicsView)
        self.DefaultScene.addText("DEVICE NOT CONNECTED")
        self.GraphicsView.setScene(self.DefaultScene)
        self.DeviceScene.installEventFilter(self)
        self.RefreshDeviceList()

    def ToggleRecord(self):
        self.isRecording = not self.isRecording
        if (self.isRecording):
            self.RecordButton.setText("Stop Recording...")
            self.currDelayAction = DeviceAction(self.ActionList)
            self.currDelayAction.StartAction()
        else:
            self.ClearPath()
            self.RecordButton.setText("Start Recording...")
            self.currDelayAction.StopAction()

    def RefreshDeviceList(self):
        self.DeviceList.clear()
        self.DeviceList.setCurrentIndex(-1)

        for i, device in enumerate(adb.iter_device()):
            self.DeviceList.addItem(
                f"{device.prop.model} ({device.serial})", device)

            if (self.stream.isConnected() and device.serial == self.stream.device.serial):
                self.DeviceList.setCurrentIndex(i)
        self.DeviceList.setPlaceholderText(f"None ({self.DeviceList.count()})")

    def ConnectDevice(self):
        if (self.stream.isConnected()):
            self.DisconnectDevice()

        self.ConnectBtn.setDisabled(True)
        self.DisconnectBtn.setDisabled(True)
        self.DeviceList.setDisabled(True)

        device: AdbDevice = self.DeviceList.currentData()
        try:
            self.stream.ConnectDevice(device)
        except BaseException as err:
            self.LogError(err)
            self.DisconnectDevice()
            return

        self.LogStatus(
            f"Connecting to {device.prop.model} ({device.serial})...")
        self.stream.StartStream()

    def on_init(self, device: AdbDevice, err: BaseException):
        self.DisconnectBtn.setDisabled(False)
        if (err):
            self.DisconnectDevice()
            self.LogError(err)
            return
        self.LogStatus(
            f"Connected to {device.prop.model} ({device.serial})")
        self.DeviceScene.clear()
        self.currPixmapItem = None
        self.currPathGroup = None
        self.RecordButton.setEnabled(True)
        self.GraphicsView.setScene(self.DeviceScene)

    def on_frame(self, frame: QPixmap):
        self.currFrame = frame
        self.ShowFrame()

    def ShowFrame(self):
        size = self.GraphicsView.size()
        px = self.currFrame.scaled(
            size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.SceneToDeviceRatio = self.currFrame.size().height() / px.size().height()
        if (not self.currPixmapItem):
            self.currPixmapItem = self.DeviceScene.addPixmap(px)
            self.currPixmapItem.setCursor(Qt.CrossCursor)
            self.currPixmapItem.setZValue(0)
        else:
            self.currPixmapItem.setPixmap(px)
        self.DeviceScene.setSceneRect(self.currPixmapItem.boundingRect())

    def ShowDeviceAction(self, Action: DeviceAction):
        self.ClearPath()
        if (Action.isPath or Action.isSwipe):
            lastPoint = Action.MousePathPoints[0]
            for point in Action.MousePathPoints:
                line = QLineF(lastPoint/self.SceneToDeviceRatio,
                              point/self.SceneToDeviceRatio)
                self.currPathGroup.addToGroup(
                    self.DeviceScene.addLine(line, self.PathPen)
                )
                lastPoint = point
        else:
            center: QPointF = Action.MousePathPoints[0]/self.SceneToDeviceRatio
            center.setX(center.x() - self.ClickSize.width()/2)
            center.setY(center.y() - self.ClickSize.height()/2)

            EllipseItem = self.DeviceScene.addEllipse(
                QRectF(center, self.ClickSize), self.PathPen, self.Brush)
            self.currPathGroup.addToGroup(EllipseItem)
        self.currSceneAction = Action

    def ClearPath(self):
        if (self.currPathGroup):
            self.DeviceScene.removeItem(self.currPathGroup)
        self.currPathGroup = self.DeviceScene.createItemGroup([])
        self.currPathGroup.setZValue(1)
        self.currSceneAction = None

    def resizeEvent(self, event) -> None:
        if (self.currFrame):
            self.ShowFrame()
        if (self.currSceneAction):
            self.ShowDeviceAction(self.currSceneAction)

        return super().resizeEvent(event)

    def DisconnectDevice(self):
        if (self.stream.isConnected()):
            self.LogStatus(
                f"Disconneted from {self.stream.device.prop.model} ({self.stream.device.serial})")
        self.stream.DisconnectDevice()
        self.GraphicsView.setScene(self.DefaultScene)
        if (self.isRecording):
            self.ToggleRecord()
        self.RecordButton.setEnabled(False)
        self.DeviceList.setDisabled(False)
        self.ConnectBtn.setDisabled(False)
        self.DisconnectBtn.setDisabled(True)
        self.RefreshDeviceList()

    def closeEvent(self, event):
        self.DisconnectDevice()
        super().closeEvent(event)

    def ConvertSceneEventToDevicePoint(self, event: QGraphicsSceneMouseEvent):
        return QPointF(event.scenePos().toPoint()) * self.SceneToDeviceRatio

    def eventFilter(self, watched: QObject, event: QGraphicsSceneMouseEvent) -> bool:
        if (self.isRecording and self.currPixmapItem and isinstance(event, QGraphicsSceneMouseEvent)):
            isContained = self.currPixmapItem.contains(
                event.scenePos().toPoint())
        else:
            return super().eventFilter(watched, event)

        if (event.type() == QEvent.GraphicsSceneMousePress):
            if (isContained):
                if (self.isDrawing):  # two buttons clicked
                    self.currAction.remove()
                    del self.currAction
                    self.ClearPath()
                    self.LogStatus("Last action has been removed!")
                    self.isDrawing = False
                    self.currDelayAction.StartAction()
                else:  # first button clicked
                    self.currAction = DeviceAction(self.ActionList)
                    self.currAction.StartAction(
                        self.ConvertSceneEventToDevicePoint(event))
                    self.isDrawing = True
                    self.currDelayAction.StopAction()
            else:
                self.ClearPath()

        elif (event.type() == QEvent.GraphicsSceneMouseMove and self.isDrawing):
            if (isContained):
                if (event.buttons() & Qt.LeftButton):  # dragging
                    self.currAction.AddPathPoint(
                        self.ConvertSceneEventToDevicePoint(event))
                elif (event.buttons() & Qt.RightButton):  # swipe
                    self.currAction.SwipeTo(
                        self.ConvertSceneEventToDevicePoint(event))
            else:  # mouse no longer on device
                self.currAction.StopAction(
                    self.currAction.MousePathPoints[-1]
                )
                self.isDrawing = False
                self.currDelayAction = DeviceAction(self.ActionList)
                self.currDelayAction.StartAction()
            self.ShowDeviceAction(self.currAction)

        elif (event.type() == QEvent.GraphicsSceneMouseRelease and self.isDrawing):
            if (isContained):
                self.currAction.StopAction(
                    self.ConvertSceneEventToDevicePoint(event))
            else:
                self.currAction.StopAction(
                    self.currAction.MousePathPoints[-1]
                )
            self.ShowDeviceAction(self.currAction)
            self.isDrawing = False
            self.currDelayAction = DeviceAction(self.ActionList)
            self.currDelayAction.StartAction()

        return super().eventFilter(watched, event)

    def LogStatus(self, msg: str, duration: int = 2500):
        self.statusBar().showMessage(msg)
        QTimer.singleShot(duration, self.statusBar().clearMessage)

    def LogError(self, err: BaseException):
        self.LogStatus(
            f"An error has occured! {type(err).__name__} : {err.args[0]}")


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    # app.setOrganizationName("FieryRMS")
    # app.setOrganizationDomain("https://github.com/FieryRMS/AndroidAutoClicker")
    app.setApplicationName("AndroidAutoClicker")
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())
