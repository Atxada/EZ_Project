from PySide6 import QtCore, QtWidgets, QtGui

from app_main_widget import EZMToolbar
from util import *

class EZMWindow(QtWidgets.QMainWindow):
    def __init__(self):
       super().__init__()
       #self.setMinimumWidth(820)
       self.initUI()
       self.initAction()
       self.resize(1000,600) # 800, 600 size old

    def initUI(self):
        #self.history = EZMHistory(self)    # custom history system

        self.main_widget = EZMToolbar(self)
        self.setCentralWidget(self.main_widget)

        self.setWindowTitle("Eazy Workflow v1.0")
        path = get_path("add.png", icon=True)
        self.setWindowIcon(QtGui.QIcon(path))
        self.statusBar().showMessage("(Offline) User: -")

    def initAction(self):
        self.undoAction = QtGui.QAction(self, shortcut='Ctrl+Z', triggered=self.onUndo)
        self.redo1Action = QtGui.QAction(self, shortcut='Ctrl+Shift+Z', triggered=self.onRedo)
        self.redo2Action = QtGui.QAction(self, shortcut='Ctrl+Y', triggered=self.onRedo)    # alternative shortcut for redo
        self.saveAction = QtGui.QAction(self, shortcut='Ctrl+S', triggered=self.onSave)
        self.addAction(self.undoAction)     # no need to add to menubar, as we don't want to display menubar
        self.addAction(self.redo1Action)
        self.addAction(self.redo2Action)
        self.addAction(self.saveAction)

    def closeEvent(self, event):
        self.main_widget.project_browser.onModified()
        # check if calendar_editor has any unsaved
        if self.main_widget.calendar_editor.is_modified:
            warning = QtWidgets.QMessageBox.warning(self,
                                                    'Save changes?',
                                                    'You have unsaved changes on calendar editor\nDo you want to save?',
                                                    QtWidgets.QMessageBox.Yes,
                                                    QtWidgets.QMessageBox.No)
            if warning == QtWidgets.QMessageBox.Yes: self.main_widget.calendar_editor.save_data()

    def show_status(self, text='', output=0):
        # 0 = success
        # 1 = error
        # 2 = warning
        # 3 = normal
        if output == 0:
            self.statusBar().setStyleSheet('color:green')
            self.statusBar().showMessage(text)
        elif output == 1:
            self.statusBar().setStyleSheet('color:red')
            self.statusBar().showMessage(text)
        elif output == 2:
            self.statusBar().setStyleSheet('color:yellow')
            self.statusBar().showMessage(text)
        else:
            self.statusBar().setStyleSheet('color:white')
            self.statusBar().showMessage(text)

    def onRedo(self):
        history_stack = self.main_widget.get_history_stack()
        if history_stack: history_stack.redo()

    def onUndo(self):
        history_stack = self.main_widget.get_history_stack()
        if history_stack: history_stack.undo()

    def onSave(self):
        if self.main_widget.calendar_dock.isActiveWindow(): 
            self.main_widget.calendar_editor.save_data()