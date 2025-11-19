### Items

All item design is stored at: ```game/sprites/item/[ITEM_NAME]```

Sprite types and codes:

- **type="utility"**
```xml
<item name="Lantern on" type="utility" state="on"> <!-- State can be ON or OFF -->
    <properties>
        <durability min="1" max="2000" /> <!-- utility durabilitie - if state ON consume -->
        <light min="5" max="100" /> <!-- utility light radius -->
        <fuel type="Matches" /> <!-- type of fuel to turn 'ON' (state="on") -->
        <sprite file="lantern_on.png" /> <!-- utility sprite -->
    </properties>
    <spawn chance="1" /> <!-- utility chance to spawn by [I] on map, or inside a type="container" -->
</item>
```

- **type="consumable"** - Status modiefier
```xml
<item name="Water bottle" type="consumable">
    <properties>
        <!-- The basic item purpose -->
        <status value="water" /> <!-- Player Status modifier: water, food, ... -->
        <restore min="25" max="25" /> <!-- Min and Max <restore> or <reduce> by status -->

        <!-- 
            Other item effects 
            status: tireness, water... min and max values
        -->
        <reduce status="[tireness]" min="5" max="10" />
        <restore status="[health, stamina]" min="1" max="2" />
        <restore status="[water]" min="1" max="10" />


        <load min="15" max="25" /> <!-- Min and Max consumable Load -->
        <capacity value="25" /> <!-- Max consumable Load -->
        <sprite file="water_bottle.png" />
    </properties>
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="conainer"**
```xml
<item name="Wallet" type="container">
    <properties>
        <capacity value="3" /> <!-- container capacitie: min: value="3" and max value="20"  -->
        <sprite file="wallet.png" /> <!-- container default sprite -->
    </properties>
    <loot> <!-- container default loot -->
        <item name="ID" chance="100" />  <!-- container default item spawn inside -->
    </loot>
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="weapon_melee"** (Melee: Axe, Knife, Batton...)
```xml
<item name="Axe" type="weapon_melee">
    <properties>
        <durability min="10" max="100" /><!-- weapon durabilitie  -->
        <damage min="20" max="50" /><!-- weapon damage  -->
        <skill type="melee" /><!-- weapon skill boost  -->
        <sprite file="axe.png" /><!-- weapon sprite  -->
    </properties>
     <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="weapon_ranged"** (Ranged: Piston, Shotgun...)
```xml
<item name="Pistol 9mm" type="weapon_ranged">
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
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="consumable"** (Ranged: 9mm ammo, Shotgun Shells...)
```xml
<item name="9mm ammo" type="consumable">
    <properties>
        <load min="10" max="50" /> <!-- weapon default load  -->
        <capacity value="100" /><!-- weapon max bullet  -->
        <sprite file="9mm_ammo.png" /> <!-- consumable sprite  -->
    </properties>
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="skill"**
```xml
<item name="Family Photo" type="skill">
    <properties>
        <sprite file="family_photo_1.png" /> <!-- Skill sprite -->
    </properties>
    <attributes>  <!-- Set the attributes to update -->
        <lucky value="0.1" />  <!-- Lucky modifier in % (Can be negative) -->
    </attributes>
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```