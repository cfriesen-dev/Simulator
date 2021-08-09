from simulation_modes import test_mode
import os
from metrics import anonymity_metrics
import pandas as pd
import json


if __name__ == "__main__":

    # try:
    print("Mix-network Simulator\n")
    print("Insert the following network parameters to test: ")

    with open('test_config.json') as config_file:
        config = json.load(config_file)

    with open('traffic_workload.json') as traffic_file:
        traffic = json.load(traffic_file)

    if not os.path.exists('./workload_experiment/logs'):
        os.makedirs('./workload_experiment/logs')
    else:
        try:
            os.remove('./workload_experiment/logs/packet_log.csv')
            os.remove('./workload_experiment/logs/message_log.csv')
            os.remove('./workload_experiment/logs/last_mix_entropy.csv')
            os.remove('./workload_experiment/logs/system_log.csv')
        except:
            pass

    test_mode.run(exp_dir='workload_experiment', conf_file=None, conf_dic=config, traffic_dic=traffic)
    throughput = test_mode.throughput

    packetLogsDir = './workload_experiment/logs/packet_log.csv'
    entropyLogsDir = './workload_experiment/logs/last_mix_entropy.csv'
    packetLogs = pd.read_csv(packetLogsDir, delimiter=';')
    entropyLogs = pd.read_csv(entropyLogsDir, delimiter=';')

    unlinkability = anonymity_metrics.get_unlinkability(packetLogs)
    entropy = anonymity_metrics.get_entropy(entropyLogs, config["misc"]["num_target_packets"])
    overall_latency = anonymity_metrics.compute_e2e_latency(packetLogs, "mean")
    min_latency = anonymity_metrics.compute_e2e_latency(packetLogs, "min")
    max_latency = anonymity_metrics.compute_e2e_latency(packetLogs, "max")


    print("\n\n")
    print("Simulation finished. Below, you can check your results.")
    print("-------------------------------------------------------")
    print("-------- Anonymity metrics --------")
    print(">>> Entropy: ", entropy)
    if unlinkability[0] is None:
        print(">>> E2E Unlinkability: epsilon= -, delta=%f)" % unlinkability[1])
    else:
        print(">>> E2E Unlinkability: (epsilon=%f, delta=%f)" % unlinkability)
    print("\n\n")
    print("-------- Performance metrics --------")
    print(">> Overall latency: %f seconds (including mixing delay and packet cryptographic processing)" % (overall_latency))
    print(">> Min latency: %f seconds (including mixing delay and packet cryptographic processing)" % (min_latency))
    print(">> Max latency: %f seconds (including mixing delay and packet cryptographic processing)" % (max_latency))
    print(">> Throughput of the network: %f [packets / second]" % throughput)
    print("-------------------------------------------------------")
