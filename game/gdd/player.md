### Player

Player template.
File located at: ```game/data/zombie/zombie.xml```

```xml

```

### Player Mechanics

| Mechanic       | Stat / Action           | Value & Calculation                                                                                                                                | Source File(s)                   |   |
|----------------|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|---|
| Core Stats     | Health (HP)             | Regenerates 0.01 per tick. This regen rate is reduced by infection. If food or water is 0, health decays by 5.0 per cycle.                         | player_progression.py, player.py |   |
|                | Stamina                 | Consumed by running at 0.08 per tick. Regenerates 0.03 + (Fitness Level * 0.1) per tick when not moving. Max stamina is capped by infection level. | player_progression.py, input.py  |   |
|                | Food                    | Decays by FOOD_DECAY_AMOUNT every DECAY_RATE_SECONDS.                                                                                              | player.py                        |   |
|                | Water                   | Decays by WATER_DECAY_AMOUNT every DECAY_RATE_SECONDS. Auto-drinks from inventory if below AUTO_DRINK_THRESHOLD.                                   | player.py                        |   |
|                | Infection               | Passively increases by 0.005 per tick if > 0. At 100, health drops to 1 (death).                                                                   | player_progression.py            |   |
|                | Anxiety                 | Passively increases by 0.001. If > 5 zombies are nearby, it increases by 0.05 instead.                                                             | player_progression.py            |   |
|                | Tireness                | Recovers (-0.01) during the day, increases (+0.005) at night. Gain is increased by anxiety and by having 0 stamina.                                | player_progression.py            |   |
| Player Offence | Melee Attack (Unarmed)  | Base Damage: 1 + (Strength Level * 0.1). This is then reduced by the player's tireness.                                                            | player_progression.py, update.py |   |
|                | Melee Attack (Weapon)   | Base Damage: (Weapon's Base Damage).Multiplier: 1 + (Melee Level * 0.1).Final damage is Base * Multiplier and is then reduced by tireness.         | player_progression.py, update.py |   |
|                | Melee Stamina/Tireness  | Costs 0.01 Stamina and adds 0.01 Tireness per swing. Fails if Stamina < 10.                                                                        | player_progression.py            |   |
|                | Melee Weapon Durability | Loss is 2.0 per hit. This is reduced to 0.5 if random.randint(0, 10) < Melee Level.                                                                | player_progression.py, update.py |   |
|                | Ranged Attack (Gun)     | Base Damage: (Weapon's Base Damage).Multiplier: 1 + (Ranged Level * 0.05).Final damage is Base * Multiplier and is then reduced by tireness.       | player_progression.py, update.py |   |
|                | Ranged Headshot         | 0.1 + (Ranged Level * 0.04) (e.g., 10% base + 4% per level) chance to inflict 2.0x damage.                                                         | player_progression.py, update.py |   |
|                | Ranged Resource Cost    | Costs 1 Ammo (load) and 0.5 Durability per shot.                                                                                                   | mouse.py                         |   |
|                | Experience (XP)         | Killing a zombie grants XP. Melee kills grant 50% XP to Strength and 100% to Melee. Ranged kills grant 100% XP to Ranged.                          | player_progression.py            |   |