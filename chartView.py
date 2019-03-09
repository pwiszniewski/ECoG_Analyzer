import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.style as mplstyle
from chartTools import MPLNavigationToolbar, Cursor
from PySide2 import QtCore
from PySide2.QtCore import Signal
from PySide2 import QtWidgets


'''

################## MAIN CHART ##################

'''
class MyMPLChart(FigureCanvas):

    viewRangeChanged = Signal(int)
    xRangeChanged = Signal(int, int)
    chartDrawn = Signal(int, int)
    xScaleChanged = Signal(int)
    
    def __init__(self, parent=None, width=10, height=10, dpi=100):
        self.dx = 0
        self.autoscaleY = False
        self.isLegendVisible = False
        self.ly = []
        self.colors = {'ly': '#7affce',
                       'mark': '#ffac7c'}
        self.xmin = 0
        self.xmax = 0
        self.vRange = 0
        self.xScale = 1
        self.dataMax = 0
        self.plotsPerAxes = 0
 
        
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.fig.subplots_adjust(top=0.96, bottom=0.06, left=0.055,
                                     right=0.985, hspace=0.01, wspace=0.2)
        axes = self.fig.add_subplot(111)

        mplstyle.use(['fast', 'bmh'])
        plt.rcParams.update({'figure.autolayout': True})
        self.cursor = Cursor(self.fig, self.colors['ly'])

        self.stat = None

        self.mpl_connect('figure_enter_event', self.enter_figure)
        self.mpl_connect('figure_leave_event', self.leave_figure)
##        self.mpl_connect('button_press_event', self.on_press)
##        self.mpl_connect('button_release_event', self.on_release)
        self.mpl_connect('scroll_event', self.on_scroll)
        self.mpl_connect('motion_notify_event', self.mouse_move)
        self.mpl_connect('key_press_event', self.key_press)
        self.mpl_connect('key_release_event', self.key_release)
##        self.mpl_connect('axes_enter_event', self.enter_axes)
##        self.mpl_connect('axes_leave_event', self.leave_axes)


    '''
    Events
    '''
    def enter_axes(self, event):
        print('enter_axes', event.inaxes)
        mplstyle.use(['fast', 'bmh'])
        event.canvas.draw()

    def leave_axes(self, event):
        print('leave_axes', event.inaxes)
        event.inaxes.patch.set_facecolor('white')
        event.canvas.draw()
            
    def on_press(self, event):
        print('you pressed', event.button, event.xdata, event.ydata, 'key', event.key, 'GUI', event.guiEvent)
            
    def on_release(self, event):
        print('you released', event.button, event.xdata, event.ydata)

    def on_scroll(self, event):
        if event.button == 'down':
            self.scrollForward()
        elif event.button == 'up':
            self.scrollBackward()

    def key_press(self, event):
        for ax in self.fig.axes:
            for line in ax.get_lines():
                if line.get_gid() == 'ly':
                    line.set_color(self.colors['mark'])
                    self.draw()

    def key_release(self, event):
        for ax in self.fig.axes:
            for line in ax.get_lines():
                if line.get_gid() == 'ly':
                    line.set_color(self.colors['ly'])
                    self.draw()

    def enter_figure(self, event):
        self.setFocus()
        self.draw()

    def leave_figure(self, event):
        self.clearFocus()
        self.draw()

    def mouse_move(self, event):
        if not event.inaxes:
            return
        x = event.xdata
        self.cursor.setXPos(x)
        self.draw()


    '''
    Data
    '''
    def XsetData(self, data, allCh, allSamp):
        self.data = data
        self.allChannels = allCh
        self.xmin = 0
        self.xmax = allSamp

    '''
    Plots
    '''
    
    def drawAllChannels(self, dataDict, sigName, xLabel='Time [min:sec]', xRange=None, color='#9c0e4f',
                        mask=None, maskColor='#fca983'):
