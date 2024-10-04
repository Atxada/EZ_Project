from PySide6 import QtCore, QtWidgets, QtGui

from util import *

import custom_widget

class EZMHome(QtWidgets.QWidget):
    def __init__(self, app):
        super().__init__()

        self.app = app

        self.initUI()

    def initUI(self):
        self.main_layout = QtWidgets.QHBoxLayout(self)

        self.project_btn = EZMIcon(get_path('ez_project_beta.png', icon=True), 
                                                       self.onClick, QtGui.QColor('silver'), 0.1, (128,153))

        self.main_layout.addWidget(self.project_btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

    def onClick(self, event):
        self.app.go_to_project(event)

class EZMIcon(custom_widget.GraphicButton):
    def __init__(self, icon="", callback=None, color=QtGui.QColor('silver'), strength=0.25, size=(32,32), parent=None):
        super().__init__(icon, callback, color, strength, size, parent)

        self.pen_hovered = QtGui.QPen(QtGui.QColor('#FFFFFF'), 1, QtCore.Qt.DashLine)
        self.hovered = False

    def enterEvent(self, event):
        super().enterEvent(event)
        self.hovered = True

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hovered = False

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.hovered:
            painter = QtGui.QPainter(self)
            painter.setPen(self.pen_hovered)
            rect = QtCore.QRect(1, 1, painter.device().width()-2, painter.device().height()-2)
            painter.drawRect(rect)