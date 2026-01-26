### Items

All item design is stored at: ```game/sprites/item/[ITEM_NAME]```

Items have some nodes:
<item 
    name="Lantern on" 
    type="utility"
    state="on"
    dispensable="true">

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

- **type="consumable_[SUFIX]"** 
Types of consumables:

* _drink: Water and drinkable
* _food: Eatable items
* _mediacation: Medication items

```xml
<item name="Water bottle" type="consumable_drink">
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

- **type="conainer"** - Container items to store another items
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

- **type="weapon_melee"** Melee weapons
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

- **type="weapon_ranged"** Ranged weapons
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

- **type="consumable"** Weapons ammo
```xml
<item name="9mm ammo" type="consumable_ammo">
    <properties>
        <load min="10" max="50" /> <!-- weapon default load  -->
        <capacity value="100" /><!-- weapon max bullet  -->
        <sprite file="9mm_ammo.png" /> <!-- consumable sprite  -->
    </properties>
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="text"**
```xml
<item name="Safety Guide" type="text">
    <properties>
        <sprite file="newspaper.png" /><!-- Text sprite -->
        <text> <!-- Main text of the item: Newspaper, NPC dialog, etc... -->
           Some item text
        </text>
    </properties>
    <spawn chance="1" />
</item>
```

- **type="charm"**
```xml
<item name="Family Photo" type="charm">
    <properties>
        <sprite file="family_photo_1.png" /> <!-- Charm sprite -->
    </properties>
    <attributes>  <!-- Set the attributes to update -->
        <lucky value="0.1" />  <!-- Lucky modifier in % (Can be negative) -->
    </attributes>
    <spawn chance="1" /> <!-- Chance to spawn by [I] on map -->
</item>
```

- **type="currency"**
```xml
<item name="Money 5" type="currency"> <!-- Currency sprite -->
    <properties>
        <sprite file="money_5.png" /> <!-- Currency sprite -->
        <load min="5" max="5">  <!-- Currency value -->
        <capacity value="1000" /> <!-- Currency max capacity of this value (stack) -->
    </properties>
    <spawn chance="0" />
</item>
```

- **type="car_fuel"**
```xml
<item name="Car Fuel" type="car_fuel">
    <properties>
        <status value="fuel" />
        <load min="1" max="25" />
        <capacity value="25" />
        <sprite file="car_gas.png" />
    </properties>
    <spawn chance="1" />
</item>
```

- **type="car_key"**
```xml
<item name="Car Key Jeep" type="car_key">
    <properties>
        <key value="car_jeep" />
        <sprite file="car_key.png" />
    </properties>
    <spawn chance="1" />
</item>
```

- **type="car_motor"** - Car enginee
```xml
<item name="Car Engine" type="car_motor">
    <properties>
        <status value="motor" />
        <durability min="1" max="100" />
        <sprite file="car_engine.png" />
    </properties>
    <spawn chance="1" />
</item>
```