##        start = time.time()
        chNames = list(dataDict.keys())

        firstChType = type(dataDict[list(dataDict.keys())[0]])
        firstChShape = np.shape(dataDict[list(dataDict.keys())[0]])
        
        if firstChType is not np.ndarray or len(firstChShape) > 1:
            return
        self.fig.clear()
        allCh = len(dataDict)
        if self.plotsPerAxes == 0:
            nPlots = allCh
        else:
            nPlots = self.plotsPerAxes
        nCols = int(allCh/nPlots)
        

        axarr = self.fig.subplots(nrows=1,
                                  ncols=nCols,
                                  sharex=True)
        if len(dataDict) == nPlots:
            axarr = [axarr]
        
        # Calculate offsets
        self.offsets = np.empty(allCh, dtype=np.float64)
        self.yMin = np.empty(allCh, dtype=np.float64)
        self.yMax = np.empty(allCh, dtype=np.float64)
        
        self.offsets[allCh-1] = abs(np.amin(dataDict[chNames[allCh-1]]))
        self.yMin[allCh-1] = np.amin(dataDict[chNames[allCh-1]])
        self.yMax[allCh-1] = np.amax(dataDict[chNames[allCh-1]])
        for ch in range(allCh-2, -1, -1):
            self.yMin[ch] = np.amin(dataDict[chNames[ch]])
            self.yMax[ch] = np.amax(dataDict[chNames[ch]])
            self.offsets[ch] = (abs(self.yMin[ch]) +
                               self.yMax[ch+1] +
                               self.offsets[ch+1] + 1)
        if mask is not None:                     
            xMask = np.arange(len(mask[0]))
        
        for nAx in range(len(axarr)):
            chMin = nAx*nPlots
            chMax = (nAx+1)*nPlots
            
            for ch in range(chMin, chMax):
                axarr[nAx].plot(dataDict[chNames[ch]]+self.offsets[ch],
                                    color=color,
                                    linewidth=0.9,
                                    picker=5)
                if mask is not None:
                    ylim = axarr[nAx].get_ylim()
                    axarr[nAx].fill_between(xMask, self.offsets[ch]+self.yMin[ch],
                                            self.offsets[ch]+self.yMax[ch],
                                            where=mask[ch]==1,
                                            color=maskColor, alpha=0.5)

            axarr[nAx].set_yticks(self.offsets[chMin : chMax])
            axarr[nAx].set_yticklabels(chNames[chMin : chMax], color='b')
            axarr[nAx].set_xlabel(xLabel, size='small')
            if xRange is not None:
                    axarr[nAx].set_xlim(xRange[0], xRange[1])
            else:
                    axarr[nAx].set_xlim(self.xmin, self.xmax)
            axarr[nAx].grid(True)

        axarr[-1].xaxis.set_major_formatter(self.formatter)

        self.fig.suptitle(sigName, fontsize=10, color='b')

        self.draw()
##        end = time.time()
##        print('drawAllChannels time:', end - start)
        self.cursor.refreshAxes()
        self.dataMax = len(axarr[0].get_lines()[0].get_data()[0])
        self.chartDrawn.emit(0, self.dataMax)
        self.stat = 'AllCh'
        self.activeData = sigName

    def drawOneChannel(self, dataDict, chName, xLabel='Time [min:sec]', yLabel='[uV]',
                       xRange=None, colors='#4dea84', mask=None, maskColor='#fff9ed'):
##        start = time.time()
        self.fig.clear()
        axarr = self.fig.subplots(len(dataDict), ncols=1, sharex=True,
                                              squeeze=True)
                
        if len(dataDict) == 1:
            axarr = [axarr]
            
        i = 0
        j = 0
        for dName in dataDict:
            noMask = False
            for d in dataDict[dName]:
                
                dataToPlot = dataDict[dName][d]
        
                if type(dataToPlot) == np.ndarray:
                    print(len(np.shape(dataToPlot)))
                    
                    if len(np.shape(dataToPlot)) == 1:
                        # 1D
                        axarr[i].plot(dataToPlot,
                                      label=d,
                                      linewidth=0.9,
                                      color=colors[j])
                        axarr[i].set_gid('2D')
                        axarr[i].set_ylabel(yLabel)
                    else:
                        # cwt
                        axarr[i].imshow(dataToPlot, aspect='auto',
                                        cmap='viridis')
##                                        cmap='seismic')
##                        axarr[i].imshow(dataToPlot, cmap='PRGn', aspect='auto',
##                                    vmax=abs(dataToPlot).max(), vmin=-abs(dataToPlot).max(),
##                                    )
                        noMask = True
                else:
                    # More than 1D
                    axarr[i].pcolormesh(dataToPlot[1],
                                        dataToPlot[0],
                                        dataToPlot[2],
                                        cmap='plasma')
                    axarr[i].set_ylabel('Frequency [Hz]')
                    noMask = True
                j += 1
            if mask is not None and not noMask:
                x = np.arange(len(mask))
                ylim = axarr[i].get_ylim()
                axarr[i].fill_between(x, ylim[0], ylim[1], where=mask==1,
                                      color=maskColor, alpha=0.5)
                    
