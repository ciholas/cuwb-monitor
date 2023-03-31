# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System Libraries
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore
from functools import partial

#Local Libraries
from device_data_items import GyroscopeCalibrationResponse
from network_objects import *
from generic_plots import *
from settings import *

class PlotGyroscopeCalibrationResponse(pg.GraphicsLayoutWidget):
    type = GyroscopeCalibrationResponse.type

    def __init__(self, device):

        pg.GraphicsLayoutWidget.__init__(self)

        self.setWindowTitle("CUWB Monitor- Gyroscope Calibration Response Device 0x{:08X}".format(device.id))
        self.device = device
        self.running = True
        self.resize(600,400)
        self.prev_count = 0

        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)

        self.x_azimuth = 0
        self.y_azimuth = 0
        self.z_azimuth = 0
        self.last_azimuth_update = time.monotonic()

        self.graph = self.addPlot(title='GyroScope XYZ', row=0, col=0, colspan=3)
        self.graph.setYRange(-15, 15)
        self.graph.showGrid(x=True, y=True)

        self.legend = self.graph.addLegend()
        self.plot_x = self.graph.plot(name='X', pen=pg.mkPen('r', width=2))
        self.plot_y = self.graph.plot(name='Y', pen=pg.mkPen('g', width=2))
        self.plot_z = self.graph.plot(name='Z', pen=pg.mkPen('b', width=2))

        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.running = True

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.running = False
            self.close()
            return

        if self.type in self.device.counts.keys() and self.device.counts[self.type] !=0:
            curr_count = self.device.counts[self.type]
            if curr_count - self.prev_count > 1000: self.prev_count = curr_count-1000
            while self.prev_count < curr_count:
                index = self.prev_count - curr_count
                packet = self.device.packets[self.type][index]
                time = self.device.times[self.type][index]
                scale = packet.scale/2147483647.0
                if self.prev_count == 0:
                    #Because this data type does not send and receive a packet often whenever there are no points, a "fake point" is
                    #placed sligtly behind in time so that the data of the first point can become visible to the user.
                    self.update_data(packet.x*scale, packet.y*scale, packet.z*scale, time-.1)
                self.update_data(packet.x*scale, packet.y*scale, packet.z*scale, time)
                self.prev_count += 1

        if len(self.t_data) < 2: return

        self.plot_x.setData(self.t_data, self.x_data)
        self.plot_y.setData(self.t_data, self.y_data)
        self.plot_z.setData(self.t_data, self.z_data)

    def update_data(self, x, y, z, t):

        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        self.t_data.append(t)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)
