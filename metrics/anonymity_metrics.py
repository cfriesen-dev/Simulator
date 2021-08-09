import math
import numpy as np


def get_entropy(data, num_target_packets):
	column_names = ['Entropy'+str(x) for x in range(num_target_packets)]
	entropies = []
	for column in column_names:
		dist = data.iloc[0][column]
		# suma = sum([float(x) for x in dist])
		# print("For column %s the sum is %f" % (column, suma))
		# entropies.append()
		entropies.append(dist)
	return np.mean(entropies)

# def getEntropy(data):
# 	tmp = data[data["Type"] == "ENTROPY"]
# 	entropy = np.mean(tmp["Entropy"].tolist())
# 	return entropy


def get_unlinkability(data):
	epsilon = []
	dlts = 0
	est_senderA = data["PrSenderA"]
	est_senderB = data["PrSenderB"]
	realSenderLabel = data["RealSenderLabel"]

	for (prA, prB, label) in zip(est_senderA, est_senderB, realSenderLabel):
		if label == 1:
			if not float(prB) == 0.0:
				ratio = float(prA) / float(prB)
				if not ratio == 0.0:
					epsilon.append(math.log(ratio))
			else:
				dlts += 1
		elif label == 2:
			if not float(prA) == 0.0:
				ratio = float(prB) / float(prA)
				if not ratio == 0.0:
					epsilon.append(math.log(ratio))
			else:
				dlts += 1
		else:
			pass
	meanEps = None
	if epsilon != []:
		meanEps = np.mean(epsilon)
	delta = float(dlts) / float(len(est_senderA))
	return (meanEps, delta)


def compute_e2e_latency(df, metric):
	travel_time = []
	for i, r in df.iterrows():
		time_sent = r['PacketTimeSent']
		time_delivered = r['PacketTimeDelivered']
		travel_time.append(time_delivered - time_sent)
	if metric == "mean":
		return np.mean(travel_time)
	elif metric == "max":
		return np.max(travel_time)
	elif metric == "min":
		return np.min(travel_time)
