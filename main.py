import sys
import threading
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QWidget, QMessageBox, 
                             QProgressBar, QDesktopWidget)
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtCore import Qt, QTimer

# Import detection dependencies
from ultralytics import YOLOWorld
import time
import requests
from twilio.rest import Client
import vimeo
import os
from flask import send_from_directory
import shutil
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps


# Flask and WebSocket dependencies
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import webbrowser

# Twilio and Vimeo credentials
ACCOUNT_SID = '---'
AUTH_TOKEN = '---'
TWILIO_PHONE_NUMBER = '+18452187956'
app = Flask(__name__)
app.config['DEBUG'] = True  # Enable debugging
app.secret_key = os.urandom(24)  # Generate a random secret key
socketio = SocketIO(app)
STATIONS = {
    'station1': {
        'latitude': 16.0,
        'phone': '+918099963336',
        'username': 'station1',
        'password': 'station1pass'
    },
    'station2': {
        'latitude': 0.0,  # Default for other locations
        'phone': '--',
        'username': 'station2',
        'password': 'station2pass'
    },
    'central': {
        'phone': '---',
        'username': 'central',
        'password': 'centralpass'
    }
}

VIMEO_CLIENT_ID = '--'
VIMEO_CLIENT_SECRET = '---'
VIMEO_ACCESS_TOKEN = '---'

