import json
import copy
import re
import pdb

def get_length(data):
    max_ = 0
    min_ = float('inf')
    acc = 0
    for item in data:
        if item['input'] == None:
            try:
                l = len(item['instruction']) + len(item['output'])
            except:
                pdb.set_trace()
            if len(item['output']) == 0:
                pdb.set_trace()
        else:
            l = len(item['instruction']) + len(item['input']) + len(item['output'])
        if l > max_:
            max_ = l
        if l < min_:
            min_ = l
        acc += l
    avg = int(acc/len(data))
    return {"max":max_,"min":min_,"avg":avg}


'''
Werewolf Agent Visiable Info
'''
class werewolf_ins():
    def __init__(self, players, type, language="zh"):
        self.players = players
        self.type = type
        self.language = language
        self.global_id = [0 for i in range(self.players)]
        self.out = [0 for i in range(self.players)] # 出夜后的存活情况
        self.inalive = [0 for i in range(self.players)] # 入夜时的存活情况
        self.wolf_list = [] # 当前狼人玩家
        self.dead = [[]] # 夜晚死亡的玩家记录 
        self.equal = [] # 平票记录


    def get_sys_prompt(self, content):
        sys_prompt = get_sysprompt(self.players,self.type, language=self.language) # + id_prompt.format(content['player'],name[content['role']],ability[content['role']])
        return sys_prompt
    
    def get_id_prompt(self, content):
        if self.language == "zh":
            role_prompt = id_prompt.format(content['player'],name[content['role']],ability[content['role']])
        else:
            role_prompt = id_prompt_en.format(content['player'],name_en[content['role']],ability_en[content['role']])
        return role_prompt  
    
    def get_simple_prompt(self, content):
        if self.language == "zh":
            role_prompt = simple_id_prompt.format(content['player'],name[content['role']])
        else:
            role_prompt = simple_id_prompt_en.format(content['player'],name_en[content['role']])
        return role_prompt  
    
    def werewolf_infos(self):
        numbers = [index+1 for index, i in enumerate(self.global_id) if i == 'werewolf']
        return ','.join(map(str, numbers))
    
    def werewolf_visiable_discuss(self, discuss_dict, player_id):
        result = {}
        for k,v in discuss_dict.items():
            if player_id > int(k):
                result[k] = v
        return result
    
    def noone_dead(self,guard_id,heal_id,poison_id,kill_id):
        if poison_id==None:
            if kill_id!=None:
                if (heal_id == kill_id or guard_id == kill_id) and (heal_id != guard_id):
                    return True
                else:
                    return False
            else:
                if heal_id==guard_id and heal_id!=None:
                    return False
                elif kill_id == None:
                    return True
        else:
            return False

    def night_event(self,night, player_id):
        guard_id = kill_id = heal_id = poison_id = None
        seer_info = guard_info = werewolf_info = heal_info = poison_info = ""
        self.inalive = copy.deepcopy(self.out)
        for item in night:
            if item['event'] == 'inquired':
                if self.language == "zh":
                    seer_info = f"预言家查验{item['content']['player']}号玩家，{item['content']['player']}号玩家是狼人。\n" if item['content']['is_werewolf'] == True else f"预言家查验{item['content']['player']}号玩家，{item['content']['player']}号玩家不是狼人。\n"
                else:
                    seer_info = f"The Seer checked Player {item['content']['player']}, Player {item['content']['player']} is a werewolf.\n" if item['content']['is_werewolf'] == True else f"The Seer checked Player {item['content']['player']}, Player {item['content']['player']} is not a werewolf.\n"
            elif item['event'] == 'guard':
                guard_id = item['content']['player']
                if self.language == "zh":
                    guard_info = f"守卫选择守护{guard_id}号玩家。\n" if guard_id != None else "守卫选择不守护任何人。\n"
                else:
                    guard_info = f"The Guard chose to protect Player {guard_id}.\n" if guard_id != None else "The Guard chose not to protect anyone.\n"
            elif item['event'] == 'werewolf_night_discuss':
                if self.language == "zh":
                    werewolf_info = f"狼人为：{self.werewolf_infos()}号玩家。\n"
                else:
                    werewolf_info = f"The Werewolves are: Player(s) {self.werewolf_infos()}.\n"
            elif item['event'] == "werewolf_kill":
                kill_id = item['content']['target_player']
            elif item['event'] == "healed":
                heal_id = item['content']['player']
                if self.language == "zh":
                    heal_info = f"女巫对{item['content']['player']}号玩家使用了解药；" if item['content']['player'] != None else "女巫没有使用解药；"
                else:
                    heal_info = f"The Witch used the healing potion on Player {item['content']['player']}; " if item['content']['player'] != None else "The Witch did not use the healing potion; "
            elif item['event'] == 'poison':
                poison_id = item['content']['player']
                if self.language == "zh":
                    poison_info = f"女巫对{item['content']['player']}号玩家使用了毒药。\n" if item['content']['player'] != None else "女巫没有使用毒药。\n"
                else:
                    poison_info = f"The Witch used the poison potion on Player {item['content']['player']}.\n" if item['content']['player'] != None else "The Witch did not use the poison potion.\n"

        if self.noone_dead(guard_id,heal_id,poison_id,kill_id):
            if self.language == "zh":
                all_visable = "昨晚是个平安夜，没有人死亡。\n"
            else:
                all_visable = "Last night was peaceful. No one died.\n"
            dead_id = []
            self.dead.append([])
        else:
            dead_id = set()
            if poison_id != None:
                dead_id.add(poison_id)
            if kill_id != None:
                if (heal_id == kill_id or guard_id == kill_id) and (heal_id != guard_id):
                    pass
                else:
                    dead_id.add(kill_id)
            if heal_id != None and guard_id != None and heal_id == guard_id:
                dead_id.add(heal_id)
            dead_id = list(dead_id)
            if dead_id not in self.dead:
                self.dead.append(dead_id)
            dead_id = [str(j) for j in dead_id]
            # pdb.set_trace()
            s = ",".join(list(dead_id))
            if self.language == "zh":
                all_visable = f"昨晚{s}号玩家死亡。\n"
            else:
                all_visable = f"Player {s} died last night.\n"

        if self.global_id[player_id] == "simple_villager":
            return all_visable,None,copy.deepcopy(self.inalive),dead_id
        elif self.global_id[player_id] == "werewolf":
            return all_visable,werewolf_info,copy.deepcopy(self.inalive),dead_id
        elif self.global_id[player_id] == "seer":
            return all_visable,seer_info,copy.deepcopy(self.inalive),dead_id
        elif self.global_id[player_id] == "guard":
            return all_visable,guard_info,copy.deepcopy(self.inalive),dead_id
        elif self.global_id[player_id] == "witch":
            return all_visable,heal_info+poison_info,copy.deepcopy(self.inalive),dead_id
        elif self.global_id[player_id] == "hunter":
            return all_visable,None,copy.deepcopy(self.inalive),dead_id


    def night_action(self, night, player_id):
        seer_input = seer_output = guard_input = guard_output = werewolf_input = werewolf_output = heal_input =  heal_output = poison_input = poison_output = witch_input = witch_output = ""
        for item in night:
            if item['event'] == 'inquired':
                if self.language == "zh":
                    seer_input = "请结合以上角色设定、客观信息和主观信息（客观信息一定为真，主观信息包含欺骗性内容），根据投票情况分析潜在的站边关系，并进一步分析玩家隐藏的真实身份信息，选择你要查验的玩家，请用关键字为'查验'、'原因'的json格式输出，直接输出玩家编号。\n"
                    seer_output = "{{'查验':'{0}'}}".format(item['content']['player'])
                else:
                    seer_input = "Based on the role settings, objective information and subjective information (objective information is always true, subjective information may contain deceptive content), analyze potential allegiances based on voting patterns, and further analyze players' hidden true identities. Choose a player to investigate, please output in JSON format with keywords 'investigate' and 'reason', directly output the player number.\n"
                    seer_output = "{{'inquired':'{0}'}}".format(item['content']['player'])
            elif item['event'] == 'guard':
                if self.language == "zh":
                    guard_input = "请结合以上角色设定、客观信息和主观信息（客观信息一定为真，主观信息包含欺骗性内容），分析潜在的站边关系和玩家的身份信息并选择选择你要守卫的玩家，请用关键字为'守卫'、'原因'的json格式输出，直接输出玩家编号，不选择守卫任何人输出否。\n"
                    guard_output = "{{'守卫':'{0}'}}".format(item['content']['player']) if item['content']['player'] != None else "{'守卫':'否'}"
                else:
                    guard_input = "Based on the role settings, objective information and subjective information (objective information is always true, subjective information may contain deceptive content), analyze potential allegiances and players' identity information to choose a player to guard. Please output in JSON format with keywords 'guard' and 'reason', directly output the player number, output 'no' if you choose not to guard anyone.\n"
                    guard_output = "{{'guard':'{0}'}}".format(item['content']['player']) if item['content']['player'] != None else "{'guard':'no'}"
            elif item['event'] == 'werewolf_night_discuss':
                if self.language == "zh":
                    werewolf_input = "请综合角色设定、客观信息和主观信息（客观信息一定为真，主观信息不一定真实），思考在场好人的真实底牌身份，选择你要杀害的玩家，请用关键字为'杀害'、'原因'的json格式输出，直接输出玩家编号，不选择杀害任何人输出否。\n"
                    if str(player_id+1) in item['content']['decision_kill'].keys():
                        kill_number = item['content']['decision_kill'][str(player_id+1)]
                        werewolf_output = json.dumps({'杀害': str(kill_number)}, ensure_ascii=False)
                    else:
                        werewolf_output = json.dumps({'杀害':'否'}, ensure_ascii=False)
                else:
                    werewolf_input = "Based on the role settings, objective information and subjective information (objective information is always true, subjective information may not be true), consider the true hidden identities of the good players present, choose a player to kill. Please output in JSON format with keywords 'kill' and 'reason', directly output the player number, output 'no' if you choose not to kill anyone.\n"
                    if str(player_id+1) in item['content']['decision_kill'].keys():
                        kill_number = item['content']['decision_kill'][str(player_id+1)]
                        werewolf_output = json.dumps({'kill': str(kill_number)}, ensure_ascii=False)
                    else:
                        werewolf_output = json.dumps({'kill':'no'}, ensure_ascii=False)
                disscuss_kill = item['content']["decision_kill"]
            elif item['event'] == "werewolf_kill":
                if self.language == "zh":
                    kill_id = item['content']['target_player']
                    werewolf_team_output_json = json.dumps({'杀害': str(kill_id)}, ensure_ascii=False)
                    werewolf_team_output = f"狼人阵营选择击杀{kill_id}号玩家。\n"
                else:
                    kill_id = item['content']['target_player']
                    werewolf_team_output_json = json.dumps({'kill': str(kill_id)}, ensure_ascii=False)
                    werewolf_team_output = f"The werewolf team chose to kill Player {kill_id}.\n"
            elif item['event'] == "healed":
                if self.language == "zh":
                    heal_output = "是" if item['content']['player'] != None else "否"
                else:
                    heal_output = "yes" if item['content']['player'] != None else "no"
            elif item['event'] == 'poison':
                if self.language == "zh":
                    poison_output = item['content']['player'] if item['content']['player'] != None else "否"
                else:
                    poison_output = item['content']['player'] if item['content']['player'] != None else "no"
        if heal_output != "" or poison_output != "":
            if self.language == "zh":
                witch_input = "请结合以上角色设定、客观信息和主观信息（客观信息一定为真，主观信息包含欺骗性内容），思考各玩家真实的身份标签，选择解救和毒杀的对象：\n- 今晚{0}号玩家死亡，你有一瓶解药要用吗？如果使用，输出“是”，不使用则输出“否”。\n- 你有一瓶毒药要用吗？如果使用，直接输出玩家编号，不使用则输出“否”。请用关键字为“解药”、“毒药”和“原因”的json格式输出。\n".format(kill_id) if kill_id != None else "请结合以上角色设定、客观信息和主观信息（客观信息一定为真，主观信息包含欺骗性内容），思考各玩家真实的身份标签，选择解救和毒杀的对象：\n- 今晚没有玩家死亡，你有一瓶毒药要用吗？如果使用，直接输出玩家编号，不使用则输出“否”。请用关键字为“解药”、“毒药”和“原因”的json格式输出，。\n"
                heal_output = "否" if heal_output == "" else heal_output
                poison_output = "否" if poison_output == "" else poison_output
                witch_output = "{{'解药': '{0}', '毒药': '{1}'}}".format(heal_output,poison_output)
            else:
                witch_input = "Based on the role settings, objective information and subjective information (objective information is always true, subjective information may contain deceptive content), consider each player's true identity and choose targets for saving and poisoning:\n- Tonight player number {0} died, do you want to use your healing potion? Output 'yes' if you want to use it, output 'no' if not.\n- Do you want to use your poison potion? If using, directly output the player number, if not, output 'no'. Please output in JSON format with keywords 'heal', 'poison' and 'reason'.\n".format(kill_id) if kill_id != None else "Based on the role settings, objective information and subjective information (objective information is always true, subjective information may contain deceptive content), consider each player's true identity and choose targets for saving and poisoning:\n- Tonight no player died. Do you want to use your poison potion? If using, directly output the player number, if not, output 'no'. Please output in JSON format with keywords 'heal', 'poison' and 'reason'.\n"
                heal_output = "no" if heal_output == "" else heal_output
                poison_output = "no" if poison_output == "" else poison_output
                witch_output = "{{'heal': '{0}', 'poison': '{1}'}}".format(heal_output,poison_output)
        
        if self.global_id[player_id] == "simple_villager":
            return None
        elif self.global_id[player_id] == "werewolf":
            # return {"action":"kill","god":werewolf_input,"target":werewolf_output,"team_target":werewolf_team_output}
            return {"action":"kill","god":werewolf_input,"target":werewolf_team_output_json ,"team_target":werewolf_team_output,"thisplayer_target":werewolf_output, "discuss_kill":self.werewolf_visiable_discuss(disscuss_kill, player_id+1)}
        elif self.global_id[player_id] == "seer":
            return {"action":"inquired","god":seer_input,"target":seer_output}
        elif self.global_id[player_id] == "guard":
            return {"action":"guard","god":guard_input,"target":guard_output}
        elif self.global_id[player_id] == "witch":
            if witch_output == "":
                if self.language == "zh":
                    witch_output = "{'解药': '否', '毒药': '否'}"
                else:
                    witch_output = "{'heal': 'no', 'poison': 'no'}"
            return {"action":"witch","god":witch_input,"target":witch_output}


    def speech_intention(self,intent):
        if self.language == "zh":
            intention = "本轮发言包含如下判断和意图：\n"
            if intent["call_for_vote"] != []:
                intention += f"我提议投票给{intent['call_for_vote'][0]}号玩家。"
            for k,v in intent['identity_label'].items():
                if v[0] == "NA":
                    continue
                guess = '或'.join(map(str, [name[value] for value in v]))
                intention += f"{k}号玩家是{guess}。\n"
            if intent["self_present"][0] != "NA":
                intention += f'我想展现出{name[intent["self_present"][0]]}身份\n'
        else:
            intention = "This round's speech contains the following judgments and intentions:\n"
            if intent["call_for_vote"] != []:
                intention += f"I propose to vote for player number {intent['call_for_vote'][0]}."
            for k,v in intent['identity_label'].items():
                if v[0] == "NA":
                    continue
                guess = ' or '.join(map(str, [name[value] for value in v]))
                intention += f"Player {k} is {guess}.\n"
            if intent["self_present"][0] != "NA":
                intention += f'I want to present myself as a {name[intent["self_present"][0]]}\n'
        return intention
    
    def vote_info(self,content):
        if self.language == "zh":
            string = f"根据上述观察，可以做出如下分析：{content['reason']}\n"
        else:
            string = f"Based on the above observations, the following analysis can be made: {content['reason']}\n"
        return string

    def vote_action(self,content):
        if content['voted_to_player'] == None:
            tar = "弃票" if self.language == "zh" else "abstain"
        else:
            tar = content['voted_to_player']
        if self.language == "zh":
            player_vote = "请选择你投票出局的玩家，直接输出编号数字，比如1。如果弃票，请输出'弃票'。\n",
        else:
            player_vote = "Please choose the player you want to vote out by entering their number (e.g., 1). If you want to abstain, enter 'abstain'.\n"
        return {
                "action": "vote",
                "player_vote": player_vote,
                "target": f"{tar}"
                }

    def all_player_vote_info(self,content):
        s = ""
        for k, v in content.items():
            if self.language == "zh":
                s += f"{k}号玩家投给：{v}号玩家；\n"
            else:
                s += f"Player #{k} voted for Player #{v}.\n"
        return s


    def get_past_speech(self,speech,player):
        cache = []
        for i in speech:
            if i['player'] == player:
                break
            else:
                cache.append(i)
        return cache


    def vote_results(self,content):
        vote = [0 for i in range(self.players)]
        for k,v in content.items():
            vote[v-1] += 1
        # self.out[vote.index(max(vote))] = -1 
        vote_out_player_list = [vote_index for vote_index in range(len(vote)) if vote[vote_index] == max(vote)]
        if len(vote_out_player_list) == 1:
            vote_out_player = vote_out_player_list[0]
            if self.language == "zh":
                vote_out_info = f"{vote.index(max(vote))+1}号玩家被投票出局。\n"
            else:
                vote_out_info = f"Player #{vote.index(max(vote))+1} was voted out.\n"
        else:
            vote_out_player = None
            equal_vote_player = ""
            for player in vote_out_player_list:
                equal_vote_player += str(player+1) + "，"
            if self.language == "zh":
                vote_out_info = f"{equal_vote_player[:-1]}号玩家平票，进入平票PK阶段。\n"
            else:
                vote_out_info = f"Players {equal_vote_player[:-1]} have tied votes, entering tie-breaker phase.\n"
        equal_player_list = [i+1 for i in vote_out_player_list]
        return vote_out_player, equal_player_list, vote_out_info


    def get_night_strategy(self, strategy):
        if not strategy.endswith("\n"):
            strategy += "\n"
        # 使用正则表达式匹配“**下一轮晚上**:”和“**下一轮白天发言思路**：”之间的文本
        night_text_search = re.search(r'\*\*下一轮晚上\*\*(.*?)\*\*下一轮白天发言思路\*\*：', strategy, re.DOTALL)
        sub_night_text_search = re.search(r'下一轮晚上：(.*?)下一轮白天发言思路：', strategy, re.DOTALL)
        sub2_night_text_search = re.search(r'\*\*下一轮晚上\*\*：(.*?)\n', strategy, re.DOTALL)
        if night_text_search or sub_night_text_search or sub2_night_text_search:
            if night_text_search:
                night_text = night_text_search.group(1).strip() 
            elif sub2_night_text_search:
                night_text = sub2_night_text_search.group(1).strip() 
            else:
                night_text = sub_night_text_search.group(1).strip()
            if '-' in night_text:
                night_text = night_text.split('-')[1].strip()
        else:
            night_text = None
        return night_text


    def get_day_strategy(self,strategy):
        # 使用正则表达式匹配白天发言思路的文本
        if self.language == "zh":
            day_text_search = re.search(r'\*\*下一轮白天发言思路\*\*：(.*?)$', strategy)
        else:
            day_text_search = re.search(r'\*\*Thoughts on speaking during the next round in the daytime\*\*：(.*?)$', strategy)
        if day_text_search:
            day_text = day_text_search.group(1).strip()
        else:
            day_text = None
        return day_text

    def note_info(self,note,player,round):
        for item in note:
            if item['content']['player'] == player:
                for i in item['content']['context']:
                    if i['round'] == round:
                        return {"note":remove_subjective_judgment(i['notes'], language=self.language),"future_night_strategy":self.get_night_strategy(i['future_strategy']),"future_day_strategy":self.get_day_strategy(i['future_strategy'])} 
    
    def shoot_info(self,index,shoot_index,hunter_player,target_player):
        if self.language == "zh":
            shoot_god = '''请综合角色设定、客观信息和主观信息（客观信息一定为真，主观信息不一定真实），思考并推测在场玩家的真实身份，选择你要开枪带走的玩家，请用关键字为'击杀'、‘原因‘的json格式输出，不选择击杀任何人输出否。'''
        else:
            shoot_god = '''Please analyze the role settings, objective information, and subjective information (objective information is always true, while subjective information may not be true) to deduce the true identities of the players present. Choose a player you want to shoot and eliminate. Please output in JSON format using the keywords 'kill' and 'reason'. If you choose not to eliminate anyone, output 'no'.'''

        if target_player != None:
            if self.language == "zh":
                shoot_info = f"{hunter_player}号玩家出局，开枪带走{target_player}号玩家。"
            else:
                shoot_info = f"Player {hunter_player} is eliminated and shoots Player {target_player}."
            if index-shoot_index>1:
                action_type = 2 # 白天被公投出局
            else:
                action_type = 1 # 夜晚被杀出局
        else:
            shoot_info = None
            if index-shoot_index>1:
                action_type = -2 # 白天被公投不开枪
            else:
                action_type = -1 # 夜晚被杀不开枪
        if target_player == None:
            return action_type, shoot_info, shoot_god, "否"
        return action_type, shoot_info, shoot_god, str(target_player)
        
    # prepare visable data for each player
    def visable_data(self, event, note):
        id_player = [[] for _ in range(self.players)]
        index = 0
        index_vote = -99
        while index < len(event):
            item = event[index]
            if item['event'] == 'roles':
                id_player[item['content']['player']-1].append({"event":"sys_prompt" ,"info":self.get_sys_prompt(item['content']),"role":f"{item['content']['role']}", "role_setting": self.get_id_prompt(item['content']), "role_number": item['content']['player'], "role_simple_des": self.get_simple_prompt(item['content'])})
                self.global_id[item['content']['player']-1] = f"{item['content']['role']}"
                index += 1
            elif item['event'] == 'cycle_round':
                round_num = item['content']['round']
                visible_event = {}
                past_speech = []
                index2 = index + 1
                while event[index2]['event'] != 'cycle_round'  and  index2 < len(event)-1:
                    index2 += 1
                    if event[index2+1]['event'] == 'end':
                        break
                for i in range(self.players):
                    if self.out[i] == 0 or (i+1 in self.dead[-1]):
                        all_visble, role_visable, innight_alive, dead_list = self.night_event(event[index:index2+1],i)
                        visible_event[str(i)] = {"night":{"all_visble":all_visble,"role_visable":role_visable,"action":self.night_action(event[index:index2+1],i), "alive": innight_alive}}
                if len(dead_list) != 0:
                    for j in dead_list:
                        id_player[int(j)-1].append({"round":round_num,"content":copy.deepcopy(visible_event[str(int(j)-1)])})
                        self.out[int(j)-1] = -1
                index = index2 + 1
                index_cycle_round = copy.deepcopy(index)
            elif item['event'] == 'shoot':
                hunter_player = item['content']['player']
                target_player = item['content']['shoot_player']
                action_type, shoot_info, god, target_player_str = self.shoot_info(index, index_cycle_round, hunter_player, target_player)
                shoot_reason = item['content']['reason']
                # if action_type == 1:
                for i in range(self.players):
                    if self.out[i] == 0:
                        visible_event[str(i)]['day'] = {"shoot_or_not":action_type,"shoot_info":{"shoot_visiable": shoot_info,"shoot_reason": shoot_reason,"hunter_player":hunter_player,"target_player":target_player_str,"god":god},"alive":copy.deepcopy(self.out)}   
                if index - index_vote == 1: # 以枪击结束当前轮次
                    for i in range(self.players):
                        if self.out[i] == 0:
                            id_player[i].pop()
                            id_player[i].append({"round":round_num,"content":copy.deepcopy(visible_event[str(i)])})
                elif target_player != None:
                    id_player[target_player-1].append({"round":round_num,"content":copy.deepcopy(visible_event[str(target_player-1)])})  
                if target_player != None: self.out[target_player-1] = -1     
                index += 1
            elif item['event'] == 'speech':
                past_speech.append({"player":item['content']['player'],"content":item['content']['context']})
                speech_summary = event[index+1]
                call_for_vote = speech_summary["content"]["call_for_vote"]
                speech_person_label = speech_summary["content"]["identity_label"]
                self_present_label = speech_summary["content"]["self_present"]
                if "perona" in event[index]["content"]:
                    persona_dict = event[index]["content"]["perona"]
                else:
                    persona_dict = None
                # if len(self.get_past_speech(past_speech,item['content']['player'])) == sum([i==0 for i in self.out]):
                #     index += 2
                #     continue
                if self.out[item['content']['player']-1] == 0:
                    if len(past_speech) <= sum([True for i in self.out if i==0]):
                        visible_event[str(item['content']['player']-1)]["speech"] = {"past_speech":self.get_past_speech(past_speech,item['content']['player']),"all_speech":past_speech,"info":item['content']['context'], "alive": copy.deepcopy(self.out), "call_for_vote": call_for_vote, "speech_person_label": speech_person_label, "self_present_label": self_present_label, "persona": persona_dict}
                    else:
                        visible_event[str(item['content']['player']-1)]["speech"] = {"past_speech":self.get_past_speech(past_speech[sum([True for i in self.out if i==0]):],item['content']['player']),"all_speech":past_speech,"info":item['content']['context'], "alive": copy.deepcopy(self.out), "call_for_vote": call_for_vote, "speech_person_label": speech_person_label, "self_present_label": self_present_label, "persona": persona_dict}
                index += 2
            elif item['event'] == 'voted':
                if self.out[item['content']['player']-1] == 0:
                    visible_event[str(item['content']['player']-1)]["note"] = {"info":self.note_info(note,item['content']['player'],round_num)}
                    visible_event[str(item['content']['player']-1)]["vote"] = {"info":self.vote_info(item['content']), "action":self.vote_action(item['content']), "alive": copy.deepcopy(self.out)}
                index += 1
            elif item['event'] == 'vote_results':
                for i in range(self.players):
                    if self.out[i] == 0:
                        vote_out_player, equal_vote_player, vote_out_info= self.vote_results(item['content'])
                        visible_event[str(i)]["vote_result"] = {"all_player_vote_info":self.all_player_vote_info(item['content']),"info":vote_out_info,"vote_equal_list":equal_vote_player}
                        id_player[i].append({"round":round_num,"content":copy.deepcopy(visible_event[str(i)])})
                if vote_out_player != None:
                    self.out[vote_out_player] = -1
                    # self.dead.append(vote_out_player)
                index_vote = copy.deepcopy(index)
                index += 1
            elif item['event'] == 'end':
                if index_vote+1 == index:
                    index += 1
                    continue
                for i in range(self.players):
                    if self.out[i] == 0 or (i+1 in self.dead[-1]):
                        id_player[i].append({"round":round_num,"content":copy.deepcopy(visible_event[str(i)])})
                index += 1
            else:
                index += 1
        return id_player


