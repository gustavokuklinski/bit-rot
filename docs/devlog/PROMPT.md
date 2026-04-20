This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to create the following:

I want to create a new door update:

Allow the player to Barricate doors.

If the door is open or close, use:
<map name="door_02_barricate" type="maptile" char="door_02_barricate" is_obstacle="false" destructible="true">
    <properties>
        <health min="160" max="260" />
    </properties>
    <visuals>
        <sprite file="door_02_barricate.png" />
    </visuals>
</map>

If the door is broken use:
<map name="door_02_broke_barricate" type="maptile" char="door_02_broke_barricate" is_obstacle="true">
    <properties>
        <health min="50" max="80" />
    </properties>
    <visuals>
        <sprite file="door_02_broke_barricate.png" />
    </visuals>
</map>

If the barricate is destroyed, go back to the previous state,
for example:
door_02_barricate back to door_02_close
door_02_broke_barricate to door_02_broke

Show me the changed code.
The code is in Python

---
This is my updated code Update your context with it. Never make any unnecessary changes. Read and understand it's design patterns and do what is being told:

---
This is my updated code folder located at: /home/gustavokuklinski/Projects/game-dev/bit-rot/core.

---
