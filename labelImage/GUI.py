"""
This module brings everything together and handles all of the functional requirements as well as non functional requirements. The classes include the MainWindow as well as classes for multi threading.
"""

#!/usr/bin/env python
# -*- coding: utf8 -*-

import codecs
import os.path
import re
import sys
import subprocess

from textDetector.textRecognizer import TextRecognizer
from textDetector.other import draw_boxes, resize_im
from textDetector.config import Config as cfg

from detector import componentDetector as cd
from detector.helperModules import *


if '/usr/local/caffe/python' in sys.path:
    sys.path.remove('/usr/local/caffe/python')

if '/data0/mahaling/TEXT/CTPN/caffe/python' not in sys.path:
    sys.path.insert(0, '/data0/mahaling/TEXT/CTPN/caffe/python')


import caffe

from functools import partial
from collections import defaultdict

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:

    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip

        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import resources

try:
    from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut
    from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
    from libs.canvas import Canvas
    from libs.zoomWidget import ZoomWidget
    from libs.labelDialog import LabelDialog
    from libs.colorDialog import ColorDialog
    from libs.labelFile import LabelFile, LabelFileError
    from libs.toolBar import ToolBar
    from libs.pascal_voc_io import PascalVocReader
    from libs.pascal_voc_io import XML_EXT
    from libs.ustr import ustr
except ImportError:
    sys.path.insert(0, 'libs/')
    from lib import struct, newAction, newIcon, addActions, fmtShortcut
    from shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
    from canvas import Canvas
    from zoomWidget import ZoomWidget
    from labelDialog import LabelDialog
    from colorDialog import ColorDialog
    from labelFile import LabelFile, LabelFileError
    from toolBar import ToolBar
    from pascal_voc_io import PascalVocReader
    from pascal_voc_io import XML_EXT
    from ustr import ustr

__appname__ = 'PyPCB'


### Utility functions and classes.

def have_qstring():
    """
    p3/qt5 get rid of QString wrapper as py3 has native unicode str type
    """
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))


def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class WindowMixin(object):
    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        return toolbar


# PyQt5: TypeError: unhashable type: 'QListWidgetItem'
class HashableQListWidgetItem(QListWidgetItem):
    def __init__(self, *args):
        super(HashableQListWidgetItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))


