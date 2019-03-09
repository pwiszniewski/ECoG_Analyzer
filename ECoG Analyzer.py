from chartView import *
from dialogs import *
from PySide2.QtWidgets import (QApplication, QMainWindow, QScrollArea,
                               QSizePolicy, QToolBar)
from PySide2.QtGui import QPalette
import gc
##import pandas as pd
from data import *
from chartWidgets import *
from algorithms import *
from fileHandlers import FileManager

'''

MAIN WINDOW CLASS

'''
class ApplicationWindow(QMainWindow):
    def __init__(self):
        # Main window - Properties
        QMainWindow.__init__(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("ECoG Analyzer")

        self.dm = DataManager(250)      
        self.chm = MyChartManager(self.dm)
        self.algManager = AlgorithmsManager(self.dm, self.chm)
        self.fileManager = FileManager()

        chartArea = ChartArea(self.chm)
        self.setCentralWidget(chartArea)

        self.setupMenu()
        self.setupToolbar()
        self.setupDockWidgets()


    def setupMenu(self):
        # Menu - File
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open...', self.fileOpen,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_O)
        self.file_menu.addAction('&Quit', self.fileQuit,
                                 QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        # Menu - Chart
        self.chart_menu = QtWidgets.QMenu('&Chart', self)
        a = self.chart_menu.addAction('&ON/OFF Autoscale')
        a.triggered.connect(self.changeChartAutoscale)
        a.setCheckable(True)
        a = self.chart_menu.addAction('Show Legend')
        a.setCheckable(True)
        a.toggled.connect(self.chm.getChart().setLegendVisible)
        self.gridChooser = self.chart_menu.addMenu('Grid')
        gridOptions = ('&20 x 1', '&5 x 4')
        for option in gridOptions:
            a = self.gridChooser.addAction(option)
            a.setCheckable(True)
            if option == '&20 x 1':
                a.setChecked(True)
        a = self.chart_menu.addAction('Show Map')
        a.triggered.connect(self.chm.showMap)
        self.gridChooser.triggered.connect(self.setChartGrid)
        self.menuBar().addMenu(self.chart_menu)
        
        # Menu - Window
        self.window_menu = QtWidgets.QMenu('&Window', self)
        self.toolWigtedVisible = self.window_menu.addAction('&Show Tool Widget',
                                       shortcut=QtCore.Qt.CTRL + QtCore.Qt.Key_L)
        self.toolWigtedVisible.triggered.connect(self.changeDockWidgetVisible)
        self.toolWigtedVisible.setCheckable(True)
        self.toolWigtedVisible.setChecked(True)
        self.menuBar().addMenu(self.window_menu)

    def setupToolbar(self):
        self.toolBar = QToolBar()
        self.toolBar.addAction('&Data processing', self.showDataProcessingDialog)
        self.toolBar.addAction('&Algorithms', self.showAlgorithmsDialog)
        self.addToolBar(self.toolBar)

    def setupDockWidgets(self):
        self.chTools = ChartTools(self.chm, self.algManager, self)
        self.chTools.setFixedWidth(0.3*self.size().width())
        self.toolWidget = QDockWidget(self)
        self.toolWidget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.toolWidget.setWidget(self.chTools)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolWidget, Qt.Vertical)
        self.toolWidget.visibilityChanged.connect(self.toolWigtedVisible.setChecked)
        self.toolWidget.setFloating(False)

    def showDataProcessingDialog(self):
        dialog = DataProcessingDialog(self.dm, self)
        dialog.show()
        dialog.exec()

    def showAlgorithmsDialog(self):
        print('type(self.chm)', type(self.chm))
        dialog = FirstAlgorithm(self.dm, self.chm, self)
        dialog.show()
        dialog.exec()

    def changeDockWidgetVisible(self):
        self.toolWidget.setVisible(not self.toolWidget.isVisible())

    def changeChartAutoscale(self, state):
        self.chm.getChart().setAutoscaleY(state)

    def setChartGrid(self, action):
        for a in self.gridChooser.actions():
            a.setChecked(False)
        plotsPerAxes = int(action.text()[1:3])
        action.setChecked(True)
        self.chm.getChart().setPlotsPerAxes(plotsPerAxes)


    def fileOpen(self):
        wsName = 'Sandbox'

        try:
            filePath, ecog, chNames = self.fileManager.openFile()
        except:
            return
        if ecog is not None:
            self.dm.removeAll()
            self.dm.createDataGroup(wsName)
            fileName = filePath.split('/')[-1].split('.')[-2]
            print('ecog len', len(ecog))
            if chNames is None:
                chNames = ['CH'+str(n) for n in range(1,len(ecog)+1)] 
            self.dm.addChannels(wsName, chNames)
            self.dm.addSignal(wsName, 'Original Signal ({})'.format(fileName), ecog, chNames)
##            self.dm.addSignal(wsName, 'Original Signal ({})+Offset'.format(fileName), ecog+2000, chNames)

    def fileQuit(self):
        self.close()


if __name__ == "__main__":

    app = QApplication(sys.argv)

    aw = ApplicationWindow()
    aw.show()

    sys.exit(app.exec_())

    
