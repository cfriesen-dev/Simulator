from classes.Node import Node
import numpy as np
from classes.Packet import Packet


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