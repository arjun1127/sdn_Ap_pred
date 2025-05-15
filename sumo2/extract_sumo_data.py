import traci
import time

# Define SUMO command
sumo_cmd = ["sumo-gui", "-c", "highway.sumocfg", "--remote-port", "5000"]

try:
    # Start SUMO process
    traci.start(sumo_cmd)
    print("✅ Connected to SUMO-GUI!")

    # Wait a bit to ensure SUMO starts
    time.sleep(2)

    # Main simulation loop
    step = 0
    while traci.simulation.getMinExpectedNumber() > 0:
        print(f"🚗 Simulation Step: {step}")
        
        # Advance the simulation
        traci.simulationStep()

        # Extract vehicle data
        vehicle_ids = traci.vehicle.getIDList()
        print(f"Active Vehicles: {len(vehicle_ids)}")

        for vid in vehicle_ids:
            speed = traci.vehicle.getSpeed(vid)
            position = traci.vehicle.getPosition(vid)
            print(f"Vehicle {vid}: Speed = {speed:.2f} m/s, Position = {position}")

        step += 1
        time.sleep(0.5)  # Slow down simulation steps

except traci.exceptions.FatalTraCIError as e:
    print(f"❌ TraCI Connection Error: {e}")

finally:
    traci.close()
    print("🔻 Simulation Ended. Connection closed.")
