This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to create the following:


The code is in python. Show the file and the changed parts of the code to be fixed. Explain the changes step by step.
---

Update your context with the new updated code

---

This is my updated code. Update your context with it. Never make any unnecessary changes. Read and understand it's design patterns and do what is being told:

I want to add new entity called Animals to the game. Here is the following animal base XML:

Rat XML can spawn anywhere in the map layer 1 and 2.

Animal can attack the player and NPCs. Animals do not attack zombies
<animal name="Rat" type="animal">
    <stats>
        <health min="10" max="20" />
        <speed min="1" max="1" />
        <attack min="1" max="5" />
        <infection min="10" max="25" />
    </stats>
    <capacity value="3" />
    <visuals>
        <sprite file="rat.png" />
    </visuals>
    
    <loot>
        <item item="Meat" chance="0.3" />
    </loot>
</animal>

Bat XML, only spawn at L2 map
<animal name="Bat" type="animal">
    <stats>
        <health min="1" max="5" />
        <speed min="1" max="1" />
        <attack min="1" max="5" />
        <infection min="1" max="10" />
    </stats>
    <capacity value="1" />
    <visuals>
        <sprite file="bat.png" />
    </visuals>
    <loot>
    </loot>
</animal>
---
