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

class SDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SDNController, self).__init__(*args, **kwargs)
        self.ap_predictions = {}  # Store LSTM predictions from each AP
        self.listen_for_predictions()
        self.datapaths = {}  # Store switch datapaths for traffic monitoring
        self.monitor_thread = hub.spawn(self._monitor)  # Start traffic monitoring

    def listen_for_predictions(self):
        """Starts a separate thread to receive LSTM predictions asynchronously."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(("0.0.0.0", 5001))
        self.logger.info("Listening for LSTM predictions on UDP port 5001...")

        thread = threading.Thread(target=self.monitor_predictions, daemon=True)
        thread.start()

    def monitor_predictions(self):
        """Receives LSTM predictions and updates AP traffic load."""
        while True:
            try:
                data, addr = self.server_socket.recvfrom(1024)
                prediction = json.loads(data.decode('utf-8'))
                ap_id = prediction["ap_id"]
                traffic_load = prediction["traffic_load"]
                self.ap_predictions[ap_id] = traffic_load

                self.logger.info(f"Received prediction from {ap_id}: {traffic_load}")

                # Append vehicle predictions to CSV
                with open("vehicle_predictions.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([time.time(), ap_id, traffic_load])

            except Exception as e:
                self.logger.error(f"Error receiving prediction: {e}")

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
        """Handle port stats replies and log to a CSV file with LSTM predictions."""
        body = ev.msg.body
        timestamp = time.time()

        with open("network_stats.csv", "a", newline="") as f:
            writer = csv.writer(f)
            for stat in body:
                ap_id = f"ap{ev.msg.datapath.id}"  # Ensure AP ID matches Mininet
                traffic_load = self.ap_predictions.get(ap_id, 0)  # Get latest LSTM prediction
                
                writer.writerow([timestamp, ev.msg.datapath.id, stat.port_no, stat.rx_packets,
                                 stat.tx_packets, stat.rx_bytes, stat.tx_bytes,
                                 stat.rx_dropped, stat.tx_dropped, traffic_load])

                self.logger.info(f"[{timestamp}] Switch {ev.msg.datapath.id} Port {stat.port_no}: RX {stat.rx_bytes} TX {stat.tx_bytes} | Predicted Load: {traffic_load}")

    def get_ap_port(self, datapath, ap_id):
        """Return the correct output port for the given AP ID."""
        # Map APs to OpenFlow switch ports
        ap_port_map = {"ap1": 1, "ap2": 2, "ap3": 3, "ap4": 4}
        
        if ap_id in ap_port_map:
            return ap_port_map[ap_id]  # Return the correct port number for the AP
        else:
            return datapath.ofproto.OFPP_FLOOD  # Default to flooding if AP not found

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Adds flow rules dynamically based on congestion data with timeout."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, 
            instructions=inst, idle_timeout=30, hard_timeout=30
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handles incoming packets and applies flow rules based on congestion and vehicle data."""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ip = pkt.get_protocol(ipv4.ipv4)

        if eth is None or ip is None:
            return

        src = eth.src
        dst = eth.dst

        # Select the least congested AP based on LSTM predictions
        least_congested_ap = min(self.ap_predictions, key=lambda k: self.ap_predictions.get(k, float("inf")), default=None)

        if least_congested_ap:
            self.logger.info(f"Redirecting traffic to {least_congested_ap}")
            output_port = self.get_ap_port(datapath, least_congested_ap)  # Correct port mapping
            actions = [parser.OFPActionOutput(output_port)]
        else:
            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        match = parser.OFPMatch(eth_src=src, eth_dst=dst)
        self.add_flow(datapath, 1, match, actions)

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=msg.data)
        datapath.send_msg(out)


# Receives LSTM Predictions via UDP (port 5001) from APs.
# Stores Traffic Load per AP in self.ap_predictions.
# Handles Incoming Packets and redirects traffic to the least congested AP.
# Installs Dynamic Flow Rules in OpenFlow switches to optimize vehicle communication.
#  Receive LSTM predictions from APs (e.g., traffic load, latency, etc.)
#  Analyze network congestion based on predicted values
# Modify flow tables dynamically to optimize vehicle data routing
# Ensure minimal load on the SDN controller by using only LSTM-based decisions

#SDN Controller's Role:

# Centralized Intelligence: It makes decisions (like redirecting traffic based on LSTM predictions) and then installs flow rules into the data plane devices (the switches).
# Policy Enforcement: It controls how traffic is routed and managed across the network, similar to a router’s function, but it doesn't physically forward the packets itself.

# Data Plane Devices:

# Switches/APs: The actual packet forwarding is done by the switches (configured as APs and the central switch) in your Mininet topology.
# Routing Decisions: The controller's decisions result in the installation of flow rules in these switches, which then handle the packet forwarding according to those rules.



# Port Statistics Collection

# The controller requests port stats every 5 seconds (self._monitor()).
# Received stats are logged to a CSV file (network_stats.csv).
# Retains LSTM Prediction Handling

# The controller still listens for LSTM predictions and uses them for traffic redirection.
# Efficient Traffic Monitoring

# Uses Ryu's hub.spawn() to run monitoring in the background.

#data getting =>timestamp,switch_id,port_no,rx_packets,tx_packets,rx_bytes,tx_bytes,rx_dropped,tx_dropped
