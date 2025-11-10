### Items

All item design is stored at: ```game/sprites/item/[ITEM_NAME]```

Sprite types and codes:

- **type="utility"**
```xml
<item name="[ITEM NAME]" type="utility" state="[STATE: 'ON'/'OFF']">
    <properties>
        <durability min="1" max="2000" /> <!-- utility durabilitie -->
        <light min="5" max="100" /> <!-- utility light radius -->
        <fuel type="Matches" /> <!-- type of fuel to turn 'ON' (state="on") -->
        <sprite file="lantern_on.png" /> <!-- utility sprite -->
    </properties>
    <spawn chance="1" /> <!-- utility chance to spawn by [I] on map, or inside a type="container" -->
</item>
```

- **type="conainer"**
```xml
<item name="[ITEM NAME]" type="container">
    <properties>
        <capacity value="3" /> <!-- container capacitie: min: value="3" and max value="20"  -->
        <sprite file="wallet.png" /> <!-- container default sprite -->
    </properties>
     <spawn chance="1" /> <!-- utility chance to spawn by [I] on map, or inside a type="container" -->
    <loot> <!-- container default loot -->
        <item name="ID" chance="100" />  <!-- container default item spawn inside -->
    </loot>
</item>
```

- **type="weapon"** (Melee: Axe, Knife, Baton...)
```xml
<item name="[WEAPON NAME]" type="weapon">
    <properties>
        <durability min="10" max="100" /><!-- weapon durabilitie  -->
        <damage min="20" max="50" /><!-- weapon damage  -->
        <skill type="melee" /><!-- weapon skill boost  -->
        <sprite file="axe.png" /><!-- weapon sprite  -->
    </properties>
     <spawn chance="1" /> <!-- chance to spawn by [I] on map, or inside a type="container" -->
</item>
```

- **type="weapon"** (Ranged: Piston, Shotgun...)
```xml
<item name="[WEAPON NAME]" type="weapon">
    <properties>
        <durability min="5" max="100" /><!-- weapon durabilitie  -->
        <load min="5" max="12" /><!-- weapon default load  -->
        <capacity value="12" /><!-- weapon max bullet  -->
        <ammo type="9mm Ammo" /><!-- weapon ammo item  -->
        <damage min="25" max="55" /><!-- weapon damage  -->
        <firing pellets="1" spread_angle="0" /><!-- weapon firing angle, ex: spread shoots with shotgun  -->
        <skill type="range" /><!-- weapon skill boost  -->
        <sprite file="pistol_9mm.png" /><!-- weapon sprite  -->
    </properties> 
    <spawn chance="1" /><!-- chance to spawn by [I] on map, or inside a type="container" -->
</item>
```

- **type="consumable"** (Ranged: 9mm ammo, Shotgun Shells...)
```xml
<item name="[AMMO NAME]" type="consumable">
    <properties>
        <load min="10" max="50" /> <!-- weapon default load  -->
        <capacity value="100" /><!-- weapon max bullet  -->
        <sprite file="9mm_ammo.png" /> <!-- consumable sprite  -->
    </properties>
    <spawn chance="12" /><!-- chance to spawn by [I] on map, or inside a type="container" -->
</item>
```

- **type="skill"**
```xml
<item name="[SKILL NAME]" type="skill">
    <properties>
        <sprite file="bible_1.png" /> <!-- Skill sprite -->
    </properties>
        <stats> <!-- Set the status to update -->
            <health value="100.0" />  <!-- Reset health to value -->
            <stamina value="100.0" /> <!-- Reset stamina to value -->
            <anxiety value="0.0" /> <!-- Reset anxiety to value -->
        </stats>
    <spawn chance="1" />
</item>
```