system_prompt='''
你现在正在玩一种叫做“狼人杀”的游戏。
在这款游戏中，玩家通常被分为两个阵营：狼人和村民。
狼人杀游戏中不同角色的玩家有不同的目标：
- 村民的目的是识别出狼人，并通过投票使他们出局。
- 对于狼人来说，他们的主要目标是隐藏他们的真实身份，在讨论中误导他人，以免被投票出局并尽可能的猎杀村民。
以下是一些基本规则：
- 身份：玩家的身份是秘密分配的。狼人彼此知道对方的身份，而村民只知道自己的身份。
- 昼夜更替：游戏有交替的白天和黑夜阶段。夜里，狼人秘密选择一名村民猎杀。白天，所有玩家讨论并投票决定他们认为是狼人的玩家，票数最多的玩家被淘汰。
- 特殊角色：游戏中有存在一些有特殊能力的角色，比如能得知玩家身份的“预言家”等。
- 获胜条件：当游戏中有一个群体实现它们的获胜条件时游戏结束。如果所有狼人被淘汰，村民就获胜。如果狼人杀死了所有普通村民或所有特殊角色，狼人就获胜。
'''

ability = {
    "seer": "你每晚可以查看一名玩家是否为狼人，你的目标是利用这些信息帮助其他人找出并淘汰所有狼人。",
    "witch": "你拥有一瓶救人的药水和一瓶毒杀的药水，你的目标是策略性利用这些能力来保护村民或淘汰狼人。",
    "guard": "你每晚可以保护一名玩家不被狼人杀害，你的目标是明智地使用这个能力来减少村民的伤亡。",
    "simple_villager": "你没有特殊能力，但你的目标是观察、讨论并投票揭示狼人的身份，并努力生存下来。",
    "werewolf": "你需要其他狼人合作，每晚选择一个村民猎杀，你的目标是隐藏你的身份，并误导其他玩家，直至狼人获得游戏的胜利。",
    "hunter": "你可以在被狼人杀害或者在白天被放逐出局后，选择翻开自己的身份牌，带走场上一位存活的玩家，你可以选择不翻牌，但是翻了牌后必须带人。你的目标是合理利用这个技能为村民消灭狼人。"
}

