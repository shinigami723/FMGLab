import socket
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
import matplotlib.pyplot as plt
import numpy as np
from collections import deque

# UDP Settings
UDP_IP = "0.0.0.0"  # Listen to all interfaces
UDP_PORT = 5000     # Port where ESP32 sends data
BUFFER_SIZE = 1024  # UDP buffer size

# Global variables
received_data = deque(maxlen=100)  # Store the last 100 packets
data_fields = {}  # Store data fields for visualization
data_file = "received_data.txt"

# Define labels for incoming data fields
labels = ['Counter', 'ADC1', 'ADC2', 'ADC3', 'ADC4', 'ADC5', 'ADC6', 'ADC7', 'ADC8', 'Ax', 'Ay', 'Az', 'Gx', 'Gy', 'Gz']

# UDP Listening Thread
def udp_listener():
    global received_data, data_fields
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_sock.bind((UDP_IP, UDP_PORT))
        print(f"Listening on UDP {UDP_IP}:{UDP_PORT}...")
        while True:
            data, addr = udp_sock.recvfrom(BUFFER_SIZE)
            decoded_data = data.decode('utf-8')
            with open(data_file, "a") as f:
                f.write(decoded_data + "\n")  # Save data to a text file
            
            data_list = decoded_data.split(",")
            if len(data_list) >= len(labels):
                received_data.append(data_list)  # Store full packet
                for i, label in enumerate(labels):
                    data_fields[label] = data_list[i]  # Update individual fields

# Kivy GUI Class
class ReceiverApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Data BoxLayout (GridLayout for values)
        self.data_layout = GridLayout(cols=8, size_hint_y=None, height=200)

        # ADC1 to ADC8 values
        self.data_labels_adc = {}
        for i in range(1, 9):
            label = Label(text=f"ADC{i}: N/A", font_size=16)
            self.data_labels_adc[f"ADC{i}"] = label
            self.data_layout.add_widget(label)

        # Acceleration values
        self.data_labels_accel = {}
        for ax in ['Ax', 'Ay', 'Az']:
            label = Label(text=f"{ax}: N/A", font_size=16)
            self.data_labels_accel[ax] = label
            self.data_layout.add_widget(label)

        # Gyroscope values
        self.data_labels_gyro = {}
        for gx in ['Gx', 'Gy', 'Gz']:
            label = Label(text=f"{gx}: N/A", font_size=16)
            self.data_labels_gyro[gx] = label
            self.data_layout.add_widget(label)

        # Add Data Layout to Main Layout
        self.layout.add_widget(self.data_layout)

        # Buttons BoxLayout (Centered)
        self.button_layout = BoxLayout(size_hint_y=None, height=80, orientation='horizontal', padding=20, spacing=20)
        self.button_layout.add_widget(BoxLayout())  # Empty box for spacing
        self.start_button = self.create_button("Start Listening")
        self.button_layout.add_widget(self.start_button)
        self.plot_button = self.create_button("Visualize Data")
        self.button_layout.add_widget(self.plot_button)
        self.button_layout.add_widget(BoxLayout())  # Empty box for spacing

        # Add Button Layout to Main Layout
        self.layout.add_widget(self.button_layout)

        # Clock for updating the GUI
        Clock.schedule_interval(self.update_labels, 0.5)

        # Clock for periodically updating the plot
        Clock.schedule_interval(self.update_plot, 1)  # Update the plot every 1 second

        return self.layout

    def create_button(self, text):
        """ Helper method to create a button """
        button = Button(text=text, size_hint=(None, None), size=(200, 50))
        if text == "Start Listening":
            button.bind(on_press=self.start_udp_listener)
        elif text == "Visualize Data":
            button.bind(on_press=self.plot_data)
        return button

    def start_udp_listener(self, instance):
        # Update the text of the start_button when the listener starts
        self.start_button.text = "Listening..."
        udp_thread = threading.Thread(target=udp_listener, daemon=True)
        udp_thread.start()

    def update_labels(self, dt):
        if received_data:
            for label_name, label_widget in self.data_labels_adc.items():
                if label_name in data_fields:
                    label_widget.text = f"{label_name}: {data_fields[label_name]}"

            for label_name, label_widget in self.data_labels_accel.items():
                if label_name in data_fields:
                    label_widget.text = f"{label_name}: {data_fields[label_name]}"

            for label_name, label_widget in self.data_labels_gyro.items():
                if label_name in data_fields:
                    label_widget.text = f"{label_name}: {data_fields[label_name]}"

    def plot_data(self, instance):
        if received_data:
            adc_values = []
            for data in received_data:
               adc_values.extend([float(data[i]) for i in range(1, 9)])
            
            accel_values = []
            for data in received_data:
                accel_values.extend([float(data[i]) for i in range(9, 12)])

            gyro_values = []
            for data in received_data:
                gyro_values.extend([float(data[i]) for i in range(12, 15)])

            # Create figure
            fig, axs = plt.subplots(3, 1, figsize=(10, 8))

            # Plot ADC values
            axs[0].plot(np.arange(len(adc_values)), adc_values)
            axs[0].set_title("ADC Values")
            axs[0].set_xlabel("Samples")
            axs[0].set_ylabel("ADC Value")

            # Plot Acceleration values
            axs[1].plot(np.arange(len(accel_values)), accel_values)
            axs[1].set_title("Acceleration Values")
            axs[1].set_xlabel("Samples")
            axs[1].set_ylabel("Acceleration (g)")

            # Plot Gyroscope values
            axs[2].plot(np.arange(len(gyro_values)), gyro_values)
            axs[2].set_title("Gyroscope Values")
            axs[2].set_xlabel("Samples")
            axs[2].set_ylabel("Gyroscope (°/s)")

            plt.tight_layout()
            plt.show()

    def update_plot(self, dt):
        """ Periodically update the plot with the latest data """
        if received_data:
            adc_values = []
            for data in received_data:
                adc_values.extend([float(data[i]) for i in range(1, 9)])
            
            accel_values = []
            for data in received_data:
                accel_values.extend([float(data[i]) for i in range(9, 12)])

            gyro_values = []
            for data in received_data:
                gyro_values.extend([float(data[i]) for i in range(12, 15)])

            # Create figure
            fig, axs = plt.subplots(3, 1, figsize=(10, 8))

            # Plot ADC values
            axs[0].plot(np.arange(len(adc_values)), adc_values)
            axs[0].set_title("ADC Values")
            axs[0].set_xlabel("Samples")
            axs[0].set_ylabel("ADC Value")

            # Plot Acceleration values
            axs[1].plot(np.arange(len(accel_values)), accel_values)
            axs[1].set_title("Acceleration Values")
            axs[1].set_xlabel("Samples")
            axs[1].set_ylabel("Acceleration (g)")

            # Plot Gyroscope values
            axs[2].plot(np.arange(len(gyro_values)), gyro_values)
            axs[2].set_title("Gyroscope Values")
            axs[2].set_xlabel("Samples")
            axs[2].set_ylabel("Gyroscope (°/s)")

            plt.tight_layout()
            plt.draw()

# Run the app
if __name__ == "__main__":
    ReceiverApp().run()
