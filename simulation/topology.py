from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from functools import partial

class MultiAPConfigurableTopo(Topo):
    def build(self, aps=10, nodes_per_ap=1):
        for ap_id in range(1, aps + 1):
            ap_switch = self.addSwitch(f'ap{ap_id}', dpid=str(ap_id).zfill(16))
            for node_id in range(1, nodes_per_ap + 1):
                host_id = (ap_id - 1) * nodes_per_ap + node_id
                ip_addr = f'10.0.{ap_id}.{node_id}'
                host = self.addHost(f'h{host_id}', ip=ip_addr)
                self.addLink(host, ap_switch)
                print(f"Connected host h{host_id} (IP: {ip_addr}) to AP ap{ap_id}")

if __name__ == '__main__':
    # 🔁 CONFIGURATION: Set this value to 1 for testing, 50 for full deployment
    nodes_per_ap = 1  # change to 50 for full scale
    aps = 10

    topo = MultiAPConfigurableTopo(aps=aps, nodes_per_ap=nodes_per_ap)
    
    net = Mininet(
        topo=topo,
        controller=None,
        switch=partial(OVSSwitch, protocols='OpenFlow13'),
        link=TCLink
    )

    # Connect to remote Ryu controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    net.start()
    print(f"Network with {aps} APs and {nodes_per_ap} nodes per AP is up. Use CLI to test.")
    CLI(net)
    net.stop()
