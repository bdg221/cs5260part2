# Standard Libraries
import argparse
import configparser
import copy
import logging
import os
import random
from typing import Callable, Dict, List
from datetime import datetime

# Local Modules
from DataTypes import \
  Country, Heuristic, Node, \
  ResourceQuantity, ResourceTemplate, Schedule, \
  TransferAction, TransformAction, TransformTemplate, Solution
from DataTypes.TransferAction import TransferDirection
from Parsers import StateParser, TransformTemplateParser
from Evaluators import StateEvaluator, ScheduleEvaluator
from ProblemFormulations import ImplicitGraph
from SearchStrategies import search_strategy_factory


CWD_PATH = os.path.abspath(os.getcwd())
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_PATH, "data")
STATES_PATH = os.path.join(DATA_PATH, "states")
TEMPLATE_EXTENSION=".tmpl"
TRANSFORM_TEMPLATES_PATH = os.path.join(DATA_PATH, "templates/base")

CONFIG: configparser.ConfigParser = None

def load_initial_state(initial_state_file: str) -> List[Country]:
    initial_state_path = os.path.join(STATES_PATH, initial_state_file)
    raw_initial_state = StateParser.read_csv(initial_state_path)
    
    logging.debug(raw_initial_state)

    if not StateParser.validate_initial_state(raw_initial_state):
      raise Exception("Initial state is invalid")

    initial_state: List[Country] = []
    for country in raw_initial_state:
      initial_state.append(Country.from_dict(country))

    return  initial_state

def load_resources(resources_file: str) -> List[ResourceTemplate]:
    resources_path = os.path.join(STATES_PATH, resources_file)
    raw_resources = StateParser.read_csv(resources_path)
    
    logging.debug(raw_resources)

    resource_names = [resource["Resource"] for resource in raw_resources]
    logging.debug(resource_names)

    if not StateParser.validate_resources(resource_names):
      raise Exception("Resources list is missing required resources")

    resources: List[ResourceTemplate] = []
    for resource in raw_resources:
      resources.append(ResourceTemplate.from_dict(resource))

    return resources

def load_states(initial_state_file, resources_file):
    initial_state = load_initial_state(initial_state_file)
    resources = load_resources(resources_file)

    return  initial_state, resources

def load_transform_templates() -> List[TransformTemplate]:
  transform_templates = []
  for file_path in os.listdir(TRANSFORM_TEMPLATES_PATH):
    if file_path.endswith(TEMPLATE_EXTENSION):
      template_path = os.path.join(TRANSFORM_TEMPLATES_PATH,file_path)
      transform_template = TransformTemplateParser.parse(template_path)
      logging.debug(transform_template)
      transform_templates.append(transform_template)
  return transform_templates

def build_country_states_map(initial_state: List[Country]) -> Dict[str, Country]:
  country_state = {}
  for country in initial_state:
    country_name = country.name
    country_state[country_name] = country
  return country_state

def build_transfer_actions(resources: List[ResourceTemplate], country_states: Dict[str, Country], self_country: Country) -> List[TransferAction]:
  # TransferActions are created for all resource types
  # - transfers are restricted to a single resource
  # - transfers are restricted in quantity to 1 - 5
  # Results in count of resource types R * 5 branching (8*5=40 basic) 
  transfer_actions = []
  for resource in resources:
    for quantity in range(1,6):
      if resource.transferable():
        for other_country in (country for country in country_states.values() if country.name != self_country.name):
          resource_quantity = ResourceQuantity(resource.name, quantity)
          send_transfer_action = TransferAction.create_from_resource_quantities(
            self_country=self_country,
            other_country=other_country,
            resource_quantities=[resource_quantity],
            transfer_direction=TransferDirection.SEND,
            cost_fn=(lambda _countries: 0.0)
          )
          transfer_actions.append(send_transfer_action)
          receive_transfer_action = TransferAction.create_from_resource_quantities(
            resource_quantities=[resource_quantity],
            transfer_direction=TransferDirection.RECEIVE,
            self_country=self_country,
            other_country=other_country,
            cost_fn=(lambda _countries: 0.0)
          )
          transfer_actions.append(receive_transfer_action)
  return transfer_actions

def build_transform_actions(transform_templates: List[TransformTemplate], target_country: Country) -> List[TransformAction]:
  # TransformTemplates need to be translated into Actions
  transform_actions = []
  for transform_template in transform_templates:
    transform_action = TransformAction.create_from_transform_template(
      transform_template=transform_template, 
      target_country=target_country
    )
    transform_actions.append(transform_action)
  return transform_actions

