from collections import OrderedDict

from PySide6 import QtCore, QtWidgets, QtGui

from app_assignment_widget import EZMCalendarWidget
from app_home_widget import EZMHome
from app_projects_widget import EZMProjectBrowser, EZMProjectItem
from app_assets_widget import EZMAssetManager
from app_extra_widget import EZMProjectWindow, EZMSettings
from app_history import *
from util import *

import json

import custom_widget

HOME_MENU = 0
PROJECT_MENU = 1
ASSET_MENU = 2

CONFIG = os.path.join(get_path(), 'data', 'user_config.json')

DEBUG = True

class EZMToolbar(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

        self.hierarchy = {}
        self.grouping = {} # this match order with hierarchy, containing which widget to show on certain page
        self.tools_widget = []

        self.current_history = None # match which history is active according to active tab/browser
        self._active_project = None # define which project user currently in

        self.project_paths = {} # contain all project file path

        self.initUI()
        self.initChildren()
        self.initAsset() # containing additional dialog bind to main widget
        self.load_config()
        self.initUndo() # after everything done create history to start record initial stamp
        self.change_page(PROJECT_MENU)  # setup default UI and hide unrelated label widget

    @property
    def active_project(self):
        return self._active_project
    
    @active_project.setter
    def active_project(self, project):
        self._active_project = project
        if project:
            self.main_window.statusBar().showMessage("Selected: 0   Total Asset: %s"%len(project.asset))
        else:
            self.main_window.statusBar().showMessage("(Offline) User: -")

    def initUI(self):
        # Project header widgets (by order left to right)
        self.big_text = QtGui.QFont('Ubuntu', 16)
        self.medium_text = QtGui.QFont('Ubuntu', 12)
        self.small_text = QtGui.QFont('Ubuntu', 8)

        self.home_btn = custom_widget.GraphicButton(get_path("home.png", icon=True),
                                                    callback=self.go_to_home,
                                                    color=QtGui.QColor('white'),
                                                    strength=1,
                                                    size=(16,16))
        
        self.welcome_label = QtWidgets.QLabel("Welcome")
        self.welcome_label.setFont(self.big_text)
        self.welcome_label.setStyleSheet('color:#cccccc')
        self.welcome_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Minimum)

        self.project_arrow = QtWidgets.QLabel(">")
        self.project_arrow.setFont(self.small_text)
        self.project_arrow.setStyleSheet('color:#cccccc')
        self.project_arrow.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Minimum)

        self.project_label = custom_widget.LabelButton("Projects", self.go_to_project, QtGui.QColor('white'), 1)
        self.project_label.setFont(self.big_text)
        self.project_label.setStyleSheet('color:#cccccc')

        self.project_name_arrow = QtWidgets.QLabel(">")
        self.project_name_arrow.setFont(self.small_text)
        self.project_name_arrow.setStyleSheet('color:#cccccc')
        self.project_name_arrow.setSizePolicy(QtWidgets.QSizePolicy.Fixed,QtWidgets.QSizePolicy.Minimum)

        self.project_name_label = EZMProjectLabel("...", color= QtGui.QColor('white'), strength=1)
        self.project_name_label.setFont(self.big_text)
        self.project_name_label.setStyleSheet('color:#cccccc')                                       

        self.new_project_btn = custom_widget.GraphicButton(get_path("add2.png", icon=True),
                                                        callback=self.new_project,
                                                        color=QtGui.QColor('white'),
                                                        strength=0.7,
                                                        size=(16,16))

        self.project_separator = QtWidgets.QFrame()
        self.project_separator.setFrameShape(QtWidgets.QFrame.HLine)
        self.project_separator.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Minimum)
        self.project_separator.setLineWidth(1)

        self.project_sorter = QtWidgets.QComboBox()
        self.project_sorter.addItems(["Last Updated", "Name", "Category"])
        self.project_sorter.textActivated.connect(self.project_sorter_changed)
        self.project_sorter.setMaximumWidth(120)

        self.asset_sorter = QtWidgets.QComboBox()
        self.asset_sorter.addItems(["Last Updated", "Priority", "Name", "Type"])
        self.asset_sorter.textActivated.connect(self.asset_sorter_changed)
        self.asset_sorter.setMaximumWidth(120)

        self.settings_btn = custom_widget.GraphicButton(get_path("settings.png", icon=True),
                                                        callback=self.open_settings,
                                                        color=QtGui.QColor('white'),
                                                        strength=0.75,
                                                        size=(16,16))

        self.stack = QtWidgets.QStackedWidget()

        # layout management
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.toolbar_layout = QtWidgets.QHBoxLayout()
        self.active_UI_layout = QtWidgets.QVBoxLayout()

        self.main_layout.addLayout(self.toolbar_layout)
        self.main_layout.addLayout(self.active_UI_layout)

        # add widget to layout
        self.toolbar_layout.addWidget(self.home_btn)
        self.toolbar_layout.addWidget(self.welcome_label)
        self.toolbar_layout.addWidget(self.project_arrow)
        self.toolbar_layout.addWidget(self.project_label)
        self.toolbar_layout.addWidget(self.project_name_arrow)
        self.toolbar_layout.addWidget(self.project_name_label)
        self.toolbar_layout.addWidget(self.new_project_btn)
        self.toolbar_layout.addWidget(self.project_separator)
        self.toolbar_layout.addWidget(self.project_sorter)
        self.toolbar_layout.addWidget(self.asset_sorter)
        self.toolbar_layout.addWidget(self.settings_btn) 

        self.active_UI_layout.addWidget(self.stack)

        # create list of all widget inside toolbar_layout
        count = self.toolbar_layout.count()
        for i in range(count): self.tools_widget.append(self.toolbar_layout.itemAt(i).widget())
        self.tools_widget.remove(self.home_btn)
        self.tools_widget.remove(self.project_separator)
        self.tools_widget.remove(self.settings_btn)

    def initChildren(self):
        self.home_UI = EZMHome(self)
        self.project_browser = EZMProjectBrowser(self)
        self.asset_manager = EZMAssetManager(self)

        # the grouping dict include which toolbar widget to show when certain page is shown
        self.hierarchy[0] = self.home_UI
        self.grouping[0] = [self.welcome_label]

        self.hierarchy[1] = self.project_browser
        self.grouping[1] = [self.project_label, self.project_arrow, self.new_project_btn, self.project_sorter]

        self.hierarchy[2] = self.asset_manager
        self.grouping[2] = [self.project_label, self.project_arrow, self.project_name_arrow, self.project_name_label, self.asset_sorter]

        # add page widget to stack widget
        self.stack.addWidget(self.home_UI)
        self.stack.addWidget(self.project_browser)
        self.stack.addWidget(self.asset_manager)

        # init calendar (different from all widget above)
        self.calendar_editor = EZMCalendarWidget(self)
        self.calendar_dock = QtWidgets.QDockWidget('Calendar Editor')
        self.calendar_dock.setWidget(self.calendar_editor)

        self.main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.calendar_dock)
        #self.calendar_dock.setFloating(True)

    def initAsset(self):
        self.settings = EZMSettings(self)

    def initUndo(self):
        ## Debug purpose undo view
        # self.history_view = QtWidgets.QDockWidget()
        # self.history_view.setWindowTitle('Command History')
        # self.history_view.setWidget(None)
        # self.history_view.setMaximumWidth(200)
        # self.main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.history_view)

        self.project_browser.history_stack = EZMHistory(self.project_browser)
        self.current_history = self.project_browser.history_stack   # setup default history stack to project

    def onModified(self):
        if DEBUG: print('toolbar: onModified called')
        self.save_config()

    def get_project_path_from_object(self, project):
        key = [i for i in self.project_paths if self.project_paths[i]==project]
        if key: return key[0]

    def set_project_label(self, name):
        self.project_name_label.setText(name)
        self.project_name_arrow.show()
        self.project_name_label.show()

    def change_page(self, menu):  # if project specified, assume it
        # hide and show visibility
        self.stack.setCurrentWidget(self.hierarchy[menu])
        for widget in self.tools_widget: widget.hide()  # hide all widget first
        for widget in self.grouping[menu]: widget.show()    # show important widget only

        # toggle active undo stack
        if menu == PROJECT_MENU:
            self.current_history = self.project_browser.history_stack
            #self.history_view.setWidget(None)  
        elif menu == ASSET_MENU and self.active_project:
            self.current_history = self.active_project.history_stack 
            #self.history_view.setWidget(self.active_project.undo_view)
        elif menu == HOME_MENU:
            self.current_history = None
            #self.history_view.setWidget(None)

    def go_to_home(self, event):
        self.active_project = None
        self.change_page(HOME_MENU)
        
    def go_to_project(self, event):
        self.active_project = None
        self.change_page(PROJECT_MENU)
        
    def go_to_asset(self, project):
        self.active_project = project
        self.asset_manager.current_project = self.active_project
        self.set_project_label(project.name)
        self.change_page(ASSET_MENU)

    def get_history_stack(self):
        return self.current_history

    def project_sorter_changed(self, event):
        sorted_item = []
        project_amount = self.project_browser.project_container.main_layout.count()
        all_project = self.project_browser.project_container.get_all_item()

        # exclude missing project from sorting calculation
        valid_project = [item for item in all_project if isinstance(item, EZMProjectItem)]
        invalid_amount = project_amount-len(valid_project) # how many invalid project to offset sorting widget
        sorted_item.extend(all_project[:invalid_amount])

        if event == 'Name': 
            project_name_list = [[item.name, item] for item in valid_project]
            self.sort_project_by_alphabet(valid_project, invalid_amount, project_name_list, sorted_item)
        if event == 'Category': 
            project_category_list = [[item.category, item] for item in valid_project]
            self.sort_project_by_alphabet(valid_project, invalid_amount, project_category_list, sorted_item)
        if event == 'Last Updated':
            return
        if not event:
            #if DEBUG: print ('sort project again with current text')
            self.project_sorter_changed(self.project_sorter.currentText())
            return 
        self.sort_project_paths(sorted_item)
        self.onModified()

    def sort_project_by_alphabet(self, valid_project, invalid_amount, project_list, sorted_list):
        by_alphabet_project = sorted([item for item in project_list], key=lambda x: x[0].lower())
        for index in range(len(valid_project)):
            self.project_browser.project_container.main_layout.insertWidget(invalid_amount+index, by_alphabet_project[index][1])
            sorted_list.append(by_alphabet_project[index][1])

    def sort_project_paths(self, project_list): 
        """sort project paths by list of project"""
        new_paths = {}
        for item in project_list:
            key = self.get_project_path_from_object(item)
            new_paths[key] = item
        self.project_paths = new_paths
        
    def asset_sorter_changed(self, event):
        scroll = self.asset_manager.get_asset_scroll()
        scroll.sort_asset(event)
        self.onModified()   # for saving the configuration

    def new_project(self, event=None):
        self.project_window = EZMProjectWindow(app=self)
        self.project_window.show()

    def open_settings(self, event):
        self.settings.show()
    
    def open_project_settings(self, project):
        self.project_window = EZMProjectWindow(project=project, edit=True, app=self)
        # set project dialog configuration according to the project atribute
        self.project_window.name_input.setText(project.name)
        for btn in self.project_window.project_btn_grp.buttons():
            if project.category == btn.text(): btn.setChecked(True)
        self.project_window.project_dir_field.setText(project.path)
        self.project_window.thumbnail_preview.change_icon(project.thumbnail)
        if not project.thumbnail in self.project_window.template_thumbnail: # leave empty field if using template folder
            self.project_window.thumbnail_field.setText(project.thumbnail)

        self.project_window.show()

    def create_project(self, name, category, thumbnail, json_path):
        self.project_browser.add_project(name, category, thumbnail, json_path)
        self.project_sorter_changed(None)
        self.onModified()
        
    def delete_project_reference(self, item):
        key = self.get_project_path_from_object(item)
        del self.project_paths[key]
        self.onModified()

    def load_config(self):
        # mean to be called once when open app only
        # check if data exist and config exist, otherwise rebuild all missing path
        data_dir = os.path.join(get_path(),'data')
        json_dir = os.path.join(data_dir, 'user_config.json')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        if not os.path.exists(json_dir):
            open(json_dir, "w")
        #try:
        with open(CONFIG, 'r') as file:
            raw_data = file.read()
            if raw_data: # check if json is not empty
                data = json.loads(raw_data)
                self.deserialize(data)
        #except Exception as e: print('ERROR trying load app config: ' + str(e))

    def save_config(self):
        try:
            with open(CONFIG, 'w') as file:
                file.write(json.dumps(self.serialize(), indent=4))
        except Exception as e: print('ERROR trying save app config: ' + str(e))

    def serialize(self):
        current_project_sorter = self.project_sorter.currentIndex()
        current_asset_sorter = self.asset_sorter.currentIndex()
        dict = OrderedDict([('project_sorter_index', current_project_sorter),
                            ('asset_sorter_index', current_asset_sorter),
                            ('projects', list(self.project_paths.keys()))])
    
        return dict

    def deserialize(self, data):
        self.project_sorter.setCurrentIndex(data['project_sorter_index'])
        self.asset_sorter.setCurrentIndex(data['asset_sorter_index'])
        self.project_browser.load_project(data['projects'])

class EZMProjectLabel(custom_widget.LabelButton):
    def __init__(self, text, callback=None, color=QtGui.QColor('white'), strength=0.25):
        super().__init__(text, callback, color, strength)

    def setText(self, text):
        if len(text) > 57:
            trunc_text = (text[:54])
            self.truncateText(trunc_text)
        else:
            super().setText(text)

    def truncateText(self, text):
        self.setText(text+"...")