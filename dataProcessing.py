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
                               QDoubleSpinBox, QCheckBox)
from PySide2.QtCore import Qt, Signal, QLocale
from chartView import *
from calculations import *

'''

ABSTRACT

'''
class AbstractProcessGroup(QGroupBox):
    
    progress = Signal(int)

    def __init__(self, title, fs):
        QGroupBox.__init__(self, title)
        self.fs = fs
        
    def process(self, inData):
        pass
    
'''

FILTER

'''
class FilterGroup(AbstractProcessGroup):
    
    def __init__(self, title, fs):
        AbstractProcessGroup.__init__(self, title, fs)
         
        self.setupFilterLayout()

    def setupFilterLayout(self):
        filterLayout = QVBoxLayout(self)
        filterSettLayout = QHBoxLayout()

        self.filterBandChooser = QComboBox()
        self.filterTypeChooser = QComboBox()        
        filterTypeLayout = QFormLayout()
        
        filterTypeLayout.addWidget(QLabel('Type'))
        filterTypeLayout.addWidget(self.filterBandChooser)
        bandTypes = {'Low Pass'  : 'lowpass',
                     'Band Pass' : 'bandpass',
                     'High Pass' : 'highpass',
                     'Band Stop' : 'bandstop'}
        [self.filterBandChooser.addItem(i, bandTypes[i]) for i in bandTypes]
        self.filterBandChooser.setCurrentText('Band Pass')
        filterTypeLayout.addWidget(self.filterTypeChooser)
        filterTypes = {'Butter' : 'butter',
                       'Bessel' : 'bessel'}
        [self.filterTypeChooser.addItem(i, filterTypes[i]) for i in filterTypes]

        self.lowFreqEdit = QDoubleSpinBox()
        self.lowFreqEdit.setSuffix(' Hz')
        self.lowFreqEdit.setDecimals(1) 
        self.lowFreqEdit.setRange(0.1, self.fs/2-0.1)
        self.highFreqEdit = QDoubleSpinBox()
        self.highFreqEdit.setSuffix(' Hz')
        self.highFreqEdit.setDecimals(1)
        self.highFreqEdit.setLocale(QLocale(QLocale.Polish, QLocale.EuropeanUnion))
        self.highFreqEdit.setRange(0.1, self.fs/2-0.1)
        self.filterBandChooser.currentTextChanged.connect(self.setFilterBand)
        filterFreqLayout = QFormLayout()
        filterFreqLayout.addRow(QLabel('Cutoff Frequencies'))
        filterFreqLayout.addRow('Low', self.lowFreqEdit)
        filterFreqLayout.addRow('High', self.highFreqEdit)

        filterOrdLayout = QFormLayout()
        self.filterOrdEdit = QSpinBox()
        self.filterOrdEdit.setMinimum(1)
        self.filterOrdEdit.setValue(5)
        filterOrdLayout.addRow(QLabel('Order'))
        filterOrdLayout.addRow(self.filterOrdEdit)
        
        filterSettLayout.addLayout(filterTypeLayout)
        filterSettLayout.addSpacing(10)
        filterSettLayout.addLayout(filterFreqLayout)
        filterSettLayout.addSpacing(10)
        filterSettLayout.addLayout(filterOrdLayout)

        btn = QPushButton('Show filter response')
        btn.clicked.connect(self.showFilterResponse)

        filterLayout.addLayout(filterSettLayout)
        filterLayout.addWidget(btn, 0, Qt.AlignRight)

    def setFilterBand(self):
        if self.filterBandChooser.currentText() == 'Low Pass':
            self.lowFreqEdit.setDisabled(True)
        else:
            self.lowFreqEdit.setEnabled(True)
        if self.filterBandChooser.currentText() == 'High Pass':
            self.highFreqEdit.setDisabled(True)
        else:
            self.highFreqEdit.setEnabled(True)

    def calcFilter(self):
        bandArr = [x.value() for x in (self.lowFreqEdit, self.highFreqEdit) if x.isEnabled() == True]
        return filterCalc(order=self.filterOrdEdit.value(),
                          bandarr=bandArr,
                          fs=self.fs,
                          btype=self.filterBandChooser.currentData(),
                          ftype=self.filterTypeChooser.currentData())

    def showFilterResponse(self):
        bandArr = [x.value() for x in (self.lowFreqEdit, self.highFreqEdit) if x.isEnabled() == True]
        b, a = self.calcFilter()
        w, h = signal.freqz(b, a)
        fig = plt.figure()
        ax1 = fig.add_subplot(111)
        ax1.set_title(label='Filter frequency response\n{}, {}, {}Hz, ord={}'.format(self.filterBandChooser.currentText(),
                                                                                     self.filterTypeChooser.currentText(),
                                                                                     bandArr,
                                                                                     self.filterOrdEdit.value()))
        ax1.plot(w*(self.fs/(2*np.pi)), 20 * np.log10(abs(h)), 'b')
        ax1.set_ylabel('Amplitude [dB]', color='b')
        ax1.set_xlabel('Frequency [Hz]')
        ax1.tick_params(axis='y', colors='b')
        ax2 = ax1.twinx()
        angles = np.unwrap(np.angle(h))
        ax2.plot(w*(self.fs/(2*np.pi)), angles, 'g')
        ax2.set_ylabel('Angle (radians)', color='g')
        ax2.tick_params(axis='y', colors='g')
        plt.grid()
        plt.axis('tight')
        plt.show()

    def process(self, inData):
        b, a = self.calcFilter()
        outData = []
        progStep = 100.0 / len(inData)
        prog = 0
        for data in inData:
            newData = signal.lfilter(b, a, data)
            outData.append(newData)
            prog = prog + progStep
            self.progress.emit(int(prog))
        return outData


