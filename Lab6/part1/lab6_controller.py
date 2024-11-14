# Lab5 Skeleton

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
import ipaddress

log = core.getLogger()

class Routing (object):
    
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)
  
  def do_routing (self, packet, packet_in, port_on_switch, switch_id):
    # Handle ARP traffic first
    if packet.find('arp') is not None:
        accept(packet, packet_in, of.OFPP_FLOOD)
        return

    # Get IP packet
    ip_packet = packet.find('ipv4')
    if not ip_packet:
        print("Non-IP packet detected - dropping")
        drop(packet, packet_in)
        return

    src_ip = ip_packet.srcip
    dst_ip = ip_packet.dstip
    print(f"Processing packet: {src_ip} -> {dst_ip}")

    # Define subnets
    student_subnet = ipaddress.ip_network('10.0.2.0/24')
    faculty_subnet = ipaddress.ip_network('10.0.1.0/24')
    it_subnet = ipaddress.ip_network('10.40.3.0/24')
    datacenter_subnet = ipaddress.ip_network('10.100.100.0/24')

    # Subnet to port mapping on core switch
    SUBNET_PORTS = {
        faculty_subnet: 1,    # Faculty -> port 1
        student_subnet: 2,    # Student -> port 2
        datacenter_subnet: 3, # DataCenter -> port 3
        it_subnet: 4,        # IT -> port 4
    }

    # Determine which subnets source and destination belong to
    src_subnet = None
    dst_subnet = None
    for subnet in SUBNET_PORTS.keys():
        if ipaddress.ip_address(str(src_ip)) in subnet:
            src_subnet = subnet
        if ipaddress.ip_address(str(dst_ip)) in subnet:
            dst_subnet = subnet

    # Rule 1: ICMP Traffic
    if packet.find('icmp') is not None:
        # Allow if same subnet
        if src_subnet and src_subnet == dst_subnet:
            accept(packet, packet_in, port_on_switch if switch_id != 1 else SUBNET_PORTS[dst_subnet])
            return
        # Allow between Student, Faculty and IT
        elif src_subnet in [student_subnet, faculty_subnet, it_subnet] and \
             dst_subnet in [student_subnet, faculty_subnet, it_subnet]:
            if switch_id == 1:  # Core switch
                accept(packet, packet_in, SUBNET_PORTS[dst_subnet])
            else:  # Edge switch
                accept(packet, packet_in, 1)  # Forward to core
            return
        drop(packet, packet_in)
        return

    # Rule 2: TCP Traffic
    elif packet.find('tcp') is not None:
        # Check exam server access restriction
        if str(dst_ip) == '10.100.100.2' and src_subnet != faculty_subnet:
            drop(packet, packet_in)
            return
        
        # Allow if same subnet
        if src_subnet and src_subnet == dst_subnet:
            accept(packet, packet_in, port_on_switch if switch_id != 1 else SUBNET_PORTS[dst_subnet])
            return
        # Allow between Data Center, IT, Faculty, Student, and trustedPC
        elif (src_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] or \
              str(src_ip) == '10.0.203.6') and \
             (dst_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] or \
              str(dst_ip) == '10.0.203.6'):
            if switch_id == 1:  # Core switch
                if str(dst_ip) == '10.0.203.6':
                    accept(packet, packet_in, 7)  # trustedPC port
                else:
                    accept(packet, packet_in, SUBNET_PORTS[dst_subnet])
            else:  # Edge switch
                accept(packet, packet_in, 1)  # Forward to core
            return
        drop(packet, packet_in)
        return

    # Rule 3: UDP Traffic
    elif packet.find('udp') is not None:
        # Allow if same subnet
        if src_subnet and src_subnet == dst_subnet:
            accept(packet, packet_in, port_on_switch if switch_id != 1 else SUBNET_PORTS[dst_subnet])
            return
        # Allow between Data Center, IT, Faculty and Student
        elif src_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] and \
             dst_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet]:
            if switch_id == 1:  # Core switch
                accept(packet, packet_in, SUBNET_PORTS[dst_subnet])
            else:  # Edge switch
                accept(packet, packet_in, 1)  # Forward to core
            return
        drop(packet, packet_in)
        return

    # Rule 4: Drop all other traffic
    drop(packet, packet_in)
    return
  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.
    self.do_routing(packet, packet_in, event.port, event.dpid)

def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Routing(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)
