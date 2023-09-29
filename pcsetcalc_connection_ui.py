# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/yota/Data/Programming/Python/PyCharmProjects/PCSetCalc/QtDesigner/PCSetCalc_Connection.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ConnectionDialog(object):
    def setupUi(self, ConnectionDialog):
        ConnectionDialog.setObjectName("ConnectionDialog")
        ConnectionDialog.resize(400, 260)
        ConnectionDialog.setStyleSheet("/* Global setting */\n"
"QWidget {\n"
"    font: 11pt \"Verdana\";\n"
"    color: rgb(189, 189, 189); /* 400 */\n"
"    background-color: rgb(33, 33, 33); /* 900 */\n"
"    }\n"
"\n"
"/*  Dialog Button Box */\n"
" QDialogButtonBox {\n"
"    button-layout: 1; \n"
"    min-width: 200px;\n"
"    }\n"
"QDialogButtonBox QPushButton {\n"
"    border: none;\n"
"    min-width: 40px;\n"
"    min-height: 20px;\n"
"    padding-left: 12px;\n"
"    padding-top: 2px;\n"
"    padding-right: 12px;\n"
"    padding-bottom: 5px;\n"
"    margin: 2px;\n"
"    background-color: rgb(66, 66, 66); /* 800 */\n"
"    }\n"
"QDialogButtonBox QPushButton:pressed, QPushButton:checked {\n"
"    color: rgb(224, 224, 224); /* 300 */\n"
"    background-color: rgb(97, 97, 97); /* 700 */\n"
"    }\n"
"\n"
"/* Combo Box { button-layout: 2 }*/\n"
"QComboBox {\n"
"    border: none;\n"
"    color: rgb(189, 189, 189); /* 400 */\n"
"    background-color: rgb(66, 66, 66); /* 800 */\n"
"    }\n"
"QComboBox::drop-down {\n"
"    border: none;\n"
"    background-color: rgb(97, 97, 97); /* 700 */\n"
"    width: 15px;\n"
"    }\n"
"QComboBox::down-arrow {\n"
"    image: url(:/Icons/Images/DownArrow_Silver_01.png); \n"
"    width: 10px;\n"
"    height: 10px;\n"
"    }\n"
"QComboBox QAbstractItemView {\n"
"    border: none;\n"
"    background-color: rgb(52, 52, 52); /* 800+ */\n"
"    min-width: 100px;\n"
"    padding: 5px;\n"
"}")
        self.buttonBox = QtWidgets.QDialogButtonBox(ConnectionDialog)
        self.buttonBox.setGeometry(QtCore.QRect(27, 185, 339, 56))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.labelMIDIInPOrt = QtWidgets.QLabel(ConnectionDialog)
        self.labelMIDIInPOrt.setGeometry(QtCore.QRect(41, 73, 69, 16))
        self.labelMIDIInPOrt.setObjectName("labelMIDIInPOrt")
        self.labelUDPPort = QtWidgets.QLabel(ConnectionDialog)
        self.labelUDPPort.setGeometry(QtCore.QRect(60, 120, 50, 14))
        self.labelUDPPort.setObjectName("labelUDPPort")
        self.comboBoxUDPPort = QtWidgets.QComboBox(ConnectionDialog)
        self.comboBoxUDPPort.setGeometry(QtCore.QRect(119, 115, 104, 26))
        self.comboBoxUDPPort.setMinimumSize(QtCore.QSize(104, 26))
        self.comboBoxUDPPort.setMaximumSize(QtCore.QSize(104, 26))
        self.comboBoxUDPPort.setFocusPolicy(QtCore.Qt.NoFocus)
        self.comboBoxUDPPort.setObjectName("comboBoxUDPPort")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxUDPPort.addItem("")
        self.comboBoxMIDIInPort = QtWidgets.QComboBox(ConnectionDialog)
        self.comboBoxMIDIInPort.setGeometry(QtCore.QRect(119, 69, 243, 26))
        self.comboBoxMIDIInPort.setMinimumSize(QtCore.QSize(243, 26))
        self.comboBoxMIDIInPort.setMaximumSize(QtCore.QSize(243, 26))
        self.comboBoxMIDIInPort.setFocusPolicy(QtCore.Qt.NoFocus)
        self.comboBoxMIDIInPort.setObjectName("comboBoxMIDIInPort")

        self.retranslateUi(ConnectionDialog)
        self.buttonBox.accepted.connect(ConnectionDialog.accept)
        self.buttonBox.rejected.connect(ConnectionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ConnectionDialog)

    def retranslateUi(self, ConnectionDialog):
        _translate = QtCore.QCoreApplication.translate
        ConnectionDialog.setWindowTitle(_translate("ConnectionDialog", "Connection"))
        self.labelMIDIInPOrt.setText(_translate("ConnectionDialog", "MIDI In Port"))
        self.labelUDPPort.setText(_translate("ConnectionDialog", "UDP Port"))
        self.comboBoxUDPPort.setItemText(0, _translate("ConnectionDialog", "3000"))
        self.comboBoxUDPPort.setItemText(1, _translate("ConnectionDialog", "3001"))
        self.comboBoxUDPPort.setItemText(2, _translate("ConnectionDialog", "3002"))
        self.comboBoxUDPPort.setItemText(3, _translate("ConnectionDialog", "3003"))
        self.comboBoxUDPPort.setItemText(4, _translate("ConnectionDialog", "3004"))
        self.comboBoxUDPPort.setItemText(5, _translate("ConnectionDialog", "3005"))
        self.comboBoxUDPPort.setItemText(6, _translate("ConnectionDialog", "3006"))
        self.comboBoxUDPPort.setItemText(7, _translate("ConnectionDialog", "3007"))
        self.comboBoxUDPPort.setItemText(8, _translate("ConnectionDialog", "3008"))
        self.comboBoxUDPPort.setItemText(9, _translate("ConnectionDialog", "3009"))

import pcsetcalc_resources_rc
