#!/usr/bin/env python3
"""
CyberNewsHub Startup Script
Starts both backend and frontend servers
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# Store process references
processes = []
log_files = []

def cleanup(signum=None, frame=None):
    """Cleanup function to kill all child processes"""
    print("\n\nShutting down servers...")
    for process in processes:
        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        except:
            try:
                process.kill()
            except:
                pass
    # Close log files
    for log_file in log_files:
        try:
            log_file.close()
        except:
            pass
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def check_setup():
    """Check if setup is complete"""
    backend_venv = Path("backend/venv")
    frontend_node_modules = Path("frontend/node_modules")
    
    if not backend_venv.exists() or not frontend_node_modules.exists():
        print("Setup not complete. Running setup first...")
        print("   Run: ./setup.sh")
        return False
    return True

def start_backend():
    """Start the Flask backend server"""
    print("Starting backend server...")
    
    # Determine the Python executable in venv
    if sys.platform == "win32":
        python_exe = "backend/venv/Scripts/python.exe"
    else:
        python_exe = "backend/venv/bin/python"
    
    if not os.path.exists(python_exe):
        python_exe = "python3"  # Fallback
    
    try:
        # Write backend output to a log file
        log_file = open("backend.log", "w")
        log_files.append(log_file)
        process = subprocess.Popen(
            [python_exe, "backend/app.py"],
            cwd=os.getcwd(),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(process)
        print("Backend starting (check logs for actual port)")
        print("   (Logs: backend.log)")
        return process
    except Exception as e:
        print(f"Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the React frontend server"""
    print("Starting frontend server...")
    
    try:
        if sys.platform == "win32":
            npm_cmd = "npm.cmd"
        else:
            npm_cmd = "npm"
        
        # Write frontend output to a log file
        log_file = open("frontend.log", "w")
        log_files.append(log_file)
        process = subprocess.Popen(
            [npm_cmd, "start"],
            cwd="frontend",
            stdout=log_file,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        processes.append(process)
        print("Frontend starting on http://localhost:3000")
        print("   (Logs: frontend.log)")
        print("   (This may take 30-60 seconds to compile)")
        return process
    except Exception as e:
        print(f"Failed to start frontend: {e}")
        return None

def main():
    print("CyberNewsHub")
    print("=" * 50)
    print()
    
    if not check_setup():
        sys.exit(1)
    
    # Start backend
    backend = start_backend()
    if not backend:
        cleanup()
        sys.exit(1)
    
    # Wait a bit for backend to initialize
    time.sleep(3)
    
    # Start frontend
    frontend = start_frontend()
    if not frontend:
        cleanup()
        sys.exit(1)
    
    print()
    print("CyberNewsHub is running!")
    print()
    print("Frontend: http://localhost:3000")
    print("Backend API: http://localhost:8000 (or check backend.log)")
    print()
    print("View logs:")
    print("   Backend:  tail -f backend.log")
    print("   Frontend: tail -f frontend.log")
    print()
    print("Press Ctrl+C to stop both servers")
    print("=" * 50)
    print()
    
    # Monitor processes
    try:
        while True:
            # Check if processes are still alive
            if backend.poll() is not None:
                print("Backend process died!")
                cleanup()
            
            if frontend.poll() is not None:
                print("Frontend process died!")
                cleanup()
            
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()

