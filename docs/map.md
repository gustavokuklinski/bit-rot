### Map
All item design is stored at: ```game/sprites/map/[MAP_TILE]```

```xml
<map 
    name="car_jeep" 
    type="maptile_car" 
    char="car_jeep" 
    is_obstacle="true">
    <visuals>
        <sprite file="car_jeep.png" />
    </visuals>
    <capacity value="5" />
    <loot>
        <item item="Car Gas" chance="1" />
        <item item="Powerbank" chance="1" />
    </loot>
</map>
```