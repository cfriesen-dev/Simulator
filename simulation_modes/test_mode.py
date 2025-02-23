import simpy
import os
import datetime
import numpy as np
import experiments.Settings
from classes.Net import *
from classes.Utilities import *


throughput = 0.0


def get_loggers(log_dir, conf):

    packet_logger = setup_logger('simulation.packet', os.path.join(log_dir, 'packet_log.csv'))
    packet_logger.info(StructuredMessage(metadata=("Type", "CurrentTime", "ClientID", "PacketID", "PacketType", "MessageID", "PacketTimeQueued", "PacketTimeSent", "PacketTimeDelivered", "TotalFragments", "PrOthers", "PrSenderA", "PrSenderB", "RealSenderLabel", "Route", "PoolSizes")))

    message_logger = setup_logger('simulation.messages', os.path.join(log_dir, 'message_log.csv'))
    message_logger.info(StructuredMessage(metadata=("Type", "CurrentTime", "ClientID", "MessageID", "NumPackets", "MsgTimeQueued", "MsgTimeSent", "TimeSpentSending", "MsgTimeDelivered", "TimeSpentDelivering", "MsgTransitTime", "MsgSize", "MsgPadding", "MsgRealSender")))

    entropy_logger = setup_logger('simulation.mix', os.path.join(log_dir, 'last_mix_entropy.csv'))
    entropy_logger.info(StructuredMessage(metadata=tuple(['Entropy' + str(x) for x in range(int(conf["misc"]["num_target_packets"]))])))

    system_logger = setup_logger('simulation.system', os.path.join(log_dir, 'system_log.csv'))
    system_logger.info(StructuredMessage(metadata=("EnvTime", "NumClients", "NumMessages", "NumRealPackets", "NumDummyPackets")))

    return (packet_logger, message_logger, entropy_logger, system_logger)


def setup_env(conf):
    env = simpy.Environment()
    env.stop_sim_event = env.event()
    env.message_ctr = 0
    env.dummy_pkts = 0
    env.real_pkts = 0
    env.total_messages_sent = 0
    env.total_messages_received = 0
    env.active_clients = 0
    env.finished = False
    env.entropy = numpy.zeros(int(conf["misc"]["num_target_packets"]))

    return env


def run_p2p(env, conf, net, loggers):
    print("Runninf P2P topology")
    peers = net.peers
    print("Number of active peers: ", len(peers))

    SenderT1 = peers.pop()
    SenderT1.label = 1
    SenderT1.verbose = True

    SenderT2 = peers.pop()
    SenderT2.label = 2
    SenderT2.verbose = True

    recipient = peers.pop()

    for c in peers:
        env.process(c.start())
        env.process(c.start_loop_cover_traffc())

    env.process(SenderT1.start())
    env.process(SenderT1.start_loop_cover_traffc())
    env.process(SenderT2.start())
    env.process(SenderT2.start_loop_cover_traffc())
    env.process(recipient.start())
    env.process(recipient.start_loop_cover_traffc())

    print("---------" + str(datetime.datetime.now()) + "---------")
    print("> Running the system for %s ticks to prepare it for measurement." % (conf["phases"]["burnin"]))

    # env.process(progress_update(env, 5))
    time_started = env.now
    time_started_unix = datetime.datetime.now()
    # ------ RUNNING THE STARTUP PHASE ----------
    if conf["phases"]["burnin"] > 0.0:
        env.run(until=conf["phases"]["burnin"])
    print("> Finished the preparation")

    # Start logging since system in steady state
    for p in net.peers:
        p.mixlogging = True

    env.process(SenderT1.simulate_adding_packets_into_buffer(recipient))
    print("> Started sending traffic for measurements")

    env.run(until=env.stop_sim_event)  # Run until the stop_sim_event is triggered.
    print("> Main part of simulation finished. Starting cooldown phase.")

    # ------ RUNNING THE COOLDOWN PHASE ----------
    env.run(until=env.now + conf["phases"]["cooldown"])

    # Log entropy
    loggers[2].info(StructuredMessage(metadata=tuple(env.entropy)))
    print("> Cooldown phase finished.")

    time_finished = env.now
    time_finished_unix = datetime.datetime.now()

    print("> Total Simulation Time [in ticks]: " + str(time_finished-time_started) + "---------")
    print("> Total Simulation Time [in unix time]: " + str(time_finished_unix-time_started_unix) + "---------")

    flush_logs(loggers)

    global throughput
    throughput = float(env.total_messages_received) / float(time_finished-time_started)

    mixthroughputs = []
    for p in net.peers:
        mixthroughputs.append(float(p.pkts_sent) / float(time_finished-time_started))

    print("Network throughput %f / second: " % throughput)
    print("Average mix throughput %f / second, with std: %f" % (np.mean(mixthroughputs), np.std(mixthroughputs)))


