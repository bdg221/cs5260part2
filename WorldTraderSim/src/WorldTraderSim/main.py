import argparse
import logging
import os

CWD_PATH = os.path.abspath(os.getcwd())
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

def country_scheduler(country_name, resources_file,
                      initial_state_file, output_file,
                      num_schedules, depth_bound,
                      frontier_size):
    pass


def parseCmdLineArgs ():
  parser = argparse.ArgumentParser (description="WorldTraderSim")

  parser.add_argument ("-c", "--country-name", default="Atlantis", help="A country name that will be used for the AI's perspective (self)")

  # Arguments governing file paths
  parser.add_argument ("-s", "--state-dir", default=SCRIPT_PATH+"/data/states/", help="Directory containing state files")
  parser.add_argument ("-r", "--resources-file", default="resources.csv", help="CSV file containing resource definitions")
  parser.add_argument ("-i", "--initial-state-file", default="initial.csv", help="CSV file containing the initial game state")
  parser.add_argument ("-o", "--output-file", default="schedules.json", help="Output file to hold schedules generated by the AI agent")

  # Arguments governing AI agent limitations and performance
  parser.add_argument ("-n", "--num-schedules", type=int, default=5, help="The number of output schedules to generate")
  parser.add_argument ("-d", "--depth-bound", type=int, choices=range(1,10), default=1, help="How deep the AI agent is allowed to search")
  parser.add_argument ("-f", "--frontier-size", type=int, default=1000, help="Max size of the Frontier")
  
  # Pass all parameters as a config (overrides)
  parser.add_argument ("--config", default="config.ini", help="configuration file (default: config.ini)")

  # Logging level
  parser.add_argument ("-l", "--logging-level", type=int, default=logging.DEBUG, choices=[logging.DEBUG,logging.INFO,logging.WARNING,logging.ERROR,logging.CRITICAL], help="logging level, choices 10,20,30,40,50: default 10=logging.DEBUG")
  
  return parser.parse_args()


def main(): 
    logging.info(CWD_PATH)
    logging.info(SCRIPT_PATH)
    args = parseCmdLineArgs ()
    print(args)
    

if __name__ == "__main__":
    main()
