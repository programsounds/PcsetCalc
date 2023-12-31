# pcsetcalc_app.py

import sys
import os
import json
import time
from typing import List, Dict
from PyQt6 import QtCore, QtWidgets
import rtmidi
from oscpy.server import OSCThreadServer
from pcpy.pcset import Pcset
from pcpy.query import toPFStr, fromPFStr, catalog
import pcpy.constants as c
from pcsetcalc_main_ui import Ui_MainWindow
from pcsetcalc_connection_ui import Ui_ConnectionDialog

# TODO: constancts here
STATUS_BYTE_NOTE_ON = 144  # MIDI channel 1
STATUS_BYTE_CONTROL_CHANGE = 176  # MIDI channel 1
CC_SUSTAIN = 11  # MIDI CC to use for sustain pedal (11 = expression controller)
SUSTAIN_THRESH = 110  # Threshold for sustain pedal (ON if less than thresh)

SERVER_ADDRESS = "127.0.0.1"
OSC_ADDRESS = b"/noteData"
MIDI_MESSAGE_POLL_INTERVAL = 10  # Polling interval for MIDI messages (ms)


class MainWindow(QtWidgets.QMainWindow):
    """Main application window"""
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setGeometry(0, 0, 1440, 830)
        # Initialize profile data
        self.pcset = Pcset({})  # Pcset object for operations with currently "active" pcs
        self.card = 0
        self.nf = []         # Normal form
        self.pf = []         # Prime form
        self.sn = ""         # Set name
        self.lvl = ""        # Tn/TnI transformation level
        self.matts = []      # Modal attributes
        self.icv = []        # Interval class vector
        self.iv = [""] * 12  # Index vector
        self.lcomp = []      # Literal complement
        self.acomp = []      # Abstract complement
        self.zcorr = ""      # Z-correspondent
        self.mcomps = {}     # Modal complements
        self.tn = []         # Tn transformation
        self.tni = []        # TnI transformation
        self.summary = ""    # Set info summary
        # Initialize widgets
        self.pcBtns = [self.ui.btnPC0, self.ui.btnPC1, self.ui.btnPC2,
                       self.ui.btnPC3, self.ui.btnPC4, self.ui.btnPC5,
                       self.ui.btnPC6, self.ui.btnPC7, self.ui.btnPC8,
                       self.ui.btnPC9, self.ui.btnPC10, self.ui.btnPC11]  # Stores the toggle states
        self.ivTable = self.setupIndexVectorTable()  # Index vector table (1d list)
        self.mcompTable = self.setupModalComplementTable()  # Modal complements table (2d list)
        self.targetSCMemberTable = self.setupTargetSCMemberTable()  # Target SC member table (2d list)
        self.mscTables = self.setupModalSetComplexTables()  # Modal set complex tables (dict)
        octLabels = self.ui.frameOCT.findChildren(QtWidgets.QLabel)
        wtLabels = self.ui.frameWT.findChildren(QtWidgets.QLabel)
        hexLabels = self.ui.frameHEX.findChildren(QtWidgets.QLabel)
        octLabelsOuter = list(set(self.ui.frameOCT_outer.findChildren(QtWidgets.QLabel)) - set(octLabels))
        hexLabelsOuter = list(set(self.ui.frameHEX_outer.findChildren(QtWidgets.QLabel)) - set(hexLabels))
        self.colLabelsInner = octLabels + wtLabels + hexLabels  # PC labels inside collection frames
        self.colLabelsOuter = octLabelsOuter + hexLabelsOuter   # PC labels outside collection frames
        # Undo/redo stacks
        self.undoStack = []  # Undo stack
        self.redoStack = []  # Redo stack
        # Recall preferences
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle
            # noinspection PyProtectedMember
            baseDir = sys._MEIPASS  # _MEIPASS is added by PyInstaller at runtime
        else:
            baseDir = os.path.dirname(__file__)
        self.prefFile = os.path.join(baseDir, "preferences.json")
        with open(self.prefFile, "r") as f:
            pref = json.load(f)
        self.midiInPort = pref["MIDIIn"]
        self.udpPort = pref["OSC"]
        # Worker thread for MIDI input
        self.threadMIDI = WorkerMIDI()
        self.threadMIDI.setInputPort(self.midiInPort)
        # Worker thread for OSC input
        self.threadOSC = WorkerOSC(self.udpPort)
        # Initialize display widgets
        self.resetTargetSCMenu()  # Target set-class menu
        # Set up dialog objects
        self.connectionDialog = ConnectionDialog(self.threadMIDI.getInputPorts())
        self.connectionDialog.setMIDIInPortMenu(self.midiInPort)
        self.connectionDialog.setUDPPortMenu(self.udpPort)
        # Signal-slot connections
        self.makeConnections()

    @staticmethod
    def makeTableItems(table, rows, cols):
        """
        Create TableWidgetItems in a table widget.

        :param table: a table widget object to write items to.
        :param rows: an int for the number of rows in the table.
        :param cols: an int for the number of columns in the table.
        :return: a list for the table items (1d if single row; 2d if multiple rows).
        """
        tableItems = []
        for row in range(rows):
            rowItems = []
            for col in range(cols):
                item = QtWidgets.QTableWidgetItem()
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter |
                                      QtCore.Qt.AlignmentFlag.AlignVCenter)
                rowItems.append(item)
                table.setItem(row, col, item)
            tableItems.append(rowItems)
        if len(tableItems) == 1:
            # Return a 1d list if there is a single row
            return tableItems[0]
        else:
            return tableItems

    def setupIndexVectorTable(self):
        """
        Returns a list of TableWidgetItems for the index vector:
        each of them is configured for the specific default.
        """
        return MainWindow.makeTableItems(self.ui.tableIndexVector, 1, 12)

    def setupModalComplementTable(self) -> List[List[QtWidgets.QTableWidgetItem]]:
        """
        Returns a list of TableWidgetItems for the modal complements.
        The list is structured for 3x3 table as:
            [[refCol, mcomp, SN],
             [refCol, mcomp, SN],
             [refCol, mcomp, SN]]
        """
        table = self.ui.tableMComps
        table.setColumnWidth(0, 55)
        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 55)
        return MainWindow.makeTableItems(table, 3, 3)

    def setupTargetSCMemberTable(self) -> List[List[QtWidgets.QTableWidgetItem]]:
        """
        Returns a list of TableWidgetItems for the target SC members.
        The list is structured for 15x5 table as:
            [[incl/comp, Tn/TnI, MA, diff, diffInfo],
             [incl/comp, Tn/TnI, MA, diff, diffInfo],
             ...,
             [incl/comp, Tn/TnI, MA, diff, diffInfo]]
        """
        table = self.ui.tableTargetSCMembers
        table.setColumnWidth(0, 140)
        table.setColumnWidth(1, 60)
        table.setColumnWidth(2, 80)
        table.setColumnWidth(3, 140)
        table.horizontalHeader().setSectionResizeMode(4,
                                                      QtWidgets.QHeaderView.ResizeMode.Stretch)
        return MainWindow.makeTableItems(table, 20, 5)

    def setupModalSetComplexTables(self) -> Dict[str, List[List[QtWidgets.QTableWidgetItem]]]:
        """
        Returns a dict of 3 key/val pairs where key is the cardinality of
        MSC members of the table, and val is a list of TableWidgetItems
        structured for the table showing MSC members. The structure of each
        list is the same except for the last column--there is no Z-corr.
        column for the table of trichordal MSC members.
            [[SN, MA, sym, count, (Z-corr)],
             [SN, MA, sym, count, (Z-corr)],
             ...
             [SN, MA, sym, count, (Z-corr)]]
        """
        tables = [self.ui.tableMSCTrichords,
                  self.ui.tableMSCTetrachords,
                  self.ui.tableMSCHexachords]
        i = 0
        for table in range(3):
            tables[i].setColumnWidth(0, 50)
            tables[i].setColumnWidth(1, 70)
            tables[i].setColumnWidth(2, 50)
            tables[i].setColumnWidth(3, 30)
            if i >= 1:
                tables[i].setColumnWidth(4, 50)
            i += 1
        tableDict = dict([("3", MainWindow.makeTableItems(tables[0], 7, 4)),
                          ("4", MainWindow.makeTableItems(tables[1], 7, 5)),
                          ("6", MainWindow.makeTableItems(tables[2], 7, 5))])
        return tableDict

    def makeConnections(self):
        """Make signal-slot connections"""
        # Membership update of the pcset through button interaction
        for i in range(12):
            self.pcBtns[i].released.connect(lambda pc=i: self.inputPC(pc, self.pcBtns[pc].isChecked()))
        # Reset pcset
        self.ui.btnReset.released.connect(self.resetPCSet)
        # Create Tn transformation
        self.ui.comboBoxTn.activated.connect(self.transpose)
        # Apply Tn transformation
        self.ui.btnTn.released.connect(self.applyTn)
        # Create TnI transformation
        self.ui.comboBoxTnI.activated.connect(self.invert)
        # Apply TnI transformation
        self.ui.btnTnI.released.connect(self.applyTnI)
        # Create target SC members in the table
        self.ui.comboBoxTargetSCs.activated.connect(self.createTargetSCMembers)
        # Retrigger the output of the target SC menu
        self.ui.btnTargetSCRetrig.released.connect(self.createTargetSCMembers)
        # Change the current pcset to the selected target SC member
        self.ui.tableTargetSCMembers.verticalHeader().sectionClicked.connect(self.changeToTargetSCMember)
        # Undo the previous operation
        self.ui.btnUndo.released.connect(self.undo)
        # Redo the undone operation
        self.ui.btnRedo.released.connect(self.redo)
        # Actions (Edit/)
        self.ui.actionUndo.triggered.connect(self.undo)
        self.ui.actionRedo.triggered.connect(self.redo)
        self.ui.actionPC0.triggered.connect(lambda: self.togglePCBtn(0))
        self.ui.actionPC1.triggered.connect(lambda: self.togglePCBtn(1))
        self.ui.actionPC2.triggered.connect(lambda: self.togglePCBtn(2))
        self.ui.actionPC3.triggered.connect(lambda: self.togglePCBtn(3))
        self.ui.actionPC4.triggered.connect(lambda: self.togglePCBtn(4))
        self.ui.actionPC5.triggered.connect(lambda: self.togglePCBtn(5))
        self.ui.actionPC6.triggered.connect(lambda: self.togglePCBtn(6))
        self.ui.actionPC7.triggered.connect(lambda: self.togglePCBtn(7))
        self.ui.actionPC8.triggered.connect(lambda: self.togglePCBtn(8))
        self.ui.actionPC9.triggered.connect(lambda: self.togglePCBtn(9))
        self.ui.actionPC10.triggered.connect(lambda: self.togglePCBtn(10))
        self.ui.actionPC11.triggered.connect(lambda: self.togglePCBtn(11))
        self.ui.actionReset.triggered.connect(self.resetPCSet)
        # Show MSC members in the tables
        self.ui.comboBoxNexus.activated.connect(self.showMSCTables)
        # Create SC members of a MSC member in the table
        self.ui.tableMSCTrichords.cellDoubleClicked.connect(
            lambda row, col: self.findMSCSCMembers(self.ui.tableMSCTrichords, row, col))
        self.ui.tableMSCTetrachords.cellDoubleClicked.connect(
            lambda row, col: self.findMSCSCMembers(self.ui.tableMSCTetrachords, row, col))
        self.ui.tableMSCHexachords.cellDoubleClicked.connect(
            lambda row, col: self.findMSCSCMembers(self.ui.tableMSCHexachords, row, col))
        # Custom signals
        # noinspection PyArgumentList
        self.threadMIDI.message.connect(self.midiInput,
                                        QtCore.Qt.ConnectionType.QueuedConnection)
        # noinspection PyArgumentList
        self.threadOSC.message.connect(self.updatePCSet,
                                       QtCore.Qt.ConnectionType.QueuedConnection)
        self.connectionDialog.message.connect(self.setPorts)
        # Show dialog boxes
        self.ui.actionMIDI_OSC.triggered.connect(self.showConnectionDialog)

    # PC input and peripheral methods -----------------------------------------

    def inputPC(self, pc, state):
        """
        Add/remove a single pc to/from the current set

        :param pc: int for pc
        :param state: bool for set membership
        """
        if state:
            self.pcset.union({pc})
        else:
            self.pcset.difference({pc})
        self.updateProfile()
        self.updateDisplay()

    def midiInput(self, pc, state):
        """
        Midi input for pcs

        :param pc: int for pc
        :param state: bool for set membership
        """
        self.pcBtns[pc].setChecked(state)
        self.inputPC(pc, state)

    def togglePCBtn(self, pc):
        """Toggle the state of a pc button"""
        self.pcBtns[pc].toggle()
        self.inputPC(pc, self.pcBtns[pc].isChecked())

    def startWorkerMIDI(self):
        """Starts the worker thread for MIDI input"""
        self.threadMIDI.start()

    def startWorkerOSC(self):
        """Starts the worker thread for OSC input"""
        self.threadOSC.start()

    def closeServerSocket(self):
        """Closes the OSC server socket"""
        self.threadOSC.close()

    def updatePCSet(self, pcs, archive=True):
        """Mutate the current set to the input set"""
        if archive:
            self.archive()
        self.pcset = Pcset(pcs)
        self.updateProfile()
        self.updateDisplay()
        self.resetOperations()
        self.resetPCBtns()
        self.showPCBtns()

    def updateProfile(self):
        """Update the instance variables for set profile"""
        self.card = len(self.pcset)
        self.nf = self.pcset.normalForm()
        self.pf = self.pcset.primeForm()
        self.sn = MainWindow.setName(self.pcset)
        self.lvl = MainWindow.transformationLevel(self.pcset)
        self.matts = self.modalAttributes(self.pcset)
        self.icv = MainWindow.intervalClassVector(self.pcset)
        self.iv = MainWindow.indexVector(self.pcset)
        self.lcomp = MainWindow.literalComplement(self.pcset)
        self.acomp = MainWindow.abstractComplement(self.pcset)
        self.zcorr = MainWindow.zCorrespondent(self.pcset)
        self.mcomps = MainWindow.modalComplements(self.pcset)
        self.summary = self.setSummary(self.pcset)

    def resetPCSet(self):
        """Clears the pcset and reset the display"""
        self.archive()
        self.pcset = Pcset({})
        self.resetProfile()
        self.resetDisplay()

    def resetProfile(self):
        """Reset the instance variables for set profile"""
        self.card = 0
        self.nf = []
        self.pf = []
        self.sn = ""
        self.lvl = ""
        self.matts = []
        self.icv = []
        self.iv = [""] * 12
        self.lcomp = []
        self.acomp = []
        self.zcorr = ""
        self.mcomps = {}
        self.tn = []
        self.tni = []
        self.summary = ""

    def archive(self):
        """Archives the current pcset to undoStack"""
        self.undoStack.insert(0, self.pcset)
        if len(self.undoStack) > 10:
            self.undoStack = self.undoStack[:10]
        self.redoStack = []

    def showConnectionDialog(self):
        """Shows Connection dialog box in modeless mode"""
        self.connectionDialog.show()

    def setUDPPort(self, port):
        """Sets the UDP port to the one selected in the connection window"""
        self.threadOSC.changePort(port)

    def setPorts(self, midiInPort, udpPort):
        """
        Effects the port changes and saves the settings in the preference file.

        :param midiInPort: an int for MIDI input port number.
        :param udpPort: an int for UDP port number.
        """
        count = 0
        # If MIDI input port is changed, update the instance variable and effect the change.
        if self.midiInPort != midiInPort:
            self.midiInPort = midiInPort
            self.threadMIDI.setInputPort(self.midiInPort)
            count += 1
        # If UDP port is changed, update the instance variable and effect the change.
        if self.udpPort != udpPort:
            self.udpPort = udpPort
            self.setUDPPort(self.udpPort)
            count += 1
        # If either of the ports are changed, write the current settings to the pref file.
        if count > 0:
            pref = {"MIDIIn": self.midiInPort, "OSC": self.udpPort}
            with open(self.prefFile, "w") as outfile:
                json.dump(pref, fp=outfile, indent=4, sort_keys=True)

    # Set profile query and calculation methods -------------------------------

    @staticmethod
    def setName(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a str for the set name of pf.
        """
        if not (3 <= len(pcsetObj) <= 9):
            return ""
        else:
            pf = toPFStr(pcsetObj.primeForm())
            return catalog["PFToSN"][pf]

    @staticmethod
    def transformationLevel(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a str for the most basic transformation level of the input set:
            if it is a symmetrical set, the Tn level with the smallest transposition
            number represents the transformation level.
        """
        if not (3 <= len(pcsetObj) <= 9):
            return ""
        dct = pcsetObj.transformationLevels()
        lvls = []
        for i in dct["Tn"]:
            lvls.append("T" + str(i))
        for j in dct["TnI"]:
            lvls.append("T" + str(j) + "I")
        return lvls[0]

    @staticmethod
    def modalAttributes(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a list of the modal attributes of the input set:
            each attribute is represented by a str.
        """
        card = len(pcsetObj)
        if not (3 <= card <= 9):
            return []
        else:
            matts = []
            ref = pcsetObj.referentialCollections()
            for col in c.REF_COLS:
                if ref[col] == 2:
                    matts.append(col)
                elif card == 6 and ref[col] == 1:
                    matts.append(col + "'")
            if ref["D"]:
                matts.append("D")
            return matts

    @staticmethod
    def intervalClassVector(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a list for the ICV of the input set.
        """
        if not (2 <= len(pcsetObj) <= 9):
            return []
        else:
            return pcsetObj.icv()

    @staticmethod
    def indexVector(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a list for the index vector of the input set.
        """
        if not (2 <= len(pcsetObj) <= 9):
            return [""] * 12
        else:
            return pcsetObj.indexVector()

    @staticmethod
    def literalComplement(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a list for the literal complement of the input set:
            the returned set is in normal form.
        """
        if len(pcsetObj) == 0:
            return []
        else:
            return Pcset(pcsetObj.complement()).normalForm()

    @staticmethod
    def abstractComplement(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a list for the abstract complement of the input set:
        the returned set is in prime form.
        """
        if len(pcsetObj) == 0:
            return []
        else:
            return Pcset(pcsetObj.complement()).primeForm()

    @staticmethod
    def zCorrespondent(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a str of the set name of Z-correspondent of the input set:
            an empty str is returned when it's not Z-related.
        """
        sn = MainWindow.setName(pcsetObj)
        # Z-related sets are only card between 4 and 8
        if not (4 <= len(pcsetObj) <= 8):
            return ""
        else:
            zcorr = catalog["SC"][sn]["Z-corr"]
            if zcorr is not None:
                return zcorr
            else:
                return ""

    @staticmethod
    def modalComplements(pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a dict (key=colName(str), val=mcomp(set)) for modal complements
            of the input set. Sets that return their modal complements are those
            with no foreign pcs or in case of a hexachord, prime M.A.
            (i.e,. hexachords with one foreign pc).
        """
        card = len(pcsetObj)
        dct = {}
        if not (3 <= card <= 9):
            return dct
        mcomps = pcsetObj.modalComplements()
        for name in c.REF_COLS:
            col = c.COL_DICT[name]
            mcomp = mcomps[name]
            union = pcsetObj.getSet() | mcomp
            # (set with no foreign pc but not col) or (hexachord with one foreign pc)
            if ((union == col) and (len(mcomp) != 0)) \
                    or ((card == 6) and (len(union) == len(col) + 1)):
                dct[name] = mcomp
        return dct

    def setSummary(self, pcsetObj):
        """
        :param pcsetObj: a Pcset object for the input set.
        :return: a str of the summary of the input set as: "SN (Tn/TnI, M.A.)".
        """
        card = len(pcsetObj)
        if card == 0:
            return ""
        elif card == 1:
            nf = pcsetObj.normalForm()
            return str(nf[0])
        elif card == 2 or (10 <= card <= 12):
            nf = ",".join(str(pc) for pc in self.nf)
            return nf
        else:
            sn = MainWindow.setName(pcsetObj)
            lvl = MainWindow.transformationLevel(pcsetObj)
            matts = " ".join(self.modalAttributes(pcsetObj))
            if matts == "":
                summary = "{0} ({1})".format(sn, lvl)
            else:
                summary = "{0} ({1}, {2})".format(sn, lvl, matts)
            return summary

    # Display methods ---------------------------------------------------------

    def updateDisplay(self):
        """Updates the display widgets"""
        self.showNormalForm()
        self.showPrimeForm()
        self.showSetName()
        self.showICV()
        self.showTransformationLevel()
        self.showModalAttributes()
        self.showIndexVector()
        self.showLiteralComplement()
        self.showAbstractComplement()
        self.showZCorrespondent()
        self.showModalComplements()
        self.showSetSummary()
        self.showTargetSCMenu()
        self.showCollectionPCs()

    def resetDisplay(self):
        """Resets the display widgets"""
        self.resetPCBtns()
        self.ui.lineEditNF.clear()
        self.ui.lineEditPF.clear()
        self.ui.lineEditSN.clear()
        self.ui.lineEditICV.clear()
        self.ui.lineEditLevel.clear()
        self.ui.lineEditMA.clear()
        self.resetIVTable()
        self.ui.lineEditLComp.clear()
        self.ui.lineEditAComp.clear()
        self.ui.lineEditACompSN.clear()
        self.ui.lineEditZCorrPF.clear()
        self.ui.lineEditZCorrSN.clear()
        self.resetMCompTable()
        self.resetTn()
        self.resetTnI()
        self.ui.lineEditSetSummary.clear()
        self.resetTargetSCMenu()
        self.resetTargetSCMemberTable()
        self.ui.comboBoxNexus.setCurrentIndex(0)
        self.resetMSCTables()
        self.resetCollectionPCs()

    def showPCBtns(self):
        """Check the pcBtns with the updated pcset"""
        for pc in self.pcset:
            self.pcBtns[pc].setChecked(True)

    def showNormalForm(self):
        """Show the normal form of the updated pcset"""
        s = ",".join(str(pc) for pc in self.nf)
        self.ui.lineEditNF.setText(s)

    def showPrimeForm(self):
        """Show the prime form of the updated pcset"""
        pf = toPFStr(self.pf)
        self.ui.lineEditPF.setText(pf)

    def showSetName(self):
        """Show the set name of the updated pcset"""
        self.ui.lineEditSN.setText(self.sn)

    def showTransformationLevel(self):
        """Show the Tn/TnI transformation level of the updated pcset"""
        self.ui.lineEditLevel.setText(self.lvl)

    def showModalAttributes(self):
        """Show the modal attributes of the updated pcset"""
        s = " ".join(self.matts)
        self.ui.lineEditMA.setText(s)

    def showICV(self):
        """Show the ICV of the updated pcset"""
        s = "".join(str(ic) for ic in self.icv)
        self.ui.lineEditICV.setText(s)

    def showIndexVector(self):
        """Show the index vector of the updated pcset"""
        col = 0
        for item in self.ivTable:
            item.setText(str(self.iv[col]))
            col += 1

    def showLiteralComplement(self):
        """Show the literal complement of the updated pcset"""
        s = ",".join(str(pc) for pc in self.lcomp)
        self.ui.lineEditLComp.setText(s)

    def showAbstractComplement(self):
        """Show the abstract complement of the updated pcset"""
        # Show the prime form
        pf = toPFStr(self.acomp)
        self.ui.lineEditAComp.setText(pf)
        # Show the set name
        if not (3 <= len(pf) <= 9):
            self.ui.lineEditACompSN.clear()
        else:
            sn = catalog["PFToSN"][pf]
            self.ui.lineEditACompSN.setText(sn)

    def showZCorrespondent(self):
        """Show the Z-correspondent of the updated pcset"""
        # Show the set name
        self.ui.lineEditZCorrSN.setText(self.zcorr)
        # Show the prime form
        if self.zcorr == "":
            self.ui.lineEditZCorrPF.clear()
        else:
            pf = catalog["SC"][self.zcorr]["PF"]
            self.ui.lineEditZCorrPF.setText(pf)

    def showModalComplements(self):
        """
        Show the modal complements of the updated pcset.
        Display by setting str to the TableWidgetItems in self.mcompTable
        which is structured as a 3x3 table as:
            [[refCol, mcomp, SN],
             [refCol, mcomp, SN],
             [refCol, mcomp, SN]]
        """
        # Clear table before writing
        for i in range(3):
            for j in range(3):
                self.mcompTable[i][j].setText("")
        # Write to the table
        row = 0
        for name in c.REF_COLS:
            mcomp = self.mcomps.get(name)
            if mcomp is not None:
                nf = Pcset(mcomp).normalForm()
                nfStr = ",".join(str(pc) for pc in nf)
                pf = Pcset(mcomp).primeForm()
                self.mcompTable[row][0].setText(name)
                self.mcompTable[row][1].setText(nfStr)
                if len(nf) >= 3:
                    sn = catalog["PFToSN"][toPFStr(pf)]
                    self.mcompTable[row][2].setText(sn)
                row += 1

    def showSetSummary(self):
        """Show the summary of the updated set as SN (Tn/TnI, M.A.)"""
        self.ui.lineEditSetSummary.setText(self.summary)

    def showTargetSCMenu(self):
        """Update items in the combo box for target set classes"""
        menu = self.ui.comboBoxTargetSCs
        prev = menu.currentIndex()
        menu.clear()
        n = 0  # Menu index
        for card in range(3, 10):
            for ord_ in range(1, len(c.SN_VECS[card])):
                # Set name of this set class
                sn = c.SN_VECS[card][ord_]
                if not (3 <= self.card <= 9) or (self.card == card):
                    target = sn
                else:
                    # Inclusion count for this target set class
                    count = catalog["inclusionTable"][self.sn][str(card)][ord_-1]
                    target = "{0:5} ({1})".format(sn, count)
                menu.addItem(target)
                if self.card == card:
                    menu.model().item(n).setEnabled(False)
                n += 1
            menu.addItem("-"*15)
            menu.model().item(n).setEnabled(False)
            n += 1
        menu.removeItem(n-1)
        menu.setCurrentIndex(prev)

    def showMSCTables(self):
        """
        With the nexus set selected in the combobox, show the MSC members
        in the tables of respective cardinal numbers.
            [[SN, MA, sym, count, (Z-corr)],
             [SN, MA, sym, count, (Z-corr)],
             ...
             [SN, MA, sym, count, (Z-corr)]]
        """
        self.resetMSCTables()
        nexus = str(self.ui.comboBoxNexus.itemText(
            self.ui.comboBoxNexus.currentIndex()))
        for card in ["3", "4", "6"]:
            table = self.mscTables[card]
            # A list of dicts, each dict = a member
            members = catalog["MSC"][nexus][card]
            row = 0
            for member in members:
                table[row][0].setText(member["SN"])
                table[row][1].setText(" ".join(member["MA"]))
                table[row][2].setText(
                    ", ".join(str(i) for i in member["symmetry"]))
                table[row][3].setText(str(member["inclusion"]))
                if card != "3":
                    zcorr = member["Z-corr"]
                    if zcorr is None:
                        table[row][4].setText("")
                    else:
                        table[row][4].setText(zcorr)
                row += 1

    def setStyleSheetColLabels(self, label, state):
        """Sets stylesheet to the collection pc labels"""
        name = label.objectName()  # Object name
        # Set RGB for the background color
        mode = name[5]
        if mode == "O":
            rgb = [8, 25, 43]   # Blue
        elif mode == "W":
            rgb = [100, 92, 23]  # Yellow
        else:
            rgb = [81, 37, 37]  # Red
        # Set the foreground color and alpha channel for the background color
        if state == 1:
            if mode == "W":
                fgColor = "rgb(0, 0, 0)"
            else:
                fgColor = "rgb(243, 243, 243)"
            if label in self.colLabelsOuter:
                alpha = 25
            else:
                if mode == "O":
                    alpha = 60
                elif mode == "W":
                    alpha = 65
                else:
                    alpha = 70
        else:
            alpha = 0
            if label in self.colLabelsOuter:
                fgColor = "rgb(170, 170, 170)"
            else:
                fgColor = "rgb(0, 0, 0)"
        # Background color comprises rgb + a
        rgba = rgb + [alpha]
        bgColor = "rgba({0}%, {1}%, {2}%, {3}%)".format(*rgba)
        # Create style sheet
        style = "QLabel#{0} {{\n" \
                "font-size: 10px;\n" \
                "font-weight: bold;\n" \
                "qproperty-alignment: AlignCenter;\n" \
                "color: {1};\n" \
                "background-color: {2}\n}}\n".format(name, fgColor, bgColor)
        # Set stylesheet
        label.setStyleSheet(style)

    def showCollectionPCs(self):
        """Show the pc labels in referential collection displays"""
        for label in self.colLabelsInner + self.colLabelsOuter:
            pc = int(label.text())
            if pc in self.pcset:
                state = 1
            else:
                state = 0
            self.setStyleSheetColLabels(label, state)

    def resetPCBtns(self):
        """Uncheck all the pcBtns"""
        for b in self.pcBtns:
            b.setChecked(False)

    def resetIVTable(self):
        """Empty all the TableWidgetItems for index vector"""
        col = 0
        for item in self.ivTable:
            item.setText("")
            col += 1

    def resetMCompTable(self):
        """Empty all the TableWidgetItems for modal complements"""
        for i in range(3):
            for j in range(3):
                self.mcompTable[i][j].setText("")

    def resetTn(self):
        """Resets the widgets and instance variable for Tn operation"""
        self.ui.comboBoxTn.setCurrentIndex(0)
        self.ui.lineEditTn.clear()
        self.tn = []

    def resetTnI(self):
        """Resets the widgets and instance variable for TnI operation"""
        self.ui.comboBoxTnI.setCurrentIndex(0)
        self.ui.lineEditTnI.clear()
        self.tni = []

    def resetTargetSCMenu(self):
        """Add items to the combo box for inclusion target set classes"""
        menu = self.ui.comboBoxTargetSCs
        menu.clear()
        for card in range(3, 10):
            for ord_ in range(1, len(c.SN_VECS[card])):
                sn = c.SN_VECS[card][ord_]
                menu.addItem(sn)
            menu.addItem("-"*15)
            n = menu.count()
            menu.model().item(n-1).setEnabled(False)
        menu.removeItem(214)

    def resetTargetSCMemberTable(self):
        """Empty all the TableWidgetItems for target SC members"""
        for row in range(20):
            for col in range(5):
                self.targetSCMemberTable[row][col].setText("")

    def resetMSCTables(self):
        """Empty all the TableWidgetItems for MSC members"""
        for card in ["3", "4", "6"]:
            for row in range(7):
                for col in range(4):
                    self.mscTables[card][row][col].setText("")
                if card != "3":
                    self.mscTables[card][row][4].setText("")

    def resetCollectionPCs(self):
        """Resets the collection pc labels"""
        for label in self.colLabelsInner + self.colLabelsOuter:
            self.setStyleSheetColLabels(label, 0)

    # Operation methods -------------------------------------------------------

    def undo(self):
        """
        Undoes the previous operation: change the current pcset to that
        at the index 0 in the undo stack.
        """
        if len(self.undoStack) != 0:
            self.redoStack.insert(0, self.pcset)
            self.updatePCSet(self.undoStack.pop(0), archive=False)

    def redo(self):
        """
        Redoes the previously undone operation: change to the current pcset
        to that at the last index in the redo stack.
        """
        if len(self.redoStack) != 0:
            self.undoStack.insert(0, self.pcset)
            self.updatePCSet(self.redoStack.pop(0), archive=False)

    def resetOperations(self):
        """Resets the widgets and instance variables for operations"""
        self.resetTn()
        self.resetTnI()
        self.resetTargetSCMemberTable()

    def transpose(self):
        """Create Tn transformation from the current pcset"""
        n = self.ui.comboBoxTn.currentIndex()
        if (n == 0) or (self.card == 0):
            self.tn = []
            self.ui.lineEditTn.clear()
        else:
            copy = self.pcset.clone()
            self.tn = copy.opT(n).normalForm()
            s = ",".join(str(pc) for pc in self.tn)
            self.ui.lineEditTn.setText(s)

    def applyTn(self):
        """Update the current pcset with the Tn transformation"""
        if len(self.tn) != 0:
            self.updatePCSet(self.tn)

    def invert(self):
        """Create TnI transformation from the current set"""
        n = self.ui.comboBoxTnI.currentIndex() - 1
        if (n == -1) or (self.card == 0):
            self.ui.lineEditTnI.clear()
        else:
            copy = self.pcset.clone()
            self.tni = copy.opTnI(n).normalForm()
            s = ",".join(str(pc) for pc in self.tni)
            self.ui.lineEditTnI.setText(s)

    def applyTnI(self):
        """Update the current pcset with the TnI transformation"""
        if len(self.tni) != 0:
            self.updatePCSet(self.tni)

    def createTargetSCMembers(self):
        """
        With the set name selected in the combo box (target), create target SC
        members in the table.
        """
        sn = self.ui.comboBoxTargetSCs.currentText()
        if (sn[0] != "-") and (sn[0] != str(self.card)) and (
                1 <= self.card <= 11):
            self.resetTargetSCMemberTable()
            sn = str(sn).split()[0]
            pf = fromPFStr(catalog["SC"][sn]["PF"])
            members = []
            if len(pf) < self.card:
                members = self.pcset.inclusion(pf)
            elif len(pf) > self.card:
                members = self.pcset.complementation(pf)
            # members is a variable for the target SC members: it is a list
            # of tuples, each tuple contains two sets ({memberPCs}, {diffPCs}).
            if members:
                row = 0
                for member, diff in members:
                    m, d = Pcset(member), Pcset(diff)
                    memberNF = ",".join(str(pc) for pc in m.normalForm())
                    memberLvl = MainWindow.transformationLevel(m)
                    memberMA = " ".join(self.modalAttributes(m))
                    diffNF = ",".join(str(pc) for pc in d.normalForm())
                    if len(d) < 3:
                        diffInfo = ""
                    else:
                        diffInfo = self.setSummary(d)
                    # tableRow = [incl/comp, Tn/TnI, MA, diff, diffInfo]
                    self.targetSCMemberTable[row][0].setText(memberNF)
                    self.targetSCMemberTable[row][1].setText(memberLvl)
                    self.targetSCMemberTable[row][2].setText(memberMA)
                    self.targetSCMemberTable[row][3].setText(diffNF)
                    self.targetSCMemberTable[row][4].setText(diffInfo)
                    row += 1

    def changeToTargetSCMember(self, n):
        """
        Change the current pcset to the selected member of the target
        SC in the table.

        :param n: an int for the clicked vertical header index.
        """
        nfStr = str(self.targetSCMemberTable[n][0].text())
        if nfStr:
            nf = [int(i) for i in nfStr.split(",")]
            self.updatePCSet(nf)

    def findMSCSCMembers(self, table, row, col):
        """
        With the set name selected in the MSC table, create its SC
        members in the table.

        :param table: a Table widget in which the target set is selected.
        :param row: an int for the row of the selected table cell.
        :param col: an int for the col of the selected table cell.
        """
        item = table.item(row, 0)
        sn = item.text()
        if self.card != 0 and self.card != int(sn[0]):
            index = self.ui.comboBoxTargetSCs.findText(sn,
                                                       QtCore.Qt.MatchFlag.MatchContains)
            self.ui.comboBoxTargetSCs.setCurrentIndex(index)
            self.createTargetSCMembers()


class ConnectionDialog(QtWidgets.QDialog):
    """
    A dialog object for MIDI input port and UDP port settings.
    """

    # Custom Qt signal
    message = QtCore.pyqtSignal(int, int)

    def __init__(self, midiInPorts, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = Ui_ConnectionDialog()
        self.ui.setupUi(self)
        self.MIDIInPortIndex = 0
        self.UDPPortIndex = 0
        # Populate MIDI input ports in the menu
        for device in midiInPorts:
            self.ui.comboBoxMIDIInPort.addItem(device)
        # Signal-slot connections
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def setMIDIInPortMenu(self, n):
        """Sets the MIDI input port menu to the index n"""
        self.MIDIInPortIndex = n
        self.ui.comboBoxMIDIInPort.setCurrentIndex(self.MIDIInPortIndex)

    def setUDPPortMenu(self, n):
        """Sets the UDP port menu with the index n"""
        self.UDPPortIndex = n - 3000
        self.ui.comboBoxUDPPort.setCurrentIndex(self.UDPPortIndex)

    def accept(self):
        """
        Overridden method for accept(): emits signal to effect the port changes
        and save the settings as preferences in MainWindow(), then hide this dialog.
        """
        self.MIDIInPortIndex = self.ui.comboBoxMIDIInPort.currentIndex()
        self.UDPPortIndex = self.ui.comboBoxUDPPort.currentIndex()
        midiInPort, udpPort = self.MIDIInPortIndex, self.UDPPortIndex + 3000
        self.message.emit(midiInPort, udpPort)
        self.hide()

    def reject(self):
        """
        Overridden method for reject(): reverts the combobox selections and
        do nothing else.
        """
        self.ui.comboBoxMIDIInPort.setCurrentIndex(self.MIDIInPortIndex)
        self.ui.comboBoxUDPPort.setCurrentIndex(self.UDPPortIndex)
        self.hide()


class WorkerMIDI(QtCore.QThread):
    """
    Class to handle real-time MIDI inputs (i.e., notes and damper).
    Input channel is fixed to ch. 1.

    Sustain is a non-public feature which I personally use with cc 11 with
    reversed values (i.e., pedal completely off = 127, on = 0).
    """

    # Custom Qt signal
    message = QtCore.pyqtSignal(int, bool)

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.pitchStates = [False] * 127
        self.midiin = rtmidi.MidiIn()  # Create a MidiIn object
        self.ports = self.midiin.get_ports()  # Get MIDI input ports

    def setInputPort(self, n):
        """"Sets MIDI input device"""
        self.midiin.close_port()
        if not self.ports:
            print("There is no MIDI input device connected.")
            return
        self.midiin.open_port(n)
        print(f"Set MIDI input port to {self.ports[n]}")

    def getInputPorts(self):
        """Returns available MIDI input ports"""
        return self.ports

    def checkPCMembers(self, pitch):
        """
        Check the presence of the pc members of the pitch.

        :param pitch: an int for pitch.
        """
        pc = pitch % 12
        pitches = {12 * octave + pc for octave in range(10)}
        pitches -= {pitch}  # All the pc members of the pitch but itself
        state = False
        for p in pitches:
            state += self.pitchStates[p]
        return state

    def setStates(self, pitch, state):
        """
        Sets the pitch state in this class, and pc state in MainWindow() class.
        The method does not execute the change of pc state, if any other pc members
        of the pitch is present. This will avoid unnecessary consumption of CPU power.

        :param pitch: an int for the pitch.
        :param state: a bool for the states.
        """
        self.pitchStates[pitch] = state
        if not self.checkPCMembers(pitch):
            self.message.emit(pitch % 12, state)

    def run(self):
        """
        Work thread process for parsing MIDI input data and generate pc input.
        Update of the instance variable, pcset, in the main thread MainWindow()
        object is made through the custom Qt signal defined here.
        """
        noteOffs = set([])    # Pitches for suspended note-off messages
        sustainState = False  # Damper pedal (sustain) status
        # MIDI event loop
        while True:
            events = []
            # Consolidate all the event data from the ring buffer
            while True:
                poll = self.midiin.get_message()  # poll = ([message], deltaTime)
                if poll is None:
                    break
                events.append(poll[0])
            # Iterate through events
            if events:
                for msg in events:  # msg = [status, data1, data2]
                    # Sustain input
                    if msg[0] == STATUS_BYTE_CONTROL_CHANGE and msg[1] == CC_SUSTAIN:
                        prev, current = sustainState, bool(msg[2] < SUSTAIN_THRESH)
                        # Release the buffered note-offs if sustain state changes from True to False
                        if prev and not current:
                            for pitch in noteOffs:
                                self.setStates(pitch, False)
                            noteOffs.clear()
                        sustainState = current  # Update sustain state
                    # Note input
                    if msg[0] == STATUS_BYTE_NOTE_ON:
                        pitch, state = msg[1], bool(msg[2])
                        # Note on
                        if state:
                            self.setStates(pitch, True)
                        # Note off
                        else:
                            # Catch and buffer note-off messages if sustainState is True
                            if sustainState:
                                noteOffs |= {pitch}
                            else:
                                self.setStates(pitch, False)
            # Process buffered MIDI messages at every MIDI_MESSAGE_POLL_INTERVAL ms
            self.msleep(MIDI_MESSAGE_POLL_INTERVAL)


class WorkerOSC(QtCore.QThread):
    """Class to handle OSC message for pc input."""

    # Custom Qt signal
    message = QtCore.pyqtSignal(set)

    def __init__(self, udpPort, parent=None):
        QtCore.QThread.__init__(self, parent)
        print("Starting OSC server (receive at port {})...".format(udpPort))
        self.server = OSCThreadServer()
        self.socket = self.server.listen(address=SERVER_ADDRESS,
                                         port=udpPort, default=True)
        self.server.bind(OSC_ADDRESS, self.noteHandler)

    def noteHandler(self, *data):
        """
        Note data from NAP in a list such as [74, 69, 76, 62].

        :param data: a list containing note data
        """
        pcs = {note % 12 for note in data}
        self.message.emit(pcs)

    def close(self):
        """Closes the server socket"""
        print("Closing OSC server...")
        self.server.stop(self.socket)

    def changePort(self, newPort):
        """Change the server port to a newPort."""
        # Close port
        self.server.stop(self.socket)
        # Terminate the entire server
        #   self.server.listen with newPort does not work
        self.server.terminate_server()
        # Wait for the server thread to finish
        self.server.join_server()
        # Wait for the server to close
        time.sleep(0.1)
        # Reinitialize the server
        self.server = OSCThreadServer()
        # Listen on the new port
        self.socket = self.server.listen(address=SERVER_ADDRESS,
                                         port=newPort, default=True)
        # Re-bind the server to handle incoming OSC messages
        self.server.bind(OSC_ADDRESS, self.noteHandler)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    form = MainWindow()
    form.startWorkerMIDI()
    form.startWorkerOSC()
    form.show()
    app.aboutToQuit.connect(form.closeServerSocket)
    sys.exit(app.exec())
