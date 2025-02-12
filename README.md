# Simulator

This repository contains the Python implementation of a mix network simulator.
Originally, the simulator was build to perform an empirical analysis of the anonymity offered by the Loopix anonymity system https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/piotrowska and further extended to support more experiments as part of the Nym project.

The goal of this fork is to analyze if the introduction of realistic traffic workloads can improve the accuracy of measuring mix network performance and strengthen performance optimizations. This is being accomplished through the stated objectives of:
• Objective 1: Develop simulator support of re-playable email traffic workloads with multi-sized messaging
• Objective 2: Compare Nym system performance metrics (anonymity, latency, and cover traffic) between original simulation parameters and when using email traffic workloads
• Objective 3: Determine the optimal packet size for supporting email traffic

The implementation is done using Python 3. My version is `3.7.6` 

To install the dependencies run

`pip3 install -r requirements.txt`

To run the simulator you need the command

`python3 playground.py`

You can change the parameters of the simulation in file `test_config.json`

To run the simulator using a traffic workload file you need to load your traffic workload json file into the Simulator directory and then run the command

`python3 workload.py`

An example workload file has been provided as `traffic_workload.json`.
Packet size and cyptographic header are only applied when packet size > 0. To maintain a 1 to 1 mapping of message to packet, set packet size equal to 0 in the `test_config.json` file.  

This extension of the nym simulator was for a masters dissertation.
