from data import *
import random

def randomColor(maxBright):
    sum = 0xFF*3
    while(sum > maxBright):
        r = random.randint(0, 0xFF)
        g = random.randint(0, 0xFF)
        b = random.randint(0, 0xFF)
        sum = r + g + b
    
    return "#%02x%02x%02x" % (r, g, b)

'''

################## CHART DATA MANAGER ##################

'''
class ChartDataManager(DataManager):
    signalGroupAdded = Signal(str, str, list)
    signalGroupChanged = Signal(str, str, list)
    signalGroupRemoved = Signal(str, str)
    signalToGrupAdded = Signal(str, str, str)
    signalFromGroupRemoved = Signal(str, str, str)
  
    def __init__(self, dataManager, parent=None):
        DataManager.__init__(self, parent)
        self.dManager = dataManager
        self.dManager.dataGroupAdded.connect(self.createDataGroup)
        self.dManager.signalRemoved.connect(self.removeSignal)
        self.dManager.channelsAdded.connect(self.addChannels)
        self.dManager.allRemoved.connect(self.removeAll)
        self._create()


    def _create(self):
        struct = self.dManager.getStructure()

        for group in struct:
            self.createDataGroup(group)
            self[group].addRows(self.dManager[group].getRowNames())
            for signal in struct[group]:
                chStruct = {}
                for channel in struct[group][signal]:
                    #                  vis, checkInCh, checkInS
                    chStruct[channel] = [True, True, True, signal, '#4dea84']
                struct[group][signal] = chStruct
        self.appendData(struct)
        self.dManager.signalAdded.connect(self.appendSignal)

    def createDataGroup(self, gName, gKind='Normal'):
        if gName in self.gNames:
            print('This name already exists')
            return
        self.mData[gName] = ChartData(self.fs)
        self.gNames.append(gName)
        self.dataGroupAdded.emit(gName, gKind)

    def appendSignal(self, group, signalName, chList):
        color = randomColor(450)
        data = [[True, True, True, signalName, color] if ch != 'CH1' else [True, True, True, signalName, color, True] for ch in chList ]
        self.mData[group].addColumn(signalName, data, chList)
        self.signalAdded.emit(group, signalName, chList)

    def removeSignal(self, group, signal):
        self[group].removeColumn(signal)
        self.signalRemoved.emit(group, signal)

    def appendSignalGroup(self, setName, groupName, chList=[], dataNames=[]):
        if(chList == [] and dataNames == []):
            self.mData[setName].addColumn(groupName)
        else:
            color = randomColor(500)
            data = [[False, True, dataNames, color] if ch != 'CH1' else [False, True, dataNames, color, None, True] for ch in chList ]
            self.mData[setName].addColumn(groupName, data, chList)
        self.signalGroupAdded.emit(setName, groupName, chList)

    def addSignalToGroup(self, setName, groupName, signalName):
##        if self[setName].isColumnEmpty(groupName):
        gStruct = self[setName].getColStructure([groupName])
        gDataStruct = self[setName].getDataFromStructure(gStruct, inv=True)
        for chData in gDataStruct[groupName]:
            chData[2].append(signalName)
            break
        self.signalToGrupAdded.emit(setName, groupName, signalName)

    def removeSignalFromGroup(self, setName, groupName, signalName):
        if self[setName].isColumnEmpty(groupName):
            return
        else:
            gStruct = self[setName].getColStructure([groupName])
            gDataStruct = self[setName].getDataFromStructure(gStruct, inv=True)
            for chData in gDataStruct[groupName]:
                chData[2].remove(signalName)
                break
        self.signalFromGroupRemoved.emit(setName, groupName, signalName)

    def removeSignalGroup(self, setName, groupName):
        self[setName].removeColumn(groupName)
        self.signalGroupRemoved.emit(setName, setName)

'''

################## CHART DATA ##################

'''
class ChartData(MyData):
    def __init__(self, fs):
        MyData.__init__(self)

    def isColumnEmpty(self, colName):
        isEmpty = True
        for col in self:
            if colName in self[col].keys():
                isEmpty = False
        return isEmpty


        
            
