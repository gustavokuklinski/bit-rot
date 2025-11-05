### Player

Player template.
File located at: ```game/data/zombie/zombie.xml```

```xml
<player name="player">
    <name value="Player" /> <!-- Player name -->
    <sex value="Male" /> <!-- Player sex -->
    <profession value="Civilian" /> <!-- Player profession -->

    <traits>
        <vaccine value="false" /> <!-- IF TRUE: -15% infection; -->
        <athletic value="false" /> <!-- IF TRUE: -10% stamina;  -->
        <strong value="false" /> <!-- IF TRUE: +2 strength; -->
        <weak value="false" /> <!-- IF TRUE: -2 strength; -->
        <luck value="false" /> <!-- IF TRUE: +1 lucky +15% bonus; -->
        <unlucky value="false" /> <!-- IF TRUE: -1 lucky; -15% lucky bonus; -->
        <runner value="false" /> <!-- IF TRUE: +1 speed; -->
        <smoker value="false" /> <!-- IF TRUE: -15% stamina; +15% anxiety -->
        <drunk value="false" /> <!-- IF TRUE: -15% speed; +15% anxiety -->
        <illnes value="false" /> <!-- IF TRUE: +15% infection rate; -->
        <sedentary value="false" /> <!-- IF TRUE: -15% stamina, -2 strenght  -->
        <myopia value="false" /> <!-- IF TRUE: -10% view radius, -10% ranged -->
        <collateral_effect value="false" /> <!-- IF TRUE: -1 stregth; -1 fitness; -1 ranged; -1 melee; -30 health; -60 infection; -15 stamina; +15 anxiety -->
    </traits>

    <stats> <!-- Player stats -->
        <health value="100.0" />
        <stamina value="100.0" />
        <water value="100.0" />
        <food value="100.0" />
        <anxiety value="0.0" />
        <tireness value="0.0" />
        <infection value="0.0" />
    </stats>

    <attributes> <!-- Skill attributes -->
        <strength value="0.0"/>
        <fitness value="0.0" />
        <melee value="0.0"  />
        <ranged value="0.0" />
        <lucky value="0.0" />
        <speed value="0.0" />
    </attributes>

    <initial_loot> <!-- Player startup loot -->
        <item name="wallet" chance="100" />
    </initial_loot>

    <visuals> <!-- Player sprite -->
        <sprite file="player.png" />
    </visuals>

    <clothes> <!-- Player Clothes -->
        <head></head>
        <legs></legs>
        <feet></feet>
        <torso></torso>
        <hand></hand>
        <body></body>
    </clothes>
</player>
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