from PyQt5.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtCore import Qt, QPoint, QRect, QSize
import time

class Capture(QWidget):

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.main.hide()
        
        self.setMouseTracking(True)
        desk_size = QApplication.primaryScreen().availableVirtualGeometry()
        print('available desktop size > ', desk_size)

        self.setGeometry(0, desk_size.y(), desk_size.width(), desk_size.height())
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.15)

        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()


        QApplication.setOverrideCursor(Qt.CrossCursor)
        screen = QApplication.primaryScreen()
        rect = QApplication.desktop().rect()

        #time.sleep(0.31)
        self.imgmap = screen.grabWindow(
            0,
            desk_size.x(), desk_size.y(), desk_size.width(), desk_size.height()
        )

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
            self.rubber_band.show() 

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if not self.origin.isNull():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event.button() == Qt.LeftButton:
            self.rubber_band.hide()
            
            rect = self.rubber_band.geometry()
            print('cropped rect > ', rect)
            self.capturedImg = self.imgmap.copy(rect)
            QApplication.restoreOverrideCursor()

            # set clipboard
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.capturedImg)

            #self.imgmap.save("TEST.png")

            self.main.label.setPixmap(self.capturedImg.scaled(QSize(500, 500), 
                                      aspectRatioMode=Qt.KeepAspectRatio,
                                      transformMode=Qt.SmoothTransformation))
            self.main.show()
            self.close()