import sys
import numpy as np
from PySide2.QtGui import QStandardItemModel
from PySide2.QtCore import Qt, Signal, QObject
from PySide2.QtWidgets import (QTreeView, QTreeWidget, QTreeWidgetItem,
                               QTreeWidgetItemIterator, QMessageBox)


'''

################# MY DATA #################

'''        
class MyData(dict):
    def __init__(self, fs=None):
        dict.__init__(self)
        # row and column names
        self.fs = fs
        self.rNames = []
        self.cNames = []
        self.struct = {}

    def addRows(self, rNames):
        for rName in rNames:
            self[rName] = {}
            if rName not in self.rNames:
                self.rNames.append(rName)

    def addColumn(self, cName, rData=None, rNames=None):
        if rData is None:
            self.cNames.append(cName)
            return
        if rNames is None:
            rNames=self.rNames
        if len(rData) != len(rNames):
            print('rData ({}) and rNames({}) must be the same length'.format(len(rData), len(rNames)))
            return
        for n in range(len(rNames)):
            self[rNames[n]][cName] = rData[n]
        if cName not in self.cNames:
            self.cNames.append(cName)

    def setFs(self, fs):
        self.fs = fs
    
    def getFs(self):
        return self.fs

    def getRowNames(self):
        return self.rNames

    def getColumnNames(self):
        return self.cNames

    def getRowStructure(self):
##        return self
        struct = {}
        for key in self:
            struct[key] = self[key].keys()
        return struct

    def getColStructure(self, cNames=None):
        if cNames == None:
            cNames = self.cNames            
        struct = {}
        for cn in cNames:
            struct[cn] = []
            for rn in self.keys():
                if cn in self[rn].keys():
                    struct[cn].append(rn)
        return struct

    def getDataFromStructure(self, struct, inv):
        dStruct = {}
        if inv:
            for row in struct:
                dList = []
                for col in struct[row]:
                    dList.append(self[col][row])
                dStruct[row] = dList
        else:
            for row in struct:
                dList = []
                for col in struct[row]:
                    dList.append(self[row][col])
                dStruct[row] = dList
        return dStruct

    def appendDataFromStructure(self, struct, inv):
        for cName in struct:
            for rName in struct[cName]:
                self[rName][cName] = struct[cName][rName]
            if cName not in self.cNames:
                self.cNames.append(cName)

    def XappendDataFromStructure(self, struct, data, inv):
        for cName in struct:
            self.addColumn(cName, data, struct[cName])

    def removeColumn(self, cName):
        for row in self:
            self[row].pop(cName, None)
        self.cNames.remove(cName)


'''

################# DATA MANAGER #################

'''
class DataManager(QObject):
    dataAdded = Signal(dict)
    channelsAdded = Signal(str, list)
    signalAdded = Signal(str, str, list)
    signalChanged = Signal(str, str, list)
    signalRemoved = Signal(str, str)
    dataGroupAdded = Signal(str, str)
    allRemoved = Signal()
        
    def __init__(self, fs, parent=None):
        QObject.__init__(self, parent)
        self.gNames = []
        self.mData = {}
        self.fs = fs

    def __getitem__(self, arg):
        return self.mData[arg]
    
    def setFs(self, fs):
        self.fs = fs
    
    def getFs(self):
        return self.fs
        
    def createDataGroup(self, gName, gKind='Normal'):
        if gName in self.gNames:
            print('This name already exists')
            return
        self.mData[gName] = MyData(self.fs)
        self.gNames.append(gName)
        self.dataGroupAdded.emit(gName, gKind)
    def removeAll(self):
        self.gNames = []
        self.mData = {}
        self.allRemoved.emit()

    def getDataGroups(self):
        return self.gNames

    def addChannels(self, gName, chNames):
        self[gName].addRows(chNames)
        self.channelsAdded.emit(gName, chNames)

    def addSignal(self, gName, cName, rData, rNames):
        self[gName].addColumn(cName, rData, rNames)
        self.signalAdded.emit(gName, cName, rNames)

    def silentChangeSignal(self, gName, cName, rData, rNames):
        self[gName].addColumn(cName, rData, rNames)

    def getStructure(self, inv=True):
        struct = {}
        for mdkey in self.mData:
            if inv:
                struct[mdkey] = self.mData[mdkey].getColStructure()
            else:
                struct[mdkey] = self.mData[mdkey].getRowStructure()
        return struct

    def getData(self, struct, inv):
        dStruct = {}
        for group in struct:
            dStruct[group] = self.mData[group].getDataFromStructure(struct[group], inv)
        return dStruct

    def appendData(self, struct, inv=True):
        for group in struct:
            self.mData[group].appendDataFromStructure(struct[group], inv=inv)
        self.dataAdded.emit(struct)

    def appendSignal(self, group, signal, chList, data):
        self.mData[group].addColumn(signal, data, chList)
        self.signalAdded.emit(group, signal, chList)

    def changeSignal(self, group, signal, chList, data):
        self.mData[group].addColumn(signal, data, chList)
        self.signalChanged.emit(group, signal, chList)

    def removeSignal(self, group, signal):
        self[group].removeColumn(signal)
        self.signalRemoved.emit(group, signal)

