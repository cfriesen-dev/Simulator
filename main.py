import os
import argparse
from simulation_modes import test_mode


def main(args):
    if args.exp_dir:
        experiment_dir = args.exp_dir
    else:
        print("Please provide filename to load the experiment settings from.")
        return

    if args.config_file:
        config_file = args.config_file
    else:
        print("Please provide the name of the config file")
        return
    print("Experimental configuration uploaded from path: %s" % config_file)

    mode = args.mode
    if mode == "transcript":
        print("Mode not supported")
        # print("Running simulator in a transcript mode")
        #
        # email_data_file = "Data/data_email/slices/slice_1.csv" #"Data/data_email/data_riseup_email.csv"
        # transcript_mode.run(data_file=email_data_file, conf_file = config_file, exp_dir=experiment_dir)

    elif mode == "synthetic":
        print("Mode not supported")
        # print("Running simulator with synthetic traffic")

    elif mode == "anon":
        print("Mode not supported")
        # print("Running simulator in a anonymous stats mode")

    elif mode == "test":
        print("Running simulator in a test mode")

        print(experiment_dir)
        test_mode.run(exp_dir=experiment_dir, conf_file=config_file)

    elif mode == "diff_test":
        print("Mode not supported")

        # print("Running simulator in a diff test mode")
        #
        # diff_config_test.run(log_dir= os.path.join(experiment_dir,conf["logging"]["dir"]), number_of_clients=conf["clients"]["number"], ticks=conf["phases"]["execution"],
        #     layers=conf["network"]["layers"],
        #     MixNodes_per_layer=conf["network"]["layer_size"], num_in=conf["network"]["prov_in"],
        #     num_out=conf["network"]["prov_out"], num_runs=conf["runs"],
        #     startup=conf["phases"]["burnin"], cooldown=conf["phases"]["cooldown"],
        #     perc_corrupt=conf["mixnodes"]["perc_corrupt"], verbose=conf["debug"]["mixnodes_verbose"])
    else:
        print("Mode is not recognised")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-mode", default="transcript", help="The mode in which we want to run the simulator: transcript, synthetic traces, anon or test")
    parser.add_argument("-exp_dir", help="The directory of the experiment directory")
    parser.add_argument("-config_file", help="The file of the experiment configuration")
    parser.add_argument("-test", help="Test flag")
    parser.add_argument("-datadir", help="The directory to the database file")
    parser.add_argument("-hour", help="Take only one hour slice of dataset")
    parser.add_argument("-12hour", help="Take only the 12hour slice of dataset")
    parser.add_argument("-minute", help="Take a minute slice of dataset")
    parser.add_argument("-day", help="Take a day slice of dataset")

    main(parser.parse_args())
