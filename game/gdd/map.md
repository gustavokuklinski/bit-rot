### Map
All item design is stored at: ```game/sprites/map/[MAP_TILE]```

**Mapping**
- **P**: Player spawn
- **Z**: Zombie spawn
- **I**: Item map spawn

#### Map container

```xml
<map name="[MAP CSV UNIQUE NAME]" type="maptile_container" char="[MAP CSV UNIQUE CHAR]" is_obstacle="true">  <!-- is_obstacle="true" or "false" -->
    <visuals>
        <sprite file="military_crate.png" /> <!-- map container sprite -->
    </visuals>
    <capacity value="10" /> <!-- map container capacity -->
    <loot>
        <item item="Pistol 9mm" chance="1" />  <!-- items to spawn -->
        <item item="Leather Black Gloves" chance="1" /> <!-- clothes pass as items to spawn -->
    </loot>
</map>
```

#### Map editor