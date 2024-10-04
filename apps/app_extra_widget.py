
from PySide6 import QtCore, QtWidgets, QtGui
 
from util import *

import random
import os

import custom_widget

class EZMDateDialog(QtWidgets.QDialog):
    def __init__(self, scroll=None):
        self.assignment_date = []   # hold the assignment date to let other system get value

        super().__init__(scroll)
        self.initUI()
        self.initConnection()

    def initUI(self):
        self.setWindowTitle('set start date')
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.start_layout = QtWidgets.QVBoxLayout()
        self.due_layout = QtWidgets.QVBoxLayout()
        
        self.start_lbl = QtWidgets.QLabel('start date')
        self.start_date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.start_date_edit.setDateTime(QtCore.QDateTime.currentDateTime())
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.start_date_edit.setMinimumWidth(220)
        self.due_lbl = QtWidgets.QLabel('due date')
        self.due_date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.due_date_edit.setDateTime(QtCore.QDateTime.currentDateTime())
        self.due_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.due_date_edit.setMinimumWidth(220)
        self.set_btn = QtWidgets.QPushButton('Set')

        self.warning_lbl = QtWidgets.QLabel("Due date can't be earlier than start date")
        self.warning_lbl.setStyleSheet('color:red')
        self.warning_lbl.hide()

        self.start_layout.addWidget(self.start_lbl)
        self.start_layout.addWidget(self.start_date_edit)

        self.due_layout.addWidget(self.due_lbl)
        self.due_layout.addWidget(self.due_date_edit)

        self.main_layout.addLayout(self.start_layout)
        self.main_layout.addLayout(self.due_layout)
        self.main_layout.addWidget(self.warning_lbl)
        self.main_layout.addWidget(self.set_btn)

    def initConnection(self):
        self.set_btn.clicked.connect(self.set_start_date)

    def add_leading_zero_date(self, year, month, day):
        # add leading zero if needed
        if len(str(day)) == 1:
            day = '0'+str(day)
        if len(str(month)) == 1:
            month = '0'+str(month)
        return '%s/%s/%s'%(day, month, year)

    def set_start_date(self):
        start_date = self.start_date_edit.dateTime().date()
        year, month, day = start_date.year(), start_date.month(), start_date.day()
        start_date_normalized = self.add_leading_zero_date(year, month, day)
        due_date = self.due_date_edit.dateTime().date()
        year, month, day = due_date.year(), due_date.month(), due_date.day()
        due_date_normalized = self.add_leading_zero_date(year, month, day)

        if start_date > due_date:
            self.warning_lbl.show()
            return

        self.warning_lbl.hide()
        self.close()
        self.assignment_date = [start_date_normalized, due_date_normalized]
        

