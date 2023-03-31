# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
from functools import partial
from pyqtgraph import QtCore, QtWidgets
import time

# Local libraries
from cdp import *
from network_objects import *
from network_discovery_window import NetworkDiscoveryWindow
from type_filter_window import TypeFilterWindow
from aggregate_plot_window import AggregatePlotWindow
from plots import *
from settings import *
from socket_processing import *


class UiMainWindow(QtWidgets.QMainWindow):

    def __init__(self, num_processes, ip=None, port=None, ifc=None):
        super().__init__()

        self.central = QtWidgets.QWidget()  # This will be our central widget
        self.grid_layout = QtWidgets.QGridLayout()
        self.setWindowTitle("CUWB Monitor - MAIN")
        self.sub_windows = dict()
        self.plot_windows = dict()

        self.network_discovery_window = NetworkDiscoveryWindow(num_processes, ip, port, ifc)
        self.aggregate_plot_window = AggregatePlotWindow()
        self.type_filter_window = TypeFilterWindow()
        self.network_discovery_window.show()

        self.type_filter_button = QtWidgets.QPushButton('Filter Data Types')
        self.type_filter_button.clicked.connect(self.open_type_filter_window)
        self.grid_layout.addWidget(self.type_filter_button, 2, 1)

        self.aggregate_plot_button = QtWidgets.QPushButton('Aggregate Plots')
        self.aggregate_plot_button.clicked.connect(self.open_aggregate_plots_window)
        self.grid_layout.addWidget(self.aggregate_plot_button, 1, 1)

        self.network_discovery_btn = QtWidgets.QPushButton('Network Discovery')
        self.network_discovery_btn.clicked.connect(self.open_discovery_window)
        self.grid_layout.addWidget(self.network_discovery_btn, 1, 0)

        self.reset_btn = QtWidgets.QPushButton('Reset All Windows')
        self.reset_btn.clicked.connect(self.reset_all_windows)
        self.grid_layout.addWidget(self.reset_btn, 2, 0)

        self.toggle_pause_play_btn = QtWidgets.QPushButton('Pause')
        self.toggle_pause_play_btn.clicked.connect(self.toggle_pause_play)
        self.grid_layout.addWidget(self.toggle_pause_play_btn, 3, 0, 1, 2)
        self.paused = False

        self.serial_title = QtWidgets.QLabel('SERIAL NUM')
        self.serial_title.setStyleSheet(GetTitleColor())
        self.serial_title.setAlignment(QtCore.Qt.AlignCenter)
        self.serial_title.setMargin(5)

        self.total_count_title = QtWidgets.QLabel('CDP CNT')
        self.total_count_title.setStyleSheet(GetTitleColor())
        self.total_count_title.setAlignment(QtCore.Qt.AlignCenter)
        self.serial_title.setMargin(5)

        self.grid_layout.addWidget(self.serial_title, 4, 0)
        self.grid_layout.addWidget(self.total_count_title, 4, 1)

        self.serial_labels = dict()
        self.total_count_labels = dict()
        self.count = 0

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)

        self.resize(300, 100)
        self.startTimer(250)
        self.currently_filtering = False
        self.previous_nodes = set(UwbNetwork.nodes.keys())

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()
            return

        current_nodes = set(UwbNetwork.nodes.keys())
        node_diff = current_nodes - self.previous_nodes
        if node_diff:
            if self.currently_filtering:
                for serial in node_diff:
                    UwbNetwork.nodes[serial].start_filtering(self.type_filter_window.current_types)
            if self.paused:
                for serial in node_diff:
                    UwbNetwork.nodes[serial].pause()
        self.previous_nodes = current_nodes


        if self.type_filter_window.filtering and not self.currently_filtering:
            for serial in UwbNetwork.nodes:
                UwbNetwork.nodes[serial].start_filtering(self.type_filter_window.current_types)
                self.currently_filtering = True
        elif not self.type_filter_window.filtering and self.currently_filtering:
            for serial in UwbNetwork.nodes:
                UwbNetwork.nodes[serial].stop_filtering()
                self.currently_filtering = False

        while len(UwbNetwork.nodes) > self.count:
            self.serial_labels.update([(self.count, QtWidgets.QLabel())])
            self.serial_labels[self.count].setAlignment(QtCore.Qt.AlignCenter)
            self.serial_labels[self.count].mouseReleaseEvent = partial(self.labelClickEvent, self.count)
            self.serial_labels[self.count].setStyleSheet(GetClickableColor())

            self.total_count_labels.update([(self.count, QtWidgets.QLabel())])
            self.total_count_labels[self.count].setAlignment(QtCore.Qt.AlignCenter)

            _row = self.count % 25
            _column = 2 * int((self.count) / 25)
            self.grid_layout.addWidget(self.serial_labels[self.count], _row + 5, _column + 0)
            self.grid_layout.addWidget(self.total_count_labels[self.count], _row + 5, _column + 1)

            self.count += 1

        if UwbNetwork.nodes.keys():
            _ids = np.sort(list(UwbNetwork.nodes.keys()))
            for _row in range(self.count):
                self.serial_labels[_row].setText('0x{:08X}'.format(_ids[_row]))
                self.total_count_labels[_row].setText('{:7d}'.format(UwbNetwork.nodes[_ids[_row]].cdp_total))

    def closeEvent(self, e):
        UwbNetwork.running = False

        for _type_val, _plot in self.plot_windows.items():
            _plot.close()

        self.network_discovery_window.close()
        exit()

    def labelClickEvent(self, index, e):
        _ids = np.sort(list(UwbNetwork.nodes.keys()))

        if _ids[index] in self.sub_windows:
            if self.sub_windows[_ids[index]].isVisible():
                self.sub_windows[_ids[index]].closeWindow()
            del self.sub_windows[_ids[index]]

        self.sub_windows.update([(_ids[index], StatsWindow(_ids[index]))])
        self.sub_windows[_ids[index]].show()

    def plotClickEvent(self, type_value, e):

        _tmp_plot = partial(map_type_to_aggregate_plot[type_value])
        self.plot_windows.update([(type_value, _tmp_plot())])
        self.plot_windows[type_value].show()

    def open_type_filter_window(self):
        self.type_filter_window.activateWindow()
        self.type_filter_window.show()

    def open_discovery_window(self):
        self.network_discovery_window.activateWindow()
        self.network_discovery_window.show()
        self.network_discovery_window.reopen()

    def open_aggregate_plots_window(self):
        self.aggregate_plot_window.activateWindow()
        self.aggregate_plot_window.show()

    def reset_all_windows(self):
        for node in UwbNetwork.nodes:
            UwbNetwork.nodes[node].reset()
        for window in self.sub_windows:
            self.sub_windows[window].reset()
        self.aggregate_plot_window.reset()

    def toggle_pause_play(self):
        if self.paused:
            self.toggle_pause_play_btn.setText('Pause')
            self.paused = False
            for serial in UwbNetwork.nodes:
                UwbNetwork.nodes[serial].resume()
        else:
            self.toggle_pause_play_btn.setText('Resume')
            self.paused = True
            for serial in UwbNetwork.nodes:
                UwbNetwork.nodes[serial].pause()

