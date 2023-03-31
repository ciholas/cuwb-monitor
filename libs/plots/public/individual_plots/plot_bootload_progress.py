# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from functools import partial

# Local libraries
from cdp import BootloadProgress
from network_objects import *
from settings import *
from generic_plots import *

class PlotBootloadProgress(QtWidgets.QMainWindow):
    type = BootloadProgress.type
    
    def __init__(self, serial):
        
        QtWidgets.QMainWindow.__init__(self)
        self.serial = serial

        self.central = QtWidgets.QScrollArea()
        self.central.setWidgetResizable(True)
        self.central_inner_widget = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.setWindowTitle("CUWB Monitor- Bootload Progress")

        self.sub_windows ={}
        self.id_total = 0
        self.prev_count = 0
        self.from_id_id_labels = {}
        self.from_id_count_labels = {}
        self.from_id_freq_labels = {}
        self.from_id_enable_checks = {}
        self.from_id_count = {}
        self.from_id_frequency_deques = {}
        self.from_ids = np.array([])

        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), 0, 0)
        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), 0, 2)
        self.grid_layout.addWidget(QtWidgets.QLabel("Print"), 0, 3)

        self.running = True
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.updateLabels()
        #This allows for a dynamic window size where the number of serials already in the window after
        #one pass affects the size of the serial choice window.
        row_height = 20
        self.resize(400, row_height+(row_height * len(self.from_id_id_labels)))

        self.central_inner_widget.setLayout(self.grid_layout)
        self.central.setWidget(self.central_inner_widget)
        self.setCentralWidget(self.central)

    def updateLabels(self):
        if BootloadProgress.type in UwbNetwork.nodes[self.serial].cdp_pkts_count:
            _current_size = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] - self.prev_count
            if _current_size > 1000: _current_size = 1000
            self.prev_count = UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]
            for idx in range(_current_size):
                _target_id = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size].serial_number.as_int
                if not (_target_id in self.from_ids):
                    self.from_id_id_labels.update([(self.id_total, QtWidgets.QLabel())])
                    self.from_id_count_labels.update([(self.id_total, QtWidgets.QLabel())])
                    self.from_id_freq_labels.update([(self.id_total, QtWidgets.QLabel())])
                    self.from_id_enable_checks.update([(self.id_total, QtWidgets.QCheckBox())])
                    self.from_id_count.update([(_target_id, 0)])
                    self.from_id_frequency_deques.update([(_target_id, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
                    self.from_ids = np.sort(np.append(self.from_ids, _target_id))

                    _row = self.id_total
                    _column = 0
                    self.grid_layout.addWidget(self.from_id_id_labels[self.id_total], _row + 1, _column + 0)
                    self.grid_layout.addWidget(self.from_id_count_labels[self.id_total], _row + 1, _column + 1)
                    self.grid_layout.addWidget(self.from_id_freq_labels[self.id_total], _row + 1, _column + 2)
                    self.grid_layout.addWidget(self.from_id_enable_checks[self.id_total], _row + 1, _column + 3)

                    if _column > 0:
                        _row = 2
                        self.grid_layout.addWidget(QtWidgets.QLabel("Serial#"), _row, _column + 0)
                        self.grid_layout.addWidget(QtWidgets.QLabel("Packet Count"), _row, _column + 1)
                        self.grid_layout.addWidget(QtWidgets.QLabel("Frequency"), _row, _column + 2)
                        self.grid_layout.addWidget(QtWidgets.QLabel("Print"), _row, _column + 3)
                    self.id_total += 1

                self.from_id_count[_target_id] += 1

                if _target_id in self.from_ids:
                    _row = np.where(self.from_ids==_target_id)[0][0]
                    if self.from_id_enable_checks[_row].isChecked():
                        print(UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size])

                if _target_id in self.sub_windows.keys():
                    _packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][idx - _current_size]
                    self.sub_windows[_target_id].updateLabels(_packet)

            for _target_id in self.from_ids:
                self.from_id_frequency_deques[_target_id].append((self.from_id_count[_target_id], time.monotonic()))

            for _row in range(self.id_total):
                _target_id = int(self.from_ids[_row])
                if self.from_id_id_labels[_row].text() != '0x{:08X}'.format(_target_id):
                    self.from_id_id_labels[_row].setText('0x{:08X}'.format(_target_id))
                    self.from_id_id_labels[_row].setStyleSheet(GetClickableColor())
                    self.from_id_id_labels[_row].mouseReleaseEvent = partial(self.labelClickEvent, _target_id)

                _freq = UwbNetwork.nodes[self.serial].calculate_frequency(self.from_id_frequency_deques[_target_id])
                self.from_id_count_labels[_row].setText('{:5d}'.format(self.from_id_count[_target_id]))
                self.from_id_freq_labels[_row].setText('{:5.1f}Hz'.format(_freq))

    def labelClickEvent(self, item_serial, e):
        self.sub_windows[item_serial] = PlotBootloadProgressSubWindow(item_serial, self)
        if UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type] != 0:
            index = -1
            while -index < UwbNetwork.nodes[self.serial].cdp_pkts_count[self.type]:
                packet = UwbNetwork.nodes[self.serial].cdp_pkts[self.type][index]
                if packet.serial_number.as_int == item_serial:
                    self.sub_windows[item_serial].updateLabels(packet)
                    break
                index -= 1
        self.sub_windows[item_serial].show()

    def timerEvent(self, e):
        if not UwbNetwork.running:
            self.killTimer(self.timer)
            self.running = False
            self.close()
            return
        if self.running:
            self.updateLabels()
        else:
            self.killTimer(self.timer)
            self.close()

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.running = False
        for window in self.sub_windows.values():
            if window.isVisible():
                window.close()
        self.close()

    def reset(self):
        for window in self.sub_windows.values():
            window.reset()