##            mline.set_gid('main')
            axarr[i].set_title(dName, visible=False)
    
            if xRange is not None:
                axarr[i].set_xlim(xRange[0], xRange[1])
            else:
                axarr[i].set_xlim(self.xmin, self.xmax)

            if axarr[i].get_gid() == '2D':
                if self.autoscaleY == True:
                        visLines = [visLine.get_data()[1][self.xmin:self.xmax] for visLine in axarr[i].get_lines() if visLine.get_gid() != 'ly' and visLine.get_gid() != 'mark']
                else:
                        visLines = [visLine.get_data()[1] for visLine in axarr[i].get_lines() if visLine.get_gid() != 'ly' and visLine.get_gid() != 'mark']
                visMax = [np.max(line) for line in visLines]
                visMin = [np.min(line) for line in visLines]
                axarr[i].set_ylim(np.min(visMin), np.max(visMax))
        
                first_legend = axarr[i].legend(loc='upper right')
                axarr[i].add_artist(first_legend)
                first_legend.set_visible(self.isLegendVisible)
                
            axarr[i].annotate(dName, xy=(0, 0.99), xycoords="axes fraction",
                                  va="top", ha="left",
                                  bbox=dict(boxstyle="round", fc="#edfffe"))
            axarr[i].tick_params(labelbottom=False)
            
            axarr[i].grid(True)
            i += 1 
        axarr[-1].tick_params(labelbottom=True)
        axarr[-1].xaxis.set_major_formatter(self.formatter)       
        self.fig.suptitle(chName, color='b')
        axarr[-1].set_xlabel(xLabel)
        self.draw()
        if xRange is not None:
                self.xmin = xRange[0]
                self.xmax = xRange[1]
##        end = time.time()
##        print('drawOneChannel time:', end - start)
        self.cursor.refreshAxes()
        self.dataMax = len(axarr[0].get_lines()[0].get_data()[0])
        self.chartDrawn.emit(0, self.dataMax)
        self.stat = 'OneCh'
        self.activeCh = chName

        
    def setXRange(self, xmin, xmax):
##        start = time.time()
        if self.stat == 'AllCh':
            self.fig.axes[0].set_xlim(xmin, xmax)
        elif self.stat == 'OneCh':
            self.fig.axes[0].set_xlim(xmin, xmax)
            for ax in self.fig.axes:
##                ax.set_xlim(xmin, xmax)            
                if (self.autoscaleY == True
                    and ax.get_gid() == '2D'):
                    visLines = [visLine.get_data()[1][xmin:xmax] for visLine in ax.get_lines() if visLine.get_gid() != 'ly' and visLine.get_gid() != 'mark']
                    visMax = [np.max(line) for line in visLines]
                    visMin = [np.min(line) for line in visLines]
                    ax.set_ylim(np.min(visMin), np.max(visMax))
        self.fig.axes[-1].xaxis.set_major_formatter(self.formatter)
        self.draw() 
##        end = time.time()
        self.xmin = xmin
        self.xmax = xmax
        self.xRangeChanged.emit(xmin, xmax)
##        print('setXViewRange time:', end - start)

    def setXScale(self, newScale):
        self.xScale = newScale
        self.formatter = matplotlib.ticker.FuncFormatter(lambda ms, x: time.strftime('%M:%S', time.gmtime(ms // newScale)))
        self.xScaleChanged.emit(newScale)

    def scrollForward(self):
        newXMax = self.xmax+self.dx
        if newXMax <= self.dataMax:
            self.cursor.setXPos(self.cursor.getXPos()+self.dx)
            self.setXRange(self.xmin+self.dx, newXMax)
    
    def scrollBackward(self):
        newXMin = self.xmin-self.dx
        if newXMin >= 0:
            self.cursor.setXPos(self.cursor.getXPos()-self.dx)
            self.setXRange(newXMin, self.xmax-self.dx)
 

    def setScrollStep(self, step):
        self.dx = step

    def setViewRange(self, newRange):
        self.setXRange(self.xmin, self.xmin + newRange)
        self.vRange = newRange
        self.viewRangeChanged.emit(newRange)

    def getViewRange(self):
        return self.vRange
    
    def setAutoscaleY(self, isOn):
        self.autoscaleY = isOn
        if self.stat == 'OneCh':
            for ax in self.fig.axes:
                if ax.get_gid() == '2D':
                    if self.autoscaleY == True:
                        visLines = [visLine.get_data()[1][self.xmin:self.xmax] for visLine in ax.get_lines() if visLine.get_gid() != 'ly' and visLine.get_gid() != 'mark']
                    else:
                        visLines = [visLine.get_data()[1] for visLine in ax.get_lines() if visLine.get_gid() != 'ly' and visLine.get_gid() != 'mark']
                    visMax = [np.max(line) for line in visLines]
                    visMin = [np.min(line) for line in visLines]
                    ax.set_ylim(np.min(visMin), np.max(visMax))
            self.draw()

    def setPlotsPerAxes(self, nPlots):
        self.plotsPerAxes = nPlots
                    

    def getLegendVisible(self):
        return self.isLegendVisible

    def setLegendVisible(self, isOn):
        if isOn != self.isLegendVisible:
            for ax in self.fig.axes:
                for legend in ax.artists:
                    legend.set_visible(isOn)
            self.draw()
            self.isLegendVisible = isOn
        
    def getAutoscaleY(self):
        return self.autoscaleY

    def closeAll(self):
        self.fig.clear()
        
