import sys
import numpy as np
from scipy import signal
import scipy.io
import matplotlib.pyplot as plt
from PySide2.QtWidgets import (QDialog, QComboBox, QGridLayout, QLabel,
                               QHBoxLayout, QGroupBox, QFormLayout,
                               QLineEdit, QFrame, QSpinBox, QDialogButtonBox,
                               QPushButton, QVBoxLayout, QStackedLayout,
                               QFileDialog, QWidget, QErrorMessage,
                               QDoubleSpinBox)
from PySide2.QtCore import Qt, Signal, QLocale
from chartView import *
from calculations import *
import pyedflib

'''

################## FILE MANAGER ##################

'''
class FileManager(object):

    def __init__(self):
        pass

    def openFile(self):
        fileDialog = OpenFileDialog()
        try:
            filePath, data, chNames = fileDialog.getData()
        except:
            return
##        fileDialog.show()
##        fileDialog.exec()
        return filePath, data, chNames

'''

################## OPEN FILE DIALOG ##################

'''
class OpenFileDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)

    def getData(self):
        fileObj = QFileDialog.getOpenFileName(self, "Choose the file", dir=".",
                                              filter="Data files (*.mat *.edf)")
        if fileObj[0] == '':
            return
        filePath = fileObj[0]
        fileType = filePath.split('.')[-1]
        chNames = None
        if fileType == 'mat':
            fileData = scipy.io.loadmat(filePath)
            data = [fileData[key] for key in fileData if type(fileData[key]) == np.ndarray][0]
            if np.shape(data)[0] > np.shape(data)[1]:
                data = data.transpose()
        elif fileType == 'edf':
            f = pyedflib.EdfReader(filePath)
            n = f.signals_in_file
            chNames = f.getSignalLabels()
            data = np.zeros((n, f.getNSamples()[0]))
            for i in np.arange(n):
                try:
                    data[i, :] = f.readSignal(i)
                except Exception as e:
                    print(chNames[i], ' skipped', e)
            print(np.shape(data))
        return filePath, data, chNames
