from collections import OrderedDict
from datetime import datetime
from send2trash import send2trash

from PySide6 import QtCore, QtWidgets, QtGui

from app_extra_widget import EZMScreenshotEdit, EZMDateDialog
from util import *

import subprocess

import custom_widget

DEBUG = True

COMPATIBLE_FILE = ['.ma', '.mb', '.fbx']
INVALID_FILENAME_CHARACTERS = ['\\','/',':','*','?','"','<','>','|']

class EZMAssetManager(QtWidgets.QWidget):
    def __init__(self, app=None):
        super().__init__()

        self.app = app
        self._current_project = None
    
        self.initUI()
        #self.setChildrenCollapsible(False)
        #self.setStretchFactor(0,1)

    @property
    def current_project(self):
        return self._current_project
    
    @current_project.setter
    def current_project(self, project):
        scroll = self.get_asset_scroll()
        self._current_project = project
        scroll.current_project = self.current_project
    
    def initUI(self):
        self.asset_browser = EZMAssetBrowser(self.app, self)
        self.asset_detail =  EZMAssetDetail()
        self.asset_splitter = EZMAssetSplitter(self.asset_detail)

        self.main_layout = QtWidgets.QHBoxLayout(self)

        self.main_layout.addWidget(self.asset_browser)
        self.main_layout.addWidget(self.asset_splitter)
        self.main_layout.addWidget(self.asset_detail)

    def get_asset_scroll(self):
        return self.asset_browser.asset_scroll
    
    def get_selected_asset(self):
        return self.asset_browser.asset_scroll.asset_container.selected_item
    
    def update_asset_detail(self, asset=None):
        # TODO: i don't like how it's now, this should be a function inside asset detail and we just refresh it from given input
        if asset:
            self.asset_detail.lock_desc = True  # refresh desc state
            self.asset_detail.has_selected = True
            self.asset_detail.name_edit.setText(asset[-1].name)
            self.asset_detail.path_field.setText(asset[-1].path)
            self.asset_detail.current_asset = asset[-1]
            if asset[-1].date_modified == '01/01/9999 00:00':
                self.asset_detail.updated_lbl.setText("Last Updated: N/A")
            else:
                self.asset_detail.updated_lbl.setText("Last Updated: %s"%asset[-1].date_modified)
            if os.path.exists(asset[-1].preview):
                self.asset_detail.thumbnail_lbl.change_icon(asset[-1].preview,(200,200)) # try to scale it for better view, the size.x and size.y doesn't matter cuz it will adapt to img ratio
            else:
                self.asset_detail.thumbnail_lbl.change_icon(get_path('no_preview.png', icon=True),(160,160)) 
            if asset[-1].notes:
                self.asset_detail.notes_edit.setPlainText(asset[-1].notes)
            else:
                self.asset_detail.notes_edit.setPlainText('')
        else: 
            self.asset_detail.has_selected = False
            self.asset_detail.current_asset = None
            self.asset_detail.lock_desc = True

