from collections import OrderedDict
#from send2trash import send2trash

from PySide6 import QtCore, QtWidgets, QtGui

from app_assets_widget import EZMAssetItem, EZMAssetStruct
from util import *

import os
import shutil

class cmd_addAsset(QtGui.QUndoCommand):
    desc = 'add asset'

    def __init__(self, project, asset_scroll, files, group):
        super().__init__(self.desc)

        self.project = project
        self.asset_scroll = asset_scroll
        self.files = files
        self.group = group
        
        self.scroll_container = self.asset_scroll.asset_container
        self.assets_name = [asset.name for asset in self.project.asset]

        self.created_asset = [] # hold the asset data if created, for undo

    def redo(self):
        for file in self.files:
            # create asset 
            name = check_duplicate_str(os.path.splitext(os.path.basename(file))[0], self.assets_name)
            info = QtCore.QFileInfo(file)
            last_modified = QtCore.QDateTime(info.lastModified()).toString('dd/MM/yyyy HH:mm')
            file_type = os.path.splitext(file)[1].lower()[1:]
            new_asset = EZMAssetItem(self.project, self.asset_scroll, name, file, self.group, last_modified, file_type, 0)
            
            # add new asset to project and show
            self.scroll_container.add_item(new_asset)
            self.project.add_asset(new_asset)
            self.created_asset.append(new_asset) 
        self.asset_scroll.onModified()

    def undo(self):
        self.project.remove_asset(self.created_asset)
        self.scroll_container.remove_item(self.created_asset)
        self.asset_scroll.onModified()  # trigger to save changes
        self.created_asset = [] # clear created asset again to inital state

class cmd_deleteAsset(QtGui.QUndoCommand):
    desc = 'delete asset'

    def __init__(self, selection, asset_scroll, project):
        super().__init__(self.desc)

        self.selection = selection.copy()    # shallow copy, prevent linked assignment
        self.asset_scroll = asset_scroll
        self.project = project
        self.scroll_container = self.asset_scroll.asset_container

    def redo(self):
        self.scroll_container.remove_item(self.selection)
        self.project.remove_asset(self.selection)
        self.asset_scroll.onModified()
        for asset in self.selection:
            asset.loadAssignment()  # update to assignment if available

    def undo(self):
        for asset in self.selection:
            self.scroll_container.add_item(asset)
            self.project.add_asset(asset)
            asset.loadAssignment()  # update to assignment if available
        self.scroll_container.reset_selection(self.selection)   # retrieve selection before deletion
        self.asset_scroll.onModified()

class cmd_renameAsset(QtGui.QUndoCommand):
    desc = 'rename asset'

    def __init__(self, asset, name):
        super().__init__(self.desc)
        self.project = asset.project

        self.asset = asset
        self.name_after = check_duplicate_str(name, [asset.name for asset in self.project.asset])
        self.name_before = self.asset.name

    def redo(self):
        self.asset.name = self.name_after
        self.asset.name_lbl.update_text(self.name_after)    # do this to make sure name still match if user do, undo and redo again 
        self.asset.asset_scroll.onModified()    # also update asset detail here
        self.asset.loadAssignment()

    def undo(self):
        self.asset.name = self.name_before
        self.asset.name_lbl.update_text(self.name_before) 
        self.asset.asset_scroll.onModified()    # also update asset detail here
        self.asset.loadAssignment()

class cmd_updateAsset(QtGui.QUndoCommand):
    desc = 'update asset'

    def __init__(self, asset_scroll, asset, file):
        super().__init__(self.desc)

        self.asset_scroll = asset_scroll
        self.asset = asset
        self.file = file

        self.prev_path = self.asset.path
        self.prev_date = self.asset.date_modified
        self.prev_type = self.asset.type

    def redo(self):
        self.asset.path = self.file
        info = QtCore.QFileInfo(self.file)
        last_modified = QtCore.QDateTime(info.lastModified()).toString('dd/MM/yyyy HH:mm')
        self.asset.date_modified = last_modified
        file_type = os.path.splitext(self.file)[1].lower()[1:]
        self.asset.type = file_type
        self.asset_scroll.onModified()

    def undo(self):
        self.asset.path = self.prev_path
        self.asset.date_modified = self.prev_date
        self.asset.type = self.prev_type
        self.asset_scroll.onModified()

