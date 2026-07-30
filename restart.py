#!/usr/bin/env python3
import subprocess
import signal
import os
import time
import sys

def kill_flask():
    """Kill any Flask process running on port 5001"""
    try:
        result = subprocess.run(
            ["lsof", "-ti", ":5001"],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        pids = [p for p in pids if p]  # Filter empty strings

        if pids:
            print(f"Found Flask process(es) on port 5001: {pids}")
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"Killed process {pid}")
                except ProcessLookupError:
                    print(f"Process {pid} already terminated")
            time.sleep(1)
        else:
            print("No Flask process found on port 5001")
    except FileNotFoundError:
        print("lsof not found, trying alternative method...")
        subprocess.run(["pkill", "-f", "flask|python run.py"], capture_output=True)

def run_flask():
    """Start the Flask app"""
    print("Starting Flask app...")
    subprocess.run([sys.executable, "run.py"])

if __name__ == "__main__":
    kill_flask()
    time.sleep(1)
    run_flask()
