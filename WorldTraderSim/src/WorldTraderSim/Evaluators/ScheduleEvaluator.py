# Standard Libraries
import logging
import math
from typing import Callable, Dict

# Local Modules
from DataTypes import Country, Schedule

# Numeric Constants
# TODO - allow config at runtime
SCHEDULE_FAILED_IMPACT=-0.25
SCHEDULE_LENGTH_IMPACT=0.9

class ScheduleEvaluator:
  def __init__(self, initial_state: Dict[str, Country], state_quality_fn: Callable[[Country], float]) -> None:
    self.initial_state = initial_state
    self.state_quality_fn = state_quality_fn
    

  def undiscounted_reward(self, country: Country, schedule: Schedule):
    logging.debug(self.undiscounted_reward.__name__)
    start_state = self.initial_state[country.name]
    logging.debug(start_state)
    start_quality = self.state_quality_fn(start_state)
    logging.debug(start_quality)
    end_state = schedule.get_country_state(country.name)
    logging.debug(end_state)
    end_quality = self.state_quality_fn(end_state) 
    logging.debug(end_quality)
    return end_quality - start_quality

  def discounted_reward(self, country: Country, schedule: Schedule) -> float:
    logging.debug(self.discounted_reward.__name__)
    gamma = SCHEDULE_LENGTH_IMPACT
    N = schedule.get_steps()
    R = self.undiscounted_reward
    exponential = gamma ** N
    return float(exponential * R(country, schedule))

  def logistic_success(self, country: Country, schedule: Schedule) -> float:
    logging.debug(self.logistic_success.__name__)
    c = country
    s = schedule
    DR = self.discounted_reward
    x = DR(c, s)
    logging.debug("Discounted Reward = {}".format(str(x)))
    L = 1
    x_0 = 1
    k = 1

    try:
      exponent =  ( -k * ( x - x_0 ) )
      power = math.e ** exponent
    except OverflowError:
      power = float("inf")

    return float( L / ( 1 + power ) )

  def country_schedule_success_probability(self, country: Country, schedule: Schedule) -> float:
    return self.logistic_success(country, schedule)

  def schedule_success_probability(self, schedule: Schedule) -> float:
    logging.debug(self.schedule_success_probability.__name__)
    countries = schedule.get_impacted_countries()
    prob = 1
    for country in countries:
      prob = prob * self.country_schedule_success_probability(country, schedule)
    return prob

  def expected_utility(self, country: Country, schedule: Schedule) -> float:
    logging.debug(self.expected_utility.__name__)
    P = self.schedule_success_probability
    DR = self.discounted_reward
    c = country
    s = schedule
    C = SCHEDULE_FAILED_IMPACT
    return float((P(s) * DR(c, s)) + ((1-P(s)) * C))
