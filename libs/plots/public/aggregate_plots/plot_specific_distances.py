# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from collections import deque
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import *
from network_objects import *
from settings import *


class PlotSpecificDistances(pg.LayoutWidget):
    type = 'SpecificDistancesPlot'

    def __init__(self):

        pg.LayoutWidget.__init__(self)

        self.setWindowTitle('CUWB Monitor - Specific Distances Plotting')
        self.resize(900,500)

        self.serial_a = pg.ComboBox(self)
        self.addWidget(self.serial_a, row=0, col=0)

        self.serial_b = pg.ComboBox(self)
        self.addWidget(self.serial_b, row=0, col=1)

        self.add_button = QtWidgets.QPushButton('Add')
        self.add_button.clicked.connect(self.add_plot)
        self.addWidget(self.add_button, row=0, col=2)

        self.distance_graph = pg.PlotWidget(title='Distance (m) vs Time (s)')
        self.legend = self.distance_graph.addLegend()
        self.distance_graph.showGrid(x=True, y=True)
        self.addWidget(self.distance_graph, row=1, col=0, colspan=3)

        self.available_devices = []
        self.device_pairs = []
        self.distance_data = dict()
        self.timestamp_data = dict()
        self.distance_plots = dict()
        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 's', (0, 51, 0), (127, 0, 255), (255, 127, 0), (0, 255, 127), (102, 0, 0), 'w', 'l']
        self.color_offset = 0

        self.show()

        self.network_serials = dict()
        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def add_plot(self):
        if self.serial_a.value() != self.serial_b.value():
            device_a = self.serial_a.value()
            device_b = self.serial_b.value()
            pair = (device_a, device_b)
            if (pair not in self.device_pairs and (device_b, device_a) not in self.device_pairs):
                self.device_pairs.append(pair)
                self.distance_data.update([(pair, deque([], TRAIL_LENGTH))])
                self.timestamp_data.update([(pair, deque([], TRAIL_LENGTH))])
                self.distance_plots.update([(pair, self.distance_graph.plot(pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
                self.legend.addItem(self.distance_graph.plot(pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)), (pair[0] + ':' + pair[1]))
                self.color_offset += 1

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        self.update_labels()

    def update_labels(self):
        change_box = False
        for serial in UwbNetwork.nodes:
            if ((serial not in self.network_serials) and DistanceV2.type in UwbNetwork.nodes[serial].cdp_pkts_count):
                self.network_serials[serial] = (UwbNetwork.nodes[serial].cdp_pkts_count[DistanceV2.type] -
                                                len(UwbNetwork.nodes[serial].cdp_pkts[DistanceV2.type]))
        for serial in self.network_serials:
            previous_count = self.network_serials[serial]
            self.network_serials[serial] = UwbNetwork.nodes[serial].cdp_pkts_count[DistanceV2.type]
            current_size = self.network_serials[serial] - previous_count
            if current_size > TRAIL_LENGTH:
                current_size = TRAIL_LENGTH

            for idx in range(current_size):
                packet = UwbNetwork.nodes[serial].cdp_pkts[DistanceV2.type][idx - current_size]
                target_id_a = '0x{:08X}'.format(packet.serial_number_1.as_int)
                target_id_b = '0x{:08X}'.format(packet.serial_number_2.as_int)
                if target_id_a not in self.available_devices:
                    self.available_devices.append(target_id_a)
                    self.serial_a.addItem(target_id_a)
                    self.serial_b.addItem(target_id_a)
                if target_id_b not in self.available_devices:
                    self.available_devices.append(target_id_b)
                    self.serial_a.addItem(target_id_b)
                    self.serial_b.addItem(target_id_b)
                pair = None
                if (target_id_a, target_id_b) in self.device_pairs:
                    pair = (target_id_a, target_id_b)
                elif (target_id_b, target_id_a) in self.device_pairs:
                    pair = (target_id_b, target_id_a)
                if pair:
                    self.distance_data[pair].append(packet.distance)
                    self.timestamp_data[pair].append(UwbNetwork.nodes[serial].cdp_pkts_time[DistanceV2.type][idx - current_size])
                    if len(self.timestamp_data[pair]) > 1:
                        self.distance_plots[pair].setData(self.timestamp_data[pair], self.distance_data[pair])

    def reset(self):
        for pair in self.distance_plots:
            self.distance_data[pair] = deque([], TRAIL_LENGTH)
            self.timestamp_data[pair] = deque([], TRAIL_LENGTH)
            self.distance_plots[pair].clear()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()
