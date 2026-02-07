import random

class Agent():

    def reset(self):
        raise NotImplementedError

    def act(self, observation):
        raise NotImplementedError


class RandomAgent(Agent):
    def __init__(self):
        pass

    def reset(self):
        pass

    def act(self, observation):
        phase = observation['phase']
        valid_action = observation['valid_action']
        if 'speech' in phase:
            action = ('speech', '')
        else:
            action = valid_action[random.randint(0, len(valid_action)-1)]
        return action