
---
0.0.6.3 - commit: 764b16f
OS: Linux/Ubuntu
About: Game crash when Hostile NPCs try to break obstacle

```log
[2026-11-20 18:20:10] [CRITICAL] CRITICAL GAME CRASH DETECTED
Traceback (most recent call last):
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/game.py", line 498, in run
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/states/playing.py", line 193, in run_playing
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/entities/npc/npc.py", line 483, in update
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/entities/zombie/zombie_ai.py", line 438, in update_ai
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/entities/zombie/zombie_ai.py", line 642, in move_towards
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/entities/zombie/zombie_ai.py", line 675, in _try_attack_obstacle
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/sound_manager.py", line 181, in play_sound
  File "/tmp/onefile_2038485_237132_nitRvPe8XSA/core/sound_manager.py", line 134, in load_sound
FileNotFoundError: No such file or directory: '/tmp/onefile_2038485_237132_nitRvPe8XSA/data.rot/lib/sfx/zombie/npc_attack.ogg'.
```