def run_client_server(env, conf, net, loggers):
    clients = net.clients
    print("Number of active clients: ", len(clients))

    sender_t1 = clients.pop(random.randint(0, len(clients)))
    sender_t1.label = 1
    sender_t1.verbose = True
    print("Target Sender1: ", sender_t1.id)

    sender_t2 = clients.pop(random.randint(0, len(clients)))
    sender_t2.label = 2
    sender_t2.verbose = True
    print("Target Sender2: ", sender_t2.id)

    recipient = clients.pop(random.randint(0, len(clients)))
    recipient.verbose = True
    print("Target Recipient: ", recipient.id)

    net.mixnodes[0].verbose = True
    model_traffic = net.traffic is not None

    for c in clients:
        c.verbose = True
        env.process(c.start())
        env.process(c.start_loop_cover_traffc())
        if model_traffic:
            env.process(c.simulate_modeled_traffic(exclude=recipient))

    env.process(sender_t1.start())
    env.process(sender_t1.start_loop_cover_traffc())
    env.process(sender_t2.start())
    env.process(sender_t2.start_loop_cover_traffc())
    env.process(recipient.start())
    env.process(recipient.start_loop_cover_traffc())

    if model_traffic:
        env.process(sender_t2.simulate_modeled_traffic(exclude=recipient))
        env.process(recipient.simulate_modeled_traffic())

    print("---------" + str(datetime.datetime.now()) + "---------")
    print("> Running the system for %s ticks to prepare it for measurement." % (conf["phases"]["burnin"]))

    time_started = env.now
    time_started_unix = datetime.datetime.now()
    # ------ RUNNING THE STARTUP PHASE ----------
    if conf["phases"]["burnin"] > 0.0:
        env.run(until=conf["phases"]["burnin"])
    print("> Finished the preparation")

    # Start logging since system in steady state
    for p in net.mixnodes:
        p.mixlogging = True

    env.process(sender_t1.simulate_message_generation(recipient, model_traffic))
    print("> Started sending traffic for measurements")

    env.run(until=env.stop_sim_event)  # Run until the stop_sim_event is triggered.
    print("> Main part of simulation finished. Starting cooldown phase.")

    # Log entropy
    loggers[2].info(StructuredMessage(metadata=tuple(env.entropy)))
    # ------ RUNNING THE COOLDOWN PHASE ----------
    env.run(until=env.now + conf["phases"]["cooldown"])

    # Log entropy
    loggers[2].info(StructuredMessage(metadata=tuple(env.entropy)))

    print("> Cooldown phase finished.")
    time_finished = env.now
    time_finished_unix = datetime.datetime.now()
    print("Receiver received: ", recipient.num_received_packets)
    print("> Total Simulation Time [in ticks]: " + str(time_finished-time_started) + "---------")
    print("> Total Simulation Time [in unix time]: " + str(time_finished_unix-time_started_unix) + "---------")

    flush_logs(loggers)

    global throughput
    throughput = float(env.total_messages_received) / float(time_finished-time_started)

    mixthroughputs = []
    for m in net.mixnodes:
        mixthroughputs.append(float(m.pkts_sent) / float(time_finished-time_started))

    print("Total number of packets which went through the network: ", float(env.total_messages_received))
    print("Network throughput %f / second: " % throughput)
    print("Average mix throughput %f / second, with std: %f" % (np.mean(mixthroughputs), np.std(mixthroughputs)))


def flush_logs(loggers):
    for l in loggers:
        for h in l.handlers:
            h.flush()


def run(exp_dir, conf_file=None, conf_dic=None, traffic_dic=None):
    print("The experiment log directory is: %s" % exp_dir)

    # Upload config file
    if conf_file:
        print("The config file is at:%s" % conf_file)
        conf = experiments.Settings.load(conf_file)
    elif conf_dic:
        conf = conf_dic
    else:
        print("A configuration dictionary or file required")

    # Logging directory
    log_dir = os.path.join(exp_dir, conf["logging"]["dir"])
    # Setup environment
    env = setup_env(conf)

    # Create the network
    type = conf["network"]["topology"]
    loggers = get_loggers(log_dir, conf)
    net = Network(env, type, conf, loggers, traffic=traffic_dic)

    if type == "p2p":
        run_p2p(env, conf, net, loggers)
    else:
        run_client_server(env, conf, net, loggers)
