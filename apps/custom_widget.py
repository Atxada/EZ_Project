from PySide6 import QtCore, QtWidgets, QtGui

from util import *

import time

DEBUG = True

class GraphicButton(QtWidgets.QLabel):
    def __init__(self, icon="", callback=None, color=QtGui.QColor('silver'), strength=0.25, size=(32,32), parent=None):
        super(GraphicButton, self).__init__(parent)

        self.icon = icon
        self.callback = []
        if callback: self.callback.append(callback)
        self.color = color
        self.strength = strength
        self.icon_size = size
        self.setFixedSize(self.icon_size[0],self.icon_size[1])

        self.initUI()

    def initUI(self):
        self.item_image = validate_image_path(self.icon, backup=get_path("python.png", icon=True))
        self.item_image = self.item_image.scaled(self.icon_size[0],self.icon_size[1],QtCore.Qt.IgnoreAspectRatio,QtCore.Qt.SmoothTransformation)
        self.item_pixmap = QtGui.QPixmap()
        self.item_pixmap.convertFromImage(self.item_image)
        self.setPixmap(self.item_pixmap)

        # set highlight mouse hover effect
        self.highlight = QtWidgets.QGraphicsColorizeEffect()
        self.highlight.setColor(self.color)
        self.highlight.setStrength(0.0)
        self.setGraphicsEffect(self.highlight)

    def change_icon(self, path):
        self.icon = path
        self.item_image = validate_image_path(self.icon)
        self.item_image = self.item_image.scaled(self.icon_size[0],self.icon_size[1],QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
        self.item_pixmap.convertFromImage(self.item_image)
        self.setPixmap(self.item_pixmap)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            for callback in self.callback: 
                callback(event)

    def enterEvent(self, event):
        self.highlight.setStrength(self.strength)
        self.update()

    def leaveEvent(self, event):
        self.highlight.setStrength(0.0)
        self.update()

class GraphicLabel(QtWidgets.QLabel):
    def __init__(self, icon="", size=(32,32)):
        super(GraphicLabel, self).__init__()

        self.icon = icon
        self.icon_size = size
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Fixed) # better+flexible than setfixedsized

        self.initUI()

    def initUI(self):
        self.item_image = validate_image_path(self.icon)
        self.item_image = self.item_image.scaled(self.icon_size[0],self.icon_size[1],QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
        self.item_pixmap = QtGui.QPixmap()
        self.item_pixmap.convertFromImage(self.item_image)
        self.setPixmap(self.item_pixmap)
    
    def change_icon(self, path, icon=None):
        self.icon = path
        self.item_image = validate_image_path(self.icon)
        if icon: self.icon_size = icon
        self.item_image = self.item_image.scaled(self.icon_size[0],self.icon_size[1],QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation)
        self.item_pixmap.convertFromImage(self.item_image)
        self.setPixmap(self.item_pixmap)

class ValidableGraphicLabel(GraphicLabel):
    def __init__(self, icon='', size=(32,32)):
        super().__init__(icon, size)

    def initUI(self):
        super().initUI()

        self.validator_icon = GraphicLabel(get_path('warning2.png', icon=True), (self.icon_size[0]/1.8,self.icon_size[1]/1.8))
        self.validator_icon.setParent(self)
        #self.validator_icon.move(self.width()/2,-2)   # offset by 2 on x and y axis (somehow it's not shown again if moved?)
        self.validator_icon.hide()

    def set_valid(self, valid=True):
        if valid == True: self.validator_icon.hide()
        else: self.validator_icon.show()

class LabelButton(QtWidgets.QLabel):
    def __init__(self, text, callback=None, color=QtGui.QColor('white'), strength=0.25):
        super().__init__(text)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.callback = []
        if callback: self.callback.append(callback)
        self.color = color
        self.strength = strength

        self.initUI()

    def initUI(self):
        # set highlight mouse hover effect
        self.highlight = QtWidgets.QGraphicsColorizeEffect()
        self.highlight.setColor(self.color)
        self.highlight.setStrength(0.0)
        self.setGraphicsEffect(self.highlight)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton: 
            for callback in self.callback: 
                callback(event)

    def enterEvent(self, event):
        self.highlight.setStrength(self.strength)
        self.update()

    def leaveEvent(self, event):
        self.highlight.setStrength(0.0)
        self.update()

class ShortLabel(QtWidgets.QLabel):
    def __init__(self, text='', max_char=50):
        super().__init__()

        self.full_text = text
        self.max_char = max_char
        self.setText(text) # automatic check for text length
        
    def setText(self, text):
        self.full_text = text
        if len(text) > self.max_char+3: # +3 for 3 dots (ex. text...)
            trunc_text = text[:self.max_char]
            self.truncateText(trunc_text)
        else:
            super().setText(text)

    def truncateText(self, text):
        self.setText(text+"...")

class LimitedLabel(QtWidgets.QLabel):
    def __init__(self, text='', max_length=30, parent=None):
        super().__init__(text, parent)
        self.max_length = max_length
        if self.max_length < 4: self.max_length = 4 # MINIMUM TEXT
        self.truncateText() # check if pass limit, else change nothing
    
    def truncateText(self):
        if len(self.text()) > self.max_length:
            truncated_text = self.text()[:self.max_length-3]+"..."
            self.setText(truncated_text)
    
    def setText(self, str):
        super().setText(str)
        self.truncateText()

class NameableLabel(QtWidgets.QWidget):
    def __init__(self, text='', max_char = 100, parent=None):
        super().__init__(parent)

        self.max_char = max_char
        self._text = text
        self.previous_text = text  # keep track of last text to revert_text

        self.initUI()
        self.initConnection()
        self.update_text(self.text) # update text if it needed to truncate

    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, text):
        if self.text != text:
            self.previous_text = self.label.text()
            self.update_text(text)
            self.renameEvent(self.text)

    def initUI(self):
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)

        self.label = QtWidgets.QLabel(self.text)
        self.line_edit = QtWidgets.QLineEdit(self.text)
        self.line_edit.hide()

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.line_edit)

        # overwrite virtual function
        self.line_edit.focusOutEvent = self.onEnter

    def initConnection(self):
        self.line_edit.returnPressed.connect(self.onEnter)

    def update_text(self, text):
        """update widget text"""
        self._text = text
        if len(text) > self.max_char:
            trunc_text = self.truncateText(text)
            self.label.setText(trunc_text)
        else:
            self.label.setText(text)
        self.line_edit.setText(text)

    def revert_changes(self):
        self.update_text(self.previous_text)

    def truncateText(self, text):
        truncated_text = text[:self.max_char-3]+"..."
        return truncated_text

    def mouseDoubleClickEvent(self, event):
        self.label.hide()
        self.line_edit.setMinimumWidth(self.label.width())
        self.line_edit.show()
        self.line_edit.setFocus()

    def onEnter(self, event=None):
        if self.line_edit.text() != self.label.text() and self.line_edit.text() != "":
            self.text = self.line_edit.text()
        self.label.show()
        self.line_edit.hide()
        self.setFocus()

    def renameEvent(self, event):
        """Virtual function called when rename label"""

