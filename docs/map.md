### Map
All item design is stored at: ```game/sprites/map/[MAP_TILE]```

**Mapping**
- **P**: Player spawn
- **Z**: Zombie spawn
- **I**: Item map spawn

#### Map tiles

type="maptile_container" 
```xml
<map name="military_crate" type="maptile_container" char="military_crate" is_obstacle="true">  <!-- is_obstacle="true" or "false" -->
    <visuals>
        <sprite file="military_crate.png" /> <!-- map container sprite -->
    </visuals>
    <capacity value="10" /> <!-- map container capacity -->
    <loot> <!-- Item loot table -->
        <item item="Pistol 9mm" chance="1" />  <!-- items to spawn -->
        <item item="Leather Black Gloves" chance="1" /> <!-- clothes pass as items to spawn -->
    </loot>
</map>
```

type="maptile_car"
```xml
<map name="car_jeep" type="maptile_car" char="car_jeep" is_obstacle="true">
    <capacity value="5" />
    <car>
        <max_speed value="8" />
        <key value="Car Key Jeep" />
        <fuel value="1.0" />
        <motor value="1.0" />
        <battery value="1.0" />
        <lights min="5" max="100" radius="8" />
    </car>
    <loot>
        <item item="Car Gas" chance="1" />
        <item item="Powerbank" chance="1" />
    </loot>
    <visuals>
        <sprite file="car_jeep.png" />
    </visuals>
</map>

```

type="maptile" - state="open/close"
```xml
<map name="wooden_door_01_close" type="maptile" char="wooden_door_01_close" state="close" is_obstacle="true">
    <visuals>
        <sprite id="close" file="wooden_door_01_close.png" />
    </visuals>
    <sound src="door_close.ogg" />
</map>
```

#### Map editor