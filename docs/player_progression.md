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

    <healing_rates>
        <part name="hand" rate="0.05" />
        <part name="arms" rate="0.05" />
        <part name="legs" rate="0.02" />
        <part name="feet" rate="0.005" />
        <part name="head" rate="0.005" />
        <part name="body" rate="0.005" />
    </healing_rates>
</progression>
```