class EZMAssetBrowser(QtWidgets.QWidget):
    def __init__(self, app, manager):
        self.app = app
        self.manager = manager

        super().__init__()
        self.initUI()
        self.initConnection()
        
    def initUI(self):
        # widgets for each tab
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)

        # asset scroll UI
        self.asset_scroll = EZMAssetScroll(self.app, self.manager, self)

        # asset tab UI
        self.asset_tab = QtWidgets.QTabBar(self)
        self.asset_tab.setObjectName('assetBrowserTab')
        self.asset_tab.addTab('All')
        self.asset_tab.addTab('Character')
        self.asset_tab.addTab('Prop')
        self.asset_tab.addTab('Sets')

        self.asset_tab.setShape(QtWidgets.QTabBar.RoundedWest)

        # parent all widget
        self.main_layout.addWidget(self.asset_tab, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(self.asset_scroll)

    def initConnection(self):
        self.asset_tab.currentChanged.connect(self.onTabChanged)

    def onTabChanged(self, index):
        tab_type = self.asset_tab.tabText(index)
        self.asset_scroll.toggle_asset_visibility()
        if DEBUG: print('Asset tab changed: ', tab_type)

    def get_current_tab(self):
        return self.asset_tab.tabText(self.asset_tab.currentIndex())

    def serialize(self, data):
        pass

    def deserialize(self, data):
        pass

class EZMAssetScroll(QtWidgets.QScrollArea):
    def __init__(self, app, manager, browser):
        super().__init__()
        self.setWidgetResizable(True)
        self.setAcceptDrops(True)

        self.app = app
        self.manager = manager
        self.browser = browser

        self._hint = True # show guide if true
        self._current_project = None

        self.initUI()
        self.initConnection()

    @property
    def hint(self):
        return self._hint
    
    @hint.setter
    def hint(self, show):
        self._hint = show
        if self._hint:
            self.drag_guide.show()
            self.asset_container.hide()
        else:
            self.drag_guide.hide()
            self.asset_container.show()

    @property
    def current_project(self):
        return self._current_project
    
    @current_project.setter
    def current_project(self, project):
        if self.current_project != project:
            self._current_project = project
            self.asset_container.clear_all_item()
            self.load_asset()
        else: self.refresh() # if project not set with different project, just refresh

    def initUI(self):
        self.center_widget = QtWidgets.QWidget()
        self.setWidget(self.center_widget)

        self.main_layout = QtWidgets.QVBoxLayout(self.center_widget)
        self.main_layout.setContentsMargins(0,0,0,0)
        #self.main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.import_btn = QtWidgets.QPushButton('import file')
        self.import_btn.setStyle(QtWidgets.QStyleFactory.create('Windows'))
        self.import_btn.setStyleSheet('background-color:#1363bf')
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText('Search')
        self.search_field.returnPressed.connect(self.search_field.clearFocus)
        self.search_field.textChanged.connect(self.toggle_asset_visibility)
        self.asset_container = custom_widget.InteractiveItemContainer()
        self.asset_container.onModifySelectedItem = self.selectionModified
        self.asset_container.main_layout.setContentsMargins(0,0,0,0)

        # placeholder on empty project
        self.drag_guide = custom_widget.GraphicLabel(get_path('drag.png', icon=True),(128,128))

        # add widget to layout
        self.main_layout.addWidget(self.import_btn)
        self.main_layout.addWidget(self.search_field)
        self.main_layout.addWidget(self.asset_container)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.drag_guide, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch()
        self.asset_container.hide()

        # extra dialog/widget
        self.group_dialog = EZMQueryAssetGroup(self)
        self.date_dialog = EZMDateDialog(self)

    def initConnection(self):
        self.import_btn.clicked.connect(self.import_file)

    def onModified(self):
        self.toggle_asset_visibility()
        self.current_project.browser.onModified(self.current_project)
        self.manager.update_asset_detail(self.asset_container.selected_item)
        # eval all asset: (# cause some lag with file more than 200+)
        self.refresh()
                
    def initProjectAsset(self):
        """Initialize asset when being shown/active, check for error if not valid"""
        for asset in self.current_project.asset:
            #if DEBUG: print('   load asset: %s'%asset.name)
            #asset.asset_scroll = self # already in deserialize project
            self.asset_container.add_item(asset)
            asset.eval()

    def toggle_asset_visibility(self):
        """toggle asset visibility by type from current tab. if tab has no object, show hint"""
        active_asset = []   # contain any visible asset to filter with search browser
        no_asset = True # check if current tab has asset, if not show hint
        all_asset = self.asset_container.get_all_item()
        # print('all asset > ', all_asset)
        current_tab = self.browser.get_current_tab()
        if current_tab != 'All':
            for asset in all_asset: 
                if asset.group == current_tab: 
                    asset.show()
                    active_asset.append(asset)
                    no_asset = False
                else: asset.hide()
        else:
            active_asset = all_asset
            for asset in all_asset: 
                asset.show()
                no_asset = False
        self.hint = no_asset

        # also check the search field if any asset needed to hide
        for asset in active_asset: 
            if self.search_field.text().lower() not in asset.name.lower(): asset.hide()

    def sort_asset(self, event=None):
        #if DEBUG: print ('sort asset')
        all_asset = self.asset_container.get_all_item()
        if event=='Name':
            name_and_asset = [[asset.name, asset] for asset in all_asset]
            sorted_asset = sorted([asset for asset in name_and_asset], key=lambda x: x[0].lower())
            self.current_project.asset = [asset[1] for asset in sorted_asset]
        if event=='Type':
            type_and_asset = [[asset.type, asset] for asset in all_asset]
            sorted_asset = sorted([asset for asset in type_and_asset], key = lambda x: x[0].lower())
            self.current_project.asset = [asset[1] for asset in sorted_asset]
        if event=='Last Updated':
            date_and_asset = [[asset.date_modified, asset] for asset in all_asset]
            sorted_asset = sorted([asset for asset in date_and_asset], key = lambda date_modified: datetime.strptime(date_modified[0], "%d/%m/%Y %H:%M"), reverse=True)
            self.current_project.asset = [asset[1] for asset in sorted_asset]
        if event=='Priority':
            due_and_asset = [[asset.days_left, asset] for asset in all_asset]
            sorted_asset = self.sort_priority(due_and_asset)
            self.current_project.asset = [asset[1] for asset in sorted_asset]
        if event==None:
            #if DEBUG: print ('sort asset again with current text')
            self.sort_asset(self.app.asset_sorter.currentText())
            return
        self.update_asset_order(self.current_project.asset)

    def update_asset_order(self, asset):
        for index in range(len(asset)):
            self.asset_container.main_layout.insertWidget(index, asset[index])

    def sort_priority(self, list):
        due_list = []
        past_list = []
        completed_list = []
        none_list = []
        for item in list:
            days_left = item[0]
            if days_left == None: none_list.append(item)
            elif item[1].status == 2: completed_list.append(item)
            elif days_left >= 0: due_list.append(item)
            elif days_left < 0: past_list.append(item)
        due_list = sorted([asset for asset in due_list], key = lambda asset: asset[0])
        past_list = sorted([asset for asset in past_list], key = lambda asset: asset[0])
        completed_list = sorted([asset for asset in completed_list], key = lambda asset: asset[0],reverse=True)
        return due_list + past_list + completed_list + none_list
    
    def add_asset(self, files, group):
        """only for adding new asset into project"""
        if DEBUG: print('add asset')
        # check for duplicate path, only accept unique path
        duplicate_path = []
        for file in files: 
            duplicate_asset = self.check_duplicated_path(file)
            if duplicate_asset: duplicate_path.append(duplicate_asset)
        unique_files = [file for file in files if file not in duplicate_path]
        self.hint = False  
        self.current_project.execute(cmd_addAsset(self.current_project, self, unique_files, group))

    def delete_asset(self):
        selection = self.asset_container.selected_item
        if selection:
            self.current_project.execute(cmd_deleteAsset(selection, self, self.current_project))

    def update_asset(self):
        selected_asset = self.asset_container.selected_item[-1]
        fname, filter = QtWidgets.QFileDialog.getOpenFileName(self, "Update File", filter=("Maya Scenes (*.ma *.mb);; Maya ASCII (*.ma);; Maya Binary (*.mb);; All Files (*)"))
        if fname != "" and self.check_if_type_compatible(fname, warning=True): 
            # check if there is asset with same path
            duplicate_asset = self.check_duplicated_path(fname, [selected_asset])
            if duplicate_asset==None:
                self.current_project.execute(cmd_updateAsset(self, selected_asset, fname))

    def check_before_publish(self, file, asset):
        # check if published file is the current file
        if os.path.normpath(file) == os.path.normpath(asset.file):
            QtWidgets.QMessageBox.warning(self, 'Operation Denied', "Can't publish file from the same directory")
            return False
        # check if published file name has the same name inside target directory
        if os.path.basename(file) in os.listdir(os.path.dirname(asset.file)) and os.path.basename(file) != os.path.basename(asset.file):
            QtWidgets.QMessageBox.warning(self, 'Operation Denied', "Can't publish file!\nsame name already exists inside target directory:\n%s"%os.path.join(os.path.dirname(asset.file), os.path.basename(file)))
            return False
        return True

    def publish_asset(self):
        selected_asset = self.asset_container.selected_item[-1]
        self.asset_container.modify_selection(selected_asset)
        if EZMAssetItem.verify_file_integrity(selected_asset):
            fname, filter = QtWidgets.QFileDialog.getOpenFileName(self, "Publish File", filter=("Maya Scenes (*.ma *.mb);; Maya ASCII (*.ma);; Maya Binary (*.mb);; All Files (*)"))
            if fname != "" and self.check_if_type_compatible(fname, warning=True): 
                    if self.check_before_publish(fname, selected_asset):
                        #self.current_project.execute(cmd_publishAsset(self, selected_asset, fname))
                        self.update_struct(selected_asset, fname)

    def update_struct(self, asset, file, version_suffix = True):
        """update struct by move the current file to old version, handle error for duplicate and versioning name"""
        # initiate target file and folder directory
        old_folder = os.path.join(asset.path, '.old')
        old_file = os.path.join(old_folder, os.path.basename(asset.file))   # targeted path to move asset file to older ver
        new_file = os.path.join(asset.path, os.path.basename(file)) # predetermined new file path
    
        # handle version name
        if version_suffix:
            version = len(asset.file_version) + 1   # add 1 to indicate the start of version count
            number_len = len(str(version))
            template_ver = '_v0001'
            if number_len > 4: return # version exceeding 9999! cancelled
            else: template_ver = template_ver[:-number_len] + str(version)
            old_file = os.path.join(old_folder, add_filename_suffix(os.path.basename(asset.file),template_ver)) 

        # check for duplicated before moving current file to folder
        if os.path.exists(asset.file):
            if not os.path.exists(old_folder):
                os.makedirs(old_folder)
            if not os.path.exists(old_file):
                shutil.move(asset.file, old_file)   # rename and move the old file path
            elif os.path.exists(old_file):
                warning = QtWidgets.QMessageBox.warning(self, "Can't publish asset!", "Can't move older version to .old folder, file already exists!\n\ndo you want to rename and move the file?",QtWidgets.QMessageBox.Yes,QtWidgets.QMessageBox.Cancel)
                if warning == QtWidgets.QMessageBox.Yes:
                    old_file = filter_path_name(old_file, file=True)
                    shutil.move(asset.file, old_file)   # rename and move the old file path
                if warning == QtWidgets.QMessageBox.Cancel:
                    return False
        
        # copy new file, check if new file is inside directory or not
        if not os.path.normpath(os.path.dirname(file)) == os.path.normpath(asset.path):
            if os.path.exists(os.path.normpath(new_file)):
                print("file already exist, can't copy")
            else:
                shutil.copy2(file, asset.path)

        # update file version
        old_item = EZMAssetVersion(asset, os.path.basename(old_file), old_file, asset.group, asset.date_modified, asset.type, asset.status)
        asset.add_version(old_item)

        # get date_modified, after everything done called onModified
        info = QtCore.QFileInfo(asset.path)
        date_modified = QtCore.QDateTime(info.lastModified()).toString('dd/MM/yyyy HH:mm')

        asset.date_modified = date_modified
        asset.file = new_file
        asset.eval()
        self.onModified()
        
    def set_assignment_date(self):
        if self.asset_container.selected_item: 
            self.date_dialog.assignment_date = []   # Refresh assignment date to empty before execute to see if user confirm
            self.date_dialog.exec()
            if self.date_dialog.assignment_date: 
                self.current_project.execute(cmd_setAssignmentDate(self, self.asset_container.selected_item, self.date_dialog.assignment_date))

    def remove_assignment_date(self):
        if self.asset_container.selected_item:  
            self.current_project.execute(cmd_removeAssignmentDate(self, self.asset_container.selected_item))

    def set_asset_status(self, status):
        valid_asset = [asset for asset in self.asset_container.selected_item if EZMAssetItem.verify_file_integrity(asset)]
        if valid_asset:
            self.current_project.execute(cmd_setAssetStatus(self, valid_asset, status))

    def filter_imported_asset(self, files):
        """check if file is maya and decide what asset type"""
        files = [file for file in files if self.check_if_type_compatible(file)]
        if files:
            if self.browser.get_current_tab() == 'All':
                confirm = self.group_dialog.exec()    # set to modal and blocking flow till user confirm
                if confirm: 
                    self.add_asset(files, self.group_dialog.get_group())
            else:
                self.add_asset(files, self.browser.get_current_tab())

    def check_duplicated_path(self, path, exclude=[]):
        """
        find any duplicate path from current project, exclude will ignore excluded asset
        this function acts as a warning to user, if found duplicate will return the not unique path (duplicate path)
        """
        duplicate_path = None
        duplicate_asset = None
        for asset in self.current_project.asset:
            if asset.path == path and asset not in exclude:
                duplicate_path = path
                duplicate_asset = asset
                break

        if duplicate_path:
            QtWidgets.QMessageBox.warning(self, 
                                        'Duplicate path',
                                        "Found asset with same path!\nasset name: %s\npath: %s"%(duplicate_asset.name, duplicate_asset.path))
            return duplicate_path
        else:
            return None

    def convert_to_struct(self):
        valid_selected_item = [asset for asset in self.asset_container.selected_item if EZMAssetItem.verify_file_integrity(asset) and type(asset) is EZMAssetItem]
        unique_selected_item = []
        for item in valid_selected_item:    # check if path unique
            if self.check_duplicated_path(os.path.dirname(item.path)) == None: unique_selected_item.append(item)
        if unique_selected_item:
            # warning = QtWidgets.QMessageBox.warning(self, 'Convert to struct', 'Converting asset to struct is undoable, do you wish to proceed?',QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            # if warning == QtWidgets.QMessageBox.No: return

            # convert to struct
            created_struct = []
            self.asset_container.remove_item(unique_selected_item)
            self.current_project.remove_asset(unique_selected_item)
            for asset in  unique_selected_item:
                if os.path.exists(asset.path):
                    struct = EZMAssetStruct(asset.project, 
                                    asset.asset_scroll, 
                                    asset.name, 
                                    os.path.dirname(asset.path),   # directory path for this struct
                                    asset.group, 
                                    asset.date_modified, 
                                    asset.type, 
                                    asset.status,
                                    asset.path,
                                    asset.date_assignment,
                                    asset.preview,
                                    asset.notes)
                created_struct.append(struct)
                self.asset_container.add_item(struct)
                self.current_project.add_asset(struct)
                self.asset_container.modify_selection(struct, add=True)
            self.current_project.execute(cmd_convertToStruct(self.current_project, self, unique_selected_item, created_struct))

    def create_asset_placeholder(self):
        self.hint = False
        if self.browser.get_current_tab() == 'All':
                confirm = self.group_dialog.exec()
                if confirm:
                    self.current_project.execute(cmd_createPlaceholder(self.current_project, self, self.group_dialog.get_group(), '.PLACEHOLDER'))
        else:
            self.current_project.execute(cmd_createPlaceholder(self.current_project, self, self.browser.get_current_tab(), '.PLACEHOLDER'))

    def load_asset(self):
        """load the asset when user open project, add to container and assign asset scroll"""
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        if DEBUG: print('current project: %s'%self.current_project.name)
        self.initProjectAsset()
        self.toggle_asset_visibility()
        self.sort_asset()
        self.manager.asset_detail.content_visible = False
        self.manager.asset_detail.has_selected = False
        QtWidgets.QApplication.restoreOverrideCursor()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet('background-color:#2E2E2E')
            files = [u.toLocalFile() for u in event.mimeData().urls()]
            for name in files: 
                if self.check_if_type_compatible(name): 
                    event.accept()
                    break
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet('background-color:none')

    def dropEvent(self, event):
        self.setStyleSheet('background-color:none')
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.filter_imported_asset(files)

    def selectionModified(self):
        self.app.main_window.statusBar().showMessage("Selected: %s   Total Asset: %s"%(len(self.asset_container.selected_item) , len(self.current_project.asset)))

    def deselect_all(self):
        self.asset_container.deselect_all()
        self.manager.update_asset_detail(self.asset_container.selected_item)    # update tab
        
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.asset_container.selected_item and not event.modifiers():
            self.deselect_all()

    def import_file(self, event):
        fnames, filter = QtWidgets.QFileDialog.getOpenFileNames(self, "Open Maya File", filter=("Maya Scenes (*.ma *.mb);; Maya ASCII (*.ma);; Maya Binary (*.mb);; All Files (*)"))
        if fnames != []:
            self.filter_imported_asset(fnames)
            
    def check_if_type_compatible(self, path, warning=False):
        extension = os.path.splitext(path)[1].lower()   # make text lower to consistency
        if extension in COMPATIBLE_FILE:
            return True
        if warning: QtWidgets.QMessageBox.warning(self, 'Operation denied', 'File type not supported!')
        return False

    def refresh(self):
        for asset in self.asset_container.get_all_item():
            asset.eval()
    
    def contextMenuEvent(self, event):
        if self.asset_container.selected_item:
            menu = QtWidgets.QMenu()
            selected_asset_class = [asset.__class__ for asset in self.asset_container.selected_item]
            selected_asset_type = [asset.type for asset in self.asset_container.selected_item]
            # check if selected has assignment date
            has_unassigned_asset_on_selection = True
            for asset in self.asset_container.selected_item:
                if not asset.date_assignment: 
                    has_unassigned_asset_on_selection = False
                    break
            
            if not EZMAssetStruct in selected_asset_class:
                updateStruct = menu.addAction(QtGui.QIcon(get_path('update.png', icon=True)),
                                            'update')
                createStruct = menu.addAction(QtGui.QIcon(get_path('file_struct.png', icon=True)),
                                            'convert to struct')
                if '.object' in selected_asset_type: createStruct.setEnabled(False) # disable if placeholder inside
            
            if not EZMAssetItem in selected_asset_class:
                publishStruct = menu.addAction(QtGui.QIcon(get_path('export.png', icon=True)),
                                            'publish asset')

            setDateAssignmentStruct = menu.addAction(QtGui.QIcon(get_path('timer.png', icon=True)),
                                                'set assignment date')
            
            if has_unassigned_asset_on_selection:
                removeDateAssignmentStruct = menu.addAction(QtGui.QIcon(get_path('delete_timer.png', icon=True)),
                                                    'remove assignment date')

            menu.addSeparator()

            verifyStruct = menu.addAction(QtGui.QIcon(get_path('verified.png', icon=True)),
                                        'verify')
            checkStruct = menu.addAction(QtGui.QIcon(get_path('checked.png', icon=True)),
                                        'check')
            uncheckStruct = menu.addAction(QtGui.QIcon(get_path('unchecked_red.png', icon=True)),
                                        'uncheck')
            menu.addSeparator()
            deselectStruct = menu.addAction(QtGui.QIcon(get_path('deselect.png', icon=True)),
                                        'deselect')
            deleteStruct = menu.addAction(QtGui.QIcon(get_path('close-small.png', icon=True)),
                                        'delete')

            res = menu.exec(event.globalPos())
            
            if not EZMAssetStruct in selected_asset_class:
                if res == updateStruct:
                    self.update_asset()
                elif res == createStruct:
                    self.convert_to_struct()
            if not EZMAssetItem in selected_asset_class:
                if res == publishStruct:
                    self.publish_asset()
            
            if has_unassigned_asset_on_selection:
                if res == removeDateAssignmentStruct:
                    self.remove_assignment_date()

            if res == setDateAssignmentStruct:
                self.set_assignment_date()
            elif res == verifyStruct:
                self.set_asset_status(2)
            elif res == checkStruct:
                self.set_asset_status(1)
            elif res == uncheckStruct:
                self.set_asset_status(0)
            elif res == deselectStruct:
                self.deselect_all()
            elif res == deleteStruct:
                self.delete_asset()

        else:
            menu = QtWidgets.QMenu()
            assetPlaceholderStruct = menu.addAction(QtGui.QIcon(get_path('file_.object.png', icon=True)),
                                    'create placeholder')
            menu.addSeparator()
            refreshStruct = menu.addAction(QtGui.QIcon(get_path('refresh.png', icon=True)),
                                    'refresh')

            res = menu.exec(event.globalPos())
            if res == assetPlaceholderStruct:
                self.create_asset_placeholder()
            elif res == refreshStruct:
                self.refresh()

class EZMAssetItem(custom_widget.InteractiveItem):
    def __init__(self, project, asset_scroll, name, path, group, date_modified, type, status, date_assignment=[], preview='',notes=''):
        """ status { 0:checked ; 1:checked ; 2:verified }"""
        
        self.project = project
        self.asset_scroll = asset_scroll
        self.name = name
        self.path = path
        self.group = group
        self.date_modified = date_modified
        self._type = type
        self._status = status  # assigned in eval when open asset
        self.preview = preview
        self.notes = notes

        self.days_left = None

        super().__init__() # it automatically call initUI and init container
        self.date_assignment = date_assignment  # contains 2 item in list [start date, due date] (called after init ui)
        self.loadAssignment()   # if asset contains assignment date, initialize to calendar editor (init last as everything is done)

    @staticmethod
    def verify_file_integrity(asset):
        asset.eval()    # update ui
        if os.path.exists(asset.path): return True
        else: return False

    @property
    def type(self):
        return self._type
    
    @type.setter
    def type(self, type):
        self._type = type
        self.reassign_file_icon()

    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, status):
        self._status = status
        if status == 0:
            self.version_lbl.change_icon(get_path('unchecked.png', icon=True))
        elif status == 1:
            self.version_lbl.change_icon(get_path('checked.png', icon=True))
        elif status == 2:
            self.version_lbl.change_icon(get_path('verified.png', icon=True))
        self.update_deadline_UI()

    @property
    def date_assignment(self):
        return self._date_assignment
    
    @date_assignment.setter
    def date_assignment(self, date):
        self._date_assignment = date
        if not date: self.days_left = None # if assignment is removed
        self.update_deadline_UI()

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.item_layout = QtWidgets.QHBoxLayout()

        self.version_lbl = custom_widget.GraphicLabel(get_path('unchecked.png', icon=True), (24,24))
        self.icon_lbl = custom_widget.ValidableGraphicLabel(get_path('file_%s.png'%self.type, icon=True), (28,28))
        self.name_lbl = custom_widget.NameableLabel(self.name, 99)
        self.name_lbl.renameEvent = self.renameEvent    # override virtual function event
        self.remaining_time_lbl = QtWidgets.QLabel('3 days')
        self.deadline_btn = custom_widget.GraphicButton(get_path('timer.png', icon=True),self.go_to_assignment,QtGui.QColor("orange"),1,(16,16))
        self.path_btn = custom_widget.GraphicButton(get_path("external_link.png",icon=True),self.go_to_path,QtGui.QColor("white"),0.7,(16,16))

        self.item_layout.addWidget(self.version_lbl)
        self.item_layout.addWidget(self.icon_lbl)
        self.item_layout.addWidget(self.name_lbl)
        self.item_layout.addStretch()
        self.item_layout.addWidget(self.remaining_time_lbl)
        self.item_layout.addWidget(self.deadline_btn)
        self.item_layout.addWidget(self.path_btn)

        self.main_layout.addLayout(self.item_layout)

    def get_date_key_calendar(self):
        """one way to check if asset is assigned with deadline"""
        key = [i for i in self.get_calendar_editor().asset_data if self in self.get_calendar_editor().asset_data[i]]
        if key: return key[0]
        else: return False
    
    def get_calendar_editor(self):
        """helper function to get calendar editor"""
        return self.asset_scroll.app.calendar_editor
    
    def is_assignment_visible(self):
        """check if assignment is being previewed, using data from calendar not assignment date"""
        if not self.get_date_key_calendar(): return False
        return self.get_date_key_calendar() in self.get_calendar_editor().date_obj
    
    def remove_asset_assignment_from_calendar(self):
        """helper function to remove cache asset data in calendar editor and assignment checkbox if date is visible. not handling assignment_date on asset"""
        if not self.get_date_key_calendar(): return False # asset is not found inside asset data
        if self.is_assignment_visible():
            date_widget = self.get_calendar_editor().date_obj[self.get_date_key_calendar()]
            assignment_box = date_widget.active_assignment[self]
            assignment_box.remove_UI_data() # handle data for ui necessity
            assignment_box.setParent(None)
            del date_widget.active_assignment[self]
            date_widget.onAddRemoveCheckboxData()
        asset_data_on_date = self.get_calendar_editor().asset_data[self.get_date_key_calendar()] 
        asset_data_on_date.remove(self)
        self.get_calendar_editor().asset_data[self.get_date_key_calendar()] = asset_data_on_date

    def loadAssignment(self):
        """update data inside this class to checklist class. act as a super function to handle multiple condition (might not be the best)"""
        # if assignment date,status,name changed (update ui in calendar editor)
        if self.get_date_key_calendar():
            # when date doesnt match
            if self.date_assignment and self.get_date_key_calendar() != self.date_assignment[1]:
                self.remove_asset_assignment_from_calendar()
                self.get_calendar_editor().add_asset(self.date_assignment[1], self)
            if self.is_assignment_visible():
                date_widget = self.get_calendar_editor().date_obj[self.get_date_key_calendar()]
                assignment_box = date_widget.active_assignment[self]
                # when status doesnt match
                if (assignment_box.isChecked and self.status != 2) or (not assignment_box.isChecked and self.status ==2):
                    if self.status == 2: assignment_box.setCheck(True)
                    else: assignment_box.setCheck(False)
                    date_widget.calendar.detail_tab.update_detail(list(date_widget.active_assignment.values())+list(date_widget.active_todolist))
                # when description doesnt match
                if assignment_box.description != self.name:
                    assignment_box.setDescription(self.name)
            self.get_calendar_editor().update_calendar() # refresh calendar widget (current month only)

        # if asset has assignment but not registered to calendar yet
        if not self.get_date_key_calendar() and len(self.date_assignment)==2:
            self.get_calendar_editor().add_asset(self.date_assignment[1], self)
            return
        # check if asset is deleted
        if self.container == None and self.get_date_key_calendar():
            self.remove_asset_assignment_from_calendar()
            return
           
    def reassign_file_icon(self):
        """decide which asset icon to display, assume all sources image has valid path name"""
        self.icon_lbl.change_icon(get_path('file_%s.png'%self.type, icon=True))

    def go_to_assignment(self, event):
        self.asset_scroll.app.calendar_dock.show()
        date = QtCore.QDate.fromString(self.date_assignment[1],'dd/MM/yyyy')
        self.get_calendar_editor().load_calendar(date.year(),date.month())
        self.get_calendar_editor().select_by_datekey(self.date_assignment[1])

    def go_to_path(self, event):
        self.asset_scroll.refresh() # update all asset ui
        if os.path.exists(self.path):
            self.process = subprocess.Popen('explorer /select,%s'%os.path.normpath(self.path))
        else: warning_path_not_exist(self, self.path)

    def renameEvent(self, text):
        self.project.execute(cmd_renameAsset(self, text))

    def selectEvent(self, asset):
        self.asset_scroll.manager.update_asset_detail(asset)    # if has multiple selection only accept last one

    def select(self):
        """select and highlight the asset and also open the asset detail"""
        self.asset_scroll.manager.update_asset_detail([self])
        self.asset_scroll.manager.asset_detail.content_visible = True
        self.container.reset_selection([self])

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if DEBUG: print("selected > ", [item.name for item in self.container.selected_item])
        self.asset_scroll.app.main_window.statusBar().showMessage("Selected: %s   Total Asset: %s"%(len(self.container.selected_item) , len(self.project.asset)))

    def mouseDoubleClickEvent(self, event):
        # reverse the asset detail tab when double click
        self.asset_scroll.manager.asset_detail.content_visible = not self.asset_scroll.manager.asset_detail.content_visible

    def eval(self):
        """this function help to take care of all ui stuff only, display warning when invalid - vice versa"""
        if self.type == '.object': return   # ignore placeholder
        if not os.path.exists(self.path):
            self.version_lbl.change_icon(get_path('warning.png', icon=True))
            self.version_lbl.setToolTip('path not found')
            self.name_lbl.label.setStyleSheet('color: #FF6E70')
        else: 
            self.status = self.status # retrieve normal status icon display
            self.version_lbl.setToolTip(None)
            self.name_lbl.label.setStyleSheet('color: white')

    def update_deadline_UI(self):
        if self.date_assignment and self.status != 2:
            self.deadline_btn.show()
            self.remaining_time_lbl.show()
            self.days_left = QtCore.QDateTime.currentDateTime().daysTo(QtCore.QDateTime.fromString(self.date_assignment[1],'dd/MM/yyyy'))
            if self.days_left > 14:
                self.remaining_time_lbl.setStyleSheet('color:DeepSkyBlue')
            elif 7 < self.days_left <= 14:
                self.remaining_time_lbl.setStyleSheet('color:yellow')
            elif 2 < self.days_left <= 7:
                self.remaining_time_lbl.setStyleSheet('color:orange')
            elif 0 <= self.days_left <= 2:
                self.remaining_time_lbl.setStyleSheet('color:tomato')
            else:
                self.remaining_time_lbl.setStyleSheet('color:grey')
            self.remaining_time_lbl.setText('%s days'%self.days_left)
        elif self.date_assignment and self.status == 2:
            self.remaining_time_lbl.hide()
            self.deadline_btn.show()
        else:
            self.remaining_time_lbl.hide()
            self.deadline_btn.hide()

    def serialize(self):
        asset_dict =  OrderedDict([('name', self.name),
                                   ('path', self.path),
                                   ('group', self.group),
                                   ('date_modified', self.date_modified),
                                   ('type', self.type),
                                   ('status', self.status),
                                   ('date_assignment', self.date_assignment),
                                   ('preview', self.preview),
                                   ('notes', self.notes)])
        return asset_dict

