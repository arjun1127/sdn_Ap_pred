import psutil
import socket
import time
import json
import netifaces

# UDP Configuration (Send data to LSTM model)
LSTM_HOST = "127.0.0.1"  # Assuming LSTM model runs locally
LSTM_PORT = 5000         # Port where LSTM model listens

def get_active_interface():
    """Returns the first active network interface (excluding loopback)."""
    interfaces = netifaces.interfaces()
    for iface in interfaces:
        if iface != "lo":
            return iface
    return "eth0"  # Fallback if no active interface found

def get_network_stats(interface):
    """Collects network statistics for the given interface."""
    stats = psutil.net_io_counters(pernic=True).get(interface, None)
    
    if stats:
        return {
            "bytes_sent": stats.bytes_sent,
            "bytes_recv": stats.bytes_recv,
            "packets_sent": stats.packets_sent,
            "packets_recv": stats.packets_recv
        }
    return None

def get_cpu_usage():
    """Returns CPU usage percentage."""
    return psutil.cpu_percent(interval=1)

def get_bandwidth_usage(interface, duration=1):
    """Measures bandwidth usage over a given duration (in seconds)."""
    initial = psutil.net_io_counters(pernic=True).get(interface, None)
    if not initial:
        return None

    time.sleep(duration)
    
    final = psutil.net_io_counters(pernic=True).get(interface, None)
    if not final:
        return None

    sent_bandwidth = (final.bytes_sent - initial.bytes_sent) / duration  # Bytes/sec
    recv_bandwidth = (final.bytes_recv - initial.bytes_recv) / duration  # Bytes/sec

    return {
        "sent_bandwidth": sent_bandwidth,
        "recv_bandwidth": recv_bandwidth
    }

def send_data_to_lstm(ap_id, interface):
    """Collects and sends network statistics to the LSTM predictor."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    while True:
        net_stats = get_network_stats(interface)
        cpu_usage = get_cpu_usage()
        bandwidth = get_bandwidth_usage(interface)

        if net_stats and bandwidth:
            data = {
                "ap_id": ap_id,
                "cpu_usage": cpu_usage,
                "bytes_sent": net_stats["bytes_sent"],
                "bytes_recv": net_stats["bytes_recv"],
                "packets_sent": net_stats["packets_sent"],
                "packets_recv": net_stats["packets_recv"],
                "sent_bandwidth": bandwidth["sent_bandwidth"],
                "recv_bandwidth": bandwidth["recv_bandwidth"]
            }
            
            # Convert to JSON and send via UDP
            message = json.dumps(data).encode()
            sock.sendto(message, (LSTM_HOST, LSTM_PORT))
            
            print(f"[AP {ap_id}] Sent network stats to LSTM model: {data}")

        time.sleep(1)  # Send data every second

if __name__ == "__main__":
    ap_id = input("Enter AP ID (e.g., ap1, ap2): ")
    network_interface = get_active_interface()  # Dynamically detect interface
    print(f"Using network interface: {network_interface}")
    send_data_to_lstm(ap_id, network_interface)
