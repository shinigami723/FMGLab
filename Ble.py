from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
import asyncio
from bleak import BleakScanner, BleakClient
import threading
import matplotlib.pyplot as plt
from collections import deque
import struct

# Constants
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHARACTERISTIC_UUID_ADC = "12345678-1234-5678-1234-56789abcdef1"
CHARACTERISTIC_UUID_ACCEL = "12345678-1234-5678-1234-56789abcdef2"
CHARACTERISTIC_UUID_ROT = "12345678-1234-5678-1234-56789abcdef3"

# Asyncio event loop for Bleak
asyncio_loop = asyncio.get_event_loop()

class SensorApp(App):
    def build(self):
        self.client = None
        self.recording = False
        self.filename = "data.txt"
        self.data_buffer = {"adc": deque(maxlen=100), "accel": deque(maxlen=100), "rot": deque(maxlen=100)}

        # UI Layout
        layout = BoxLayout(orientation="vertical", spacing=10, padding=20)

        self.refresh_button = Button(text="Refresh and Connect", size_hint=(1, 0.2))
        self.refresh_button.bind(on_press=self.refresh_and_connect)
        layout.add_widget(Label(text="BLE Sensor App", size_hint=(1, 0.1)))
        layout.add_widget(self.refresh_button)

        self.record_button = Button(text="Start Recording", size_hint=(1, 0.2))
        self.record_button.bind(on_press=self.toggle_recording)
        layout.add_widget(self.record_button)

        self.visualize_button = Button(text="Visualize Data", size_hint=(1, 0.2))
        self.visualize_button.bind(on_press=self.visualize_data)
        layout.add_widget(self.visualize_button)

        return layout

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.devices = []

    def refresh_and_connect(self, instance):
        asyncio.run_coroutine_threadsafe(self.scan_and_connect(), asyncio_loop)

    async def scan_and_connect(self):
        devices = await BleakScanner.discover(timeout=5.0)
        for device in devices:
            if device.name == "ESP32_Sensor_Module":  # Replace with your ESP32 device name
                await self.connect_to_device(device)
                break

    async def connect_to_device(self, device):
        try:
            if self.client:
                await self.client.disconnect()
            
            self.client = BleakClient(device)
            print(f"Attempting to connect to {device.name} @ {device.address}")
            
            await self.client.connect(timeout=20.0)
            
            # Add a small delay before service discovery
            await asyncio.sleep(2)
            
            is_connected = await self.client.is_connected()
            
            if is_connected:
                self.refresh_button.text = f"Connected to {device.name}"
                print(f"Connected to {device.name} @ {device.address}")
                # Discover services to verify connection
                services = await self.client.get_services()
                for service in services:
                    print(f"Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"  Characteristic: {char.uuid}")
            else:
                self.refresh_button.text = "Failed to Connect"
                print(f"Failed to connect to {device.name} @ {device.address}")
        except Exception as e:
            self.refresh_button.text = "Failed to Connect"
            print(f"Error connecting to device: {e}")

    def toggle_recording(self, instance):
        if not self.client or not self.client.is_connected:
            self.record_button.text = "Connect First"
            return

        if self.recording:
            self.recording = False
            self.record_button.text = "Start Recording"
        else:
            self.recording = True
            self.record_button.text = "Stop Recording"
            asyncio.run_coroutine_threadsafe(self.start_receiving_data(), asyncio_loop)

    async def start_receiving_data(self):
        try:
            while self.recording:
                adc_data = await self.client.read_gatt_char(CHARACTERISTIC_UUID_ADC)
                accel_data = await self.client.read_gatt_char(CHARACTERISTIC_UUID_ACCEL)
                rot_data = await self.client.read_gatt_char(CHARACTERISTIC_UUID_ROT)

                # Handle raw ADC data
                adc_values = struct.unpack('8h', adc_data)

                # Handle raw accelerometer data
                accel_values = struct.unpack('3h', accel_data)

                # Handle raw rotation data
                rot_values = struct.unpack('3h', rot_data)

                self.data_buffer["adc"].append(adc_values)
                self.data_buffer["accel"].append(accel_values)
                self.data_buffer["rot"].append(rot_values)

                with open(self.filename, "a") as f:
                    f.write(",".join(map(str, adc_values + accel_values + rot_values)) + "\n")
        except Exception as e:
            print(f"Error receiving data: {e}")

    def visualize_data(self, instance):
        if not self.data_buffer["adc"]:
            return

        plt.figure("Real-Time Sensor Data")
        plt.subplot(3, 1, 1)
        plt.plot(list(range(len(self.data_buffer["adc"]))), [v[0] for v in self.data_buffer["adc"]])
        plt.title("ADC Data")

        plt.subplot(3, 1, 2)
        plt.plot(list(range(len(self.data_buffer["accel"]))), [v[0] for v in self.data_buffer["accel"]])
        plt.title("Acceleration Data")

        plt.subplot(3, 1, 3)
        plt.plot(list(range(len(self.data_buffer["rot"]))), [v[0] for v in self.data_buffer["rot"]])
        plt.title("Rotation Data")

        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    threading.Thread(target=asyncio_loop.run_forever).start()
    SensorApp().run()
