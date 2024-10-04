from PySide6 import QtCore, QtWidgets, QtGui

import os 

main_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')
icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'sources', 'icons')

INVALID_FILENAME_CHARACTERS = ['\\','/',':','*','?','"','<','>','|']

# # verify intergrity with file browser
# def verify_file_integrity(path):
#     if os.path.exists(path): return True
#     else: return False

# rename duplicated string with suffix '(number)'
def check_duplicate_str(text, list):
    if text in list:
        start_index = None
        if text[-1] == ')' and '(' in text and text[-2] != '(':
            for index, character in enumerate(text):
                # searching for "("
                if text[-2-index].isnumeric(): pass
                elif text[-2-index] == '(': 
                    start_index = -2-index
                    number = int(text[-1-index:-1])
                    incremented_number = number + 1
                    while text[:start_index] + '({0})'.format(incremented_number) in list:
                        incremented_number+=1
                    return text[:start_index] + '({0})'.format(incremented_number)
                else: 
                    return check_duplicate_str(text + ' (1)', list)
        else:
            return check_duplicate_str(text + ' (1)', list)
    else:
        return text

# from given path check if directory is unique, if not will generate unique directory to return (also filter out invalid character)
def filter_path_name(path, file=False):
    basename = os.path.basename(path)
    dirname = os.path.dirname(path)
    name_list = []

    # validate basename character
    for char in INVALID_FILENAME_CHARACTERS: 
        if char in basename: 
            print('FOUND')
            valid_basename = basename.replace(char, '_')    # replace invalid character with '_' like maya
            basename = valid_basename
            print (valid_basename, basename)

    if os.path.exists(os.path.join(dirname,basename)):  # using path join because we want to filter out invalid character just in case
        if file: 
            if not os.path.isfile(path): return False   # check if file or has extension
            if '.' in basename: file_ext = '.' + basename.rpartition('.')[2]    # get file ext to append at the end
            else: file_ext = ''

            for filename in os.listdir(dirname):
                if '.' in filename: name_list.append(filename.rpartition('.')[0])
                else: name_list.append(filename)
            if '.' in basename: basename = basename.rpartition('.')[0]
            unique_name = check_duplicate_str(basename, name_list)
            unique_name += file_ext    # if file, add extension
    
        else: 
            name_list = os.listdir(dirname)
            unique_name = check_duplicate_str(basename, name_list)

        return os.path.join(dirname, unique_name)
    else:
        return os.path.join(dirname,basename)   # return this version to filtered out invalid character, rather than return from given path
    
def add_filename_suffix(filename, suffix=''):
    name = filename
    ext = ''
    if '.' in filename: 
        name = filename.rpartition('.')[0] 
        ext = filename.rpartition('.')[2]
    name = name + suffix
    return name + "." + ext

# return main directory if no argument passed
def get_path(*args, icon=False):
    path = main_path
    if icon: path = icon_path
    path = os.path.join(path, *args)
    if os.path.exists(path):
        return path
    else:
        return False

# Loads an qss stylesheet to the current QApplication instance
def loadStylesheet(instance, filename):
    with open(filename, "r") as file:
        _style = file.read()
        instance.setStyleSheet(_style)

# validate image from giver directory path
def can_read_image(path):
    validator = QtGui.QImageReader(path)
    if QtGui.QImageReader.canRead(validator):
        return True
    else:
        return False
    
def validate_image_path(path, backup=get_path("image_not_found.png", icon=True)):  
    if path and can_read_image(path):
        return QtGui.QImage(path)
    else:
        try:
            return QtGui.QImage(backup)
        except Exception as e: 
            print("backup icon not found! #validate_image_path function")
            print(e)

def create_rotated_icon(image_path, angle):
    if can_read_image(image_path):
        pixmap = QtGui.QPixmap()
        image = QtGui.QImage(image_path)
        pixmap.convertFromImage(image)
        transform = QtGui.QTransform().rotate(angle)
        rotated_pixmap = pixmap.transformed(transform)
        return QtGui.QIcon(rotated_pixmap)
    
# warning messagebox
def warning_path_not_exist(parent=None, path=''):
    QtWidgets.QMessageBox.warning(parent, 
                                'Path not found!',
                                "The following path is not exists:\n\n%s"%path)
    
def warning_path_already_exist(parent=None, project='', path=''):
    QtWidgets.QMessageBox.warning(parent, 
                                'Path already existed',
                                "Can't load project: %s\n\nThe following path is already exists:\n%s"%(project, path))
    
def warning_root_path_not_exist(parent=None, path=''):
    QtWidgets.QMessageBox.warning(parent, 
                                'Project path not found!',
                                "The current project path not found: %s \n\ntry to repath with valid directory, in project menu"%path)