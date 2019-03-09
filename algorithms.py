import sys
import time
import numpy as np
from scipy import signal
from PySide2.QtWidgets import (QDialog, QComboBox, QGridLayout, QLabel,
                               QHBoxLayout, QGroupBox, QFormLayout,
                               QLineEdit, QFrame, QSpinBox, QDialogButtonBox,
                               QPushButton, QVBoxLayout, QStackedLayout,
                               QErrorMessage, QProgressBar, QCheckBox,
                               QDoubleSpinBox)
from PySide2.QtCore import Qt, QObject, Signal
from data import *
from calculations import *
from copy import deepcopy
import csv

class FirstAlgorithm(QDialog):

    executed = Signal(dict, list)

    defaultParameters = {'offset filter' : True,
                         'supply filter' : True,
                         'LPF highcut'   : 3,
                         'BPF lowcut'    : 8,
                         'BPF highcut'   : 30,
                         'art thres'     : 100,
                         'window'        : 25,
                         'prev sec'      : 5,
                         'hmt larger'    : 3,
                         'hmt larger mean' : 2,
                        }
    
    def __init__(self, dataManager, chartManager, parent=None, inputList=None, initParam=None):
        QDialog.__init__(self, parent)

        self.dataManager = dataManager
        self.fs = self.dataManager.getFs()
        self.chartManager = chartManager
        self.setWindowTitle('Algorithms')
        self.inputList = inputList
        if initParam:
            self.parameters = initParam
            print('initParam')
        else:
            self.parameters = self.defaultParameters
            print('defaultParameters')
        
        #Setup Layouts
        self.mainLayout = QVBoxLayout(self)
        self.setupInLayout()

        self.setupSettings()

        self.setupBtnBoxLayout()

        

    def setupInLayout(self):
        inGroup = QGroupBox('Input to process')
        inLayout = QFormLayout(inGroup)

        self.inTree = DataSelector(self.dataManager, inputList=self.inputList)

        inLayout.addWidget(QLabel('Select Input'))
        inLayout.addWidget(self.inTree)

        self.mainLayout.addWidget(inGroup)

    def setupSettings(self):
       
        spinBoxLayout = QFormLayout()

        self.removeOffset = QCheckBox('Remove DC offset')
        self.removeOffset.setChecked(self.parameters['offset filter'])
        spinBoxLayout.addRow(self.removeOffset)

        self.removeSupply = QCheckBox('Remove 50Hz')
        self.removeSupply.setChecked(self.parameters['supply filter'])
        spinBoxLayout.addRow(self.removeSupply)

##        self.lpfHighcut = QSpinBox()
##        self.lpfHighcut.setMaximum(10000)
##        self.lpfHighcut.setValue(self.parameters['LPF highcut'])
##        spinBoxLayout.addRow('LPF highcut frequency:', self.lpfHighcut)

        self.bpfLowcut = QSpinBox()
        self.bpfLowcut.setMaximum(10000)
        self.bpfLowcut.setValue(self.parameters['BPF lowcut']) 
        spinBoxLayout.addRow('BPF lowcut frequency:', self.bpfLowcut)

        self.bpfHighcut = QSpinBox()
        self.bpfHighcut.setMaximum(10000)
        self.bpfHighcut.setValue(self.parameters['BPF highcut'])
        spinBoxLayout.addRow('BPF highcut frequency:', self.bpfHighcut)
        
