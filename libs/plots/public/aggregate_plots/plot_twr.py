# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import pyqtgraph as pg
from collections import deque
from pyqtgraph.Qt import QtGui, QtCore

# Local libraries
from network_objects import *
from cdp import *
from settings import *


class PlotTwr(pg.LayoutWidget):
    type = 'TwrPlot'

    def __init__(self):

        pg.LayoutWidget.__init__(self)

        self.setWindowTitle('CUWB Monitor - TWR Plotting')
        self.resize(900,500)

        self.serial_a = pg.ComboBox(self)
        self.addWidget(self.serial_a, row=0, col=0)

        self.serial_b = pg.ComboBox(self)
        self.addWidget(self.serial_b, row=0, col=1)

        self.ant_delay_box = pg.SpinBox(self)
        self.ant_delay_box.setSingleStep(1)
        self.ant_delay_box.setOpts(int=True)
        self.ant_delay_box.setValue(0)
        self.ant_delay_box.setMaximumWidth(150)
        self.addWidget(self.ant_delay_box, row=0, col=2)

        self.add_button = QtGui.QPushButton('Add')
        self.add_button.clicked.connect(self.add_plot)
        self.addWidget(self.add_button, row=0, col=3)

        self.twr_graph = pg.PlotWidget(title='Distance (m) vs Time (s)')
        self.legend = self.twr_graph.addLegend()
        self.twr_graph.showGrid(x=True, y=True)
        self.addWidget(self.twr_graph, row=1, col=0, colspan=4)
        self.plot_line = dict()
        self.ordered_data = dict()
        self.colors = ['r', 'g', 'b', 'c', 'm', 'y', 'w']
        self.color_offset = 0

        self.show()

        self.available_nodes = np.array([])
        self.twr_pairs = np.empty((0,2))
        self.node_tick_prev_count = dict()
        self.node_trx_prev_count = dict()
        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def add_plot(self):
        if 0 < self.serial_a.value() < 0x80000000 and 0< self.serial_b.value() < 0x80000000 and self.serial_a.value() != self.serial_b.value():
            _node_a = self.serial_a.value()
            _node_b = self.serial_b.value()
            self.twr_pairs = np.vstack((self.twr_pairs, [_node_a, _node_b]))

            if not (_node_a in self.node_tick_prev_count.keys()):
                if     TickV4.type in UwbNetwork.nodes[_node_a].cdp_pkts_count.keys():
                    _a_tick_count = UwbNetwork.nodes[_node_a].cdp_pkts_count[TickV4.type]
                else:
                    _a_tick_count = 0
                if TimedRxV5.type in UwbNetwork.nodes[_node_a].cdp_pkts_count.keys():
                    _a_trx_count = UwbNetwork.nodes[_node_a].cdp_pkts_count[TimedRxV5.type]
                else:
                    _a_trx_count = 0
            if not (_node_b in self.node_tick_prev_count.keys()):
                if     TickV4.type in UwbNetwork.nodes[_node_b].cdp_pkts_count.keys():
                    _b_tick_count = UwbNetwork.nodes[_node_b].cdp_pkts_count[TickV4.type]
                else:
                    _b_tick_count = 0
                if TimedRxV5.type in UwbNetwork.nodes[_node_b].cdp_pkts_count.keys():
                    _b_trx_count = UwbNetwork.nodes[_node_b].cdp_pkts_count[TimedRxV5.type]
                else:
                    _b_trx_count = 0
            self.node_tick_prev_count.update([(len(self.twr_pairs)-1, [_a_tick_count, _b_tick_count])])
            self.node_trx_prev_count.update([(len(self.twr_pairs)-1, [_a_trx_count, _b_trx_count])])

            self.plot_line.update([(len(self.twr_pairs) - 1, self.twr_graph.plot(pen=pg.mkPen(self.colors[self.color_offset % len(self.colors)], width=2)))])
            self.ordered_data.update([(len(self.twr_pairs)-1, deque([], TRAIL_LENGTH))])
            self.color_offset += 1

            self.legend.addItem(self.plot_line[len(self.twr_pairs)-1], '0x{:08X}:0x{:08X}'.format(int(self.twr_pairs[-1][0]), int(self.twr_pairs[-1][1])))

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
            return

        _change_box = False
        for _id in UwbNetwork.nodes.keys():
            if _id not in self.available_nodes:
                self.available_nodes = np.append(self.available_nodes, _id)
                _change_box = True
        if _change_box:
            self.serial_a.clear()
            self.serial_b.clear()
            for _id in sorted(list(UwbNetwork.nodes.keys())):
                self.serial_a.addItem('0x{:08X}'.format(_id), _id)
                self.serial_b.addItem('0x{:08X}'.format(_id), _id)

        _pairs_idx = -1
        for [_node_a, _node_b] in self.twr_pairs:

            _pairs_idx += 1  # Increment first to avoid continue

            if not (_node_a in UwbNetwork.nodes.keys()): continue
            if not (_node_b in UwbNetwork.nodes.keys()): continue
            if not (TickV4.type     in UwbNetwork.nodes[_node_a].cdp_pkts_count.keys()): continue
            if not (TimedRxV5.type in UwbNetwork.nodes[_node_a].cdp_pkts_count.keys()): continue
            if not (TickV4.type     in UwbNetwork.nodes[_node_b].cdp_pkts_count.keys()): continue
            if not (TimedRxV5.type in UwbNetwork.nodes[_node_b].cdp_pkts_count.keys()): continue

            # Process one less tick packet to give time to receive trx
            _current_size_ticks_a = (UwbNetwork.nodes[_node_a].cdp_pkts_count[TickV4.type]-2) - self.node_tick_prev_count[_pairs_idx][0]
            _current_size_ticks_b = (UwbNetwork.nodes[_node_b].cdp_pkts_count[TickV4.type]-2) - self.node_tick_prev_count[_pairs_idx][1]
            _current_size_trx_a = UwbNetwork.nodes[_node_a].cdp_pkts_count[TimedRxV5.type] - self.node_trx_prev_count[_pairs_idx][0]
            _current_size_trx_b = UwbNetwork.nodes[_node_b].cdp_pkts_count[TimedRxV5.type] - self.node_trx_prev_count[_pairs_idx][1]

            if _current_size_ticks_a <= 0 or _current_size_ticks_b <= 0 or _current_size_trx_a == 0 or _current_size_trx_b == 0: continue

            self.node_tick_prev_count[_pairs_idx][0] = UwbNetwork.nodes[_node_a].cdp_pkts_count[TickV4.type]-2
            self.node_tick_prev_count[_pairs_idx][1] = UwbNetwork.nodes[_node_b].cdp_pkts_count[TickV4.type]-2
            self.node_trx_prev_count[_pairs_idx][0] = UwbNetwork.nodes[_node_a].cdp_pkts_count[TimedRxV5.type]
            self.node_trx_prev_count[_pairs_idx][1] = UwbNetwork.nodes[_node_b].cdp_pkts_count[TimedRxV5.type]

            _a_ticks = deque([], 100)
            _b_ticks = deque([], 100)
            _a_trx = deque([], 100)
            _b_trx = deque([], 100)
            _a_time = deque([], 100)
            _b_time = deque([], 100)
            _a_tx_decaticks = deque([], 100)
            _a_rx_decaticks = deque([], 100)
            _b_tx_decaticks = deque([], 100)
            _b_rx_decaticks = deque([], 100)
            for _idx in np.arange(_current_size_ticks_a):
                _a_ticks.append(UwbNetwork.nodes[_node_a].cdp_pkts[TickV4.type][_idx - _current_size_ticks_a].nt64)
                _a_tx_decaticks.append(UwbNetwork.nodes[_node_a].cdp_pkts[TickV4.type][_idx - _current_size_ticks_a].dt64)
                _a_time.append(UwbNetwork.nodes[_node_a].cdp_pkts_time[TickV4.type][_idx - _current_size_ticks_a])
            for _idx in np.arange(_current_size_ticks_b):
                _b_ticks.append(UwbNetwork.nodes[_node_b].cdp_pkts[TickV4.type][_idx - _current_size_ticks_b].nt64)
                _b_tx_decaticks.append(UwbNetwork.nodes[_node_b].cdp_pkts[TickV4.type][_idx - _current_size_ticks_b].dt64)
                _b_time.append(UwbNetwork.nodes[_node_b].cdp_pkts_time[TickV4.type][_idx - _current_size_ticks_b])
            for _idx in np.arange(_current_size_trx_a):
                _a_trx.append(UwbNetwork.nodes[_node_a].cdp_pkts[TimedRxV5.type][_idx - _current_size_trx_a].tx_nt64)
                _a_rx_decaticks.append(UwbNetwork.nodes[_node_a].cdp_pkts[TimedRxV5.type][_idx - _current_size_trx_a].rx_dt64)
            for _idx in np.arange(_current_size_trx_b):
                _b_trx.append(UwbNetwork.nodes[_node_b].cdp_pkts[TimedRxV5.type][_idx - _current_size_trx_b].tx_nt64)
                _b_rx_decaticks.append(UwbNetwork.nodes[_node_b].cdp_pkts[TimedRxV5.type][_idx - _current_size_trx_b].rx_dt64)

            [_a_ticks_idx, _b_trx_idx] = self.overlap(np.array(_a_ticks), np.array(_b_trx))
            [_b_ticks_idx, _a_trx_idx] = self.overlap(np.array(_b_ticks), np.array(_a_trx))

            _last_atick_found = _last_btick_found = _last_atrx_found = _last_btrx_found = 0
            if _a_ticks_idx.size > 0: _last_atick_found = _a_ticks_idx[-1] + 1
            if _b_ticks_idx.size > 0: _last_btick_found = _b_ticks_idx[-1] + 1
            if _a_trx_idx.size > 0   : _last_atrx_found = _a_trx_idx[-1] + 1
            if _b_trx_idx.size > 0   : _last_btrx_found = _b_trx_idx[-1] + 1

            if len(_a_ticks) != len(_a_ticks_idx):
                self.node_tick_prev_count[_pairs_idx][0] -= len(_a_ticks) - _last_atick_found
                self.node_trx_prev_count[_pairs_idx][1] -= len(_b_trx) - _last_btrx_found
            if len(_b_ticks) != len(_b_ticks_idx):
                self.node_tick_prev_count[_pairs_idx][1] -= len(_b_ticks) - _last_btick_found
                self.node_trx_prev_count[_pairs_idx][0] -= len(_a_trx) - _last_atrx_found

            if len(_a_ticks_idx) <= len(_b_ticks_idx):
                _total_steps = len(_a_ticks_idx)
                _left_over = len(_b_ticks_idx) - _total_steps
            else:
                _total_steps = len(_b_ticks_idx)
                _left_over = len(_a_ticks_idx) - _total_steps

            for _step in np.arange(_total_steps):

                if _a_ticks[_a_ticks_idx[_step]] <= _b_ticks[_b_ticks_idx[_step]]:
                    self.ordered_data[_pairs_idx].append([_a_tx_decaticks[_a_ticks_idx[_step]],
                                                          _b_rx_decaticks[_b_trx_idx[_step]],
                                                          _a_time[_a_ticks_idx[_step]],
                                                          self.calculate_twr(_pairs_idx),
                                                          _node_a])
                    if len(_a_ticks_idx) > _step+1 and _a_ticks[_a_ticks_idx[_step+1]] < _b_ticks[_b_ticks_idx[_step]]:
                        self.ordered_data[_pairs_idx].append([np.nan, np.nan, np.nan, np.nan, _node_b])
                    else:
                        self.ordered_data[_pairs_idx].append([_b_tx_decaticks[_b_ticks_idx[_step]],
                                                              _a_rx_decaticks[_a_trx_idx[_step]],
                                                              _b_time[_b_ticks_idx[_step]],
                                                              self.calculate_twr(_pairs_idx),
                                                              _node_b])
                else:
                    self.ordered_data[_pairs_idx].append([_b_tx_decaticks[_b_ticks_idx[_step]],
                                                          _a_rx_decaticks[_a_trx_idx[_step]],
                                                          _b_time[_b_ticks_idx[_step]],
                                                          self.calculate_twr(_pairs_idx),
                                                          _node_b])
                    if len(_b_ticks_idx) > _step+1 and _b_ticks[_b_ticks_idx[_step+1]] < _a_ticks[_a_ticks_idx[_step]]:
                        self.ordered_data[_pairs_idx].append([np.nan, np.nan, np.nan, np.nan, _node_a])
                    else:
                        self.ordered_data[_pairs_idx].append([_a_tx_decaticks[_a_ticks_idx[_step]],
                                                              _b_rx_decaticks[_b_trx_idx[_step]],
                                                              _a_time[_a_ticks_idx[_step]],
                                                              self.calculate_twr(_pairs_idx),
                                                              _node_a])
            for _step in np.arange(_left_over) + _total_steps:
                if len(_a_ticks_idx) > len(_b_ticks_idx):
                    self.ordered_data[_pairs_idx].append([_a_tx_decaticks[_a_ticks_idx[_step]],
                                                          _b_rx_decaticks[_b_trx_idx[_step]],
                                                          _a_time[_a_ticks_idx[_step]],
                                                          self.calculate_twr(_pairs_idx),
                                                          _node_a])
                else:
                    self.ordered_data[_pairs_idx].append([_b_tx_decaticks[_b_ticks_idx[_step]],
                                                          _a_rx_decaticks[_a_trx_idx[_step]],
                                                          _b_time[_b_ticks_idx[_step]],
                                                          self.calculate_twr(_pairs_idx),
                                                          _node_b])

            if len(self.ordered_data[_pairs_idx]) > 0:
                self.plot_line[_pairs_idx].setData(np.array(self.ordered_data[_pairs_idx])[:,2], np.array(self.ordered_data[_pairs_idx])[:,3])

    def calculate_twr(self, pair_idx):

        # Not enough data to calculate
        if len(self.ordered_data[pair_idx]) < 3: return np.nan

        # If data from same ID 2x in a row we missed a packet, return NaN
        if self.ordered_data[pair_idx][-3][4] == self.ordered_data[pair_idx][-2][4] or \
           self.ordered_data[pair_idx][-2][4] == self.ordered_data[pair_idx][-1][4]: return np.nan

        ant_delay = self.ant_delay_box.value()
        T1 = self.ordered_data[pair_idx][-3][0] + ant_delay
        M1 = self.ordered_data[pair_idx][-3][1] - ant_delay
        M2 = self.ordered_data[pair_idx][-2][0] + ant_delay
        T2 = self.ordered_data[pair_idx][-2][1] - ant_delay
        T3 = self.ordered_data[pair_idx][-1][0] + ant_delay
        M3 = self.ordered_data[pair_idx][-1][1] - ant_delay

        # Apply correction for fixed delay non-equal
        if M3 - M1 == 0: return np.nan
        CorrectionFactor = (T3 - T1)/(M3 - M1);
        M1 *= CorrectionFactor;
        M2 *= CorrectionFactor;
        M3 *= CorrectionFactor;

        # Do the subtractions here just to make the code readable. Algorithm below is from
        # TWR documentation.
        DiffT21 = T2 - T1;
        DiffM21 = M2 - M1;
        DiffM32 = M3 - M2;
        DiffT32 = T3 - T2;

        # TWR algorithm
        Distance = C * (((DiffT21 - DiffM21 + DiffM32 - DiffT32)*TICK)/4);
        return Distance

    def closeEvent(self, e):
        self.killTimer(self.timer)

    def reset(self):
        self.color_offset = 0
        for pairs_idx in self.plot_line.keys():
            self.plot_line[pairs_idx].clear()
            self.ordered_data[pairs_idx] = deque([], TRAIL_LENGTH)
            self.node_tick_prev_count[pairs_idx] = [0, 0]
            self.node_trx_prev_count[pairs_idx] = [0, 0]
