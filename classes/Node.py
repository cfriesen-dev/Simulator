from classes.Utilities import random_string, StructuredMessage, get_exponential_delay
import math
import numpy as np
from classes.Packet import Packet
from classes.Message import Message
import random


class Node(object):

    def __init__(self, env, conf, net=None, label=0, loggers=None, id=None):

        self.env = env
        self.conf = conf
        self.id = id or random_string(self.conf["misc"]["id_len"])
        self.net = net

        self.pkts_received = 0
        self.pkts_sent = 0

        self.avg_delay = 0.0 if self.conf["mixnodes"]["avg_delay"] == 0.0 else float(self.conf["mixnodes"]["avg_delay"])

        # State
        self.pool = {}
        self.inter_pkts = 0 #ctr which count how many new packets arrived since the last time a packet left
        self.probability_mass = None
        self.sender_estimates = None
        self.pool = {}
        self.mixlogging = False

        self.loggers = loggers if loggers else None
        (self.packet_logger, self.message_logger, self.entropy_logger) = self.loggers

        #State
        self.alive = True

        self.rate_sending = 1.0/float(self.conf["clients"]["rate_sending"])

        # This specifies how often we put a real message in the bugger
        # Only used when there is no traffic file
        self.rate_generating = float(self.conf["clients"]["sim_add_buffer"])

        self.cover_traffic = self.conf["clients"]["cover_traffic"]
        self.cover_traffic_rate = 1.0/float(self.conf["clients"]["cover_traffic_rate"])

        self.verbose = False
        self.pkt_buffer_out = []
        self.pkt_buffer_out_not_ack = {}
        self.label = label
        self.send_dummy_ACK = self.conf["clients"]["dummies_acks"]
        self.send_ACK = self.conf["clients"]["ACK"]
        self.num_received_packets = 0
        self.msg_buffer_in = {}
        self.start_logs = False
        self.batch_num = 0
        self.free_to_batch = True

    def start_loop_cover_traffc(self):
        ''' Function responsible for managing the independent Poisson stream
            of loop cover traffic.
        '''

        if self.cover_traffic:
            delays = []
            while True:
                if self.alive:
                    if delays == []:
                        delays = list(np.random.exponential(self.cover_traffic_rate, 10000))

                    delay = delays.pop()
                    yield self.env.timeout(float(delay))

                    cover_loop_packet = Packet.dummy(conf=self.conf, net = self.net, dest=self, sender=self)
                    cover_loop_packet.time_queued = self.env.now
                    self.send_packet(cover_loop_packet)
                    self.env.total_messages_sent += 1
                else:
                    break
        else:
            pass

    def send_packet(self, packet):
        ''' Methods sends a packet into the network,
         and logs information about the sending.
​
            Keyword arguments:
            packet - an object of class Packet which is sent into the network.
        '''

        packet.time_sent = self.env.now
        packet.current_node = -1  # If it's a retransmission this needs to be reset
        packet.times_transmitted += 1

        if packet.type == "REAL" and packet.message.time_sent is None:
            packet.message.time_sent = packet.time_sent

        self.env.process(self.net.forward_packet(packet))

    def process_batch_round(self):
        ''' Additional function if we want to simulate a batching technique.
        '''
        self.batch_num += 1

        batch = list(self.pool.keys())[:int(self.conf["mixnodes"]["batch_size"])]
        random.shuffle(batch)
        for pktid in batch:
            if pktid in self.pool.keys():
                pkt = self.pool[pktid]
                yield self.env.timeout(0.000386) # add some delay for packet cryptographinc processing
                self.forward_packet(pkt)
        self.free_to_batch = True
        return
        yield

    def process_packet(self, packet):
        ''' Function performs processing of the given packet and logs information
            about it and forwards it to the next destionation.
            While processing the packet, the function also calculates the probability
            that the given packet comes from a particular sender (target sender).

            Keyword arguments:
            packet - the packet which should be processed.
        '''
        # Check if this is the desired destination
        if self.id == packet.dest.id:
            self.env.process(self.process_received_packet(packet))
        else:
            self.pkts_received += 1
            self.add_pkt_in_pool(packet)

            if (self.net.type == "cascade" or self.net.type == "multi_cascade") and self.conf["mixnodes"]["batch"] == True:
                if len(self.pool) >= int(self.conf["mixnodes"]["batch_size"]) and self.free_to_batch == True:
                    self.free_to_batch = False
                    self.env.process(self.process_batch_round())
            else:

                delay = get_exponential_delay(self.avg_delay) if self.avg_delay != 0.0 else 0.0
                wait = delay + 0.000386 # add the time of processing the Sphinx packet (benchmarked using our Sphinx rust implementation).
                yield self.env.timeout(wait)

                if not packet.dropped: # It may get dropped if pool gets full, while waiting
                    self.forward_packet(packet)
                else:
                    pass

    def process_received_packet(self, packet):
        ''' 1. Processes the received packets and logs informatiomn about them.
            2. If enabled, it sends an ACK packet to the sender.
            3. Checks whether all the packets of particular message were received and logs the information about the reconstructed message.
            Keyword arguments:
            packet - the received packet.
        '''

        packet.time_delivered = self.env.now
        self.env.total_messages_received += 1
        # print(self.env.message_ctr)

        if packet.type == "REAL":
            self.num_received_packets += 1
            msg = packet.message

            if not msg.complete_receiving:
                msg.register_received_pkt(packet)
                self.msg_buffer_in[msg.id] = msg
                if self.conf["logging"]["enabled"] and self.packet_logger is not None and self.start_logs:
                    self.packet_logger.info(StructuredMessage(metadata=("RCV_PKT_REAL", self.env.now, self.id, packet.id, packet.type, packet.msg_id, packet.time_queued, packet.time_sent, packet.time_delivered, packet.fragments, packet.sender_estimates[0], packet.sender_estimates[1], packet.sender_estimates[2], packet.real_sender.label, packet.route, packet.pool_logs)))

            if msg.complete_receiving:
                msg_transit_time = (msg.time_delivered - msg.time_sent)
                if self.conf["logging"]["enabled"] and self.message_logger is not None and self.start_logs:
                    self.message_logger.info(StructuredMessage(metadata=("RCV_MSG", self.env.now, self.id, msg.id, len(msg.pkts), msg.time_queued, msg.time_sent, msg.time_delivered, msg_transit_time, len(msg.payload), msg.real_sender.label)))
                self.env.message_ctr -= 1

                # this part is used to stop the simulator at a time when all sent packets got delivered!
                if self.env.finished and self.env.message_ctr <= 0:
                  print('> The stop simulation condition happened.')
                  self.env.stop_sim_event.succeed()

        elif packet.type == "DUMMY":
            pass
        else:
            raise Exception("Packet type not recognised")

        return
        yield  # self.env.timeout(0.0)

    def forward_packet(self, packet):
        if not self.probability_mass is None:
            packet.probability_mass = self.probability_mass.copy()
        if not self.sender_estimates is None:
            packet.sender_estimates = self.sender_estimates.copy()

        #If it has been dropped in the meantime, we just skip sending it.
        try:
            self.pool.pop(packet.id)
        except Exception as e:
            pass

        # If the pool dries out, then we start measurements from scratch
        if len(self.pool) == 0:
            self.sender_estimates = None
            self.probability_mass = None
        self.pkts_sent += 1

        # If this is the last mixnode, update the entropy taking into account probabilities
        # of packets leaving the network
        if self.id == packet.route[-2].id and self.mixlogging:
            self.update_entropy(packet)

        self.env.process(self.net.forward_packet(packet))

    def update_entropy(self, packet):
        for i, pr in enumerate(packet.probability_mass):
            if pr != 0.0:
                self.env.entropy[i] += -(float(pr) * math.log(float(pr), 2))

    def add_pkt_in_pool(self, packet):
        ''' Method adds incoming packet in mixnode pool and updates the vector
            of estimated probabilities, taking into account the new state of the pool.

            Keyword arguments:
            packet - the packet for which we update the probabilities vector
        '''
        self.inter_pkts += 1
        if self.probability_mass is None and self.sender_estimates is None:
            self.pool[packet.id] = packet
            self.probability_mass = packet.probability_mass.copy()
            self.sender_estimates = packet.sender_estimates.copy()
        else:
            dist_pm = self.probability_mass * len(self.pool) + packet.probability_mass
            dist_se = self.sender_estimates * len(self.pool) + packet.sender_estimates

            self.pool[packet.id] = packet  # Add Packet in Pool

            dist_pm = dist_pm / float(len(self.pool))
            dist_se = dist_se / float(len(self.pool))

            self.probability_mass = dist_pm.copy()
            self.sender_estimates = dist_se.copy()

    def set_start_logs(self, time=0.0):
        yield self.env.timeout(time)
        self.start_logs = True
        if self.verbose:
            print("> Logs set on for Client %s." % self.id)

    def simulate_modeled_traffic(self):
        messages = self.net.traffic[self.id]

        for message in messages:
            yield self.env.timeout(message['time_from_last_msg'])

            for recipient in message['to']:
                # New Message
                msg = Message.random(conf=self.conf, net=self.net, sender=self, dest=recipient, size=message['size'])
                self.simulate_adding_packets_into_buffer(msg)
                # !!!! TODO: Do I need to add the probability mass here for sender 1?
            self.env.finished = True

    def simulate_message_generation(self, dest):
        ''' This method generates actual 'real' messages that can be used to compute the entropy.
            The rate and amount at which we generate this traffic is defined by rate_generating and num_target_packets
            in the config file.'''
        i = 0

        while i < self.conf["misc"]["num_target_packets"]:
            yield self.env.timeout(float(self.rate_generating))

            # New Message
            msg = Message.random(conf=self.conf, net=self.net, sender=self, dest=dest)
            self.simulate_adding_packets_into_buffer(msg)
            for num, pkt in enumerate(msg.pkts):
                pkt.probability_mass[i + num] = 1.0  # only needed for sender1
            i += len(msg.pkts)
        self.env.finished = True

    def simulate_adding_packets_into_buffer(self, msg):
        #  This function is used in the test mode
        current_time = self.env.now
        msg.time_queued = current_time  # The time when the message was created and placed into the queue
        for pkt in msg.pkts:
            pkt.time_queued = current_time
        self.add_to_buffer(msg.pkts)
        self.env.message_ctr += 1

    def terminate(self, delay=0.0):
        ''' Function changes user's alive status to False after a particular delay
            Keyword argument:
            delayd (float) - time after the alice status should be switched to False.
        '''
        yield self.env.timeout(delay)
        self.alive = False
        print("Node %s terminated at time %s ." % (self.id, self.env.now))

    def add_to_buffer(self, packets):
        for pkt in packets:
            tmp_now = self.env.now
            pkt.time_queued = tmp_now
            self.pkt_buffer_out.append(pkt)

    def __repr__(self):
        return self.id
