"""
TODO: use NTP or any other method that always try to sync the date, prevent when localtime is not accurate
"""
from collections import OrderedDict

from PySide6 import QtCore, QtWidgets, QtGui

from util import *

import calendar
import datetime
import json

import custom_widget

DEBUG = True
TO_DO_DATA = os.path.join(get_path(), 'data', 'to_do_data.json')

# step
# 1. get current date
# 2. from current date initiate this year and also before and after this year (3 year/36 month max)

class EZMCalendarWidget(QtWidgets.QWidget):
    """This class include calendar system that have to_do (for basic note) or assignment object (for asset)"""
    def __init__(self, app):
        self.app = app
        self.today_dates = datetime.datetime.now()
        self.weekday_name = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

        # cache
        self.selectedDate = None
        self.to_do_list_data = {}   # date (year, month, day) (key) : list of to_do obj (value) (not include asset assignment)
        self.asset_data = {}    # date (year, month, day) (key) : list of asset obj (value) (only include asset)
        self.date_obj = {}  # date (year, month, day) (key) : date widget
        
        self._is_modified = False

        super().__init__()
        self.initUI()
        self.load_data()
        self.load_date()
    
    @property
    def is_modified(self):
        return self._is_modified
    
    @is_modified.setter
    def is_modified(self, value=True):
        self._is_modified = value
        dock_widget = self.parent()
        if dock_widget:
            if value: 
                dock_widget.setWindowTitle('Calendar Editor *')
            else:
                dock_widget.setWindowTitle('Calendar Editor ')

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.header_layout = QtWidgets.QHBoxLayout()
        self.calendar_grid_layout = QtWidgets.QGridLayout()

        self.month_font = QtGui.QFont('Ubuntu', 16)
        self.month_lbl = QtWidgets.QLabel(str(self.today_dates.strftime("%B %Y")))
        self.month_lbl.setFont(self.month_font)
        self.previous_btn = custom_widget.GraphicButton(get_path('left.png',icon=True),self.previous_page,QtGui.QColor('white'),1,(16,16))
        self.next_btn = custom_widget.GraphicButton(get_path('right.png',icon=True),self.next_page,QtGui.QColor('white'),1,(16,16))

        self.detail_separator = QtWidgets.QFrame()
        self.detail_separator.setFrameShape(QtWidgets.QFrame.HLine)
        self.detail_separator.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Minimum)
        self.detail_separator.setLineWidth(1)

        self.detail_tab = EZMDateDetail(self)

        self.header_layout.addWidget(self.month_lbl)
        self.header_layout.addWidget(self.previous_btn)
        self.header_layout.addSpacing(15)
        self.header_layout.addWidget(self.next_btn)

        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addSpacing(10)
        self.main_layout.addLayout(self.calendar_grid_layout)
        self.main_layout.addWidget(self.detail_separator)
        self.main_layout.addWidget(self.detail_tab)

    def load_date(self):
        self.previewed_year_month = (self.today_dates.year, self.today_dates.month) # hold the active preview year and month of UI (not current local time)
        self.load_calendar(self.previewed_year_month[0], self.previewed_year_month[1])

    def load_data(self):
        try:
            data_dir = os.path.join(get_path(),'data')
            json_dir = os.path.join(data_dir, 'to_do_data.json')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            if not os.path.exists(json_dir):
                open(json_dir, "w")
            with open(TO_DO_DATA, 'r') as file:
                raw_data = file.read()
                if raw_data:    # check if not empty
                    data = json.loads(raw_data)
                    self.deserialize(data)
        except Exception as e: print(e)

    def save_data(self):
        if DEBUG: print('save to_do data')
        try:
            with open(TO_DO_DATA, 'w') as file:
                file.write(json.dumps(self.serialize(), indent=4))
            self.is_modified = False
        except Exception as e: print('ERROR whike saving calendar data: ' + str(e))

    def update_calendar(self):
        for date in self.date_obj:
            self.date_obj[date].update()

    def load_calendar(self, year, month):
        if DEBUG: print('loading calendar > month: %s and year: %s'%(month, year))
        self.clear_calendar()
        self.current_dates_of_month = self.get_full_dates_of_month(year, month)
        first_row_offset = int(self.current_dates_of_month[0].strftime("%w"))+7   # find offset on first row (from start of day in month)
        positions = [(i,j) for i in range(7) for j in range(7)]
  
        day = 0 
        for index, position in enumerate(positions):
            if index >= first_row_offset and not day == len(self.current_dates_of_month):
                widget = EZMDateWidget(self, self.current_dates_of_month[day])   # symbol (#) to remove leading zero. it's said only on windows tho
                self.load_date_data(self.current_dates_of_month[day], widget)
                day +=1
            elif index < 7: # name of the week
                widget = QtWidgets.QLabel(self.weekday_name[index])
            elif index < first_row_offset and index >= 7: # before start of month (Calendar/datetime)
                date_before_this_month = self.current_dates_of_month[0]-datetime.timedelta(days=first_row_offset-index)
                widget = EZMDateWidget(self, date_before_this_month, True)
                self.load_date_data(date_before_this_month, widget)
            elif day == len(self.current_dates_of_month):    # after start of month (Calendar/datetime)
                date_after_this_month = self.current_dates_of_month[-1]+datetime.timedelta(days=index+1-len(self.current_dates_of_month)-first_row_offset)
                widget = EZMDateWidget(self, date_after_this_month, True)
                self.load_date_data(date_after_this_month, widget)
            self.calendar_grid_layout.addWidget(widget, *position, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # set text and data
        self.month_lbl.setText(("%s %s"%(calendar.month_name[month],year)))
        self.previewed_year_month = (year, month)

    def load_date_data(self, date, widget):
        self.add_data_to_this_date(date, widget)
        self.date_obj[date.strftime("%d/%m/%Y")] = widget

    def clear_calendar(self):
        self.selectedDate = None # remove selection
        self.detail_tab.clear_detail()
        for key in self.date_obj:
            self.date_obj[key].setParent(None)
            self.date_obj[key].deleteLater()
        self.date_obj = {}

        # cleanup after date_obj deleted (before and after date of this month ultimately)
        # https://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt (thx for suggestion!)
        while self.calendar_grid_layout.count():
            child = self.calendar_grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def add_data_to_this_date(self, date, widget):
        """load todolist or assignment data if available on given date"""
        # check to_do data
        if date.strftime("%d/%m/%Y") in self.to_do_list_data: 
            for to_do in self.to_do_list_data[date.strftime("%d/%m/%Y")]:
                widget.add_to_do(to_do['description'], to_do['checked'], False)
        # check asset data
        if date.strftime("%d/%m/%Y") in self.asset_data:
            for asset in self.asset_data[date.strftime("%d/%m/%Y")]:
                widget.add_assignment(asset)

    def add_asset(self, date_key, asset):
        """function to provide access for asset manager to add assignment data"""
        # add asset data first (so calendar can load it to calendar, when user change month)
        data_list = []
        if date_key in self.asset_data:
            data_list = self.asset_data[date_key]
        data_list.append(asset)
        self.asset_data[date_key] = data_list
        # add asset assignment (add assignment on date widget will automatically load it in)
        if date_key in self.date_obj:   # check if assignment month is the same as previewed, else don't add_assignment yet
            date_widget = self.date_obj[date_key]
            date_widget.add_assignment(asset)
            if date_widget == self.selectedDate: self.detail_tab.load_detail(date_widget.active_assignment.values(), date_widget.active_todolist)    # update detail again
  
    def select_by_datekey(self, datekey):
        """provide helper function to select date widget by datekey"""
        if not datekey in self.date_obj: return False # check if datekey on current month
        date = self.date_obj[datekey]
        self.detail_tab.load_detail(date.active_assignment.values(), date.active_todolist)
    
        # refresh ui
        if self.selectedDate:
            self.selectedDate.setStyleSheet('EZMDateWidget#dateFrame{border: 0px solid #101010}')
        self.selectedDate = date
        date.setStyleSheet('EZMDateWidget#dateFrame{border: 1px solid #FFA500}')

    def next_page(self, event):
        year, month = calendar._nextmonth(self.previewed_year_month[0], self.previewed_year_month[1])
        self.load_calendar(year, month)

    def previous_page(self, event):
        year, month = calendar._prevmonth(self.previewed_year_month[0], self.previewed_year_month[1])
        self.load_calendar(year, month)

    def get_full_dates_of_month(self, year, month):
        number_days = calendar.monthrange(year, month)[1]
        days_on_this_month = [datetime.date(year, month, day) for day in range(1, number_days+1)]
        return days_on_this_month

    def serialize(self):
        return self.to_do_list_data # just return data again

    def deserialize(self, data):
        self.to_do_list_data = data # just put it here

class EZMDateDetail(QtWidgets.QWidget):
    def __init__(self, calendar):
        super().__init__()
        self.calendar = calendar
        self.initUI()
    
    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.header_layout = QtWidgets.QHBoxLayout(self)

        self.add_btn = QtWidgets.QPushButton('create')
        self.add_btn.clicked.connect(self.add_to_do)
        self.add_btn.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        self.add_btn.setStyleSheet('background-color:#BF138C')
        self.add_btn.setIcon(QtGui.QIcon(QtGui.QPixmap(get_path('add.png',icon=True))))

        self.checked_lbl = custom_widget.GraphicLabel(get_path('checked_2.png',icon=True),(20,20))
        self.checked_count_lbl = QtWidgets.QLabel('0')
        self.checked_count_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Minimum) #TODO might not be best solution? what if assignment more than 999? also note for unchecked below
        self.unchecked_lbl = custom_widget.GraphicLabel(get_path('unchecked_2.png',icon=True),(20,20))
        self.unchecked_count_lbl = QtWidgets.QLabel('0')
        self.unchecked_count_lbl.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Minimum)   #TODO same as above

        self.scroll_content = QtWidgets.QScrollArea()
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_widget.setStyleSheet('background-color: #252528')
        self.scroll_content.setWidgetResizable(True)
        self.scroll_content.setWidget(self.scroll_widget)
        self.content_layout = QtWidgets.QVBoxLayout()
        self.scroll_widget_layout = QtWidgets.QVBoxLayout(self.scroll_widget)
        self.scroll_widget_layout.addLayout(self.content_layout)
        self.scroll_widget_layout.addStretch()

        self.header_layout.addWidget(self.add_btn)
        self.header_layout.addWidget(self.checked_lbl)
        self.header_layout.addWidget(self.checked_count_lbl)
        self.header_layout.addWidget(self.unchecked_lbl)
        self.header_layout.addWidget(self.unchecked_count_lbl)

        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addWidget(self.scroll_content)

    def add_to_do(self):
        if self.calendar.selectedDate:
            widget = self.calendar.selectedDate.add_to_do()
            self.content_layout.addWidget(widget)

    def load_detail(self, assignment=[], todolist=[]):
        self.clear_detail()

        self.checked = 0
        self.unchecked = 0

        # load assignment
        for assign in assignment:
            self.content_layout.addWidget(assign)
            if assign.isChecked: self.checked +=1
            else: self.unchecked += 1

        # load todolist
        for todo in todolist:
            self.content_layout.addWidget(todo)
            if todo.isChecked: self.checked +=1
            else: self.unchecked += 1

        self.checked_count_lbl.setText(str(self.checked))
        self.unchecked_count_lbl.setText(str(self.unchecked))

    def update_detail(self, all_checkbox=[]): 
        self.checked = 0
        self.unchecked = 0

        for widget in all_checkbox:
            if widget.isChecked: self.checked += 1
            else: self.unchecked += 1

        self.checked_count_lbl.setText(str(self.checked))
        self.unchecked_count_lbl.setText(str(self.unchecked))           

    def clear_detail(self):
        self.checked_count_lbl.setText('0')
        self.unchecked_count_lbl.setText('0')
        for index in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(index).widget()
            widget.setParent(None)

