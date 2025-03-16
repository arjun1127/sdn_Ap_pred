import subprocess

AP_ID = "ap2"  # Change this for ap2, ap3, ap4 accordingly

def start_monitoring():
    """Start AP monitoring script to collect and send network statistics."""
    print(f"Starting network monitoring for {AP_ID}...")
    subprocess.Popen(["python3", "ap_monitor.py"], stdin=subprocess.PIPE)
    
if __name__ == "__main__":
    start_monitoring()