class EZMProjectWindow(QtWidgets.QDialog):
    def __init__(self, project=None, edit=False, app=None):
        super().__init__(app)

        self.setWindowTitle("Project Configuration")

        self.project = project
        self.edit = edit
        self.app = app
        self.setModal(True)

        self.template_thumbnail=[get_path('project0.png', icon=True),
                                 get_path('project1.png', icon=True),
                                 get_path('project2.png', icon=True),
                                 get_path('project3.png', icon=True),
                                 get_path('project4.png', icon=True),
                                 get_path('project5.png', icon=True),
                                 get_path('project6.png', icon=True)]

        self.initUI()
        self.initConnection()

    def initUI(self):
        # font
        self.error_font = QtGui.QFont('Ubuntu', 8)

        # layouts
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.name_layout = QtWidgets.QHBoxLayout() 
        self.type_layout = QtWidgets.QHBoxLayout()
        self.directory_layout = QtWidgets.QHBoxLayout()
        self.thumbnail_layout = QtWidgets.QHBoxLayout()
        self.confirm_layout = QtWidgets.QHBoxLayout()      

        # WIDGETS
        ## project name
        self.name_label = QtWidgets.QLabel("Project Name:")
        self.name_input = QtWidgets.QLineEdit()

        self.name_error = QtWidgets.QLabel("This field is required!")
        self.name_error.setFont(self.error_font)
        self.name_error.setStyleSheet('color:red')
        
        self.close_btn = QtWidgets.QPushButton("Close")
        self.close_btn.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        self.close_btn.setStyleSheet('background-color:#bf1313')
        self.confirm_btn = QtWidgets.QPushButton("Confirm")

        ## project type
        self.project_type = QtWidgets.QLabel("Type:")
        self.project_btn_grp = QtWidgets.QButtonGroup()
        self.game_btn = QtWidgets.QRadioButton("Animation")
        self.game_btn.setChecked(True)
        self.animation_btn = QtWidgets.QRadioButton("Game")
        self.other_btn = QtWidgets.QRadioButton("Other")

        self.project_btn_grp.addButton(self.game_btn)
        self.project_btn_grp.addButton(self.animation_btn)
        self.project_btn_grp.addButton(self.other_btn)

        ## project folder
        self.project_dir_label = QtWidgets.QLabel("Path:")
        self.project_dir_field = QtWidgets.QLineEdit()
        self.project_dir_error = QtWidgets.QLabel()
        self.project_dir_error.setFont(self.error_font)
        self.project_dir_error.setStyleSheet('color:red')
        self.project_dir_icon = custom_widget.GraphicButton(get_path("folder.png", icon=True), 
                                                            callback=self.openDirectoryDialog, 
                                                            size=(20,20))
        
        ## project thumbnail
        self.thumbnail_preview = custom_widget.GraphicLabel(self.template_thumbnail[(random.randint(0,6))],(60,60))
        self.thumbnail_field = QtWidgets.QLineEdit()
        self.thumbnail_field.setReadOnly(True)
        self.thumbnail_random_btn = custom_widget.GraphicButton(get_path('dice.png', icon=True), 
                                                            self.randomize_thumbnail, 
                                                            size=(16,16),
                                                            parent=self.thumbnail_preview)
        self.thumbnail_random_btn.move(44,5)
        self.thumbnail_folder = custom_widget.GraphicButton(get_path('folder.png', icon=True),
                                                            callback=self.openFileDialog,
                                                            size=(20,20))

        # parent widget to sub-layout
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_input)

        self.type_layout.addWidget(self.project_type)
        self.type_layout.addWidget(self.game_btn)
        self.type_layout.addWidget(self.animation_btn)
        self.type_layout.addWidget(self.other_btn)

        self.directory_layout.addWidget(self.project_dir_label)
        self.directory_layout.addWidget(self.project_dir_field)
        self.directory_layout.addWidget(self.project_dir_icon)

        self.thumbnail_layout.addWidget(self.thumbnail_preview)
        self.thumbnail_layout.addWidget(self.thumbnail_field)
        #self.thumbnail_layout.addWidget(self.thumbnail_random)
        self.thumbnail_layout.addWidget(self.thumbnail_folder)

        self.confirm_layout.addWidget(self.close_btn)
        self.confirm_layout.addWidget(self.confirm_btn)

        # parent layout and widget to main
        self.main_layout.addLayout(self.name_layout)
        self.main_layout.addWidget(self.name_error)
        self.main_layout.addLayout(self.type_layout)
        self.main_layout.addLayout(self.directory_layout)
        self.main_layout.addWidget(self.project_dir_error)
        self.main_layout.addLayout(self.thumbnail_layout)
        self.main_layout.addLayout(self.confirm_layout)

        # initial widget visibility state
        self.project_dir_error.hide()
        self.name_error.hide()
        if not self.edit: self.close_btn.hide()

    def initConnection(self):
        self.confirm_btn.clicked.connect(self.onConfirm)
        self.close_btn.clicked.connect(self.onCloseItem)

    def randomize_thumbnail(self, event):
        if os.path.exists(self.thumbnail_field.text()): return  # prevent randomize icon if thumbnail present
        path = self.template_thumbnail[random.randint(0,6)]
        self.thumbnail_preview.change_icon(path)

    def openDirectoryDialog(self, event):
        fname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Project Path')
        if fname != "": self.project_dir_field.setText(fname)

    def openFileDialog(self, event):
        fname, filter = QtWidgets.QFileDialog.getOpenFileName(self, "Thumbnail Image", filter=("Image Files (*.png *.jpg *.bmp)"))
        if fname != "":
            self.thumbnail_field.setText(fname)
            self.thumbnail_preview.change_icon(fname)

    def onCloseItem(self):
        if self.app.project_browser.close_project([self.project]):
            self.deleteLater()
            
    def onConfirm(self, event):
        # process and screening all input before proceed
        error = 0

        # checking name...
        name = self.name_input.text()
        if name == "":
            self.name_error.show()
            error = 1
        else:
            self.name_error.hide()
        
        # checking category...
        category = self.project_btn_grp.checkedButton().text()

        # checking path...
        path = self.project_dir_field.text()
        if not os.path.isdir(path):
            self.project_dir_error.setText("Directory not found!")
            self.project_dir_error.show()
            error = 1
        else:
            self.project_dir_error.hide()

        if self.edit:
            if self.app.project_browser.is_project_path_exists(path, [self.project.path]):
                self.project_dir_error.setText("Same path already used by another project!")
                self.project_dir_error.show()
                error = 1
        elif not self.edit and self.app.project_browser.is_project_path_exists(path):
            self.project_dir_error.setText("Same path already used by another project!")
            self.project_dir_error.show()
            error = 1

        # checking thumbnail...
        thumbnail = self.thumbnail_field.text()
        if thumbnail == '':
            thumbnail = self.thumbnail_preview.icon 
        
        # finally add project if everything required is valid
        if error == 1:
            return
        elif self.edit:
            # check if project before and after has any difference after edit
            query_attr = [self.project.name, self.project.category, self.project.path, self.project.thumbnail]
            input_attr = [self.name_input.text(), self.project_btn_grp.checkedButton().text(), self.project_dir_field.text(), thumbnail]
            if query_attr == input_attr: 
                self.hide()
                return

            # check if project path is used by other project
            if self.app.project_browser.is_project_path_exists(self.project_dir_field.text(), self.project.path):   # check if data with same name already exists
                warning_path_already_exist(self, name, self.project_dir_field.text())
                return
            self.project.name = self.name_input.text()
            self.project.category = self.project_btn_grp.checkedButton().text()
            self.project.path = self.project_dir_field.text()
            self.project.thumbnail = thumbnail
            self.app.project_browser.history_stack.storeHistory("edit project details")
            self.app.project_browser.onModified(self.project)
        else: 
            # generated_root_path = os.path.normpath(os.path.join(path, name))
            # generated_json_path = os.path.normpath(os.path.join(generated_root_path, name+'.json'))
            # if os.path.exists(generated_root_path) or self.app.project_browser.is_project_path_exists(generated_root_path):   # check if data with same name already exists
            #     warning_path_already_exist(self, name, generated_root_path)
            #     return
            generated_json_path = os.path.normpath(os.path.join(path, name+'.json'))
            generated_json_path = filter_path_name(generated_json_path, file=True)   # check if file already exist, else rename
            self.app.create_project(name, category, thumbnail, generated_json_path) # create project data json in root folder

        self.hide()