class EZMDateWidget(QtWidgets.QFrame):
    def __init__(self, calendar, date, another_month=False, parent=None):
        self.calendar = calendar # calendar editor/system
        self.date = date            
        self.active_todolist = {}    # todo checkbox class (key) : detail/obj (desc + check status) (value)
        self.active_assignment = {}  # asset (key) : assignment checkbox (value) (REVERSED REMEMBER!)
        self.another_month = another_month
        
        # ui related cache
        self.incompleted_assignment = []
        self.incompleted_todolist = []
        self.completed_task = []

        super().__init__(parent)
        self.setObjectName('dateFrame')
        self.initUI()

    def initUI(self):
        self.setFixedSize(40,40)
        #self.setStyleSheet('EZMDateWidget#dateFrame{border: 1px solid #101010}')   # default style when loaded
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.date_lbl = QtWidgets.QLabel(self.date.strftime("%#d"))
        self.main_layout.addWidget(self.date_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        if self.calendar.today_dates.strftime("%d/%m/%Y") == self.date.strftime("%d/%m/%Y"):
            font = QtGui.QFont()
            font.setBold(True)
            self.date_lbl.setFont(font)
            self.date_lbl.setStyleSheet('color:orange')
        if self.another_month:
            self.date_lbl.setStyleSheet('color:gray')

    def onAddRemoveCheckboxData(self):
        """help update ui for calendar and details, need to call manually when removing or appending data to active assignment or todolist (no need for changing checked/unchecked)"""
        self.update()
        if self == self.calendar.selectedDate:
            self.calendar.detail_tab.update_detail(list(self.active_assignment.values())+list(self.active_todolist))    # append 2 data

    def enterEvent(self, event):
        if self.calendar.selectedDate == self: return
        #self.setStyleSheet('EZMDateWidget#dateFrame{background-color:#ff4da6}')
        self.setStyleSheet('EZMDateWidget#dateFrame{border: 1px solid #FFFFFF}')

    def leaveEvent(self, event):
        if self.calendar.selectedDate == self: return
        #self.setStyleSheet('EZMDateWidget#dateFrame{background-color:none}')
        self.setStyleSheet('EZMDateWidget#dateFrame{border: 0px solid #101010}')

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # check if calendar has other selected present
            if self.calendar.selectedDate :
                self.calendar.selectedDate.setStyleSheet('EZMDateWidget#dateFrame{border: 0px solid #101010}')
            self.calendar.selectedDate = self
            self.calendar.detail_tab.load_detail(self.active_assignment.values(), self.active_todolist)
            self.setStyleSheet('EZMDateWidget#dateFrame{border: 1px solid #FFA500}')

    def update_todolist_data(self, modified=True):
        """will always update to calendar editor all to_do data, to keep up with latest changes"""
        date_key = self.date.strftime("%d/%m/%Y")
        self.calendar.to_do_list_data[date_key] = list(self.active_todolist.values())
        # check if current date has any other to_do, if not will delete the key also from calendar (garbage collector)
        if self.calendar.to_do_list_data[date_key] == []: del self.calendar.to_do_list_data[date_key]
        if modified: self.calendar.is_modified = True

    def update_assignment_data(self):
        """will always update to calendar editor all assignment data, to keep up with latest changes"""
        date_key = self.date.strftime("%d/%m/%Y")
        self.calendar.asset_data[date_key] =  list(self.active_assignment.keys())

    def add_to_do(self, description='description', checked=False, modified=True):
        to_do_widget = EZMTodoCheckbox(self, description, checked)
        self.active_todolist[to_do_widget] = to_do_widget.serialize()
        self.update_todolist_data(modified)
        self.onAddRemoveCheckboxData()
        return to_do_widget

    def add_assignment(self, asset):
        assignment_widget = EZMAssignmentCheckbox(self, asset)
        self.active_assignment[asset] = assignment_widget
        self.update()   # call refresh ui
        return assignment_widget

    def paintEvent(self, event=None):
        painter = QtGui.QPainter(self)
        left_start = self.width()/6
        assignment = False
        to_do = False
        if self.incompleted_assignment:
            brush = QtGui.QBrush(QtGui.QColor('orange'))
            if self.another_month:
                brush = QtGui.QBrush(QtGui.QColor('DarkSalmon'))
            painter.setBrush(brush)
            painter.drawRoundedRect(left_start,self.height()/1.3,7,7,5,5)
            assignment = True
        if self.incompleted_todolist:
            if assignment: left_start += 10
            brush = QtGui.QBrush(QtGui.QColor('DeepSkyBlue'))
            if self.another_month:
                brush = QtGui.QBrush(QtGui.QColor('SteelBlue'))
            painter.setBrush(brush)
            painter.drawRoundedRect(left_start,self.height()/1.3,7,7,5,5)
            to_do = True
        if self.completed_task:
            if to_do or assignment: left_start += 10
            brush = QtGui.QBrush(QtGui.QColor('lime'))
            if self.another_month:
                brush = QtGui.QBrush(QtGui.QColor('OliveDrab'))
            painter.setBrush(brush)
            painter.drawRoundedRect(left_start,self.height()/1.3,7,7,5,5)

class EZMTodoCheckbox(QtWidgets.QWidget):
    def __init__(self, date_widget, description='description', checked=False):
        self.date_widget = date_widget # hold the date widget parent
        self.description = description
        self.isChecked = checked

        super().__init__()
        self.initUI()
        self.initConnection()

    @property
    def isChecked(self):
        return self._isChecked
    
    @isChecked.setter
    def isChecked(self, value):
        self._isChecked = value
        if self.isChecked:
            self.date_widget.completed_task.append(self)
            if self in self.date_widget.incompleted_todolist: self.date_widget.incompleted_todolist.remove(self)
        else:
            self.date_widget.incompleted_todolist.append(self)
            if self in self.date_widget.completed_task: self.date_widget.completed_task.remove(self)
        self.date_widget.update()

    def initUI(self):
        self.setStyleSheet('background-color:none') # override bg color from parent to avoid unwanted graphic effect
        self.main_layout = QtWidgets.QHBoxLayout(self)

        self.checkbox = custom_widget.simpleCheckBox()
        self.checkbox.change_signature_color(QtGui.QColor('DodgerBlue'))   # change signature color of checkbox for todo
        self.checkbox.setMinimumSize(16,16)
        self.checkbox.setChecked(self.isChecked)
        self.description_lbl = custom_widget.NameableLabel(self.description, 100)
        self.description_lbl.renameEvent = self.onRenameDescription
        self.delete_btn = custom_widget.GraphicButton(get_path("exit.png",icon=True), self.deleteThis,  size=(16,16))

        self.main_layout.addWidget(self.checkbox)
        self.main_layout.addWidget(self.description_lbl)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.delete_btn)

    def initConnection(self):
        self.checkbox.clicked.connect(self.onCheck)

    def onRenameDescription(self, text):
        self.date_widget.active_todolist[self] = self.serialize()
        self.date_widget.update_todolist_data()

    def onCheck(self):
        self.isChecked = not self.isChecked # flip current checkbox whenever triggered
        self.date_widget.active_todolist[self] = self.serialize()
        self.date_widget.update_todolist_data()
        self.date_widget.calendar.detail_tab.update_detail(list(self.date_widget.active_assignment.values())+list(self.date_widget.active_todolist))

    def deleteThis(self, event=None):
        del self.date_widget.active_todolist[self]
        self.setParent(None)
        self.deleteLater()
        self.remove_UI_data()
        self.date_widget.update_todolist_data() 
        self.date_widget.onAddRemoveCheckboxData()
        
    def remove_UI_data(self):
        """handle removing ui related data to date widget"""
        if self in self.date_widget.incompleted_todolist:
            self.date_widget.incompleted_todolist.remove(self)
        if self in self.date_widget.completed_task:
            self.date_widget.completed_task.remove(self)

    def serialize(self):
        dict = OrderedDict([('description', self.description_lbl.text),
                            ('checked', self.isChecked)])
        return dict

