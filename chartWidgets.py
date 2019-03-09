from PySide2 import QtCore
from PySide2.QtWidgets import (QApplication, QMainWindow, QAction, QListWidget,
                               QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                               QTreeWidgetItemIterator, QScrollBar,
                               QDialog, QListWidgetItem, QPushButton, QInputDialog,
                               QMenu, QComboBox, QFormLayout, QDockWidget,
                               QAbstractItemView, QGroupBox, QLabel, QColorDialog)
from PySide2.QtGui import (QIcon, QColor, QBrush, QDrag, QPalette, QFont,
                           QLinearGradient )
from PySide2.QtCore import Qt, QObject, Signal, QTimer
from chartView import MyMPLChart
from chartTools import MPLNavigationToolbar, Cursor
from chartData import ChartDataManager
from dialogs import DataProcessingDialog
from algorithms import FirstAlgorithm
import numpy as np
import matplotlib.pyplot as plt


'''

################## CHART TOOLS ##################

'''
class ChartTools(QWidget):
    def __init__(self, chm, algManager, parent=None):
        QWidget.__init__(self, parent)

        self.mainLay = QVBoxLayout(self)

        self.scrollLay = QFormLayout(self)
        self.mainLay.addLayout(self.scrollLay)
        
        self.scrollStepChooser = chm.createScrollStepChooser()
        self.scrollLay.addRow('Scroll Step', self.scrollStepChooser)

        viewRangeChooser = chm.createViewRangeChooser()
        self.scrollLay.addRow('View Range', viewRangeChooser)

        self.chartTimer = QTimer()
        self.chartTimer.timeout.connect(chm.getChart().scrollForward)

        options = {'x1' : 1000,
                   'x2' : 500,
                   'x4' : 250,
                   'x8' : 125}
        self.updateChooser = Chooser(options)
        self.updateChooser.setCurrentText('x1')
        self.chartTimer.setInterval(self.updateChooser.getCurrentValue())
        self.updateChooser.currentValueChanged.connect(self.chartTimer.setInterval)
        self.scrollLay.addRow('Updates Per Sec', self.updateChooser)
        
        self.startBtn = QPushButton('Run')
        self.startBtn.setCheckable(True)
        self.a = QAction('SCROLL')
        self.startBtn.addAction(self.a)
        self.a.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_Space)
        self.a.setCheckable(True)
        self.a.triggered.connect(self.startBtn.toggle)
        self.startBtn.toggled.connect(self.setAutoscroller)
        self.scrollLay.addRow(self.startBtn)
        

        chartSelector = chm.createSelector(algManager)
        self.mainLay.addWidget(chartSelector)

    def setAutoscroller(self, newState):
        if newState:
            self.chartTimer.start()
            self.startBtn.setText('Stop')
        else:
            self.chartTimer.stop()
            self.startBtn.setText('Run')

