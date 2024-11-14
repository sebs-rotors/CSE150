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
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.match.in_port = port_on_switch  # Explicitly match input port
        msg.idle_timeout = 45
        msg.hard_timeout = 300
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD if out_port is None else out_port))
        msg.data = packet_in
        self.connection.send(msg)
        
        # Immediate packet handling
        msg2 = of.ofp_packet_out()
        msg2.data = packet_in
        msg2.in_port = port_on_switch
        msg2.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD if out_port is None else out_port))
        self.connection.send(msg2)
        print(f"Packet sent immediately from port {port_on_switch} to port {out_port}")

    def drop(packet, packet_in):
        """Drop a packet and install a flow rule to continue dropping similar packets"""
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = 45
        msg.hard_timeout = 300
        msg.data = packet_in
        self.connection.send(msg)
        print("Packet dropped")

    # Add this helper function for inter-subnet routing
    def get_next_hop_port(src_ip, dst_ip, switch_id):
        """Determine the output port for inter-subnet routing"""
        # If we're at the core switch (s1)
        if switch_id == 1:
            if ipaddress.ip_address(dst_ip) in faculty_subnet:
                return s1_ports['s2']
            elif ipaddress.ip_address(dst_ip) in student_subnet:
                return s1_ports['s3']
            elif ipaddress.ip_address(dst_ip) in it_subnet:
                return s1_ports['s5']
            elif ipaddress.ip_address(dst_ip) in datacenter_subnet:
                return s1_ports['s4']
        # If we're at an edge switch
        else:
            # If destination is in a different subnet, send to core switch
            if str(dst_ip) not in switch_ports[switch_id]:
                return switch_ports[switch_id]['s1']  # Port connecting to core switch
            # If destination is in same subnet, send directly
            else:
                return switch_ports[switch_id][str(dst_ip)]
        return None

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
    # Port mappings for each switch
    # Core Switch (s1) ports
    s1_ports = {
        's2': 1,  # Faculty switch
        's3': 2,  # Student switch  
        's4': 3,  # Data Center switch
        's5': 4,  # IT switch
        'guest1': 5,
        'guest2': 6,
        'trustedPC': 7
    }

    # Faculty Switch (s2) ports 
    s2_ports = {
        's1': 1,  # Core switch
        '10.0.1.2': 2,  # facultyWS
        '10.0.1.4': 3,  # facultyPC
        '10.0.1.3': 4   # printer
    }

    # Student Switch (s3) ports
    s3_ports = {
        's1': 1,  # Core switch
        '10.0.2.2': 2,  # studentPC1
        '10.0.2.40': 3, # studentPC2
        '10.0.2.3': 4   # labWS
    }

    # Data Center Switch (s4) ports
    s4_ports = {
        's1': 1,  # Core switch
        '10.100.100.2': 2,  # examServer
        '10.100.100.20': 3, # webServer
        '10.100.100.56': 4  # dnsServer
    }

    # IT Switch (s5) ports
    s5_ports = {
        's1': 1,  # Core switch
        '10.40.3.30': 2,  # itWS
        '10.40.3.254': 3  # itPC
    }

    # Map switch DPIDs to their port mappings
    switch_ports = {
        1: s1_ports,  # Core switch
        2: s2_ports,  # Faculty switch
        3: s3_ports,  # Student switch
        4: s4_ports,  # Data Center switch
        5: s5_ports   # IT switch
    }


    # Rule 1: ICMP Traffic
    if packet.find('icmp') is not None:
        print("ICMP packet detected")
        
        # Check subnet membership
        src_in_student = ipaddress.ip_address(src_ip) in student_subnet
        src_in_faculty = ipaddress.ip_address(src_ip) in faculty_subnet
        src_in_it = ipaddress.ip_address(src_ip) in it_subnet
        
        dst_in_student = ipaddress.ip_address(dst_ip) in student_subnet
        dst_in_faculty = ipaddress.ip_address(dst_ip) in faculty_subnet
        dst_in_it = ipaddress.ip_address(dst_ip) in it_subnet

        # Handle routing based on switch
        if switch_id == 1:  # Core switch
            if dst_in_faculty:
                accept(packet, packet_in, s1_ports['s2'])
            elif dst_in_student:
                accept(packet, packet_in, s1_ports['s3'])
            elif dst_in_it:
                accept(packet, packet_in, s1_ports['s5'])
            else:
                drop(packet, packet_in)
        
        elif switch_id == 5:  # IT switch
            if str(dst_ip) in s5_ports:  # Destination is in this subnet
                accept(packet, packet_in, s5_ports[str(dst_ip)])
            else:  # Need to forward to core switch
                accept(packet, packet_in, s5_ports['s1'])
        
        elif switch_id == 2:  # Faculty switch
            if str(dst_ip) in s2_ports:
                accept(packet, packet_in, s2_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s2_ports['s1'])
        
        elif switch_id == 3:  # Student switch
            if str(dst_ip) in s3_ports:
                accept(packet, packet_in, s3_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s3_ports['s1'])
        
        else:
            drop(packet, packet_in)
        return

    # Rule 2: TCP Traffic
    elif packet.find('tcp') is not None:
        print("TCP packet detected")
        
        # Check subnet membership
        src_in_student = ipaddress.ip_address(src_ip) in student_subnet
        src_in_faculty = ipaddress.ip_address(src_ip) in faculty_subnet
        src_in_it = ipaddress.ip_address(src_ip) in it_subnet
        src_in_datacenter = ipaddress.ip_address(src_ip) in datacenter_subnet
        src_is_trusted = str(src_ip) == '10.0.203.6'  # trustedPC IP
        
        dst_in_student = ipaddress.ip_address(dst_ip) in student_subnet
        dst_in_faculty = ipaddress.ip_address(dst_ip) in faculty_subnet
        dst_in_it = ipaddress.ip_address(dst_ip) in it_subnet
        dst_in_datacenter = ipaddress.ip_address(dst_ip) in datacenter_subnet
        dst_is_trusted = str(dst_ip) == '10.0.203.6'  # trustedPC IP
        dst_is_examserver = str(dst_ip) == '10.100.100.2'  # examServer IP

        # Check if source and destination are in same subnet
        same_subnet = (
            (src_in_student and dst_in_student) or
            (src_in_faculty and dst_in_faculty) or
            (src_in_it and dst_in_it) or
            (src_in_datacenter and dst_in_datacenter)
        )

        # Check if it's allowed cross-subnet communication
        allowed_subnets = (
            (src_in_student or src_in_faculty or src_in_it or src_in_datacenter or src_is_trusted) and
            (dst_in_student or dst_in_faculty or dst_in_it or dst_in_datacenter or dst_is_trusted)
        )

        # Special case: Only faculty can access exam server
        if dst_is_examserver and not src_in_faculty:
            print("Non-faculty access to exam server denied")
            drop(packet, packet_in)
            return

        if not (same_subnet or allowed_subnets):
            print("TCP traffic not allowed between these subnets")
            drop(packet, packet_in)
            return

        # Handle routing based on switch
        if switch_id == 1:  # Core switch
            if dst_in_faculty:
                accept(packet, packet_in, s1_ports['s2'])
            elif dst_in_student:
                accept(packet, packet_in, s1_ports['s3'])
            elif dst_in_datacenter:
                accept(packet, packet_in, s1_ports['s4'])
            elif dst_in_it:
                accept(packet, packet_in, s1_ports['s5'])
            elif dst_is_trusted:
                accept(packet, packet_in, s1_ports['trustedPC'])
            else:
                drop(packet, packet_in)
        
        elif switch_id == 2:  # Faculty switch
            if str(dst_ip) in s2_ports:
                accept(packet, packet_in, s2_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s2_ports['s1'])
        
        elif switch_id == 3:  # Student switch
            if str(dst_ip) in s3_ports:
                accept(packet, packet_in, s3_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s3_ports['s1'])
        
        elif switch_id == 4:  # Data Center switch
            if str(dst_ip) in s4_ports:
                accept(packet, packet_in, s4_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s4_ports['s1'])
        
        elif switch_id == 5:  # IT switch
            if str(dst_ip) in s5_ports:
                accept(packet, packet_in, s5_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s5_ports['s1'])
        else:
            drop(packet, packet_in)
        return

    # Rule 3: UDP Traffic
    elif packet.find('udp') is not None:
        print("UDP packet detected")
        
        # Check subnet membership
        src_in_student = ipaddress.ip_address(src_ip) in student_subnet
        src_in_faculty = ipaddress.ip_address(src_ip) in faculty_subnet
        src_in_it = ipaddress.ip_address(src_ip) in it_subnet
        src_in_datacenter = ipaddress.ip_address(src_ip) in datacenter_subnet
        
        dst_in_student = ipaddress.ip_address(dst_ip) in student_subnet
        dst_in_faculty = ipaddress.ip_address(dst_ip) in faculty_subnet
        dst_in_it = ipaddress.ip_address(dst_ip) in it_subnet
        dst_in_datacenter = ipaddress.ip_address(dst_ip) in datacenter_subnet

        # Check if source and destination are in same subnet
        same_subnet = (
            (src_in_student and dst_in_student) or
            (src_in_faculty and dst_in_faculty) or
            (src_in_it and dst_in_it) or
            (src_in_datacenter and dst_in_datacenter)
        )

        # Check if it's allowed cross-subnet communication
        allowed_subnets = (
            (src_in_student or src_in_faculty or src_in_it or src_in_datacenter) and
            (dst_in_student or dst_in_faculty or dst_in_it or dst_in_datacenter)
        )

        if not (same_subnet or allowed_subnets):
            print("UDP traffic not allowed between these subnets")
            drop(packet, packet_in)
            return

        # Handle routing based on switch
        if switch_id == 1:  # Core switch
            if dst_in_faculty:
                accept(packet, packet_in, s1_ports['s2'])
            elif dst_in_student:
                accept(packet, packet_in, s1_ports['s3'])
            elif dst_in_datacenter:
                accept(packet, packet_in, s1_ports['s4'])
            elif dst_in_it:
                accept(packet, packet_in, s1_ports['s5'])
            else:
                drop(packet, packet_in)
        
        elif switch_id == 2:  # Faculty switch
            if str(dst_ip) in s2_ports:
                accept(packet, packet_in, s2_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s2_ports['s1'])
        
        elif switch_id == 3:  # Student switch
            if str(dst_ip) in s3_ports:
                accept(packet, packet_in, s3_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s3_ports['s1'])
        
        elif switch_id == 4:  # Data Center switch
            if str(dst_ip) in s4_ports:
                accept(packet, packet_in, s4_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s4_ports['s1'])
        
        elif switch_id == 5:  # IT switch
            if str(dst_ip) in s5_ports:
                accept(packet, packet_in, s5_ports[str(dst_ip)])
            else:
                accept(packet, packet_in, s5_ports['s1'])
        else:
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
