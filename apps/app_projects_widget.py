from collections import OrderedDict

from PySide6 import QtCore, QtWidgets, QtGui

from app_assets_widget import EZMAssetItem, EZMAssetStruct
from app_extra_widget import EZMGetStarted
from app_history import *
from util import *

import json

import custom_widget

DEBUG = True

class EZMProjectBrowser(QtWidgets.QWidget):
    def __init__(self, top_widget):
        super().__init__()
        self.top_widget = top_widget

        self.history_stack = None   # let toolbar finish loading, finally assign the history stack (inside initUndo)

        self.setAcceptDrops(True)

        self.initUI()

    def initUI(self):
        self.big_header = QtGui.QFont('Ubuntu', 16)

        # layout management
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # create widget containing container and hint first
        self.project_widget = QtWidgets.QWidget()
        self.project_layout = QtWidgets.QVBoxLayout(self.project_widget)
        self.project_container = custom_widget.InteractiveItemContainer()
        self.import_guide = custom_widget.GraphicLabel(get_path('empty.png', icon=True),(144,144))
        self.get_started_btn = QtWidgets.QPushButton('Get Started')
        self.get_started_btn.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        self.get_started_btn.setStyleSheet('background-color:#1363bf')
        self.get_started_btn.setIcon(QtGui.QIcon(QtGui.QPixmap(get_path('rocket.png',icon=True))))
        self.get_started_btn.setIconSize(QtCore.QSize(24,24))
        self.get_started_btn.clicked.connect(self.get_started)
 
        # create hint widget to align it center (button has weird behaviour when maximum width is restricted it wont align middle)
        self.hint_widget = QtWidgets.QWidget()
        self.hint_layout = QtWidgets.QVBoxLayout(self.hint_widget)
        self.hint_layout.addWidget(self.import_guide)
        self.hint_layout.addWidget(self.get_started_btn)

        self.project_layout.addWidget(self.project_container)
        self.project_layout.addStretch()
        self.project_layout.addWidget(self.hint_widget, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.project_layout.addStretch()

        self.project_scroll = QtWidgets.QScrollArea()
        self.project_scroll.setWidgetResizable(True)
        self.project_scroll.setWidget(self.project_widget)
        self.project_scroll.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Expanding)

        self.project_container.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.main_layout.addWidget(self.project_scroll)

    def show_hint(self, show=True):
        self.import_guide.setVisible(show)
        self.get_started_btn.setVisible(show)

    def get_started(self):
        self.get_started_dialog = EZMGetStarted(self)
        self.get_started_dialog.show()

    def add_project(self, name, category, thumbnail, data_path):
        project = EZMProjectItem(self, self.project_container, name, category, os.path.dirname(data_path), thumbnail)
        with open(data_path, 'w+') as file:
            file.write(json.dumps(project.serialize(), indent=4))
        self.top_widget.project_paths[data_path] = project
        self.show_hint(False)   # when project created successfully hide hint

    def add_missing_project(self, path, warning_text=None, incomplete=False):
        if not warning_text: warning_text = 'File not found '
        item = EZMMissingProjectItem(self.top_widget,
                                     self,
                                     '<b style="color:yellow;">{0}</b>:'.format(warning_text),
                                     path,
                                     incomplete)
        self.project_container.main_layout.insertWidget(0, item)
        self.top_widget.project_paths[path] = item

    def close_project(self, project, confirmation=True):
        """close project only accept list"""
        if confirmation:
            if len(project) > 1: window_title = "Close {0} selected project".format(len(project))
            else: window_title = "Close '{0}' Project".format(project[0].name)
            confirm = QtWidgets.QMessageBox.warning(self, 
                                                    window_title,
                                                    "are you sure?",
                                                    QtWidgets.QMessageBox.Yes,
                                                    QtWidgets.QMessageBox.No)

        if confirmation and confirm == QtWidgets.QMessageBox.Yes: 
            self.project_container.deselect_all()   # clean C++ internal object reference
            for item in project:
                item.deleteLater()
                item.setParent(None)
                self.top_widget.delete_project_reference(item)
            return True
        
        if not confirmation:
            self.project_container.deselect_all()
            project.deleteLater()
            project.setParent(None)
            self.top_widget.delete_project_reference(project)

    def is_project_path_exists(self, path, exclude=[]):
        """Check if project inside browser has the same root path, avoid editing same root with different project"""
        all_project_paths = [project.path for project in self.project_container.get_all_item() if isinstance(project, EZMProjectItem)]
        if path in all_project_paths and path not in exclude: return True
        else: return False

    def onModified(self, project=None):
        """only serve to update project data with serialization"""
        if DEBUG: print('Project browser: on modified called')
        # eval all project without exception (cuz it's light performance)
        for item in self.project_container.get_all_item(): 
            if isinstance(item, EZMProjectItem): item.eval()    # name item, cause we don't override project variable passed to this function
        if project:
            path = self.top_widget.get_project_path_from_object(project)
            self.save_project(path, project)
        else:   # if no project specified, just save all current project
            for path in list(self.top_widget.project_paths.keys()):
                self.save_project(path, self.top_widget.project_paths[path])

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            for name in files: 
                extension = os.path.splitext(name)[1]
                if extension == '.json':
                    self.setStyleSheet('background-color:#2E2E2E')
                    event.accept()
                    break
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet('background-color:none')

    def dropEvent(self, event):
        self.setStyleSheet('background-color:none')
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        json_files = [file for file in files if os.path.splitext(file)[1] == '.json']

        self.load_project(json_files)
        self.project_container.deselect_all()

    def contextMenuEvent(self, event):
        if self.project_container.selected_item:
            menu = QtWidgets.QMenu()
            exportStruct = menu.addAction(QtGui.QIcon(get_path('export.png', icon=True)), 'export project')
            menu.addSeparator()
            deselectStruct = menu.addAction(QtGui.QIcon(get_path('deselect.png', icon=True)), 'deselect')
            closetStruct = menu.addAction(QtGui.QIcon(get_path('close-small.png', icon=True)), 'close')
            
            res = menu.exec_(event.globalPos())
            if res == exportStruct:
                self.export_project(self.project_container.selected_item)
            elif res == deselectStruct:
                self.project_container.deselect_all()
            elif res == closetStruct:
                self.close_project(self.project_container.selected_item)
        
        else:
            menu = QtWidgets.QMenu()
            importStruct = menu.addAction(QtGui.QIcon(get_path('import.png', icon=True)), 'import project')

            res = menu.exec_(event.globalPos())
            if res == importStruct:
                self.import_project()

    def load_project(self, paths):
        for path in paths:
            if not path: continue   # weird bug when user config project contain false
            if DEBUG: print('loading path > ', path)
            try:
                # check if project already loaded
                if path in self.top_widget.project_paths: 
                    print('WARNING: project already loaded, skip')
                    return False
                if os.path.exists(path):
                    file = open(path, 'r')
                    raw_data = file.read()
                    if raw_data:
                        try:
                            data = json.loads(raw_data)
                        
                            # file checking passes
                            if self.is_project_path_exists(data['path']):
                                warning_path_already_exist(self, data['name'], data['path'])
                                continue
                            
                            # initialize project and deserialize data
                            project = EZMProjectItem(self, self.project_container)
                            project.deserialize(data)

                            # assign to application project paths dict
                            self.top_widget.project_paths[path] = project
                            self.show_hint(False)   # when one project loaded successfully, hide hint

                        except:  
                            self.add_missing_project(path, "Can't read file content")   # if json file is not valid throw error
                            continue
                    else:
                        self.add_missing_project(path, 'Content not found')
                else:
                    self.add_missing_project(path)
        
            except Exception as e: print("can't load the project: %s"%e)
        
        if paths: self.top_widget.project_sorter_changed(None)   # finally, trigger project sorter to refresh project order

    def save_project(self, path, project):
        if os.path.exists(path) and isinstance(project, EZMProjectItem):
            with open(path, 'w') as file:  
                    file.write(json.dumps(project.serialize(), indent=4))
        elif isinstance(project, EZMProjectItem):
            print ('WARNING: file project not exist, create file again')
            with open(path, 'w') as file:
                file.write(json.dumps(project.serialize(), indent=4))
        else:
            print("WARNING: can't save project. might be missing content or data")

    def save_project_as(self, path, item):
        try:
            with open(path, 'w') as file:  
                file.write(json.dumps(item.serialize(), indent=4))
        except Exception as e: print('Cannot save project to %s'%path + str(e))

    def import_project(self):
        fnames, filter = QtWidgets.QFileDialog.getOpenFileNames(self, 'Import Project', filter=("JSON (*.json);;"))
        self.load_project(fnames)
        self.project_container.deselect_all()

    def export_project(self, project):
        fnames, filter = QtWidgets.QFileDialog.getSaveFileName(self, 'Export Project', filter=("JSON (*.json);;"))
        if fnames != "":
            self.save_project_as(fnames, project[-1])
            self.project_container.deselect_all()

    def serialize(self):
        """Serialize neccessary info for project undo history, include project paths to identify object between history"""
        project_list = []
        all_project = self.project_container.get_all_item()
        for project in all_project:
            if isinstance(project, EZMProjectItem): # prevent missing object being listed 
                object = project.serialize()
                object['project_paths'] = self.top_widget.get_project_path_from_object(project) # serialize project_paths as it's the only way to identify object after user edit through browser
                project_list.append(object)

        result = OrderedDict([('project', project_list)])
        return result
    
    def deserialize(self, data):
        """Deserialize data from undo history"""
        unmodified = list(self.top_widget.project_paths.values())   # contain current project that not modified, just close if found 
        for project_data in data['project']:
            if project_data['project_paths'] in self.top_widget.project_paths:  # if found same object, just reassign data/deserialize
                project = self.top_widget.project_paths[project_data['project_paths']]
                # rather than deserialize all data again, just assign project attribute
                project.name = project_data['name']
                project.category = project_data['category']
                project.path = project_data['path']
                project.thumbnail = project_data['thumbnail']
                unmodified.remove(project)
            elif project_data['project_paths'] not in self.top_widget.project_paths:   # if not found object, create one
                project = EZMProjectItem(self, self.project_container)
                project.deserialize(project_data)
                self.top_widget.project_paths[project_data['project_paths']] = project
        
        if unmodified:
            for project in unmodified:
                if isinstance(project, EZMProjectItem):     # prevent missing item being closed, only user can close missing item
                    self.close_project(project, confirmation=False)
        self.top_widget.project_sorter_changed(None)    # call on modified update app config and file paths