class StatsWindow(QtWidgets.QMainWindow):

    def __init__(self, serial, main_window=None):
        super().__init__()
        # Reference to the main window when device_id is provided as a command argument.
        # This reference is used to close the main window, which is hidden in this mode.
        self.main_window = main_window
        self.resize_flag = True

        self.central = QtWidgets.QWidget()  # This will be our central widget
        self.grid_layout = QtWidgets.QGridLayout()
        self.plot_windows = dict()

        self.serial = serial
        self.setWindowTitle('CUWB Monitor - ID: 0x{:08X}'.format(self.serial))

        self.type_title = QtWidgets.QLabel('Type')
        self.type_title.setStyleSheet(GetTitleColor())
        self.type_title.setAlignment(QtCore.Qt.AlignRight)
        self.type_title.setMargin(5)

        self.count_title = QtWidgets.QLabel('Count')
        self.count_title.setStyleSheet(GetTitleColor())
        self.count_title.setAlignment(QtCore.Qt.AlignCenter)
        self.count_title.setMargin(5)

        self.freq_title = QtWidgets.QLabel('Frequency')
        self.freq_title.setStyleSheet(GetTitleColor())
        self.freq_title.setAlignment(QtCore.Qt.AlignCenter)
        self.freq_title.setMargin(5)

        self.print_title = QtWidgets.QLabel('Print')
        self.print_title.setStyleSheet(GetTitleColor())
        self.print_title.setAlignment(QtCore.Qt.AlignLeft)
        self.print_title.setMargin(5)

        self.grid_layout.addWidget(self.type_title, 0, 0)
        self.grid_layout.addWidget(self.count_title, 0, 1)
        self.grid_layout.addWidget(self.freq_title, 0, 2)
        self.grid_layout.addWidget(self.print_title, 0, 3)

        self.type_count = 0
        self.type_labels = dict()
        self.count_labels = dict()
        self.disp_checks = dict()
        self.disp_freqs = dict()
        if self.serial in UwbNetwork.nodes.keys():
            _cdp_types = np.sort(list(UwbNetwork.nodes[self.serial].cdp_pkts.keys()))
            for _type in _cdp_types:

                self.type_labels.update([(self.type_count, QtWidgets.QLabel(UwbNetwork.nodes[self.serial].cdp_pkts_name[_type]))])
                self.count_labels.update([(self.type_count, QtWidgets.QLabel('{:5d}'.format(UwbNetwork.nodes[self.serial].cdp_pkts_count[_type])))])
                self.disp_freqs.update([(self.type_count, QtWidgets.QLabel('{:0.3f} Hz'.format(UwbNetwork.nodes[self.serial].cdp_pkts_freq [_type])))])
                self.disp_checks.update([(self.type_count, QtWidgets.QCheckBox())])

                self.type_labels[self.type_count].setAlignment(QtCore.Qt.AlignRight)
                self.count_labels[self.type_count].setAlignment(QtCore.Qt.AlignCenter)
                self.disp_freqs[self.type_count].setAlignment(QtCore.Qt.AlignCenter)

                self.grid_layout.addWidget(self.type_labels[self.type_count], self.type_count+1, 0)
                self.grid_layout.addWidget(self.count_labels[self.type_count], self.type_count+1, 1)
                self.grid_layout.addWidget(self.disp_freqs[self.type_count], self.type_count+1, 2)
                self.grid_layout.addWidget(self.disp_checks[self.type_count], self.type_count+1, 3)

                if _type in map_type_to_plot.keys() or _type == AppSettingsChunk.type:
                    self.type_labels[self.type_count].setStyleSheet(GetClickableColor())
                    self.type_labels[self.type_count].mouseReleaseEvent = partial(self.labelClickEvent, _type)

                self.count_labels[self.type_count].mouseReleaseEvent = partial(self.countClickEvent, self.type_count)
                self.count_labels[self.type_count].setStyleSheet(GetClickableColor())

                self.type_count += 1

        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def closeWindow(self):
        self.close()

    def closeEvent(self, e):
        # Close main window if device_id was provided as a command argument
        # if self.main_window is not None:
        #     self.main_window.close()
        for _type in self.plot_windows.keys():
            if self.plot_windows[_type].isVisible():
                self.plot_windows[_type].close()
        self.killTimer(self.timer)

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.close()

        if self.serial in UwbNetwork.nodes.keys():

            if self.resize_flag:
                self.resize(400, 5)
                self.resize_flag = False

            if self.type_count > len(UwbNetwork.nodes[self.serial].cdp_pkts):
                for row in range(self.type_count):
                    self.type_labels[row].close()
                    self.count_labels[row].close()
                    self.disp_freqs[row].close()
                    self.disp_checks[row].close()
                    del self.type_labels[row]
                    del self.count_labels[row]
                    del self.disp_freqs[row]
                    del self.disp_checks[row]
                self.resize_flag = True
                self.type_count = 0


            while len(UwbNetwork.nodes[self.serial].cdp_pkts) > self.type_count:
                self.type_labels.update([(self.type_count, QtWidgets.QLabel())])
                self.count_labels.update([(self.type_count, QtWidgets.QLabel())])
                self.disp_freqs.update([(self.type_count, QtWidgets.QLabel())])
                self.disp_checks.update([(self.type_count, QtWidgets.QCheckBox())])

                self.type_labels[self.type_count].setAlignment(QtCore.Qt.AlignRight)
                self.count_labels[self.type_count].setAlignment(QtCore.Qt.AlignCenter)
                self.disp_freqs[self.type_count].setAlignment(QtCore.Qt.AlignCenter)
                self.grid_layout.addWidget(self.type_labels[self.type_count], self.type_count + 1, 0)
                self.grid_layout.addWidget(self.count_labels[self.type_count], self.type_count + 1, 1)
                self.grid_layout.addWidget(self.disp_freqs[self.type_count], self.type_count + 1, 2)
                self.grid_layout.addWidget(self.disp_checks[self.type_count], self.type_count + 1, 3)

                self.count_labels[self.type_count].mouseReleaseEvent = partial(self.countClickEvent, self.type_count)
                self.count_labels[self.type_count].setStyleSheet(GetClickableColor())

                self.type_count += 1

            for type in UwbNetwork.nodes[self.serial].cdp_pkts.keys():
                UwbNetwork.nodes[self.serial].cdp_pkts_frequency_deques[type].append((UwbNetwork.nodes[self.serial].cdp_pkts_count[type], time.monotonic()))
                UwbNetwork.nodes[self.serial].cdp_pkts_freq[type] = UwbNetwork.nodes[self.serial].calculate_frequency(UwbNetwork.nodes[self.serial].cdp_pkts_frequency_deques[type])

            _cdp_types = np.sort(list(UwbNetwork.nodes[self.serial].cdp_pkts.keys()))
            for _row in range(self.type_count):

                if self.type_labels[_row].text() != UwbNetwork.nodes[self.serial].cdp_pkts_name[_cdp_types[_row]]:
                    self.type_labels[_row].setText(UwbNetwork.nodes[self.serial].cdp_pkts_name[_cdp_types[_row]])
                    if _cdp_types[_row] in map_type_to_plot or _cdp_types[_row] == AppSettingsChunk.type :
                        self.type_labels[_row].setStyleSheet(GetClickableColor())
                        self.type_labels[_row].mouseReleaseEvent = partial(self.labelClickEvent, _cdp_types[_row])
                    else:
                        self.type_labels[_row].setStyleSheet('color: grey')
                        self.type_labels[_row].mouseReleaseEvent = None

                    if UwbNetwork.nodes[self.serial].cdp_pkts_selected[_cdp_types[_row]]:
                        self.disp_checks[_row].setCheckState(QtCore.Qt.Checked)
                    else:
                        self.disp_checks[_row].setCheckState(QtCore.Qt.Unchecked)

                _previous_count = self.count_labels[_row].text()
                if _previous_count: _previous_count = int(_previous_count)
                self.count_labels[_row].setText('{:5d}'.format(UwbNetwork.nodes[self.serial].cdp_pkts_count[_cdp_types[_row]]))
                self.disp_freqs[_row].setText('{:0.3f} Hz'.format(UwbNetwork.nodes[self.serial].cdp_pkts_freq[_cdp_types[_row]]))
                if not _previous_count: _previous_count = int(self.count_labels[_row].text())


                if self.disp_checks[_row].isChecked():
                    _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[_cdp_types[_row]] - _previous_count
                    UwbNetwork.nodes[self.serial].cdp_pkts_selected[_cdp_types[_row]] = True
                    for idx in range(_current_size):
                        print(UwbNetwork.nodes[self.serial].cdp_pkts[_cdp_types[_row]][idx - _current_size])
                else: UwbNetwork.nodes[self.serial].cdp_pkts_selected[_cdp_types[_row]] = False

    def reset(self):
        for type in self.plot_windows.keys():
            reset_method = getattr(self.plot_windows[type], 'reset', None)
            if callable(reset_method):
                self.plot_windows[type].reset()

    def labelClickEvent(self, data_type, e):
        if (data_type == AppSettingsChunk.type):
            self.writeSettingsToFile(self.serial)
        else:
            _tmp_plot = partial(map_type_to_plot[data_type], self.serial)
            if data_type in self.plot_windows.keys():
                if self.plot_windows[data_type].isVisible():
                    self.plot_windows[data_type].close()
                del self.plot_windows[data_type]
            self.plot_windows.update([(data_type, _tmp_plot())])
            self.plot_windows[data_type].show()

    def writeSettingsToFile(self, serial):
        group = UDP_IP
        port = UDP_PORT
        _name = ""
        settings_chunk_count = 0
        settings_chunks = {}
        chunks_stored = UwbNetwork.nodes[serial].cdp_pkts_count[AppSettingsChunk.type]
        stored_chunks = UwbNetwork.nodes[serial].cdp_pkts[AppSettingsChunk.type]

        idx = chunks_stored - 1
        done = False
        while idx >= 0 and done == False:
            _chunk = stored_chunks[idx]
            if (_chunk.chunk_id not in settings_chunks):
                if (_name == ""):
                    _name = _chunk.instance_name
                    _name = _name.rstrip(' \t\r\n\0')
                settings_chunks[_chunk.chunk_id] = _chunk.chunk_data
                settings_chunk_count += 1
            if (settings_chunk_count == _chunk.number_of_chunks):
                done = True
            idx -= 1

        write_filestream = open(_name, 'bw')
        for i in range(settings_chunk_count):
            write_filestream.write(settings_chunks[i])
        write_filestream.close()
        print ("Settings saved in the current directory as: " + _name)

    def countClickEvent(self, row, e):
        _cdp_types = np.sort(list(UwbNetwork.nodes[self.serial].cdp_pkts.keys()))
        _type = _cdp_types[row]
        _size = len(UwbNetwork.nodes[self.serial].cdp_pkts[_type])
        for idx in range(-_size, 0):
            print ("RX Time: {:f}".format(UwbNetwork.nodes[self.serial].cdp_pkts_time[_type][idx]),)
            print(UwbNetwork.nodes[self.serial].cdp_pkts[_type][idx])
