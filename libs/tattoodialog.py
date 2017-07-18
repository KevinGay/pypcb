from PyQt4 import QtGui
from PyQt4 import QtCore
from lib import newIcon

BB = QtGui.QDialogButtonBox

class TattooDialog(QtGui.QDialog):
    """
    This class is a dialog box that will appear when the user selects the label_class 'Tattoo'
    """

    def __init__(self, parent=None):
        super(TattooDialog, self).__init__(parent)

        self.setMinimumSize(488, 411)

        # Layouts
        layout = QtGui.QVBoxLayout()
        torplayout = QtGui.QHBoxLayout()

        leftbuttonset = QtGui.QVBoxLayout()
        ttypelayout = QtGui.QVBoxLayout()
        self.colorlayout = QtGui.QVBoxLayout()
        tclasslayout = QtGui.QVBoxLayout()
        tattoolayout = QtGui.QHBoxLayout()

        piercinglayout = QtGui.QHBoxLayout()
        ptypelayout = QtGui.QVBoxLayout()
        ploclayout = QtGui.QVBoxLayout()

        # Group declarations
        self.tattoogroup = QtGui.QGroupBox("Tattoo")
        self.ttypegroup = QtGui.QGroupBox("Type")
        self.colorgroup = QtGui.QGroupBox("Color")
        self.tclassgroup = QtGui.QGroupBox("Class")

        self.piercinggroup = QtGui.QGroupBox("Piercing")
        self.ptypegroup = QtGui.QGroupBox("Type")
        self.plocgroup = QtGui.QGroupBox("Location")

        self.piercinggroup.setCheckable(True)
        self.tattoogroup.setCheckable(True)
        self.piercinggroup.setChecked(False)
        self.tattoogroup.setChecked(False)


        # Tattoo Types
        chemical = QtGui.QRadioButton("Chemical")
        brand = QtGui.QRadioButton("Brand")
        cut = QtGui.QRadioButton("Cut")

        # Connect buttons to methods to set the color property to visible or invisible.
        # This is because only chemical tattoos can have color.
        chemical.toggled.connect(self.chemtoggled)
        brand.toggled.connect(self.brandtoggled)
        cut.toggled.connect(self.cuttoggled)

        self.ttypes = [chemical, brand, cut]
        for type in self.ttypes:
            ttypelayout.addWidget(type)
        self.ttypegroup.setLayout(ttypelayout)

        # Tattoo color
        self.monochrome = QtGui.QRadioButton("Monochrome")
        self.color = QtGui.QRadioButton("Color")
        self.colors = [self.monochrome, self.color]
        for c in self.colors:
            self.colorlayout.addWidget(c)
        self.colorgroup.setLayout(self.colorlayout)

        # leftbuttonset consists of tattoo types and color
        leftbuttonset.addStretch()
        leftbuttonset.addWidget(self.ttypegroup)
        leftbuttonset.addStretch()
        leftbuttonset.addWidget(self.colorgroup)
        leftbuttonset.addStretch()

        #Tattoo class
        # Note: tclasses will contain the actual QtGui buttons after the following loop executes
        self.tclasses = ['Human', 'Animal', 'Plant', 'Flag', 'Object', 'Abstract', 'Symbol', 'Word', 'Other']
        for i in range(len(self.tclasses)):
            button = QtGui.QRadioButton(self.tclasses[i])
            tclasslayout.addWidget(button)
            #Replace the strings in tclasses with the actual button
            self.tclasses[i] = button
        self.tclassgroup.setLayout(tclasslayout)

        tattoolayout.addLayout(leftbuttonset)
        tattoolayout.addWidget(self.tclassgroup)

        self.tattoogroup.setLayout(tattoolayout)
        torplayout.addWidget(self.tattoogroup)

        #Piercings

        # Piering types
        # Note: ptypes will contain the actual QtGui buttons after the following loop executes
        self.ptypes = ['Stud', 'Ring', 'Bar', 'Plug', 'Taper', 'Flesh Tunnel', 'Implant']
        for i in range(len(self.ptypes)):
            button = QtGui.QRadioButton(self.ptypes[i])
            ptypelayout.addWidget(button)
            self.ptypes[i] = button
        self.ptypegroup.setLayout(ptypelayout)

        piercinglayout.addWidget(self.ptypegroup)

        self.plocations = ['Forehead', 'Eyebrow', 'Bridge', 'Anti-eyebrow', 'Nose', 'Septum', 'Medusa', 'Monroe',
                      'Dimple', 'Labret', 'Ear', 'Body', 'Other']
        for i in range(len(self.plocations)):
            button = QtGui.QRadioButton(self.plocations[i])
            ploclayout.addWidget(button)
            self.plocations[i] = button
        self.plocgroup.setLayout(ploclayout)

        piercinglayout.addWidget(self.plocgroup)

        self.piercinggroup.setLayout(piercinglayout)
        torplayout.addStretch()
        torplayout.addSpacing(10)
        torplayout.addWidget(self.piercinggroup)


        # Ok / cancel buttons
        self.buttonbox = QtGui.QDialogButtonBox(BB.Ok | BB.Cancel, QtCore.Qt.Horizontal, self)
        self.buttonbox.button(BB.Ok).setIcon(newIcon('done'))
        self.buttonbox.button(BB.Cancel).setIcon(newIcon('undo'))

        self.buttonbox.accepted.connect(self.validate)
        self.buttonbox.rejected.connect(self.reject)

        #Finalize layout
        layout.addLayout(torplayout)
        layout.addWidget(self.buttonbox)

        self.setWindowTitle("Tattoo & Piercing Information")
        self.setLayout(layout)

        self.selected = []

    def validate(self):
        if self.piercinggroup.isChecked() == False and self.tattoogroup.isChecked() == False:
            return QtGui.QMessageBox.critical(self, u'Error',
                                              u'<p><b>Error</b></p> Tattoo or piercing must be selected.')
        elif self.piercinggroup.isChecked() and self.tattoogroup.isChecked():
            return QtGui.QMessageBox.critical(self, u'Error',
                                        u'<p><b>Error</b></p> Tattoo and piercing cannot both be selected.')
        elif (len(self.getSelected()) < 4 and self.tattoogroup.isChecked()) or \
                (len(self.getSelected()) < 3 and self.piercinggroup.isChecked()):
            return QtGui.QMessageBox.critical(self, u'Error',
                                        u'<p><b>Error</b></p> Each category must be selected.')
        else:
            self.accept()

    def chemtoggled(self, checked):
        if checked:
            self.color.setAutoExclusive(False)
            self.monochrome.setAutoExclusive(False)
            self.monochrome.setChecked(False)
            self.color.setVisible(True)
            self.color.setAutoExclusive(True)
            self.monochrome.setAutoExclusive(True)

    def brandtoggled(self, checked):
        if checked:
            self.monochrome.setChecked(True)
            self.color.setVisible(False)

    def cuttoggled(self, checked):
        if checked:
            self.monochrome.setChecked(True)
            self.color.setVisible(False)

    def getSelected(self):
        self.selected = []
        if self.tattoogroup.isChecked():
            self.selected.append('t')
            for button in self.ttypes:
                if button.isChecked():
                    self.selected.append(str(button.text()))
            for button in self.tclasses:
                if button.isChecked():
                    self.selected.append(str(button.text()))
            for button in self.colors:
                if button.isChecked():
                    self.selected.append(str(button.text()))
        elif self.piercinggroup.isChecked():
            self.selected.append('p')
            for button in self.ptypes:
                if button.isChecked():
                    self.selected.append(str(button.text()))
            for button in self.plocations:
                if button.isChecked():
                    self.selected.append(str(button.text()))


        return self.selected

    def resetSelected(self):
        """
        Reset all of the checked radio buttons and check boxes.
        """

        def _resethelp(button):
            #All button groups must be set to non exclusive for setChecked to work
            button.setAutoExclusive(False)
            button.setChecked(False)
            button.setAutoExclusive(True)

        for button in self.ttypes:
            _resethelp(button)
        for button in self.tclasses:
            _resethelp(button)
        for button in self.colors:
            _resethelp(button)

        for button in self.ptypes:
            _resethelp(button)
        for button in self.plocations:
            _resethelp(button)

        self.tattoogroup.setChecked(False)
        self.piercinggroup.setChecked(False)


    def setSelected(self, tp, type, classorloc, color=None):
        self.resetSelected()
        if tp == 't':
            self.tattoogroup.setChecked(True)
            for button in self.ttypes:
                if type == button.text():
                    button.setChecked(True)
            for button in self.tclasses:
                if classorloc == button.text():
                    button.setChecked(True)
            for button in self.colors:
                if color == button.text():
                    button.setChecked(True)

        elif tp == 'p':
            self.piercinggroup.setChecked(True)
            for button in self.ptypes:
                if type == button.text():
                    button.setChecked(True)
            for button in self.plocations:
                if classorloc == button.text():
                    button.setChecked(True)

    def popUp(self, x, y):

        self.setFocus(QtCore.Qt.PopupFocusReason)
        self.move(x, y)
        return self.getSelected() if self.exec_() else None
