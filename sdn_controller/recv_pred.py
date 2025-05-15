# my_controller.py
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
from ryu.lib import hub

import socket
import json

class MLSDNController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MLSDNController, self).__init__(*args, **kwargs)
        self.datapaths = {}         # {dpid: datapath}
        self.predictions = {}       # {ap_id: prediction}
        self.udp_thread = hub.spawn(self.udp_listener)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self.logger.info("Registered switch (AP) ID: %s", dp.id)

        # Install default flow to send unmatched packets to controller
        match = dp.ofproto_parser.OFPMatch()
        actions = [dp.ofproto_parser.OFPActionOutput(
            dp.ofproto.OFPP_CONTROLLER, dp.ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, match, actions)

    def add_flow(self, dp, priority, match, actions, idle_timeout=10, hard_timeout=30):
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=dp,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        )
        dp.send_msg(mod)
        self.logger.info("Flow added on switch %s with timeouts", dp.id)


    def udp_listener(self):
        udp_port = 9999
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', udp_port))
        self.logger.info("Listening for predictions on UDP %d", udp_port)

        while True:
            data, addr = sock.recvfrom(4096)
            try:
                msg = json.loads(data.decode())

                self.logger.info("Raw message: %s", msg)  # Add this line for debugging

                if msg.get("type") == "batch":
                    self.logger.info("Received batch prediction")
                    self.process_batch(msg["data"])
                else:
                    #self.logger.info("Received single prediction")
                    self.handle_prediction(msg)

            except Exception as e:
                self.logger.error("Error parsing prediction: %s", e)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        src_mac = eth.src

        # Store the mapping
        if dpid not in self.port_ap_map:
            self.port_ap_map[dpid] = {}
        if dpid not in self.ap_port_map:
            self.ap_port_map[dpid] = {}

        self.port_ap_map[dpid][in_port] = src_mac
        self.ap_port_map[dpid][src_mac] = in_port

        self.logger.debug("Learned AP %s is on port %d of switch %d", src_mac, in_port, dpid)


    def process_batch(self, batch_data):
        self.logger.info("Received batch data: %s", batch_data)
        self.predictions.clear()

        for p in batch_data:
            self.predictions[p["ap_id"]] = p

        # Choose least congested AP (lowest latency + packet_rate)
        def congestion_score(p):
            return p["predicted_features"]["avg_packet_rate"] + \
                p["predicted_features"]["avg_latency"] + \
                0.5 * p["predicted_features"]["bandwidth_usage"] - \
                0.2 * p["predicted_features"]["speed"] + \
                0.1 * p["predicted_features"]["acceleration"] + \
                0.3 * p["predicted_features"]["active_nodes"]

        best_ap = min(batch_data, key=congestion_score)
        best_ap_id = best_ap["ap_id"]

        self.logger.info("Least congested AP: %d (score: %.2f)", best_ap_id, congestion_score(best_ap))

        # Reroute high-load APs to best AP
        for ap_id, pred in self.predictions.items():
            if pred["predicted_features"]["avg_packet_rate"] > 0.300:
                self.logger.info("AP %d is congested rerouting...",
                                ap_id)
                self.reroute_ap_traffic(from_ap=ap_id, to_ap=best_ap_id)
    
    def delete_flows(self, dp, match):
        parser = dp.ofproto_parser
        ofproto = dp.ofproto

        mod = parser.OFPFlowMod(
            datapath=dp,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            match=match
        )
        dp.send_msg(mod)
        self.logger.info("Deleted matching old flows on switch %s", dp.id)


#reroute_ap_traffic
    def reroute_ap_traffic(self, from_ap, to_ap):
        if from_ap == to_ap:
            self.logger.info("Skipping reroute: from_ap and to_ap are the same (%d)", from_ap)
            return

        if from_ap not in self.datapaths or to_ap not in self.datapaths:
            self.logger.warning("Datapath missing: from_ap %d or to_ap %d not found", from_ap, to_ap)
            return

        from_dp = self.datapaths[from_ap]
        parser = from_dp.ofproto_parser

        # Example assumption: from_ap's uplink is on port 1, to_ap reachable via port 2
        in_port = 1   # Update if dynamic
        out_port = 2  # Update if dynamic

        match = parser.OFPMatch(in_port=in_port)
        actions = [parser.OFPActionOutput(out_port)]

        # Delete previous flows with same match
        self.delete_flows(from_dp, match)

        # Install new rerouting flow with timeout
        self.add_flow(from_dp, 100, match, actions, idle_timeout=15, hard_timeout=60)

        self.logger.info("Installed reroute flow on AP %d: match in_port %d → output to port %d (AP %d)",
                        from_ap, in_port, out_port, to_ap)
    

    def handle_prediction(self, msg):
            node_id = msg["node_id"]
            predicted_ap = msg["predicted_ap"]

            # Store prediction (optional, for later use or inspection)
            if not hasattr(self, "node_ap_predictions"):
                self.node_ap_predictions = {}

            self.node_ap_predictions[node_id] = predicted_ap

            self.logger.info(f"[Prediction] Node {node_id} → Predicted AP {predicted_ap}")

            # Check if the predicted AP exists
            if predicted_ap not in self.datapaths:
                self.logger.warning(f"Predicted AP {predicted_ap} not found in registered datapaths.")
                return

            # Optionally install a flow for that AP
            self.install_special_flow(predicted_ap)  

    
    def install_special_flow(self, predicted_ap):
        dp = self.datapaths[predicted_ap]
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        # Define a special match, e.g., match packets from certain node_id or type
        match = parser.OFPMatch()  # Modify this match as needed

        # Define the action (e.g., special forwarding or modifying packets)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]

        # Install the special flow rule with high priority (e.g., priority 100)
        self.add_flow(dp, priority=100, match=match, actions=actions)

        self.logger.info(f"Installed special flow rule on AP {predicted_ap}")

