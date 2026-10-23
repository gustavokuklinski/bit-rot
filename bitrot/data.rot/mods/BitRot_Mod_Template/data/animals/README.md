# Creating Animal

```json
{
  "animals": {
    "rat": {
      "name": "Rat",
      "type": "animal",
      "attack_player": false,
      "spawn_weight": 100,
      "spawn_layer": ["L1", "L2", "L3"],
      "spawn_zombies_multiplier": 1,
      "capacity": 3,
      "stats": {
        "health": { "min": 10, "max": 20 },
        "speed": { "min": 0.5, "max": 0.8 },
        "attack": { "min": 1, "max": 5 },
        "infection": { "min": 5, "max": 15 }
      },
      "visuals": {
        "center": "rat.png",
        "left": "rat.png",
        "right": "rat.png"
      },
      "loot": [
        { "item": "Rot Meat", "chance": 1.0 },
        { "item": "Kukaroach (Bit Rot publisher)", "chance": 1.0 }
      ],
      "sound": {
        "hit": "animal_rat_hit.ogg",
        "attack": "animal_rat_attack.ogg",
        "dead": "animal_dead.ogg",
        "steps": "animal_rat_steps.ogg"
      }
    }
  }
}
```