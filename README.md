

# SDN-LSTM Based Network Congestion Reduction for Autonomous Vehicles/ IOT devices

#  Table of Contents

- [SDN-LSTM Based Network Congestion Reduction for Autonomous Vehicles/IoT Devices](#sdn-lstm-based-network-congestion-reduction-for-autonomous-vehicles-iot-devices)
- [Project Components](#project-components)
  - [1. SDN Controller (Ryu-based)](#1-sdn-controller-ryu-based)
  - [2. Machine Learning Predictor (LSTM)](#2-machine-learning-predictor-lstm)
  - [3. Simulation Environment](#3-simulation-environment)
- [Installation](#installation)
  - [1. System Dependencies (LSTM Setup)](#1-system-dependencies)
  - [2. Ryu and Mininet Setup](#2-ryu-and-mininet-setup)
  - [3. Install Mininet](#3-install-mininet)
  - [4. Activating and Deactivating Environments](#4-activating-and-deactivating-environments)
- [How to Run the Project](#how-to-run-the-project)
  - [Step 1: Run LSTM Prediction Notebook](#step-1-run-lstm-prediction-notebook)
  - [Step 2: Send Predictions to SDN Controller](#step-2-send-predictions-to-sdn-controller)
  - [Step 3: Start Ryu SDN Controller](#step-3-start-ryu-sdn-controller)
  - [Step 4: Run Mininet Simulation](#step-4-run-mininet-simulation)
  - [Step 5: Start SDN Controller to Receive Predictions](#step-5-start-sdn-controller-to-receive-predictions)
- [Repository Clone Instructions](#clone-repo)
- [Results](#results)
- [Core Theory](#core-theory)


This project integrates **Software Defined Networking (SDN)** with **Long Short-Term Memory (LSTM)** neural networks to proactively reduce network congestion in vehicular networks. It predicts traffic patterns at Access Points (APs) using machine learning and reroutes data flows using SDN to the least congested AP.

##  Project Components

### 1. SDN Controller (Ryu-based)
- Receives real-time LSTM predictions over UDP.
- Dynamically reroutes traffic between APs based on predicted congestion.
- Installs and deletes OpenFlow rules accordingly.

### 2. Machine Learning Predictor (LSTM)
- Trained LSTM models to predict:
  - Average latency
  - Bandwidth usage
  - Packet rate
  - Speed, acceleration, and active nodes
- Sends prediction batches every 5 seconds to the Ryu controller.

### 3. Simulation Environment
- **Mininet**: Emulates network topology with switches as APs and hosts as vehicles.
- **SUMO**: Simulates vehicle movement and generates mobility data.
- **Python Scripts**: Extract vehicle and network data for training LSTM models.

---


##  Installation

Follow the steps below to set up the SDN-LSTM Congestion Reduction project on a Ubuntu-based system.

### 1. System Dependencies

Install required packages: this is LSTM part setup , note this should be in root folder

```
sudo apt update
sudo apt install -y git python3 
python3 -m venv sdn_lstm_env
source sdn_lstm_env/bin/activate
pip install --upgrade pip

pip install \
  tensorflow \
  pandas \
  numpy \
  scikit-learn \
  matplotlib \
  seaborn \
  scapy \
  keras

```
## After having setup for LSTM open a new terminal and install/ setup ryu and mininet 
```
# Update and install Python 3.10
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils

# Set python3.10 as default (optional, skip if you want to use system python)
# sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Create and activate a virtual environment for Ryu
python3.10 -m venv ryu_env
source ryu_env/bin/activate

# Upgrade pip and install Ryu dependencies
pip install --upgrade pip
pip install msgpack-python eventlet greenlet netaddr oslo.config tinyrpc webob

# Clone Ryu and install it
git clone https://github.com/osrg/ryu.git
cd ryu
pip install .
```

```
# Test Ryu installation
ryu-manager --version
# should show the version 
```
```
cd ..
```

## Install mininet 

```
sudo apt install -y git make gcc python3-pip openvswitch-switch openvswitch-common \
    openvswitch-test openvswitch-pki openvswitch-ipsec net-tools iputils-ping \
    iproute2 ethtool socat xterm

# Clone Mininet repo
git clone https://github.com/mininet/mininet.git
cd mininet

# Install Mininet using the install script (only core)
sudo util/install.sh -n3
```

```

# Test Mininet installation
sudo mn --test pingall

```
```
cd ..
```

## to activate and decactivate the env 
```
#activate ryu
cd ryu
source ryu_env/bin/activate
```
```
#activate lstm
#make sure to be root folder 
source sdn_lstm_env/bin/activate
```
```
deactivate
```

#  How to Run the Project

Follow these steps **in order** to properly run the full system:

---

## Step 1: Run LSTM Prediction Notebook

1. Open the following Jupyter notebook:

   ```
   ap_node_prediction/model_new (2).ipynb
   ```
2. Click **"Run All"** to generate AP traffic predictions.

---

##  Step 2: Send Predictions to SDN Controller

1. Open this notebook:

   ```
   train_model/sent_predictions.ipynb
   ```
2. Click **"Run All"** to send predictions periodically via UDP to the SDN controller.

---

## Step 3: Start Ryu SDN Controller

1. Open a **new terminal**.
2. Navigate to the Ryu directory and activate the virtual environment:

   ```
   # if lstm env is activated deactivate it
   deactivate
   cd ryu
   source /ryu_env/bin/activate
   cd ..
   ```

---

##  Step 4: Run Mininet Simulation

1. In the same terminal, go to the simulation directory:

   ```
   cd ../simulation
   ```
2. Run the Mininet topology script:

   ```
   sudo python3 topology.py
   ```

---

##  Step 5: Start SDN Controller to Receive Predictions

1. Open **another new terminal**.
2. Run the SDN controller code:

   ```
   cd sdn_controller
   ryu-manager recv_pred.py   # Starts the Ryu controller
   ```

---

# NOTE EVERYTIME WHEN YOU WANT TO RUN LSTM/ MACHINE LEARINING PART OF CODE ACTIVATE sdn_lstm_env
# AND TO START THE CONTROLLER / RUN ANY RYU FILES ACTIVATE ryu_env


## Clone repo
```
git clone https://github.com/your-username/sdn-lstm-vehicular.git
cd sdn-lstm-vehicular
```


# RESULTS 
![image](https://github.com/user-attachments/assets/d655c95a-f219-40f1-b414-10455774229e)

![image](https://github.com/user-attachments/assets/658f14e4-b55b-44ef-9787-125808d01159)

![image](https://github.com/user-attachments/assets/60805a9b-2217-4e0b-a72e-d160a1dc863f)




# Core Theory

This project is built on the convergence of Software Defined Networking (SDN) and Machine Learning (LSTM) to intelligently manage and optimize data flow in vehicular networks.

Traditional vehicular networks suffer from unpredictable congestion due to fluctuating traffic density, mobility patterns, and limited bandwidth at wireless access points (APs). To address this, the project uses Long Short-Term Memory (LSTM) models to forecast key network metrics—such as latency, bandwidth usage, and packet rate—based on real-time mobility and network data.

These predictions are then sent to an SDN controller (Ryu) that dynamically reroutes traffic away from predicted congested APs by updating OpenFlow rules across the network. This approach creates a proactive congestion avoidance mechanism, unlike conventional reactive routing systems.

By integrating:

LSTM’s sequence learning ability for time-series traffic prediction, and

SDN’s programmability and centralized control for real-time traffic management,

the system achieves adaptive and intelligent network behavior, improving throughput, reducing packet loss, and enabling reliable data delivery in high-mobility IoT and autonomous vehicle environments.




