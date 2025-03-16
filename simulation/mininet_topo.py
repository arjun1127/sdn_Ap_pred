from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

def create_topology():
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    # Add SDN Controller (External Ryu Controller)
    controller = net.addController('c0', ip="127.0.0.1", port=6633)
    # Add Access Points (APs) as Switches
    ap1 = net.addSwitch('ap1')
    ap2 = net.addSwitch('ap2')
    ap3 = net.addSwitch('ap3')
    ap4 = net.addSwitch('ap4')

    # Add Central Switch
    s1 = net.addSwitch('s1')

    # Connect APs to the central switch
    net.addLink(ap1, s1)
    net.addLink(ap2, s1)
    net.addLink(ap3, s1)
    net.addLink(ap4, s1)

    # Add 16 Vehicles (Hosts), 4 per AP
    for i in range(1, 17):
        host = net.addHost(f'h{i}')
        if i <= 4:
            net.addLink(host, ap1)
        elif i <= 8:
            net.addLink(host, ap2)
        elif i <= 12:
            net.addLink(host, ap3)
        else:
            net.addLink(host, ap4)

    # Start network
    net.build()
    controller.start()
    s1.start([controller])
    ap1.start([controller])
    ap2.start([controller])
    ap3.start([controller])
    ap4.start([controller])

    print("✅ Mininet Network with SDN-Enabled APs is Up! 🚦")
    CLI(net)  # Open Mininet CLI for testing
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')  # Set logging level
    create_topology()
