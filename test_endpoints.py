import subprocess
import time
import requests

print("Starting Uvicorn...")
proc = subprocess.Popen(
    ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(5) # wait for startup
try:
    health = requests.get("http://127.0.0.1:8000/health")
    print("Health Status:", health.status_code)
    print("Health Data:", health.json())

    # Note the double prefix
    students = requests.get("http://127.0.0.1:8000/api/v1/students/students?skip=0&limit=2")
    print("Students Status:", students.status_code)
    data = students.json()
    print("Students length:", len(data.get("students", [])))
    if data.get("students"):
        print("Sample student id:", data.get("students")[0].get("id"))
    else:
        print("No students found in array")
except Exception as e:
    print(f"Error connecting: {e}")
finally:
    proc.terminate()
    stdout, stderr = proc.communicate()
    print("Server output excerpt:", stderr.decode()[-500:])

