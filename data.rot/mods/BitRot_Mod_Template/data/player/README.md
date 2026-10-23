# Balance Player

## player/milestones.json
```json
{
    "milestones": [
        {
            "type": "kill",
            "entity": "zombie",
            "name": "First Rotter",
            "number": 1,
            "message": "First Blood!"
        },
        {
            "type": "hit",
            "entity": "static_npc",
            "name": "Was it friendly?",
            "number": 1,
            "message": "You hit a friend! It will become Hostile!"
        },
        {
            "type": "craft_craft",
            "entity": "item",
            "name": "The Builder",
            "number": 1,
            "message": "You made your first craft!"
        },
        {
            "type": "craft_repair",
            "entity": "item",
            "name": "The Fixer",
            "number": 1,
            "message": "You made your first repair!"
        },
        {
            "type": "craft_dismantle",
            "entity": "item",
            "name": "The Tweaker",
            "number": 1,
            "message": "You made your first dismantle!"
        },
        {
            "type": "days",
            "entity": "world_day",
            "number": 1,
            "name": "First day alive",
            "message": "You survived your first day."
        }
    ]
}
```

## player/player.json
```json
{
  "player": {
    "name": "Player",
    "sex": "Male",
    "traits": [],
    "stats": {
      "health": 100.0,
      "stamina": 100.0,
      "water": 100.0,
      "food": 100.0,
      "anxiety": 0.0,
      "infection": 0.0,
      "defence": 0.0
    },
    "attributes": {
      "strength": 0.0,
      "fitness": 0.0,
      "melee": 0.0,
      "ranged": 0.0,
      "maintenance": 0.0,
      "lucky": 0.0,
      "agility": 0.0,
      "intelligence": 0.0
    },
    "initial_loot": [
      { "name": "ID", "chance": 1.0 },
      { "name": "Wallet", "chance": 1.0 },
      { "name": "Cartography Sector [MAP_POS]", "chance": 1.0 },
      { "name": "38 Revolver", "chance": 1.0 },
      { "name": "Ammo Box 38", "chance": 1.0 }
    ],
    "visuals": {
      "center": "player.png",
      "left": "player_left.png",
      "right": "player_right.png"
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
      "legs": null,
      "util2": null,
      "util3": null
    },
    "recipes": []
  }
}
```

## player/progression.json
```json
{
  "progression": {
    "attributes": {
      "strength": {
        "name": "Strength",
        "image": "ui/strength.png",
        "base_xp": 750,
        "effects": [
          { "target": "unarmed_damage", "value": 0.05, "type": "multiplier_add" },
          { "target": "carry_weight", "value": 1.5, "type": "flat" }
        ]
      },
      "fitness": {
        "name": "Fitness",
        "image": "ui/fitness.png",
        "base_xp": 750,
        "effects": [
          { "target": "stamina_regen", "value": 0.01, "type": "flat" }
        ]
      },
      "melee": {
        "name": "Melee",
        "image": "ui/melee.png",
        "base_xp": 200,
        "effects": [
          { "target": "melee_damage", "value": 0.05, "type": "multiplier_add" },
          { "target": "durability_save_chance_minor", "value": 2.0, "type": "flat" }
        ]
      },
      "ranged": {
        "name": "Aiming",
        "image": "ui/range.png",
        "base_xp": 200,
        "effects": [
          { "target": "ranged_damage", "value": 0.05, "type": "multiplier_add" },
          { "target": "headshot_chance", "value": 0.015, "type": "flat" }
        ]
      },
      "maintenance": {
        "name": "Maintenance",
        "image": "ui/maintenance.png",
        "base_xp": 150,
        "effects": [
          { "target": "durability_save_chance", "value": 2.5, "type": "flat" }
        ]
      },
      "agility": {
        "name": "Agility",
        "image": "ui/agility.png",
        "base_xp": 200,
        "effects": [
          { "target": "stamina_consumption_reduction", "value": 0.01, "type": "flat" }
        ]
      },
      "lucky": {
        "name": "Luck",
        "image": "ui/lucky.png",
        "base_xp": 300,
        "effects": [
          { "target": "xp_gain", "value": 0.02, "type": "multiplier_add" }
        ]
      },
      "intelligence": {
        "name": "Intelligence",
        "image": "ui/intelligence.png",
        "base_xp": 300,
        "effects": [
          { "target": "reading_speed", "value": 0.4, "type": "flat" },
          { "target": "crafting_speed", "value": 0.2, "type": "flat" },
          { "target": "xp_gain", "value": 0.02, "type": "multiplier_add" },
          { "target": "durability_save_chance", "value": 1.0, "type": "flat" }
        ]
      }
    },
    "stats": {
      "stamina": {
        "regen_base": 0.025,
        "run_cost_base": 0.08,
        "run_drain": 0.08,
        "bed_recovery_mult": 3.0,
        "melee_cost": 0.03,
        "alert_threshold": 20.0
      },
      "health": {
        "bed_sleep_regen": 0.05,
        "alert_threshold": 40.0
      },
      "metabolism": {
        "decay_rate_seconds": 10.0
      },
      "food": {
        "decay_amount": 0.1,
        "alert_threshold": 20.0
      },
      "water": {
        "decay_amount": 0.15,
        "alert_threshold": 20.0
      },
      "anxiety": {
        "horde_gain": 0.05,
        "passive_gain": 0.001,
        "alert_threshold": 30.0
      },
      "infection": {
        "passive_gain": 0.001,
        "passive_gain_on_rain": 0.005,
        "death_threshold": 100.0,
        "alert_threshold": 70.0
      }
    }
  }
}
```

