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
      msg = of.ofp_packet_out()
      msg.data = packet_in
      msg.idle_timeout = 45
      msg.hard_timeout = 600

      if out_port is not None:
        msg.actions.append(of.ofp_action_output(port=out_port))
      else: msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD)) # specifically for ARP packets

      self.connection.send(msg)
      print("Packet Accepted - Flow Table Installed on Switches")

    def drop(packet, packet_in):
      msg = of.ofp_packet_out()
      msg.data = packet_in
      self.connection.send(msg)
      print("Packet Dropped - Flow Table Installed on Switches")


    pass

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