class PlotBootloadProgressSubWindow(QtWidgets.QMainWindow):

    def __init__(self, device_serial, parent):
        
        QtWidgets.QMainWindow.__init__(self)

        self.central = QtWidgets.QWidget()
        self.grid_main = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_main)
        self.setCentralWidget(self.central)
        self.parent = parent

        self.setWindowTitle("CUWB Monitor- Bootload Progress ID 0x{:08X}".format(device_serial))
        self.device_serial = device_serial
        length = 400
        width = 180
        self.resize(length, width)

        self.running = True
        self.timer = self.startTimer(QPLOT_FREQUENCY)
        self.createLayout()

    def createLayout(self):
        self.bootload_widgets = []
        grid_rows = []
        first_row = 0
        total_rows = 4

        createRows(self.bootload_widgets, grid_rows, self.grid_main, first_row, total_rows)

        curr_row = 0
        spacer_size = 20

        #Row 0
        graphics = pg.GraphicsLayoutWidget(show = False)
        graphics.setFixedSize(380.0,70.0)
        grid_rows[curr_row].addWidget(graphics, 0, 0)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 1)
        graphics.ci.setContentsMargins(0,0,0,0)
        self.flags_progress = pg.ImageItem()
        #Pyqtgraph color schemes made it to where the unset flags are 1 and set flags are 0
        self.flags_progress.setImage(np.ones((200,1)))
        flags_viewer = graphics.addViewBox()
        flags_viewer.setMouseEnabled(False, False)
        flags_viewer.setAspectLocked(False)
        #flags_viewer.setRange(rect = graphics.ci.boundingRect())
        flags_viewer.addItem(self.flags_progress)
        color_scheme = pg.colormap.get("CET-D3")
        flags_color = pg.ColorBarItem(values = (0,1), colorMap = color_scheme)
        flags_color.setImageItem(self.flags_progress)
        curr_row += 1

        #Row 1
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Last Signal's Strength: "), 0, 0)
        self.last_packet_rssi_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.last_packet_rssi_label, 0, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Last Heard Packet Time: "), 0, 3)
        self.last_packet_time_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.last_packet_time_label, 0, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 5)
        curr_row += 1

        #Row 2
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Max # of Sectors per Flag: "), 0, 0)
        self.max_sectors_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.max_sectors_label, 0, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0), 0, 2)
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Last Max Sector Flag: "), 0, 3)
        self.last_max_sector_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.last_max_sector_label, 0, 4)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 5)
        curr_row += 1

        #Row 3
        grid_rows[curr_row].addWidget(QtWidgets.QLabel("Completion: "), 0, 0)
        self.sectors_complete_label = QtWidgets.QLabel("?")
        grid_rows[curr_row].addWidget(self.sectors_complete_label, 0, 1)
        grid_rows[curr_row].addItem(QtWidgets.QSpacerItem(spacer_size, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum), 0, 2)

    def updateLabels(self, packet):
        MAX_SIGNAL_STRENGTH = 255
        self.last_packet_rssi_label.setText("{}%".format(((packet.last_received_total_path_rssi/MAX_SIGNAL_STRENGTH)*100)))
        self.last_packet_time_label.setText("{}s".format(packet.last_heard_packet_time))
        self.max_sectors_label.setText("{}".format(packet.max_sectors_per_flag))
        self.last_max_sector_label.setText("{}".format(packet.last_max_sector_flag))
        self.sectors_complete_label.setText("{}%".format(packet.percentage))
        flags = []
        #Parse each byte down into a list of bool and then if the boolean is true that means the flag is set
        for byte in packet.flags:
            flags_of_byte = [bool(byte & (1<<n)) for n in range(8)]
            for flag in flags_of_byte:
                #Pyqtgraph color schemes made it to where the unset flags are 1 and set flags are 0
                if flag:
                    flags.append([0])
                else:
                    flags.append([1])
        flags_array = np.array(flags)
        self.flags_progress.setImage(flags_array)

    def timerEvent(self, e):
        if not UwbNetwork.running or not self.parent.running:
            self.killTimer(self.timer)
            self.close()
            return

    def closeEvent(self, e):
        self.killTimer(self.timer)
        self.close()

    def reset(self):
        self.last_packet_rssi_label.setText("?")
        self.last_packet_time_label.setText("?")
        self.max_sectors_label.setText("?")
        self.last_max_sector_label.setText("?")
        self.sectors_complete_label.setText("0%")
        self.flags_progress.setValue(0)
