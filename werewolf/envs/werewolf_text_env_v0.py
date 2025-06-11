import random
from copy import deepcopy
import json, os
import numpy as np
import gym
from collections import Counter
import json

from werewolf.helper.log_utils import Log


class WerewolfTextEnvV0(gym.Env):
    def __init__(self, **kwargs):
        self.n_player = kwargs.get('n_player', 9)
        self.n_role = kwargs.get('n_role', 5)
        self.n_werewolf = kwargs.get('n_werewolf', 3)
        self.n_seer = kwargs.get('n_seer', 1)
        self.n_guard = kwargs.get('n_guard', 1)
        self.n_witch = kwargs.get('n_witch', 1)
        self.n_hunter = kwargs.get('n_hunter', 0)
        self.n_villager = kwargs.get('n_villager', 3)
        assert self.n_werewolf + self.n_seer + self.n_witch + self.n_guard + self.n_hunter + self.n_villager == self.n_player
        assert self.n_seer == 1
        assert self.n_witch <= 1
        assert self.n_hunter <= 1
        assert self.n_guard <= 1
        self.roles = (["Werewolf" for _ in range(self.n_werewolf)] + ["Seer" for _ in range(self.n_seer)] +
                      ["Guard" for _ in range(self.n_guard)] + ["Witch" for _ in range(self.n_witch)] +
                      ["Hunter" for _ in range(self.n_hunter)] + ["Villager" for _ in range(self.n_villager)])
        self.game_phase_set = ['init', 'skill_wolf', 'skill_seer', 'skill_guard', 'skill_witch', 'skill_hunter',
                               'speech', 'speech_pk', 'vote', 'vote_pk', 'end_game']

        self.game_count = 0
        self.wolf_win_count = 0

        self.werewolf_reward = kwargs.get('werewolf_reward', 1)
        self.village_reward = kwargs.get('village_reward', 1)
        self.game_log = []

        self.hunter_in_night = False
        self.hunter_in_daytime = False

        self.log_save_path = kwargs.get('log_save_path', os.path.join(os.getcwd(), 'tmp_logs'))


    def reset(self, **kwargs):
        self.game_count += 1
        if 'roles' in kwargs:
            self.roles = kwargs['roles']
        else:
            random.shuffle(self.roles)

        self.WOLF_IDX = [idx for idx, role in enumerate(self.roles) if role == 'Werewolf']
        self.SEER_IDX = self.roles.index('Seer')
        self.GUARD_IDX = self.roles.index('Guard') if 'Guard' in self.roles else -1
        self.WITCH_IDX = self.roles.index('Witch') if 'Witch' in self.roles else -1
        self.HUNTER_IDX = self.roles.index('Hunter') if 'Hunter' in self.roles else -1
        self.VILLAGER_IDX = [idx for idx, role in enumerate(self.roles) if role == 'Villager']

        self.speech_queue = []
        self.vote_queue = []
        self.day = 0
        self.day_or_night = 'day'
        self.alive = [1 for _ in range(self.n_player)]

        self.single_werewolf_kill_target = [{} for _ in range(len(self.WOLF_IDX))]
        self.werewolf_kill_decision = {}
        self.seer_check_target = {}
        self.guard_target = {}
        self.hunter_target = {}
        self.witch_heal_target = {}
        self.witch_poison_target = {}
        self.vote_target = [{} for _ in range(self.n_player)]
        self.game_log = []
        self.vote_pk_players = []


        self.phase = 'init'
        self.game_log.append(Log(viewer=[i for i in range(self.n_player)], source=-1, target=-1,
                                 content=Counter(self.roles), day=self.day,
                                 time=self.get_time(), event='game_setting'))
        self.game_log.append(Log(viewer=[-1,], source=-1, target=-1,
                                 content={idx+1: self.roles[idx] for idx in range(self.n_player)}, day=self.day,
                                 time=self.get_time(), event='god_view'))
        self.game_log.append(Log(viewer=self.WOLF_IDX, source=-1, target=self.WOLF_IDX,
                                 content={'wolf_team': self.WOLF_IDX}, day=self.day,
                                 time=self.get_time(), event='werewolf_team_info'))
        for idx, role in enumerate(self.roles):
            self.game_log.append(Log(viewer=[idx, ], source=-1, target=idx, content={'identity': self.roles[idx]},
                                     day=self.day, time=self.get_time(),
                                     event='self_identity'))


        self.hunter_in_night = False
        self.hunter_in_daytime = False


        self.current_act_idx = self.WOLF_IDX[0]
        self.phase = 'skill_wolf'
        self.day_or_night = 'night'
        observation = self.get_observation()
        return observation

    def step(self, action):
        observation, reward, done, info = self.next_phase(action)
        return observation, reward, done, info

    def next_phase(self, action):
        done = False
        reward = [0 for _ in range(self.n_player)]
        info = {}

        action = self.trans_action_agt_to_env(action)
        action_type = action[0]
        action_content = action[1]

        if self.phase == 'skill_wolf':
            assert self.current_act_idx in self.WOLF_IDX
            assert type(action_content) == int and -1 <= action_content < self.n_player 
            if action_content >= 0:
                assert self.alive[action_content] == 1

            self.single_werewolf_kill_target[self.WOLF_IDX.index(self.current_act_idx)][
                self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
            self.game_log.append(
                Log(viewer=[idx for idx in self.WOLF_IDX], source=self.current_act_idx, target=action_content,
                    content={'kill_target': action_content},
                    day=self.day, time=self.get_time(), event=self.phase))

            tmp_idx = self.WOLF_IDX.index(self.current_act_idx)
            if tmp_idx < len(self.WOLF_IDX) - 1 and self.alive[self.WOLF_IDX[tmp_idx + 1]] == 1:
                self.current_act_idx = self.WOLF_IDX[tmp_idx + 1]
                self.phase = 'skill_wolf'
            else:
                kill_candidate = [target.get(self.get_phase(self.day, self.day_or_night, 'skill_wolf'), -1) for target
                                  in self.single_werewolf_kill_target]
                kill_condidate_counter = Counter(kill_candidate)
                del kill_condidate_counter[-1]
                wolf_kill_idx = -1

                if len(kill_condidate_counter) > 0:
                    most_count = kill_condidate_counter.most_common(1)[0]
                    if list(kill_condidate_counter.values()).count(most_count[1]) > 1:
                        for i in range(len(kill_candidate) - 1, -1, -1):
                            if kill_candidate[i] != -1:
                                wolf_kill_idx = kill_candidate[i]
                                break
                    else:
                        wolf_kill_idx = most_count[0]
                self.werewolf_kill_decision[self.get_phase(self.day, self.day_or_night, self.phase)] = wolf_kill_idx
                self.game_log.append(Log(viewer=self.WOLF_IDX + ([self.WITCH_IDX] if self.WITCH_IDX != -1 else []), source=-1, target=wolf_kill_idx,
                                         content={'kill_decision': wolf_kill_idx}, day=self.day,
                                         time=self.get_time(),
                                         event='kill_decision'))

                if self.alive[self.SEER_IDX] == 1:
                    self.current_act_idx = self.SEER_IDX
                    self.phase = 'skill_seer'
                elif self.GUARD_IDX != -1 and self.alive[self.GUARD_IDX] == 1:
                    self.current_act_idx = self.GUARD_IDX
                    self.phase = 'skill_guard'
                elif self.WITCH_IDX != -1 and self.alive[self.WITCH_IDX] == 1:
                    self.current_act_idx = self.WITCH_IDX
                    self.phase = 'skill_witch'
                else:
                    reward, done, info = self.end_night()
        elif self.phase == 'skill_seer':
            assert self.current_act_idx == self.SEER_IDX
            assert type(action_content) == int and -1 <= action_content < self.n_player 
            self.seer_check_target[self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
            checked_identity = None
            if action_content>=0:
                checked_identity = 'bad' if self.roles[action_content] == 'Werewolf' else 'good'
            self.game_log.append(
                Log(viewer=[self.SEER_IDX, ], source=self.current_act_idx, target=action_content,
                    content={'cheked_identity': checked_identity},
                    day=self.day, time=self.get_time(), event=self.phase))
            if self.GUARD_IDX != -1 and self.alive[self.GUARD_IDX] == 1:
                self.current_act_idx = self.GUARD_IDX
                self.phase = 'skill_guard'
            elif self.WITCH_IDX != -1 and self.alive[self.WITCH_IDX] == 1:
                self.current_act_idx = self.WITCH_IDX
                self.phase = 'skill_witch'
            else:
                reward, done, info = self.end_night()
        elif self.phase == 'skill_guard':
            assert self.current_act_idx == self.GUARD_IDX
            assert type(action_content) == int and -1 <= action_content < self.n_player 
            self.guard_target[self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
            self.game_log.append(
                Log(viewer=[self.GUARD_IDX, ], source=self.current_act_idx, target=action_content,
                    content={'protected': action_content}, day=self.day,
                    time=self.get_time(), event=self.phase))
            if self.WITCH_IDX != -1 and self.alive[self.WITCH_IDX] == 1:
                self.current_act_idx = self.WITCH_IDX
                self.phase = 'skill_witch'
            else:
                reward, done, info = self.end_night()
        elif self.phase == 'skill_witch':
            assert self.current_act_idx == self.WITCH_IDX
            assert type(action_content) == int and -1 <= action_content < self.n_player 
            if action_type == 'witch_heal':
                assert action_content != -1
                self.witch_heal_target[self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
                self.game_log.append(
                    Log(viewer=[self.WITCH_IDX, ], source=self.current_act_idx, target=action_content,
                        content={'heal': action_content}, day=self.day,
                        time=self.get_time(), event=self.phase))
            elif action_type == 'witch_poison':
                assert action_content != -1
                self.witch_poison_target[self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
                self.game_log.append(
                    Log(viewer=[self.WITCH_IDX, ], source=self.current_act_idx, target=action_content,
                        content={'poison': action_content}, day=self.day,
                        time=self.get_time(), event=self.phase))
            elif action_type == 'witch_pass':
                self.game_log.append(
                    Log(viewer=[self.WITCH_IDX, ], source=self.current_act_idx, target=-1,
                        content={'pass': -1}, day=self.day,
                        time=self.get_time(), event=self.phase))
            else:
                raise ValueError
            reward, done, info = self.end_night()
        elif self.phase == 'skill_hunter':
            assert self.current_act_idx == self.HUNTER_IDX
            assert self.hunter_in_night or self.hunter_in_daytime
            assert action_type == 'shoot' and -1 <= action_content < self.n_player 

            self.hunter_target[self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
            if action_content != -1:
                assert self.alive[action_content] == 1
                self.alive[action_content] = 0
                self.game_log.append(
                    Log(viewer=[i for i in range(self.n_player)], source=self.current_act_idx, target=action_content,
                        content={'shoot': action_content}, day=self.day,
                        time=self.get_time(), event=self.phase))

            if self.hunter_in_night:
                self.phase = 'speech'
                tmp_speech_queue = [idx for idx, live in enumerate(self.alive) if live == 1]
                assert len(tmp_speech_queue) > 0
                speak_n = random.randint(0, len(tmp_speech_queue))
                self.speech_queue = tmp_speech_queue[speak_n:] + tmp_speech_queue[:speak_n]
                self.current_act_idx = self.speech_queue.pop(0)
            elif self.hunter_in_daytime:
                self.phase = 'skill_wolf'
                for idx in self.WOLF_IDX:
                    if self.alive[idx] == 1:
                        self.current_act_idx = idx
                        break
                self.day_or_night = 'night'
            else:
                raise ValueError
            reward, done, info = self.is_done()

        elif self.phase == 'speech' or self.phase == 'speech_pk':
            assert action_type == 'speech' or action_type == 'speech_pk'
            self.game_log.append(
                Log(viewer=[i for i in range(self.n_player)], source=self.current_act_idx,
                    target=[i for i in range(self.n_player)],
                    content={'speech_content': action_content}, day=self.day,
                    time=self.get_time(), event=self.phase))
            if len(self.speech_queue) > 0:
                self.current_act_idx = self.speech_queue.pop(0)
            else:
                self.phase = 'vote' if self.phase == 'speech' else 'vote_pk'
                if self.phase == 'vote_pk':
                    assert len(self.vote_queue) > 0
                else:
                    assert len(self.vote_queue) == 0
                    self.vote_queue = [idx for idx, live in enumerate(self.alive) if live == 1.]
                    assert len(self.vote_queue) > 0
                self.current_act_idx = self.vote_queue.pop(0)
        elif self.phase == 'vote' or self.phase == 'vote_pk':
            assert (action_type == 'vote' or action_type == 'vote_pk') and -1 <= action_content < self.n_player 
            self.game_log.append(
                Log(viewer=[-1,], source=self.current_act_idx,
                    target=action_content,
                    content={'vote_target': action_content}, day=self.day,
                    time=self.get_time(), event=self.phase))
            self.vote_target[self.current_act_idx][
                self.get_phase(self.day, self.day_or_night, self.phase)] = action_content
            if len(self.vote_queue) > 0:
                self.current_act_idx = self.vote_queue.pop(0)
            else:
                reward, done, info = self.end_vote()
        else:
            raise ValueError("Unknown game phase {}".format(self.phase))

        if done:
            self.phase = 'end_game'
            self.game_log.append(Log(viewer=[idx for idx in range(self.n_player)], source=-1, target=-1,
                                     content={'outcome': info['Werewolf']}, day=self.day, time=self.get_time(),
                                     event=self.phase))
            if self.log_save_path is not None:
                if not os.path.exists(self.log_save_path):
                    os.mkdir(self.log_save_path)
                with open(os.path.join(self.log_save_path, f'game_log.json'), 'w', encoding='utf-8') as file:
                    self.trans_obs_env_to_agt(self.game_log)
                    tmp_game_log = [log.__dict__ for log in self.game_log]
                    logs = json.dumps(tmp_game_log,ensure_ascii=False,indent=4)
                    file.write(logs)

        return self.get_observation(), reward, done, info

    def end_night(self):
        wolf_kill_idx = -1
        guard_protect_idx = -1
        witch_heal_idx = -1
        witch_poison_idx = -1

        wolf_kill_idx = self.werewolf_kill_decision.get(self.get_phase(self.day, self.day_or_night, 'skill_wolf'))

        if self.GUARD_IDX != -1:
            guard_protect_idx = self.guard_target.get(self.get_phase(self.day, self.day_or_night, 'skill_guard'), -1)
        if self.WITCH_IDX != -1:
            witch_heal_idx = self.witch_heal_target.get(self.get_phase(self.day, self.day_or_night, 'skill_witch'), -1)
            witch_poison_idx = self.witch_poison_target.get(self.get_phase(self.day, self.day_or_night, 'skill_witch'),
                                                            -1)
            assert witch_heal_idx == -1 or witch_poison_idx == -1

        dead_idx = set()
        if wolf_kill_idx != -1:
            dead_idx.add(wolf_kill_idx)
        if guard_protect_idx == wolf_kill_idx and guard_protect_idx in dead_idx:
            dead_idx.remove(guard_protect_idx)
        if witch_heal_idx == wolf_kill_idx and witch_heal_idx in dead_idx:
            dead_idx.remove(witch_heal_idx)
        if witch_heal_idx == guard_protect_idx and witch_heal_idx != -1:
            dead_idx.add(witch_heal_idx)
        if witch_poison_idx != -1:
            dead_idx.add(witch_poison_idx)

        for dead in list(dead_idx):
            self.alive[dead] = 0.

        self.game_log.append(
            Log(viewer=[i for i in range(self.n_player)], source=-1, target=list(dead_idx),
                content={'dead_list': list(dead_idx)}, day=self.day,
                time=self.get_time(), event='end_night'))

        self.day += 1
        self.day_or_night = 'day'

        if self.HUNTER_IDX in dead_idx and witch_poison_idx != self.HUNTER_IDX and self.HUNTER_IDX != -1:
            self.current_act_idx = self.HUNTER_IDX
            self.phase = 'skill_hunter'
            self.hunter_in_night = True

        else:
            self.phase = 'speech'
            tmp_speech_queue = [idx for idx, live in enumerate(self.alive) if live == 1]
            assert len(tmp_speech_queue) > 0
            speak_n = random.randint(0, len(tmp_speech_queue))
            self.speech_queue = tmp_speech_queue[speak_n:] + tmp_speech_queue[:speak_n]
            self.current_act_idx = self.speech_queue.pop(0)

        reward, done, info = self.is_done()
        return reward, done, info

    def end_vote(self):
        for log in self.game_log:
            if 'vote' in log.event:
                log.viewer = [i for i in range(self.n_player)]

        expelled_target = -1
        if self.phase == 'vote':
            vote_candidate = [target.get(self.get_phase(self.day, self.day_or_night, 'vote'), -1) for target in
                              self.vote_target]

            vote_candidate_counter = Counter(vote_candidate)
            del vote_candidate_counter[-1]
            if len(vote_candidate_counter) == 0:
                expelled_target = -1
                self.game_log.append(Log(viewer=[idx for idx in range(self.n_player)], source=-1, target=-1,
                                         content={'vote_outcome': 'all abstention'}, day=self.day,
                                         time=self.get_time(),
                                         event='end_vote'))
            else:
                most_count = vote_candidate_counter.most_common(1)[0]
                if list(vote_candidate_counter.values()).count(most_count[1]) > 1:
                    tmp_speech_queue = []
                    for player_idx, vote_count in vote_candidate_counter.items():
                        if vote_count == most_count[1]:
                            tmp_speech_queue.append(player_idx)
                    assert len(tmp_speech_queue) > 1
                    tmp_speech_queue.sort()
                    speak_n = random.randint(0, len(tmp_speech_queue))
                    self.speech_queue = tmp_speech_queue[speak_n:] + tmp_speech_queue[:speak_n]

                    self.vote_queue = []
                    for player_idx in range(self.n_player):
                        if self.alive[player_idx] == 1 and player_idx not in self.speech_queue:
                            self.vote_queue.append(player_idx)

                    if len(self.vote_queue) == 0:
                        self.vote_queue = deepcopy(self.speech_queue)
                        self.vote_queue.sort()
                    self.vote_pk_players = deepcopy(self.speech_queue)

                    self.game_log.append(Log([idx for idx in range(self.n_player)], source=-1, target=-1,
                                             content={'vote_outcome': 'draw',
                                                      'speech_queue': deepcopy(
                                                          self.speech_queue),
                                                      'vote_queue': deepcopy(
                                                          self.vote_queue)},
                                             day=self.day, time=self.get_time(),
                                             event='end_vote'))

                    self.current_act_idx = self.speech_queue.pop(0)
                    self.phase = 'speech_pk'
                    reward, done, info = self.is_done()
                    return reward, done, info
                else:
                    expelled_target = most_count[0]
        elif self.phase == 'vote_pk':
            vote_pk_candidate = [target.get(self.get_phase(self.day, self.day_or_night, 'vote_pk'), -1) for target
                                 in self.vote_target]
            vote_pk_candidate_counter = Counter(vote_pk_candidate)
            del vote_pk_candidate_counter[-1]
            if len(vote_pk_candidate_counter) == 0:
                expelled_target = -1
                self.game_log.append(Log(viewer=[idx for idx in range(self.n_player)], source=-1, target=-1,
                                         content={'vote_outcome': 'all abstention in pk'}, day=self.day,
                                         time=self.get_time(),
                                         event='end_vote'))
            else:
                most_count = vote_pk_candidate_counter.most_common(1)[0]
                if list(vote_pk_candidate_counter.values()).count(most_count[1]) > 1:
                    expelled_target = -1
                    self.game_log.append(Log(viewer=[idx for idx in range(self.n_player)], source=-1, target=-1,
                                             content={'vote_outcome': 'draw in pk'},
                                             day=self.day, time=self.get_time(),
                                             event='end_vote'))
                else:
                    expelled_target = most_count[0]
        else:
            raise ValueError


        if expelled_target != -1:
            assert self.alive[expelled_target] == 1
            self.alive[expelled_target] = 0
            self.game_log.append(
                Log(viewer=[i for i in range(self.n_player)], source=-1,
                    target=expelled_target,
                    content={'vote_outcome': expelled_target,
                             'expelled': expelled_target}, day=self.day,
                    time=self.get_time(), event='end_vote'))

        if expelled_target == self.HUNTER_IDX and self.HUNTER_IDX != -1:
            self.current_act_idx = self.HUNTER_IDX
            self.phase = 'skill_hunter'
            self.hunter_in_daytime = True

        else:
            self.phase = 'skill_wolf'
            for idx in self.WOLF_IDX:
                if self.alive[idx] == 1:
                    self.current_act_idx = idx
                    break
            self.day_or_night = 'night'

        reward, done, info = self.is_done()
        return reward, done, info

    def is_done(self):
        wolf_count = 0
        villager_count = 0
        god_count = 0
        for idx, role in enumerate(self.roles):
            if self.alive[idx] == 1.:
                if role == 'Werewolf':
                    wolf_count += 1
                elif role == 'Villager':
                    villager_count += 1
                else:
                    god_count += 1
        if wolf_count == 0:
            done = True
            reward = [-self.werewolf_reward if role == 'Werewolf' else self.village_reward for role in self.roles]
            info = {'Werewolf': -1}
        elif villager_count == 0 or god_count == 0:
            done = True
            reward = [self.werewolf_reward if role == 'Werewolf' else -self.village_reward for role in self.roles]
            info = {'Werewolf': 1}
            self.wolf_win_count += 1
        else:
            done = False
            reward = [0 for _ in range(self.n_player)]
            info = {}
        return reward, done, info

    def get_observation(self):
        game_log = []
        for log in self.game_log:
            if self.current_act_idx in log.viewer:
                game_log.append(deepcopy(log))

        if self.phase == 'skill_wolf':
            valid_action = [('kill', -1)] + [('kill', idx) for idx, is_live in enumerate(self.alive) if is_live == 1]
        elif self.phase == 'skill_seer':
            valid_action = [('check', -1)] + [('check', idx) for idx, is_live in enumerate(self.alive) if
                                              is_live == 1 and idx not in self.seer_check_target.values()]
        elif self.phase == 'skill_guard':
            valid_action = [('guard', -1)] + [('guard', idx) for idx, is_live in enumerate(self.alive) if is_live == 1]
            last_guard = self.guard_target.get(self.get_phase(self.day - 1, 'night', 'skill_guard'), None)
            if ('guard', last_guard) in valid_action:
                valid_action.remove(('guard', last_guard))
        elif self.phase == 'skill_witch':
            valid_action = [('witch_pass', -1)]
            wolf_kill_decision = self.werewolf_kill_decision.get(self.get_phase(self.day, 'night', 'skill_wolf'), -1)
            if len(self.witch_poison_target) == 0:
                valid_action += [('witch_poison', idx) for idx, is_live in enumerate(self.alive) if is_live == 1]
            if len(self.witch_heal_target) == 0 and wolf_kill_decision != -1:
                valid_action.append(('witch_heal', wolf_kill_decision))
        elif self.phase == 'skill_hunter':
            valid_action = [('shoot', -1)] + [('shoot', idx) for idx, is_live in enumerate(self.alive) if is_live == 1]
        elif self.phase == 'speech':
            valid_action = ("speech", -1)
        elif self.phase == 'speech_pk':
            valid_action = ("speech_pk", -1)
        elif self.phase == 'vote':
            valid_action = [('vote', -1)] + [('vote', idx) for idx, is_live in enumerate(self.alive) if is_live == 1]
        elif self.phase == 'vote_pk':
            assert len(self.vote_pk_players) > 0
            valid_action = [('vote_pk', -1)] + [('vote_pk', idx) for idx in self.vote_pk_players]
        elif self.phase == 'end_game':
            valid_action = []
        else:
            raise ValueError
        if 'speech' not in self.phase:
            valid_action = [(action_type, action_content + 1) for (action_type, action_content) in valid_action]

        observation = {'current_act_idx': self.current_act_idx + 1,
                       'identity': self.roles[self.current_act_idx],
                       'game_log': self.trans_obs_env_to_agt(game_log),
                       'phase': self.get_phase(self.day, self.day_or_night, self.phase),
                       'valid_action': valid_action,
                       'roles':self.roles,
                       }
        return observation

    def get_phase(self, day, day_or_night, phase):
        return str(day) + '_' + day_or_night + '_' + phase

    def get_time(self):
        return '第' + str(self.day) + '天' + ('白天' if self.day_or_night == 'day' else '夜晚')

    def trans_obs_env_to_agt(self, game_log):
        for log in game_log:
            log.viewer = [idx + 1 for idx in log.viewer]
            log.source += 1
            log.target = [idx + 1 for idx in log.target] if type(log.target) is list else log.target + 1
            for key, value in log.content.items():
                if log.event == 'game_setting' or log.event == 'end_game':
                    continue
                if type(value) is int:
                    log.content[key] += 1
                if type(value) is list:
                    log.content[key] = [idx + 1 for idx in log.content[key]]
        return game_log

    def trans_action_agt_to_env(self, action):
        assert type(action) is tuple and len(action) == 2 and type(action[0]) == str
        action_type = action[0]
        action_content = action[1]
        if not action_type.startswith('speech'):
            assert type(action_content) is int
            action_content -= 1
        action = (action_type, action_content)
        return action
