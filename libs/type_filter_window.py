# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
from pyqtgraph import QtCore, QtWidgets

# Local libraries
import cdp
from settings import *

class TypeFilterWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CUWB Monitor - CDP Data Type Filtering')
        self.num_columns = 10
        self.central = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout()
        self.central.setLayout(self.grid_layout)
        self.setCentralWidget(self.central)
        self.resize(1410, 900)
        self.current_types = set()
        self.filtering = False

        self.filter_toggle_button = QtWidgets.QPushButton('Start Filter')
        self.filter_toggle_button.clicked.connect(self.toggle_filter)
        self.grid_layout.addWidget(self.filter_toggle_button, 0, 0)

        self.search_bar = QtWidgets.QLineEdit()
        self.grid_layout.addWidget(self.search_bar, 1, 0)

        self.type_count = 0
        self.type_checkboxes = dict()
        self.type_labels = dict()
        self.types = dict()

        self.types_widget = QtWidgets.QWidget()
        self.scroll = QtWidgets.QScrollArea()
        self.types_layout = QtWidgets.QGridLayout()

        for cdp_type in cdp.CDP.data_item_classes.keys():
            self.types[cdp_type] = cdp.CDP.data_item_classes[cdp_type].__name__
            self.type_checkboxes[cdp_type] = QtWidgets.QCheckBox()
            self.type_labels[cdp_type] = QtWidgets.QLabel()
            self.type_count += 1

        self.types[UNKNOWN_FILTER_TYPE] = 'Unknown Types'
        self.type_checkboxes[UNKNOWN_FILTER_TYPE] = QtWidgets.QCheckBox()
        self.type_labels[UNKNOWN_FILTER_TYPE] = QtWidgets.QLabel()

        type_per_col = (int(self.type_count / (self.num_columns / 2)) + 1)
        row = 0
        col = 0
        for cdp_type in sorted(self.types.keys()):
            self.types_layout.addWidget(self.type_checkboxes[cdp_type], row, col)
            self.types_layout.addWidget(self.type_labels[cdp_type], row, col + 1)
            self.type_labels[cdp_type].setText(self.types[cdp_type])
            self.type_labels[cdp_type].setAlignment(QtCore.Qt.AlignLeft)
            row += 1
            if row > type_per_col:
                col += 2
                row = 0

        self.types_widget.setLayout(self.types_layout)
        self.scroll.setWidget(self.types_widget)
        self.grid_layout.addWidget(self.scroll, 2, 0)

        self.timer = self.startTimer(QPLOT_FREQUENCY)

    def timerEvent(self, e):
        for cdp_type in self.types.keys():
            if self.filtering:
                if self.type_checkboxes[cdp_type].isChecked() and cdp_type not in self.current_types:
                    self.current_types.add(cdp_type)
                elif not self.type_checkboxes[cdp_type].isChecked() and cdp_type in self.current_types:
                    self.current_types.remove(cdp_type)

            if self.search_bar.text() != "":
                if self.search_bar.text().lower() in self.types[cdp_type].lower():
                    self.type_labels[cdp_type].setStyleSheet(GetClickableColor())
                else:
                    self.type_labels[cdp_type].setStyleSheet('color:grey')
            else:
                self.type_labels[cdp_type].setStyleSheet(GetTitleColor())

    def toggle_filter(self):
        if not self.filtering:
            self.filtering = True
            self.filter_toggle_button.setText('Stop Filter')
        else:
            self.filtering = False
            self.filter_toggle_button.setText('Start Filter')