'''

################## CHART MANAGER ##################

'''
class MyChartManager(QObject):
    def __init__(self, dataManager, parent=None):
        QObject.__init__(self, parent)
        self.dManager = dataManager
        self.fs = self.dManager.getFs()
        self.mChart = MyMPLChart()
        self.mChart.setXScale(self.fs)
        self.scroller = None
        self.mask = None
        self.spikeMap = None

    def createToolbar(self):
        self.toolbar = MPLNavigationToolbar(self.mChart)
        return self.toolbar

    def createSelector(self, algManager):
        self.chartData = ChartDataManager(self.dManager)
        self.selector = DataToDrawSelector(self.dManager, self.chartData, self, algManager)
        self.selector.newChannelSelected.connect(self.drawChannelFromStruct)
        self.selector.newSignalSelected.connect(self.drawSignalsFromStruct)
        self.selector.newMaskSelected.connect(self.setMask)
        return self.selector

    def createScrollBar(self):
        self.scroller = ChartScroller(self.mChart, Qt.Horizontal)
        return self.scroller

    def createScrollStepChooser(self):
        options = {'1 sec' : 1*self.fs,
                   '2 sec' : 2*self.fs,
                   '4 sec' : 4*self.fs,
                   '8 sec': 8*self.fs,
                   '16 sec': 16*self.fs,
                   '32 sec': 32*self.fs}
        sStepChooser = Chooser(options)
        sStepChooser.setCurrentText('2 sec')
        self.mChart.setScrollStep(sStepChooser.getCurrentValue())
        sStepChooser.currentValueChanged.connect(self.mChart.setScrollStep)
        return sStepChooser

    def createViewRangeChooser(self):
        options = {'2 sec' : 2*self.fs,
                   '5 sec' : 5*self.fs,
                   '10 sec' : 10*self.fs,
                   '20 sec' : 20*self.fs,
                   '40 sec' : 40*self.fs,
                   '60 sec' : 60*self.fs,
                   '120 sec': 120*self.fs,
                   }
        vRangeChooser = Chooser(options)
        vRangeChooser.setCurrentText('20 sec')
        self.mChart.setViewRange(vRangeChooser.getCurrentValue())
        vRangeChooser.currentValueChanged.connect(self.mChart.setViewRange)
        return vRangeChooser


    def getChart(self):
        return self.mChart

    def setXRange(self, xmin, xmax):
        self.mChart.setXRange(xmin, xmax)
        
    def drawChannelFromStruct(self, dataGroup, channel, dataToDraw):
        signals = list(dataToDraw.keys())
        colors = []
        chChData = self.chartData[dataGroup].getDataFromStructure({channel : signals}, inv=False)[channel]
        i = 0
        for d in dataToDraw:
            if chChData[i][0] == True:      #Signal
                dataNames = [chChData[i][3]]
                colors.append(chChData[i][4])
            else:                           #Group
                dataNames = chChData[i][2]
                gSData = self.chartData[dataGroup].getDataFromStructure({channel : dataNames}, inv=False)[channel]
                for gs in gSData:
                    colors.append(gs[4])
            dataToDraw[d] = {dName : None  for dName in dataNames}
            i += 1

        signals = []
        for d in dataToDraw:
            for k in list(dataToDraw[d].keys()):
                signals.append(k)


        chData = self.dManager[dataGroup].getDataFromStructure({channel : signals}, inv=False)[channel]
        i = 0
        for d in dataToDraw:
            for k in list(dataToDraw[d].keys()):
                dataToDraw[d][k] = chData[i]
                i = i+1
             
        chMask = None
        chMaskColor = None
        if self.mask:
            chMask = self.dManager[self.mask[0]].getDataFromStructure({channel : [self.mask[1]]}, inv=False)[channel]
            chMask = chMask[0]
            chMaskColor = self.chartData[self.mask[0]].getDataFromStructure({channel : [self.mask[1]]}, inv=False)[channel][0][4]
        self.mChart.drawOneChannel(dataToDraw, channel, mask=chMask, colors=colors, maskColor=chMaskColor)
        
    def drawSignalsFromStruct(self, dataGroup, signal, dataToDraw):
        channels = list(dataToDraw.keys())
        sChData = self.chartData[dataGroup].getDataFromStructure({signal : [channels[0]]}, inv=True)[signal]
        color = sChData[0][4]
        sData = self.dManager[dataGroup].getDataFromStructure({signal : channels}, inv=True)[signal]
        i = 0
        for d in dataToDraw:
            dataToDraw[d] = sData[i]
            i = i+1
        sMask = None
        sMaskColor = None
        if self.mask:
            sMask = self.dManager[self.mask[0]].getDataFromStructure({self.mask[1] : channels}, inv=True)[self.mask[1]]
            sMaskColor = self.chartData[self.mask[0]].getDataFromStructure({self.mask[1] : channels}, inv=True)[self.mask[1]][0][4]
        self.mChart.drawAllChannels(dataToDraw, signal, mask=sMask, color=color, maskColor=sMaskColor)

    def setMask(self, dataGroup, signal):
        self.mask = [dataGroup, signal]

    def setMap(self, spikeMap):
        self.spikeMap = spikeMap

    def showMap(self):
        if self.spikeMap is not None:
            fig = plt.figure("Spikes frequency")
            axes = plt.axes()
            fig.add_axes(axes)
            p = axes.pcolormesh(np.reshape(self.spikeMap, (5, 4), order='F'), cmap='bone')
            axes.invert_yaxis() 
            clb = plt.colorbar(p)
            clb.ax.set_title('Number of \ndetected spikes', fontdict = {'fontsize' : 10})
            plt.show()
        
        '''
        keys = ['CH1', 'CH2', 'CH3', 'CH4']
        sData = self.dManager[self.activeChart].getDataFromStructure({'Original Signal' : keys}, inv=True)['Original Signal']
        ssData = {}
        for k in range(len(keys)):
            ssData[keys[k]] = sData[k]
        self.mChart.drawAllChannels(ssData, 'Original Signal') #do popr
        '''

