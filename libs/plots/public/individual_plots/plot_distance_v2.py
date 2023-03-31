# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# Local libraries
from cdp import DistanceV2
from network_objects import *
from settings import *

from collections import deque


class PlotDistanceV2(pg.LayoutWidget):
    type = DistanceV2.type

    def __init__(self, serial):

        pg.LayoutWidget.__init__(self)

        self.setWindowTitle('DistanceV2 Plotting')
        self.resize(900, 900)
        self.serial = serial

        self.serial_a = pg.ComboBox(self)
        self.addWidget(self.serial_a, row=0, col=0)

        self.serial_b = pg.ComboBox(self)
        self.addWidget(self.serial_b, row=0, col=1)

        self.add_button = QtWidgets.QPushButton('Add')
        self.add_button.clicked.connect(self.add_plot)
        self.addWidget(self.add_button, row=0, col=2)

        self.twr_graph = pg.PlotWidget(name='TWR', title='Distance (m) vs Time (s)')
        self.legend = self.twr_graph.addLegend()
        self.twr_graph.showGrid(x=True, y=True)
        self.addWidget(self.twr_graph, row=1, col=0, colspan=3)
        self.twr_plot_line = dict()
        self.twr_ordered_data = dict()

        self.quality_graph = pg.PlotWidget(title='Quality vs Time (s)')
        self.quality_graph.showGrid(x=True, y=True)
        self.quality_graph.setXLink('TWR')
        self.quality_graph.setYRange(0, 1)
        self.addWidget(self.quality_graph, row=2, col=0, colspan=3)
        self.quality_plot_line = dict()
        self.quality_ordered_data = dict()

        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        self.color_offset = 0

        self.show()

        self.available_nodes = []
        self.twr_pairs = np.empty((0,2))
        self.dist_prev_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def add_plot(self):
        if 0 < self.serial_a.value() < 0x80000000 and 0< self.serial_b.value() < 0x80000000 and self.serial_a.value() != self.serial_b.value():
            _node_a = self.serial_a.value()
            _node_b = self.serial_b.value()
            self.twr_pairs = np.vstack((self.twr_pairs, [_node_a, _node_b]))

            self.twr_plot_line.update([(len(self.twr_pairs) - 1, self.twr_graph.plot(pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.twr_ordered_data.update([(len(self.twr_pairs) - 1, deque([], TRAIL_LENGTH))])
            self.quality_plot_line.update([(len(self.twr_pairs) - 1, self.quality_graph.plot(pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.quality_ordered_data.update([(len(self.twr_pairs) - 1, deque([], TRAIL_LENGTH))])

            self.color_offset += 1

            self.legend.addItem(self.twr_plot_line[len(self.twr_pairs)-1], '0x{:08X}:0x{:08X}'.format(int(self.twr_pairs[-1][0]), int(self.twr_pairs[-1][1])))

    def overlap(self, array_a, array_b):
        # return the indices in a that overlap with b
        # only works if both a and b are unique!
        _bool_a = np.in1d(array_a, array_b)
        _ind_a = np.arange(len(array_a))
        _ind_a = _ind_a[_bool_a]

        _ind_b = np.array([np.argwhere(array_b == array_a[x]) for x in _ind_a]).flatten()
        return _ind_a,_ind_b

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()

        _current_size_distance = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - self.dist_prev_count
        self.dist_prev_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
        if _current_size_distance <= 0:
            return
        elif _current_size_distance > TRAIL_LENGTH:
            _current_size_distance = TRAIL_LENGTH

        _change_box = False
        for _idx in np.arange(_current_size_distance):
            _serial_1 = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][_idx - _current_size_distance].serial_number_1
            if _serial_1 not in self.available_nodes:
                self.available_nodes.append(_serial_1.as_int)
                _change_box = True
            _serial_2 = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][_idx - _current_size_distance].serial_number_2
            if _serial_2 not in self.available_nodes:
                self.available_nodes.append(_serial_2.as_int)
                _change_box = True
        if _change_box:
            self.serial_a.clear()
            self.serial_b.clear()
            for _id in sorted(self.available_nodes):
                self.serial_a.addItem('0x{:08X}'.format(_id), _id)
                self.serial_b.addItem('0x{:08X}'.format(_id), _id)

        _pairs_idx = -1
        for [_node_a, _node_b] in self.twr_pairs:

            _pairs_idx += 1  #increment first to avoid continue

            for _idx in np.arange(_current_size_distance):
                _serial_1 = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][_idx - _current_size_distance].serial_number_1.as_int
                _serial_2 = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][_idx - _current_size_distance].serial_number_2.as_int
                if ((_node_a != _serial_1 and _node_a != _serial_2)
                    or (_node_b != _serial_1 and _node_b != _serial_2)):
                    continue

                _distance = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][_idx - _current_size_distance].distance / 1000.0
                _quality = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][_idx - _current_size_distance].quality / 10000.0
                _timestamp = UwbNetwork.nodes[self.serial].cdp_pkts_time[self.type][_idx - _current_size_distance]
                self.twr_ordered_data[_pairs_idx].append([_timestamp, _distance])
                self.quality_ordered_data[_pairs_idx].append([_timestamp, _quality])

            if len(self.twr_ordered_data[_pairs_idx]) > 1:
                self.twr_plot_line[_pairs_idx].setData(np.array(self.twr_ordered_data[_pairs_idx])[:,0], np.array(self.twr_ordered_data[_pairs_idx])[:,1])
                self.quality_plot_line[_pairs_idx].setData(np.array(self.quality_ordered_data[_pairs_idx])[:,0], np.array(self.quality_ordered_data[_pairs_idx])[:,1])

    def closeEvent(self, e):
        self.killTimer(self.timer)

    def reset(self):
        for _pairs_idx in self.twr_ordered_data:
            self.twr_ordered_data[_pairs_idx] = list()
            self.twr_plot_line[_pairs_idx].clear()
        for _pairs_idx in self.quality_ordered_data:
            self.quality_ordered_data[_pairs_idx] = list()
            self.quality_plot_line[_pairs_idx].clear()