##        self.ArtefactsThreshold = QSpinBox()
##        self.ArtefactsThreshold.setMaximum(10000)
##        self.ArtefactsThreshold.setValue(self.parameters['art thres'])
##        spinBoxLayout.addRow('Artefacts Threshold:', self.ArtefactsThreshold)
        
        self.algWindowSize = QSpinBox()
        self.algWindowSize.setMaximum(10000)
        self.algWindowSize.setValue(self.parameters['window'])
        spinBoxLayout.addRow('Window (samples):', self.algWindowSize)

        self.hmtLargerMean = QDoubleSpinBox()
        self.hmtLargerMean.setMinimum(0.1)
        self.hmtLargerMean.setMaximum(10000)
        self.hmtLargerMean.setValue(self.parameters['hmt larger mean'])
        spinBoxLayout.addRow('How many times larger than mean:', self.hmtLargerMean)

        self.prevSeconds = QDoubleSpinBox()
        self.prevSeconds.setMinimum(0.1)
        self.prevSeconds.setMaximum(10000)
        self.prevSeconds.setValue(self.parameters['prev sec'])
        spinBoxLayout.addRow('Number of previous seconds:', self.prevSeconds)

        self.hmtLarger = QDoubleSpinBox()
        self.hmtLarger.setMinimum(0.1)
        self.hmtLarger.setMaximum(10000)
        self.hmtLarger.setValue(self.parameters['hmt larger'])
        spinBoxLayout.addRow('How many times larger than previous:', self.hmtLarger)

        gBox = QGroupBox('Settings')
        gBox.setLayout(spinBoxLayout)
        self.mainLayout.addWidget(gBox)
        

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
        self.mainLayout.addLayout(bottomLayout)

    def okBtnBox(self):
        inStruct = self.inTree.getSelectedStruct()
        inDataStruct = self.dataManager.getData(inStruct, inv=True)

        self.progBar.setVisible(True)
        self.progBar.setValue(0)
        nProgres = 5
        progStep = 100.0/nProgres
        progress = 0
        
        wName = list(inDataStruct.keys())[0]
        gName = list(inDataStruct[wName].keys())[0]
        
        ## Input
        inData = np.copy(inDataStruct[wName][gName])

        ## Noises
        if self.removeOffset.isChecked():
            inData = [signal.detrend(data, type='constant') for data in inData]

        if self.removeSupply.isChecked():
            b, a = filterCalc(order=5,
                          bandarr=[48, 52],
                          fs=self.fs,
                          btype='bandstop',
                          ftype='butter')
            inData = [signal.lfilter(b, a, data) for data in inData]
            
        winLen = self.algWindowSize.value()
        
##        ## Artefacts
##        lpfHighcut = self.lpfHighcut.value()
##        order=5
##        
##        b, a = filterCalc(order, [lpfHighcut], self.fs, 'low', 'butter')
##        lpfData = []
##        for data in inData:
##            newData = signal.lfilter(b, a, data)
##            lpfData.append(newData)
##
##        
##
##        segNmbr = int(np.shape(lpfData)[1]/winLen)
##        artefactsThreshold = self.ArtefactsThreshold.value()
##
##        lpfWinData = np.copy(lpfData)
##        lpfWinData = [np.array_split(ch, segNmbr) for ch in lpfWinData]
##
##        for ch in lpfWinData:
##            for seg in ch:
##                seg.fill(max(seg)- min(seg))
##
        progress += progStep
        self.progBar.setValue(progress)
##    
####        thresLpfData = np.copy(lpfWinData)
##        thresLpfData = deepcopy(lpfWinData)
##        
##        for x in thresLpfData:
##            for y in x:
##                if y[0] >= artefactsThreshold:
##                    y.fill(1)
##                else:
##                    y.fill(0)
##
##        lpfWinData = [np.concatenate(ch) for ch in lpfWinData]
##        thresLpfData = [np.concatenate(ch) for ch in thresLpfData]
##
        progress += progStep
        self.progBar.setValue(progress)
            

        ## Spikes
        bpfLowcut = self.bpfLowcut.value()
        bpfHighcut = self.bpfHighcut.value()
        order=4
        b, a = filterCalc(order, [bpfLowcut, bpfHighcut], self.fs, 'band', 'butter')
        bpfData = []
        for data in inData:
            newData = signal.lfilter(b, a, data)
            bpfData.append(newData)

        segNmbr = int(np.shape(bpfData)[1]/winLen)

        prevSeconds = self.prevSeconds.value()
        prevWindows = int(prevSeconds*self.fs/winLen)

        progress += progStep
        self.progBar.setValue(progress)

        bpfWinData = np.copy(bpfData)
        bpfWinData = [np.array_split(ch, segNmbr) for ch in bpfWinData]
        chi = 0
        for ch in bpfWinData:
            for seg in ch:
                seg.fill(max(seg)- min(seg))

        progress += progStep
        self.progBar.setValue(progress)

        hmtLarger = self.hmtLarger.value()
        hmtLargerMean = self.hmtLargerMean.value()