class EZMAssetStruct(EZMAssetItem):
    def __init__(self, project, asset_scroll, name, path, group, date_modified, type, status, file, date_assignment=[], preview='', notes=''):
        self._file = file
        super().__init__(project, asset_scroll, name, path, group, date_modified, type, status, date_assignment, preview, notes) 
        self.reassign_file_icon()   # cheating way to update file icon, might need to cleaner way

        self.collapsed = True
        self.file_version = []  # contain other version of this struct

        #self.initFolder()

    @property
    def file(self):
        return self._file
    
    @file.setter
    def file(self, file):
        self._file = file
        basename = os.path.basename(self._file)
        self.file_lbl.setText(basename)
        self.reassign_file_icon()

    def reassign_file_icon(self):
        self.file_icon.change_icon(get_path('file_%s.png'%os.path.splitext(self.file)[1].lower()[1:], icon=True))

    # def initFolder(self):
    #     """Guard to check folder, everytime object is created or load"""
    #     if os.path.exists(self.project.path) and not os.path.exists(self.path):
    #         if DEBUG: print('init folder struct for %s, folder path: %s'%(self.name, self.path))
    #         os.makedirs(self.path)
    #     else:
    #         if DEBUG: print('(Struct) %s > cancelled build, folder with same path might be existed'%self.name)

    def initUI(self):
        super().initUI()
        self.detail_widget = QtWidgets.QFrame()
        self.detail_widget.setObjectName('struct_detail')
        self.detail_widget.setContentsMargins(20,0,0,0)
        self.detail_widget.setStyleSheet('QFrame#struct_detail{border: 1px solid #505050}') #1363bf > blue
        self.detail_layout = QtWidgets.QVBoxLayout(self.detail_widget)
        self.file_layout = QtWidgets.QHBoxLayout()
        self.old_ver_layout = QtWidgets.QVBoxLayout()

        # struct additional widget
        self.icon_lbl.change_icon(get_path('file_struct.png', icon=True))
        self.detail_icon = custom_widget.GraphicButton(get_path('expand.png', icon=True),
                                                       self.toggle_detail, 
                                                       color=QtGui.QColor('white'), 
                                                       strength=1,
                                                       size=(12,12))

        #self.warning_icon = custom_widget.GraphicLabel(get_path('warning.png', icon=True), (20,20))
        self.file_icon = custom_widget.ValidableGraphicLabel(get_path('file_%s.png'%self.type, icon=True), (24,24))
        self.file_lbl = custom_widget.LimitedLabel(os.path.basename(self.file), 99)

        # old version widget configuration
        self.old_file_widget = custom_widget.ExpandableWidget()
        self.folder_icon = custom_widget.GraphicLabel(get_path('folder.png', icon=True), (20,20))
        self.other_ver_lbl = QtWidgets.QLabel('version [0 items]')

        self.old_file_widget.header_layout.insertWidget(0, self.folder_icon)
        self.old_file_widget.header_layout.insertWidget(1, self.other_ver_lbl)
        self.old_file_widget.header_layout.addStretch()

        # self.option_icon = custom_widget.GraphicButton(get_path('option.png', icon=True), 
        #                                                color=QtGui.QColor('white'), 
        #                                                strength=1,
        #                                                size=(16,16))
        # self.item_layout.insertWidget(5, self.option_icon)

        self.item_layout.insertWidget(2, self.detail_icon)

        #self.file_layout.addWidget(self.warning_icon)
        self.file_layout.addWidget(self.file_icon)
        self.file_layout.addWidget(self.file_lbl)

        self.old_ver_layout.addWidget(self.old_file_widget)

        self.detail_layout.addLayout(self.file_layout)
        self.detail_layout.addLayout(self.old_ver_layout)

        self.main_layout.addLayout(self.item_layout)
        self.main_layout.addWidget(self.detail_widget)
        
        self.detail_widget.hide()

    def add_version(self, item):
        self.filter_duplicate(item)
        self.file_version.append(item)
        self.old_file_widget.add_item(item)
        self.other_ver_lbl.setText('version [%s items]'%len(self.file_version))

    def remove_version(self, item):
        self.file_version.remove(item)
        self.asset_scroll.onModified()
        self.other_ver_lbl.setText('version [%s items]'%len(self.file_version))

    def filter_duplicate(self, item):
        """check if any duplicate version available, if present will always delete older one"""
        for version in self.file_version: # bug prevent from duplicate path old version
            if os.path.normpath(version.path) == os.path.normpath(item.path):
                self.file_version.remove(version)
                version.setParent(None)
                version.deleteLater()

    # def renameEvent(self, text):
    #     # this will called if text not empty or same as previous text
    #     if self.verify_file_integrity(self):
    #         for char in INVALID_FILENAME_CHARACTERS: 
    #             if char in text: 
    #                 print("filename can't contains invalid character!")
    #                 self.name_lbl.revert_changes()
    #                 return
    #         #self.rename_active_struct(text)
    #         self.project.execute(cmd_renameStruct(self, text))
    #     else: 
    #         self.name_lbl.revert_changes()
    #         print('cant rename, path not found')

    # def rename_active_struct(self, text):
    #     """check for duplicate for all asset in project and target directory, return unique path, unique name for both.might work unexpectedly for file (not folder)"""
    #     all_asset_name_in_project = [asset.name for asset in self.project.asset]
    #     unique_path = filter_path_name(os.path.join(os.path.dirname(self.path), text), text)
    #     unique_name = check_duplicate_str(os.path.basename(unique_path), all_asset_name_in_project)

    #     while os.path.basename(unique_path) != unique_name:
    #         unique_path = filter_path_name(os.path.join(os.path.dirname(self.path), unique_name), unique_name)
    #         unique_name = check_duplicate_str(os.path.basename(unique_path), all_asset_name_in_project)
        
    #     return unique_path, unique_name

    def go_to_path(self, event):
        self.asset_scroll.refresh() # update all asset ui
        if os.path.exists(self.path):
            os.startfile(self.path)
        else: warning_path_not_exist(self, self.path)

    def toggle_detail(self, event):
        if self.collapsed:
            self.detail_widget.show()
            self.detail_icon.change_icon(get_path('collapse.png', icon=True))
            self.collapsed = False
        else:
            self.detail_widget.hide()
            self.detail_icon.change_icon(get_path('expand.png', icon=True))
            self.collapsed = True

    def eval(self):
        super().eval()
        # evaluation for file
        if os.path.exists(self.file): 
            #self.warning_icon.hide()
            self.icon_lbl.set_valid(True)
            self.file_icon.set_valid(True)
            self.file_icon.setToolTip(None)
            self.file_lbl.setStyleSheet('color: white')
        else: 
            #self.warning_icon.show()
            self.icon_lbl.set_valid(False)
            self.file_icon.set_valid(False)
            self.file_icon.setToolTip('file missing')
            self.file_lbl.setStyleSheet('color: #FF6E70')
        # evaluation for older file version
        for version in self.file_version: version.eval()

    def serialize(self):
        all_version = []
        for version in self.file_version:
            all_version.append(version.serialize())

        asset_dict =  OrderedDict([('name', self.name),
                                   ('path', self.path),
                                   ('group', self.group),
                                   ('date_modified', self.date_modified),
                                   ('type', self.type),
                                   ('status', self.status),
                                   ('file', self.file),
                                   ('date_assignment', self.date_assignment),
                                   ('preview', self.preview),
                                   ('file_version', all_version),
                                   ('notes', self.notes)])
        return asset_dict
    
    def deserialize(self, file_version=[]):
        try:
            for data in file_version:
                version = EZMAssetVersion(self, data['name'], data['path'], data['group'], data['date_modified'], data['type'], data['status'])
                self.add_version(version)
        except Exception as e: print(e)

