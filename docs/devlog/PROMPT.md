This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to create the following:

The only friendly NPC who player can chat are the Static NPCs.
Add this flag to the NPCs in game:
is_friendly="false" => Set if NPC is friendly (Default all to false) 
is_static="false" => Set if NPC walks around the world (Default set to false).
<npc type="worker" spawn_weight="20" is_friendly="false" is_static="false">
    <name value="RANDOM" />
    <sex value="RANDOM" />
    <xp min="1" max="15" />
    <stats>
        <health min="100" max="100" />
        <speed min="1" max="1" />
        <attack min="5" max="15" />
        <infection min="2" max="5" />
    </stats>
    <clothes>
        <head><cloth name="Worker Helmet" /></head>
        <util></util>
        <hair></hair>
        <facial></facial>
        <feet><cloth name="Shoes" /></feet>
        <hand><cloth name="Leather Black Gloves" /></hand>
        <body><cloth name="Next Petrol Tshirt" /></body>
        <arms></arms>
        <legs></legs>
    </clothes>
    <visuals>
        <sprite id="center" file="player.png" />
        <sprite id="left" file="player_left.png" />
        <sprite id="right" file="player_right.png" />
    </visuals>   
    <loot>
        <item item="Zombie Meat" chance="1.0" />
        <item item="Screwdriver" chance="1.0" />
        <item item="Toolkit" chance="1.0" />
        <item item="38 Revolver" chance="1.0" />
        <item item="Kukaroach (Bit Rot publisher)" chance="0.1" />
    </loot>
    <sound>
        <hit src="npc_hit.ogg" />
        <attack src="npc_attack.ogg" />
        <dead src="npc_dead.ogg" />
        <steps src="npc_steps.ogg" />
    </sound>
</npc>

I also want to apply the new Quest NPCs for example: 
If quest_npc="true" Zombies, Animals and Hostile NPCs cannot kill them.
They only spawn ONCE in the full map.
If the player Hit this NPC, it becomes hostile and follow the player.
quest_npc="true" only spawn Static NPCs.
<npc type="quest_dr_yu" quest_npc="true" is_static="true">
    <name value="Dr. Yu" />
    <sex value="RANDOM" />
    <xp min="1" max="15" />
    <stats>
        <health min="100" max="100" />
        <speed min="1" max="1" />
        <attack min="1" max="15" />
        <infection min="1" max="5" />
    </stats>
    <clothes>
        <head><cloth name="Medical Mask" /></head>
        <util></util>
        <hair></hair>
        <facial></facial>
        <feet><cloth name="Shoes" /></feet>
        <hand></hand>
        <body></body>
        <arms><cloth name="Medical Vest" /></arms>
        <legs><cloth name="Jeans Pants" /></legs>
    </clothes>
    <visuals>
        <sprite id="center" file="player.png" />
        <sprite id="left" file="player_left.png" />
        <sprite id="right" file="player_right.png" />
    </visuals>
    <loot>
        <item item="Zombie Meat" chance="1.0" />
        <item item="Vaccine" chance="1.0" />
        <item item="Medicine Vol.1" chance="1.0" />
        <item item="Sewing Kit" chance="1.0" />
        <item item="Medical Kit" chance="1.0" />
        <item item="Kukaroach (Bit Rot publisher)" chance="0.1" />
    </loot>
    <sound>
        <hit src="npc_hit.ogg" />
        <attack src="npc_attack.ogg" />
        <dead src="npc_dead.ogg" />
        <steps src="npc_steps.ogg" />
    </sound>
</npc>


---
This is my updated code Update your context with it. Never make any unnecessary changes. Read and understand it's design patterns and do what is being told:

---
This is my updated code folder located at: /home/gustavokuklinski/Projects/game-dev/bit-rot/core.

---
