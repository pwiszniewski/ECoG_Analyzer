import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.style as mplstyle
from PySide2 import QtCore, QtWidgets
from PySide2.QtWidgets import (QApplication, QMainWindow, QAction, QListWidget,
                               QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                               QTreeWidgetItemIterator, QScrollBar,
                               QDialog, QListWidgetItem, QPushButton, QInputDialog,
                               QMenu)

from data import *
from PySide2.QtGui import QIcon
'''

################## CURSOR ##################

'''
class Cursor():
    def __init__(self, fig, color):
        self.fig = fig
        self.ly = []
        self.xPos = 0
        self.color = color

    def refreshAxes(self):
        self.ly.clear()
        for ax in self.fig.axes:
            self.addAxes(ax)

    def addAxes(self, ax):
        line = ax.axvline(linewidth=0.9, color=self.color, label='_Cursor')
        line.set_gid('ly')
        self.ly.append(line)

    def setXPos(self, x):
        for line in self.ly:
            line.set_xdata(x)
        self.xPos = x

    def getXPos(self):
        return self.xPos
    

'''

################## MARKER SET ##################

'''
class MarkerSet(object):
    def __init__(self, mcolor):
        self.mcolor = mcolor
        self.markers = [None, None]
        self.span = None
        self.ann = None
        self.scale = 4
        
    def setMarker(self, ax, x, num):
        if self.markers[1]:
            self.clear()
        if num == 0:
            self.markers[0] = ax.axvline(linewidth=1, color=self.mcolor)
            self.markers[0].set_gid('mark')
            self.markers[0].set_xdata(x)
        elif num == 1:
            self.markers[1] = ax.axvline(linewidth=1, color=self.mcolor)
            self.markers[1].set_gid('mark')
            self.markers[1].set_xdata(x)

    def drawSpan(self, ax, x):
        if self.span:
            self.span.remove()
            self.ann.remove()
        self.span = ax.axvspan(self.markers[0].get_xdata(), x,
                               color=self.mcolor, alpha=0.5)
        diff = abs(int(x-self.markers[0].get_xdata()))
        self.ann = ax.annotate(str(diff*self.scale)+' ms',
                               xy=(0, 0.98), xycoords="axes fraction",
                               xytext=(0, -20), textcoords='offset pixels', 
                               va="top", ha="left",
                               bbox=dict(boxstyle="round", fc=self.mcolor, alpha=0.85))

    def isFirstMarkerOnly(self):
        return self.markers[0] != None and self.markers[1] == None

    def areBothMarkers(self):
        return self.markers[0] and self.markers[1]

    def clear(self):
        for mark in self.markers:
            if mark:
                try:
                    mark.remove()
                except:
                    pass
        if self.span:
            try:
                self.span.remove()
            except:
                pass
        if self.ann:
            try:
                self.ann.remove()
            except:
                pass
        self.markers = [None, None]
        self.span = None
        self.ann = None

'''

################## NAVIGATION TOOLBAR ##################

'''
class MPLNavigationToolbar(NavigationToolbar):
    def __init__(self, canvas, parent=None, coordinates=True):
        NavigationToolbar.__init__(self, canvas, parent, coordinates)
        self.colors = {'ly': '#7affce',
                       'mark': '#ffac7c'}
        self.markSet = MarkerSet(self.colors['mark'])
        

    def _init_toolbar(self):
        super(MPLNavigationToolbar, self)._init_toolbar()
        self.addSeparator()
        a = QAction('MEAS')
        a.setShortcut(QtCore.Qt.CTRL + QtCore.Qt.Key_A)
        self.insertAction(self._actions['zoom'], a)
        self._actions['measure'] = a
        a.setToolTip('Measure time difference')
        a.setCheckable(True)
        a.triggered.connect(self.measure)
        a.setIcon(QIcon('Resources\\measure.png'))

    def _update_buttons_checked(self):
        super(MPLNavigationToolbar, self)._update_buttons_checked()
        self._actions['measure'].setChecked(self._active == 'MEAS')

    def measure(self):
        if self._active == 'MEAS':
            self.canvas.setCursor(Qt.ArrowCursor)
            self.markSet.clear()
            self._active = None
            
        else:
            self._active = 'MEAS'
            self.canvas.setCursor(Qt.SizeHorCursor)

        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''

        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''

        if self._active:
            self._idPress = self.canvas.mpl_connect(
                'button_press_event', self.press_measure)
            self._idRelease = self.canvas.mpl_connect(
                'button_release_event', self.release_measure)
            self.mode = 'measure'
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self.set_message(self.mode)
        self._update_buttons_checked()

    def press_measure(self, event):
        if not event.inaxes:
            return
        if event.button == 1:
            self._button_pressed = 1
        elif event.button == 3:
            self._button_pressed = 3
        else:
            self._button_pressed = None
            return

        if self._button_pressed == 1:
            self.markSet.setMarker(event.inaxes, event.xdata, 0)
            self.curAxes = event.inaxes
        elif self._button_pressed == 3:
            if self.markSet.areBothMarkers():
                self.markSet.clear()

        self.canvas.mpl_connect('motion_notify_event', self.drag_measure)
                
        self.canvas.draw()
        self.press(event)

    def release_measure(self, event):
        if not event.inaxes:
            self.markSet.setMarker(self.curAxes, event.xdata, 1)
            return
        if event.button == 1:
            self.markSet.setMarker(self.curAxes, event.xdata, 1)
        self.canvas.draw()
        self.release(event)

    def drag_measure(self, event):
        if not event.inaxes:
            return
        if self.markSet.isFirstMarkerOnly():
            self.markSet.drawSpan(self.curAxes, event.xdata)



