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