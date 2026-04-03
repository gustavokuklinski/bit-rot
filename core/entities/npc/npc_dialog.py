import os
import random
import json
from datetime import datetime
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH, CHUNK_SIZE, MAP_CHUNKS

class NPCDialog:
    NPC_DIALOGS = None
    QUESTS_FILE_PATH = None  

    PROCEDURAL_ITEM_POOL = []
    MAX_PROCEDURAL_QUESTS = 12

    @staticmethod
    def load_dialogs(game=None):
        if NPCDialog.NPC_DIALOGS is not None: return
        
        NPCDialog.NPC_DIALOGS = {} 
        path = os.path.join(DATA_PATH, 'npc', 'dialogs.xml')
        
        if not os.path.exists(path):
            print(f"NPC Warning: Dialog file not found at {path}")
            return

        fragments = {}

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            
            for node in root.findall('node'):
                node_id = node.get('id')
                if not node_id: continue
                
                # ==========================================================
                # [NEW] Intercept the procedural items pool node
                # ==========================================================
                if node_id == "proc_items_quest":
                    rqsts = [e.get('rqst_item', '').replace('[', '').replace(']', '') for e in node.findall('npc_rqst')]
                    awards = [e.get('award_item', '').replace('[', '').replace(']', '') for e in node.findall('player_award')]
                    
                    # Combine all items into a single unique pool for 1:1 swapping
                    pool = [i for i in rqsts + awards if i]
                    if pool:
                        NPCDialog.PROCEDURAL_ITEM_POOL = list(set(pool))
                    continue
                
                options_elements = node.findall('options')
                if options_elements:
                    if node_id not in NPCDialog.NPC_DIALOGS:
                        NPCDialog.NPC_DIALOGS[node_id] = []
                    
                    def parse_option(opt):
                        question = opt.get('player_question')
                        answer = opt.get('npc_answer')
                        
                        if question and answer:
                            try:
                                priority = int(opt.get('priority', '100'))
                            except ValueError:
                                priority = 100

                            NPCDialog.NPC_DIALOGS[node_id].append({
                                'q': question, 
                                'a': answer,
                                'priority': priority,
                                'unlock_flag': opt.get('unlock_flag'),
                                'npc_state_friendly': opt.get('npc_state_friendly'),
                                'npc_state_static': opt.get('npc_state_static'),
                                'award_item': opt.get('award_item'),
                                'rqst_item': opt.get('rqst_item'),
                                'complete_flag': opt.get('complete_flag'),
                                'req_item': opt.get('req_item'),
                                'req_level': opt.get('req_level'),
                                'gain_xp': opt.get('gain_xp'),
                                'dialog_type': opt.get('dialog_type'),
                                'node_id': node_id
                            })

                    for opt in options_elements:
                        parse_option(opt)
                        
                else:
                    p_elements = node.findall('player_question')
                    n_elements = node.findall('npc_answer') + node.findall('npc_awnser')
                    
                    if p_elements or n_elements:
                        fragments[node_id] = {
                            'p': [e.get('p') for e in p_elements if e.get('p')],
                            'n': [e.get('n') for e in n_elements if e.get('n')]
                        }
                        
            # ==========================================================
            # PROCEDURAL DIALOG COMPILER
            # ==========================================================
            if fragments and 'hail' in fragments and 'context' in fragments and 'end' in fragments:
                if "small_talk" not in NPCDialog.NPC_DIALOGS:
                    NPCDialog.NPC_DIALOGS["small_talk"] = []
                    
                def pick_frag(frag_dict, key):
                    lst = frag_dict.get(key, [])
                    return random.choice(lst) if lst else ""

                unique_combinations = set()
                
                for _ in range(100):
                    pq = f"{pick_frag(fragments['hail'], 'p')} {pick_frag(fragments['context'], 'p')} {pick_frag(fragments['end'], 'p')}".strip()
                    na = f"{pick_frag(fragments['hail'], 'n')} {pick_frag(fragments['context'], 'n')} {pick_frag(fragments['end'], 'n')}".strip()
                    
                    pq = " ".join(pq.split())
                    na = " ".join(na.split())
                    
                    if pq and na and (pq, na) not in unique_combinations:
                        unique_combinations.add((pq, na))
                        NPCDialog.NPC_DIALOGS["small_talk"].append({
                            'q': pq, 
                            'a': na,
                            'priority': 90,
                            'unlock_flag': None,
                            'npc_state_friendly': None,
                            'npc_state_static': None,
                            'award_item': None,
                            'rqst_item': None,
                            'complete_flag': None,
                            'req_item': None,
                            'req_level': None,
                            'gain_xp': None,
                            'dialog_type': 'procedural',
                            'node_id': 'small_talk'
                        })
                        
        except Exception as e:
            print(f"NPC Error: Could not load dialogs: {e}")

        # ==========================================================
        # DYNAMIC SAVE DIRECTORY RESOLUTION
        # ==========================================================
        if game:
            if not getattr(game, 'current_save_folder_name', None):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                game.current_save_folder_name = f"save_{timestamp}"
            
            save_path = os.path.join("game", "save", "game", game.current_save_folder_name)
            os.makedirs(save_path, exist_ok=True)
            NPCDialog.QUESTS_FILE_PATH = os.path.join(save_path, "quests.rot")
        else:
            NPCDialog.QUESTS_FILE_PATH = os.path.join(DATA_PATH, 'npc', 'quests.rot')

        quests_file = NPCDialog.QUESTS_FILE_PATH
        
        if "quest_branch" not in NPCDialog.NPC_DIALOGS:
            NPCDialog.NPC_DIALOGS["quest_branch"] = []

        if os.path.exists(quests_file):
            try:
                with open(quests_file, 'r') as f:
                    proc_data = json.load(f)
                    
                for trig in proc_data.get("triggers", []):
                    trig['dialog_type'] = ""
                for opts in proc_data.get("nodes", {}).values():
                    for opt in opts:
                        opt['dialog_type'] = ""
                        
                NPCDialog.NPC_DIALOGS["quest_branch"].extend(proc_data.get("triggers", []))
                for node_id, options in proc_data.get("nodes", {}).items():
                    NPCDialog.NPC_DIALOGS[node_id] = options
            except Exception as e:
                print(f"Error reading {quests_file}: {e}")
        else:
            proc_triggers = []
            proc_nodes = {}
            
            t_qs = fragments.get('proc_quest', {}).get('p', ["Is the survivor camp looking for any specific supplies?"])
            t_as = fragments.get('proc_quest', {}).get('n', ["Yeah, the word on the radio is we are critically low on {item}. If you find one, bring it to me. We'll trade you a {reward_item}."])
            
            e_qs = fragments.get('proc_end_quest', {}).get('p', ["I heard over the radio that you guys needed a {item}. I have one here."])
            e_as = fragments.get('proc_end_quest', {}).get('n', ["Thank god! The network sent you. Here is the {reward_item} we promised. Stay safe out there."])

            # Safety fallback if XML doesn't have the new node yet
            if not NPCDialog.PROCEDURAL_ITEM_POOL:
                NPCDialog.PROCEDURAL_ITEM_POOL = [
                    "Infection Pills", "Medical Bandage", "Plastic Bottle", "Canned Food", "Powerbank",
                    "Pistol 9mm", "Shotgun Shells", "Blueprint", "Car Key Jeep", "Vaccine"
                ]

            pool = NPCDialog.PROCEDURAL_ITEM_POOL
            
            # [NEW] Sample up to MAX distinct requested items
            request_items = random.sample(pool, min(NPCDialog.MAX_PROCEDURAL_QUESTS, len(pool)))

            for item in request_items:
                quest_node_id = f"Quest: Proc_{item}"
                
                # [NEW] Pick a random reward that is NOT the currently requested item
                possible_rewards = [r for r in pool if r != item]
                reward_item = random.choice(possible_rewards) if possible_rewards else item
                
                trigger_q = random.choice(t_qs).replace('{item}', item).replace('{reward_item}', reward_item)
                trigger_a = random.choice(t_as).replace('{item}', item).replace('{reward_item}', reward_item)
                
                end_q = random.choice(e_qs).replace('{item}', item).replace('{reward_item}', reward_item)
                end_a = random.choice(e_as).replace('{item}', item).replace('{reward_item}', reward_item)
                
                trigger_opt = {
                    'q': trigger_q,
                    'a': trigger_a,
                    'priority': 15,
                    'unlock_flag': quest_node_id,
                    'npc_state_friendly': None,
                    'npc_state_static': None,
                    'award_item': None,
                    'rqst_item': None,
                    'complete_flag': None,
                    'req_item': None,
                    'req_level': None,
                    'gain_xp': "[lucky:20]",
                    'dialog_type': "", 
                    'node_id': "quest_branch"
                }
                
                node_opts = [{
                    'q': end_q,
                    'a': end_a,
                    'priority': 100,
                    'unlock_flag': None,
                    'npc_state_friendly': None,
                    'npc_state_static': None,
                    'award_item': f"[{reward_item}]",
                    'rqst_item': f"[{item}]",
                    'req_item': f"[{item}]",
                    'complete_flag': quest_node_id,
                    'req_level': None,
                    'gain_xp': "[lucky:100]",
                    'dialog_type': "", 
                    'node_id': quest_node_id
                }]
                
                NPCDialog.NPC_DIALOGS["quest_branch"].append(trigger_opt)
                NPCDialog.NPC_DIALOGS[quest_node_id] = node_opts
                
                proc_triggers.append(trigger_opt)
                proc_nodes[quest_node_id] = node_opts
                
            try:
                with open(quests_file, 'w') as f:
                    json.dump({"triggers": proc_triggers, "nodes": proc_nodes}, f, indent=4)
            except Exception as e:
                print(f"Error saving {quests_file}: {e}")

    def get_dialog_options(self):
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs(getattr(self, 'game', None))
        
        options = []
        
        mandatory_nodes = {"greeting", "small_talk", "tips", "lore_branch", "quest_branch"}
        active_nodes = mandatory_nodes.union(self.dialog_flags)

        if hasattr(self.game.player, 'quests') and self.game.player.quests:
            active_nodes.update(self.game.player.quests)
        
        sorted_nodes = sorted(list(active_nodes))
        player_lucky = self.game.player.progression.get_lucky(self.game.player)

        completed_quests = getattr(self.game.player, 'completed_quests', [])
        active_quests = getattr(self.game.player, 'quests', [])
        
        completed_procs = [q for q in completed_quests if str(q).startswith("Quest: Proc_")]
        
        # [NEW] Clear up quests once the dynamic limit is hit
        if len(completed_procs) >= NPCDialog.MAX_PROCEDURAL_QUESTS:
            for q in completed_procs:
                if q in completed_quests: completed_quests.remove(q)
                if q in active_quests: active_quests.remove(q)
        
        active_story_quests = [q for q in active_quests if str(q).startswith("Quest:") and "Proc_" not in str(q) and q not in completed_quests]
        active_procedural_quests = [q for q in active_quests if str(q).startswith("Quest: Proc_") and q not in completed_quests]
                         
        has_active_story_quest = len(active_story_quests) > 0
        has_active_procedural_quest = len(active_procedural_quests) > 0
        mobile_quest_done = "Quest: Mobile phone" in completed_quests

        for node_id in sorted_nodes:
            node_options = NPCDialog.NPC_DIALOGS.get(node_id)

            if not node_options: continue
                
            valid_options = []
            for opt in node_options:
                
                unlock = opt.get('unlock_flag', '')
                is_procedural = "Proc_" in str(unlock) or "Proc_" in str(node_id) or opt.get('dialog_type') == 'procedural'
                
                if not is_procedural:
                    dialog_key = f"{node_id}_{opt['q']}"
                    if hasattr(self.game.player, 'dialog_history') and dialog_key in self.game.player.dialog_history:
                        continue

                req = opt.get('req_level')
                if req and "[lucky:" in req:
                    try:
                        req_val = int(req.split(':')[1].replace(']', ''))
                        if player_lucky < req_val:
                            continue
                    except: pass
                
                def player_has_item(item_name):
                    if any(i and i.name == item_name for i in self.game.player.inventory): return True
                    if any(i and i.name == item_name for i in self.game.player.belt): return True
                    if any(i and i.name == item_name for i in self.game.player.clothes.values()): return True
                    return False

                req_item = opt.get('req_item')
                if req_item:
                    item_names = [i.strip() for i in req_item.replace('[', '').replace(']', '').split(',')]
                    if not all(player_has_item(name) for name in item_names):
                        continue

                rqst_item = opt.get('rqst_item')
                if rqst_item:
                    item_names = [i.strip() for i in rqst_item.replace('[', '').replace(']', '').split(',')]
                    if not any(player_has_item(name) for name in item_names):
                        continue
                        
                is_quest_starter = unlock and str(unlock).startswith("Quest:")

                if is_quest_starter:
                    if is_procedural:
                        if has_active_procedural_quest:
                            continue
                    else:
                        if has_active_story_quest:
                            continue
                        if not mobile_quest_done and unlock != "Quest: Mobile phone":
                            continue
                
                valid_options.append(opt)

            if not valid_options: continue

            if str(node_id).startswith("Quest:"):
                if node_id in completed_quests:
                    continue
                for opt in valid_options:
                    c_opt = opt.copy()
                    c_opt['priority'] = 1100 
                    options.append(c_opt)
                    
            elif str(node_id) == "quest_branch":
                story_starters = [o for o in valid_options if "Proc_" not in str(o.get('unlock_flag', ''))]
                proc_starters = [o for o in valid_options if "Proc_" in str(o.get('unlock_flag', ''))]
                
                proc_starters = [o for o in proc_starters if o.get('unlock_flag') not in completed_quests]
                
                if story_starters:
                    weights = [int(o.get('priority', 100)) for o in story_starters]
                    chosen_story = random.choices(story_starters, weights=weights, k=1)[0].copy() 
                    chosen_story['priority'] = 1000  
                    options.append(chosen_story)
                    
                if proc_starters:
                    chosen_proc = random.choice(proc_starters).copy()
                    chosen_proc['priority'] = 999 
                    options.append(chosen_proc)
                    
            elif str(node_id) == "small_talk":
                k_val = min(1, len(valid_options))
                chosen_opts = random.sample(valid_options, k_val)
                for chosen_opt in chosen_opts:
                    c_opt = chosen_opt.copy()
                    c_opt['priority'] = 60 
                    options.append(c_opt)
                    
            else:
                weights = [int(opt.get('priority', 100)) for opt in valid_options]
                chosen_opt = random.choices(valid_options, weights=weights, k=1)[0].copy()
                
                if node_id == "greeting":
                    chosen_opt['priority'] = 100 
                elif node_id == "lore_branch":
                    chosen_opt['priority'] = 80  
                elif node_id == "tips":
                    chosen_opt['priority'] = 40  
                    
                options.append(chosen_opt)
            
        inv_str = ", ".join([i.name for i in self.inventory]) if self.inventory else "nothing"
        cloth_str = ", ".join([i.name for i in self.clothes.values()]) if self.clothes else "ragged clothes"
        
        for opt in options:
            if opt['a']:
                opt['a'] = opt['a'].replace('[inventory_list]', inv_str)
                opt['a'] = opt['a'].replace('[clothes_list]', cloth_str)
                
        options.sort(key=lambda x: int(x.get('priority', 100)), reverse=True)
                
        return options

    def unlock_node(self, node_id):
        if node_id:
            self.dialog_flags.add(node_id)
            print(f"NPC Dialog unlocked: {node_id}")
            
            if hasattr(self.game.player, 'quests'):
                if node_id not in self.game.player.quests:
                    self.game.player.quests.append(node_id)