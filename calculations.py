import sys
import numpy as np
from scipy import signal
from PySide2.QtWidgets import (QDialog, QComboBox, QGridLayout, QLabel,
                               QHBoxLayout, QGroupBox, QFormLayout,
                               QLineEdit, QFrame, QSpinBox, QDialogButtonBox,
                               QPushButton, QVBoxLayout, QStackedLayout,
                               QErrorMessage)
from PySide2.QtCore import Qt

def filterCalc(order, bandarr, fs, btype, ftype):
    nyq = 0.5 * fs
    bandarr = [i/nyq for i in bandarr]
    if ftype == 'butter':
        b, a = signal.butter(order, bandarr, btype=btype, analog=False)
    if ftype == 'bessel':
        b, a = signal.bessel(order, bandarr, btype=btype)
    return b, a
