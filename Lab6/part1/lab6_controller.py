# Lab5 Skeleton

from pox.core import core

import pox.openflow.libopenflow_01 as of
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
    # port_on_swtich - the port on which this packet was received
    # switch_id - the switch which received this packet

    # Your code here
    def accept(packet, packet_in, out_port=None):
      msg = of.ofp_packet_out(data=packet_in,
                             idle_timeout=45,
                             hard_timeout=600)
      msg.actions.append(of.ofp_action_output(port=out_port if out_port is not None else of.OFPP_FLOOD))
      self.connection.send(msg)
      print("Packet Accepted - Flow Table Installed on Switches")

    def drop(packet, packet_in):
      self.connection.send(of.ofp_packet_out(data=packet_in))
      print("Packet Dropped - Flow Table Installed on Switches")

    # Get IP packet if it exists
    ip_packet = packet.find('ipv4')
    if not ip_packet:
      drop(packet, packet_in)
      return

    src_ip = ip_packet.srcip
    dst_ip = ip_packet.dstip

    # Define subnets
    student_subnet = ipaddress.ip_network('10.0.2.0/24')
    faculty_subnet = ipaddress.ip_network('10.0.1.0/24')
    it_subnet = ipaddress.ip_network('10.40.3.0/24')
    datacenter_subnet = ipaddress.ip_network('10.100.100.0/24')
    
    src_in_subnet = None
    dst_in_subnet = None
    
    # Determine which subnets source and destination belong to
    for subnet in [student_subnet, faculty_subnet, it_subnet, datacenter_subnet]:
      if ipaddress.ip_address(str(src_ip)) in subnet:
        src_in_subnet = subnet
      if ipaddress.ip_address(str(dst_ip)) in subnet:
        dst_in_subnet = subnet

    # Handle ICMP traffic
    if packet.find('icmp'):
      # Allow if same subnet
      if src_in_subnet and src_in_subnet == dst_in_subnet:
        accept(packet, packet_in)
        return
      # Allow between Student, Faculty and IT
      elif src_in_subnet in [student_subnet, faculty_subnet, it_subnet] and \
           dst_in_subnet in [student_subnet, faculty_subnet, it_subnet]:
        accept(packet, packet_in)
        return
      else:
        drop(packet, packet_in)
        return

    # Handle TCP traffic  
    elif packet.find('tcp'):
      # Check if trying to access exam server
      if str(dst_ip) == '10.100.100.2' and src_in_subnet != faculty_subnet:
        drop(packet, packet_in)
        return
        
      # Allow if same subnet
      if src_in_subnet and src_in_subnet == dst_in_subnet:
        accept(packet, packet_in)
        return
      # Allow between Data Center, IT, Faculty, Student, and trustedPC
      elif (src_in_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] or \
            str(src_ip) == '10.0.203.6') and \
           (dst_in_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] or \
            str(dst_ip) == '10.0.203.6'):
        accept(packet, packet_in)
        return
      else:
        drop(packet, packet_in)
        return

    # Handle UDP traffic
    elif packet.find('udp'):
      # Allow if same subnet
      if src_in_subnet and src_in_subnet == dst_in_subnet:
        accept(packet, packet_in)
        return
      # Allow between Data Center, IT, Faculty and Student
      elif src_in_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet] and \
           dst_in_subnet in [datacenter_subnet, it_subnet, faculty_subnet, student_subnet]:
        accept(packet, packet_in)
        return
      else:
        drop(packet, packet_in)
        return
        
    # Drop all other traffic
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