name = {
    "seer": "预言家",
    "witch": "女巫",
    "guard": "守卫",
    "simple_villager": "村民",
    "werewolf": "狼人",
    "hunter": "猎人"
}

ROLE_CN_MAPPING = {
    "werewolf": "狼人",
    "seer": "预言家",
    "simple_villager": "普通村民",
    "witch": "女巫",
    "guard": "守卫",
    "hunter": "猎人"
}

id_prompt = """你是{}号玩家。
你的身份是：{}。
{}""" #身份后面加上一句描述 

simple_id_prompt = '''你目前是{}号{}。'''


system_prompt_en='''
You are now playing a game called "Werewolf" (also known as "Mafia").
In this game, players are typically divided into two factions: Werewolves and Villagers.
Different roles in the Werewolf game have different objectives:
- Villagers aim to identify the werewolves and eliminate them through voting.
- For Werewolves, their main goal is to hide their true identity, mislead others during discussions to avoid being voted out, and hunt down villagers whenever possible.
Here are some basic rules:
- Identity: Players' identities are secretly assigned. Werewolves know each other's identities, while villagers only know their own identity.
- Day-Night Cycle: The game alternates between day and night phases. At night, werewolves secretly choose a villager to kill. During the day, all players discuss and vote on who they think is a werewolf, and the player with the most votes is eliminated.
- Special Roles: There are some roles with special abilities in the game, such as the "Seer" who can learn players' identities.
- Win Conditions: The game ends when one group achieves their victory conditions. Villagers win if all werewolves are eliminated. Werewolves win if they kill all regular villagers or all special roles.
'''

