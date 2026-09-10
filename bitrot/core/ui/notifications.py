import pygame
from core.data.config import GAME_WIDTH, WHITE, font_12
from core.entities.npc.npc_dialog import NPCDialog

def add_notification(game, title, message, duration=5000, target_tab='Quests'):
    if not hasattr(game, 'notifications'): 
        game.notifications = []
        
    game.notifications.append({
        'title': title,
        'message': message,
        'remaining_time': duration,
        'rect': None,
        'target_tab': target_tab
    })

def draw_notifications(surface, game):
    if not hasattr(game, 'notifications') or not game.notifications: 
        return
    
    mouse_pos = game._get_scaled_mouse_pos()
    active_notifications = []
    
    dynamic_w = getattr(game, 'dynamic_w', GAME_WIDTH)
    viewport_left = getattr(game, 'viewport_left_offset', 0)
    anchor_x = viewport_left + dynamic_w
    start_y = 60 
    
    for notif in game.notifications:
        title_surf = font_12.render(notif['title'], True, (255, 215, 0))
        
        lines = notif['message'].split('\n')
        max_msg_w = max([font_12.render(line, True, WHITE).get_width() for line in lines] + [0])
        
        width = max(title_surf.get_width(), max_msg_w) + 30
        height = 35 + (len(lines) * 15)
        
        # Position relative to the active game viewport anchor (No animation)
        x = anchor_x - width - 20
        
        chip_rect = pygame.Rect(x, start_y, width, height)
        notif['rect'] = chip_rect  # Save the rect so mouse.py can detect clicks
        
        # Check hover state
        is_hovered = chip_rect.collidepoint(mouse_pos)
        
        # Only tick down the timer if the mouse is NOT hovering over it
        if not is_hovered:
            notif['remaining_time'] -= getattr(game, 'dt_ms', 16)
            
        if notif['remaining_time'] > 0:
            chip_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # Highlight background and border slightly if hovered
            bg_color = (50, 50, 50, 240) if is_hovered else (30, 30, 30, 220)
            border_color = (255, 215, 0) if is_hovered else (150, 150, 150)
            
            chip_surface.fill(bg_color)
            pygame.draw.rect(chip_surface, border_color, chip_surface.get_rect(), 1, border_radius=6)
            
            surface.blit(chip_surface, (x, start_y))
            surface.blit(title_surf, (x + 15, start_y + 8))
            
            msg_y = start_y + 25
            for line in lines:
                line_surf = font_12.render(line, True, WHITE)
                surface.blit(line_surf, (x + 15, msg_y))
                msg_y += 15
            
            start_y += height + 10
            active_notifications.append(notif)
            
    game.notifications = active_notifications

def check_milestone_progress(game, m_type, entity):
    """
    Call this function whenever a milestone-related event occurs in the game.
    Example inside Zombie Death: check_milestone_progress(game, 'kill', 'zombie')
    """
    player = getattr(game, 'player', None)
    if not player: return
    
    if not hasattr(player, 'completed_milestones'):
        player.completed_milestones = []
    if not hasattr(player, 'milestone_progress'):
        player.milestone_progress = {}
        
    key = f"{m_type}_{entity}"
    player.milestone_progress[key] = player.milestone_progress.get(key, 0) + 1
    current_val = player.milestone_progress[key]
    
    if NPCDialog.MILESTONES is None:
        NPCDialog.load_dialogs(game)
        
    milestones = NPCDialog.MILESTONES or []
    
    for ms in milestones:
        if ms['type'] == m_type and ms['entity'] == entity:
            ms_name = ms.get('name', '').strip() # Clean string
            
            if ms_name not in player.completed_milestones and current_val >= ms['number']:
                # Milestone Completed!
                player.completed_milestones.append(ms_name)
                add_notification(game, ms_name, f"{ms['message']}\nCheck your quest tab", target_tab='Quests')