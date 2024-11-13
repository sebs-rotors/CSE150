#!/usr/bin/python
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController

class MyTopology(Topo):
  def __init__(self):
    Topo.__init__(self)
   
    # laptop1 = self.addHost('Laptop1', ip='200.20.2.8/24',defaultRoute="Laptop1-eth1")
    coreSwitch = self.addSwitch('coreSwitch')
    facultySwitch = self.addSwitch('facultySwitch')
    studentSwitch = self.addSwitch('studentSwitch')
    dataCenterSwitch = self.addSwitch('dataCenterSwitch')
    itSwitch = self.addSwitch('itSwitch')
    
    # We're gonna do hosts BY NETWORK:
    # University Data Center
    facultyExamServer = self.addHost('FacultyExamServer', ip='10.100.100.2/24')

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