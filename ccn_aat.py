from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import RemoteController
from mininet.cli import CLI

class ComplexCampusTopo(Topo):
    def build(self):
        # Core switch
        core = self.addSwitch('s1')

        # Distribution switches
        dist1 = self.addSwitch('s2')
        dist2 = self.addSwitch('s3')

        # Access layer switches
        access1 = self.addSwitch('s4')
        access2 = self.addSwitch('s5')
        access3 = self.addSwitch('s6')
        access4 = self.addSwitch('s7')

        # Hosts
        hosts = []
        for i in range(1, 9):
            host = self.addHost(f'h{i}', ip=f'10.0.0.{i}')
            hosts.append(host)

        # Links from core to distribution (redundant)
        self.addLink(core, dist1)
        self.addLink(core, dist2)

        # Links from distribution to access (redundant)
        self.addLink(dist1, access1)
        self.addLink(dist1, access2)
        self.addLink(dist2, access3)
        self.addLink(dist2, access4)

        # Redundant cross-links
        self.addLink(dist1, access3)
        self.addLink(dist2, access1)

        # Hosts to access switches
        self.addLink(access1, hosts[0])
        self.addLink(access1, hosts[1])
        self.addLink(access2, hosts[2])
        self.addLink(access2, hosts[3])
        self.addLink(access3, hosts[4])
        self.addLink(access3, hosts[5])
        self.addLink(access4, hosts[6])
        self.addLink(access4, hosts[7])

if __name__ == '__main__':
    topo = ComplexCampusTopo()
    net = Mininet(topo=topo, controller=RemoteController)
    net.start()
    CLI(net)
    net.stop()
