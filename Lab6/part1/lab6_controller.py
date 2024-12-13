from pox.core import core
import pox.openflow.libopenflow_01 as of
import ipaddress

log = core.getLogger()

class Routing(object):
    def __init__(self, connection):
        self.connection = connection
        connection.addListeners(self)

    def do_routing(self, packet, packet_in, port_on_switch, switch_id):
        def accept(packet, packet_in, out_port):
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet)
            msg.match.in_port = port_on_switch
            msg.idle_timeout = 45
            msg.hard_timeout = 300
            msg.actions.append(of.ofp_action_output(port=out_port))
            msg.data = packet_in
            self.connection.send(msg)

            msg2 = of.ofp_packet_out()
            msg2.data = packet_in
            msg2.in_port = port_on_switch
            msg2.actions.append(of.ofp_action_output(port=out_port))
            self.connection.send(msg2)

        def drop(packet, packet_in):
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet)
            msg.idle_timeout = 45
            msg.hard_timeout = 300
            msg.data = packet_in
            self.connection.send(msg)

        student_subnet = ipaddress.ip_network('10.0.2.0/24')
        faculty_subnet = ipaddress.ip_network('10.0.1.0/24')
        it_subnet = ipaddress.ip_network('10.40.3.0/24')
        datacenter_subnet = ipaddress.ip_network('10.100.100.0/24')

        ip_packet = packet.find('ipv4')
        if not ip_packet:
            drop(packet, packet_in)
            return

        src_ip = ip_packet.srcip
        dst_ip = ip_packet.dstip

        if packet.find('icmp') is not None:
            allowed_subnets = [student_subnet, faculty_subnet, it_subnet]
            if not any(ipaddress.ip_address(src_ip) in subnet for subnet in allowed_subnets) or not any(
                    ipaddress.ip_address(dst_ip) in subnet for subnet in allowed_subnets):
                drop(packet, packet_in)
                return
            accept(packet, packet_in, port_on_switch)

        elif packet.find('tcp') is not None:
            if str(dst_ip) == '10.100.100.2' and not ipaddress.ip_address(src_ip) in faculty_subnet:
                drop(packet, packet_in)
                return
            allowed_subnets = [student_subnet, faculty_subnet, it_subnet, datacenter_subnet]
            if not any(ipaddress.ip_address(src_ip) in subnet for subnet in allowed_subnets) or not any(
                    ipaddress.ip_address(dst_ip) in subnet for subnet in allowed_subnets):
                drop(packet, packet_in)
                return
            accept(packet, packet_in, port_on_switch)

        elif packet.find('udp') is not None:
            allowed_subnets = [student_subnet, faculty_subnet, it_subnet, datacenter_subnet]
            if not any(ipaddress.ip_address(src_ip) in subnet for subnet in allowed_subnets) or not any(
                    ipaddress.ip_address(dst_ip) in subnet for subnet in allowed_subnets):
                drop(packet, packet_in)
                return
            accept(packet, packet_in, port_on_switch)

        else:
            drop(packet, packet_in)

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        packet_in = event.ofp
        self.do_routing(packet, packet_in, event.port, event.dpid)


def launch():
    def start_switch(event):
        Routing(event.connection)

    core.openflow.addListenerByName("ConnectionUp", start_switch)
