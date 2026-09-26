import os
import json
import shutil
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Employee Monitoring Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_STORAGE = "storage"
os.makedirs(BASE_STORAGE, exist_ok=True)
app.mount("/storage", StaticFiles(directory=BASE_STORAGE), name="storage")

PRODUCTIVE_KEYWORDS = ["code", "excel", "word", "figma", "chrome", "vscode", "slack", "teams", "canva"]

@app.post("/api/upload")
async def upload_data(
    employee_name: str = Form(...),
    active_window: str = Form(...),
    status: Optional[str] = Form("Active Working"),
    work_seconds: Optional[int] = Form(0),
    break_seconds: Optional[int] = Form(0),
    is_idle: Optional[bool] = Form(False),
    screenshot: Optional[UploadFile] = File(None)
):
    today_date = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H-%M-%S")
    time_formatted = datetime.now().strftime("%I:%M:%S %p")

    # Folder Structure: storage/Employee_[name]/[date]/
    emp_dir = os.path.join(BASE_STORAGE, f"Employee_{employee_name}", today_date)
    shots_dir = os.path.join(emp_dir, "screenshots")
    breaks_dir = os.path.join(emp_dir, "breaks")
    
    os.makedirs(shots_dir, exist_ok=True)
    os.makedirs(breaks_dir, exist_ok=True)

    file_name = "None"
    if screenshot:
        file_name = f"{time_str}.jpg"
        file_path = os.path.join(shots_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(screenshot.file, buffer)

    # Log in breaks folder
    break_log_file = os.path.join(breaks_dir, "day_summary_log.txt")
    with open(break_log_file, "a", encoding="utf-8") as bf:
        bf.write(f"[{time_formatted}] Status: {status} | Window: {active_window} | WorkSecs: {work_seconds} | BreakSecs: {break_seconds}\n")

    # Save Live Status
    emp_path = os.path.join(BASE_STORAGE, f"Employee_{employee_name}")
    with open(os.path.join(emp_path, "current_status.json"), "w", encoding="utf-8") as sf:
        json.dump({"status": status, "last_active": time_formatted, "window": active_window}, sf)

    return {"status": "success", "message": "Data recorded"}

@app.get("/api/employees")
def get_employees():
    if not os.path.exists(BASE_STORAGE):
        return []
    return sorted([d.replace("Employee_", "") for d in os.listdir(BASE_STORAGE) if d.startswith("Employee_")])

@app.get("/api/employees/{employee_name}/dates")
def get_employee_dates(employee_name: str):
    emp_path = os.path.join(BASE_STORAGE, f"Employee_{employee_name}")
    if not os.path.exists(emp_path):
        raise HTTPException(status_code=404, detail="Employee not found")
    dates = [d for d in os.listdir(emp_path) if os.path.isdir(os.path.join(emp_path, d))]
    return sorted(dates, reverse=True)

@app.get("/api/data/{employee_name}/{date}")
def get_day_details(employee_name: str, date: str):
    day_dir = os.path.join(BASE_STORAGE, f"Employee_{employee_name}", date)
    shots_dir = os.path.join(day_dir, "screenshots")
    breaks_dir = os.path.join(day_dir, "breaks")

    # Live Status
    emp_path = os.path.join(BASE_STORAGE, f"Employee_{employee_name}")
    status_file = os.path.join(emp_path, "current_status.json")
    live_status = "Inactive"
    if os.path.exists(status_file):
        with open(status_file, "r") as sf:
            live_status = json.load(sf).get("status", "Inactive")

    # Load Screenshots
    screenshots = []
    if os.path.exists(shots_dir):
        for img in sorted(os.listdir(shots_dir), reverse=True):
            screenshots.append({
                "time": img.replace(".jpg", "").replace("-", ":"),
                "url": f"/storage/Employee_{employee_name}/{date}/screenshots/{img}"
            })

    # Read Break Folder Logs
    break_logs = []
    total_work_secs = 0
    total_break_secs = 0
    clock_out_count = 0
    idle_count = 0

    break_log_file = os.path.join(breaks_dir, "day_summary_log.txt")
    if os.path.exists(break_log_file):
        with open(break_log_file, "r", encoding="utf-8") as bf:
            lines = bf.readlines()
            break_logs = lines
            for line in lines:
                if "WorkSecs:" in line and "BreakSecs:" in line:
                    parts = line.split("|")
                    for p in parts:
                        if "WorkSecs:" in p:
                            total_work_secs = max(total_work_secs, int(p.split(":")[1].strip()))
                        if "BreakSecs:" in p:
                            total_break_secs = max(total_break_secs, int(p.split(":")[1].strip()))
                if "Clocked Out" in line or "Clock Out" in line:
                    clock_out_count += 1
                if "Idle" in line:
                    idle_count += 1

    # Shift Hours Target Logic
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    is_saturday = date_obj.weekday() == 5
    target_hours = 5 if is_saturday else 9
    target_secs = target_hours * 3600

    work_progress = min(100, round((total_work_secs / target_secs) * 100, 1))
    break_progress = min(100, round((total_break_secs / (2 * 3600)) * 100, 1))

    return {
        "employee_name": employee_name,
        "date": date,
        "live_status": live_status,
        "shift_schedule": "4:00 PM - 9:00 PM" if is_saturday else "4:00 PM - 1:00 AM",
        "work_hours": f"{total_work_secs // 3600}h {(total_work_secs % 3600) // 60}m",
        "break_hours": f"{total_break_secs // 3600}h {(total_break_secs % 3600) // 60}m",
        "work_progress": work_progress,
        "break_progress": break_progress,
        "clock_out_count": clock_out_count,
        "idle_count": idle_count,
        "break_folder_logs": break_logs,
        "screenshots": screenshots
    }