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
            
            for node in root.findall('node'):
                node_id = node.get('id')
                if not node_id: continue
                
                NPCDialog.NPC_DIALOGS[node_id] = []
                
                # --- Helper to parse options ---
                def parse_option(opt):
                    question = opt.get('player_question')
                    answer = opt.get('npc_answer')
                    
                    if question and answer:
                        req_level = opt.get('req_level')
                        gain_xp = opt.get('gain_xp')
                        dialog_type = opt.get('dialog_type')
                        
                        try:
                            priority = int(opt.get('priority', '100'))
                        except ValueError:
                            priority = 100
                            
                        unlock_flag = opt.get('unlock_flag')
                        npc_state_friendly = opt.get('npc_state_friendly')
                        npc_state_static = opt.get('npc_state_static')
                        
                        award_item = opt.get('award_item')
                        req_item = opt.get('req_item')

                        NPCDialog.NPC_DIALOGS[node_id].append({
                            'q': question, 
                            'a': answer,
                            'priority': priority,
                            'unlock_flag': unlock_flag,
                            'npc_state_friendly': npc_state_friendly,
                            'npc_state_static': npc_state_static,
                            'award_item': award_item,
                            'req_item': req_item,
                            'req_level': req_level,
                            'gain_xp': gain_xp,
                            'dialog_type': dialog_type,
                            'node_id': node_id
                        })

                # Parse standard flat <options>
                for opt in node.findall('options'):
                    parse_option(opt)
                    
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
        
        # Sort the nodes
        sorted_nodes = sorted(list(active_nodes))
        player_lucky = self.game.player.progression.get_lucky(self.game.player)

        # 3. Generate one option per active node
        for node_id in sorted_nodes:
            node_options = NPCDialog.NPC_DIALOGS.get(node_id)

            if not node_options: continue
                
            valid_options = []
            for opt in node_options:
                # Dialogs strictly never repeat
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
                
                # --- [NEW] Check req_item for Quest Turn-ins ---
                req_item = opt.get('req_item')
                if req_item:
                    # Strip the brackets to check raw name
                    item_name = req_item.replace('[', '').replace(']', '')
                    # Validate against player inventory
                    has_item = any(i.name == item_name for i in self.game.player.inventory)
                    if not has_item:
                        continue # Hide option if player doesn't have the item
                
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
            
        # 4. Format Text Wildcards
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