'''

################## CHART SELECTOR ##################

'''
class DataToDrawSelector(QWidget):

    exampleDataToDraw = {     'OS': {'Original Signal': None},
                  'PS-,PS+': {'Processed Signal -' : None, 'Processed Signal +' : None},
                   'OS,PS+': {'Original Signal' : None, 'Processed Signal +' : None}}
    '''
        self.chartSelector = QListWidget()
        for ch in self.charts:
            self.chartSelector.addItem(ch)
        self.chartSelector.currentTextChanged.connect(self.setAtiveChart)
        return self.chartSelector
    '''

    newChannelSelected = Signal(str, str, dict)
    newSignalSelected = Signal(str, str, dict)
    newMaskSelected = Signal(str, str)
    signalColorChanged = Signal(str, str)
    
    def __init__(self, dataManager, chartData, charManager, algManager, parent=None):
        QWidget.__init__(self, parent)
        self.dataManager = dataManager
        self.chartData = chartData
        self.charManager = charManager
        self.algManager = algManager
        self._crateSelectors()
        self.curSelect = None
        self.signalPressed = False

    def _crateSelectors(self):
        self.mLayout = QVBoxLayout(self)
        
        wsLayout = QVBoxLayout()
        alg = self.algManager
        self.wsSelector = WorkspaceChooser(alg)
        self.wsSelector.setMaximumHeight(70)
        groups = self.chartData.getDataGroups()
        self.wsSelector.addItems(groups)
        self.wsSelector.currentTextChanged.connect(self._updateAll)
        self.chartData.dataGroupAdded.connect(self.addNewGroup)
        self.mLayout.addWidget(QLabel('Workspaces'))
        self.mLayout.addWidget(self.wsSelector)
        self.chartData.allRemoved.connect(self._resetWorkspaces)
        
        self.chSelector = QTreeWidget()
        self.chSelector.setHeaderHidden(True)
        self.chSelector.itemClicked.connect(self.changeCurrentSelect)
        self.chSelector.itemChanged.connect(self.itemChanged)
        self.mLayout.addWidget(QLabel('Channels'))
        self.mLayout.addWidget(self.chSelector)
        
        self.sSelector = SignalChooser()
        self.sSelector.setHeaderHidden(True)
        self.sSelector.setDragEnabled(True)
        self.sSelector.setDropIndicatorShown(True)
        self.sSelector.setContextMenuPolicy(Qt.CustomContextMenu)
        self.createSignalPopupMenu(self.sSelector)
        self.sSelector.customContextMenuRequested.connect(self.onSignalContextMenu)
        self.sSelector.itemClicked.connect(self.changeCurrentSelect)
        self.sSelector.itemPressed.connect(self.signalPress)        
        self.sSelector.itemChanged.connect(self.itemChanged)
        self.mLayout.addWidget(QLabel('Signals'))
        self.mLayout.addWidget(self.sSelector)

        self.gSelector = SignalGroupsChooser(self.chartData, self.wsSelector)
        self.mLayout.addWidget(QLabel('Signal Groups'))
        self.mLayout.addWidget(self.gSelector)

        self.wsSelector.setCurrentRow(0)
        self.chartData.signalAdded.connect(self._updateAll)
        self.chartData.signalRemoved.connect(self._updateAll)
        self.chartData.signalGroupAdded.connect(self._updateAll)
        self.chartData.signalGroupRemoved.connect(self._updateAll)
        self.chartData.signalToGrupAdded.connect(self._updateAll)
        self.chartData.signalFromGroupRemoved.connect(self._updateAll)
        

    def signalPress(self):
        self.signalPressed = True
    
    def createSignalPopupMenu(self, parent=None):
        self.popupMenu = QMenu(parent)
        self.popupMenu.addAction("Process...", self.openSignalProcessingDialog)
        self.popupMenu.addAction("Apply algorithm...", self.openAlgorithmDialog)
        self.popupMenu.addAction("Set as Current Mask", self.maskSelected)
        self.popupMenu.addAction("Change color", self.changeSignalColor)
        self.popupMenu.addSeparator()
        self.popupMenu.addAction("Delete", self.deleteSignal)

    def onSignalContextMenu(self, pos):        
        self.clickedItem = self.sSelector.itemAt(pos)
        if self.clickedItem is None:
            return
        if self.clickedItem.parent() is None:
            self.popupMenu.exec_(self.sSelector.mapToGlobal(pos))

    def deleteSignal(self):
        ws = self.wsSelector.currentItem().text()
        signalToDel = self.clickedItem.text(0)
        self.dataManager.removeSignal(ws, signalToDel)

    def addNewGroup(self, newGroup, gKind):
        newItem = QListWidgetItem(newGroup)
        newItem.setData(1, gKind)
        self.wsSelector.addItem(newItem)
        self.wsSelector.setCurrentItem(newItem)
        
    def _resetWorkspaces(self):
        self.wsSelector.currentTextChanged.disconnect(self._updateAll)
        wsCount = self.wsSelector.count()
        for i in range(wsCount-1, -1, -1):
            self.wsSelector.takeItem(i)
        self.wsSelector.currentTextChanged.connect(self._updateAll)
        

    def _updateAll(self, newGroup=None):
        try:
            self.chSelector.itemChanged.disconnect(self.itemChanged)
            self.sSelector.itemChanged.disconnect(self.itemChanged)
        except:
            pass
        if newGroup == '':
            return
        
        chStruct = self.chartData[newGroup]
        sStruct = self.chartData[newGroup].getColStructure()
        
        self.chSelector.clear()
        for ws in chStruct:
            gparent = QTreeWidgetItem(self.chSelector)
            gparent.setText(0, ws)
            gparent.setBackgroundColor(0, Qt.white)
            gparent.setFlags(Qt.ItemIsEnabled)
            for key in chStruct[ws]:
                parent = QTreeWidgetItem(gparent)
                parent.setText(0, key)
                if chStruct[ws][key][0] == True:
                    dataNames = chStruct[ws][key][3]
                    sColor = QColor(chStruct[ws][key][4])
                    sColor.setAlpha(100)
                    parent.setBackgroundColor(0, sColor)
                else:
                    dataNames = ','.join(chStruct[ws][key][2])
                    sColor = QColor(chStruct[ws][key][3])
                    sColor.setAlpha(100)
                    parent.setBackgroundColor(0, sColor)
                    
                parent.setText(1, dataNames)
                if chStruct[ws][key][1] == True:
                    parent.setCheckState(0, Qt.Checked)
                else:
                    parent.setCheckState(0, Qt.Unchecked)
                parent.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        
        self.sSelector.clear()
        self.gSelector.clear()
        for ws in sStruct:
            firstChannel = sStruct[ws][0]
            isOneSignal = self.chartData[newGroup][firstChannel][ws][0]
            if isOneSignal:
                gparent = QTreeWidgetItem(self.sSelector)
                gparent.setText(0, ws)
                gparent.setFlags(Qt.ItemIsEnabled | Qt.ItemIsDragEnabled
                                 | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                if True:
##                if chStruct['CH1'][ws][5] == True:
                    gparent.setCheckState(0, Qt.Checked) 
                else:
                    gparent.setCheckState(0, Qt.Unchecked)
                    
                for key in sStruct[ws]:
                    parent = QTreeWidgetItem(gparent)
                    parent.setText(0, key)
                    if chStruct[key][ws][2] == True:
                        parent.setCheckState(0, Qt.Checked)
                    else:
                        parent.setCheckState(0, Qt.Unchecked)
                    parent.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    sColor = QColor(chStruct[key][ws][4])
                    sColor.setAlpha(100)
                    sGradient = QLinearGradient(0, 0, 100, 10)
                    sGradient.setColorAt(0, sColor)
                    sGradient.setColorAt(1, Qt.white)
                    sBrush = QBrush(sGradient)
                    sBrush.setStyle(Qt.LinearGradientPattern)
                    sBrush.setColor(sColor)
                    gparent.setBackground(0, sBrush)
                    
            else:
                gparent = QTreeWidgetItem(self.gSelector)
                gparent.setText(0, ws)
                gparent.setFlags(Qt.ItemIsEnabled | Qt.ItemIsDropEnabled
                                 | Qt.ItemIsUserCheckable)
                if chStruct['CH1'][ws][5] == True:
                    gparent.setCheckState(0, Qt.Checked)
                else:
                    gparent.setCheckState(0, Qt.Unchecked)
                
                signalNames = chStruct[key][ws][2]
                sColor = QColor(chStruct[key][ws][3])
                sColor.setAlpha(100)
                gparent.setBackgroundColor(0, sColor)
                for signal in signalNames:
                    parent = QTreeWidgetItem(gparent)
                    parent.setText(0, signal)
                    parent.setFlags(Qt.ItemIsEnabled)

                    for key in sStruct[signal]:
                        sColor = QColor(chStruct[key][signal][4])
                        sColor.setAlpha(100)
                        parent.setBackgroundColor(0, sColor)
                        break                   
            
        self.chSelector.itemChanged.connect(self.itemChanged)
        self.sSelector.itemChanged.connect(self.itemChanged)
        self.curSelect = None

    def _updateSignalColor(self, signalName, newColor):
        chIter = QTreeWidgetItemIterator(self.chSelector,
                                        QTreeWidgetItemIterator.Checked)
        while chIter.value():
            if chIter.value().text(0) == signalName:
                sColor = QColor(newColor)
                sColor.setAlpha(100)
                chIter.value().setBackgroundColor(0, sColor)
            chIter += 1

        sIter = QTreeWidgetItemIterator(self.sSelector)
        while sIter.value():
            if sIter.value().text(0) == signalName:
                sColor = QColor(newColor)
                sColor.setAlpha(100)
                sGradient = QLinearGradient(0, 0, 100, 10)
                sGradient.setColorAt(0, sColor)
                sGradient.setColorAt(1, Qt.white)
                sBrush = QBrush(sGradient)
                sBrush.setStyle(Qt.LinearGradientPattern)
                sBrush.setColor(sColor)
                sIter.value().setBackground(0, sBrush)
                if sIter.value() is self.curSelect:
                    self.prevBackGround = sIter.value().background(0)
            sIter += 1

        self.changeCurrentSelect(self.curSelect)

            
        

    def changeCurrentSelect(self, newItem):
        if newItem is None:
            print('newItem is None')
            self.curSelect = None
            return

        if (newItem.treeWidget() is self.sSelector
            and not self.signalPressed):
            ws = self.wsSelector.currentItem().text()
            isChecked = [True if newItem.checkState(0) is Qt.Checked else False]
            channel = 'CH1'
            signal = newItem.text(0)
            self.chartData[ws][channel][signal][5] = isChecked[0]
            return
        self.signalPressed = False

        newItem.setSelected(False)
        
        if newItem.parent() is None:
            
            if self.curSelect is not None:
                self.curSelect.setFont(0, self.prevFont)
                self.curSelect.setBackground(0, self.prevBackGround)
                self.curSelect.setForeground(0, self.prevForeground)
            self.prevBackGround = newItem.background(0)
            self.prevForeground = newItem.foreground(0)
            self.prevFont = newItem.font(0)
            
            sBrush = newItem.background(0)
            sBColor = sBrush.color()
            sBColor.setAlpha(200)
            sBrush.setColor(sBColor)
            sBrush.setStyle(Qt.SolidPattern)

            sFont = newItem.font(0)
            sFont.setBold(True)
            
            if newItem.treeWidget() is self.chSelector:
                sBrush.setColor(QColor(56, 211, 255, 120))
            newItem.setBackground(0, sBrush)
            newItem.setForeground(0, QBrush(Qt.white))
            newItem.setFont(0, sFont)
            


            
            self.curSelect = newItem
            if self.curSelect.treeWidget() is self.chSelector:
                self.ChannelSelected()
            elif self.curSelect.treeWidget() is self.sSelector:
                self.SignalSelected()

    def ChannelSelected(self):
        dChecked = []
        sIter = QTreeWidgetItemIterator(self.sSelector, QTreeWidgetItemIterator.Checked)
        while sIter.value():
            if not sIter.value().parent():
                dChecked.append(sIter.value().text(0))
            sIter += 1

        gIter = QTreeWidgetItemIterator(self.gSelector, QTreeWidgetItemIterator.Checked)
        while gIter.value():
            if not gIter.value().parent():
                dChecked.append(gIter.value().text(0))
            gIter += 1


        
        chStruct = {}
        sIter = QTreeWidgetItemIterator(self.curSelect,
                                        QTreeWidgetItemIterator.Checked)
        while (sIter.value()
               and sIter.value().parent() is self.curSelect
               and sIter.value().checkState(0) == Qt.Checked):
            sItem = sIter.value()
            dataName = sItem.text(0)
            if dataName in dChecked:
                chStruct[sItem.text(0)] = None
            sIter += 1
        group = self.wsSelector.currentItem().text()
        channel = self.curSelect.text(0)
        self.newChannelSelected.emit(group, channel, chStruct)
        
    def SignalSelected(self):
        sStruct = {}
        chIter = QTreeWidgetItemIterator(self.curSelect,
                                        QTreeWidgetItemIterator.Checked)
        if not chIter.value().parent():     #Skip signal 
            chIter += 1
        while (chIter.value()
               and chIter.value().parent() is self.curSelect
               and chIter.value().checkState(0) == Qt.Checked):
            chItem = chIter.value()
            sStruct[chItem.text(0)] = None
            chIter += 1
        ws = self.wsSelector.currentItem().text()
        signal = self.curSelect.text(0)    
        self.newSignalSelected.emit(ws, signal, sStruct)

    def maskSelected(self):
        ws = self.wsSelector.currentItem().text()
        signal = self.clickedItem.text(0)
        self.newMaskSelected.emit(ws, signal)

    def changeSignalColor(self):
        ws = self.wsSelector.currentItem().text()
        signal = self.clickedItem.text(0)
        
        channels = []
        sIter = QTreeWidgetItemIterator(self.clickedItem)
        sIter += 1              # First children
        while(sIter.value()):
            if sIter.value().parent() is self.clickedItem:
                channels.append(sIter.value().text(0))
                sIter += 1
            else:
                break
        
        sData = self.chartData[ws].getDataFromStructure({signal : channels}, inv=True)[signal]
        sColor = sData[0][4]
        newColor = QColorDialog().getColor(QColor(sColor), self)
        if newColor.isValid():
            for sD in sData:
                sD[4] = newColor.name()
            self._updateSignalColor(signal, newColor.name())
            self.signalColorChanged.emit(ws, signal)

    def openSignalProcessingDialog(self):
        ws = self.wsSelector.currentItem().text()
        signal = self.clickedItem.text(0)
        dialog = DataProcessingDialog(self.dataManager, self, [ws, signal])
        dialog.show()
        dialog.exec()

    def openAlgorithmDialog(self):
        ws = self.wsSelector.currentItem().text()
        signal = self.clickedItem.text(0)
        self.algManager.showAlgorithmDialog(ws, signal)    

    def itemChanged(self, item):
        
        if item.flags() == (Qt.ItemIsUserCheckable | Qt.ItemIsEnabled):
            ws = self.wsSelector.currentItem().text()
            isChecked = [True if item.checkState(0) is Qt.Checked else False]
            if item.treeWidget() is self.chSelector:
                channel = item.parent().text(0)
                signal = item.text(0)
                self.chartData[ws][channel][signal][1] = isChecked[0]
            elif item.treeWidget() is self.sSelector:
                signal = item.parent().text(0)
                channel = item.text(0)
                self.chartData[ws][channel][signal][1] = isChecked[0]


    def addSignalItem(self, group, signal, chList):
        pass
        '''
        NOT IMPLEMENTED
        rootIter = QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.HasChildren)
        gparent = None
        while (rootIter.value()):
            item = rootIter.value()
            print(item.text(0), rootIter.value().parent())
            if item.text(0) == group and rootIter.value().parent() is None:
                gparent = item
                break
            rootIter += 1
            
        parent = QTreeWidgetItem(gparent)
        parent.setText(0, row)
        parent.setFlags(parent.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
        for k in colList:
            child = QTreeWidgetItem(parent)
            child.setFlags(child.flags())
            child.setText(0, k)
            child.setCheckState(0, Qt.Unchecked)
        '''

'''

################## WORKSPACE CHOOSER ##################

'''
class WorkspaceChooser(QListWidget):
    def __init__(self, algManager, parent=None):
        QListWidget.__init__(self, parent)

        self.algManager = algManager
        self._createPopupMenu()

    def _createPopupMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.onContextMenu)
        
        self.algorithmMenu = QMenu(None)
        self.algorithmMenu.addAction("Adjust parameters...", self.adjustAlgorithm)


    def onContextMenu(self, pos):
        self.clickedItem = self.itemAt(pos)
        if self.clickedItem is None:
            return
        if self.clickedItem.data(1)[:9] == 'Algorithm':
            self.algorithmMenu.exec_(self.mapToGlobal(pos))


    def adjustAlgorithm(self):
        wsName =  self.clickedItem.text()
        self.algManager.adjustAlogrithmParameters(wsName)

        

