This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to create the following:

I have this type of static generic NPC:

<npc type="common" spawn_weight="55" is_friendly="true" is_static="true">
    <name value="RANDOM" />
    <sex value="RANDOM" />
    <stats>
        <health min="100" max="100" />
        <speed min="1" max="1" />
        <attack min="1" max="15" />
        <infection min="1" max="5" />
    </stats>    
    <clothes>
        <head></head>
        <util></util>
        <hair></hair>
        <facial></facial>
        <feet></feet>
        <hand></hand>
        <body></body>
        <arms></arms>
        <legs></legs>
    </clothes>
    <visuals>
        <sprite id="center" file="player.png" />
        <sprite id="left" file="player_left.png" />
        <sprite id="right" file="player_right.png" />
    </visuals>
    <loot>
        <item item="Kukaroach (Bit Rot publisher)" chance="0.1" />
    </loot>
    <sound>
        <hit src="npc_hit.ogg" />
        <attack src="npc_attack.ogg" />
        <dead src="npc_dead.ogg" />
        <steps src="npc_steps.ogg" />
    </sound>
</npc>

The player is allowed to chat with this NPCs. I want them to have some procedural, generic chatty lines. Provided by my dialogs.xml
<?xml version='1.0' encoding='utf-8'?>
<npc_dialog>
    <node id="greeting" x="65" y="120">
        <options player_question="How's it going?" npc_answer="I just escaped with: [inventory_list]. You look like you've seen better days too." priority="100" />
        <options player_question="You look like you've been through hell." npc_answer="Hell? No, this is just corporate cost-cutting with extra steps. At least in hell, the medical benefits would be better." priority="50" req_level="[lucky:1]" gain_xp="[lucky:50]" />
    </node>
    <node id="tips" x="443" y="140">
        <options player_question="How do I stay alive out here?" npc_answer="Here's a map. This may save you." priority="10" req_level="[lucky:2]" gain_xp="[lucky:20]" dialog_type="once" award_item="[Island Map]" />
        <options player_question="Any way to get around faster?" npc_answer="Exxoil left keys in all their jeeps. Same ignition. Corporate cost-cutting. Try these—they might work." priority="10" req_level="[lucky:3]" gain_xp="[lucky:50]" dialog_type="once" award_item="[Car Key Jeep]" />
    </node>
    <node id="lore_branch" x="779" y="133">
        <options player_question="What happened to the continent?" npc_answer="Brazil fell first. Then the rest. The Plague didn't care about borders. Only the islands survived. For now." priority="20" gain_xp="[lucky:50]" />
        <options player_question="Why did the helicopters leave us?" npc_answer="Standard protocol. Next Petrol doesn't rescue liabilities. We are the liability now. Every person is a potential carrier." priority="19" gain_xp="[lucky:50]" />
    </node>
</npc_dialog>

Also for the Quest NPCs (XML Below) I want to add a new <node id="quest"> where the player can have little objectives with NPCs in exchange to rewards like rare items and info, procedurally ofcorse:
<npc type="quest" quest_npc="true" is_static="true">
    <name value="RANDOM" />
    <sex value="RANDOM" />
    <stats>
        <health min="100" max="100" />
        <speed min="1" max="1" />
        <attack min="1" max="15" />
        <infection min="1" max="5" />
    </stats>
    <clothes>
        <head></head>
        <util></util>
        <hair></hair>
        <facial></facial>
        <feet></feet>
        <hand></hand>
        <body></body>
        <arms></arms>
        <legs></legs>
    </clothes>
    <visuals>
        <sprite id="center" file="player.png" />
        <sprite id="left" file="player_left.png" />
        <sprite id="right" file="player_right.png" />
    </visuals>
    <loot>
        <item item="Kukaroach (Bit Rot publisher)" chance="0.1" />
    </loot>
    <sound>
        <hit src="npc_hit.ogg" />
        <attack src="npc_attack.ogg" />
        <dead src="npc_dead.ogg" />
        <steps src="npc_steps.ogg" />
    </sound>
</npc>

Make the dialog likes always unique, and do not repeat them during game play

---
This is my updated code Update your context with it. Never make any unnecessary changes. Read and understand it's design patterns and do what is being told:

---
This is my updated code folder located at: /home/gustavokuklinski/Projects/game-dev/bit-rot/core.

---
