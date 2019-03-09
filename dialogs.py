import sys
import numpy as np
from scipy import signal
import scipy.io
import matplotlib.pyplot as plt
from PySide2.QtWidgets import (QDialog, QComboBox, QGridLayout, QLabel,
                               QHBoxLayout, QGroupBox, QFormLayout,
                               QLineEdit, QFrame, QSpinBox, QDialogButtonBox,
                               QPushButton, QVBoxLayout, QStackedLayout,
                               QFileDialog, QWidget, QCheckBox,
                               QErrorMessage, QProgressBar)
from PySide2.QtCore import Qt, Signal
from chartView import *
from dataProcessing import *
from data import *


'''

################## DATA PROCESSING ##################

'''
class DataProcessingDialog(QDialog):

    '''
    Signals
    '''
    newDataAdded = Signal(str, str, str)
    dataChanged = Signal(str, str, str)
    
    def __init__(self, dataManager, parent=None, inputList=None):
        self.operations = {'Filtering': [FilterGroup, 'Filter settings', -1],
                             'Average': [AverageGroup, 'Window settings', -1],
                              'Energy': [EnergyGroup, 'Window settings', -1],
                               'Power': [PowerGroup, 'Window settings', -1],
                        'Peak-To-Peak': [Peak2PeakGroup, 'Window settings', -1],
                            'Variance': [VarianceGroup, 'Window settings', -1],
                             'Entropy': [EntropyGroup, 'Window settings', -1],
                            'Skewness': [SkewnessGroup, 'Window settings', -1],
                        'Thresholding': [ThresholdGroup, 'Settings', -1],
                             'Detrend': [DetrendGroup, 'Settings', -1],
                                'STFT': [STFTGroup, 'Spectrum settings', -1],
                                 'CWT': [CWTGroup, 'CWT settings', -1]}
        QDialog.__init__(self, parent)
        self.dataManager = dataManager
        self.setWindowTitle('Data Processing')
        self.inputList = inputList
        
        #Setup Layouts
        self.mainLayout = QGridLayout(self)
        self.setupInLayout()
        self.setupProcessLayout()
        self.setupOutLayout()
        self.setupBtnBoxLayout()

    '''
    Input Layout
    '''
    def setupInLayout(self):
        inGroup = QGroupBox('Input to process')
        inLayout = QFormLayout(inGroup)

        self.inTree = DataSelector(self.dataManager, inputList=self.inputList)
        
        self.operChooser = QComboBox()
        [self.operChooser.addItem(i) for i in self.operations]
        self.operChooser.currentTextChanged.connect(self.setOperation)
        inLayout.addRow(QLabel('Select Input'))
        inLayout.addRow(self.inTree)
        inLayout.addRow(QLabel('Operation'), self.operChooser)

        self.mainLayout.addWidget(inGroup, 0, 0)

    def setOperation(self):
        print('Set Operation')
        index = self.operations[self.operChooser.currentText()][2]
        self.processLayout.setCurrentIndex(index)

    '''
    Signal Processing Settings Layout
    '''
    def setupProcessLayout(self):
        processGroup = QGroupBox('Processing settings')
        self.processLayout = QStackedLayout()
        self.mainLayout.addLayout(self.processLayout, 1, 0)

        # Setup Processing Sublayouts
        for op in self.operations:
            index = self.createGroup(self.operations[op][0], op, self.operations[op][1])
            self.operations[op][2] = index   

    '''
    Create Groups
    '''
    def createGroup(self, GroupClass, name, title):
        newGroup = GroupClass(title, fs=self.dataManager.getFs())
        newGroup.progress.connect(self.updateProgress)
        index = self.processLayout.addWidget(newGroup)
        return index

    '''
    Output Layout
    '''
    def setupOutLayout(self):
        outGroup = QGroupBox('Output')
        outLayout = QFormLayout(outGroup)
        self.outNameEdit = QLineEdit()
        inAsOutCheck = QCheckBox('Replace input')
        inAsOutCheck.toggled.connect(self.setInputAsOutput)
        outLayout.addWidget(inAsOutCheck)
        outLayout.addRow('Output name', self.outNameEdit)
        self.mainLayout.addWidget(outGroup, 2, 0)

    def setInputAsOutput(self, isOn):
        if isOn:
            inStruct = self.inTree.getSelectedStruct()
            wName = list(inStruct.keys())[0]
            gName = list(inStruct[wName].keys())[0]
            self.outNameEdit.setText(gName)
            self.outNameEdit.setDisabled(True)
        else:
            self.outNameEdit.setEnabled(True)

    '''
    Button Box Layout
    '''
    def setupBtnBoxLayout(self):
        bottomLayout = QHBoxLayout()
        self.progBar = QProgressBar()
        self.progBar.setVisible(False)
        bottomLayout.addWidget(self.progBar)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Close)
        buttonBox.accepted.connect(self.okBtnBox)
        buttonBox.rejected.connect(self.close)
        bottomLayout.addWidget(buttonBox)
        self.mainLayout.addLayout(bottomLayout, 3, 0)

    def okBtnBox(self):
        inStruct = self.inTree.getSelectedStruct()
        data = self.dataManager.getData(inStruct, inv=True)
        wName = list(data.keys())[0]
        gName = list(data[wName].keys())[0]
        outName = self.outNameEdit.text()

        if outName in self.dataManager[wName].getColumnNames():
            msgBox = QMessageBox()
            msgBox.setText('Signal already exists')
            msgBox.setInformativeText("Do you want to replace it?");
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel);
            msgBox.setDefaultButton(QMessageBox.Ok);
            ret = msgBox.exec()
            if ret == QMessageBox.Ok:
                self.dataManager.removeSignal(wName, outName)
                print('removed')
            else:
                return
                       
        self.progBar.setVisible(True)
        outData = self.processLayout.currentWidget().process(data[wName][gName])
        self.dataManager.appendSignal(wName, outName, inStruct[wName][gName], outData)
        self.newDataAdded.emit(wName, gName, self.outNameEdit.text())


    def updateProgress(self, prog):
            self.progBar.setValue(prog)