class EZMAssetVersion(QtWidgets.QFrame):
    """it's similar to how you treat EZMAssetItem without interactive and additional properties"""
    def __init__(self, struct, name, path, group, date_modified, type, status):
        super().__init__()
        self.struct = struct
        self.name = name
        self.path = path
        self.group = group
        self.date_modified = date_modified
        self.type = type
        self.status = status

        self.initUI()

    def initUI(self):
        self.setMaximumHeight(30)
        self.setObjectName('assetVersion')
        self.setStyleSheet('QFrame#assetVersion{border: 1px solid #505050}')

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(3,3,3,3)
        self.warning_lbl = custom_widget.GraphicLabel(get_path('warning2.png', icon=True), (16,16))
        self.warning_lbl.hide()
        self.icon_lbl = custom_widget.ValidableGraphicLabel(get_path('file_%s.png'%os.path.splitext(self.path)[1].lower()[1:], icon=True), (16,16))
        self.filename_lbl = custom_widget.LimitedLabel(self.name, 45)
        self.filename_lbl.setMinimumWidth(345)
        self.filename_lbl.setFont(QtGui.QFont('Consolas'))
        self.date_lbl = QtWidgets.QLabel(self.date_modified)
        self.date_lbl.setFont(QtGui.QFont('Consolas'))
        self.switch_btn = custom_widget.GraphicButton(get_path("switch.png", icon=True), self.switch_version, size=(16,16))
        self.switch_btn.setToolTip('set this version as default')
        self.delete_btn = custom_widget.GraphicButton(get_path('delete.png', icon=True), self.onDelete, size=(16,16))

        self.main_layout.addWidget(self.warning_lbl)
        self.main_layout.addWidget(self.icon_lbl)
        self.main_layout.addWidget(self.filename_lbl)
        self.main_layout.addWidget(self.date_lbl)
        self.main_layout.addWidget(self.switch_btn)
        self.main_layout.addWidget(self.delete_btn)

    def switch_version(self, event):
        if os.path.exists(self.path):
            if self.struct.asset_scroll.check_before_publish(self.path, self.struct):   # check if all goes well
                if self.struct.asset_scroll.update_struct(self.struct, self.path, version_suffix=False) == False: return # check if user not cancelled (if current file exist in older ver)
                self.struct.remove_version(self)
                self.setParent(None)
                self.deleteLater()
                if os.path.exists(self.path): send2trash(self.path.replace("/", "\\"))  # safe version: cuz it's copy and delete the older version
                self.struct.asset_scroll.onModified()
        else: print("can't switch version, file is not found!")

    def onDelete(self, event):
        self.struct.remove_version(self)
        self.setParent(None)
        self.deleteLater()
        if os.path.exists(self.path): send2trash(self.path.replace("/", "\\"))  # safe version: it's intuitive and clear

    def eval(self):
        if os.path.exists(self.path):
            self.setStyleSheet('QFrame#assetVersion{border: 1px solid #505050}')
            self.warning_lbl.hide()
            self.warning_lbl.setToolTip(None)
        else:
            self.setStyleSheet('QFrame#assetVersion{border: 1px solid crimson}')
            self.warning_lbl.show()
            self.warning_lbl.setToolTip('file not found')

    def serialize(self):
        version_dict =  OrderedDict([('name', self.name),
                                    ('path', self.path),
                                    ('group', self.group),
                                    ('date_modified', self.date_modified),
                                    ('type', self.type),
                                    ('status', self.status)])
        return version_dict

