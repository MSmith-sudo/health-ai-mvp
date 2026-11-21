import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import requests 

BASE = Path(__file__).parent
BACKUP = BASE / "backups"
LOGS = BASE / "logs"

BACKUP.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS / f"refresh_{timestamp}.log"

def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def run(command):
    log(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    log(result.stdout)
    if result.stderr:
        log("ERROR:")
        log(result.stderr)

    if result.returncode != 0:
        raise Exception(f"Command failed: {command}")

def backup_file(filename):
    src = BASE / filename
    if src.exists():
        shutil.copy(src, BACKUP / f"{timestamp}_{filename}")

def main():
    log("=== START REFRESH ===")

    backup_file("raw_providers.json")
    backup_file("clean_providers.json")
    backup_file("medicos.db")

    try:
        run("python scrape_directory.py")
        run("python normalize_data.py")

        # ✅ THIS IS THE KEY PART
        try:
            response = requests.post("http://127.0.0.1:8000/admin/reload", timeout=5)
            log(f"Reload API response: {response.status_code}")
        except Exception as e:
            log(f"Reload API failed: {str(e)}")

        log("SUCCESS: Provider data refreshed.")

    except Exception as e:
        log(f"FAILED: {str(e)}")

    log("=== END REFRESH ===")

if __name__ == "__main__":
    main()