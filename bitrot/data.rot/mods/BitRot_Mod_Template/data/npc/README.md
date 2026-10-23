# Creating Crafts

Read and understand the craft types.

## npc/[TYPE: item_type]_[TEXT: text].xml
```json
{
  "npcs": {
    "common": {
      "spawn_weight": 55,
      "is_friendly": false,
      "is_static": false,
      "spawn_zombies_multiplier": 1,
      "name": "RANDOM",
      "sex": "RANDOM",
      "stats": {
        "health": { "min": 10, "max": 80 },
        "speed": { "min": 1, "max": 1 },
        "attack": { "min": 1, "max": 15 },
        "infection": { "min": 1, "max": 5 }
      },
      "clothes": {
        "head": null,
        "util": null,
        "hair": null,
        "facial": null,
        "feet": null,
        "hand": null,
        "body": null,
        "arms": null,
        "legs": null
      },
      "visuals": {
        "center": "npc_zombie.png",
        "left": "npc_zombie_left.png",
        "right": "npc_zombie_right.png"
      },
      "loot": [
        { "item": "Rot Meat", "chance": 1.0 },
        { "item": "Kukaroach (Bit Rot publisher)", "chance": 0.1 }
      ],
      "sound": {
        "hit": "npc_hit.ogg",
        "attack": "npc_attack.ogg",
        "dead": "npc_dead.ogg",
        "steps": "npc_steps.ogg"
      }
    }
  }
}
```