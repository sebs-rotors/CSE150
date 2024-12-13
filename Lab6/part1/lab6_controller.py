from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
log = core.getLogger()

class Routing(object):
    def __init__(self, connection):
        def addProto (self, nw_proto, dl_type):
            msg = of.ofp_flow_mod()
            match = of.ofp_match()
            match.nw_proto = nw_proto
            match.dl_type = dl_type
            msg.match = match
            msg.hard_timeout = of.OFP_FLOW_PERMANENT
            msg.soft_timeout = of.OFP_FLOW_PERMANENT
            msg.priority = of.OFP_DEFAULT_PRIORITY
            action = of.ofp_action_output(port = of.OFPP_NORMAL)
            msg.actions.append(action)
#        print "Inserting flow for protocol: " + msg.__str__()

            self.connection.send(msg)
        self.connection = connection
        connection.addListeners(self)
        # Define subnet groupings
        self.student_housing = ['10.0.2']
        self.faculty = ['10.0.1']
        self.it_department = ['10.40.3']
        self.data_center = ['10.100.100']
        self.trusted_ip = '10.0.203.6'
        addProto(self, pkt.arp.REQUEST, pkt.ethernet.ARP_TYPE)
        addProto(self, pkt.arp.REPLY, pkt.ethernet.ARP_TYPE)
        addProto(self, pkt.arp.REV_REQUEST, pkt.ethernet.ARP_TYPE)
        addProto(self, pkt.arp.REV_REPLY, pkt.ethernet.ARP_TYPE)

    def do_routing(self, packet, packet_in, port_on_switch, switch_id):
        print ("do_routing " + str( switch_id))

        isICMP = packet.find("icmp")
        isTCP = packet.find("tcp")
        isUDP = packet.find("udp")

        # Extract IP addresses
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.buffer_id = packet_in.buffer_id
        srcip = str(msg.match.nw_src)
        dstip = str(msg.match.nw_dst)

        # Get source and destination networks
        srcnw = ".".join(srcip.split(".")[:3])
        dstnw = ".".join(dstip.split(".")[:3])

        # Apply routing rules
        if isICMP:
            # ICMP Rule 1
            if (srcnw in self.student_housing or srcnw in self.faculty or srcnw in self.it_department) and \
               (dstnw in self.student_housing or dstnw in self.faculty or dstnw in self.it_department):
                self.forward_packet(msg, dstip, switch_id)
            elif srcnw == dstnw:
                self.forward_packet(msg, dstip, switch_id)
        elif isTCP:
            # TCP Rule 2
            if (srcnw in self.student_housing or srcnw in self.faculty or srcnw in self.it_department or
                srcnw in self.data_center or srcip == self.trusted_ip) and \
               (dstnw in self.student_housing or dstnw in self.faculty or dstnw in self.it_department or
                dstnw in self.data_center or dstip == self.trusted_ip):
                if srcnw == "10.0.1" and dstip == "10.100.100.2":
                    self.forward_packet(msg, dstip, switch_id)  # Faculty access to exam server
                elif srcnw == dstnw:
                    self.forward_packet(msg, dstip, switch_id)
        elif isUDP:
            # UDP Rule 3
            if (srcnw in self.student_housing or srcnw in self.faculty or srcnw in self.it_department or
                srcnw in self.data_center) and \
               (dstnw in self.student_housing or dstnw in self.faculty or dstnw in self.it_department or
                dstnw in self.data_center):
                self.forward_packet(msg, dstip, switch_id)
            elif srcnw == dstnw:
                self.forward_packet(msg, dstip, switch_id)
        else:
            # Rule 4: Drop all other traffic
            log.info("Dropping packet from %s to %s" % (srcip, dstip))

    def forward_packet(self, msg, dstip, switch_id):
        # Define switch-port mappings based on your topology
        switches = {
            1: {},
            2: {'10.0.1.2': 2, '10.0.1.3': 3, '10.0.1.4': 4},
            3: {'10.0.2.2': 2, '10.0.2.3': 3, '10.0.2.40': 4},
            4: {'10.40.3.30': 2, '10.40.3.254': 3},
            5: {'10.100.100.2': 2, '10.100.100.20': 3, '10.100.100.56': 4},
        }
        if dstip in switches[switch_id]:
            dport = switches[switch_id][dstip]
            msg.actions.append(of.ofp_action_output(port=dport))
            self.connection.send(msg)
        else:
            log.warning("No forwarding rule for destination %s on switch %d" % (dstip, switch_id))

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            log.warning("Ignoring incomplete packet")
            return
        packet_in = event.ofp
        self.do_routing(packet, packet_in, event.port, event.dpid)

def launch():
    def start_switch(event):
        log.debug("Controlling %s" % (event.connection,))
        Routing(event.connection)
    core.openflow.addListenerByName("ConnectionUp", start_switch)
