import sys
import asyncio
import threading
import struct
from bleak import BleakScanner, BleakClient
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QPushButton, QLabel, QComboBox, QWidget, QHBoxLayout
)
from PyQt5.QtCore import QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from collections import deque

# BLE UUIDs
CHARACTERISTIC_UUID_ADC = "12345678-1234-5678-1234-56789abcdef1"
CHARACTERISTIC_UUID_ACCEL = "12345678-1234-5678-1234-56789abcdef2"
CHARACTERISTIC_UUID_ROT = "12345678-1234-5678-1234-56789abcdef3"

class BLEApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.devices = []
        self.client = None
        self.recording = False
        self.data_file = None

        # Data Buffers
        self.adc_data = deque(maxlen=100)
        self.accel_data = deque(maxlen=100)
        self.rot_data = deque(maxlen=100)

        # Timer for updating graphs
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graphs)

    def init_ui(self):
        self.setWindowTitle("BLE Sensor App")
        self.setGeometry(100, 100, 800, 600)

        # Layouts
        layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Device selection
        self.device_label = QLabel("Devices:")
        self.device_list = QComboBox()
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.scan_devices)

        # Connect Button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_device)

        # Recording Button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)

        # Add widgets to layout
        button_layout.addWidget(self.device_label)
        button_layout.addWidget(self.device_list)
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.record_button)
        layout.addLayout(button_layout)

        # Real-time Graphs
        self.fig, self.ax = plt.subplots(3, 1, figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def scan_devices(self):
        asyncio.run_coroutine_threadsafe(self.async_scan_devices(), asyncio.get_event_loop())

    async def async_scan_devices(self):
        self.devices = await BleakScanner.discover()
        self.device_list.clear()
        for device in self.devices:
            if device.name:
                self.device_list.addItem(device.name)

    def connect_device(self):
        if not self.devices:
            self.connect_button.setText("No Devices Found")
            return

        selected_name = self.device_list.currentText()
        for device in self.devices:
            if device.name == selected_name:
                asyncio.run_coroutine_threadsafe(self.async_connect_device(device), asyncio.get_event_loop())
                return

    async def async_connect_device(self, device):
        try:
            self.client = BleakClient(device)
            await self.client.connect()
            self.connect_button.setText("Connected")
        except Exception as e:
            self.connect_button.setText("Connection Failed")
            print(e)

    def toggle_recording(self):
        if not self.client:
            self.record_button.setText("Connect First")
            return

        if self.recording:
            self.recording = False
            self.record_button.setText("Start Recording")
            self.data_file.close()
            self.timer.stop()
        else:
            self.recording = True
            self.record_button.setText("Stop Recording")
            self.data_file = open("sensor_data.txt", "w")
            self.timer.start(100)
            asyncio.run_coroutine_threadsafe(self.async_receive_data(), asyncio.get_event_loop())

    async def async_receive_data(self):
        try:
            while self.recording:
                adc_raw = await self.client.read_gatt_char(CHARACTERISTIC_UUID_ADC)
                accel_raw = await self.client.read_gatt_char(CHARACTERISTIC_UUID_ACCEL)
                rot_raw = await self.client.read_gatt_char(CHARACTERISTIC_UUID_ROT)

                adc = struct.unpack('8h', adc_raw)
                accel = struct.unpack('3h', accel_raw)
                rot = struct.unpack('3h', rot_raw)

                self.adc_data.append(adc)
                self.accel_data.append(accel)
                self.rot_data.append(rot)

                # Save to file
                self.data_file.write(",".join(map(str, adc + accel + rot)) + "\n")
        except Exception as e:
            print(f"Data reception error: {e}")

    def update_graphs(self):
        self.ax[0].cla()
        self.ax[0].plot([x[0] for x in self.adc_data])
        self.ax[0].set_title("ADC Data")

        self.ax[1].cla()
        self.ax[1].plot([x[0] for x in self.accel_data])
        self.ax[1].set_title("Acceleration Data")

        self.ax[2].cla()
        self.ax[2].plot([x[0] for x in self.rot_data])
        self.ax[2].set_title("Rotation Data")

        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.Thread(target=loop.run_forever, daemon=True).start()
    window = BLEApp()
    window.show()
    sys.exit(app.exec_())