class cmd_setAssetStatus(QtGui.QUndoCommand):
    desc = 'set asset status'

    def __init__(self, asset_scroll, assets, status):
        super().__init__(self.desc)

        self.asset_scroll = asset_scroll
        self.assets = assets.copy()
        self.status = status

        self.assets_status = [asset.status for asset in self.assets] # save all status data from order selection

    def redo(self):
        for asset in self.assets:
            asset.status = self.status
            asset.loadAssignment()
        self.asset_scroll.onModified()

    def undo(self):
        for index, asset in enumerate(self.assets):
            asset.status = self.assets_status[index]
            asset.loadAssignment()
        self.asset_scroll.onModified()

class cmd_createPlaceholder(QtGui.QUndoCommand):
    desc = 'create placeholder asset'

    def __init__(self, project, asset_scroll, group, name):
        super().__init__(self.desc)
        self.project = project
        self.asset_scroll = asset_scroll
        self.group = group
        self.name = check_duplicate_str(name, [asset.name for asset in self.project.asset])

        self.scroll_container = self.asset_scroll.asset_container

        self.placeholder = None

    def redo(self):
        self.placeholder = EZMAssetItem(self.project, self.asset_scroll,self. name, '', self.group, '01/01/9999 00:00', '.object', 0)  #.object name to put this type at top when sort by name

        # add new asset to project and show
        self.scroll_container.add_item(self.placeholder)
        self.project.add_asset(self.placeholder)
        self.asset_scroll.onModified()

    def undo(self):
        self.project.remove_asset([self.placeholder])
        self.scroll_container.remove_item([self.placeholder])
        self.asset_scroll.onModified()  # trigger to save changes

class cmd_convertToStruct(QtGui.QUndoCommand):
    desc = 'convert to struct'

    def __init__(self, project, asset_scroll, assets, structs):
        super().__init__(self.desc)
        self.project = project
        self.asset_scroll = asset_scroll
        self.assets = assets
        self.structs = structs
        self.scroll_container = self.asset_scroll.asset_container

    def redo(self):
        # remove assets
        self.scroll_container.remove_item(self.assets)
        self.project.remove_asset(self.assets)

        # add struct
        for struct in self.structs:
            self.scroll_container.add_item(struct)
            self.project.add_asset(struct)
            self.scroll_container.modify_selection(struct, add=True)
        self.asset_scroll.onModified()

    def undo(self):
        # add assets
        for asset in self.assets:
            self.scroll_container.add_item(asset)
            self.project.add_asset(asset)

        # remove struct
        self.scroll_container.remove_item(self.structs)
        self.project.remove_asset(self.structs)
        self.asset_scroll.onModified()

