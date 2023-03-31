# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

#System Libraries
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore
from functools import partial

#Local Libraries
from device_data_items import MagnetometerCalibrationResponse
from network_objects import *
from rolling_std import *
from settings import *

class PlotMagnetometerCalibrationResponse(pg.GraphicsLayoutWidget):
    type = MagnetometerCalibrationResponse.type

    def __init__(self, device):

        pg.GraphicsLayoutWidget.__init__(self)

        self.setWindowTitle("CUWB Monitor- Magnetometer Calibration Response Device 0x{:08X}".format(device.id))
        self.device = device
        self.running = True
        self.resize(600,400)
        self.prev_count = 0

        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)
        self.magnitude_data = deque([], TRAIL_LENGTH)

        self.avg_magnitude = RollingStandardDeviationDeque(200)

        self.graph = self.addPlot(title='Magnetometer XYZ', row=0, col=0, colspan=3)
        self.graph.setYRange(-100, 100)
        self.graph.showGrid(x=True, y=True)

        self.legend = self.graph.addLegend()
        self.plot_x = self.graph.plot(name='X', pen=pg.mkPen('r', width=2))
        self.plot_y = self.graph.plot(name='Y', pen=pg.mkPen('y', width=2))
        self.plot_z = self.graph.plot(name='Z', pen=pg.mkPen('b', width=2))
        self.plot_mag = self.graph.plot(name='MagXYZ', pen=pg.mkPen('w', width=1))

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        if self.type in self.device.counts.keys() and self.device.counts[self.type] !=0:
            curr_count = self.device.counts[self.type]
            if curr_count - self.prev_count > 1000: self.prev_count = curr_count-1000
            while self.prev_count < curr_count:
                index = self.prev_count - curr_count
                packet = self.device.packets[self.type][index]
                time = self.device.times[self.type][index]
                if self.prev_count == 0:
                    #Because this data type does not send and receive a packet often whenever there are no points, a "fake point" is
                    #placed sligtly behind in time so that the data of the first point can become visible to the user.
                    self.updateData(packet.x, packet.y, packet.z, time-.1)
                self.updateData(packet.x, packet.y, packet.z, time)
                self.prev_count += 1

        if len(self.t_data) > 1:
            self.plot_x.setData(self.t_data, self.x_data)
            self.plot_y.setData(self.t_data, self.y_data)
            self.plot_z.setData(self.t_data, self.z_data)
            self.plot_mag.setData(self.t_data, self.magnitude_data)

    def updateData(self, x, y, z, t):

        _magnitude = np.linalg.norm([x,y,z])
        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        self.t_data.append(t)
        self.magnitude_data.append(_magnitude)

        if _magnitude > 8 and _magnitude < 35:
            self.avg_magnitude.push(_magnitude)

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False

    def reset(self):
        self.x_data = deque([], TRAIL_LENGTH)
        self.y_data = deque([], TRAIL_LENGTH)
        self.z_data = deque([], TRAIL_LENGTH)
        self.t_data = deque([], TRAIL_LENGTH)
        self.magnitude_data = deque([], TRAIL_LENGTH)