'''

################## SIGNAL CHOOSER ##################

'''
class SignalChooser(QTreeWidget):
    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)

##    def mousePressEvent(self, event):
##        self.clickedButton = event.button()
##        event.accept()
##        print('mousePressEvent', event.button())

##    def startDrag(self, event):
##        ##        event.accept()
##        drag = QDrag(self)
##        drag.exec_(event)
##        self.dragEnterEvent(drag)
##        print('startDrag')

        
'''

################## SIGNAL GROUPS CHOOSER ##################

'''
class SignalGroupsChooser(QTreeWidget):
    def __init__(self, chartData, wsSelector, parent=None):
        QTreeWidget.__init__(self, parent)
        
        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)

        
        self.chartData = chartData
        self.wsSelector = wsSelector
        self.createPopupMenu()

        self.itemChanged.connect(self.itemHasChanged)
        self.isDroppedItem = False

    def createPopupMenu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.onContextMenu)

        self.blankMenu = QMenu(None)
        self.blankMenu.addAction("New Group", self.showGrouper)
        
        self.groupMenu = QMenu(None)
        self.groupMenu.addSeparator()
        self.groupMenu.addAction("Delete", self.deleteSignalGroup)

        self.signalMenu = QMenu(None)
        self.signalMenu.addAction("Remove from Group", self.removeSignalFromGroup)

    def dropEvent(self, event):
        pos = event.pos()
        mimeData = event.mimeData().hasUrls()
        source = event.source()
        if self.itemAt(pos) is not None and self.itemAt(pos).parent() is None:
            self.parentDroppedItem = self.itemAt(pos)
            self.isDroppedItem = True
            super(QTreeWidget, self).dropEvent(event)


    def onContextMenu(self, pos):
        self.clickedItem = self.itemAt(pos)
        if self.clickedItem is None:
            self.blankMenu.exec_(self.mapToGlobal(pos))
            return
        if self.clickedItem.parent() is None:
            self.groupMenu.exec_(self.mapToGlobal(pos))
        else:
            self.signalMenu.exec_(self.mapToGlobal(pos))
        

    def itemHasChanged(self, item):
        if self.isDroppedItem:
            self.isDroppedItem = False
            ws = self.wsSelector.currentItem().text()
            groupName = self.parentDroppedItem.text(0)
            signalName = item.text(0)
            self.chartData.addSignalToGroup(ws, groupName, signalName)


    def deleteSignalGroup(self):
        ws = self.wsSelector.currentItem().text()
        groupToDel = self.clickedItem.text(0)
        self.chartData.removeSignalGroup(ws, groupToDel)

    def removeSignalFromGroup(self):
        ws = self.wsSelector.currentItem().text()
        groupName = self.clickedItem.parent().text(0)
        signalName = self.clickedItem.text(0)
        self.chartData.removeSignalFromGroup(ws, groupName, signalName)

    def showGrouper(self):
        grouper = SignalGrouper(self.chartData)
        grouper.show()
        grouper.exec()
        