def country_scheduler(country_name, resources_file,
                      initial_state_file, output_file,
                      num_schedules, depth_bound,
                      frontier_size):
  logging.info("Loading initial state and resources...")
  initial_state, resources = load_states(initial_state_file, resources_file)
  logging.info("Initial state and resources loaded")

  logging.info("Loading transform templates...")
  transform_templates = load_transform_templates()
  logging.info("Transform templates loaded")

  logging.info("Building country states map...")
  country_states = build_country_states_map(initial_state)
  logging.info("Country states map built")

  self_country: Country = country_states.get(country_name)
  if not self_country:
    raise Exception("Agent country {} not defined in initial state".format(country_name))

  logging.info("Building actions for all countries ...")
  # transfer_actions = build_transfer_actions(resources, country_states, self_country)
  # logging.info("Actions built")
  #
  # logging.info("Building transform actions...")
  # transform_actions = build_transform_actions(transform_templates, target_country=self_country)
  # logging.info("Transform actions built")
  #
  # # Combine all the actions into a single list
  # # Shuffle the list randomly so as not to have any implied bias to actions via ordering
  # all_actions = transfer_actions + transform_actions


  actions = {}
# BUILD ACTIONS FOR EACH COUNTRY INTO A DICTIONARY country_name : all_actions
  for country in country_states.keys():
    transfer_actions = build_transfer_actions(resources, country_states, country_states.get(country))
    transform_actions = build_transform_actions(transform_templates, target_country=country_states.get(country))
    all_actions = transfer_actions + transform_actions
    actions[country] = all_actions
  logging.info("Actions built")
  #bdg - moved processing code to a separate function to make turn-based calls easier
  # now just call run_scheduler

  # solutions, schedule_evaluator, state_evaluator = run_scheduler(all_actions, country_states, resources, self_country,
  #                                                                num_schedules, depth_bound, frontier_size)


  current_world_state = copy.deepcopy(country_states)
  initial_world_state = copy.deepcopy(country_states)
  node = Node(current_world_state, None, None, 0.0)

  # final_solutions will contain the steps for the world schedule
  # it will be a list of dictionaries where the dictionaries include
  # {name_of_country} : NODE
  # the initial entry will be "root": node
  final_solutions = []
  final_solutions.append({'name': 'root', 'node': node})

  """ Number of rounds will be set to 5 for right now"""
  for index in range(100):
    logging.info("### ROUND "+str(index +1)+ " ###")
  # do we need to use the initial_world_state or just the current_world_state?

    for i in country_states.keys():
        self_country = country_states[i]
        logging.debug("#### country state = "+self_country.name)
        solutions, schedule_evaluator, state_evaluator = run_scheduler(actions[self_country.name], current_world_state, resources, self_country, num_schedules, depth_bound, frontier_size)
        # bdg add datetime to output files so they aren't overwritten
        current_dt = datetime.now()

        if index == 0:
          Schedule.write_solutions(solutions, schedule_evaluator.expected_utility, self_country, "sub_call_"+i+
                                 output_file + str(current_dt))

        best_eu = None
        best_solution = None
        for eu, solution in solutions.items():
          if not best_eu or eu > best_eu:
            best_eu = eu
            best_solution = solution

        # get first action from the best solution and perform the action on the current_world_state
        # also add the action to the
        # best_solution.PATH[1] = Node
        next_action = best_solution.PATH[1].PARENT_ACTION
        current_world_state = next_action.apply(current_world_state)
        final_solutions.append({'name': i, 'node' : Node(current_world_state, final_solutions[len(final_solutions)-1]['node'], next_action, 0)})

        # Schedule.write_csv(best_solution, state_evaluator.state_quality, schedule_evaluator.expected_utility,
        #                    self_country, "best_sub_solution_for_"+ i + + str(current_dt) + ".csv")

  current_dt = datetime.now()
  schedule_evaluator = ScheduleEvaluator(
    initial_state=initial_world_state,
    state_quality_fn=state_evaluator.state_quality
  )

  Schedule.write_turn_solutions(final_solutions, schedule_evaluator.state_quality_fn, "turn_based_"+output_file + str(current_dt))
  Schedule.write_turn_solutions_csv(final_solutions, schedule_evaluator.state_quality_fn, "turn_based_"+output_file + str(current_dt)+".csv")



  # #bdg add datetime to output files so they aren't overwritten
  # current_dt = datetime.now()
  # state_list = []
  # for i in range(final_solutions):
  #   state_list.append(final_solutions[i].STATE)
  # solution = Solution(final_solutions[len(final_solutions)-1], state_list)
  # Schedule.write_turn__solutions(solutions, schedule_evaluator.expected_utility, self_country, output_file+str(current_dt))
  #
  # best_eu = None
  # best_solution = None
  # for eu, solution in solutions.items():
  #   if not best_eu or eu > best_eu:
  #     best_eu = eu
  #     best_solution = solution
  # print("#######")
  # print(best_solution.PATH[1].PARENT_ACTION.to_string(self_country))
  #
  # print("#######")
  # Schedule.write_csv(best_solution, state_evaluator.state_quality, schedule_evaluator.expected_utility, self_country, "best_solution_"+str(current_dt)+".csv")

