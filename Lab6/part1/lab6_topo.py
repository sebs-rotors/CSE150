#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController

class MyTopology(Topo):
  def __init__(self):
    Topo.__init__(self)

    # laptop1 = self.addHost('Laptop1', ip='200.20.2.8/24',defaultRoute="Laptop1-eth1")

    # switch1 = self.addSwitch('s1')

    # self.addLink(laptop1, switch1, port1=1, port2=2)
    #Switches and links
    coreSwitch = self.addSwitch("s1")
    facultySwitch = self.addSwitch("s2")
    studentSwitch = self.addSwitch("s3")
    itSwitch = self.addSwitch("s4")
    dataCenterSwitch = self.addSwitch("s5")
    self.addLink(facultySwitch,coreSwitch,port1=1,port2=1)
    self.addLink(studentSwitch,coreSwitch,port1=1,port2=2)
    self.addLink(itSwitch,coreSwitch,port1=1,port2=3)
    self.addLink(dataCenterSwitch,coreSwitch,port1=1,port2=4)

    #Faculty LAN
    facultyWS = self.addHost('facultyWS', mac="00:00:00:00:00:01",ip='10.0.1.2/24',defaultRoute="facultyWS-eth1")
    printer = self.addHost('printer', mac="00:00:00:00:00:02",ip='10.0.1.3/24',defaultRoute="printer-eth1")
    facultyPC = self.addHost('facultyPC', mac="00:00:00:00:00:03",ip='10.0.1.4/24',defaultRoute="facultyPC-eth1")
    self.addLink(facultyWS,facultySwitch,port1=1,port2=2)
    self.addLink(printer,facultySwitch,port1=1,port2=3)
    self.addLink(facultyPC,facultySwitch,port1=1,port2=4)

    #Student Housing LAN
    studentPC1 = self.addHost('studentPC1', mac="00:00:00:00:00:04",ip='10.0.2.2/24',defaultRoute="studentPC1-eth1")
    labWS = self.addHost('labWS', mac="00:00:00:00:00:05",ip='10.0.2.3/24',defaultRoute="labWS-eth1")
    studentPC2 = self.addHost('studentPC2', mac="00:00:00:00:00:06",ip='10.0.2.40',defaultRoute="studentPC2-eth1")
    self.addLink(studentPC1,studentSwitch,port1=1,port2=2)
    self.addLink(labWS,studentSwitch,port1=1,port2=3)
    self.addLink(studentPC2,studentSwitch,port1=1,port2=4)

    #IT Department LAN
    itWS = self.addHost('itWS', mac="00:00:00:00:00:07",ip='10.40.3.30',defaultRoute="itWS-eth1")
    itPC = self.addHost('itPC', mac="00:00:00:00:00:08",ip='10.40.3.254',defaultRoute="itPC-eth1")
    self.addLink(itWS,itSwitch,port1=1,port2=2)
    self.addLink(itPC,itSwitch,port1=1,port2=3)

    #University Data Center
    facultyExamServer = self.addHost('examServer', mac="00:00:00:00:00:09",ip='10.100.100.2/24',defaultRoute="examServer-eth1")
    webServer = self.addHost('webServer', mac="00:00:00:00:00:10",ip='10.100.100.20',defaultRoute="webServer-eth1")
    dnsServer = self.addHost('dnsServer', mac="00:00:00:00:00:11",ip='10.100.100.56',defaultRoute="dnsServer-eth1")
    self.addLink(facultyExamServer,dataCenterSwitch,port1=1,port2=2)
    self.addLink(webServer,dataCenterSwitch,port1=1,port2=3)
    self.addLink(dnsServer,dataCenterSwitch,port1=1,port2=4)

    #Internet
    trustedPC = self.addHost('trustedPC', mac="00:00:00:00:00:12",ip='10.0.203.6/32',defaultRoute="trustedPC-eth1")
    guest1 = self.addHost('guest1', mac="00:00:00:00:00:13",ip='10.0.198.6/32',defaultRoute="guest1-eth1")
    guest2 = self.addHost('guest2', mac="00:00:00:00:00:14",ip='10.0.198.10/32',defaultRoute="guest2-eth1")
    self.addLink(trustedPC,coreSwitch,port1=1,port2=5)
    self.addLink(guest1,coreSwitch,port1=1,port2=6)
    self.addLink(guest2,coreSwitch,port1=1,port2=7)




if __name__ == '__main__':
  #This part of the script is run when the script is executed
  topo = MyTopology() #Creates a topology
  c0 = RemoteController(name='c0', controller=RemoteController, ip='127.0.0.1', port=6633) #Creates a remote controller
  net = Mininet(topo=topo, controller=c0) #Loads the topology
  net.start() #Starts mininet
  CLI(net) #Opens a command line to run commands on the simulated topology
  net.stop() #Stops mininet

