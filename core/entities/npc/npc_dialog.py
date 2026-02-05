import os
import random
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH

class NPCDialog:
    NPC_DIALOGS = None

    @staticmethod
    def load_dialogs():
        """Parses the new Node-based XML structure."""
        if NPCDialog.NPC_DIALOGS is not None: return
        
        NPCDialog.NPC_DIALOGS = {} 
        path = os.path.join(DATA_PATH, 'npc', 'dialogs.xml')
        
        if not os.path.exists(path):
            print(f"NPC Warning: Dialog file not found at {path}")
            return

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            
            # [CHANGED] Iterate through <node> elements instead of flat <options>
            for node in root.findall('node'):
                node_id = node.get('id')
                if not node_id: continue
                
                NPCDialog.NPC_DIALOGS[node_id] = []
                
                for opt in node.findall('options'):
                    question = opt.get('player_question')
                    answer = opt.get('npc_answer')
                    req_level = opt.get('req_level')
                    gain_xp = opt.get('gain_xp')
                    dialog_type = opt.get('dialog_type')
                    # Read priority (default 100) and unlock_flag
                    try:
                        priority = int(opt.get('priority', '100'))
                    except ValueError:
                        priority = 100
                        
                    unlock_flag = opt.get('unlock_flag') # Can be None
                    npc_state_friendly = opt.get('npc_state_friendly') # Returns string "true"/"false" or None
                    npc_state_static = opt.get('npc_state_static')     # Returns string "true"/"false" or None
                    award_item = opt.get('award_item')

                    if question and answer:
                        NPCDialog.NPC_DIALOGS[node_id].append({
                            'q': question, 
                            'a': answer,
                            'priority': priority,
                            'unlock_flag': unlock_flag,
                            'npc_state_friendly': npc_state_friendly, # Store raw string
                            'npc_state_static': npc_state_static,     # Store raw string
                            'award_item': award_item,
                            'req_level': req_level,
                            'gain_xp': gain_xp,
                            'dialog_type': dialog_type,
                            'node_id': node_id
                        })
                    
        except Exception as e:
            print(f"NPC Error: Could not load dialogs: {e}")

    def get_dialog_options(self):
        """Generates options based on mandatory nodes + unlocked flags."""
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs()
        
        options = []
        
        # 1. Define Mandatory Nodes
        mandatory_nodes = {"greeting", "tips", "lore_branch"}
        
        # 2. Determine Active Nodes (Mandatory + Unlocked)
        active_nodes = mandatory_nodes.union(self.dialog_flags)
        
        # [CHANGED] Sort the nodes. 
        sorted_nodes = sorted(list(active_nodes))
        player_lucky = self.game.player.progression.get_lucky(self.game.player)

        # 3. Generate one option per active node
        for node_id in sorted_nodes:
            node_options = NPCDialog.NPC_DIALOGS.get(node_id)

            if not node_options: continue
                
            # [NEW] Filter options based on Lucky level and "once" status
            valid_options = []
            for opt in node_options:
                # Check dialog_type="once"
                if opt.get('dialog_type') == 'once':
                    dialog_key = f"{node_id}_{opt['q']}"
                    if dialog_key in self.game.player.dialog_history:
                        continue

                # Check req_level="[lucky:3]"
                req = opt.get('req_level')
                if req and "[lucky:" in req:
                    try:
                        req_val = int(req.split(':')[1].replace(']', ''))
                        if player_lucky < req_val:
                            continue
                    except: pass
                
                valid_options.append(opt)

            if not valid_options: continue

            # Weighted Random Selection
            total_priority = sum(opt['priority'] for opt in valid_options)
            if total_priority <= 0: continue
            
            pick = random.randint(1, total_priority)
            current = 0
            selected_opt = None
            for opt in valid_options:
                current += opt['priority']
                if pick <= current:
                    selected_opt = opt.copy() 
                    break
            
            if selected_opt:
                options.append(selected_opt)
            
        # 4. Format Text
        inv_str = ", ".join([i.name for i in self.inventory]) if self.inventory else "nothing"
        cloth_str = ", ".join([i.name for i in self.clothes.values()]) if self.clothes else "ragged clothes"
        
        for opt in options:
            if opt['a']:
                opt['a'] = opt['a'].replace('[inventory_list]', inv_str)
                opt['a'] = opt['a'].replace('[clothes_list]', cloth_str)
                
        return options

    def unlock_node(self, node_id):
        """Unlocks a new dialog node for this NPC."""
        if node_id:
            self.dialog_flags.add(node_id)
            print(f"NPC Dialog unlocked: {node_id}")