'''

################# DATA SELECTOR #################

'''
class DataSelector(QTreeWidget):
    def __init__(self, dataManager, parent=None, inv=True, onlyOne=True, inputList=None):
        QTreeWidget.__init__(self, parent)
        self.isInverse = inv
        self.inputList = inputList
        self.dm = dataManager
        self.setHeaderHidden(True)
        self._create()
        if onlyOne:
            if inputList is None:
                self.curChecked = None
            self.itemChanged.connect(self.itemHasChanged)
        self.dm.signalAdded.connect(self.addItem)
        self.dm.signalRemoved.connect(self.removeItem)

    def _create(self):
        struct = self.dm.getStructure(self.isInverse)
        for ws in struct:
            gparent = QTreeWidgetItem(self)
            gparent.setText(0, ws)
            for key in struct[ws]:
                parent = QTreeWidgetItem(gparent)
                parent.setText(0, key)
                parent.setFlags(parent.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                if (self.inputList is not None
                    and key == self.inputList[1]
                    and ws == self.inputList[0]):
                    channelsChecked = True
                    gparent.setExpanded(True)
                    self.curChecked = parent
                    parent.setSelected(True)
                else:
                    channelsChecked = False
                for k in struct[ws][key]:
                    child = QTreeWidgetItem(parent)
                    child.setFlags(child.flags())
                    child.setText(0, k)
                    if channelsChecked:
                        child.setCheckState(0, Qt.Checked)
                    else:
                        child.setCheckState(0, Qt.Unchecked)

    def getSelectedStruct(self):
        chStruct = {}
        rootIter = QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.HasChildren)
        while rootIter.value():
            item = rootIter.value()
            if (item.checkState(0) == Qt.CheckState.Checked
                or item.checkState(0) == Qt.CheckState.PartiallyChecked):
                if item.parent().text(0) not in chStruct.keys():
                    chStruct[item.parent().text(0)] = {}
                chList = []
                for ch in range(item.childCount()):
                    if item.child(ch).checkState(0) == Qt.CheckState.Checked:
                        chList.append(item.child(ch).text(0))
                chStruct[item.parent().text(0)][item.text(0)] = chList
            rootIter += 1
            
        return chStruct
    
    def itemHasChanged(self, item, column):
        if item.childCount() > 0:
            if self.curChecked is item:
                return
            if (item.checkState(0) == Qt.CheckState.Checked
                    or item.checkState(0) == Qt.CheckState.PartiallyChecked):
                if self.curChecked is not None:
                    self.curChecked.setCheckState(0, Qt.Unchecked)
                self.setCurrentItem(item)
                self.curChecked = item
        self.update()

    def updateData(self, struct):
        group = list(struct.keys())[0]
        row = list(struct[group].keys())[0]
        chList = struct[group][row]        
        self.addItem(group, row, colList)

    def addItem(self, group, row, colList):
        rootIter = QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.HasChildren)
        gparent = None
        while (rootIter.value()):
            item = rootIter.value()
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

    def removeItem(self, itParent, itName):
        rootIter = QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.HasChildren)

        while (rootIter.value()):
            item = rootIter.value()
            if (item.text(0) == itName
                and rootIter.value().parent() is not None
                and rootIter.value().parent().text(0) == itParent):
                item.parent().removeChild(item)
                del item
                self.update()
                self.repaint()
                break
            rootIter += 1
    

        