class InteractiveItemContainer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # system data (contain selected item inside scroll)
        self._selected_item = []

        self.initUI()

    @property
    def selected_item(self):
        return self._selected_item
    
    @selected_item.setter
    def selected_item(self, value):
        self._selected_item = value
        self.onModifySelectedItem()

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)

    def get_all_item(self):
        return [self.main_layout.itemAt(i).widget() for i in range(self.main_layout.count())]

    def add_item(self, instance):
        """helper function to add item that doesnt have container"""
        instance.container = self   # automaticlly add widget to container main layout

    def remove_item(self, items):
        """removing item but doesnt delete the item, only detach from container"""
        for item in items:
            item.setParent(None)    # somehow need to unparent, or else program still detect widget inside main_layout
            item.selected = False   # prevent bug, when undo item on select mode
            item.container = None    # remove container also (it can be a way for item to detect if it already removed)
        new_selected = [item for item in self.selected_item if item not in items]
        self.selected_item = new_selected

    # DEPRECATED, following current architecture we still want to conserve the pyqt c++ object reference
    def delete_item(self, items):
        """helper function to delete item completely and detach from container"""
        for item in items:
            item.setParent(None)
            item.deleteLater()
        new_selected = [item for item in self.selected_item if item not in items]
        self.selected_item = new_selected

    def clear_all_item(self):
        """only unparent but still preserve the memory address"""
        for index in reversed(range(self.main_layout.count())):
            widget = self.main_layout.itemAt(index).widget()
            widget.setParent(None)
        self.deselect_all()
        #widget.deleteLater()   # this would free the memory, also delete the object or item inside

    def modify_selection(self, item, add=False):
        """add or remove selection to container .like cmds.select in maya"""
        if add:
            if item in self.selected_item: return
            self.selected_item.append(item)
            item.selected = True
        else:
            self.reset_selection([item])

    def reset_selection(self, new_selection=None):
        """If nothing given, will basically clear anything. if given will clear anything and select the given arg"""
        for item in self.selected_item:
            item.selected = False
        self.selected_item.clear()
        if new_selection:
            self.selected_item = new_selection  # to trigger modified selection
            for item in new_selection:
                item.selected = True

    def delete_selected(self):
        if self.selected_item:
            for item in self.selected_item:
                item.deleteLater()
                item.setParent(None)
            self.selected_item = []
    
    def deselect_item(self, items):
        for item in items:
            if item in self.selected_item:
                item.selected = False
                self.selected_item.remove(item)

    def deselect_all(self):
        if self.selected_item:
            for item in self.selected_item:
                item.selected = False
            self.selected_item = []

    def onModifySelectedItem(self):
        """virtual function when selected item assigned with value"""
            
