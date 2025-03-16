import traci
import socket
import json
import time
import csv

SUMO_CMD = ["sumo", "-c", "sumo_config.sumocfg"]  # Start SUMO

def send_to_sdn(ap_id, vehicle_count):
    """Send vehicle count per AP to the SDN controller."""
    data = {"ap_id": ap_id, "traffic_load": vehicle_count}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(data).encode(), ("127.0.0.1", 5001))
    sock.close()

def main():
    traci.start(SUMO_CMD)
    print("SUMO started and connected to TraCI.")

    # Open CSV file to log vehicle data
    with open("vehicle_data.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Vehicle ID", "AP ID", "Speed", "Lane ID", "X", "Y"])  # Header

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()  # Advance SUMO simulation step
            timestamp = traci.simulation.getTime()

            # Count vehicles in each lane (each lane = 1 AP)
            ap_traffic = {"ap1": 0, "ap2": 0, "ap3": 0, "ap4": 0}

            for vehicle_id in traci.vehicle.getIDList():
                lane_id = traci.vehicle.getLaneID(vehicle_id)  # Get lane (AP zone)
                speed = traci.vehicle.getSpeed(vehicle_id)  # Get speed
                x, y = traci.vehicle.getPosition(vehicle_id)  # Get coordinates
                
                # Assign AP ID based on lane
                if lane_id.startswith("road1"):
                    ap_id = "ap1"
                    ap_traffic["ap1"] += 1
                elif lane_id.startswith("road2"):
                    ap_id = "ap2"
                    ap_traffic["ap2"] += 1
                elif lane_id.startswith("road3"):
                    ap_id = "ap3"
                    ap_traffic["ap3"] += 1
                elif lane_id.startswith("road4"):
                    ap_id = "ap4"
                    ap_traffic["ap4"] += 1
                else:
                    ap_id = "unknown"

                # Write data to CSV
                writer.writerow([timestamp, vehicle_id, ap_id, speed, lane_id, x, y])

            # Send traffic data to SDN Controller
            for ap, count in ap_traffic.items():
                send_to_sdn(ap, count)

            time.sleep(1)  # Sync every second

    traci.close()
    print("SUMO simulation finished.")

if __name__ == "__main__":
    main()