ability_en = {
    "seer": "Each night, you can check if one player is a werewolf. Your goal is to use this information to help others find and eliminate all werewolves.",
    "witch": "You have one healing potion and one poison potion. Your goal is to use these abilities strategically to protect villagers or eliminate werewolves.",
    "guard": "Each night, you can protect one player from being killed by werewolves. Your goal is to use this ability wisely to reduce villager casualties.",
    "simple_villager": "You have no special abilities, but your goal is to observe, discuss, and vote to reveal werewolves' identities while trying to survive.",
    "werewolf": "You need to cooperate with other werewolves to choose a villager to kill each night. Your goal is to hide your identity and mislead other players until the werewolves achieve victory.",
    "hunter": "When killed by werewolves or voted out during the day, you can choose to reveal your identity card and take one surviving player with you. You can choose not to reveal your card, but if you do reveal it, you must take someone with you. Your goal is to use this ability wisely to help villagers eliminate werewolves."
}

name_en = {
    "seer": "Seer",
    "witch": "Witch",
    "guard": "Guard",
    "simple_villager": "Villager",
    "werewolf": "Werewolf",
    "hunter": "Hunter"
}

ROLE_EN_MAPPING = {
    "werewolf": "Werewolf",
    "seer": "Seer",
    "simple_villager": "Simple Villager",
    "witch": "Witch",
    "guard": "Guard",
    "hunter": "Hunter"
}

id_prompt_en = """You are Player #{}.
Your role is: {}.
{}""" #Add a description after the identity

simple_id_prompt_en = '''You are currently Player #{}, the {}.'''

