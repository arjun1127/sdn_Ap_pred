from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4
import json
import socket
import threading
import csv
from ryu.lib import hub
import time
import os

class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.ap_predictions = {}  # Store LSTM predictions
        self.vehicle_data = {}  # Store latest vehicle data

        self.listen_for_predictions()  # UDP listener for LSTM predictions
        self.listen_for_vehicle_data()  # UDP listener for SUMO vehicle data

        self.datapaths = {}  # Store switch datapaths for monitoring
        self.monitor_thread = hub.spawn(self._monitor)  # Start traffic monitoring

        self.network_csv = "network_stats.csv"
        self.vehicle_csv = "vehicle_data.csv"
        self.initialize_csvs()  # Ensure CSV files have headers

    def initialize_csvs(self):
        """Create CSV files with column headers if they don't exist."""
        if not os.path.exists(self.network_csv):
            with open(self.network_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "switch_id", "port_no", "rx_packets",
                    "tx_packets", "rx_bytes", "tx_bytes",
                    "rx_dropped", "tx_dropped", "traffic_load"
                ])

        if not os.path.exists(self.vehicle_csv):
            with open(self.vehicle_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "vehicle_id", "ap_id", "speed", "x", "y", "lane"])

    def listen_for_predictions(self):
        """Start a separate thread to receive LSTM predictions asynchronously."""
        self.prediction_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.prediction_socket.bind(("0.0.0.0", 5001))
        self.logger.info("Listening for LSTM predictions on UDP port 5001...")

        thread = threading.Thread(target=self.monitor_predictions, daemon=True)
        thread.start()

    def listen_for_vehicle_data(self):
        """Start a separate thread to receive vehicle data asynchronously from SUMO."""
        self.vehicle_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.vehicle_socket.bind(("0.0.0.0", 5002))
        self.logger.info("Listening for vehicle data on UDP port 5002...")

        thread = threading.Thread(target=self.monitor_vehicle_data, daemon=True)
        thread.start()

    def monitor_predictions(self):
        """Receives LSTM predictions and updates AP traffic load."""
        while True:
            try:
                data, addr = self.prediction_socket.recvfrom(1024)
                prediction = json.loads(data.decode('utf-8'))
                ap_id = prediction.get("ap_id")
                traffic_load = prediction.get("traffic_load")

                if ap_id and traffic_load is not None:
                    self.ap_predictions[ap_id] = traffic_load
                    self.logger.info(f"Received prediction from {ap_id}: {traffic_load}")
                else:
                    self.logger.warning(f"Invalid prediction data received: {prediction}")

            except Exception as e:
                self.logger.error(f"Error receiving prediction: {e}")

    def monitor_vehicle_data(self):
        """Receives vehicle data from SUMO and logs it."""
        while True:
            try:
                data, addr = self.vehicle_socket.recvfrom(1024)
                vehicle_info = json.loads(data.decode('utf-8'))
                vehicle_id = vehicle_info.get("vehicle_id")
                ap_id = vehicle_info.get("ap_id")
                speed = vehicle_info.get("speed")
                x = vehicle_info.get("x")
                y = vehicle_info.get("y")
                lane = vehicle_info.get("lane")

                if vehicle_id and ap_id:
                    self.vehicle_data[vehicle_id] = vehicle_info
                    self.logger.info(f"Received vehicle data: {vehicle_info}")

                    # Save to CSV
                    with open(self.vehicle_csv, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([time.time(), vehicle_id, ap_id, speed, x, y, lane])

            except Exception as e:
                self.logger.error(f"Error receiving vehicle data: {e}")

    @set_ev_cls(ofp_event.EventOFPStateChange, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def _state_change_handler(self, ev):
        """Register and unregister switches dynamically."""
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[datapath.id] = datapath
        elif ev.state == CONFIG_DISPATCHER and datapath.id in self.datapaths:
            del self.datapaths[datapath.id]

    def _monitor(self):
        """Continuously request port stats from switches and save data."""
        while True:
            for datapath in self.datapaths.values():
                self._request_stats(datapath)
            hub.sleep(5)  # Collect stats every 5 seconds

    def _request_stats(self, datapath):
        """Request port statistics from a switch."""
        self.logger.info(f"Requesting stats from switch {datapath.id}")
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        """Handle port stats replies and log to a CSV file."""
        body = ev.msg.body
        timestamp = time.time()

        try:
            with open(self.network_csv, "a", newline="") as f:
                writer = csv.writer(f)
                for stat in body:
                    ap_id = f"ap{ev.msg.datapath.id}"  # Ensure AP ID matches Mininet
                    traffic_load = self.ap_predictions.get(ap_id, 0)

                    writer.writerow([
                        timestamp, ev.msg.datapath.id, stat.port_no, stat.rx_packets,
                        stat.tx_packets, stat.rx_bytes, stat.tx_bytes,
                        stat.rx_dropped, stat.tx_dropped, traffic_load
                    ])

                    self.logger.info(
                        f"[{timestamp}] Switch {ev.msg.datapath.id} Port {stat.port_no}: "
                        f"RX {stat.rx_bytes} TX {stat.tx_bytes} | Predicted Load: {traffic_load}"
                    )
        except Exception as e:
            self.logger.error(f"Error writing to network_stats.csv: {e}")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handles switch connection and installs default flow rules."""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        actions = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=1, instructions=inst)
        datapath.send_msg(mod)

        self.logger.info(f"Installed default forwarding rule on Switch {datapath.id}")
