from PySide6 import QtCore, QtWidgets, QtGui

from app_window import EZMWindow
from util import *

import sys
              
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    loadStylesheet(app, get_path('sources', 'style', 'dark.qss')) # applied to application to affect qmenu widget

    window = EZMWindow()
    window.show()

    sys.exit(app.exec())