class cmd_publishAsset(QtGui.QUndoCommand):
    """DEPRECATED, NOT USED"""
    desc = 'publish asset to struct'

    def __init__(self, asset_scroll, asset, file):
        super().__init__(self.desc)
        self.asset_scroll = asset_scroll
        self.asset = asset
        self.file = file

    def redo(self):
        # move existing file if exists to old file, also check if old present
        self.old_folder = os.path.join(self.asset.path, '.old')
        self.old_file = os.path.join(self.old_folder, os.path.basename(self.asset.file))
        self.new_file = os.path.join(self.asset.path, os.path.basename(self.file))

        if os.path.exists(self.asset.file):
            if not os.path.exists(self.old_folder):
                os.makedirs(self.old_folder)
            if not os.path.exists(self.old_file):
                shutil.move(self.asset.file, self.old_folder)
            elif os.path.exists(self.old_file):
                warning = QtWidgets.QMessageBox.warning('File already exists!', "Can't move older version to .old folder, file already exists!\n\ndo you want to replace existing?",QtWidgets.QMessageBox.Yes,QtWidgets.QMessageBox.No)
                if warning == QtWidgets.QMessageBox.Yes:
                    os.remove(self.old_file)
                    shutil.move(self.asset.file, self.old_folder)
                    
        # copy new file, check if new file is inside directory or not
        if not os.path.normpath(os.path.dirname(self.file)) == os.path.normpath(self.asset.path):
            shutil.copy2(self.file, self.asset.path)

        # get date_modified, after everything done modified
        info = QtCore.QFileInfo(self.asset.path)
        date_modified = QtCore.QDateTime(info.lastModified()).toString('dd/MM/yyyy HH:mm')

        self.asset.date_modified = date_modified
        self.asset.file = self.new_file
        self.asset.eval()
        self.asset_scroll.onModified()

    def undo(self):
        pass
        # step 1: delete self.asset.file (current file)
        # step 2: recover self.old_file
        # step 3:
        # finally: assign self.asset.file and date_modified

class cmd_setAssignmentDate(QtGui.QUndoCommand):
    desc = 'set assignment date'

    def __init__(self, asset_scroll, assets, date):
        super().__init__(self.desc)
        self.asset_scroll = asset_scroll
        self.assets = assets.copy()
        self.date = date

        self.prev_assignment_dates = [asset.date_assignment for asset in self.assets]

    def redo(self):
        for asset in self.assets:
            asset.date_assignment = self.date
            asset.loadAssignment() # update to checklist class
        self.asset_scroll.onModified()
        
    def undo(self):
        for index, asset in enumerate(self.assets):
            asset.date_assignment = self.prev_assignment_dates[index]
            if asset.date_assignment == []: 
                asset.remove_asset_assignment_from_calendar()
            asset.loadAssignment() # update to checklist class
        self.asset_scroll.onModified()

class cmd_removeAssignmentDate(QtGui.QUndoCommand):
    desc = 'remove assignment date'

    def __init__(self, asset_scroll, assets):
        super().__init__(self.desc)
        self.asset_scroll = asset_scroll
        self.assets = assets.copy()

        self.prev_assignment_dates = [asset.date_assignment for asset in self.assets]

    def redo(self):
        for asset in self.assets:
            asset.date_assignment = []
            asset.remove_asset_assignment_from_calendar()
        self.asset_scroll.onModified()

    def undo(self):
        for index, asset in enumerate(self.assets):
            asset.date_assignment = self.prev_assignment_dates[index]
            asset.loadAssignment() # update to checklist class
        self.asset_scroll.onModified()

