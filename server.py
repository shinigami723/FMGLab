import socket
import threading
import time
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.core.window import Window
import pywebview

# UDP Settings
UDP_IP = "0.0.0.0"  # Listen to all interfaces
UDP_PORT = 5000     # Port where ESP32 sends data
BUFFER_SIZE = 1024  # UDP buffer size

received_data = []  # Store received data

# UDP Listener Thread
def udp_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_sock.bind((UDP_IP, UDP_PORT))
        print(f"Listening on UDP {UDP_IP}:{UDP_PORT}...")
        while True:
            data, addr = udp_sock.recvfrom(BUFFER_SIZE)
            decoded_data = data.decode('utf-8')
            data_list = decoded_data.split(",")
            if len(data_list) >= 15:
                received_data.append(data_list)
                if len(received_data) > 100:  # Limit to last 100 data points
                    received_data.pop(0)
                time.sleep(0.1)  # Prevent CPU overuse

# HTML Content for Graphs
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-Time Data Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.1/socket.io.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(120deg, #f8f9fa, #e9ecef);
        }

        h1 {
            text-align: center;
            color: #333;
            font-weight: bold;
            margin: 20px 0;
        }

        .charts-container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 10px;
            height: calc(100vh - 60px);
            padding: 10px;
        }

        .chart-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            padding: 10px;
            overflow: hidden;
        }

        .large-chart {
            grid-row: span 2;
        }

        canvas {
            width: 100% !important;
            height: 100% !important;
        }
    </style>
</head>
<body>
    <h1>Real-Time Data Visualization</h1>
    <div class="charts-container">
        <!-- ADC Graph -->
        <div class="chart-container large-chart">
            <canvas id="adcChart"></canvas>
        </div>

        <!-- Acceleration Graph -->
        <div class="chart-container">
            <canvas id="accelChart"></canvas>
        </div>

        <!-- Rotation Graph -->
        <div class="chart-container">
            <canvas id="rotationChart"></canvas>
        </div>
    </div>

    <script>
        const socket = io();
        const maxVisiblePoints = 100;
        const updateInterval = 100;
        const adcBuffer = [];
        const accelBuffer = [];
        const rotationBuffer = [];

        function createDataset(label, color) {
            return {
                label: label,
                data: [],
                borderColor: color,
                backgroundColor: 'rgba(0, 0, 0, 0)',
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 0
            };
        }

        function createChartOptions(xLabel, yLabel) {
            return {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: '#333',
                            font: { size: 14 }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        cornerRadius: 6
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: xLabel,
                            color: '#555',
                            font: { size: 14, weight: 'bold' }
                        },
                        grid: { color: 'rgba(220, 220, 220, 0.3)' },
                        ticks: { color: '#333' }
                    },
                    y: {
                        title: {
                            display: true,
                            text: yLabel,
                            color: '#555',
                            font: { size: 14, weight: 'bold' }
                        },
                        grid: { color: 'rgba(220, 220, 220, 0.3)' },
                        ticks: { color: '#333' }
                    }
                }
            };
        }

        const ctxAdc = document.getElementById('adcChart').getContext('2d');
        const adcDatasets = Array(8).fill().map((_, i) => 
            createDataset(`ADC ${i + 1}`, `hsl(${i * 45}, 80%, 60%)`)
        );

        const ctxAccel = document.getElementById('accelChart').getContext('2d');
        const accelDatasets = [
            createDataset("Acceleration X", "rgba(255, 99, 132, 1)"),
            createDataset("Acceleration Y", "rgba(54, 162, 235, 1)"),
            createDataset("Acceleration Z", "rgba(75, 192, 192, 1)")
        ];

        const ctxRotation = document.getElementById('rotationChart').getContext('2d');
        const rotationDatasets = [
            createDataset("Rotation X", "rgba(153, 102, 255, 1)"),
            createDataset("Rotation Y", "rgba(255, 159, 64, 1)"),
            createDataset("Rotation Z", "rgba(255, 205, 86, 1)")
        ];

        const adcChart = new Chart(ctxAdc, {
            type: 'line',
            data: { labels: [], datasets: adcDatasets },
            options: createChartOptions("Time (s)", "ADC Value")
        });

        const accelChart = new Chart(ctxAccel, {
            type: 'line',
            data: { labels: [], datasets: accelDatasets },
            options: createChartOptions("Time (s)", "Acceleration (g)")
        });

        const rotationChart = new Chart(ctxRotation, {
            type: 'line',
            data: { labels: [], datasets: rotationDatasets },
            options: createChartOptions("Time (s)", "Rotation (°/s)")
        });

        function updateChart(chart, buffer, maxVisiblePoints) {
            if (buffer.length > 0) {
                buffer.forEach(({ counter, values }) => {
                    chart.data.labels.push(counter);
                    chart.data.datasets.forEach((dataset, index) => {
                        dataset.data.push(values[index]);
                    });
                    if (chart.data.labels.length > maxVisiblePoints) {
                        chart.data.labels.shift();
                        chart.data.datasets.forEach(dataset => dataset.data.shift());
                    }
                });
                buffer.length = 0;
                chart.update();
            }
        }

        setInterval(() => {
            updateChart(adcChart, adcBuffer, maxVisiblePoints);
            updateChart(accelChart, accelBuffer, maxVisiblePoints);
            updateChart(rotationChart, rotationBuffer, maxVisiblePoints);
        }, updateInterval);

        socket.on('new_data', (data) => {
            const { counter, adc, acceleration, rotation } = data;
            adcBuffer.push({ counter, values: adc });
            accelBuffer.push({ counter, values: acceleration });
            rotationBuffer.push({ counter, values: rotation });
        });
    </script>
</body>
</html>
"""

# Kivy App with UDP Listener and WebView for Graphs
class ReceiverApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')

        # Listening Button
        self.listen_button = Button(text="Listening", size_hint=(1, 0.1))
        self.listen_button.bind(on_press=self.start_udp_listener)

        # Visualize Data Button
        self.visualize_button = Button(text="Visualize Data", size_hint=(1, 0.1))
        self.visualize_button.bind(on_press=self.visualize_data)

        # Layout for buttons
        self.buttons_layout = BoxLayout(size_hint=(1, 0.1))
        self.buttons_layout.add_widget(self.listen_button)
        self.buttons_layout.add_widget(self.visualize_button)

        # Graph Display Area
        self.graph_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.8))
        
        self.layout.add_widget(self.buttons_layout)
        self.layout.add_widget(self.graph_layout)

        # Start UDP listener thread
        self.udp_thread = threading.Thread(target=udp_listener, daemon=True)
        self.udp_thread.start()

        return self.layout

    def start_udp_listener(self, instance):
        """Start listening for data"""
        print("UDP Listener started...")

    def visualize_data(self, instance):
        """Display the graphs inside the app using HTML"""
        # Clear any previous widgets in the graph layout
        self.graph_layout.clear_widgets()

        # Create a webview window in a Kivy widget using HTML graphs
        webview.create_window("Real-Time Data Visualization", html=html_content)
        webview.start()

if __name__ == "__main__":
    ReceiverApp().run()