class EZMAssignmentCheckbox(EZMTodoCheckbox):
    def __init__(self, date_widget, asset):
        self.project = asset.project
        self.asset = asset

        if self.asset.status == 2: checked = True     # if verified asset will checked it automatically
        else: checked = False

        super().__init__(date_widget, self.asset.name, checked)

    @property
    def isChecked(self):
        return self._isChecked
    
    @isChecked.setter
    def isChecked(self, value):
        self._isChecked = value
        if self.isChecked:
            self.date_widget.completed_task.append(self)
            if self in self.date_widget.incompleted_assignment: self.date_widget.incompleted_assignment.remove(self)
        else:
            self.date_widget.incompleted_assignment.append(self)
            if self in self.date_widget.completed_task: self.date_widget.completed_task.remove(self)
        self.date_widget.update()

    def initUI(self):
        super().initUI()
        self.checkbox.change_signature_color(QtGui.QColor('DarkOrange'))   # change signature color of checkbox for assignment
        self.search_btn = custom_widget.GraphicButton(get_path("external_link.png",icon=True), self.search_asset, strength=1, size=(16,16))
        self.main_layout.insertWidget(3,self.search_btn)

    def setCheck(self, value):
        """for asset update to checkbox"""
        self.isChecked = value
        self.checkbox.setChecked(value)

    def setDescription(self, text):
        """for asset update to description"""
        self.description = text
        self.description_lbl.text = text

    def onRenameDescription(self, text):
        # renaming description for asset, don't affect anything for now
        pass

    def onCheck(self):
        self.isChecked = not self.isChecked
        if self.isChecked: self.asset.status = 2
        else: self.asset.status = 0
        self.date_widget.calendar.detail_tab.update_detail(list(self.date_widget.active_assignment.values())+list(self.date_widget.active_todolist))

    def deleteThis(self, event=None):
        # ask for confirmation, since this action is undable
        warning = QtWidgets.QMessageBox.warning(self, 'delete assignment?', 'are you sure? this action is undoable',
                                                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if warning == QtWidgets.QMessageBox.Yes:
            del self.date_widget.active_assignment[self.asset]
            self.setParent(None)
            self.date_widget.update_assignment_data() 
            self.date_widget.onAddRemoveCheckboxData()
            self.asset.date_assignment = []
            self.remove_UI_data()
            
            # on mofidied assetscroll but without current project 
            self.asset.asset_scroll.toggle_asset_visibility()
            self.asset.project.browser.onModified(self.asset.project)
            self.asset.asset_scroll.manager.update_asset_detail(self.asset.asset_scroll.asset_container.selected_item)
            self.asset.asset_scroll.refresh()

    def remove_UI_data(self):
        """handle removing ui related data to date widget"""
        if self in self.date_widget.incompleted_assignment:
            self.date_widget.incompleted_assignment.remove(self)
        if self in self.date_widget.completed_task:
            self.date_widget.completed_task.remove(self)

    def search_asset(self, event):
        self.date_widget.calendar.app.go_to_asset(self.project)
        self.asset.select()