"""

⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣤⣤⣤⣀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡴⠶⠖⠋⠉⠀⠀⣀⠀⠀⠀⠀⠈⢉⠓⠲⢤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠞⠁⠀⠀⠀⠀⠀⠀⠀⠗⠀⠀⠀⠀⠀⠈⢳⠀⢷⡈⠙⠶⣤⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡴⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠑⢄⠈⠇⢨⡷⠶⢀⣀⠙⠲⣄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠀⠠⡄⠀⠈⢣⣸⡀⢀⠔⠋⠀⠀⠀⠈⢳⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⡤⠍⠓⢌⢶⣄⡀⠘⣷⠃⠀⠀⢀⠀⠀⠀⠀⠹⣄⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢚⠰⣿⡦⠀⠈⠮⣿⡭⠽⠉⡗⢶⡞⣛⣲⣦⣄⠀⠀⠹⡆⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣈⣒⠻⠇⢀⣠⠔⠛⠻⠒⢤⡄⢺⣾⠉⣼⣯⣿⡇⠀⠀⢳⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣬⡉⠉⢉⠁⣀⠔⠀⠀⠀⠀⠁⠸⡟⠢⠼⠿⠟⠀⠀⠀⠘⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠀⠀⢹⣦⣦⡀⠀⠀⠹⡀⠀⠀⠀⠀⠀⠀⠀⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣻⣩⠙⠛⠛⠶⣿⡆⠀⠀⠀⠀⠀⠀⡇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡁⠀⠉⢳⣄⠀⠀⣰⠃⠀⠀⠀⠀⠀⠀⠇
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣧⠀⠀⠀⠀⠀⠀⠐⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣷⣶⣾⡷⠼⣟⣛⣿⠁⠀⠀⠀⠀⠀⠀⢸⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡿⢛⣷⣾⣿⣷⣦⡹⡟⠀⠀⠀⠀⠀⠀⡞⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠄⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣷⣿⣯⣹⣿⣴⡇⠀⠀⠀⠀⠀⢠⠇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡏⡙⠼⠟⠫⣽⡟⢳⠏⠀⠀⠀⠀⠀⣠⠟⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠟⠷⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡴⢀⣿⡷⠯⢦⣄⡀⠀⠁⣠⠀⠀⠀⠀⣀⡜⠃⠁⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠛⢡⡀⠀⠈⠙⠶⣤⣀⠀⠀⠀⢀⡠⠞⠀⡸⠋⠀⠀⠀⠀⠉⠉⠉⠀⣧⣀⡤⠞⠉⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣠⠴⠋⠀⠀⠀⠹⣦⡀⠀⠀⠀⠉⠙⠓⠶⠿⣤⣤⣀⣁⣀⣀⣀⣀⣀⣀⣤⠴⠚⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⢀⡠⠞⠁⠀⠀⠀⠀⠀⠀⠈⠻⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣏⡁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣀⠀⡆⠀⠀
⠀⠀⠀⠀⢠⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣆⡀⠀⠀⠀⠀⠀⠀⢠⡾⠁⠀⠙⢦⣀⣆⢘⡄⢰⠀⠀⠀⠀⣠⠏⠙⠛⠁⠀
⠀⠀⠀⣰⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣦⡀⠀⣀⣀⣰⣟⣠⡤⠤⠴⠒⠛⠻⡛⠻⠧⠄⣠⠴⠊⠁⠀⠀⠀⠀⠀
⠀⣠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠉⠉⣹⠁⠀⠀⠀⠀⠀⠀⠀⠀⠈⠲⠒⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠘⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡴⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀


pure art to seperate deprecated class > https://www.messletters.com/en/text-art/memes/

⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣤⣶⣶⣿⣿⣿⡟⠒⠒⠶⠦⢤⣤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⠀⠀⠀⠈⠙⠓⠦⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣰⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠳⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢦⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⢀⣤⠀⢠⣾⠀⢠⠀⠀⠀⠀⠀⠀⠀⠀⠙⢦⡀⠀⠀⠀⠀⠀⠀
⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⣾⣿⠀⠸⣿⡄⠈⠓⠶⠖⠒⠒⠒⠀⠀⠀⠈⠻⣦⠀⠀⠀⠀⠀
⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣼⣿⣿⣶⣶⣶⣶⣶⡶⠄⠀⠀⠀⠀⠀⠘⢧⠀⠀⠀⠀
⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⢛⣿⣿⣿⡇⠀⠀⡟⠉⢸⣿⡿⢦⣤⣤⣄⠀⠀⠀⠀⠀⠀⠀⠘⣧⠀⠀⠀
⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣀⣘⣿⣿⣃⡽⠀⠀⢻⡄⢸⣯⣀⣻⣿⣿⣸⠇⠀⠀⠀⠀⠀⠀⠀⠸⡆⠀⠀
⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠻⣌⡛⠿⣿⣭⣤⡤⠖⠀⠀⡄⠀⠀⠀⠀⠀⢹⡀⠀
⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠛⠀⣤⣀⡀⠉⣿⣦⡀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠈⣧⠀
⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣾⣿⣿⣿⣶⠟⠘⣷⡀⠀⠀⠀⢠⡇⠀⠀⠀⠀⠀⠀⢸⡄
⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠏⠉⢼⣋⣿⠀⠀⠀⠀⢹⣧⠀⠀⠀⠾⠁⠀⠀⠀⠀⠀⠀⠀⡇
⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠦⠤⠤⠤⠤⠶⠶⢦⡀⠈⣿⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡇
⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡷⠖⠒⠒⠒⠒⠒⠲⣿⡇⠀⢹⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡾⠁
⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣶⣶⣶⣶⣶⡿⠟⠁⠀⠘⠋⠀⠀⠀⠀⠀⠀⠀⠀⣠⡞⠁⠀
⠀⠀⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠋⠀⠀⠀
⠀⠀⠀⠀⠹⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠀⠀⠀⠀⠀⠀⢲⡄⠀⠀⠀⠀⠀⢀⣴⠏⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⢀⣼⡇⠀⠀⠀⣠⡴⠛⠁⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣤⣤⣤⣶⠿⠋⣀⣤⣶⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣍⣉⣉⣉⣥⣴⣶⣿⣿⣿⡿⢻⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⠁⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠋⠁⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣯⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠘⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⣷⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⢹⠀⠀⠀⠀⠀⠀⠀⠀⠀

"""
###
### deprecated asset browser commands: reason > unused
###