'''

################## CHOOSER ##################

'''
class Chooser(QComboBox):

    currentValueChanged = Signal(int)
    
    def __init__(self, options, parent=None):
        QComboBox.__init__(self, parent)
        self.options = options
        for opt in self.options:
            self.addItem(opt, self.options[opt])
        self.currentIndexChanged.connect(self.changeCurrentValue)

    def getCurrentValue(self):
        return self.itemData(self.currentIndex())

    def changeCurrentValue(self, curIndex):
        self.currentValueChanged.emit(self.itemData(curIndex))

'''

################## SIGNAL GROUPER ##################

'''
class SignalGrouper(QDialog):
    def __init__(self, chartData, parent=None):
        QDialog.__init__(self, parent)
        self.chartData = chartData
        self._create()

    def _create(self):
        self.mLayout = QVBoxLayout(self)
        
        self.gSelector = QListWidget()
        groups = self.chartData.getDataGroups()
        self.gSelector.addItems(groups)
        self.gSelector.currentTextChanged.connect(self._updateGroupList)
        self.chartData.dataGroupAdded.connect(self.gSelector.addItem)
        self.chartData.dataGroupAdded.connect(self.gSelector.addItem)
        self.mLayout.addWidget(self.gSelector)

        self.sSelector = QListWidget()
        self.mLayout.addWidget(self.sSelector)

        groupBtn = QPushButton('Create group from selected')
        groupBtn.clicked.connect(self.createNewGroup)
        self.mLayout.addWidget(groupBtn)
        

    def _updateGroupList(self):
        newGroup = self.gSelector.currentItem().text()
        sStruct = self.chartData[newGroup].getColStructure()
        self.sSelector.clear()
        for ws in sStruct:
            firstChannel = sStruct[ws][0]
            isOneSignal = self.chartData[newGroup][firstChannel][ws][0]
            if isOneSignal:
                item = QListWidgetItem(ws, self.sSelector)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Unchecked)

    def createNewGroup(self):
        checkList = []
        for i in range(self.sSelector.count()):
            sItem = self.sSelector.item(i)
            if sItem.checkState() == Qt.Checked:
                checkList.append(sItem.text())
        if len(checkList) > 0:
            groupName, result = QInputDialog().getText(self, 'Input', 'Enter group name:')
            if result:
                ws = self.gSelector.currentItem().text()
                sStruct = self.chartData[ws].getColStructure(checkList)
                sKeys = list(sStruct.keys())
                for s in range(len(sKeys)):
                    if sStruct[sKeys[s]] != sStruct[sKeys[s-1]]:
                        print('Signals have diffrent channel sets')
                        return
                self.chartData.appendSignalGroup(ws, groupName, sStruct[sKeys[0]], checkList)
            else:
                return
        else:
            return

