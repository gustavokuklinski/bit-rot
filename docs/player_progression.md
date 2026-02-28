# Player Progression

```xml
<progression>
    <attributes>
        <attribute id="strength" name="Strength" image="ui/strength.png" base_xp="1000">
            <effect target="unarmed_damage" value="0.01" type="multiplier_add" />
        </attribute>
    </attributes>

    <stats>
        <stat id="stamina">
            <param name="regen_base" value="0.03" />
            <param name="run_cost_base" value="0.08" />
        </stat>
    </stats>
</progression>
```