# Flask Web Alert Setup
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@login_required
def home():
    try:
        station = session.get('station', '')
        latitude = STATIONS.get(station, {}).get('latitude', 0.0)
        
        # Render the index template with proper context
        return render_template('index.html', 
                             access_level='central' if station == 'central' else 'station',
                             assigned_latitude=latitude)
    except Exception as e:
        app.logger.error(f"Error in home route: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                return render_template('login.jsx', error='Please provide both username and password')
            
            for station, details in STATIONS.items():
                if details.get('username') == username and details.get('password') == password:
                    session['username'] = username
                    session['station'] = station
                    session['latitude'] = details.get('latitude', 0.0)
                    return redirect(url_for('home'))
            
            return render_template('login.html', error='Invalid credentials')
        
        return render_template('login.html')
    except Exception as e:
        app.logger.error(f"Error in login route: {str(e)}")
        return render_template('error.html', error=str(e))

@app.route('/static/<path:filename>')
@login_required
def serve_static(filename):
    try:
        if 'station' in session:
            station = session['station']
            if station != 'central':
                latitude = STATIONS[station]['latitude']
                if (latitude == 16 and session.get('current_alert_latitude') != 16) or \
                   (latitude != 16 and session.get('current_alert_latitude') == 16):
                    return "Access denied", 403
        
        return send_from_directory('static', filename)
    except Exception as e:
        app.logger.error(f"Error serving static file: {str(e)}")
        return "File not available", 404

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

def send_web_alert(message, latitude):
    alert_data = {
        'message': message,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'latitude': latitude
    }
    socketio.emit('fire_alert', alert_data)

def run_flask_app():
    """Run Flask app in a separate thread"""
    try:
        # Create required directories
        if not os.path.exists('static'):
            os.makedirs('static')
        if not os.path.exists('templates'):
            os.makedirs('templates')
        
        # Run the Flask app
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Error starting Flask app: {str(e)}")

class StyledButton(QPushButton):
    def __init__(self, text, icon=None):
        super().__init__(text)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        if icon:
            self.setIcon(QIcon(icon))

class FireDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initialize_ui()
        self.twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
        self.vimeo_client = vimeo.VimeoClient(
            token=VIMEO_ACCESS_TOKEN,
            key=VIMEO_CLIENT_ID,
            secret=VIMEO_CLIENT_SECRET
        )

    def initialize_ui(self):
        # Window configuration
        self.setWindowTitle("🔥 Smart Fire Detection System")
        self.setGeometry(100, 100, 1000, 700)
        self.center_on_screen()

        # Styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f4f4f4;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
        """)

        # Central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Left side - Camera Feed
        left_layout = QVBoxLayout()
        self.camera_label = QLabel("Camera Feed")
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            border: 2px solid #4CAF50;
            background-color: black;
        """)
        left_layout.addWidget(self.camera_label)
        
        # Progress and Status
        status_layout = QHBoxLayout()
        self.detection_progress = QProgressBar()
        self.detection_progress.setMaximum(100)
        self.detection_progress.setTextVisible(False)
        status_layout.addWidget(self.detection_progress)
        left_layout.addLayout(status_layout)

        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = StyledButton("Start Detection")
        self.stop_button = StyledButton("Stop Detection")
        
        self.start_button.clicked.connect(self.start_detection)
        self.stop_button.clicked.connect(self.stop_detection)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        left_layout.addLayout(button_layout)

        # Right side - Log and Status
        right_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(QLabel("Detection Log"))
        right_layout.addWidget(self.log_text)

        # Add layouts to main layout
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)

        # Set the layout
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Detection variables
        self.detection_active = False
        self.cap = None
        self.model = None

        # Initialize clients
        self.initialize_clients()

    def initialize_clients(self):
        """Initialize Twilio, Vimeo, and Web Alert clients."""
        try:
            # Twilio client
            self.twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

            # Vimeo client
            self.vimeo_client = vimeo.VimeoClient(
                token=VIMEO_ACCESS_TOKEN,
                key=VIMEO_CLIENT_ID,
                secret=VIMEO_CLIENT_SECRET
            )

            # Start Flask web alert server
            self.flask_thread = threading.Thread(target=run_flask_app)
            self.flask_thread.daemon = True
            self.flask_thread.start()

            self.log_message("🌐 Web alert server started", 'success')
        except Exception as e:
            self.log_message(f"❌ Client initialization error: {str(e)}", 'error')

    def center_on_screen(self):
        """Center the window on the screen."""
        frame_geometry = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def log_message(self, message, level='info'):
        """Log messages with different styles."""
        color_map = {
            'info': 'black',
            'warning': 'orange',
            'error': 'red',
            'success': 'green'
        }
        color = color_map.get(level, 'black')
        styled_message = f'<span style="color:{color};">{message}</span>'
        self.log_text.append(styled_message)

        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def get_location(self):
        """Fetch coordinates from IP-based location service."""
        try:
            response = requests.get('https://ipinfo.io/json')
            if response.status_code == 200:
                data = response.json()
                latitude, longitude = data['loc'].split(',')
                return float(latitude), float(longitude)
            else:
                return 37.7749, -122.4194  # Fallback to San Francisco
        except Exception as e:
            self.log_message(f"❌ Location fetch error: {str(e)}", 'error')
            return 37.7749, -122.4194
    def get_relevant_stations(self, latitude):
        """Determine which stations to alert based on location"""
        stations_to_alert = ['central']  # Central station always gets alerts
        
        if abs(latitude - 16.0) < 0.1:  # Close to latitude 16
            stations_to_alert.append('station1')
        else:
            stations_to_alert.append('station2')
            
        return stations_to_alert

    def send_fire_alert(self, location_coordinates):
        try:
            latitude, longitude = location_coordinates
            stations_to_alert = self.get_relevant_stations(latitude)
            
            base_message = f"🔥 Fire detected at Location: {latitude}, {longitude}"
            
            for station in stations_to_alert:
                station_info = STATIONS[station]
                station_specific_message = f"{base_message}\nAlert for: {station.upper()}"
                
                # Send SMS
                self.twilio_client.messages.create(
                    body=station_specific_message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=station_info['phone']
                )
                
                self.log_message(f"📱 Alert sent to {station}", 'success')
            
            # Send web alert
            send_web_alert(base_message, latitude)
            
        except Exception as e:
            self.log_message(f"❌ Alert error: {str(e)}", 'error')
   
    def upload_video(self, video_file_path):
        """Upload video to Vimeo and return video link."""
        try:
            uri = self.vimeo_client.upload(video_file_path)
            video_url = f"https://vimeo.com{uri}"
            self.log_message(f"🎥 Video uploaded to: {video_url}", 'success')
            return video_url
        except Exception as e:
            self.log_message(f"❌ Video upload error: {str(e)}", 'error')
            return None

    def send_video_link_alert(self, video_link):
        """Send SMS alert with video link."""
        try:
            message_body = f"🔥 Fire detection video available at: {video_link}"
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=ALERT_RECIPIENT
            )
            self.log_message(f"📱 Video link alert sent!", 'success')
        except Exception as e:
            self.log_message(f"❌ Video link alert error: {str(e)}", 'error')

    def update_camera_feed(self):
        """Update the camera feed display."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                
                scaled_pixmap = pixmap.scaled(
                    self.camera_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                
                self.camera_label.setPixmap(scaled_pixmap)

    def start_detection(self):
        """Start fire detection process."""
        if not self.detection_active:
            try:
                self.detection_active = True
                self.log_message("🔍 Initializing fire detection system...", 'info')
                
                # Initialize camera
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    self.log_message("❌ Camera access failed. Check camera connection.", 'error')
                    self.detection_active = False
                    return

                # Initialize YOLO model
                self.model = YOLOWorld('fire.pt')
                
                # Camera feed timer
                self.camera_timer = QTimer(self)
                self.camera_timer.timeout.connect(self.update_camera_feed)
                self.camera_timer.start(30)

                # Detection thread
                self.detection_thread = threading.Thread(target=self.run_detection)
                self.detection_thread.start()

                # Update UI
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
            except Exception as e:
                self.log_message(f"❌ Startup error: {str(e)}", 'error')
                self.stop_detection()
    
    def run_detection(self):
        cooldown_time = 30
        fire_detected = False

        while self.detection_active and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.log_message("❌ Frame capture failed", 'error')
                    break

                if not fire_detected:
                    result = self.model.predict(source=frame, imgsz=640, conf=0.9)
                    detections = result[0].boxes

                    if detections is not None:
                        for box in detections:
                            if int(box.cls.item()) == 0:  # Assuming 0 is fire class
                                # Get location and send alerts
                                latitude, longitude = self.get_location()
                                self.send_fire_alert((latitude, longitude))

                                # Record and save video
                                video_path = os.path.join('static', 'fire_detection.mp4')
                                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                                out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 480))

                                start_time = time.time()
                                while time.time() - start_time < 10:
                                    ret, frame = self.cap.read()
                                    if not ret:
                                        break
                                    out.write(frame)
                                out.release()

                                # Upload to Vimeo
                                video_link = self.upload_video(video_path)
                                if video_link:
                                    self.send_video_link_alert(video_link)

                                fire_detected = True
                                break

                if fire_detected:
                    self.log_message(f"⏳ Detection paused for {cooldown_time} seconds", 'info')
                    time.sleep(cooldown_time)
                    fire_detected = False
                    self.log_message("🔄 Detection resumed", 'success')

            except Exception as e:
                self.log_message(f"❌ Detection error: {str(e)}", 'error')
                break
    def stop_detection(self):
        """Stop the detection process."""
        self.detection_active = False
        
        if hasattr(self, 'camera_timer'):
            self.camera_timer.stop()

        if self.cap:
            self.cap.release()
            self.cap = None

        self.camera_label.clear()
        self.camera_label.setText("Camera Feed")

        self.log_message("🛑 Fire detection system stopped", 'info')
        
        # Reset UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        """Handle application closure with confirmation."""
        reply = QMessageBox.question(
            self, 'Exit', 'Are you sure you want to exit?', 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.stop_detection()
            event.accept()
        else:
            event.ignore()

def main():
    try:
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Start PyQt application
        qt_app = QApplication(sys.argv)
        window = FireDetectionApp()
        window.show()
        sys.exit(qt_app.exec_())
    except Exception as e:
        print(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