def run_scheduler(all_actions, country_states, resources, self_country, num_schedules, depth_bound, frontier_size):
  if CONFIG.getboolean("Actions", "Shuffle"):
    random.shuffle(all_actions)

  #logging.info("Establishing evaluation functions...")
  initial_country_states = copy.deepcopy(country_states)
  state_evaluator = StateEvaluator(resources)
  schedule_evaluator = ScheduleEvaluator(
    initial_state=initial_country_states,
    state_quality_fn=state_evaluator.state_quality
  )
  utility_fn: Callable[[Node], float] = lambda node: schedule_evaluator.expected_utility(self_country, Schedule(node))
  heuristic = Heuristic(utility_fn)
  #logging.info("Evaluation functions established")

  start_country_state = initial_country_states[self_country.name]
  #logging.debug("Start Agent Country State = {}".format(start_country_state))
  #logging.info("Start Agent Country State Quality = {}".format(state_evaluator.state_quality(start_country_state)))

  solutions = {}
  for _schedule_count in range(1, num_schedules + 1):
    #logging.info("Building search graph...")
    shuffled_all_actions = copy.deepcopy(all_actions)
    if CONFIG.getboolean("Actions", "Shuffle"):
      random.shuffle(shuffled_all_actions)
    graph = ImplicitGraph(country_states, shuffled_all_actions, heuristic)

    strategy = search_strategy_factory(CONFIG.get("Search", "Strategy"))
    enable_reached = CONFIG.getboolean("Search", "EnableReached")
    #logging.info("Executing {} strategy...".format(strategy.__name__))
    #logging.info("Reached Enabled = {}".format(enable_reached))
    solution = graph.search(country_states, strategy((not enable_reached), depth_bound, frontier_size))

    final_state = solution.NODE.STATE
    final_country_state = final_state[self_country.name]
    #logging.debug("Final Agent Country State = {}".format(final_country_state))
    #logging.info("Final Agent Country State Quality = {}".format(state_evaluator.state_quality(final_country_state)))

    schedule = Schedule(solution.NODE)
    expected_utility = schedule_evaluator.expected_utility(start_country_state, schedule)
    #logging.info("Schedule Expected Utility = {}".format(expected_utility))
    solutions[expected_utility] = solution
  return solutions, schedule_evaluator, state_evaluator

def parseCmdLineArgs():
  parser = argparse.ArgumentParser (description="WorldTraderSim")

  parser.add_argument ("-c", "--country-name", default="Atlantis", help="A country name that will be used for the AI's perspective (self)")

  # Arguments governing file paths
  parser.add_argument ("-s", "--state-dir", default=SCRIPT_PATH+"/data/states/", help="Directory containing state files")
  parser.add_argument ("-r", "--resources-file", default="resources.csv", help="CSV file containing resource definitions")
  parser.add_argument ("-i", "--initial-state-file", default="initial.csv", help="CSV file containing the initial game state")
  parser.add_argument ("-o", "--output-file", default="schedules.txt", help="Output file to hold schedules generated by the AI agent")

  # Arguments governing AI agent limitations and performance
  parser.add_argument ("-n", "--num-schedules", type=int, default=1, help="The number of output schedules to generate")
  parser.add_argument ("-d", "--depth-bound", type=int, choices=range(1,1001), default=100, help="How deep the AI agent is allowed to search")
  parser.add_argument ("-f", "--frontier-size", type=int, default=20000, help="Max size of the Frontier")
  
  # Pass all parameters as a config (overrides)
  parser.add_argument ("--config", default=SCRIPT_PATH+"/config.ini", help="configuration file (default: config.ini)")

  # Logging level
  parser.add_argument ("-l", "--logging-level", type=int, default=logging.INFO, choices=[logging.DEBUG,logging.INFO,logging.WARNING,logging.ERROR,logging.CRITICAL], help="logging level, choices 10,20,30,40,50: default 10=logging.DEBUG")
  
  return parser.parse_args()

def parseConfig(args):
  global CONFIG
  parser = configparser.ConfigParser()
  parser.read(args.config)
  CONFIG = parser

def main(): 
  logging.info("Starting WorldTraderSim")
  args = parseCmdLineArgs ()
  logging.getLogger().setLevel(args.logging_level)

  parseConfig(args)

  country_scheduler(args.country_name, args.resources_file, args.initial_state_file,
                    args.output_file, args.num_schedules,
                    args.depth_bound, args.frontier_size)


if __name__ == "__main__":
    # set underlying default logging capabilities
  logging.basicConfig (level=logging.DEBUG,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  main()
