# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from cdp import MPUAccelerometerV2
from network_objects import *
from settings import *


class PlotAccel(pg.GraphicsWindow):
    type = MPUAccelerometerV2.type

    def __init__(self, serial):

        pg.GraphicsWindow.__init__(self)

        self.setWindowTitle('CUWB Monitor - Position Accel Plot ID: 0x{:08X}'.format(serial))
        self.resize(900, 500)
        self.serial = serial

        self.xyz_graph = self.addPlot(title='Accelerometer XYZ')
        self.xyz_graph.addLegend()
        self.xyz_graph.showGrid(x=True, y=True)
        self.x = self.xyz_graph.plot(pen='r', name='X')
        self.y = self.xyz_graph.plot(pen='g', name='Y')
        self.z = self.xyz_graph.plot(pen='b', name='Z')

        self.timer = self.startTimer(QPLOT_FREQUENCY)

        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[MPUAccelerometerV2.type]
        self.data = deque([], TRAIL_LENGTH)
        self.time = deque([], TRAIL_LENGTH)
        _current_size = len(UwbNetwork.nodes[self.serial].cdp_pkts[MPUAccelerometerV2.type])
        for idx in range(_current_size):
            self.data.append(UwbNetwork.nodes[self.serial].cdp_pkts[MPUAccelerometerV2.type][idx - _current_size].get_xyz())
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[MPUAccelerometerV2.type][idx - _current_size])

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.close()
            return

        _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[MPUAccelerometerV2.type] - self.last_count
        self.last_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[MPUAccelerometerV2.type]
        if _current_size == 0: return

        for idx in range(_current_size):
            self.data.append(UwbNetwork.nodes[self.serial].cdp_pkts[MPUAccelerometerV2.type][idx - _current_size].get_xyz())
            self.time.append(UwbNetwork.nodes[self.serial].cdp_pkts_time[MPUAccelerometerV2.type][idx - _current_size])

        _data = np.array(self.data)
        _times = np.array(self.time)
        self.x.setData(_times, _data[:,0])
        self.y.setData(_times, _data[:,1])
        self.z.setData(_times, _data[:,2])


    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()