'''

WINDOW

'''
class WindowGroup(AbstractProcessGroup):
    
    def __init__(self, title, fs):
        AbstractProcessGroup.__init__(self, title, fs)
        self.setupWindowLayout()

    def setupWindowLayout(self):
        winLayout = QHBoxLayout(self)
        wiinSettLayout = QFormLayout()
        winLayout.addLayout(wiinSettLayout)
        self.winLenEdit = QSpinBox()
        self.winLenEdit.setMaximum(10000) #do poprawki
        self.winLenEdit.setValue(self.fs/10)
        wiinSettLayout.addRow('Lenght (samples)', self.winLenEdit)
##        self.winOverEdit = QSpinBox()
##        self.winOverEdit.setMaximum(10000)
##        wiinSettLayout.addRow('Overlapping (samples)', self.winOverEdit)
##        self.winBackOverEdit = QSpinBox()
##        self.winBackOverEdit.setMaximum(10000)
##        wiinSettLayout.addRow('Back Overlapping (samples)', self.winBackOverEdit)

    def process(self, inData):
        self.winLen = self.winLenEdit.value()
##        winOver = self.winOverEdit.value()
        segNmbr = int(np.shape(inData)[1]/(self.winLen))
        progStep = 100.0 / len(inData)
        prog = 0

        outData = np.copy(inData)
        outData = [np.array_split(ch, segNmbr) for ch in outData]
        chi = 0
        for ch in outData:
            for seg in ch:
                proc = self.operation(seg)
                seg.fill(proc) 
            prog = prog + progStep
            self.progress.emit(int(prog))
            chi += 1

        outData = [np.concatenate(ch) for ch in outData]
        return outData
'''
AVERAGE
'''
class AverageGroup(WindowGroup):
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        return np.mean(seg)

'''
ENERGY
'''
class EnergyGroup(WindowGroup):   
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        sen = [s**2 for s in seg]
        return sum(sen)

'''
POWER
'''
class PowerGroup(WindowGroup):   
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        sen = [s**2 for s in seg]
        return sum(sen)/self.winLen
  
