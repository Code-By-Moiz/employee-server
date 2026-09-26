import os
import time
import datetime
import requests
from PIL import ImageGrab
import platform

# Active Window Title Identifier for Windows/Mac
def get_active_window_title():
    try:
        if platform.system() == "Windows":
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        else:
            return "Non-Windows OS"
    except Exception:
        return "Unknown"

def capture_and_send(server_url, employee_id):
    try:
        # 1. Capture Screen
        screenshot = ImageGrab.grab()
        temp_filename = f"temp_{employee_id}.jpeg"
        screenshot.save(temp_filename, "JPEG", quality=50)

        # 2. Get Active Window Title
        active_window = get_active_window_title()

        # 3. Post to API
        files = {'image': open(temp_filename, 'rb')}
        payload = {
            'employee_id': employee_id,
            'active_window': active_window,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        response = requests.post(f"{server_url}/api/upload-screenshot", files=files, data=payload, timeout=10)
        files['image'].close()

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        return response.status_code == 200
    except Exception as e:
        print(f"[Tracker Error]: {e}")
        return False