class EZMProjectItem(custom_widget.InteractiveItem):
    def __init__(self, browser, container, name='project_template', category='Other', path='', thumbnail=''):
        self.asset = [] # include asset item and asset struct
        self.all_asset_dues = []

        self.browser = browser
        self._name = name
        self._category = category
        self._path = path
        self._thumbnail = thumbnail

        super().__init__(container=container)    # call initUI at last
        self.initUndo()

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        self._name = name
        self.name_label.setText(self._name)
        
    @property
    def category(self):
        return self._category
    
    @category.setter
    def category(self, category):
        self._category = category
        icon = self.get_icon()
        self.category_icon.change_icon(icon)

    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, path):
        self._path = path
        self.path_field.setText(self._path)

    @property
    def thumbnail(self):
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, thumbnail):
        self._thumbnail = thumbnail
        self.thumbnail_icon.change_icon(self._thumbnail)

    def initUI(self):
        self.project_font = QtGui.QFont('Ubuntu', 12)

        # layout
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.detail_layout = QtWidgets.QVBoxLayout()
        
        self.path_layout = QtWidgets.QHBoxLayout()
        self.icon_layout = QtWidgets.QHBoxLayout()

        self.config_layout = QtWidgets.QVBoxLayout()

        # widget
        self.thumbnail_icon = custom_widget.GraphicLabel(get_path(self.thumbnail, icon=True), (64, 64))

        self.name_label = custom_widget.ShortLabel(self.name, 70)
        self.name_label.setFont(self.project_font)
        self.path_field = QtWidgets.QLineEdit(self._path)
        self.path_field.setMinimumWidth(220)
        self.path_field.setReadOnly(True)
        self.path_btn = custom_widget.GraphicButton(get_path("external_link.png",icon=True),self.go_to_folder,QtGui.QColor("white"),0.7,(16,16))
        self.path_warning_lbl = custom_widget.GraphicLabel(get_path('warning2.png', icon=True), (16,16))
        self.path_warning_lbl.setToolTip('path not found inside json, might cause issues')
        self.path_warning_lbl.hide()
        self.category_icon = custom_widget.GraphicLabel(self.get_icon(), (16,16))
        self.category_icon.setToolTip("Project Type")
        self.path_editor_icon = custom_widget.GraphicButton(get_path('structure.png',icon=True), self.open_path_editor, color=QtGui.QColor('orange'), strength=1, size=(16,16))

        self.settings_btn = custom_widget.GraphicButton(get_path('more-horizontal.png',icon=True), self.open_settings, QtGui.QColor("white"), 0.7, (16,16))
        self.active_assignment_lbl = QtWidgets.QLabel("")

        # add widget to layout
        self.detail_layout.addWidget(self.name_label)
        self.detail_layout.addLayout(self.path_layout)
        self.detail_layout.addSpacing(5)
        self.detail_layout.addLayout(self.icon_layout)

        self.path_layout.addWidget(self.path_field)
        self.path_layout.addWidget(self.path_btn)
        self.path_layout.addWidget(self.path_warning_lbl)
        self.path_layout.addStretch()

        self.icon_layout.addWidget(self.category_icon)
        self.icon_layout.addWidget(self.path_editor_icon)
        self.icon_layout.addStretch()
    
        self.config_layout.addWidget(self.settings_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.config_layout.addWidget(self.active_assignment_lbl)

        # parent layout
        self.main_layout.addWidget(self.thumbnail_icon)
        self.main_layout.addLayout(self.detail_layout)
        self.main_layout.addStretch()
        self.main_layout.addLayout(self.config_layout)

    def initUndo(self):
        self.history_stack = EZMUndoStack(self)
        # self.undo_view = QtWidgets.QUndoView(self.history_stack)
        # self.undo_view.setEmptyLabel('initial history')  

    def add_asset(self, file):
        self.asset.append(file)

    def remove_asset(self, selection):
        """remove asset by selection, accept list as an input"""
        res = [item for item in self.asset if item not in selection]
        self.asset = res
        # reload assignment to also delete the connected checklist if available

    def execute(self, command):
        """execute command and push to history stack for undo redo functionality"""
        self.history_stack.push(command)

    def mouseDoubleClickEvent(self, event):
        # check if currently browser has more than 1 object selected, if true refresh selection to current project
        if len(self.browser.project_container.selected_item) > 1:
            self.browser.project_container.reset_selection([self])
            return
        self.browser.top_widget.go_to_asset(self)

    def go_to_folder(self, event):
        try:
            os.startfile(self.path)
        except FileNotFoundError as e: print(str(e))
        except Exception as e: print(str(e))

    def open_settings(self, event):
        self.browser.top_widget.open_project_settings(self)

    def open_path_editor(self, event):
        return
        #self.path_editor = EZMPathEditor(self)

    def get_icon(self):
        if self._category == "Animation":
            return get_path("TV.png", icon=True)
        elif self._category == "Game":
            return get_path("game.png", icon=True)
        else:
            return get_path("package.png", icon=True)

    # def update_assignment_lbl(self):
    #     self.all_asset_dues = []
    #     for asset in self.asset: 
    #         if asset.days_left != None and asset.days_left >= 0 and asset.status != 2:
    #             self.all_asset_dues.append(asset.days_left)
    #     if self.all_asset_dues:
    #         closest_due = min(self.all_asset_dues)
    #         modus = self.all_asset_dues.count(closest_due)
    #         self.active_assignment_lbl.setText("%s/%s assignment due in %s days"%(modus,len(self.all_asset_dues),closest_due))
    #         if closest_due > 14:
    #             self.active_assignment_lbl.setStyleSheet('color:DeepSkyBlue')
    #         elif 7 < closest_due <= 14:
    #             self.active_assignment_lbl.setStyleSheet('color:yellow')
    #         elif 2 < closest_due <= 7:
    #             self.active_assignment_lbl.setStyleSheet('color:orange')
    #         elif 0 <= closest_due <= 2:
    #             self.active_assignment_lbl.setStyleSheet('color:tomato')
    #     else:
    #         self.active_assignment_lbl.setText("")

    def serialize(self):
        # serialize asset 
        asset_list = []
        struct_list = []
        for asset in self.asset:
            if type(asset) is EZMAssetItem: # using type rather than isinstance to ignore inheritance
                asset_list.append(asset.serialize())
            elif type(asset) is EZMAssetStruct:
                struct_list.append(asset.serialize())

        dict = OrderedDict([('name', self.name),
                            ('category', self.category),
                            ('path', self.path),
                            ('thumbnail', self.thumbnail),
                            ('asset', asset_list),
                            ('struct', struct_list)])
        return dict

    def deserialize(self, data):
        # deserialize method here is assigning each data value to the instance
        try:
            self.name = data['name']
            self.category = data['category']
            self.path = data['path']
            self.thumbnail = data['thumbnail']
            
            new_asset = []
            for asset_data in data['asset']:
                asset = EZMAssetItem(self,
                                        self.browser.top_widget.asset_manager.get_asset_scroll(),
                                        asset_data['name'],
                                        asset_data['path'],
                                        asset_data['group'],
                                        asset_data['date_modified'],
                                        asset_data['type'],
                                        asset_data['status'],
                                        asset_data['date_assignment'],
                                        asset_data['preview'],
                                        asset_data['notes'])
                new_asset.append(asset)

            new_struct = []
            for struct_data in data['struct']:
                struct = EZMAssetStruct(self,
                                        self.browser.top_widget.asset_manager.get_asset_scroll(),
                                        struct_data['name'],
                                        struct_data['path'],
                                        struct_data['group'],
                                        struct_data['date_modified'],
                                        struct_data['type'],
                                        struct_data['status'],
                                        struct_data['file'],
                                        struct_data['date_assignment'],
                                        struct_data['preview'],
                                        struct_data['notes'])
                struct.deserialize(struct_data['file_version'])    # initialize file version if found
                new_struct.append(struct)

            self.asset = new_asset + new_struct
            self.eval() # update ui

        except:  # canceled add project if deserialization failed
            print('PROBLEM DESERIALIZATION')
            self.browser.add_missing_project("path unavailable", "Can't read file content")   # if json file is not valid throw error
            self.setParent(None)
            self.deleteLater()

    def eval(self):
        """if project path inside json is not valid, raise warning. remember it's different from path for json, it's INSIDE json"""
        if not os.path.exists(self.path): self.path_warning_lbl.show()
        else: self.path_warning_lbl.hide()

class EZMMissingProjectItem(QtWidgets.QFrame):
    def __init__(self, top_widget, browser, text, path, incomplete=False):
        super().__init__()
        self.top_widget = top_widget  
        self.browser = browser
        self.text = text
        self.path = path
        self.incomplete = incomplete

        self.initUI()
        self.setObjectName('missingProject')
        self.setStyleSheet('EZMMissingProjectItem#missingProject{border: 1px solid #C5C500}')
        self.initData() # initialize project item as incomplete version so we can retrieve data if needed later
        
    def initUI(self):
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)
        self.main_layout = QtWidgets.QHBoxLayout(self)

        self.warning_icon = custom_widget.GraphicLabel(get_path('warning.png', icon=True),(20,20))
        self.warning_lbl = QtWidgets.QLabel(self.text)
        self.name_field = QtWidgets.QLineEdit(self.path)
        self.name_field.setReadOnly(True)
        self.close_btn = custom_widget.GraphicButton(get_path('close.png', icon=True), self.onClose, size=(18,18))
        self.fix_btn = custom_widget.GraphicButton(get_path('wrench.png', icon=True), self.fix_path, size=(20,20))
        self.fix_btn.setToolTip('repath project')

        self.main_layout.addWidget(self.warning_icon)
        self.main_layout.addWidget(self.warning_lbl)
        self.main_layout.addWidget(self.name_field)
        if self.incomplete: self.main_layout.addWidget(self.fix_btn)
        self.main_layout.addWidget(self.close_btn)

    def initData(self):
        if self.incomplete:
            try:
                file = open(self.path, 'r')
                raw_data = file.read()
                data = json.loads(raw_data)
                self.project = EZMProjectItem(self.browser, None)   # pass None to container as cheating, to avoid ui being present. as we want only serialize function
                self.project.deserialize(data)
            except Exception as e: print(e)

    def onClose(self, event):
        confirm = QtWidgets.QMessageBox.warning(self, 
                                                'Close project?',
                                                'are you sure?',
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        
        if confirm == QtWidgets.QMessageBox.Yes:
            self.deleteLater()
            self.setParent(None)
            self.top_widget.delete_project_reference(self)

    def fix_path(self, event):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Find Project File')
        if fname != "": 
            self.project.path = fname
            self.save_project_file()
            # basically refresh incomplete project by load it again and remove current, close first to avoid load project detect already loaded file exception
            self.browser.close_project(self, confirmation=False)
            self.browser.load_project([self.path])  

    def save_project_file(self):
        if os.path.exists(self.path):
            with open(self.path, 'w') as file:  
                file.write(json.dumps(self.project.serialize(), indent=4))