'''
PEAK2PEAK
'''
class Peak2PeakGroup(WindowGroup):
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        return np.max(seg)- np.min(seg)
'''
VARIANCE
'''
class VarianceGroup(WindowGroup):
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        avg = np.mean(seg)
        sq = [(s-avg)**2 for s in seg]
        return sum(sq)/self.winLen

'''
ENTROPY
'''
class EntropyGroup(WindowGroup):
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        try:
            sq = [s*np.log(abs(s)) for s in seg]
        except:
            print('log err in seg ', seg)
        return -sum(sq)

'''
SKEWNESS
'''
class SkewnessGroup(WindowGroup):
    def __init__(self, title, fs):
        WindowGroup.__init__(self, title, fs)

    def operation(self, seg):
        avg = np.mean(seg)
        nomp = [(s-avg)**3 for s in seg]
        denomp = [(s-avg)**2 for s in seg]

        nom = sum(nomp)/self.winLen
        denom = sum(denomp)/(self.winLen-1)**(3/2)
        return nom/denom
         

'''

STFT

'''
class STFTGroup(AbstractProcessGroup):

    winTypes = ('boxcar', 'triang', 'blackman', 'hamming', 'hann', 'bartlett',
                'flattop', 'parzen', 'bohman', 'blackmanharris', 'nuttall',
                'barthann', 'kaiser', 'gaussian', 'slepian', 'chebwin')
##    winParams = {'std' : 
##                 }

    defaultParam = {'maxFreq'  : 50,
                    'nPerSeg'  : 100,
                    'nOverlap' : 50}
    
    def __init__(self, title, fs):
        AbstractProcessGroup.__init__(self, title, fs)
        self.specWindows = {'gaussian' : ('Standard deviation', int, 0, 100, 7),
                            'kaiser' : ('Beta', int, 0, 100, 14),
                            'slepian' : ('Bandwidth', float, 0, 100, 0.3),
                            'chebwin' : ('Attenuation (dB)', int, 0, 1000, 100)
                            }
        self.setupSTFTLayout()

    def setupSTFTLayout(self):
        
        STFTSettLayout = QFormLayout(self)

        for winType in self.specWindows:
            if self.specWindows[winType][1] == int:
                paramEdit = QSpinBox()
            else:
                paramEdit = QDoubleSpinBox()
            paramEdit.setMinimum(self.specWindows[winType][2])
            paramEdit.setMaximum(self.specWindows[winType][3])
            paramEdit.setValue(self.specWindows[winType][4])
            paramLabel = QLabel(self.specWindows[winType][0])
            self.specWindows[winType] = [paramLabel, paramEdit]

        self.winTypeChooser = QComboBox()
        for winType in self.winTypes:
            self.winTypeChooser.addItem(winType)

        self.winTypeChooser.currentTextChanged.connect(self.windowChanged)
        self.winTypeChooser.setCurrentText('hann')
        STFTSettLayout.addRow('Window type', self.winTypeChooser)

    

        self.maxFreqEdit = QSpinBox()
        self.maxFreqEdit.setMaximum(self.fs/2)
        self.maxFreqEdit.setValue(self.defaultParam['maxFreq'])
        STFTSettLayout.addRow('Max output Frequency (Hz)', self.maxFreqEdit)

        self.nPerSegEdit = QSpinBox()
        self.nPerSegEdit.setMaximum(1000)
        self.nPerSegEdit.setValue(self.defaultParam['nPerSeg'])
        STFTSettLayout.addRow('Length of segment (samples)', self.nPerSegEdit)

        self.nOverlapEdit = QSpinBox()
        self.nOverlapEdit.setMaximum(1000)
        self.nOverlapEdit.setValue(self.defaultParam['nOverlap'])
        STFTSettLayout.addRow('Overlap (samples)', self.nOverlapEdit)

        for winType in self.specWindows:
            paramLabel = self.specWindows[winType][0]
            paramEdit = self.specWindows[winType][1]
            STFTSettLayout.addRow(paramLabel, paramEdit)

    def windowChanged(self):
        curWindow = self.winTypeChooser.currentText()
        for winType in self.specWindows:
            self.specWindows[winType][0].setVisible(False)
            self.specWindows[winType][1].setVisible(False)
        if curWindow in self.specWindows:
            self.specWindows[curWindow][0].setVisible(True)
            self.specWindows[curWindow][1].setVisible(True)

    def process(self, inData):

        progStep = 100.0 / len(inData)
        prog = 0
        outData = []
        chi = 0
        
        winName = (self.winTypeChooser.currentText())
        if winName in self.specWindows:
            winParam = self.specWindows[winName][1].value()
            window = (winName, winParam)
        else:
            window = winName
            
        maxFreq = self.maxFreqEdit.value()
        for chData in inData:
            f, t, Zxx = signal.stft(chData, fs=self.fs,
                                    nperseg=self.nPerSegEdit.value(),
                                    noverlap=self.nOverlapEdit.value(),
                                    window=window)