# shouldn't be used alone, recommended used with InteractiveItemSystem
class InteractiveItem(QtWidgets.QFrame):
    def __init__(self, container=None): 
        super().__init__()

        self.setObjectName('selectiveFrame')
        self.setStyleSheet('InteractiveItem#selectiveFrame{border: 1px solid #101010}')


        self._selected = False # use for highlight asset and trigger details tab
        self.hovered = False
        self.container = container  # trigger to parent item to container
        
        #self.setFocusPolicy(QtCore.Qt.ClickFocus)
        
        self.initUI()

    @property
    def container(self):
        return self._container
    
    @container.setter
    def container(self, container):
        self._container = container
        if self.container:  self._container.main_layout.addWidget(self)

    @property
    def selected(self):
        return self._selected
    
    @selected.setter
    def selected(self, select):
        if self.container:
            self._selected = select
            self.paintBorder()
            if select: self.selectEvent(self.container.selected_item)

    def initUI(self):
        #self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)
        #self.setLineWidth(2)
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_widget = QtWidgets.QWidget()
        self.main_layout.addWidget(self.main_widget)

    def onClickCtrl(self):
        if self.selected:
            self.container.selected_item.remove(self)
            self.selected = False
        else:
            self.container.modify_selection(self, add=True)

    def onClickShift(self):
        if self.container.selected_item:
            last_item = self.container.selected_item[-1]
            last_index = self.container.main_layout.indexOf(last_item)
            current_index = self.container.main_layout.indexOf(self)
            for index in range(min(last_index, current_index), max(last_index, current_index)+1):
                item = self.container.main_layout.itemAt(index).widget()
                item.container.modify_selection(item, add=True)
        else:
            self.container.modify_selection(self, add=True)

    def selectEvent(self, select):
        """virtual function, called when select object"""

    def mousePressEvent(self, event):
        # Dispatch Qt's mousePress event to corresponding function below
        if event.button() == QtCore.Qt.LeftButton and self.container:
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                self.onClickShift()
            elif event.modifiers() & QtCore.Qt.ControlModifier:
                self.onClickCtrl()
            else: 
                self.container.reset_selection([self])
        else: super().mousePressEvent(event)
        
    def enterEvent(self, event):
        self.hovered = True
        self.paintBorder()

    def leaveEvent(self, event):
        self.hovered = False
        self.paintBorder()

    def focusOutEvent(self, event):
        if self.selected and event.reason() != QtCore.Qt.FocusReason.PopupFocusReason : 
            self.selected = False

    def paintBorder(self):
        if self.selected:
            self.setStyleSheet('InteractiveItem#selectiveFrame{border: 1px solid #FFA500}')
        elif self.hovered:
            self.setStyleSheet('InteractiveItem#selectiveFrame{border: 1px solid #1363bf}')
        else:
            self.setStyleSheet('InteractiveItem#selectiveFrame{border: 1px solid #101010}')

class ExpandableWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.collapsed = True
    
    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(3,0,0,0)    # cheating to align old folder with maya file icon in EZMAssetStruct
        self.header_layout = QtWidgets.QHBoxLayout()
        self.content_scroll = QtWidgets.QScrollArea()
        self.content_scroll.setStyleSheet('background-color:#303030')
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setMinimumHeight(120)
        self.content_widget = QtWidgets.QWidget()
        self.content_scroll.setWidget(self.content_widget)
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5,5,5,5)
        self.content_layout.addStretch()

        self.expand_icon = GraphicButton(get_path('expand.png', icon=True), self.toggle_detail, QtGui.QColor('white'),1,(12,12))

        self.header_layout.addWidget(self.expand_icon)
        
        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addWidget(self.content_scroll)

        self.content_scroll.hide()

    def add_item(self, widget):
        self.content_layout.insertWidget(0, widget)

    def remove_widget(self, widget):
        widget.setParent(None)

    def toggle_detail(self, event):
        if self.collapsed:
            self.content_scroll.show()
            self.expand_icon.change_icon(get_path('collapse.png', icon=True))
            self.collapsed = False
        else:
            self.content_scroll.hide()
            self.expand_icon.change_icon(get_path('expand.png', icon=True))
            self.collapsed = True

# reference: https://github.com/Fus3n/PySnipTool/blob/main/Capturer.py
class screenCapture(QtWidgets.QDialog):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.main_window.hide()

        self.setMouseTracking(True)

        desk_size = QtCore.QRect(0, 0, 0, 0)
        window_size = QtCore.QRect(0, 0, 0, 0)
        # get all screen independently and calculate the device ratio, cause qt6 seems to doesnt support scale settings to match display hardware configuration
        # https://doc.qt.io/qt-6/highdpi.html#device-independent-screen-geometry
        pixelRatioPrimary = QtWidgets.QApplication.primaryScreen().devicePixelRatio()
        for screen in QtWidgets.QApplication.screens():
            geo = screen.geometry()
            real_scale = screen.devicePixelRatio()
            if screen == QtWidgets.QApplication.primaryScreen(): 
                desk_rect = QtCore.QRect(geo.x(), geo.y(), geo.width(), geo.height())
                window_rect = QtCore.QRect(geo.x(), geo.y(), geo.width()*real_scale, geo.height()*real_scale)
                desk_size = desk_size.united(desk_rect)
                window_size = window_size.united(window_rect)
                continue
            print('geo > ', geo)
            print(pixelRatioPrimary)
            scale = screen.devicePixelRatio()
            #print('scale > ', scale)
            desk_rect = QtCore.QRect(geo.x()/pixelRatioPrimary, geo.y()/pixelRatioPrimary, geo.width()/pixelRatioPrimary*scale, geo.height()/pixelRatioPrimary*scale)
            window_rect = QtCore.QRect(geo.x(), geo.y(), geo.width()*real_scale, geo.height()*real_scale)
            print('desk_rect > ', desk_rect)
            print('window rect > ', window_rect)
            desk_size = desk_size.united(desk_rect)
            window_size = window_size.united(window_rect)

        # print('')
        print('final desktop size ', desk_size)
        print('final window size ', window_size)

        self.setGeometry(window_size.x(), window_size.y(), window_size.width(), window_size.height())
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.25)

        self.rubber_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.origin = QtCore.QPoint()

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CrossCursor)
        screen = QtWidgets.QApplication.primaryScreen()

        time.sleep(0.3)
        self.imgmap = screen.grabWindow(0, desk_size.x(), desk_size.y(), desk_size.width(), desk_size.height())

    def mousePressEvent(self, event: QtGui.QMouseEvent | None) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())
            self.rubber_band.show() 

    def mouseMoveEvent(self, event: QtGui.QMouseEvent | None) -> None:
        #if not self.origin.isNull(): # idk why if it enable you can drag from (0,0) screen position
        self.rubber_band.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent | None) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.rubber_band.hide()
            
            rect = self.rubber_band.geometry()    # old is geometry
            self.capturedImg = self.imgmap.copy(rect)
            QtWidgets.QApplication.restoreOverrideCursor()

            # set picture to clipboard
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setPixmap(self.capturedImg)

            self.main_window.thumbnail_lbl.setPixmap(self.capturedImg.scaled(QtCore.QSize(500, 500), 
                                      aspectMode=QtCore.Qt.KeepAspectRatio,
                                      mode=QtCore.Qt.SmoothTransformation))  # hard-code for parent to use this name

            self.main_window.show()
            self.close()

    def getScreenshot(self):
        return self.capturedImg

