# NPC Dialog

```xml
<npc_dialog>
    <node id="greeting">
        <options 
            player_question="How's it going?" 
            npc_answer="I just escaped with: [inventory_list]. You look like you've seen better days too." 
            priority="100"/>
    </node>
    <node id="tips">
        <options
            player_question="Got any advice?" 
            npc_answer="For our lucky the company made all vehicle keys the same. Here is a gift."
            priority="1"
            award_item="[Car Key Jeep, Car Key Pickup]" />
        <options
            player_question="Got any advice?" 
            npc_answer="Run, and..." 
            unlock_flag="just_run"
            priority="10" />
    </node>

    <node id="lore_branch">
        <options 
            player_question="How is the oil rigs?"
            npc_answer="Fully functional for years. I miss my family so much."
            award_item="[Family Photo]"
            priority="100" />
    </node>

    <node id="just_run">
        <options
            player_question="So...why?" 
            npc_answer="Maybe you can finish my misery." 
            unlock_flag="is_hostile" />
    </node>

    <node id="is_hostile">
        <options 
            player_question="One more thing..."
            npc_answer="Stop bothering me before I lose my temper. Every man for himself, remember?"
            npc_state_friendly="false"
            npc_state_static="false"
            priority="100" />
    </node>
</npc_dialog>
```