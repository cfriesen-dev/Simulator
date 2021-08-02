from classes.Node import Node
import numpy as np
from classes.Packet import Packet
from classes.Message import Message
from scipy.stats import levy
from classes.Utilities import StructuredMessage


class Client(Node):
    def __init__(self, env, conf, net, loggers=None, label=0, id=None, p2p=False, messages=None):
        self.conf = conf
        self.message_workload = messages
        super().__init__(env=env, conf=conf, net=net, loggers=loggers, id=id)

    def schedule_retransmits(self):
        pass

    def schedule_message(self, message):
        #  This function is used in the transcript mode
        ''' schedule_message adds given message into the outgoing client's buffer. Before adding the message
            to the buffer the function records the time at which the message was queued.'''

        print("> Scheduled message")
        current_time = self.env.now
        message.time_queued = current_time
        for pkt in message.pkts:
            pkt.time_queued = current_time
        self.add_to_buffer(message.pkts)

    def print_msgs(self):
        ''' Method prints all the messages gathered in the buffer of incoming messages.'''
        for msg in self.msg_buffer_in:
            msg.output()

    def start(self):
        ''' Main client method; It sends packets out.
        It checks if there are any new packets in the outgoing buffer.
        If it finds any, it sends the first of them.
        If none are found, the client sends out a dummy
        packet (i.e., cover loop packet).
        '''

        delays = []

        while True:
            if self.alive:
                if delays == []:
                    delays = list(np.random.exponential(self.rate_sending, 10000))

                delay = delays.pop()
                yield self.env.timeout(float(delay))

                if len(self.pkt_buffer_out) > 0: #If there is a packet to be send
                    tmp_pkt = self.pkt_buffer_out.pop(0)
                    self.send_packet(tmp_pkt)
                    self.env.total_messages_sent += 1

                else:
                    tmp_pkt = Packet.dummy(conf=self.conf, net=self.net, dest=self, sender=self)  # sender_estimates[sender.label] = 1.0
                    tmp_pkt.time_queued = self.env.now
                    self.send_packet(tmp_pkt)
                    self.env.total_messages_sent += 1
            else:
                break

    def simulate_modeled_traffic(self, exclude=None):
        messages = self.net.traffic[self.id]

        for message in messages:
            if self.alive:
                yield self.env.timeout(message['time_from_last_msg'])

                for recipient in message['to']:
                    # Prevent the second sender from sending to the tracked recipient
                    if exclude and recipient == exclude.id:
                        continue

                    # New Message
                    r_client = self.net.clients_dict[recipient]
                    msg = Message.random(conf=self.conf, net=self.net, sender=self, dest=r_client, size=message['size'])
                    self.simulate_adding_packets_into_buffer(msg)
            else:
                break

    def simulate_message_generation(self, dest, model_traffic):
        ''' This method generates actual 'real' messages that can be used to compute the entropy.
            The rate and amount at which we generate this traffic is defined by rate_generating and num_target_packets
            in the config file.'''
        i = 0

        generation_rate = self.rate_generating
        if model_traffic:
            # Hardcoded generation distribution based on traffic workload files
            # Should be size=self.conf["misc"]["num_target_packets"] but the distribution is shifted into negative values
            # therefore extra is needed for values picked < 0
            delays = [x for x in levy.rvs(*(-60.86760352972247, 230.09494123284878), size=2000) if x > 0]

        while i < self.conf["misc"]["num_target_packets"]:
            if model_traffic:
                generation_rate = delays.pop()

            yield self.env.timeout(float(generation_rate))

            # New Message
            msg = Message.random(conf=self.conf, net=self.net, sender=self, dest=dest, model_traffic=model_traffic)
            self.simulate_adding_packets_into_buffer(msg)
            for num, pkt in enumerate(msg.pkts):
                if i + num < len(pkt.probability_mass):
                    pkt.probability_mass[i + num] = 1.0  # only needed for sender1
            i += len(msg.pkts)
            print(f" {i} packets sent for entropy measurement")
        self.env.finished = True

    def simulate_adding_packets_into_buffer(self, msg):
        #  This function is used in the test mode
        current_time = self.env.now
        msg.time_queued = current_time  # The time when the message was created and placed into the queue
        for pkt in msg.pkts:
            pkt.time_queued = current_time
        self.add_to_buffer(msg.pkts)
        self.env.message_ctr += 1
        self.system_logger.info(StructuredMessage(metadata=(self.env.now, self.env.real_pkts, self.env.dummy_pkts)))

    def add_to_buffer(self, packets):
        for pkt in packets:
            tmp_now = self.env.now
            pkt.time_queued = tmp_now
            self.pkt_buffer_out.append(pkt)
