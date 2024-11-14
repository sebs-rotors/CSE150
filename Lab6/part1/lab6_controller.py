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
    # Add debug logging at the start
    print(f"\nPacket received on switch s{switch_id} port {port_on_switch}")
    
    def accept(packet, packet_in, out_port=None):
        print(f"Accepting packet on switch s{switch_id}: in_port={port_on_switch}, out_port={out_port}")
        """Accept a packet and install a flow rule"""
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = 45
        msg.hard_timeout = 300
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD if out_port is None else out_port))
        msg.data = packet_in
        self.connection.send(msg)
        
        # Add this line to handle the packet immediately
        msg2 = of.ofp_packet_out()
        msg2.data = packet_in
        msg2.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD if out_port is None else out_port))
        self.connection.send(msg2)
        print("Packet sent immediately")

    def drop(packet, packet_in):
        """Drop a packet and install a flow rule to continue dropping similar packets"""
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = 45
        msg.hard_timeout = 300
        msg.data = packet_in
        self.connection.send(msg)
        print("Packet dropped")

    # Handle ARP traffic first
    if packet.find('arp') is not None:
        accept(packet, packet_in)
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
    SWITCH_PORTS = {
        1: {  # Core switch (s1)
            'faculty': 1,    # to s2
            'student': 2,    # to s3
            'datacenter': 3, # to s4
            'it': 4,        # to s5
        },
        2: {  # Faculty switch (s2)
            'core': 1,      # to s1
            'hosts': [2, 3, 4]  # to faculty hosts
        },
        3: {  # Student switch (s3)
            'core': 1,      # to s1
            'hosts': [2, 3, 4]  # to student hosts
        },
        4: {  # Datacenter switch (s4)
            'core': 1,      # to s1
            'hosts': [2, 3, 4]  # to datacenter hosts
        },
        5: {  # IT switch (s5)
            'core': 1,      # to s1
            'itws': 2,      # to itWS
            'itpc': 3       # to itPC
        }
    }

    # Helper function to get port for subnet on core switch
    def get_core_port_for_subnet(subnet):
        if subnet == faculty_subnet:
            return SWITCH_PORTS[1]['faculty']
        elif subnet == student_subnet:
            return SWITCH_PORTS[1]['student'] 
        elif subnet == datacenter_subnet:
            return SWITCH_PORTS[1]['datacenter']
        elif subnet == it_subnet:
            return SWITCH_PORTS[1]['it']
        return None

    # Determine which subnets source and destination belong to
    src_subnet = None
    dst_subnet = None
    for subnet in [student_subnet, faculty_subnet, it_subnet, datacenter_subnet]:
        if ipaddress.ip_address(str(src_ip)) in subnet:
            print(f"Source IP {src_ip} is in subnet {subnet}")
            src_subnet = subnet
        if ipaddress.ip_address(str(dst_ip)) in subnet:
            print(f"Destination IP {dst_ip} is in subnet {subnet}")
            dst_subnet = subnet

    # Rule 1: ICMP Traffic
    if packet.find('icmp') is not None:
        print("ICMP packet detected")
        # Allow if same subnet
        if src_subnet and src_subnet == dst_subnet:
            if switch_id == 1:
                accept(packet, packet_in, get_core_port_for_subnet(dst_subnet))
            else:
                accept(packet, packet_in, port_on_switch)
            return
        # Allow between Student, Faculty and IT
        elif src_subnet in [student_subnet, faculty_subnet, it_subnet] and \
             dst_subnet in [student_subnet, faculty_subnet, it_subnet]:
            if switch_id == 1:  # Core switch
                accept(packet, packet_in, get_core_port_for_subnet(dst_subnet))
            else:  # Edge switch
                accept(packet, packet_in, 1)  # Forward to core
            return
        drop(packet, packet_in)
        return

    # Rule 2: TCP Traffic
    elif packet.find('tcp') is not None:
        print("TCP packet detected")
        # Check exam server access restriction
        if str(dst_ip) == '10.100.100.2' and src_subnet != faculty_subnet:
            drop(packet, packet_in)
            return
        
        # Allow if same subnet
        if src_subnet and src_subnet == dst_subnet:
            if switch_id == 1:
                accept(packet, packet_in, get_core_port_for_subnet(dst_subnet))
            else:
                accept(packet, packet_in, port_on_switch)
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
                    accept(packet, packet_in, get_core_port_for_subnet(dst_subnet))
            else:  # Edge switch
                accept(packet, packet_in, 1)  # Forward to core
            return
        drop(packet, packet_in)
        return

    # Rule 3: UDP Traffic
    elif packet.find('udp') is not None:
        print("UDP packet detected")
        # Allow if same subnet
        if src_subnet and src_subnet == dst_subnet:
            if switch_id == 1:
                accept(packet, packet_in, get_core_port_for_subnet(dst_subnet))
            else:
                accept(packet, packet_in, port_on_switch)
            return
        # Allow between Data Center, IT, Faculty and Student
        elif src_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] and \
             dst_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet]:
            if switch_id == 1:  # Core switch
                accept(packet, packet_in, get_core_port_for_subnet(dst_subnet))
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