class MainWindow(QMainWindow, WindowMixin):
    """
    This class handles the entire GUI.
    """
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None):
        """
        Create a main window GUI.
        :param defaultFilename: The default file to load into the GUI.
        :param defaultPrefdefClassFile: The name of the file with the class names to load into the label dialog 
                    by default.
        """
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)
        # Save as Pascal voc xml
        self.defaultSaveDir = None
        self.usingPascalVocFormat = True
        # For loading all image under a directory
        self.mImgList = []
        self.dirname = None
        self.labelHist = []
        self.lastOpenDir = None

        # Whether we need to save or not.
        self.dirty = False

        # Enble auto saving if pressing next
        self._noSelectionSlot = False
        self._beginner = True
        self.storedToggleLabel = None

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)

        self.itemsToShapes = {}
        self.shapesToItems = {}
        self.prevLabelText = ''

        listLayout = QVBoxLayout()
        listLayout.setContentsMargins(0, 0, 0, 0)

        # Create a widget for using default label
        self.useDefaultLabelCheckbox = QCheckBox(u'Use default label')
        self.useDefaultLabelCheckbox.setChecked(False)
        self.defaultLabelTextLine = QLineEdit()
        useDefaultLabelQHBoxLayout = QHBoxLayout()
        useDefaultLabelQHBoxLayout.addWidget(self.useDefaultLabelCheckbox)
        useDefaultLabelQHBoxLayout.addWidget(self.defaultLabelTextLine)
        useDefaultLabelContainer = QWidget()
        useDefaultLabelContainer.setLayout(useDefaultLabelQHBoxLayout)

        # Create a widget for edit and diffc button
        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Add some of widgets to listLayout
        listLayout.addWidget(self.editButton)
        listLayout.addWidget(useDefaultLabelContainer)

        # Create and add a widget for showing current label items
        self.labelList = QListWidget()
        labelListContainer = QWidget()
        labelListContainer.setLayout(listLayout)
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        # Connect to itemChanged to detect checkbox changes.
        self.labelList.itemChanged.connect(self.labelItemChanged)
        listLayout.addWidget(self.labelList)

        self.dock = QDockWidget(u'Box Labels', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(labelListContainer)

        self.fileListWidget = QListWidget()
        self.fileListWidget.itemDoubleClicked.connect(self.fileitemDoubleClicked)
        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)
        filelistLayout.addWidget(self.fileListWidget)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)
        self.filedock = QDockWidget(u'File List', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(fileListContainer)

        self.zoomWidget = ZoomWidget()
        self.colorDialog = ColorDialog(parent=self)

        self.canvas = Canvas()
        self.canvas.zoomRequest.connect(self.zoomRequest)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll
        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)

        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.filedock)
        self.dockFeatures = QDockWidget.DockWidgetClosable \
                            | QDockWidget.DockWidgetFloatable
        self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)

        # Actions
        action = partial(newAction, self)
        quit = action('&Quit', self.close,
                      'Ctrl+Q', 'quit', u'Quit application')

        open = action('&Open', self.openFile,
                      'Ctrl+O', 'open', u'Open image or label file')

        opendir = action('&Open Dir', self.openDir,
                         'Ctrl+u', 'open', u'Open Dir')

        changeSavedir = action('&Change Default Save Annotation Dir', self.changeSavedir,
                               'Ctrl+r', 'open', u'Change Default Saved Annotation Dir')

        openAnnotation = action('&Open Annotation', self.openAnnotation,
                                'Ctrl+A', 'open', u'Open Annotation')

        openNextImg = action('&Next Image', self.openNextImg,
                             'd', 'next', u'Open Next')

        openPrevImg = action('&Prev Image', self.openPrevImg,
                             'a', 'prev', u'Open Prev')

        save = action('&Save', self.saveFile,
                      'Ctrl+S', 'save', u'Save labels to file', enabled=False)
        saveAs = action('&Save As', self.saveFileAs,
                        'Ctrl+Shift+S', 'save-as', u'Save labels to a different file',
                        enabled=False)
        exportAsXML = action('&Export as XML', self.exportAsXML,
                             'Ctrl+Shift+T', 'labels', u'Save labels as a XML file',
                             enabled=False)
        close = action('&Close', self.closeFile,
                       'Ctrl+W', 'close', u'Close current file')
        color1 = action('Box &Line Color', self.chooseColor1,
                        'Ctrl+L', 'color_line', u'Choose Box line color')
        color2 = action('Box &Fill Color', self.chooseColor2,
                        'Ctrl+Shift+L', 'color', u'Choose Box fill color')

        predictions = action('Component\nPredictions', self.getComponentPredictions,
                             'Ctrl+M', 'component', u'Get component predictions')

        createMode = action('Create\nMode', self.setCreateMode,
                            'Ctrl+N', 'new', u'Start drawing Boxes', enabled=False)
        editMode = action('&Edit\nMode', self.setEditMode,
                          'Ctrl+J', 'edit', u'Move and edit Boxes', enabled=False)

        create = action('Create\nRectBox', self.createShape,
                        'w', 'new', u'Draw a new Box', enabled=False)
        delete = action('Delete\nRectBox', self.deleteSelectedShape,
                        'Delete', 'delete', u'Delete', enabled=False)
        copy = action('&Duplicate\nRectBox', self.copySelectedShape,
                      'Ctrl+D', 'copy', u'Create a duplicate of the selected Box',
                      enabled=False)

        advancedMode = action('&Advanced Mode', self.toggleAdvancedMode,
                              'Ctrl+Shift+A', 'expert', u'Switch to advanced mode',
                              checkable=True)

        hideAll = action('&Hide\nRectBox', partial(self.togglePolygons, False),
                         'Ctrl+H', 'hide', u'Hide all Boxes',
                         enabled=False)
        showAll = action('&Show\nRectBox', partial(self.togglePolygons, True),
                         'Ctrl+I', 'hide', u'Show all Boxes',
                         enabled=False)

        help = action('&Tutorial', self.tutorial, 'Ctrl+T', 'help',
                      u'Show demos')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with" \
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('Zoom &In', partial(self.addZoom, 10),
                        'Ctrl++', 'zoom-in', u'Increase zoom level', enabled=False)
        zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'Zoom to original size', enabled=False)
        fitWindow = action('&Fit Window', self.setFitWindow,
                           'Ctrl+F', 'fit-window', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'Zoom follows window width',
                          checkable=True, enabled=False)
        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut, zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&Edit Label', self.editLabel,
                      'Ctrl+E', 'edit', u'Modify the label of the selected Box',
                      enabled=False)
        self.editButton.setDefaultAction(edit)

        shapeLineColor = action('Shape &Line Color', self.chshapeLineColor,
                                icon='color_line', tip=u'Change the line color for this specific shape',
                                enabled=False)
        shapeFillColor = action('Shape &Fill Color', self.chshapeFillColor,
                                icon='color', tip=u'Change the fill color for this specific shape',
                                enabled=False)

        labels = self.dock.toggleViewAction()
        labels.setText('Show/Hide Label Panel')
        labels.setShortcut('Ctrl+Shift+L')

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(self.popLabelListMenu)

        # Store actions for further handling.
        self.actions = struct(save=save, saveAs=saveAs, exportAsXML=exportAsXML, open=open, close=close,
                              lineColor=color1, fillColor=color2,
                              create=create, predictions=predictions, delete=delete, edit=edit, copy=copy,
                              createMode=createMode, editMode=editMode, advancedMode=advancedMode,
                              shapeLineColor=shapeLineColor, shapeFillColor=shapeFillColor,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  open, opendir, save, saveAs, exportAsXML, close, quit),
                              beginner=(), advanced=(),
                              editMenu=(edit, copy, delete, None, color1, color2),
                              beginnerContext=(create, edit, copy, delete),
                              advancedContext=(createMode, editMode, edit, copy,
                                               delete, shapeLineColor, shapeFillColor),
                              onLoadActive=(close, create, createMode, editMode),
                              onShapesPresent=(saveAs, hideAll, showAll))

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentFiles=QMenu('Open &Recent'),
            labelList=labelMenu)

        # Auto saving : Enble auto saving if pressing next
        self.autoSaving = QAction("Auto Saving", self)
        self.autoSaving.setCheckable(True)

        addActions(self.menus.file,
                   (open, opendir, changeSavedir, openAnnotation, self.menus.recentFiles, None, predictions, None, save,
                    saveAs, exportAsXML, close, None, quit))
        addActions(self.menus.help, (help,))
        addActions(self.menus.view, (
            self.autoSaving,
            labels, advancedMode, None,
            hideAll, showAll, None,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (
            open, opendir, openPrevImg, openNextImg, save, None, predictions, None, create, copy, delete, None,
            zoomIn, zoomOut, fitWindow, fitWidth, zoom)

        self.actions.advanced = (
            open, save, None, predictions, None,
            openPrevImg, openNextImg, None,
            createMode, editMode, None,
            hideAll, showAll)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.zoom_level = 100
        self.fit_window = False

        # Load predefined classes to the lits
        self.loadPredefinedClasses(defaultPrefdefClassFile)

        # XXX: Could be completely declarative.
        # Restore application settings.
        if have_qstring():
            types = {
                'filename': QString,
                'recentFiles': QStringList,
                'window/size': QSize,
                'window/position': QPoint,
                'window/geometry': QByteArray,
                'line/color': QColor,
                'fill/color': QColor,
                'advanced': bool,
                # Docks and toolbars:
                'window/state': QByteArray,
                'savedir': QString,
                'lastOpenDir': QString,
            }
        else:
            types = {
                'filename': str,
                'recentFiles': list,
                'window/size': QSize,
                'window/position': QPoint,
                'window/geometry': QByteArray,
                'line/color': QColor,
                'fill/color': QColor,
                'advanced': bool,
                # Docks and toolbars:
                'window/state': QByteArray,
                'savedir': str,
                'lastOpenDir': str,
            }

        self.settings = settings = Settings(types)

        if settings.get('recentFiles'):
            if have_qstring():
                recentFileQStringList = settings.get('recentFiles')
                self.recentFiles = [ustr(i) for i in recentFileQStringList]
            else:
                self.recentFiles = recentFileQStringList = settings.get('recentFiles')

        size = settings.get('window/size', QSize(600, 500))
        position = settings.get('window/position', QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = ustr(settings.get('savedir', None))
        self.lastOpenDir = ustr(settings.get('lastOpenDir', None))
        if saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage(
                '%s started. Annotation will be saved to %s' % (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        # or simply:
        # self.restoreGeometry(settings['window/geometry']
        self.restoreState(settings.get('window/state', QByteArray()))
        self.lineColor = QColor(settings.get('line/color', Shape.line_color))
        self.fillColor = QColor(settings.get('fill/color', Shape.fill_color))
        Shape.line_color = self.lineColor
        Shape.fill_color = self.fillColor

        def xbool(x):
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        if xbool(settings.get('advanced', False)):
            self.actions.advancedMode.setChecked(True)
            self.toggleAdvancedMode()

        # Populate the File menu dynamically.
        self.updateFileMenu()
        # Since loading the file may take some time, make sure it runs in the background.
        self.queueEvent(partial(self.loadFile, self.filePath or ""))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

    ## Support Functions ##

    def noShapes(self):
        """
        :return: True if there are no shapes currently drawn. False otherwise. 
        """
        return not self.itemsToShapes

    def toggleAdvancedMode(self, value=True):
        """
        Toggle advanced mode so that users can draw multiple boxes without having to interact with the label dialog box each time. In advanced mode, the user selects the label and then can draw multiple boxes with that label.
        :param value: The boolean value that tells whether to set advanced mode or not.
        """
        self._beginner = not value
        self.canvas.setEditing(True)
        self.populateModeActions()
        self.editButton.setVisible(not value)
        if value:
            if self.image.isNull():
                self.actions.createMode.setEnabled(False)
            self.actions.editMode.setEnabled(False)
            self.dock.setFeatures(self.dock.features() | self.dockFeatures)
        else:
            self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)

    def populateModeActions(self):
        """
        Changes the tool bar and based on whether the tool is in advanced mode or beginner mode.
        """
        if self.beginner():
            tool, menu = self.actions.beginner, self.actions.beginnerContext
        else:
            tool, menu = self.actions.advanced, self.actions.advancedContext
        self.tools.clear()
        addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create,) if self.beginner() \
            else (self.actions.createMode, self.actions.editMode)
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def setBeginner(self):
        """
        Change the tool bar so that the beginner mode buttons are displayed.
        """
        self.tools.clear()
        addActions(self.tools, self.actions.beginner)

    def setAdvanced(self):
        """
        Change the tool bar so that the advanced mode buttons are displayed.
        """
        self.tools.clear()
        addActions(self.tools, self.actions.advanced)

    def setDirty(self):
        """
        Set dirty mode to true. Dirty means that there are boxes drawn that are not currently saved.
        """
        self.dirty = True
        self.actions.save.setEnabled(True)
        self.actions.exportAsXML.setEnabled(True)

    def setClean(self):
        """
        Set dirty mode to false. Clean means that every drawn box is saved in a file.
        """
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)

    def toggleActions(self, value=True):
        """
        Enable/Disable widgets which depend on an opened image.
        """
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        """
        Display a given message on the status bar.
        :param message: The message to display on the status bar.
        :param delay: The amount of time (in ms) to wait before displaying the message.
        """
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        """
        Reset everything about the stored GUI information, including the annotation boxes, image, and save files.
        """
        self.itemsToShapes.clear()
        self.shapesToItems.clear()
        self.labelList.clear()
        self.filePath = None
        self.imageData = None
        self.labelFile = None
        self.canvas.resetState()

    def currentItem(self):
        """
        :return: The currently selected label. 
        """
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filePath):
        """
        Add a file to the recent file list after it is opened.
        :param filePath: The path to the file that was just opened.
        """
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def beginner(self):
        """
        :return: True if the GUI is in beginner mode. False otherwise. 
        """
        return self._beginner

    def advanced(self):
        """
        :return: True if the GUI is in advanced mode. False otherwise. 
        """
        return not self.beginner()

    ## Callbacks ##
    def tutorial(self):
        """
        This is called whenever the user clicks on help. Not yet implemented, as no tutorial doc exists yet.
        """
        # Todo: add in html page with instructions for use
        pass

    def createShape(self):
        """
        Create a shape on the canvas.
        """
        assert self.beginner()
        self.canvas.setEditing(False)
        self.actions.create.setEnabled(False)

    def toggleDrawingSensitive(self, drawing=True):
        """
        In the middle of drawing, toggling between modes should be disabled.
        """
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            print('Cancel creation.')
            self.canvas.setEditing(True)
            self.canvas.restoreCursor()
            self.actions.create.setEnabled(True)

    def toggleDrawMode(self, edit=True):
        """
        This is a helper function for setCreateMode and setEditMode. It toggles beginner/advanced mode.
        :param edit: bool value that tells whether edit mode is enabled or not.
        """
        self.canvas.setEditing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def setCreateMode(self):
        """
        Set create mode while the user is in advanced mode. This happens when the user clicks the create mode button.
        """
        assert self.advanced()
        if self.storedToggleLabel is None:
            self.storedToggleLabel = self.labelDialog.popUp()
        self.toggleDrawMode(False)

    def setEditMode(self):
        """
        Set edit mode while the user is in the edit mode. This happens when the user clicks the edit mode button.
        :return: 
        """
        assert self.advanced()
        self.storedToggleLabel = None
        self.toggleDrawMode(True)

    def updateFileMenu(self):
        """
        Update the file menu whenever the user opens a new image. Add the file to the recently opened list.
        """
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)

        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f != currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = newIcon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        """
        Populate the label list menu.
        """
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def editLabel(self, item=None):
        """
        This occurs when the user clicks edit label on a particular bounding box.
        :param item: The item that the user is editing the label for.
        """
        if not self.canvas.editing():
            return
        item = item if item else self.currentItem()
        text = self.labelDialog.popUp(item.text())
        if text is not None:
            item.setText(text)
            self.setDirty()

    def fileitemDoubleClicked(self, item=None):
        """
        This event is triggered whenever the user double clicks on an image in the image list.
        :param item: The item that the user clicked on.
        """
        currIndex = self.mImgList.index(ustr(item.text()))
        if currIndex < len(self.mImgList):
            filename = self.mImgList[currIndex]
            if filename:
                self.loadFile(filename)

    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        """
        This event is triggered when the user clicks on a new shape. 
        :param selected: boolean value that tells whether a shape is selected.
        """
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape:
                self.shapesToItems[shape].setSelected(True)
            else:
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)

    def addLabel(self, shape):
        """
        Add a label (corresponding to the recently drawn shape) to the label list.
        :param shape: The shape that corresponds to the label.
        """
        item = HashableQListWidgetItem(shape.label)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item
        self.labelList.addItem(item)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

    def remLabel(self, shape):
        """
        Remove a label and delete the shape.
        :param shape: The shape to delete and remove the label for.
        """
        if shape is None:
            return
        item = self.shapesToItems[shape]
        self.labelList.takeItem(self.labelList.row(item))
        del self.shapesToItems[shape]
        del self.itemsToShapes[item]

    def loadLabels(self, shapes):
        """
        Load labels based on the shapes that are given.
        :param shapes: The shapes to load the labels for.
        """
        s = []
        for label, points, line_color, fill_color in shapes:
            shape = Shape(label=label)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.close()
            s.append(shape)
            self.addLabel(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            if fill_color:
                shape.fill_color = QColor(*fill_color)

        self.canvas.loadShapes(s)

    def saveLabels(self, annotationFilePath):
        """
        Save the labels in the file path currently specified. This is for XML files.
        :param annotationFilePath: The path to save the file to.
        """
        annotationFilePath = ustr(annotationFilePath)
        if self.labelFile is None:
            self.labelFile = LabelFile()

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb() if s.line_color != self.lineColor else None,
                        fill_color=s.fill_color.getRgb() if s.fill_color != self.fillColor else None,
                        points=[(p.x(), p.y()) for p in s.points])

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # Can add differrent annotation formats here
        try:
            if self.usingPascalVocFormat is True:
                print ('Img: ' + self.filePath + ' -> Its xml: ' + annotationFilePath)
                self.labelFile.savePascalVocFormat(annotationFilePath, shapes, self.filePath, self.imageData,
                                                   self.lineColor.getRgb(), self.fillColor.getRgb())
            else:
                self.labelFile.save(annotationFilePath, shapes, self.filePath, self.imageData,
                                    self.lineColor.getRgb(), self.fillColor.getRgb())
                # self.filePath = annotationFilePath
            return True
        except LabelFileError as e:
            self.errorMessage(u'Error saving label data',
                              u'<b>%s</b>' % e)
            return False

    def copySelectedShape(self):
        """
        Copy the currently selected shape and display it offset from the original by a few pixels.
        """
        self.addLabel(self.canvas.copySelectedShape())
        # fix copy and delete
        self.shapeSelectionChanged(True)

    def labelSelectionChanged(self):
        """
        This event triggers whenever the user selects a new label in the label list.
        """
        item = self.currentItem()
        if item and self.canvas.editing():
            self._noSelectionSlot = True
            self.canvas.selectShape(self.itemsToShapes[item])

    def labelItemChanged(self, item):
        """
        This event is triggered whenever the user changes the label associated with a shape.
        :param item: The item in the label list.
        """
        shape = self.itemsToShapes[item]
        label = item.text()
        if label != shape.label:
            shape.label = item.text()
            self.setDirty()
        else:  # User probably changed item visibility
            self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    ## Callback functions:
    def newShape(self):
        """
        Pop-up and give focus to the label editor.

        Position MUST be in global coordinates.
        """
        if not self.useDefaultLabelCheckbox.isChecked() or not self.defaultLabelTextLine.text():
            if len(self.labelHist) > 0:
                self.labelDialog = LabelDialog(parent=self, listItem=self.labelHist)

        if self.advanced():
            text = self.storedToggleLabel
        else:
            text = self.labelDialog.popUp()

        if text is not None:
            self.prevLabelText = text
            self.addLabel(self.canvas.setLastLabel(text))
            if self.beginner():  # Switch to edit mode.
                self.canvas.setEditing(True)
                self.actions.create.setEnabled(True)
                self.actions.createMode.setEnabled(True)
            else:
                self.actions.editMode.setEnabled(True)
            self.setDirty()

            if text not in self.labelHist:
                self.labelHist.append(text)
        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

    def scrollRequest(self, delta, orientation):
        """
        This handles the scroll bar.
        """
        units = - delta / (8 * 15)
        bar = self.scrollBars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def setZoom(self, value):
        """
        Set the zoom of the image to the given value.
        :param value: The amount of zoom.
        """
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        """
        Zoom in.
        :param increment: how much to zoom in.
        """
        self.setZoom(self.zoomWidget.value() + increment)

    def zoomRequest(self, delta):
        """
        This event is called whenever the user zooms in/out.
        """
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()

        cursor_x = pos.x()
        cursor_y = pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values form 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        """
        This event is called whenever the user select 'fit to window'
        :param value: Whether 'fit to window' is selected or not.
        """
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        """
        Set the image to fit horizontally inside of the canvas.
        :param value: Whether the image is fit horizontally or not.
        """
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def togglePolygons(self, value):
        """
        Toggle all of the polygons to visible/invisible based on the value.
        :param value: Whether the shapes are shown or not.
        :return: 
        """
        for item, shape in self.itemsToShapes.items():
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def loadFile(self, filePath=None):
        """
        Load the specified image. Also load the annotations if the default annotation dir is specified.
        :param filePath: The path to the image.
        :return: True if load is successful. False otherwise.
        """
        self.resetState()
        self.canvas.setEnabled(False)
        if filePath is None:
            filePath = self.settings.get('filename')
        unicodeFilePath = ustr(filePath)
        # Highlight the file item
        if unicodeFilePath and self.fileListWidget.count() > 0:
            index = self.mImgList.index(unicodeFilePath)
            fileWidgetItem = self.fileListWidget.item(index)
            fileWidgetItem.setSelected(True)

        if unicodeFilePath and os.path.exists(unicodeFilePath):
            if LabelFile.isLabelFile(unicodeFilePath):
                try:
                    self.labelFile = LabelFile(unicodeFilePath)
                except LabelFileError as e:
                    self.errorMessage(u'Error opening file',
                                      (u"<p><b>%s</b></p>"
                                       u"<p>Make sure <i>%s</i> is a valid label file.") \
                                      % (e, unicodeFilePath))
                    self.status("Error reading %s" % unicodeFilePath)
                    return False
                self.imageData = self.labelFile.imageData
                self.lineColor = QColor(*self.labelFile.lineColor)
                self.fillColor = QColor(*self.labelFile.fillColor)
            else:
                # Load image:
                # read data first and store for saving into label file.
                self.imageData = read(unicodeFilePath, None)
                self.labelFile = None
            image = QImage.fromData(self.imageData)
            if image.isNull():
                self.errorMessage(u'Error opening file',
                                  u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
                self.status("Error reading %s" % unicodeFilePath)
                return False
            self.status("Loaded %s" % os.path.basename(unicodeFilePath))
            self.image = image
            self.filePath = unicodeFilePath
            self.canvas.loadPixmap(QPixmap.fromImage(image))
            if self.labelFile:
                self.loadLabels(self.labelFile.shapes)
            self.setClean()
            self.canvas.setEnabled(True)
            self.adjustScale(initial=True)
            self.paintCanvas()
            self.addRecentFile(self.filePath)
            self.toggleActions(True)

            ## Label xml file and show bound box according to its filename
            if self.usingPascalVocFormat is True and \
                            self.defaultSaveDir is not None:
                basename = os.path.basename(os.path.splitext(self.filePath)[0])
                xmlPath = os.path.join(self.defaultSaveDir, basename + XML_EXT)
                txtPath = os.path.join(self.defaultSaveDir, basename + '.txt')

                # If both a txt and xml file with the same name exist, prioritize the xml file
                if os.path.exists(xmlPath):
                    self.loadPascalXMLByFilename(xmlPath)
                elif os.path.exists(txtPath):
                    self.loadTXTByFilename(txtPath)

            self.setWindowTitle(__appname__ + ' ' + filePath)

            # Default : select last item if there is at least one item
            if self.labelList.count():
                self.labelList.setCurrentItem(self.labelList.item(self.labelList.count() - 1))
                self.labelList.item(self.labelList.count() - 1).setSelected(True)

            self.canvas.setFocus(True)

            return True
        return False

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull() \
                and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """
        Figure out the size of the pixmap in order to fit the main widget.
        """
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        """
        This is called whenever the user clicks the close button. The image is closed and all of the annotations are reset.
        :param event: The close event (button click). 
        """
        if not self.mayContinue():
            event.ignore()
        s = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            s['filename'] = self.filePath if self.filePath else ''
        else:
            s['filename'] = ''

        s['window/size'] = self.size()
        s['window/position'] = self.pos()
        s['window/state'] = self.saveState()
        s['line/color'] = self.lineColor
        s['fill/color'] = self.fillColor
        s['recentFiles'] = self.recentFiles
        s['advanced'] = not self._beginner
        if self.defaultSaveDir is not None and len(self.defaultSaveDir) > 1:
            s['savedir'] = ustr(self.defaultSaveDir)
        else:
            s['savedir'] = ""

        if self.lastOpenDir is not None and len(self.lastOpenDir) > 1:
            s['lastOpenDir'] = str(self.lastOpenDir)
        else:
            s['lastOpenDir'] = ""

    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def scanAllImages(self, folderPath):
        """
        Scan all of the images in the given directory path and sort them (ignore case).
        :param folderPath: The directory to load the images from.
        :return: A list of the images paths.
        """
        extensions = {'.jpeg', '.jpg', '.png', '.bmp'}
        images = []

        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.join(root, file)
                    path = ustr(os.path.abspath(relativePath))
                    images.append(path)
        images.sort(key=lambda x: x.lower())
        return images

    def changeSavedir(self, _value=False):
        """
        Change default save directory. The default save directory is where annotations for all loaded images (via open dir) will be saved.
        :param _value: Whether there is a default save directory given or not.
        """
        if self.defaultSaveDir is not None:
            path = ustr(self.defaultSaveDir)
        else:
            path = '.'

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                        '%s - Save to the directory' % __appname__, path,
                                                        QFileDialog.ShowDirsOnly
                                                        | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:
            self.defaultSaveDir = dirpath

        self.statusBar().showMessage(
            '%s . Annotation will be saved to %s' % ('Change saved folder', self.defaultSaveDir))
        self.statusBar().show()

    def openAnnotation(self, _value=False):
        """
        Open the annotation file. This method display a dialog box and asks the user to select a txt or xml file.
        The method will then call the appropriate loadTXT or loadXML method based on the user's selection.
        :param _value: Whether an annotation is loaded or not.
        """
        if self.image.isNull():
            self.errorMessage(u'No image open',
                              u'Open an image before loading the annotations.')

        if self.filePath is None:
            return

        path = os.path.dirname(ustr(self.filePath)) \
            if self.filePath else '.'

        if self.usingPascalVocFormat:
            filters = "Open Annotation XML or TXT file (%s)" % ' '.join(['*.xml'] + ['*.txt'])
            filename = QFileDialog.getOpenFileName(self, '%s - Choose a xml or txt file' % __appname__, path, filters)
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            if filename:
                self.labelList.clear()

                # Edit for face aging group input. If file ends with .txt,
                # assume it is of the form: class \t x(top left corner) \t y \t width \t height \t
                # where class= 1-ic; 2-capacitor; 3-resistor; 4-inductor; 5-sscapacitor
                if isinstance(filename, str) and filename.endswith('.txt'):
                    self.loadTXTByFilename(filename)
                elif isinstance(filename, QString) and filename.endsWith('.txt'):
                    self.loadTXTByFilename(filename)
                else:
                    self.loadPascalXMLByFilename(filename)

    def openDir(self, _value=False):
        """
        Open all images in a specified directory.
        :param _value: Whether a directory is opened or not.
        """
        if not self.mayContinue():
            return

        path = os.path.dirname(self.filePath) \
            if self.filePath else '.'

        if self.lastOpenDir is not None and len(self.lastOpenDir) > 1:
            path = self.lastOpenDir

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                        '%s - Open Directory' % __appname__, path,
                                                        QFileDialog.ShowDirsOnly
                                                        | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:
            self.lastOpenDir = dirpath

            '''
            self.itemsToShapes.clear()
            self.shapesToItems.clear()
            self.labelList.clear()
            self.filePath = None
            self.imageData = None
            self.labelFile = None
            '''

            self.dirname = dirpath
            self.filePath = None
            self.fileListWidget.clear()
            self.mImgList = self.scanAllImages(dirpath)
            # self.openNextImg()

            self.loadFile(self.mImgList[0])

            for imgPath in self.mImgList:
                item = QListWidgetItem(imgPath)
                self.fileListWidget.addItem(item)

    def openPrevImg(self, _value=False):
        """
        Open previous image if there is a directory of images open.
        """
        if self.autoSaving.isChecked() and self.defaultSaveDir is not None:
            if self.dirty is True and self.hasLabels():
                self.saveFile()

        if not self.mayContinue():
            return

        if len(self.mImgList) <= 0:
            return

        if self.filePath is None:
            return

        currIndex = self.mImgList.index(self.filePath)
        if currIndex - 1 >= 0:
            filename = self.mImgList[currIndex - 1]
            if filename:
                self.loadFile(filename)

    def openNextImg(self, _value=False):
        """
        Open the next image in the image list if there is a directory of images open.
        """
        if self.autoSaving.isChecked() and self.defaultSaveDir is not None:
            if self.dirty is True and self.hasLabels():
                self.saveFile()

        if not self.mayContinue():
            return

        if len(self.mImgList) <= 0:
            return

        filename = None
        if self.filePath is None:
            filename = self.mImgList[0]
        else:
            currIndex = self.mImgList.index(self.filePath)
            if currIndex + 1 < len(self.mImgList):
                filename = self.mImgList[currIndex + 1]
                # else:
                #    return

        if filename:
            self.loadFile(filename)

    def openFile(self, _value=False):
        """
        This method displays a dialog box that prompts the user to select an image. Then it calls the loadFile method
            with the given image as a parameter.
        """
        if not self.mayContinue():
            return
        path = os.path.dirname(ustr(self.filePath)) if self.filePath else '.'
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image files (%s)" % \
                  ' '.join(formats)
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image' % __appname__, path, filters)
        if isinstance(filename, (tuple, list)):
            filename = filename[0]
        if filename:
            self.loadFile(filename)
            if self.advanced():
                self.actions.createMode.setEnabled(True)
                self.actions.editMode.setEnabled(False)

    def exportAsXML(self, _value=False):
        """
        Export the annotations as a xml file.
        """
        assert not self.image.isNull(), "cannot save empty image"
        if self.defaultSaveDir is not None and len(ustr(self.defaultSaveDir)):
            if self.defaultSaveDir is not None and len(ustr(self.defaultSaveDir)):
                print ('handle the image:' + self.filePath)
                imgFileName = os.path.basename(self.filePath)
                savedFileName = os.path.splitext(imgFileName)[0] + XML_EXT
                savedPath = os.path.join(ustr(self.defaultSaveDir), savedFileName)
                self._exportAsXML(savedPath)
        else:
            imgFileDir = os.path.dirname(self.filePath)
            imgFileName = os.path.basename(self.filePath)
            savedFileName = os.path.splitext(imgFileName)[0] + XML_EXT
            savedPath = os.path.join(imgFileDir, savedFileName)
            self._exportAsXML(savedPath if self.labelFile
                              else self.exportXMLDialog())


    def saveFile(self):
        """
        Method to export annotations to a text file of the form:
        class x(top left corner) y width height
        where class= 1-ic; 2-capacitor; 3-resistor; 4-inductor; 5-sscapactitor
        """
        assert not self.image.isNull(), "cannot save empty image"
        if self.defaultSaveDir is not None and len(ustr(self.defaultSaveDir)):
            if self.filePath:
                imgFileName = os.path.basename(self.filePath)
                savedFileName = os.path.splitext(imgFileName)[0] + '.txt'
                savedPath = os.path.join(ustr(self.defaultSaveDir), savedFileName)
                self._saveFile(savedPath)

        else:
            imgFileDir = os.path.dirname(os.path.abspath(self.filePath))
            imgFileName = os.path.basename(self.filePath)
            savedFileName = os.path.splitext(imgFileName)[0] + '.txt'
            savedPath = os.path.join(imgFileDir, savedFileName)
            self._saveFile(savedPath if self.labelFile
                           else self.saveFileDialog())

    def _saveFile(self, annotationFilePath):
        """
        Helper function for save. Opens the file and writes annotations to file in format: 
        class x(top left corner) y width height
        where class= 1-ic; 2-capacitor; 3-resistor; 4-inductor; 5-sscapactitor
        :param annotationFilePath: The file path to the 
        :return: 
        """
        f = open(annotationFilePath, 'w')
        componentCode = 0  # 1=ic, 2=cap, 3=resistor, 4=inductor, 5=solid state cap

        def format_shape(s):
            return dict(label=s.label,
                        points=[(p.x(), p.y()) for p in s.points])

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        for i in range(len(shapes)):
            componentCode = shapes[i]['label']

            # Add handling for component code here

            xMin = 9999
            yMin = 9999
            xMax = -9999
            yMax = -9999
            for vertices in range(len(shapes[i]['points'])):
                x = shapes[i]['points'][vertices][0]
                y = shapes[i]['points'][vertices][1]
                if x < xMin:
                    xMin = x
                if y < yMin:
                    yMin = y
                if x > xMax:
                    xMax = x
                if y > yMax:
                    yMax = y

            f.write(str(componentCode) + '\t' + str(round(xMin, 1)) + '\t' + str(round(yMin, 1)) + '\t' +
                    str(round(xMax - xMin, 1)) + '\t' + str(round(yMax - yMin, 1)) + '\n')

            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()

        f.close()

    # Method added by Kevin Gay for the Face Aging Group
    def saveFileDialog(self):
        """
        Open the file dialog to save text files. The user selects the location to save the file.
        :return: 
        """
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % '.txt'
        openDialogPath = self.currentPath()
        dlg = QFileDialog(self, caption, openDialogPath, filters)
        dlg.setDefaultSuffix('txt')
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            return dlg.selectedFiles()[0]
        return ''

    def saveFileAs(self, _value=False):
        """
        Save the file regardless of whether the image is dirty or clean.
        :param _value: 
        :return: 
        """
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def exportXMLDialog(self):
        """
        Opens up a file dialog for the user to select where to save the XML file.
        """
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        openDialogPath = self.currentPath()
        dlg = QFileDialog(self, caption, openDialogPath, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filenameWithoutExtension = os.path.splitext(self.filePath)[0]
        dlg.selectFile(filenameWithoutExtension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            return dlg.selectedFiles()[0]
        return ''

    def _exportAsXML(self, annotationFilePath):
        """
        Helper functions for exporting as xml.
        :param annotationFilePath: The path to save the xml file to.
        """
        if annotationFilePath and self.saveLabels(annotationFilePath):
            self.setClean()
            self.statusBar().showMessage('Saved to  %s' % annotationFilePath)
            self.statusBar().show()

    def closeFile(self, _value=False):
        """
        Called whenever the image is closed.
        """
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    # Message Dialogs. #
    def hasLabels(self):
        """
        :return: True if the image has labels. False otherwise. 
        """
        if not self.itemsToShapes and self.dirty:
            self.errorMessage(u'No objects labeled',
                              u'You must label at least one object to save the file.')
            return False
        return True

    def mayContinue(self):
        """
        Return true if there are no unsaved boxes on the image.
        """
        return not (self.dirty and not self.discardChangesDialog())

    def discardChangesDialog(self):
        """
        Display a dialog to the user to ensure that they actually want to proceed without saving.
        """
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You have unsaved changes, proceed anyway?'
        return yes == QMessageBox.warning(self, u'Attention', msg, yes | no)

    def errorMessage(self, title, message):
        """
        Display an error message pop up box.
        :param title: The string to display on the title bar of the dialog box.
        :param message: The message to display in the dialog box.
        :return: The dialog box.
        """
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        """
        :return:  The currently open path if one is opened. Otherwise return the location of the program. 
        """
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def chooseColor1(self):
        """
        Open a color dialog and set the line color to the selected color.
        """
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.lineColor = color
            # Change the color for all shape lines:
            Shape.line_color = self.lineColor
            self.canvas.update()
            self.setDirty()

    def chooseColor2(self):
        """
        Open a color dialog and set the fill color to the selected color.
        """
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.fillColor = color
            Shape.fill_color = self.fillColor
            self.canvas.update()
            self.setDirty()

    def deleteSelectedShape(self):
        """
        Delete the currently selected shape. Display a confirmation dialog to ensure the user meant to hit delete.
        """
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You are about to permanently delete this Box, proceed anyway?'
        if yes == QMessageBox.warning(self, u'Attention', msg, yes | no):
            self.remLabel(self.canvas.deleteSelected())
            self.setDirty()
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)

    def chshapeLineColor(self):
        """
        Open a color dialog and set the line color to the selected color.
        """
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selectedShape.line_color = color
            self.canvas.update()
            self.setDirty()

    def chshapeFillColor(self):
        """
        Open a color dialog and set the fill color to the selected color.
        """
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selectedShape.fill_color = color
            self.canvas.update()
            self.setDirty()

    def copyShape(self):
        """
        Copy the currently selected shape.
        """
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        """
        Move the currently selected shape.
        """
        self.canvas.endMove(copy=False)
        self.setDirty()

    def loadPredefinedClasses(self, predefClassesFile):
        """
        Load the contents of the text file into the label selection dialog box as labels to select.
        :param predefClassesFile: The path to the file to load the labels from.
        """
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.lablHist = [line]
                    else:
                        self.labelHist.append(line)


    def loadTXTByFilename(self, txtPath):
        """
        Load annotation boxes from a txt file.
        :param txtPath: The path to the text file.
        """
        if self.filePath is None:
            return
        if os.path.exists(txtPath) is False:
            return

        shapes = []
        f = open(txtPath, 'r')

        for line in f.readlines():
            line = line.rstrip('\n')
            info = line.split('\t')

            component = info[0]

            ##Find corner coordinates and put them in order of topleft - topright - bottomright - bottomleft
            topleftx = float(info[1])
            toplefty = float(info[2])
            width = float(info[3])
            height = float(info[4])
            points = []
            points.append((topleftx, toplefty))
            points.append((topleftx + width, toplefty))  # topright
            points.append((topleftx + width, toplefty + height))  # bottomright
            points.append((topleftx, toplefty + height))  # bottomleft

            shapes.append((component, points, None, None))

        self.loadLabels(shapes)

        f.close()

    def loadPascalXMLByFilename(self, xmlPath):
        """
        Load annotation boxes from a xml file.
        :param xmlPath: The path to the xml file.
        """
        if self.filePath is None:
            return
        if os.path.exists(xmlPath) is False:
            return

        tVocParseReader = PascalVocReader(xmlPath)
        shapes = tVocParseReader.getShapes()

        # KG Fix where label would include '\n' and '\t' when read from XML
        for shape in range(len(shapes)):
            temp = shapes[shape][0].strip('\n')
            temp = temp.strip('\t')
            temp = temp.strip('\n')
            temp = (temp,)
            formatted = temp + shapes[shape][1:]
            shapes[shape] = formatted

        self.loadLabels(shapes)

    def getComponentPredictions(self):
        """
        Display the dialog box where the user can select the components to get the predicted boxes for.
            This accesses the individual caffe model for the component that the user selects.
        """
        if self.image.isNull():
            self.errorMessage(u'No image open',
                              u'Open an image before accessing models.')
            return

        dlg = DetectionDialog(self.filePath, self)
        if len(dlg.getShapes()) > 0:
            self.loadLabels(dlg.getShapes())


class Settings(object):
    """Convenience dict-like wrapper around QSettings."""

    def __init__(self, types=None):
        self.data = QSettings()
        self.types = defaultdict(lambda: QVariant, types if types else {})

    def __setitem__(self, key, value):
        t = self.types[key]
        self.data.setValue(key,
                           t(value) if not isinstance(value, t) else value)

    def __getitem__(self, key):
        return self._cast(key, self.data.value(key))

    def get(self, key, default=None):
        return self._cast(key, self.data.value(key, default))

    def _cast(self, key, value):
        # XXX: Very nasty way of converting types to QVariant methods :P
        t = self.types.get(key)
        if t is not None and t != QVariant:
            if t is str:
                return ustr(value)
            else:
                try:
                    method = getattr(QVariant, re.sub(
                        '^Q', 'to', t.__name__, count=1))
                    return method(value)
                except AttributeError as e:
                    return value
        return value

class DetectionDialog(QDialog):

    def __init__(self, filePath, parent=None):
        """
        Design the dialog box and display it on the center of the screen.
        :param filePath: The path to the image to run the network on.
        """
        super(DetectionDialog, self).__init__(parent)

        self.filePath = filePath
        self.shapes = []
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(5)

        # Create a progress bar and a button and add them to the main layout
        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0,1)
        self.progressBar.setAlignment(Qt.AlignCenter)

        self.setFixedSize(250, 300)
        self.setWindowTitle("Select components")

        self.icCheck = QCheckBox(self)
        self.capCheck = QCheckBox(self)
        self.resCheck = QCheckBox(self)
        self.labelCheck = QCheckBox(self)

        self.minSize = QSpinBox(self)
        self.minSize.setFixedWidth(60)
        self.minSize.setRange(1, 9999)
        self.minSize.setValue(1)

        self.acceptButton = QPushButton("Ok")
        self.acceptButton.clicked.connect(self.runModels)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)

        checklayout = QGridLayout()
        checklayout.setSpacing(30)
        checklayout.addWidget(QLabel("ICs"), 0, 0)
        checklayout.addWidget(self.icCheck, 0, 2)
        checklayout.addWidget(QLabel("Capacitors"), 1, 0)
        checklayout.addWidget(self.capCheck, 1, 2)
        checklayout.addWidget(QLabel("Resistors"), 2, 0)
        checklayout.addWidget(self.resCheck, 2, 2)
        checklayout.addWidget(QLabel("Labels"), 3, 0)
        checklayout.addWidget(self.labelCheck, 3, 2)
        checklayout.addWidget(QLabel("Min. Box Size"), 4, 0)
        checklayout.addWidget(self.minSize, 4, 2)
        checklayout.setAlignment(Qt.AlignCenter)

        buttonlayout = QHBoxLayout()
        buttonlayout.addWidget(self.acceptButton)
        buttonlayout.addWidget(cancelButton)

        layout = QVBoxLayout()
        layout.addLayout(checklayout)
        layout.addWidget(self.progressBar)
        layout.addLayout(buttonlayout)

        self.setLayout(layout)
        self.exec_()

    def runModels(self):
        """
        Run the models on a separate thread from the GUI.
        """
        self.acceptButton.setEnabled(False)
        self.progressBar.setRange(0, 0)

        components = [self.icCheck.isChecked(), self.capCheck.isChecked(), self.resCheck.isChecked(), self.labelCheck.isChecked(),
                      self.minSize.value()]

        self.modelThread = TaskThread(components, self.filePath)
        self.modelThread.signals.finished.connect(self.onFinished)
        self.threadpool.start(self.modelThread)

    def _loadPredictions(self, component, boxes):
        """
        Put the predictions in the format that labelImg can read.
        :param component: The component to identify.
        :param boxes: The boxes 
        :return: Shapes from the component detector module.
        """
        shapes = []
        for i in range(len(boxes)):
            points = []
            leftx = boxes[i][0]
            topy = boxes[i][1]
            rightx = boxes[i][2]
            bottomy = boxes[i][3]
            points.append((leftx, topy))
            points.append((rightx, topy))  # topright
            points.append((rightx, bottomy))  # bottomright
            points.append((leftx, bottomy))  # bottomleft
            shapes.append([component + str(i), points, None, None])

        return shapes

    def _loadLabels(self, component, boxes):
        """
        Put the predictions in the format that labelImg can read.
        :param component: The component to identify.
        :param boxes: The boxes 
        :return: Shapes from the component detector module.
        """
        shapes = []
        for i in range(len(list(boxes[0]))):
            print(boxes[0][i])
            points = []
            leftx = boxes[0][i][0]
            topy = boxes[0][i][1]
            rightx = boxes[0][i][2]
            bottomy = boxes[0][i][3]
            points.append((leftx, topy))
            points.append((rightx, topy))  # topright
            points.append((rightx, bottomy))  # bottomright
            points.append((leftx, bottomy))  # bottomleft
            shapes.append([component + str(i), points, None, None])

        return shapes

    def getShapes(self):
        """
        :return: The shapes. 
        """
        return self.shapes

    def onFinished(self):
        """
        Display a load bar whenever the user clicks OK.
        """
        # Stop the pulsation
        self.progressBar.setRange(0,1)
        if len(self.modelThread.ics) > 0:
            [self.shapes.append(box) for box in self._loadPredictions("ic", self.modelThread.ics)]
        if len(self.modelThread.caps) > 0:
            [self.shapes.append(box) for box in self._loadPredictions("capacitor", self.modelThread.caps)]
        if len(self.modelThread.res) > 0:
            [self.shapes.append(box) for box in self._loadPredictions("resistor", self.modelThread.res)]
        if len(self.modelThread.labels) > 0:
            [self.shapes.append(box) for box in self._loadLabels("label", self.modelThread.labels)]

        self.accept()

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class TaskThread(QRunnable):
    def __init__(self, components, filePath):
        super(TaskThread, self).__init__()
        self.signals = WorkerSignals()
        self.components = components
        self.filePath = filePath
        self.ics = []
        self.caps = []
        self.res = []
        self.labels = []

    def run(self):
        """
        Run the models.
        """
        boxes = []
        minSize = self.components[4]
        if self.components[0]:  # ic
            detector = cd.componentDetector("ic", "gpu")
            self.ics = detector.detectfast(self.filePath, minSize)
        if self.components[1]:
            detector = cd.componentDetector("capacitor", "gpu")
            self.caps = detector.detectfast(self.filePath, minSize)
        if self.components[2]:
            detector = cd.componentDetector("resistor", "gpu")
            self.res = detector.detectfast(self.filePath, minSize)
        if self.components[3]:
            detector = TextRecognizer("GPU")
            self.labels = detector.detectText(self.filePath)
        self.signals.finished.emit()


def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("logo"))
    # Accept extra agruments to change predefined class file
    # Usage : labelImg.py image predefClassFile
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join('data', 'predefined_classes.txt'))
    win.show()
    return app, win


def main(argv=[]):
    '''construct main app and run it'''
    app, _win = get_main_app(argv)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