'''

################## CHART SCROLLER ##################

'''
class ChartScroller(QScrollBar):
    
    def __init__(self, chart, orientation, parent=None):
        QScrollBar.__init__(self, orientation, parent)
        self.mChart = chart
        self.mChart.chartDrawn.connect(self.setRange)
        self.mChart.viewRangeChanged.connect(self.setScrollSize)
        self.mChart.xRangeChanged.connect(self.setPos)
        self.sliderMoved.connect(self.posChanged)

        self.dataMax = 0

        self.setStyleSheet("""
        QScrollBar:horizontal {
            border: none;
            background: none;
            height: 26px;
            margin: 0px 26px 0 26px;
        }

        QScrollBar::handle:horizontal {
            background: #38d3ff;
            min-width: 25px;
        }

        QScrollBar::add-line:horizontal {
            background: none;
            width: 26px;
            subcontrol-position: right;
            subcontrol-origin: margin;
            
        }

        QScrollBar:left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
            width: 26px;
            height: 26px;
            background: none;
        }

        QScrollBar::sub-line:horizontal {
            background: none;
            width: 26px;
            subcontrol-position: top left;
            subcontrol-origin: margin;
            position: absolute;
        }

        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }

    """)

        self.setMinimum(0)
        self.setMaximum(0)
        self.setPageStep(0)
        self.scrollerSize = self.mChart.getViewRange()

    def posChanged(self, pos):
        self.pos = pos
        self.mChart.setXRange(pos, pos+self.scrollerSize)

    def setRange(self, dMin, dMax):
        self.setMinimum(dMin)
        self.setMaximum(dMax-self.scrollerSize)
        self.dataMax = dMax

    def setScrollSize(self, newSize):
        self.setPageStep(newSize)
        self.scrollerSize = newSize
        self.setMaximum(self.dataMax-self.scrollerSize)

    def setPos(self, newPos):
        self.setSliderPosition(newPos)

'''

################## CHART AREA ##################

'''
class ChartArea(QWidget):
    def __init__(self, chm, parent=None):
        QWidget.__init__(self, parent)

        mainLay = QVBoxLayout()
        self.setLayout(mainLay)
        
        toolbar = chm.createToolbar()
        mainLay.addWidget(toolbar)
        
        chart = chm.getChart()
        mainLay.addWidget(chart)

        scroller = chm.createScrollBar()
        mainLay.addWidget(scroller)
