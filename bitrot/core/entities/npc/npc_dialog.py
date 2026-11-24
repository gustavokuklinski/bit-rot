# core/entities/npc/npc_dialog.py

import os
import json
import random
from core.data.config import DATA_PATH

class NPCDialog:
    NPC_DIALOGS = None
    MILESTONES = None # Class variable for Milestones

    QUEST_META = {}

    @staticmethod
    def load_dialogs(game=None):
        if NPCDialog.NPC_DIALOGS is not None and NPCDialog.MILESTONES is not None: 
            return
        
        from core.systems.mod_manager import mod_manager

        NPCDialog.NPC_DIALOGS = {} 
        NPCDialog.MILESTONES = []
        NPCDialog.QUEST_META = {}
        
        # 1. Load Milestones JSON
        milestones_path = mod_manager.get_override_path(os.path.join(DATA_PATH, 'player', 'milestones.json'))
        if os.path.exists(milestones_path):
            try:
                with open(milestones_path, 'r', encoding='utf-8') as f:
                    ms_data = json.load(f)
                    for ms in ms_data.get('milestones', []):
                        NPCDialog.MILESTONES.append({
                            'is_milestone': True,
                            'type': ms.get('type'),
                            'entity': ms.get('entity'),
                            'name': ms.get('name'),
                            'number': int(ms.get('number', 1)),
                            'message': ms.get('message')
                        })
            except Exception as e:
                print(f"NPC Error: Could not load milestones.json: {e}")

        # Helper to process mapped options for dialogues and quests
        def process_options(node_id, options_list):
            if node_id not in NPCDialog.NPC_DIALOGS:
                NPCDialog.NPC_DIALOGS[node_id] = []
            
            for opt in options_list:
                question = opt.get('player_question')
                answer = opt.get('npc_answer')
                if question and answer:
                    try:
                        priority = int(opt.get('priority', 100))
                    except (ValueError, TypeError):
                        priority = 100

                    NPCDialog.NPC_DIALOGS[node_id].append({
                        'q': question, 
                        'a': answer,
                        'priority': priority,
                        'stage': opt.get('stage'),
                        'tip': opt.get('tip'),
                        'unlock_flag': opt.get('unlock_flag'),
                        'award_item': opt.get('award_item'),
                        'rqst_item': opt.get('rqst_item'),
                        'complete_flag': opt.get('complete_flag'),
                        'req_item': opt.get('req_item'),
                        'req_level': opt.get('req_level'),
                        'gain_xp': opt.get('gain_xp'),
                        'dialog_type': opt.get('dialog_type'),
                        'node_id': node_id
                    })

        # 2. Load Quests JSON
        quests_path = mod_manager.get_override_path(os.path.join(DATA_PATH, 'player', 'quests.json'))
        if os.path.exists(quests_path):
            try:
                with open(quests_path, 'r', encoding='utf-8') as f:
                    q_data = json.load(f)
                    for q_root in q_data.get('quests', []):
                        for quest_node in q_root.get('options', []):
                            node_id = quest_node.get('id')
                            options = quest_node.get('options', [])
                            if node_id and options:
                                if str(node_id).startswith("Quest:") and node_id in NPCDialog.NPC_DIALOGS:
                                    continue
                                if str(node_id).startswith("Quest:"):
                                    NPCDialog.QUEST_META[node_id] = {
                                        'saved': bool(quest_node.get('saved', False)),
                                        'assign_npc': quest_node.get('assign_npc')
                                    }
                                process_options(node_id, options)
            except Exception as e:
                print(f"NPC Error: Could not load quests.json: {e}")

        # 3. Load arbitrary dialogs (tips, chats, lore, etc.)
        dialogs_dir = os.path.join(DATA_PATH, 'npc_dialogs')
        if os.path.exists(dialogs_dir):
            for root_dir, _, full_paths in mod_manager.vfs_walk(dialogs_dir):
                for filepath in full_paths:
                    if filepath.endswith('.json'):
                        filename = os.path.basename(filepath)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            dialog_data = json.load(f)
                            # Iterate through root objects mapping to our config format
                            for root_key, nodes in dialog_data.items():
                                if isinstance(nodes, list):
                                    for node in nodes:
                                        if not isinstance(node, dict):
                                            continue
                                        node_id = node.get('id')
                                        options = node.get('options', [])
                                        if node_id and options:
                                            process_options(node_id, options)
                    except Exception as e:
                        print(f"NPC Error: Could not load dialog file {filename}: {e}")

    def get_dialog_options(self):
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs(getattr(self, 'game', None))
        
        options = []
        
        def _is_lobby_npc():
            if getattr(self, 'is_at_lobby', False) or getattr(self, 'saved', False):
                return True
            gen = getattr(self.game, 'generator', None)
            lobby_chunk = getattr(gen, 'lobby_chunk', None) if gen else None
            if lobby_chunk is not None and getattr(self, 'layer', 1) == 1 and getattr(self, 'is_friendly', False):
                lobby_map = f"map_L1_{lobby_chunk[0]}_{lobby_chunk[1]}_map.csv"
                cur_map = getattr(self.game.map_manager, 'current_map_filename', '')
                npc_map = getattr(self, 'map_filename', '') or cur_map
                if npc_map == lobby_map:
                    return True
            return False

        is_lobby_npc = _is_lobby_npc()
        completed_quests = getattr(self.game.player, 'completed_quests', [])
        active_quests = getattr(self.game.player, 'quests', [])
        quest_assignments = getattr(self.game.player, 'quest_assignments', {})

        def _quest_belongs_to_self(q_node_id):
            q_title = str(q_node_id)[6:].strip() if str(q_node_id).startswith("Quest:") else str(q_node_id)
            info = quest_assignments.get(q_node_id) or quest_assignments.get(q_title)
            if info:
                assigned_id = info.get('npc_id')
                assigned_name = info.get('npc_name')
                if assigned_id:
                    return getattr(self, 'id', None) == assigned_id
                if assigned_name and assigned_name != "[NPC_NAME_HERE]":
                    return getattr(self, 'name', None) == assigned_name
            meta = NPCDialog.QUEST_META.get(q_node_id, {})
            static_npc = meta.get('assign_npc')
            if static_npc and str(static_npc).strip() not in ("", "[NPC_NAME_HERE]"):
                return getattr(self, 'name', None) == str(static_npc).strip()
            return True

        if is_lobby_npc:
            mandatory_nodes = {"greeting", "tips", "lore_branch", "quest_branch"}
            active_nodes = mandatory_nodes.union(self.dialog_flags)

            if active_quests:
                active_nodes.update(active_quests)

            # Include uncompleted Quest nodes assigned to this NPC or unassigned
            for n_id in NPCDialog.NPC_DIALOGS.keys():
                if str(n_id).startswith("Quest:"):
                    quest_title = str(n_id)[6:].strip()
                    if n_id not in completed_quests and quest_title not in completed_quests:
                        if _quest_belongs_to_self(n_id):
                            active_nodes.add(n_id)
        else:
            # World NPCs are only allowed Tip and Gossip (plus Greeting)
            mandatory_nodes = {"greeting", "tips", "lore_branch"}
            active_nodes = mandatory_nodes.union(
                f for f in self.dialog_flags
                if not str(f).startswith("Quest:") and str(f) != "quest_branch"
            )
        
        sorted_nodes = sorted(list(active_nodes))
        player_lucky = self.game.player.progression.get_lucky(self.game.player)

        def is_dialog_item_match(it_name, target):
            it_name = it_name.strip().lower()
            target = target.strip().lower()
            if it_name == target:
                return True
            if target == "id":
                return it_name.startswith("id:") or it_name.startswith("id ") or it_name == "id card"
            # Support Mobile on/off interchangeably for quest checks
            if target in ("mobile", "mobile off", "mobile on") and "mobile" in it_name:
                return True
            if target in it_name and len(target) >= 3:
                return True
            return False

        def player_has_item(item_name):
            target = item_name.strip().lower()
            def check_list(items):
                if not items: return False
                for it in items:
                    if not it: continue
                    it_name = getattr(it, 'name', '').strip().lower()
                    if is_dialog_item_match(it_name, target):
                        return True
                    if hasattr(it, 'inventory') and it.inventory:
                        if check_list(it.inventory):
                            return True
                return False

            if check_list(self.game.player.inventory): return True
            if check_list(self.game.player.belt): return True
            if check_list(list(self.game.player.clothes.values())): return True
            return False

        for node_id in sorted_nodes:
            node_options = NPCDialog.NPC_DIALOGS.get(node_id)
            if not node_options: 
                continue

            is_quest_node = str(node_id).startswith("Quest:")
            quest_name = str(node_id)[6:].strip() if is_quest_node else ""
            is_quest_active = is_quest_node and ((node_id in active_quests) or (quest_name in active_quests))
            is_quest_completed = is_quest_node and ((node_id in completed_quests) or (quest_name in completed_quests))

            if is_quest_completed:
                continue
                
            if is_quest_node and not _quest_belongs_to_self(node_id):
                continue

            valid_options = []
            for opt in node_options:
                stage = opt.get('stage')

                # Stage lifecycle:
                # - When quest is NOT active: only show stage="offer"
                # - When quest IS active: only show stage="turn_in"
                if is_quest_node:
                    if not is_quest_active:
                        if stage == 'turn_in':
                            continue
                        if stage is None and (opt.get('complete_flag') or opt.get('rqst_item')):
                            continue
                    else:
                        if stage == 'offer':
                            continue
                        if stage is None and opt.get('unlock_flag') and not opt.get('complete_flag'):
                            continue

                if opt.get('dialog_type') == 'once':
                    dialog_key = f"{node_id}_{opt['q']}"
                    if hasattr(self.game.player, 'dialog_history') and dialog_key in self.game.player.dialog_history:
                        continue

                req = opt.get('req_level')
                if req and "[lucky:" in req:
                    try:
                        req_val = int(req.split(':')[1].replace(']', ''))
                        if player_lucky < req_val:
                            continue
                    except Exception: 
                        pass

                req_item = opt.get('req_item')
                if req_item:
                    item_names = [i.strip() for i in req_item.replace('[', '').replace(']', '').split(',') if i.strip()]
                    if not any(player_has_item(name) for name in item_names):
                        continue

                rqst_item = opt.get('rqst_item')
                if rqst_item:
                    item_names = [i.strip() for i in rqst_item.replace('[', '').replace(']', '').split(',') if i.strip()]
                    if not any(player_has_item(name) for name in item_names):
                        continue
                
                valid_options.append(opt)

            if not valid_options: 
                continue

            if is_quest_node:
                for opt in valid_options:
                    c_opt = opt.copy()
                    # Turn-in options get highest priority (1100); offer options keep their XML priority
                    if c_opt.get('stage') == 'turn_in' or c_opt.get('complete_flag'):
                        c_opt['priority'] = max(1100, int(opt.get('priority', 1100)))
                    else:
                        c_opt['priority'] = int(opt.get('priority', 100))
                    options.append(c_opt)
                    
            elif str(node_id) == "quest_branch":
                story_starters = [
                    o for o in valid_options
                    if o.get('unlock_flag') not in completed_quests
                    and o.get('unlock_flag') not in active_quests
                    and _quest_belongs_to_self(o.get('unlock_flag', ''))
                ]
                if story_starters:
                    weights = [int(o.get('priority', 100)) for o in story_starters]
                    chosen_story = random.choices(story_starters, weights=weights, k=1)[0].copy() 
                    chosen_story['priority'] = 1000  
                    options.append(chosen_story)
                    
            elif node_id in ("greeting", "tips", "lore_branch"):
                weights = [int(opt.get('priority', 100)) for opt in valid_options]
                chosen_opt = random.choices(valid_options, weights=weights, k=1)[0].copy()
                
                if node_id == "greeting":
                    chosen_opt['priority'] = 100 
                elif node_id == "lore_branch":
                    chosen_opt['priority'] = 80  
                elif node_id == "tips":
                    chosen_opt['priority'] = 40  
                    
                options.append(chosen_opt)
            else:
                for opt in valid_options:
                    c_opt = opt.copy()
                    c_opt['priority'] = c_opt.get('priority', 90)
                    options.append(c_opt)
            
        inv_str = ", ".join([i.name for i in self.inventory]) if self.inventory else "nothing"
        cloth_str = ", ".join([i.name for i in self.clothes.values()]) if self.clothes else "ragged clothes"
        
        for opt in options:
            npc_name_str = getattr(self, 'name', 'Survivor')
            if opt.get('q'):
                opt['q'] = opt['q'].replace('[NPC_NAME_HERE]', npc_name_str)
            if opt.get('a'):
                opt['a'] = opt['a'].replace('[inventory_list]', inv_str)
                opt['a'] = opt['a'].replace('[clothes_list]', cloth_str)
                opt['a'] = opt['a'].replace('[NPC_NAME_HERE]', npc_name_str)
            if opt.get('tip'):
                opt['tip'] = opt['tip'].replace('[NPC_NAME_HERE]', npc_name_str)
                
        options.sort(key=lambda x: int(x.get('priority', 100)), reverse=True)
        return options

    def unlock_node(self, node_id):
        if node_id:
            self.dialog_flags.add(node_id)
            print(f"NPC Dialog unlocked: {node_id}")
            
            if hasattr(self.game.player, 'quests'):
                if node_id not in self.game.player.quests:
                    self.game.player.quests.append(node_id)