def get_sysprompt(players, type, language="zh"):
    num = players
    message = system_prompt if language=="zh" else system_prompt_en
    if  num == 9:
        if type == "guard_witch_seer":
            if language == "zh":
                message += f"""
在这个游戏中，我们有从1到9号共9名玩家 —— 6名村民和3名狼人。村民中有特殊角色，包括：
- 1位预言家：
    - 目标：预言家的目的是帮助村民识别狼人。
    - 能力：在夜晚阶段，预言家可以秘密选择一名玩家，每晚了解他的真实身份（是否为狼人）。
- 1位女巫：
    - 目标：女巫的目的是策略性地使用她的特殊能力来帮助村民。
    - 能力：女巫有一瓶解药和一瓶毒药。一旦使用，后续回合中不能再用。女巫不能在同一晚既使用解药又使用毒药。解药可以用来救一名在夜间被狼人猎杀的玩家。毒药可以淘汰一名很可能是狼人的玩家。
- 1位守卫：
    - 目标：守卫的目的是策略性地使用他的特殊能力来帮助村民。
    - 能力：守卫每晚可以保护一名玩家，防止他们受到狼人的攻击。守卫可以选择保护自己，或者选择不保护任何人，但他不能在连续两个夜晚保护同一个玩家。
其他的都是普通村民。"""
            else:
                message += f"""
In this game, we have 9 players numbered from 1 to 9 — 6 villagers and 3 werewolves. Among the villagers, there are special roles including:
- 1 Seer:
    - Objective: The Seer's purpose is to help villagers identify werewolves.
    - Ability: During the night phase, the Seer can secretly choose one player and learn their true identity (whether they are a werewolf or not) each night.
- 1 Witch:
    - Objective: The Witch's purpose is to strategically use her special abilities to help villagers.
    - Ability: The Witch has one healing potion and one poison potion. Once used, they cannot be used in subsequent rounds. The Witch cannot use both the healing potion and poison potion in the same night. The healing potion can save a player who was killed by werewolves during the night. The poison potion can eliminate a player who is likely to be a werewolf.
- 1 Guard:
    - Objective: The Guard's purpose is to strategically use his special ability to help villagers.
    - Ability: The Guard can protect one player each night from werewolf attacks. The Guard can choose to protect themselves or choose not to protect anyone, but they cannot protect the same player for two consecutive nights.
The rest are simple villagers."""
                
        elif type == "hunter_witch_seer":
            if language == "zh":
                message += f"""
在这个游戏中，我们有从1到9号共9名玩家 —— 6名村民和3名狼人。村民中有特殊角色，包括：
- 1位预言家：
    - 目标：预言家的目的是帮助村民识别狼人。
    - 能力：在夜晚阶段，预言家可以秘密选择一名玩家，每晚了解他的真实身份（是否为狼人）。
- 1位女巫：
    - 目标：女巫的目的是策略性地使用她的特殊能力来帮助村民。
    - 能力：女巫有一瓶解药和一瓶毒药。一旦使用，后续回合中不能再用。女巫不能在同一晚既使用解药又使用毒药。解药可以用来救一名在夜间被狼人猎杀的玩家。毒药可以淘汰一名很可能是狼人的玩家。
- 1位猎人：
    - 目标：猎人的目的是策略性地使用他的特殊能力帮助村民消灭狼人。
    - 能力：当猎人被狼人杀害或者在白天被放逐出局后，他可以翻开自己的身份牌并向场上任意一位活着的玩家射出一发复仇的子弹，带着这位玩家一起死亡。猎人可以选择不翻牌，但是只要翻了牌就必须带人（注意，当猎人被女巫毒杀后，不能翻牌带人）。
其他的都是普通村民。"""
            else:
                message += f"""
In this game, we have 9 players numbered from 1 to 9 — 6 villagers and 3 werewolves. Among the villagers, there are special roles including:
- 1 Seer:
    - Objective: The Seer's purpose is to help villagers identify werewolves.
    - Ability: During the night phase, the Seer can secretly choose one player and learn their true identity (whether they are a werewolf or not) each night.
- 1 Witch:
    - Objective: The Witch's purpose is to strategically use her special abilities to help villagers.
    - Ability: The Witch has one healing potion and one poison potion. Once used, they cannot be used in subsequent rounds. The Witch cannot use both the healing potion and poison potion in the same night. The healing potion can save a player who was killed by werewolves during the night. The poison potion can eliminate a player who is likely to be a werewolf.
- 1 Hunter:
    - Objective: The Hunter's purpose is to strategically use his special ability to help villagers eliminate werewolves.
    - Ability: When the Hunter is killed by werewolves or voted out during the day, they can reveal their identity card and shoot a revenge bullet at any living player, taking that player down with them. The Hunter can choose not to reveal their card, but once they reveal it, they must take someone with them (Note: if the Hunter is killed by the Witch's poison, they cannot reveal their card and take someone with them).
The rest are simple villagers."""
                
    elif num == 7:
        if type == "seer_witch":
            if language == "zh":
                message += f'''
在这个游戏中，我们有从1到7号共7名玩家 —— 5名村民和2名狼人。村民中有特殊角色，包括：
- 1位预言家：
    - 目标：预言家的目的是帮助村民识别狼人。
    - 能力：在夜晚阶段，预言家可以秘密选择一名玩家，每晚了解他的真实身份（是否为狼人）。
- 1位女巫：
    - 目标：女巫的目的是策略性地使用她的特殊能力来帮助村民。
    - 能力：女巫有一瓶解药和一瓶毒药。一旦使用，后续回合中不能再用。女巫不能在同一晚既使用解药又使用毒药。解药可以用来救一名在夜间被狼人猎杀的玩家。毒药可以淘汰一名很可能是狼人的玩家。
其他的都是普通村民。
'''
            else:
                message += '''
In this game, we have 7 players numbered from 1 to 7 — 5 villagers and 2 werewolves. Among the villagers, there are special roles including:
- 1 Seer:
    - Objective: The Seer's purpose is to help villagers identify werewolves.
    - Ability: During the night phase, the Seer can secretly choose one player and learn their true identity (whether they are a werewolf or not) each night.
- 1 Witch:
    - Objective: The Witch's purpose is to strategically use her special abilities to help villagers.
    - Ability: The Witch has one healing potion and one poison potion. Once used, they cannot be used in subsequent rounds. The Witch cannot use both the healing potion and poison potion in the same night. The healing potion can save a player who was killed by werewolves during the night. The poison potion can eliminate a player who is likely to be a werewolf.
The rest are simple villagers.
'''
        elif type == "seer_guard":
            if language == "zh":
                message += f'''
在这个游戏中，我们有从1到7号共7名玩家 —— 5名村民和2名狼人。村民中有特殊角色，包括：
- 1位预言家：
    - 目标：预言家的目的是帮助村民识别狼人。
    - 能力：在夜晚阶段，预言家可以秘密选择一名玩家，每晚了解他的真实身份（是否为狼人）。
- 1位守卫：
    - 目标：守卫的目的是策略性地使用他的特殊能力来帮助村民。
    - 能力：守卫每晚可以保护一名玩家，防止他们受到狼人的攻击。守卫可以选择保护自己，或者选择不保护任何人，但他不能在连续两个夜晚保护同一个玩家。
其他的都是普通村民。
'''
            else:
                message += '''
In this game, we have 7 players numbered from 1 to 7 — 5 villagers and 2 werewolves. Among the villagers, there are special roles including:
- 1 Seer:
    - Objective: The Seer's purpose is to help villagers identify werewolves.
    - Ability: During the night phase, the Seer can secretly choose one player and learn their true identity (whether they are a werewolf or not) each night.
- 1 Guard:
    - Objective: The Guard's purpose is to strategically use his special ability to help villagers.
    - Ability: The Guard can protect one player each night from werewolf attacks. The Guard can choose to protect himself or choose not to protect anyone, but he cannot protect the same player for two consecutive nights.
The rest are simple villagers.
'''
    return message


'''
speech
'''
def generate_persona(persona):
    for k,v in persona.items():
        name, charater = k,v
    intro = charater['特点']
    behaviour = charater['行为习惯']
    s = f"你现在需要扮演一个{name}，你的特点是：{intro}同时你的行为习惯为：{behaviour}你需要扮演该角色进行狼人杀游戏。"
    return s
    