##            f = [fi for fi in f if float(fi) > minFreq and float(fi) < maxFreq]
            f = [fi for fi in f if float(fi) <= maxFreq]
            Zxx = Zxx[:len(f)]
            t *= self.fs
            Zxx = np.abs(Zxx)

            outData.append([f, t, Zxx])
            prog = prog + progStep
            self.progress.emit(int(prog))
            chi += 1

        return outData

'''

CWT

'''
class CWTGroup(AbstractProcessGroup):

    winTypes = ('boxcar', 'triang', 'blackman', 'hamming', 'hann', 'bartlett',
                'flattop', 'parzen', 'bohman', 'blackmanharris', 'nuttall',
                'barthann', 'kaiser', 'gaussian', 'slepian', 'chebwin')
##    winParams = {'std' : 
##                 }

    defaultParam = {'maxScale'  : 30,
                    'minScale'  : 1,
                    'nOverlap' : 50}
    
    def __init__(self, title, fs):
        AbstractProcessGroup.__init__(self, title, fs)
        self.specWindows = {'gaussian' : ('Standard deviation', int, 0, 100, 7),
                            'kaiser' : ('Beta', int, 0, 100, 14),
                            'slepian' : ('Bandwidth', float, 0, 100, 0.3),
                            'chebwin' : ('Attenuation (dB)', int, 0, 1000, 100)
                            }
        self.setupCWTLayout()

    def setupCWTLayout(self):
        
        CWTSettLayout = QFormLayout(self)

##        for winType in self.specWindows:
##            if self.specWindows[winType][1] == int:
##                paramEdit = QSpinBox()
##            else:
##                paramEdit = QDoubleSpinBox()
##            paramEdit.setMinimum(self.specWindows[winType][2])
##            paramEdit.setMaximum(self.specWindows[winType][3])
##            paramEdit.setValue(self.specWindows[winType][4])
##            paramLabel = QLabel(self.specWindows[winType][0])
##            self.specWindows[winType] = [paramLabel, paramEdit]
##
##        self.winTypeChooser = QComboBox()
##        for winType in self.winTypes:
##            self.winTypeChooser.addItem(winType)
##
##        self.winTypeChooser.currentTextChanged.connect(self.windowChanged)
##        self.winTypeChooser.setCurrentText('hann')
##        STFTSettLayout.addRow('Window type', self.winTypeChooser)

        self.minScaleEdit = QSpinBox()
        self.minScaleEdit.setMaximum(self.fs/2)
        self.minScaleEdit.setValue(self.defaultParam['minScale'])
        CWTSettLayout.addRow('Min output Scale', self.minScaleEdit)

        self.maxScaleEdit = QSpinBox()
        self.maxScaleEdit.setMaximum(self.fs/2)
        self.maxScaleEdit.setValue(self.defaultParam['maxScale'])
        CWTSettLayout.addRow('Max output Scale', self.maxScaleEdit)

