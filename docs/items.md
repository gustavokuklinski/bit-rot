### Items

```xml
<item 
    name="Car Engine" 
    type="car_motor" 
    state="on" 
    allow_liquid="true"
    liquid="true">
    <properties>
        <status value="motor" />
        <restore status="[tireness]" min="5" max="10" />
        <reduce status="[anxiety]" min="5" max="20" />
        <durability min="1" max="100" />
        <load min="1" max="25" />
        <capacity value="25" />
        <light min="5" max="30" />
        <fuel type="[Matches, Lighter on]" />
        <damage min="3" max="5" />
        <skill type="melee" />
        <knockback value="0" />
        <sprite file="car_engine.png" />
    </properties>
    <attributes>
        <lucky value="0.1" />
    </attributes>
    <loot>
        <item name="Scissor" chance="0.3" />
    </loot>
    <sound>
        <swing src="axe.ogg" />
        <shoot src="mpk5.ogg" />
        <reload src="reload.ogg" />
        <noammo src="outofammo.ogg" />
    </sound>
    <spawn chance="1" />
</item>
```