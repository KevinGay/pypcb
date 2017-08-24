try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

try:
    from libs.lib import newIcon, labelValidator
except ImportError:
    from lib import newIcon, labelValidator

BB = QDialogButtonBox

class LabelDialog(QDialog):
    """
    This class inherits the QDialog class. LabelDialogs are displayed after the user draws a shape. It helps the 
    user pick a label from a list of declare a new label to associate with a shape.
    """

    def __init__(self, text="Enter object label", parent=None, listItem=None):
        """
        Create an instance of the labelDialog.
        :param text: The text to display at the top of the dialog box.
        :param parent: The parent of the dialog box. None by default.
        :param listItem: The listItem to select when the dialog box is displayed.
        """
        super(LabelDialog, self).__init__(parent)
        self.edit = QLineEdit()
        self.edit.setText(text)
        self.edit.setValidator(labelValidator())
        self.edit.editingFinished.connect(self.postProcess)
        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        self.buttonBox = bb = BB(BB.Ok | BB.Cancel, Qt.Horizontal, self)
        bb.button(BB.Ok).setIcon(newIcon('done'))
        bb.button(BB.Cancel).setIcon(newIcon('undo'))
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

        if listItem is not None and len(listItem) > 0:
            self.listWidget = QListWidget(self)
            for item in listItem:
                self.listWidget.addItem(item)
            self.listWidget.itemDoubleClicked.connect(self.listItemClick)
            layout.addWidget(self.listWidget)

        self.setLayout(layout)

    def validate(self):
        """
        Validate that the string supplied has no leading or trailing spaces.
        """
        try:
            if self.edit.text().trimmed():
                self.accept()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            if self.edit.text().strip():
                self.accept()

    def postProcess(self):
        try:
            self.edit.setText(self.edit.text().trimmed())
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            self.edit.setText(self.edit.text())

    def popUp(self, text='', move=True):
        """
        Display the dialog box in front of the main application.
        :param text: The text that will currently be displayed in the dialog.
        :param move: A bool that tells whether or not to move the dialog box before displaying it.
        :return: 
        """
        self.edit.setText(text)
        self.edit.setSelection(0, len(text))
        self.edit.setFocus(Qt.PopupFocusReason)
        if move:
            self.move(QCursor.pos())
        return self.edit.text() if self.exec_() else None

    def listItemClick(self, QListWidgetItem):
        """
        This is called whenever an item in the list is clicked.
        :param tQListWidgetItem: The QListWidgetItem that is clicked.
        """
        try:
            text = QListWidgetItem.text().trimmed()
        except AttributeError:
            # PyQt5: AttributeError: 'str' object has no attribute 'trimmed'
            text = QListWidgetItem.text().strip()
        self.edit.setText(text)
        self.validate()