## player/quests.json
```json
{
  "quests": [
    {
      "id": "quests",
      "options": [
        {
          "id": "Quest: Mobile phone",
          "options": [
            {
              "stage": "offer",
              "player_question": "I have my ID, how to get faster to the helipoint?",
              "npc_answer": "Helipoint? That area is a mess kiddo! Best you can do is survive here.",
              "unlock_flag": "Quest: Mobile phone",
              "req_item": "[ID]",
              "dialog_type": "once",
              "priority": 100,
              "gain_xp": "[lucky:100]"
            },
            {
              "stage": "turn_in",
              "player_question": "If I have a mobile I could try to call someone...",
              "npc_answer": "Lucky for you, take my Mobile. It's useless right now.",
              "req_item": "[ID]",
              "gain_xp": "[lucky:100]",
              "dialog_type": "once",
              "award_item": "[Mobile off, Personal Data]",
              "tip": "Your ID may save your life",
              "complete_flag": "Quest: Mobile phone"
            }
          ]
        }
      ]
    }
  ]
}
```

## player/traits.json
```json
{
  "player_traits": {
    "professions": {
      "Profession_Unemployed": {
        "name": "Unemployed",
        "cost": 0,
        "tooltip": "A blank slate. No bonuses, but no deficits.",
        "disable": ["Profession_Maintenance", "Profession_CEO_assistant", "Profession_Mechanic", "Profession_Spy", "Profession_Scientist", "Profession_Nurse", "Profession_Police_Officer"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5 }
        }
      },
      "Profession_Nurse": {
        "name": "Nurse",
        "cost": 2,
        "tooltip": "Knows basic medicine and is light on their feet.",
        "disable": ["Profession_Maintenance", "Profession_CEO_assistant", "Profession_Mechanic", "Profession_Spy", "Profession_Scientist", "Profession_Unemployed", "Profession_Police_Officer"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 3, "maintenance": 1, "intelligence": 3, "lucky": 1 }
        },
        "recipe":["Survivor Guide Basic"]
      },
      "Profession_Police_Officer": {
        "name": "Police Officer",
        "cost": 4,
        "tooltip": "Proficient with firearms and moderately fit.",
        "disable": ["Profession_Maintenance", "Profession_CEO_assistant", "Profession_Mechanic", "Profession_Spy", "Profession_Scientist", "Profession_Unemployed", "Profession_Nurse"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 2, "maintenance": 1, "intelligence": 1, "ranged": 3, "lucky": 1 }
        },
        "recipe":["Survivor Guide Basic"]
      },
      "Profession_Scientist": {
        "name": "Scientist",
        "cost": 3,
        "tooltip": "High intelligence, but severely lacking in physical prowess.",
        "disable": ["Profession_Maintenance", "Profession_CEO_assistant", "Profession_Mechanic", "Profession_Spy", "Profession_Unemployed", "Profession_Nurse", "Profession_Police_Officer"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 1, "lucky": 2, "maintenance": 2, "intelligence": 5 }
        },
        "recipe":["Survivor Guide Basic"]
      },
      "Profession_Mechanic": {
        "name": "Mechanic",
        "cost": 3,
        "tooltip": "Knows how vehicles work and maintains tools well.",
        "disable": ["Profession_Maintenance", "Profession_Scientist", "Profession_CEO_assistant", "Profession_Unemployed", "Profession_Spy", "Profession_Nurse", "Profession_Police_Officer"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 2, "maintenance": 4, "intelligence": 2 }
        },
        "recipe":["Survivor Guide Basic"]
      },
      "Profession_Spy": {
        "name": "Spy",
        "cost": 4,
        "tooltip": "Highly agile and incredibly lucky.",
        "disable": ["Profession_Maintenance", "Profession_Scientist", "Profession_CEO_assistant", "Profession_Mechanic", "Profession_Unemployed", "Profession_Nurse", "Profession_Police_Officer"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 4, "lucky": 4, "maintenance": 1, "intelligence": 2 }
        },
        "recipe":["Survivor Guide Basic"]
      },
      "Profession_CEO_assistant": {
        "name": "CEO Assistant",
        "cost": 1,
        "tooltip": "Organized but inexperienced in combat.",
        "disable": ["Profession_Maintenance", "Profession_Spy", "Profession_Scientist", "Profession_Mechanic", "Profession_Unemployed", "Profession_Nurse", "Profession_Police_Officer"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 2, "lucky": 2, "maintenance": 1, "intelligence": 3 }
        },
        "recipe":["Survivor Guide Basic"]
      },
      "Profession_Maintenance": {
        "name": "Maintenance",
        "cost": 2,
        "tooltip": "Handy with tools and physical labor.",
        "disable": ["Profession_Spy", "Profession_Scientist", "Profession_Mechanic", "Profession_Unemployed", "Profession_Nurse", "Profession_Police_Officer", "Profession_CEO_assistant"],
        "attributes": {
          "level": { "strength": 5, "fitness": 5, "agility": 2, "lucky": 1, "maintenance": 3, "intelligence": 2 }
        },
        "recipe":["Survivor Guide Basic"]
      }
    },
    "traits": {
      "vaccine": {
        "name": "Vaccine",
        "cost": 2,
        "tooltip": "-20% infection rate",
        "stats": { "infection": -20 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "athletic": {
        "name": "Athletic",
        "cost": 4,
        "tooltip": "+20% stamina recovery, +10% Speed",
        "stats": { "stamina": 20 },
        "config": { "PLAYER_SPEED": 1.1, "ZOMBIE_MAX_CHUNK": 2 }
      },
      "runner": {
        "name": "Runner",
        "cost": 3,
        "tooltip": "+10% stamina recovery, +15% Speed",
        "stats": { "stamina": 10 },
        "config": { "PLAYER_SPEED": 1.15, "ZOMBIE_MAX_CHUNK": 2 }
      },
      "strong": {
        "name": "Strong",
        "cost": 4,
        "tooltip": "+1 Level and +25% XP on Strength | +1 Level and +10% XP on Fitness",
        "disable": ["fit", "weak"],
        "attributes": {
          "strength": 25,
          "fitness": 10,
          "level": { "strength": 1, "fitness": 1 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 4 }
      },
      "luck": {
        "name": "Luck",
        "cost": 2,
        "tooltip": "+1 Level and +25% XP on Luck",
        "attributes": {
          "lucky": 25,
          "level": { "lucky": 1 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "light_hands": {
        "name": "Light Hands",
        "cost": 3,
        "tooltip": "+25% XP and +2 level Agility",
        "attributes": {
          "agility": 25,
          "level": { "agility": 2 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "eagle_eyed": {
        "name": "Eagle Eyed",
        "cost": 2,
        "tooltip": "+25% Vision Radius",
        "disable": ["myopia"],
        "config": { "BASE_PLAYER_VIEW_RADIUS": 1.25, "ZOMBIE_MAX_CHUNK": 4 }
      },
      "healthy": {
        "name": "Healthy",
        "cost": 3,
        "tooltip": "-15% Damage taken",
        "stats": { "health": 15 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "rested": {
        "name": "Rested",
        "cost": 2,
        "tooltip": "+15% stamina recovery",
        "stats": { "stamina": 15 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "camel": {
        "name": "Camel",
        "cost": 2,
        "tooltip": "20% slower water decay",
        "stats": { "water": 20 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "iron_stomach": {
        "name": "Iron Stomach",
        "cost": 2,
        "tooltip": "15% slower food decay",
        "stats": { "food": 15 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "fit": {
        "name": "Fit",
        "cost": 3,
        "tooltip": "+1 Level and +25% XP Fitness",
        "attributes": {
          "fitness": 25,
          "level": { "fitness": 1 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "brawler": {
        "name": "Brawler",
        "cost": 3,
        "tooltip": "+1 Level and +25% XP Melee",
        "attributes": {
          "melee": 25,
          "level": { "melee": 1 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "shooter": {
        "name": "Shooter",
        "cost": 4,
        "tooltip": "+1 Level and +25% XP on Ranged Weapons",
        "attributes": {
          "ranged": 25,
          "level": { "ranged": 1 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "weak": {
        "name": "Weak",
        "cost": -3,
        "tooltip": "-25% XP Strength gain, -4 Level Strength",
        "disable": ["strong"],
        "attributes": {
          "strength": -25,
          "level": { "strength": -4 }
        },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "smoker": {
        "name": "Smoker",
        "cost": -2,
        "tooltip": "-15% slower recovery stamina and +15% faster increase anxiety",
        "stats": { "stamina": -15, "anxiety": 15 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "drunk": {
        "name": "Drunk",
        "cost": -2,
        "tooltip": "-15% XP Agility penalty and +15% faster increase anxiety",
        "attributes": { "agility": -15 },
        "stats": { "anxiety": 15 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "illness": {
        "name": "Illness",
        "cost": -3,
        "tooltip": "+20% infection rate",
        "stats": { "infection": 20 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "sedentary": {
        "name": "Sedentary",
        "cost": -4,
        "tooltip": "-30% stamina, -10% Speed",
        "stats": { "stamina": -30 },
        "config": { "PLAYER_SPEED": 0.9, "ZOMBIE_MAX_CHUNK": 2 }
      },
      "myopia": {
        "name": "Myopia",
        "cost": -2,
        "tooltip": "-20% Aiming XP, -35% View Radius",
        "disable": ["eagle_eyed"],
        "attributes": { "ranged": -20 },
        "config": { "BASE_PLAYER_VIEW_RADIUS": 0.65, "ZOMBIE_MAX_CHUNK": 2 }
      },
      "frail": {
        "name": "Frail",
        "cost": -3,
        "tooltip": "+15% Damage taken",
        "stats": { "health": -15 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "sleepy": {
        "name": "Sleepy",
        "cost": -2,
        "tooltip": "-20% stamina recovery",
        "stats": { "stamina": -20 },
        "config": { "ZOMBIE_MAX_CHUNK": 4 }
      },
      "high_thirst": {
        "name": "High Thirst",
        "cost": -2,
        "tooltip": "-25% water recovery",
        "stats": { "water": -25 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "sweet_tooth": {
        "name": "Sweet Tooth",
        "cost": -2,
        "tooltip": "-20% food recovery",
        "stats": { "food": -20 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "unfit": {
        "name": "Unfit",
        "cost": -3,
        "tooltip": "-25% XP Fitness level",
        "disable": ["fit", "athletic"],
        "attributes": { "fitness": -25 },
        "config": { "ZOMBIE_MAX_CHUNK": 2 }
      },
      "clumsy": {
        "name": "Clumsy",
        "cost": -3,
        "tooltip": "-25% XP Melee level, -5% Speed",
        "attributes": { "melee": -25 },
        "config": { "PLAYER_SPEED": 0.95, "ZOMBIE_MAX_CHUNK": 2 }
      }
    }
  }
}
```