##
##        self.nOverlapEdit = QSpinBox()
##        self.nOverlapEdit.setMaximum(1000)
##        self.nOverlapEdit.setValue(self.defaultParam['nOverlap'])
##        STFTSettLayout.addRow('Overlap (samples)', self.nOverlapEdit)

##        for winType in self.specWindows:
##            paramLabel = self.specWindows[winType][0]
##            paramEdit = self.specWindows[winType][1]
##            STFTSettLayout.addRow(paramLabel, paramEdit)

    def waveletChanged(self):
        curWindow = self.winTypeChooser.currentText()
        for winType in self.specWindows:
            self.specWindows[winType][0].setVisible(False)
            self.specWindows[winType][1].setVisible(False)
        if curWindow in self.specWindows:
            self.specWindows[curWindow][0].setVisible(True)
            self.specWindows[curWindow][1].setVisible(True)

    def process(self, inData):

        progStep = 100.0 / len(inData)
        prog = 0
        outData = []
        chi = 0
        
##        winName = (self.winTypeChooser.currentText())
##        if winName in self.specWindows:
##            winParam = self.specWindows[winName][1].value()
##            window = (winName, winParam)
##        else:
##            window = winName
##            
##        maxFreq = self.maxFreqEdit.value()
        
        widths = np.arange(self.minScaleEdit.value(), self.maxScaleEdit.value()+1)
        wavelet = signal.ricker
##        wavelet = signal.morlet
        for chData in inData:            
            cwtmatr = signal.cwt(chData, wavelet, widths)
##            print(type(cwtmatr))
##            print(np.shape(cwtmatr))
            cwtmatr = abs(cwtmatr)
            outData.append(cwtmatr)
            prog = prog + progStep
            self.progress.emit(int(prog))
            chi += 1

        return outData

'''

THRESHOLD

'''
class ThresholdGroup(AbstractProcessGroup):
    
    def __init__(self, title, fs):
        AbstractProcessGroup.__init__(self, title, fs)
        self.setupLayout()

    def setupLayout(self):
        mainLayout = QFormLayout(self)

        self.thresEdit = QSpinBox()
        self.thresEdit.setMaximum(999999)
        self.thresEdit.setValue(0)
        mainLayout.addRow('Threshold value', self.thresEdit)

    def process(self, inData):
        thresh = self.thresEdit.value()
        outData = []
        progStep = 100.0 / len(inData)
        prog = 0
        for chData in inData:
            a = [1 if a_ > thresh else 0 for a_ in chData]
            outData.append(np.array(a))
            prog = prog + progStep
            self.progress.emit(int(prog))
        return outData


'''

DETREND

'''
class DetrendGroup(AbstractProcessGroup):
    
    def __init__(self, title, fs):
        AbstractProcessGroup.__init__(self, title, fs)
        self.setupLayout()

    def setupLayout(self):
        mainLayout = QFormLayout(self)

        self._toggle = True
        self.constCheck = QCheckBox ('Constant')
        mainLayout.addRow(self.constCheck)
        self.constCheck.setChecked(True)
        self.lineCheck = QCheckBox ('Linear')
        mainLayout.addRow(self.lineCheck)

        self.constCheck.clicked.connect(self.toggle)
        self.lineCheck.clicked.connect(self.toggle)
        
    def toggle(self):
        self._toggle = not self._toggle
        self.constCheck.setChecked(self._toggle)
        self.lineCheck.setChecked(not self._toggle)

    def process(self, inData):
        if self.constCheck.isChecked():
            dType = 'constant'
        elif self.lineCheck.isChecked():
            dType = 'linear'
        print(dType)
        outData = []
        progStep = 100.0 / len(inData)
        prog = 0
        for chData in inData:
            det = signal.detrend(chData, type=dType)
            outData.append(det)
            prog = prog + progStep
            self.progress.emit(int(prog))
        return outData










        

