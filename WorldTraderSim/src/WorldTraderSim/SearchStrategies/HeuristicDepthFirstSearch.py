#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations
import logging
from typing import Dict, List

from DataTypes import Action, Country, Heuristic, Node, PriorityQueue, Solution
from .SearchStrategy import SearchStrategy

class HeuristicDepthFirstSearch(SearchStrategy):

   def _expand(self, actions: List[Action], heuristic: Heuristic, node: Node) -> List[Node]:
      nodes = PriorityQueue(lambda node: heuristic.apply(node), True)
      for action in actions:
         next_state = action.apply(node.STATE)
         if next_state is not None:
            logging.debug(node.STATE)
            logging.debug(action.ACTION_TYPE)
            nodes.add(Node(next_state, node, action, 0))
      return nodes.as_list()

   def search_with_reached(self, country_states: Dict[str, Country], actions: List[Action], heuristic: Heuristic) -> Solution:
      max_frontier_length = 1
      visited = []
      node = Node(country_states, None, None, 0.0)
      frontier = [ node ]
      reached = [ node.state_hash() ]
      while len(frontier):
         node = frontier.pop()
         visited.append(node.STATE)
         if node.depth() < self.DEPTH_BOUND:
            for child in self._expand(actions, heuristic, node):
               if child.state_hash() not in reached:
                  reached.append(child.state_hash())
                  if len(frontier) < self.MAX_FRONTIER_SIZE:
                     frontier.append(child)
               else:
                  logging.debug("CHILD DETECTED AS REACHED")
            
            new_frontier_length = len(frontier)
            if new_frontier_length > max_frontier_length:
               max_frontier_length = new_frontier_length
         else:
            logging.debug(f"Max Frontier Length = {max_frontier_length}")
            return Solution(node, visited)
      logging.debug(f"Max Frontier Length {max_frontier_length}")
      return Solution(node, visited)

   def search_without_reached(self, country_states: Dict[str, Country], actions: List[Action], heuristic: Heuristic) -> Solution:
      visited = []
      frontier = [ Node(country_states, None, None, 0.0) ]
      while len(frontier):
         node = frontier.pop()
         visited.append(node.STATE)
         if node.depth() < self.DEPTH_BOUND:
            for child in self._expand(actions, heuristic, node):
               if len(frontier) < self.MAX_FRONTIER_SIZE:
                  frontier.append(child)
         else:
            return Solution(node, visited)
      return Solution(node, visited)

   def search(self, country_states: Dict[str, Country], actions: List[Action], heuristic: Heuristic) -> Solution:
      logging.debug(f"Max Frontier Size = {self.MAX_FRONTIER_SIZE}")
      search_function = self.search_without_reached if self.TREE_BASED_SEARCH else self.search_with_reached
      return search_function(country_states, actions, heuristic)
