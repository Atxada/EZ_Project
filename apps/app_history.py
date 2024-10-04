from PySide6 import QtCore, QtWidgets, QtGui
from commands import *  

DEBUG = True

class EZMHistory():
    """Contains code for undo/redo for ez manager application"""
    def __init__(self, program):

        self.program = program

        self.history_stack = []
        self.current_step = -1
        self.limit = 10

        self.clear()
        self.storeInitialHistoryStamp() # serialize initial config of program

    def clear(self):
        self.history_stack = []
        self.current_step = -1

    def canUndo(self):
        return self.current_step > 0
    
    def canRedo(self):
        return self.current_step + 1 < len(self.history_stack)
    
    def undo(self):
        if self.canUndo():
            self.current_step -= 1
            self.restoreHistory()
        elif DEBUG:
            print ('cannot undo, current step > %s of %s'%(self.current_step, len(self.history_stack)-1))
    
    def redo(self):
        if self.canRedo():
            self.current_step += 1
            self.restoreHistory()
        elif DEBUG:
            print ('cannot redo, current step > %s of %s'%(self.current_step, len(self.history_stack)-1))

    def storeInitialHistoryStamp(self):
        self.storeHistory("init history")

    def storeHistory(self, desc=''):
        # if the pointer (history_current_step) is not at the end of history stack
        if self.current_step+1 < len(self.history_stack):
            self.history_stack = self.history_stack[0:self.current_step+1]

        # history is outside of the limit
        if self.current_step+1 >= self.limit:
            self.history_stack = self.history_stack[1:]
            self.current_step -= 1

        # create history stamp containing the data
        history_stamp = self.createHistoryStamp(desc)
        self.history_stack.append(history_stamp)

        self.current_step += 1
        if DEBUG: print('store history:: current step > %s of %s [%s]'%(self.current_step, len(self.history_stack)-1, self.history_stack[self.current_step]['desc']))

    def restoreHistory(self):
        if DEBUG: print ('restore history:: current step > %s of %s [%s]'%(self.current_step, len(self.history_stack)-1, self.history_stack[self.current_step]['desc']))
        self.restoreHistoryStamp(self.history_stack[self.current_step])

    def createHistoryStamp(self, desc):
        history_stamp = {
            'desc'     : desc,
            'snapshot' : self.program.serialize()
        }
        return history_stamp
    
    def restoreHistoryStamp(self, history_stamp):
        self.program.deserialize(history_stamp['snapshot'])

class EZMUndoStack(QtGui.QUndoStack):
    def __init__(self, parent=None):    # let qt destroy undostack when parent is destroyed
        super().__init__(parent)
        self.top_widget = parent

    # def undo(self):
    #     # before undo check type first
    #     command = self.command(self.index()-1)
    #     if type(command) is cmd_convertToStruct:
    #         string_from_list = ' ,'.join([asset.name for asset in command.assets])
    #         confirm = QtWidgets.QMessageBox.warning(self.top_widget, 
    #                                                 'Undo struct creation',
    #                                                 "This will delete the following struct folder from your computer:\n%s"%string_from_list,
    #                                                 QtWidgets.QMessageBox.Yes,
    #                                                 QtWidgets.QMessageBox.No)
    #         if confirm == QtWidgets.QMessageBox.Yes:
    #             super().undo()
    #     else:
    #         super().undo()