'''
class cmd_renameStruct(QtGui.QUndoCommand):
    desc = 'rename struct'

    def __init__(self, asset, name):
        super().__init__(self.desc)
        self.asset = asset
        self.name_after = name
        self.name_before = self.asset.name

    def redo(self):
        self.rename(self.name_after)

    def undo(self):
        self.rename(self.name_before)

    def rename(self, text):
        unique_path, unique_name = self.asset.rename_active_struct(text)    # find truly unique path/name for both project and file browser
        
        self.asset.name_lbl.update_text(unique_name)
        os.rename(self.asset.path, unique_path)
        self.asset.path = unique_path
        self.asset.name = unique_name
        self.asset.asset_scroll.onModified()
'''

###
### deprecated project browser commands: reason > circular import / repetitive code / not so intuitive approach even tho it's cheap source
###

'''
class projectDetailsEditCommand(QtGui.QUndoCommand):
    desc = 'edit project details'
    
    def __init__(self, project, name, category, path, thumbnail):
        super().__init__(self.desc)
        self.project = project

        self.prev_name = self.project.name
        self.prev_category = self.project.category
        self.prev_path = self.project.path
        self.prev_thumbnail = self.project.thumbnail

        self.name = name
        self.category = category
        self.path = path
        self.thumbnail = thumbnail

    def redo(self):
        self.project.name = self.name
        self.project.category = self.category
        self.project.path = self.path
        self.project.thumbnail = self.thumbnail

    def undo(self):
        self.project.name = self.prev_name
        self.project.category = self.prev_category
        self.project.path = self.prev_path
        self.project.thumbnail = self.prev_thumbnail

class deleteProjectCommand(QtGui.QUndoCommand):
    desc = 'delete project'

    def __init__(self, project, browser, toolbar):
        super().__init__(self.desc)
        self.project = project
        self.prev_project = self.project.copy()
        self.prev_data_path = []    # get the data path before deleting, to recover later
        self.browser = browser
        self.toolbar = toolbar

    def redo(self):
        for item in self.project:
            self.prev_data_path.append(self.toolbar.get_project_path_from_object(item))
            #item.deleteLater()
            item.setParent(None)
            self.toolbar.delete_project_reference(item)

    def undo(self):
        for index,item in enumerate(self.prev_project):
            self.browser.project_container.add_item(item)
            self.toolbar.project_paths[self.prev_data_path[index]] = item
            self.toolbar.onModified()
        self.toolbar.project_sorter_changed(None)

class addProjectCommand(QtGui.QUndoCommand):
    desc = 'add new project'

    def __init__(self, browser, name, category, path, thumbnail, container, data_path):
        super().__init__(self.desc)
        self.name = name
        self.category = category
        self.path = path
        self.thumbnail = thumbnail
        self.container = container
        self.data_path = data_path
        self.item = None

    def redo(self):
        pass

    def undo(self):
        pass
'''