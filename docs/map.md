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
</map>
```