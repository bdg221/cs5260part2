#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard Libraries
from __future__ import annotations
import hashlib
import json
from typing import Dict, Any
from uuid import UUID, uuid4

# Local Modules
from .Action import Action
from .Country import Country

class Node(object):

   ID: UUID
   STATE: Dict[str, Country]
   STATE_HASH: str
   PARENT: Node
   PARENT_ACTION: Action
   PATH_COST: float

   def __init__(self, state: Dict[str, Country], parent: Node, parent_action: Action, path_cost: float) -> None:
      super().__init__()
      self.ID = uuid4()
      self.STATE = state
      self.STATE_HASH = None
      self.PARENT = parent
      self.PARENT_ACTION = parent_action
      self.PATH_COST = path_cost
      self.DEPTH = None

   def __eq__(self, other: Node) -> bool:
      return self.state_hash() == other.state_hash()

   def state_hash(self) -> str:
      if self.STATE_HASH:
         return self.STATE_HASH

      json_state = {}
      for name, country in self.STATE.items():
         json_state[name] = dict(country)

      dhash = hashlib.md5()
      encoded = json.dumps(json_state, sort_keys=True).encode()
      dhash.update(encoded)

      self.STATE_HASH = dhash.hexdigest()
      return self.STATE_HASH

   def depth(self):
      if self.DEPTH:
         return self.DEPTH

      node_count = 1
      current_node = self.PARENT
      while current_node:
         node_count += 1
         current_node = current_node.PARENT
      self.DEPTH = node_count

      return self.DEPTH
