This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to create the following:

I want my game to have a procedural dialogs. So I want to change the dialogs.xml to read by some sentence fragment and try to predict another making a sense text, also to generate random quests for the player.

<npc_dialog>
    <node id="greeting" x="65" y="120">
        <player_question p="Hello" />
        <player_question p="How'd!" />
        <npc_awnser n="Hello" />
        <npc_awnser n="Hi" />
    </node>
    <node id="context" x="65" y="120">
        <player_question p="we need to get out of this mess!" />
        <player_question p="just hope the helicopter still on the pad." />
        <npc_awnser n="I don't think we are going anywhere soon." />
        <npc_awnser n="Here we need to try to survive." />
    </node>
    <node id="end" x="65" y="120">
        <player_question p="those Rotters almost got me!" />
        <player_question p="I'm lucky to stay alive." />
        <npc_awnser n="They brought an helicpter with survivors from the mainland." />
        <npc_awnser n="Just got news from Brazil, It fell just after USA get dark." />
    </node>
</npc_dialog>

This should generate dialogs like:
Player: How'd! just hope the helicopter still on the pad. I'm lucky to stay alive.
NPC: Hi I don't think we are going anywhere soon. Just got news from Brazil, It fell just after USA get dark.

And randomize Player and NPC awnsers with those fragments generating a procedural randomized dialog tables.

My code is in python.
---
This is my updated code Update your context with it. Never make any unnecessary changes. Read and understand it's design patterns and do what is being told:

---
This is my updated code folder located at: /home/gustavokuklinski/Projects/game-dev/bit-rot/core.

---
