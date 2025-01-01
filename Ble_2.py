from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel, QComboBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QThread, pyqtSignal
import os
import sys
import asyncio
from qasync import QEventLoop
from bleak import BleakScanner, BleakClient
import nest_asyncio

# Allow nested asyncio event loops
nest_asyncio.apply()

class BluetoothScanner(QThread):
    devices_found = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    async def scan(self):
        try:
            devices = await BleakScanner.discover()
            device_list = [(device.name or "Unknown", device.address) for device in devices]
            self.devices_found.emit(device_list)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def run(self):
        asyncio.run(self.scan())

class BluetoothConnector(QThread):
    connected = pyqtSignal(bool, str)

    def __init__(self, device_addr):
        super().__init__()
        self.device_addr = device_addr
        self.client = None

    async def connect_to_device(self):
        try:
            self.client = BleakClient(self.device_addr)
            await self.client.connect()
            if self.client.is_connected:
                self.connected.emit(True, f"Connected to {self.device_addr}")
            else:
                self.connected.emit(False, "Connection failed.")
        except Exception as e:
            self.connected.emit(False, f"Connection error: {str(e)}")

    def run(self):
        asyncio.run(self.connect_to_device())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Data Visualization with Bluetooth")
        self.setGeometry(100, 100, 1200, 800)

        self.is_recording = False
        self.client = None

        # UI Components
        self.setup_ui()

        # Bluetooth Scanner
        self.bt_scanner = BluetoothScanner()
        self.bt_scanner.devices_found.connect(self.update_device_list)
        self.bt_scanner.error_occurred.connect(self.handle_scan_error)

    def setup_ui(self):
        self.browser = QWebEngineView()
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        html_path = os.path.join(base_path, "index.html")
        self.browser.setUrl(QUrl.fromLocalFile(html_path))

        self.scan_button = QPushButton("Scan Bluetooth")
        self.scan_button.clicked.connect(self.scan_bluetooth)

        self.connect_button = QPushButton("Connect")
        self.connect_button.setEnabled(False)
        self.connect_button.clicked.connect(self.connect_device)

        self.device_selector = QComboBox()
        self.device_selector.setEnabled(False)

        self.status_label = QLabel("Status: Disconnected")

        self.record_button = QPushButton("Start Recording")
        self.record_button.setEnabled(False)
        self.record_button.clicked.connect(self.toggle_recording)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.device_selector)
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.record_button)

        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def scan_bluetooth(self):
        self.status_label.setText("Status: Scanning...")
        self.device_selector.setEnabled(False)
        self.device_selector.clear()
        self.bt_scanner.start()

    def handle_scan_error(self, error_message):
        self.status_label.setText(f"Status: Scan Error - {error_message}")

    def update_device_list(self, devices):
        self.status_label.setText("Status: Scan Complete")
        self.device_selector.setEnabled(True)
        self.device_selector.addItem("Select Device")
        for name, addr in devices:
            self.device_selector.addItem(f"{name} ({addr})")

        self.connect_button.setEnabled(True)

    def connect_device(self):
        selection = self.device_selector.currentText()
        if selection == "Select Device":
            self.status_label.setText("Status: No device selected.")
            return

        device_addr = selection.split("(")[-1].strip(")")
        self.status_label.setText(f"Status: Connecting to {device_addr}...")

        self.connector = BluetoothConnector(device_addr)
        self.connector.connected.connect(self.on_device_connected)
        self.connector.start()

    def on_device_connected(self, success, message):
        self.status_label.setText(f"Status: {message}")
        if success:
            self.connect_button.setEnabled(False)
            self.record_button.setEnabled(True)
            self.client = self.connector.client

    def toggle_recording(self):
        if not self.client or not self.client.is_connected:
            self.status_label.setText("Status: No device connected.")
            return

        if not self.is_recording:
            self.is_recording = True
            self.record_button.setText("Stop Recording")
            self.status_label.setText("Status: Recording...")
            asyncio.create_task(self.record_data())
        else:
            self.is_recording = False
            self.record_button.setText("Start Recording")
            self.status_label.setText("Status: Recording stopped.")

    async def record_data(self):
        adc_uuid = "12345678-1234-5678-1234-56789abcdef1"
        accel_uuid = "12345678-1234-5678-1234-56789abcdef2"
        rot_uuid = "12345678-1234-5678-1234-56789abcdef3"

        try:
            with open("recorded_data.txt", "w") as file:
                while self.is_recording:
                    if not self.client.is_connected:
                        self.status_label.setText("Status: Device disconnected. Reconnecting...")
                        try:
                            await self.client.connect()
                            if not self.client.is_connected:
                                raise Exception("Reconnection failed.")
                            self.status_label.setText("Status: Reconnected.")
                        except Exception as reconnect_error:
                            self.status_label.setText(f"Status: Reconnection error - {str(reconnect_error)}")
                            self.is_recording = False
                            break

                    try:
                        # Attempt to read data
                        adc_data = await self.client.read_gatt_char(adc_uuid)
                        accel_data = await self.client.read_gatt_char(accel_uuid)
                        rot_data = await self.client.read_gatt_char(rot_uuid)

                        # Convert the binary data to integers (assuming little-endian format)
                        adc_values = list(int.from_bytes(adc_data[i:i+2], byteorder='little', signed=True) for i in range(0, len(adc_data), 2))
                        accel_values = list(int.from_bytes(accel_data[i:i+2], byteorder='little', signed=True) for i in range(0, len(accel_data), 2))
                        rot_values = list(int.from_bytes(rot_data[i:i+2], byteorder='little', signed=True) for i in range(0, len(rot_data), 2))

                        # Write to file
                        file.write(f"{adc_values},{accel_values},{rot_values}\n")
                        file.flush()

                        print(f"{adc_values}, {accel_values}, {rot_values}")
                    except Exception as read_error:
                        self.status_label.setText(f"Status: Read error - {str(read_error)}")
                        await asyncio.sleep(2)  # Add a short delay before retrying

                    await asyncio.sleep(1)  # Adjust delay to avoid overwhelming the BLE device
        except Exception as e:
            self.status_label.setText(f"Status: Error during recording - {str(e)}")
            self.is_recording = False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    main_window = MainWindow()
    main_window.show()

    with loop:
        sys.exit(loop.run_forever())