def get_night_info(past, language="zh"):
    text = ""
    init_round = 0
    for i in past:
        night_info = i['content']['night']['all_visble']
        next_round = i['round']
        if next_round == init_round:
            continue
        if language == "zh":
            if "昨晚" in night_info:
                text += f"第{i['round']}轮{night_info[2:-2]}"
            else:
                text += f"第{i['round']}轮是平安夜"
        else:
            if "Last night" in night_info:
                text += f"Round {i['round']}: {night_info[2:-2]}"
            else:
                text += f"Round {i['round']}: It was a peaceful night."
        text += "；"
        init_round = next_round
    return text[:-1] + "。"

def get_round_speech(speech, language="zh"):
    if len(speech) == 0:
        return ""
    if language == "zh":
        s = "- 本轮所有玩家发言：\n"
    else:
        s = "- Players' speech of this round:\n"
    for item in speech:
        if language == "zh":
            s += f"**{item['player']}号玩家**：{item['content']}\n"
        else:
            s += f"**Player {item['player']}**: {item['content']}\n"
    return s

def get_all_speech(round, speech, language="zh"):
    if language == "zh":
        s = f"- 第{round}轮所有玩家发言：\n"
    else:
        s = f"- All players' speech of Round {round}:\n"
    for item in speech:
        if language == "zh":
            s += f"**{item['player']}号玩家**：{item['content']}\n"
        else:
            s += f"**Player {item['player']}**: {item['content']}\n"
    return s

def get_pk_speech(round, past_speech, current_speech, language="zh"):
    if language == "zh":
        s = f"- 本轮（第{round}轮）所有玩家发言：\n"
    else:
        s = f"- Round {round}, all players' speech:\n"
    for item in past_speech:
        if language == "zh":
            s += f"**{item['player']}号玩家**：{item['content']}\n"
        else:
            s += f"**Player {item['player']}:** {item['content']}\n"
    if len(current_speech) == 0:
        if language == "zh":
            s += "- 目前PK阶段，你是第一个发言。"
        else:
            s += "- Currently in the PK phase, you are the first to speak."
    else:
        if language == "zh":
            s += "- 当前PK阶段玩家发言：\n"
        else:
            s += "- Currently in the PK phase, players' speech:\n"
        for item in current_speech:
            if language == "zh":
                s += f"**{item['player']}号玩家**：{item['content']}\n"
            else:
                s += f"**Player {item['player']}:** {item['content']}\n"
    return s

def get_pk_round_speech(round, past_speech, current_speech):
    s = f"- 本轮（第{round}轮）所有玩家发言：\n"
    for item in past_speech:
        s += f"**{item['player']}号玩家**：{item['content']}\n"
    s += f"- 第{round}轮PK阶段所有玩家发言：\n"
    for item in current_speech:
        s += f"**{item['player']}号玩家**：{item['content']}\n"
    return s

def get_speech_order(speech, language="zh"):
    if len(speech) == 0:
        return ""
    if language== "zh":
        s = "- 本轮的发言顺序为："
    else:
        s = "- The speaking order for this round is: "
    for item in speech:
        if language=="zh":
            s += f"{item['player']}号玩家；"
        else:
            s += f"Player {item['player']}；"
    if language == "zh":
        s = s[:-1] + "。"
    else:
        s = s[:-1] + "."
    return s

def get_pk_speech_order(speech, language="zh"):
    if len(speech) == 0:
        return ""
    if language== "zh":
        s = "- PK阶段的发言顺序为："
    else:
        s = "- The speaking order for this round is: "
    for item in speech:
        if language== "zh":
            s += f"{item['player']}号玩家；"
        else:
            s += f"Player {item['player']}; "
    if language == "zh":
        s = s[:-1] + "。"
    else:
        s = s[:-1] + "."
    return s

def get_pk_info(equal_list):
    s = ""
    for player in equal_list:
        s += str(player) + "号，"
    vote_out_info = f"{s[:-1]}玩家。"
    return vote_out_info

def get_call_for_vote(call_vote_list, language="zh"):
    text = ""
    if len(call_vote_list) == 0:
        text += "无" if language == "zh" else "None"
    else:
        if language == "zh":
            call_vote_cn = [str(i) + "号玩家" for i in call_vote_list]
            text += "和".join(call_vote_cn)
        else:
            call_vote_cn = [ "Player " + str(i) for i in call_vote_list]
            text += "and ".join(call_vote_cn)
    return text

def get_speech_person_label(person_label_dict, language="zh"):
    if language == "zh":
        roles_dict = {
            "witch": "女巫", 
            "guard": "守卫", 
            "seer": "预言家", 
            "simple_villager": "村民", 
            "werewolf": "狼人", 
            "hunter": "猎人",
            "NA": "未知身份"
        }
    else:
        roles_dict = {
            "witch": "witch",
            "guard": "guard",
            "seer": "seer",
            "simple_villager": "villager",
            "werewolf": "werewolf",
            "hunter": "hunter",
            "NA": "unknown"
        }
    person_dict_cn = {}
    for item in person_label_dict:
        if language == "zh":
            current_role_label = [roles_dict[player] for player in person_label_dict[item]]
            person_dict_cn[item + "号玩家"] = "和".join(current_role_label)
        else:
            current_role_label = [roles_dict[player] for player in person_label_dict[item]]
            person_dict_cn[f"Player {item}"] = "and ".join(current_role_label)
    return person_dict_cn

def get_self_present_label(self_present, language="zh"):
    roles_dict = {
        "witch": "女巫", 
        "guard": "守卫", 
        "seer": "预言家", 
        "simple_villager": "村民", 
        "werewolf": "狼人", 
        "hunter": "猎人",
        "NA": "未知身份"
    }
    text = ""
    if len(self_present) == 0:
        if language == "zh":
            text += "未知"
        else:
            text += "Unknown"
    else:
        if language == "zh":
            present_cn = [roles_dict[label] for label in self_present]
            text += "或".join(present_cn)
        else:
            text += "or ".join(self_present)
    return text

def get_past_note_speech(past, language="zh"):
    s = ""
    # print(len(past))
    for i in past:
        if language == "zh":
            event = i['content']['night']['all_visble'] + f"你的动作为：{i['content']['night']['role_visable']}" if i['content']['night']['role_visable'] != None else i['content']['night']['all_visble']
            s += f"第{i['round']}轮发生：{event}；\n第{i['round']}轮总结：{i['content']['note']['info']['note']}；\n第{i['round']}轮投票记录：{i['content']['vote_result']['all_player_vote_info']}；\n结果：{i['content']['vote_result']['info']}\n"
        else:
            event = i['content']['night']['all_visble'] + f"Your action: {i['content']['night']['role_visable']}" if i['content']['night']['role_visable']!= None else i['content']['night']['all_visble']
            s += f"Round {i['round']}: {event};\nRound {i['round']} Note: {i['content']['note']['info']['note']};\nRound {i['round']} Vote Record: {i['content']['vote_result']['all_player_vote_info']};\nResult: {i['content']['vote_result']['info']}\n"
    return s

def get_last_night_speech(night):
    if night['role_visable'] == None:
        return f"昨晚发生：{night['all_visble']}。"
    else:
        return f"昨晚发生：{night['all_visble']}; 昨晚行动：{night['role_visable']}。\n"

def get_past_speech_speech(round, speech, language="zh"):
    if len(speech) == 0:
        return ""
    if language == "zh":
        s = f"目前是第{round}轮，本轮在你之前的玩家发言：\n"
    else:
        s = f"This is Round {round}. The player's speeches before you are:\n"
    for item in speech:
        if language == "zhe":
            s += f"**{item['player']}号玩家**：{item['content']}\n"
        else:
            s += f"**Player {item['player']}**: {item['content']}\n"
    return s

def integrate_speech(self_present, person_label, call_for_vote, speech, language="zh"):
    out_dict = {}
    if language == "zh":
        out_dict["想要展示的身份"], out_dict["身份标签"], out_dict["归票"], out_dict["发言"] = self_present, person_label, call_for_vote, speech
    else:
        out_dict["self_present"], out_dict["role_label"], out_dict["call_for_vote"], out_dict["speech"] = self_present, person_label, call_for_vote, speech
    result = json.dumps(out_dict, ensure_ascii= False)
    return result


