import socket
import json
import torch
import numpy as np
from model import LSTMModel  # Ensure this file exists and contains your LSTM model class

# UDP Server Configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 5000  # Port where APs send data

# Load trained LSTM model
model = LSTMModel()
model.load_state_dict(torch.load("lstm_model.pth"))  # Ensure "lstm_model.pth" exists
model.eval()

def predict_traffic(features):
    """Runs LSTM prediction using network features."""
    input_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)  # Add batch dimension
    output = model(input_tensor)
    return output.item()  # Return predicted congestion level

def receive_data():
    """Receives network statistics from APs and makes LSTM predictions."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    print("📡 Listening for network statistics from APs...")

    while True:
        data, addr = sock.recvfrom(1024)  # Buffer size: 1024 bytes
        ap_stats = json.loads(data.decode())

        # Extract features for LSTM prediction
        features = [
            ap_stats["cpu_usage"], 
            ap_stats["bytes_sent"], 
            ap_stats["bytes_recv"], 
            ap_stats["packets_sent"], 
            ap_stats["packets_recv"],
            ap_stats["sent_bandwidth"],
            ap_stats["recv_bandwidth"]
        ]

        prediction = predict_traffic(features)
        print(f"📊 Predicted Traffic Load for {ap_stats['ap_id']}: {prediction}")

        # Send prediction to SDN Controller (UDP port 5001)
        controller_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        controller_message = json.dumps({
            "ap_id": ap_stats["ap_id"],
            "traffic_load": prediction
        }).encode()
        controller_sock.sendto(controller_message, ("127.0.0.1", 5001))

if __name__ == "__main__":
    receive_data()