class EZMAssetSplitter(QtWidgets.QFrame):

    def __init__(self, detail, parent=None):
        super().__init__(parent)

        self.setObjectName('splitterFrame')
        self.detail = detail
        self.setStyleSheet('EZMAssetSplitter#splitterFrame {border: 1px solid #505050}')
        self.setFixedWidth(5)

    def enterEvent(self, event):
        if self.detail.content_visible: self.setCursor(QtCore.Qt.SplitHCursor)

    def leaveEvent(self, event):
        self.setCursor(QtCore.Qt.ArrowCursor)
        
    def mouseMoveEvent(self, event):
        if self.detail.content_visible:
            detail_width = self.detail.width()-event.pos().x()
            if detail_width > 200:
                self.detail.setMaximumWidth(self.detail.width()-event.pos().x())

class EZMAssetDetail(QtWidgets.QTabWidget):

    def __init__(self):
        super().__init__()
        self.setObjectName('assetDetailTab')

        self.current_asset = None
        self._content_visible = True
        self._has_selected = False

        self._lock_desc = True

        self.initUI()
        self.initConnection()

        # collapse content property
        self.tabBarClicked.connect(self.onClickTab)
        self.stacked_widget = self.findChild(QtWidgets.QStackedWidget)

    @property
    def has_selected(self):
        return self._has_selected

    @has_selected.setter
    def has_selected(self, selection):
        self.selection = selection
        self.show_selected_detail(self.selection)

    @property
    def content_visible(self):
        return self._content_visible
    
    @content_visible.setter
    def content_visible(self, show):
        if self.content_visible != show:
            self._content_visible = show
            self.set_content_visible(self.content_visible)

    @property
    def lock_desc(self):
        return self._lock_desc
    
    @lock_desc.setter
    def lock_desc(self, value):
        self._lock_desc = value
        if self.lock_desc: self.notes_btn.change_icon(get_path('edit.png', icon=True))
        else: self.notes_btn.change_icon(get_path('save.png', icon=True))
        self.notes_edit.setReadOnly(self.lock_desc)

    def initUI(self):
        self.max_size = 300  # default maximum size
        self.setMaximumWidth(self.max_size)

        self.main_widget = QtWidgets.QStackedWidget()
        self.main_widget.setMinimumWidth(225)
        self.detail_widget = QtWidgets.QWidget()
        self.detail_layout = QtWidgets.QVBoxLayout(self.detail_widget)
        self.description_layout = QtWidgets.QHBoxLayout()
        self.empty_widget = QtWidgets.QWidget()
        self.empty_layout = QtWidgets.QHBoxLayout(self.empty_widget)
        self.path_layout = QtWidgets.QHBoxLayout()

        self.name_edit = custom_widget.ShortLabel('PlaceHolder', 50)
        self.thumbnail_lbl = custom_widget.GraphicLabel(get_path('no_preview.png', icon=True),(160,96))
        self.screenshot_btn = custom_widget.GraphicButton(get_path('screenshot.png', icon=True), self.takeScreenshot, QtGui.QColor('orange'), strength=1, size=(28,28))
        self.screenshot_btn.setParent(self.thumbnail_lbl)
        self.path_lbl = QtWidgets.QLabel("Path:")
        self.path_field = QtWidgets.QLineEdit('-')
        self.path_field.setReadOnly(True)
        self.path_btn = custom_widget.GraphicButton(get_path("external_link.png",icon=True),self.go_to_path,QtGui.QColor("white"),0.7,(16,16))
        self.updated_lbl = QtWidgets.QLabel("Last Updated: ")
        self.notes_edit = QtWidgets.QPlainTextEdit()
        self.notes_edit.setPlaceholderText('description...')
        self.notes_edit.setReadOnly(True)
        self.notes_btn = custom_widget.GraphicButton(get_path("edit.png",icon=True),self.toggle_edit_desc,size=(20,20))
        self.open_btn = QtWidgets.QPushButton("Open")

        self.no_selection_lbl = QtWidgets.QLabel('No Selected Items')

        self.path_layout.addWidget(self.path_lbl)
        self.path_layout.addWidget(self.path_field)
        self.path_layout.addWidget(self.path_btn)

        self.detail_layout.addWidget(self.name_edit)
        self.detail_layout.addSpacing(16)
        self.detail_layout.addWidget(self.thumbnail_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.detail_layout.addSpacing(16)
        self.detail_layout.addLayout(self.path_layout)
        self.detail_layout.addWidget(self.updated_lbl)
        self.detail_layout.addLayout(self.description_layout)
        self.description_layout.addWidget(self.notes_edit)
        self.description_layout.addWidget(self.notes_btn,alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        self.detail_layout.addWidget(self.open_btn)
        
        self.empty_layout.addWidget(self.no_selection_lbl, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.main_widget.addWidget(self.empty_widget)
        self.main_widget.addWidget(self.detail_widget)

        self.addTab(self.main_widget, 'Asset Details')
        self.setTabPosition(QtWidgets.QTabWidget.East)

    def initConnection(self):
        self.open_btn.clicked.connect(self.open_file)

    def go_to_path(self, event):
        self.current_asset.eval()   # update ui
        if os.path.exists(self.path_field.text()):
            if type(self.current_asset) is EZMAssetItem:
                self.process = subprocess.Popen('explorer /select,%s'%os.path.normpath(self.path_field.text()))
            elif type(self.current_asset) is EZMAssetStruct:
                os.startfile(self.path_field.text())
        else: warning_path_not_exist(self, self.path_field.text())

    def open_file(self):
        if type(self.current_asset) is EZMAssetItem:
            if os.path.exists(self.path_field.text()):
                os.startfile(self.path_field.text())
            else: warning_path_not_exist(self, self.path_field.text())

        if type(self.current_asset) is EZMAssetStruct:
            if os.path.exists(self.current_asset.file):
                os.startfile(self.current_asset.file)
            else: warning_path_not_exist(self, self.current_asset.file)
        
    def takeScreenshot(self, event):
        screenshot_dialog = EZMScreenshotEdit(self.current_asset ,self)
        screenshot_dialog.captureImg()

    def toggle_edit_desc(self, event):
        if not self.lock_desc:  # save notes to asset
            self.current_asset.notes = self.notes_edit.toPlainText()
            self.current_asset.asset_scroll.onModified() # save
            return # just return cause onmodified will lock the desc
        self.lock_desc = not self.lock_desc
        
    def onClickTab(self, index):
        self.content_visible = not self.content_visible  # reverse value True/False from current

    def set_content_visible(self, visible):
        self.setDocumentMode(not visible) # make tab widget read-only, prevent unwanted process
        self.stacked_widget.setVisible(visible)
        tab_hint = self.tabBar().sizeHint()
        self.max_size = 300

        # work only on vertical tab widget, if horizontal change tab_hint.width() to height() and maximumwidth to maximumheight
        if not visible:
            self.max_size = tab_hint.width()
            self.setMaximumWidth(self.max_size)
            #self.parent().moveSplitter(0,1) # update splitter
        else:
            self.setMaximumWidth(self.max_size)

    def show_selected_detail(self, selection):
        if selection: self.main_widget.setCurrentWidget(self.detail_widget)
        else: self.main_widget.setCurrentWidget(self.empty_widget)

class EZMQueryAssetGroup(QtWidgets.QDialog):
    def __init__(self, asset_scroll=None):
        super().__init__(asset_scroll)

        self.setWindowTitle('Choose Asset Type')

        self.initUI()
        self.initConnection()

    def initUI(self):
        self.setModal(True)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.type_layout = QtWidgets.QHBoxLayout()
        self.btn_layout = QtWidgets.QHBoxLayout()

        self.type_btn_grp = QtWidgets.QButtonGroup()

        self.character_btn = QtWidgets.QRadioButton("Character")
        self.prop_btn = QtWidgets.QRadioButton("Prop")
        self.prop_btn.setChecked(True)
        self.sets_btn = QtWidgets.QRadioButton("Sets")

        self.type_btn_grp.addButton(self.character_btn)
        self.type_btn_grp.addButton(self.prop_btn)
        self.type_btn_grp.addButton(self.sets_btn)

        self.confirm_btn = QtWidgets.QPushButton('Confirm')

        self.type_layout.addWidget(self.character_btn)
        self.type_layout.addWidget(self.prop_btn)
        self.type_layout.addWidget(self.sets_btn)

        self.btn_layout.addWidget(self.confirm_btn)

        self.main_layout.addLayout(self.type_layout)
        self.main_layout.addLayout(self.btn_layout)

    def initConnection(self):
        self.confirm_btn.clicked.connect(self.onClickConfirm)

    def get_group(self):
        return self.type_btn_grp.checkedButton().text()

    def onClickConfirm(self):
        self.close()
        self.accept()   # return true

# evading circular import, when all class initialize than initialize all commands (cheat)
from commands import *  