class simpleCheckBox(QtWidgets.QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signature_color = QtGui.QColor('white')

    def change_signature_color(self, color):
        self.signature_color = color
        self.update()

    # credit: https://stackoverflow.com/questions/71630498/qt-custom-checkbox-help-about-paintevent
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)

        size = min(self.width(), self.height())
        border = max(0.75, size / 32)
        rect = QtCore.QRectF(0, 0, size - border, size - border)
        # move the square to the *exact* center using a QRectF based on the
        # current widget; note: it is very important that you get the center
        # using a QRectF, because the center of QRect is always in integer
        # values, and will almost always be imprecise at small sizes
        rect.moveCenter(QtCore.QRectF(self.rect()).center())

        borderPath = QtGui.QPainterPath()
        # with RelativeSize we can specify the radius as 30% of half the size
        borderPath.addRoundedRect(rect, 30, 30, QtGui.Qt.RelativeSize)
        painter.setPen(QtGui.QPen(self.signature_color, border * 2.5))
        painter.drawPath(borderPath)
        
        if self.isChecked():
            painter.setBrush(self.signature_color)
            painter.drawPath(borderPath)

            painter.setPen(QtGui.QPen(QtCore.Qt.white, size * .125,c=QtCore.Qt.RoundCap, j=QtCore.Qt.RoundJoin))
            arrow_path = QtGui.QPainterPath()
            arrow_path.moveTo(size * .25, size * .5)
            arrow_path.lineTo(size * .40, size * .65)
            arrow_path.lineTo(size * .7, size * .325)
            painter.drawPath(arrow_path.translated(rect.topLeft()))

class simpleButton(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor('white')
  
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
        painter.setBrush(self.color)
        rect = QtCore.QRectF(0, 0, self.width(), self.height())
        painter.drawRoundedRect(rect,30,30,QtCore.Qt.RelativeSize)
        return
        size = min(self.width(), self.height())
        
        painter.setPen(QtGui.QPen(QtCore.Qt.white, size * .125,c=QtCore.Qt.RoundCap, j=QtCore.Qt.RoundJoin))
        arrow_path = QtGui.QPainterPath()
        arrow_path.moveTo(size * .25, size * .5)
        arrow_path.lineTo(size * .40, size * .65)
        arrow_path.lineTo(size * .7, size * .325)
        painter.drawPath(arrow_path.translated(rect.topLeft()))

class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, tolerance=40):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))

        self._item_list = []
        self.tolerance = tolerance # tolerance size when next widget push to new row

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QtCore.QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x - self.tolerance > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()