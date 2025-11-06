### Zombies

Zombies have random modifiers.
File located at: ```game/data/zombie/zombie.xml```

**Base Zombie XML**
```xml
<zombie>
    <name value="RANDOM" /> <!-- Random generated name -->
    <profession value="RANDOM" /> <!-- Random generated profession -->
    <sex value="RANDOM" /> <!-- Random generated sex -->
    <vaccine value="RANDOM" /> <!-- Random generated if vaccined -->

    <xp min="0.2" max="10" /> <!-- Random min and aax kill XP -->
    
    <stats>
        <health min="30" max="200" /> <!-- Random min and max health -->
        <speed min="1" max="2" /> <!-- Random min and max speed -->
        <attack min="1" max="3" /> <!-- Random min and max attack rate -->
        <infection min="1" max="3" /> <!-- Random min and max infection rate -->
    </stats>
    
    <clothes> <!-- Random Zombie clothes -->
        <head></head>
        <feet></feet>
        <hand></hand>
        <torso></torso>
        <body></body>
        <legs></legs>
    </clothes>

    <visuals> <!-- Zombie default sprite -->
        <sprite file="zombie.png" />
    </visuals>
    
    <loot> <!-- Zombie mandatory loot -->
        <item name="Wallet" chance="100.0" />
    </loot>

</zombie>
```

### Zombie Mechanics

| Mechanic        | Stat / Action           | Value & Calculation                                                                                                                            | Source File(s)       |   |
|-----------------|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|---|
| Zombie Offence  | Attack Damage (Raw)     | random.randint(min_attack, max_attack). These min/max values are loaded from the zombie's template.                                            | zombie.py            |   |
|                 | Infection (Raw)         | random.randint(min_infection, max_infection). Also loaded from the template.                                                                   | zombie.py            |   |
|                 | Attack Cooldown         | 500ms (Attacks once every half-second if in range).                                                                                            | update.py            |   |
| Player Defence  | Clothing Durability Hit | (Step 1) When a zombie hits, before defence is calculated, a random piece of equipped clothing is chosen.                                      | player.py, zombie.py |   |
|                 | Durability Damage       | The chosen clothing item loses raw_damage * 0.25 durability. If its durability reaches 0, it breaks and is unequipped.                         | player.py            |   |
|                 | Defence Stat            | (Step 2) The player's total Defence is calculated by summing the defence value of all equipped clothes that are not broken (Durability > 0).   | player.py            |   |
|                 | Damage Reduction        | (Step 3) The raw zombie damage is reduced by the Defence percentage.final_damage = raw_damage * (1.0 - (total_defence / 100.0))                | zombie.py            |   |
|                 | Infection Reduction     | (Step 4) The raw infection is reduced by half the Defence percentage.final_infection = raw_infection * (1.0 - ((total_defence / 2.0) / 100.0)) | zombie.py            |   |
|                 | Tooltip Info            | When hovering over a piece of clothing, the tooltip now correctly displays both its Durability and its Defence value.                          | tooltip.py, item.py  |   |
| Zombie Spawning | Spawn Restrictions      | Zombies are now blocked from spawning on any tile that is an obstacle (is_obstacle="true") or has a tile ID of bg, water_, or petrol_.         | map_loader.py        |   |