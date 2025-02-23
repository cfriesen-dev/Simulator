from simulation_modes import test_mode
import os
from metrics import anonymity_metrics
import pandas as pd
import json


if __name__ == "__main__":

	# try:
	print("Mix-network Simulator\n")
	print("Insert the following network parameters to test: ")

	with open('test_config.json') as json_file:
		config = json.load(json_file)

	if not os.path.exists('./playground_experiment/logs'):
		os.makedirs('./playground_experiment/logs')
	else:
		try:
			os.remove('./playground_experiment/logs/packet_log.csv')
			os.remove('./playground_experiment/logs/message_log.csv')
			os.remove('./playground_experiment/logs/last_mix_entropy.csv')
		except:
			pass

	test_mode.run(exp_dir='playground_experiment', conf_file=None, conf_dic=config)
	throughput = test_mode.throughput

	packetLogsDir = './playground_experiment/logs/packet_log.csv'
	entropyLogsDir = './playground_experiment/logs/last_mix_entropy.csv'
	packetLogs = pd.read_csv(packetLogsDir, delimiter=';')
	entropyLogs = pd.read_csv(entropyLogsDir, delimiter=';')

	unlinkability = anonymity_metrics.get_unlinkability(packetLogs)
	entropy = anonymity_metrics.get_entropy(entropyLogs, config["misc"]["num_target_packets"])
	latency = anonymity_metrics.compute_e2e_latency(packetLogs, "mean")

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
	print(">> Overall latency: %f seconds (including mixing delay and packet cryptographic processing)" % (latency))
	print(">> Throughput of the network: %f [packets / second]" % throughput)
	print("-------------------------------------------------------")