'''
note/vote
'''
def remove_note_vote(input_string):
    vote_pattern_1 = r"\n# 我的投票：\n.*?$"
    vote_pattern_2 = r"\n# 投票\n.*?$"
    
    # 使用 re.sub 方法删除所有匹配的子字符串
    result_string = re.sub(vote_pattern_1, "", input_string)
    result_string = re.sub(vote_pattern_2, "", result_string)
    
    return result_string

def remove_note_vote_en(input_string):
    vote_pattern_1 = r"\n# My vote:\n.*?$"
    vote_pattern_2 = r"\n# Voting results:\n.*?$"
    
    # 使用 re.sub 方法删除所有匹配的子字符串
    result_string = re.sub(vote_pattern_1, "", input_string)
    result_string = re.sub(vote_pattern_2, "", result_string)
    
    return result_string

def remove_subjective_judgment(input_string, language="zh"):
    if not input_string.endswith("\n"):
        input_string += "\n"
    # 定义正则表达式模式，匹配任意身份的“主观身份判断”
    if language == "zh":
        subjective_pattern = r"\n主观身份判断：.*?\n"
    else:  
        subjective_pattern = r"\nSubjective identity assessment:\n.*?\n"
    
    # 定义正则表达式模式，匹配“本轮投票身份预测”段落
    if language == "zh":
        prediction_pattern = r"# 本轮投票身份预测\n(?:- \*\*.*?\*\*：.*?\n)+"
    else:
        prediction_pattern = r"# Identity Predictions for This Round\n(?:- \*\*.*?\*\*：.*?\n)+"
    
    
    # 使用 re.sub 方法删除所有匹配的子字符串
    result_string = re.sub(subjective_pattern, "\n", input_string)
    result_string = re.sub(prediction_pattern, "\n", result_string)
    
    return result_string

def integrate_vote(summary, reason, target, language="zh"):
    out_dict = {}
    if language == "zh":
        out_dict["笔记"], out_dict["投票原因"], out_dict["投票玩家"] = remove_note_vote(summary), reason, target
    else:
        out_dict["notes"], out_dict["voting_reason"], out_dict["voting_player"] = remove_note_vote_en(summary), reason, target
    result = json.dumps(out_dict, ensure_ascii= False)
    return result

def integrate_vote_nonote(reason, target, language="zh"):
    out_dict = {}
    if language == "zh":
        out_dict["投票原因"], out_dict["投票玩家"] = reason, target
    else:
        out_dict["voting_reason"], out_dict["voting_player"] = reason, target
    result = json.dumps(out_dict, ensure_ascii= False)
    return result

def get_live_player_vote(live_list, action_dict, werewolf_info, past, round, type, language="zh"):
    situation = ""
    if action_dict is None: action_type = "villager"
    else: action_type = action_dict["action"] 
    if action_type == "kill":
        situation += werewolf_info.split("\n")[0] + "\n- " 
    if language == "zh":
        situation += "当前存活的玩家有："
    else:
        situation += "Currently alive players are: "
    for i in range(len(live_list)):
        if live_list[i] == 0:
            if language == "zh":
                situation += f"{i+1}号，"
            else:
                situation += f"Player {i+1}, "
    if len(past) != 0 and action_type in ["guard", "inquired", "witch"]:
        if language == "zh":
            situation += "\n- 行动记录："
        else:
            situation += "\n- Action record:"
        init_round = 0
        for j in past: 
            next_round = j['round']
            if next_round == init_round:
                continue
            if language == "zh":
                situation += f"第{j['round']}轮" + j['content']['night']['role_visable'][:-1]
            else:
                situation += f"Round {j['round']} " + j['content']['night']['role_visable'][:-1]
            init_round = next_round
    elif len(past) != 0 and type in ["kill"]:
        if language == "zh":
            situation += "\n- 行动记录："
        else:
            situation += "\n- Action record:"
        init_round = 0
        for j in past: 
            next_round = j['round']
            if next_round == init_round:
                continue
            if language == "zh":
                situation += f"第{j['round']}轮" + j['content']['night']['action']["team_target"][:-1]
            else:
                situation += f"Round {j['round']}" + j['content']['night']['action']["team_target"][:-1]
            init_round = next_round
    if len(past) != 0 and (type not in ["shoot"]):
        for i in past:
            if 'day' in i['content']:
                if i['content']['day']['shoot_or_not'] == 1:  
                    situation += hunter_info(i['content']['day']['shoot_or_not'], i['round'], i['content']['day']['shoot_info']['hunter_player'], i['content']['day']['shoot_info']['target_player'])
                elif i['content']['day']['shoot_or_not'] == 2 and i['round'] < round:
                    situation += hunter_info(i['content']['day']['shoot_or_not'], i['round'], i['content']['day']['shoot_info']['hunter_player'], i['content']['day']['shoot_info']['target_player'])
    return situation 


def get_past_note_action(past, language):
    s = ""
    for i in past:
        if language == "zh":
            s += f"第{i['round']}轮总结：\n{i['content']['note']['info']['note']}；\n第{i['round']}轮投票记录：\n{i['content']['vote_result']['all_player_vote_info']}；\n结果：\n{i['content']['vote_result']['info']}\n"
            s += "请依据总结和投票记录，进行思考并选择你要执行的动作。\n"
        else:
            s += f"Round {i['round']} Summary:\n{i['content']['note']['info']['note']}；\nRound {i['round']} Vote Record:\n{i['content']['vote_result']['all_player_vote_info']}；\nResult:\n{i['content']['vote_result']['info']}\n"
            s += "Based on the summary and voting records, please think carefully and choose your action.\n"
    return s

def get_past_note(past, language="zh"):
    s = ""
    current_round = 0
    for i in past:
        next_round = i['round']
        if next_round != current_round:
            if language == "zh":
                s += f"第{i['round']}轮总结：{i['content']['note']['info']['note']}\n"
            else:
                s += f"Round {i['round']} Summary: {i['content']['note']['info']['note']}\n"
        current_round = next_round
    return s

def get_past_note_ucround(past, uc_round, language="zh"): # 限定特定轮次的笔记可以加入
    s = ""
    current_round = 0
    for i in past:
        next_round = i['round']
        if int(next_round) >= int(uc_round) - 1: # 因为第 n 轮有全部的发言，只需要加入前 n-1 轮的笔记 
            break
        if next_round != current_round:
            if language == "zh":
                s += f"第{i['round']}轮总结：{i['content']['note']['info']['note']}\n"
            else:
                s += f"Round {i['round']} Summary: {i['content']['note']['info']['note']}\n"
        current_round = next_round
    return s

def get_past_vote(past, language="zh"):
    s = ""
    current_round = 0
    for i in past:
        next_round = i['round']
        if "vote_result" in i['content']:
            if next_round == current_round:
                if language == "zh":
                    s += f"第{i['round']}轮PK阶段投票记录：{i['content']['vote_result']['all_player_vote_info']}结果：{i['content']['vote_result']['info']}"
                else:
                    s += f"Round {i['round']} PK Stage Vote Record: {i['content']['vote_result']['all_player_vote_info']} Result: {i['content']['vote_result']['info']}"
            else:
                if language == "zh":
                    s += f"第{i['round']}轮投票记录：{i['content']['vote_result']['all_player_vote_info']}结果：{i['content']['vote_result']['info']}"
                else:
                    s += f"Round {i['round']} Voting Record: {i['content']['vote_result']['all_player_vote_info']} Result: {i['content']['vote_result']['info']}"
                current_round = next_round
    return s

def get_last_note(round, last, language="zh"):
    s = ""
    if len(last) != 0:
        if language == "zh":
            s += f"- 第{round}轮你的投票理由为：\n{last['content']['vote']['info']}\n"
        else:
            s += f"- Your Voting Reason at Round {round} is:\n{last['content']['vote']['info']}\n"
    return s
    

