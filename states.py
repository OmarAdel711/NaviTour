from enum import Enum


class State(Enum):
    IDLE = 1
    AWAITING_DESTINATION = 2
    AWAITING_START = 3
    AWAITING_TIME = 4
