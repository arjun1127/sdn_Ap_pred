import pandas as pd

# Load both CSV files
network_df = pd.read_csv("network1_stats.csv")
vehicle_df = pd.read_csv("vehicle_predictions.csv")

# Merge based on the 'timestamp' column (ensuring float format)
network_df["timestamp"] = network_df["timestamp"].astype(float)
vehicle_df["timestamp"] = vehicle_df["timestamp"].astype(float)

# Merge using an "inner join" (only matching timestamps)
merged_df = pd.merge(network_df, vehicle_df, on="timestamp", how="inner")

# Save to new CSV
merged_df.to_csv("merged_data.csv", index=False)

print("✅ Merged CSV saved as 'merged_data.csv'")