class EZMGetStarted(QtWidgets.QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setWindowTitle("Get Started")
        self.setModal(True)

        self.initUI()

    def initUI(self):
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.left_layout = QtWidgets.QVBoxLayout()
        self.right_layout = QtWidgets.QVBoxLayout()
        self.center_layout = QtWidgets.QVBoxLayout()

        self.create_img_lbl = custom_widget.GraphicLabel(get_path('create_project.png',icon=True),(256,256))
        self.create_project_btn = QtWidgets.QPushButton('Create New Project')
        self.create_project_btn.clicked.connect(self.create_project)

        self.import_img_lbl = custom_widget.GraphicLabel(get_path('import_project.png',icon=True),(256,256))
        self.import_project_btn = QtWidgets.QPushButton('Import Project')
        self.import_project_btn.clicked.connect(self.import_project)

        self.separator1 = QtWidgets.QFrame()
        self.separator1.setFrameShape(QtWidgets.QFrame.VLine)
        self.separator1.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Minimum)
        self.separator1.setLineWidth(2)

        self.center_lbl = QtWidgets.QLabel('OR')
        self.center_lbl.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Fixed)

        self.separator2 = QtWidgets.QFrame()
        self.separator2.setFrameShape(QtWidgets.QFrame.VLine)
        self.separator2.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Minimum)
        self.separator2.setLineWidth(2)

        self.left_layout.addWidget(self.create_img_lbl)
        self.left_layout.addWidget(self.create_project_btn)

        self.right_layout.addWidget(self.import_img_lbl)
        self.right_layout.addWidget(self.import_project_btn)

        self.center_layout.addWidget(self.separator1)
        self.center_layout.addWidget(self.center_lbl)
        self.center_layout.addWidget(self.separator2)

        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addLayout(self.center_layout)
        self.main_layout.addLayout(self.right_layout)

    def create_project(self):
        self.browser.top_widget.new_project()
        self.deleteLater()

    def import_project(self):
        self.browser.import_project()
        self.deleteLater()

class EZMPathEditor(QtWidgets.QDialog):
    def __init__(self, project=None):
        super().__init__(project)
        self.setWindowTitle("Path Editor")
        self.setModal(True)

class EZMSettings(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")

        # Placeholder, delete later
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QLabel('nothing here for now...')
        self.main_layout.addWidget(self.label)
        self.setMinimumSize(100,50)

### ASET WIDGET

# reference: https://github.com/Fus3n/PySnipTool/blob/main/Capturer.py
class EZMScreenshotEdit(QtWidgets.QDialog):
    def __init__(self, asset, parent=None):
        super().__init__(parent)

        self.asset = asset

        self.setWindowTitle('Screenshot Edit')
        self.initUI()
        self.initConnection()

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.footer_layout = QtWidgets.QHBoxLayout()

        self.thumbnail_lbl = QtWidgets.QLabel()
        self.accept_btn = QtWidgets.QPushButton('accept')
        self.capture_btn = QtWidgets.QPushButton('capture')

        self.main_layout.addWidget(self.thumbnail_lbl)
        self.main_layout.addLayout(self.footer_layout)

        self.footer_layout.addWidget(self.accept_btn)
        self.footer_layout.addWidget(self.capture_btn)

    def initConnection(self):
        self.accept_btn.clicked.connect(self.acceptImg)
        self.capture_btn.clicked.connect(self.captureImg)

    def acceptImg(self):
        if os.path.exists(self.asset.project.path):
            # check if .screenshot is avail, if not create
            ss_folder = os.path.join(self.asset.project.path,'.screenshot')
            if not os.path.exists(ss_folder): os.makedirs(ss_folder)
            img_path = filter_path_name(os.path.join(ss_folder, self.asset.name+'.png'),file=True)
            self.capturer.capturedImg.save(img_path)
            self.asset.preview = img_path
            self.asset.asset_scroll.onModified() #trigger save + update asset detail
            self.close()
        else: 
            warning = QtWidgets.QMessageBox.warning(self, "project path not exists!", "can't save screenshot, project path not found!")
            self.close()

    def captureImg(self):
        self.capturer = custom_widget.screenCapture(self)
        self.capturer.show()