##        thresBpfData = np.copy(bpfWinData)
        thresBpfData = deepcopy(bpfWinData)
        
        for ch in range(len(bpfWinData)):
            channelMean = self.hmtLargerMean.value()*np.mean(inData[ch])
            for i in range(prevWindows, len(bpfWinData[ch])):
                if bpfWinData[ch][i][0] > channelMean:
                    prev = [bpfWinData[ch][j][0] for j in range(i-prevWindows,i)]
                    if bpfWinData[ch][i][0] > hmtLarger*np.mean(prev):
                        thresBpfData[ch][i].fill(1)
                    else:
                        thresBpfData[ch][i].fill(0)
                else:
                    thresBpfData[ch][i].fill(0)
        
        progress += progStep
        self.progBar.setValue(progress)
        
        for ch in thresBpfData:
            for i in range(prevWindows):
                ch[i].fill(0)
    

        bpfWinData = [np.concatenate(ch) for ch in bpfWinData]
        thresBpfData = [np.concatenate(ch) for ch in thresBpfData]

        spikeMap = [np.sum(x)/winLen for x in thresBpfData]
        nazwaPliku = str(winLen) + '_' + str(prevSeconds) + '_' + str(hmtLarger) + '.csv'
        with open(nazwaPliku, 'w', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(spikeMap)
##        for ch in spikeMap
##            csvwriter.writerow(spikeMap)

        ## Add data or replace existing
        swsName = 'Algorithm output'
        chNames = inStruct[wName][gName]
        if swsName not in self.dataManager.getDataGroups():
            self.dataManager.createDataGroup(swsName, 'Algorithm')
            self.dataManager.addChannels(swsName, chNames)
            
            self.dataManager.addSignal(swsName, 'Input Signal', inData, chNames)
##            self.dataManager.addSignal(swsName, 'LPF', lpfData, chNames)
##            self.dataManager.addSignal(swsName, 'LPF+Window+Peak-to-peak', lpfWinData, chNames)
##            self.dataManager.addSignal(swsName, 'LPF+Threshold - Artefacts', thresLpfData, chNames)
            self.dataManager.addSignal(swsName, 'BPF', bpfData, chNames)
            self.dataManager.addSignal(swsName, 'BPF+Window+Peak-to-peak', bpfWinData, chNames)
            self.dataManager.addSignal(swsName, 'BPF+Threshold - Spikes', thresBpfData, chNames)
        else:
            self.dataManager.silentChangeSignal(swsName, 'Input Signal', inData, chNames)
##            self.dataManager.silentChangeSignal(swsName, 'LPF', lpfData, chNames)
##            self.dataManager.silentChangeSignal(swsName, 'LPF+Window+P2P', lpfWinData, chNames)
##            self.dataManager.silentChangeSignal(swsName, 'LPF+Threshold - Artefacts', thresLpfData, chNames)
            self.dataManager.silentChangeSignal(swsName, 'BPF', bpfData, chNames)
            self.dataManager.silentChangeSignal(swsName, 'BPF+Window+Peak-to-peak', bpfWinData, chNames)
            self.dataManager.silentChangeSignal(swsName, 'BPF+Threshold - Spikes', thresBpfData, chNames)

        self.chartManager.setMask('Algorithm output', 'BPF+Threshold - Spikes')
        self.chartManager.setMap(spikeMap)
        self.parameters = {'offset filter' : self.removeOffset.isChecked(),
                           'supply filter' : self.removeSupply.isChecked(),
##                           'LPF highcut'   : lpfHighcut,
                           'BPF lowcut'    : bpfLowcut,
                           'BPF highcut'   : bpfHighcut,
##                           'art thres'     : artefactsThreshold,
                           'window'        : winLen,
                           'prev sec'      : prevSeconds,
                           'hmt larger'    : hmtLarger,
                           'hmt larger mean'    : hmtLargerMean,
                            }
        self.executed.emit(self.parameters, self.inputList)

class AlgorithmsManager(QObject):
    def __init__(self, dataManager, chartManager):
        self.dataManager = dataManager
        self.chartManager = chartManager
        self.usedParam = None
        self.inputList = None

    def showAlgorithmDialog(self, ws=None, signal=None):
        dialog = FirstAlgorithm(self.dataManager, self.chartManager, inputList=[ws, signal],
                                initParam = self.usedParam)
        dialog.executed.connect(self._saveUsedParam)
        dialog.show()
        dialog.exec()

    def adjustAlogrithmParameters(self, wsName):
        dialog = FirstAlgorithm(self.dataManager, self.chartManager,
                                inputList=self.inputList, initParam = self.usedParam)
        dialog.executed.connect(self._saveUsedParam)
        dialog.show()
        dialog.exec()

    def _saveUsedParam(self, newParam, inputList):
        self.usedParam = newParam
        self.inputList = inputList
    

        
