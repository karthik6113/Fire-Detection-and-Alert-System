# Fire-Detection-and-Alert-System
smart-fire-detection/
│
├── main.py                 # Main PyQt5 application
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
│
├── static/                 # Static files for web interface
│   ├── fire.pt             # YOLO model weights
│   └── placeholder.txt     # Placeholder for uploads
│
├── templates/              # HTML templates
│   ├── index.html          # Main dashboard
│   ├── login.html          # Login page
│   └── error.html          # Error page
│
├── config/                 # Configuration files
│   └── credentials.py      # Sensitive credentials (git-ignored)
│
└── scripts/                # Utility scripts
    └── setup.sh            # Setup and installation script

    Prerequisites

Python 3.8+
pip (Python package manager)

Installation

Clone the repository:

bashCopygit clone https://github.com/yourusername/smart-fire-detection.git
cd smart-fire-detection

Create a virtual environment:

bashCopypython3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

Install dependencies:

bashCopypip install -r requirements.txt

Set up credentials:


Create config/credentials.py with the following format:

pythonCopyTWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
VIMEO_CLIENT_ID = 'your_vimeo_client_id'
VIMEO_CLIENT_SECRET = 'your_vimeo_client_secret'
VIMEO_ACCESS_TOKEN = 'your_vimeo_access_token'

Run the application:

bashCopypython main.py
Features

Fire detection using YOLO
Real-time video streaming
SMS and web alerts
Multi-station support
Vimeo video upload

Security Notes

Do not commit credentials.py
Use environment variables in production
Rotate credentials periodically

## requirements.txt
PyQt5==5.15.7
ultralytics==8.0.1
opencv-python==4.7.0.72
numpy==1.22.4
twilio==7.16.3
vimeo==0.5.0
flask==2.1.0
flask-socketio==5.1.1
requests==2.27.1
Copy
## .gitignore
Virtual environment
venv/
*.venv
env/
Python cache files
pycache/
*.py[cod]
*$py.class
Credentials
config/credentials.py
Video and log files
static/*.mp4
*.log
IDE files
.vscode/
.idea/
OS generated files
.DS_Store
Thumbs.db
Copy
## Additional Setup Steps

1. Replace placeholder credentials in `main.py`
2. Obtain a valid `fire.pt` YOLO model weights file
3. Configure Twilio and Vimeo accounts

## Development Recommendations
- Use virtual environments
- Implement proper error handling
- Consider containerization with Docker
- Set up CI/CD pipelines
- Regularly update dependencies
