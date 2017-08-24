try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import QColorDialog, QDialogButtonBox
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

BB = QDialogButtonBox

class ColorDialog(QColorDialog):
    """
    A color dialog displays whenever the user wants to change the line color or fill color of the shapes.
    """
    def __init__(self, parent=None):
        """
        Create a color dialog box.
        :param parent: The parent of the dialog box.
        """
        super(ColorDialog, self).__init__(parent)
        self.setOption(QColorDialog.ShowAlphaChannel)
        # The Mac native dialog does not support our restore button.
        self.setOption(QColorDialog.DontUseNativeDialog)
        ## Add a restore defaults button.
        # The default is set at invocation time, so that it
        # works across dialogs for different elements.
        self.default = None
        self.bb = self.layout().itemAt(1).widget()
        self.bb.addButton(BB.RestoreDefaults)
        self.bb.clicked.connect(self.checkRestore)

    def getColor(self, value=None, title=None, default=None):
        """
        Get the color from the dialog box.
        :param value: The color that the user picked in the dialog box.
        :param title: The title to display on the dialog box.
        :param default: The default color to select.
        :return: The color that the user picked in the dialog box.
        """
        self.default = default
        if title:
            self.setWindowTitle(title)
        if value:
            self.setCurrentColor(value)
        return self.currentColor() if self.exec_() else None

    def checkRestore(self, button):
        if self.bb.buttonRole(button) & BB.ResetRole and self.default:
            self.setCurrentColor(self.default)