def get_past_note_vote(past, language="zh"):
    s = ""
    if len(past) != 0:
        if language == "zh":
            s += "- 笔记记录："
        else:
            s += "- Note Record:"
    for i in past:
        if language == "zh":
            s += f"第{i['round']}轮总结：{i['content']['note']['info']['note']}；第{i['round']}轮投票记录：{i['content']['vote_result']['all_player_vote_info']}；结果：\n{i['content']['vote_result']['info']}\n"
        else:
            s += f"Round {i['round']} Summary: {i['content']['note']['info']['note']}；Round {i['round']} Vote Record: {i['content']['vote_result']['all_player_vote_info']}；Result: \n{i['content']['vote_result']['info']}\n"
    return s


'''
action
'''

def generate_reason(action_type, target, werewolf_info):
    text = ""
    if action_type == "inquired":
        text += "随机查验一名玩家"
    elif action_type == "kill":
        target_json = json.loads(target)
        text += "随机杀害一名玩家" if target_json['杀害'] not in werewolf_info.split("\n")[0] else "选择自刀，骗取女巫的解药"
    elif action_type == "guard":
        if '否' in target: text += "选择空守"
        else: text += "随机守护一名玩家"
    elif action_type == "witch":
        if target.count("否") >= 2: 
            text += "为避免狼人自刀骗药，我不选择解救"
        else: 
            try:
                json_target = json.loads(target)
                if json_target["解药"] == "否": text += "随机毒杀一名玩家"
                else: text += "对死亡的玩家使用解药"
            except:
                heal, poison = target.split(",")[0], target.split(",")[1]
                if "否" in heal: text += "随机毒杀一名玩家"
                else: text += "对死亡的玩家使用解药"
    return text

def generate_reason_en(action_type, target, werewolf_info):
    text = ""
    if action_type == "inquired":
        text += "randomly inspect a player"
    elif action_type == "kill":
        target_json = json.loads(target)
        text += "randomly kills a player" if target_json['kill'] not in werewolf_info.split("\n")[0] else "chooses to kill themselves to deceive the Witch's antidote"
    elif action_type == "guard":
        if '否' in target: text += "chooses to guard no one"
        else: text += "randomly guards a player"
    elif action_type == "witch":
        if target.count("否") >= 2: 
            text += "to avoid being deceived by werewolf's self-kill strategy, I choose not to save"
        else: 
            try:
                json_target = json.loads(target)
                if json_target["heal"] == "否": text += "randomly poison a player"
                else: text += "use antidote on the dying player"
            except:
                heal, poison = target.split(",")[0], target.split(",")[1]
                if "否" in heal: text += "randomly poison a player"
                else: text += "use antidote on the dying player"
    return text

def get_discuss_kill(dicuss_dict, language="zh"):
    dialogue = ""
    for k,v in dicuss_dict.items():
        if language == "zh":
            dialogue += f"{k}号选择杀害{v}号;"
        else:
            dialogue += f"Player {k} chooses to kill Player {v};"
    if dialogue == "":
        if language == "zh":
            return "你是第一个行动的狼人，请选择你的杀害目标。"
        else:
            return "You are the first player to choose to kill a player. Please choose your target."
    if language == "zh":
        return "狼人投票杀害目标（得票多者被杀害，若平票，编号大的狼人选择的目标被杀害）：" + dialogue
    else:
        return "Werewolves vote to kill a player (the player with the most votes is killed, if there is a tie, the wolf with the larger number chooses to kill): " + dialogue

def integrate_action(text1, text2, action_type, language="zh"):
    try: json.loads(text1.replace("'", '"'))
    except: print(text1)
    dict1 = json.loads(text1.replace("'", '"'))
    if language == "zh":
        dict1['原因'] = text2
    else:
        dict1['reason'] = text2
    result = json.dumps(dict1, ensure_ascii=False) 
    return result

def integrate_shoot(target_player, shoot_reason, language="zh"):
    out_dict = {}
    if language == "zh":
        out_dict['击杀'], out_dict['原因'] = str(target_player), shoot_reason
    else:
        out_dict['kill'], out_dict['reason'] = str(target_player), shoot_reason
    result = json.dumps(out_dict, ensure_ascii=False)
    return result


def hunter_info(shoot_type, round, hunter_player, target_player):
    s = "\n- 猎人开枪记录："
    if shoot_type == 1:
        s += f"{str(hunter_player)}号猎人在第{round}轮夜晚被杀害出局，开枪带走了{target_player}号玩家。\n"
    elif shoot_type == 2:
        s += f"{str(hunter_player)}号猎人在第{round}轮白天被投票出局，开枪带走了{target_player}号玩家。\n"
    return s

def get_live_player_action(live_list, action_type, werewolf_dicuss, werewolf_info, past, round, language="zh"):
    if language == "zh":
        action_dict = {
            "kill": '杀害',
            "heal": "解救",
            "vote": "投票",
            "guard": "守护",
            "inquired": "查验"
        }
    else:
        action_dict = {
            "kill": 'kill',
            "heal": "heal",
            "vote": "vote",
            "guard": "guard",
            "inquired": "inquired"
        }
    situation = ""
    if language == "zh":
        situation += "当前存活的玩家有："
    else:
        situation += "Current alive players are: "
    for i in range(len(live_list)):
        if live_list[i] == 0:
            if language == "zh":
                situation += f"{i+1}号，"
            else:
                situation += f"Player {i+1},"
    if action_type in action_dict:
        if language == "zh":
            situation += f"只能在以上玩家中选择进行{action_dict[action_type]}\n"
        else:
            situation += f"You can only choose from the above players to perform {action_dict[action_type]}\n"
    if action_type == "kill":
        situation += "-" + werewolf_info 
        situation += get_discuss_kill(werewolf_dicuss['discuss_kill'], language=language)
    if len(past) != 0 and action_type in ["guard", "inquired", "witch"]:
        if language == "zh":
            situation += "- 行动记录："
        else:
            situation += "- Action record:"
        for i in past: 
            if language == "zh":
                situation += f"第{i['round']}轮" + i['content']['night']['role_visable'][:-1] 
            else:
                situation += f"Round {i['round']} " + i['content']['night']['role_visable'][:-1]
    if len(past) != 0:
        for i in past:
            if 'day' in i['content'] and i['round'] < round:
                if i['content']['day']['shoot_or_not'] == 1:  
                    situation += hunter_info(i['content']['day']['shoot_or_not'], i['round'], i['content']['day']['shoot_info']['hunter_player'], i['content']['day']['shoot_info']['target_player'])
                elif i['content']['day']['shoot_or_not'] == 2:
                    situation += hunter_info(i['content']['day']['shoot_or_not'], i['round'], i['content']['day']['shoot_info']['hunter_player'], i['content']['day']['shoot_info']['target_player'])
    return situation 

# add role prediction
def get_rp_speech(speech_list, language="zh"):
    if len(speech_list) == 0:
        return ""
    s = ""
    last_round = None
    current_round = 0
    for item in speech_list:
        if "speech" not in item['content'].keys():
            continue
        current_round = item['round']
        if last_round == current_round:
            if language == "zh":
                s += f"第{current_round}轮PK阶段玩家的发言为：\n"
            else:
                s += f"All players' speech at Round {current_round}:\n"
            for speech in item['content']['speech']['all_speech'][-len(last_one['content']['vote_result']['vote_equal_list']):]:
                if language == "zh":
                    s += f"**{speech['player']}号玩家**：{speech['content']}\n"
                else:
                    s += f"**Player {speech['player']}**: {speech['content']}\n"
        else:
            if language == "zh":
                s += f"第{current_round}轮所有玩家的发言为：\n"
            else:
                s += f"All players' speech at Round {current_round}:\n"
            for speech in item['content']['speech']['all_speech']:
                if language == "zh":
                    s += f"**{speech['player']}号玩家**：{speech['content']}\n"
                else:
                    s += f"**Player {speech['player']}**: {speech['content']}\n"
        last_round = item['round']
        last_one = copy.deepcopy(item)
    return s

def integrate_rp(role_dict, language="zh"):
    out_dict = {}
    for item in role_dict:
        if language == "zh":
            current_key = f"{item}号玩家"
        else:
            current_key = f"Player {item}"
        out_dict[current_key] = role_dict[item]
    result = json.dumps(out_dict, ensure_ascii=False)
    return result