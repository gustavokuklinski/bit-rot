# core/entities/npc/npc_dialog.py

import os
import random
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH

class NPCDialog:
    NPC_DIALOGS = None
    MILESTONES = None # Class variable for Milestones

    @staticmethod
    def load_dialogs(game=None):
        if NPCDialog.NPC_DIALOGS is not None and NPCDialog.MILESTONES is not None: 
            return
        
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.NPC_DIALOGS = {} 
            
        NPCDialog.MILESTONES = []
        
        dialogs_dir = os.path.join(DATA_PATH, 'npc_dialogs')
        if not os.path.exists(dialogs_dir):
            print(f"NPC Warning: Dialogs directory not found at {dialogs_dir}")
            return

        for filename in os.listdir(dialogs_dir):
            if filename.endswith('.xml'):
                filepath = os.path.join(dialogs_dir, filename)
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    
                    for node in root.iter('node'):
                        node_id = node.get('id')
                        if not node_id: 
                            continue
                        
                        # ==========================================================
                        # Intercept the milestones node
                        # ==========================================================
                        if node_id == "milestones":
                            for ms in node.iter('milestone'):
                                NPCDialog.MILESTONES.append({
                                    'is_milestone': True,
                                    'type': ms.get('type'),
                                    'entity': ms.get('entity'),
                                    'name': ms.get('name'),
                                    'number': int(ms.get('number', 1)),
                                    'message': ms.get('message')
                                })
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
                except Exception as e:
                    print(f"NPC Error: Could not load dialog file {filename}: {e}")

    def get_dialog_options(self):
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs(getattr(self, 'game', None))
        
        options = []
        
        # Mandatory starter categories and any unlocked story/lore flags
        mandatory_nodes = {"greeting", "tips", "lore_branch", "quest_branch"}
        active_nodes = mandatory_nodes.union(self.dialog_flags)

        if hasattr(self.game.player, 'quests') and self.game.player.quests:
            active_nodes.update(self.game.player.quests)
        
        sorted_nodes = sorted(list(active_nodes))
        player_lucky = self.game.player.progression.get_lucky(self.game.player)

        completed_quests = getattr(self.game.player, 'completed_quests', [])
        active_quests = getattr(self.game.player, 'quests', [])
        
        active_story_quests = [q for q in active_quests if str(q).startswith("Quest:") and q not in completed_quests]
        has_active_story_quest = len(active_story_quests) > 0

        for node_id in sorted_nodes:
            node_options = NPCDialog.NPC_DIALOGS.get(node_id)
            if not node_options: 
                continue
                
            valid_options = []
            for opt in node_options:
                unlock = opt.get('unlock_flag', '')
                
                # FIX 1: ONLY filter out if this dialogue is explicitly marked as "once"
                if opt.get('dialog_type') == 'once':
                    dialog_key = f"{node_id}_{opt['q']}"
                    if hasattr(self.game.player, 'dialog_history') and dialog_key in self.game.player.dialog_history:
                        continue

                # Skill requirement check
                req = opt.get('req_level')
                if req and "[lucky:" in req:
                    try:
                        req_val = int(req.split(':')[1].replace(']', ''))
                        if player_lucky < req_val:
                            continue
                    except Exception: 
                        pass
                
                # FIX 2: Deep recursive check that searches inventory, belt, clothes, and containers
                def is_dialog_item_match(it_name, target):
                    it_name = it_name.strip().lower()
                    target = target.strip().lower()
                    if it_name == target:
                        return True
                    if target == "id":
                        return it_name.startswith("id:") or it_name.startswith("id ") or it_name == "id card"
                    if target in it_name and len(target) >= 3:
                        return True
                    return False

                # Deep recursive check that searches inventory, belt, clothes, and containers
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
                        
                # FIX 3: Do not block quest starters with mobile_quest_done check
                is_quest_starter = unlock and str(unlock).startswith("Quest:")
                if is_quest_starter:
                    if has_active_story_quest:
                        continue
                
                valid_options.append(opt)

            if not valid_options: 
                continue

            if str(node_id).startswith("Quest:"):
                if node_id in completed_quests:
                    continue
                for opt in valid_options:
                    c_opt = opt.copy()
                    c_opt['priority'] = 1100 
                    options.append(c_opt)
                    
            elif str(node_id) == "quest_branch":
                story_starters = [o for o in valid_options if o.get('unlock_flag') not in completed_quests]
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
                # FIX 4: For custom/unlocked dialogue nodes, append ALL valid options
                for opt in valid_options:
                    c_opt = opt.copy()
                    c_opt['priority'] = c_opt.get('priority', 90)
                    options.append(c_opt)
            
        inv_str = ", ".join([i.name for i in self.inventory]) if self.inventory else "nothing"
        cloth_str = ", ".join([i.name for i in self.clothes.values()]) if self.clothes else "ragged clothes"
        
        for opt in options:
            if opt.get('a'):
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