#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController

class MyTopology(Topo):
  def __init__(self):
    Topo.__init__(self)
   
    # laptop1 = self.addHost('Laptop1', ip='200.20.2.8/24',defaultRoute="Laptop1-eth0")
    coreSwitch = self.addSwitch('s1')
    facultySwitch = self.addSwitch('s2')
    studentSwitch = self.addSwitch('s3')
    dataCenterSwitch = self.addSwitch('s4')
    itSwitch = self.addSwitch('s5')
    
    self.addLink(coreSwitch, facultySwitch, port1=1, port2=1)
    self.addLink(coreSwitch, studentSwitch, port1=2, port2=1)
    self.addLink(coreSwitch, dataCenterSwitch, port1=3, port2=1)
    self.addLink(coreSwitch, itSwitch, port1=4, port2=1)
    
    
    # We're gonna do hosts and links BY NETWORK:
    # University Data Center
    facultyExamServer = self.addHost('FacultyExamServer', ip='10.100.100.2/24', mac='00:00:00:00:00:01')
    webServer = self.addHost('webServer', ip='10.100.100.20/24', mac='00:00:00:00:00:02')
    dnsServer = self.addHost('dnsServer', ip='10.100.100.56/24', mac='00:00:00:00:00:03')
    
    self.addLink(facultyExamServer, dataCenterSwitch, port1=1, port2=2)
    self.addLink(webServer, dataCenterSwitch, port1=1, port2=3)
    self.addLink(dnsServer, dataCenterSwitch, port1=1, port2=4)
    
    # IT Department LAN
    itWS = self.addHost('itWS', ip='10.40.3.30/24', mac='00:00:10:00:00:01')
    itPC = self.addHost('itPC', ip='10.40.3.254/24', mac='00:00:10:00:00:02')
    
    self.addLink(itWS, itSwitch, port1=1, port2=2)
    self.addLink(itPC, itSwitch, port1=1, port2=3)
    
    # Faculty LAN
    facultyWS = self.addHost('facultyWS', ip='10.0.1.2/24', mac='00:00:20:00:00:01')
    facultyPC = self.addHost('facultyPC', ip='10.0.1.4/24', mac='00:00:20:00:00:02')
    printer = self.addHost('printer', ip='10.0.1.3/24', mac='00:00:20:00:00:03')
    
    self.addLink(facultyWS, facultySwitch, port1=1, port2=2)
    self.addLink(facultyPC, facultySwitch, port1=1, port2=3)
    self.addLink(printer, facultySwitch, port1=1, port2=4)
    
    # Student Housing LAN
    studentPC1 = self.addHost('studentPC1', ip='10.0.2.2/24', mac='00:00:30:00:00:01')
    studentPC2 = self.addHost('studentPC2', ip='10.0.2.40/24', mac='00:00:30:00:00:02')
    labWS = self.addHost('labWS', ip='10.0.2.3/24', mac='00:00:30:00:00:03')
    
    self.addLink(studentPC1, studentSwitch, port1=1, port2=2)
    self.addLink(studentPC2, studentSwitch, port1=1, port2=3)
    self.addLink(labWS, studentSwitch, port1=1, port2=4)
    self.addLink(studentPC1, labWS, port1=2, port2=2)
    
    # Intenet
    trustedPC = self.addHost('trustedPC', ip='10.0.203.6/32', mac='00:00:40:00:00:01')
    guest1 = self.addHost('guest1', ip='10.0.196.6/32', mac='00:00:40:00:00:02')
    guest2 = self.addHost('guest2', ip='10.0.198.10/32', mac='00:00:40:00:00:03')

    self.addLink(guest1, coreSwitch, port1=1, port2=5)
    self.addLink(guest2, coreSwitch, port1=1, port2=6)
    self.addLink(trustedPC, coreSwitch, port1=1, port2=7)

    # switch1 = self.addSwitch('s1')

    # self.addLink(laptop1, switch1, port1=1, port2=2)

if __name__ == '__main__':
  #This part of the script is run when the script is executed
  topo = MyTopology() #Creates a topology
  c0 = RemoteController(name='c0', controller=RemoteController, ip='127.0.0.1', port=6633) #Creates a remote controller
  net = Mininet(topo=topo, controller=c0) #Loads the topology
  net.start() #Starts mininet
  CLI(net) #Opens a command line to run commands on the simulated topology
  net.stop() #Stops mininet