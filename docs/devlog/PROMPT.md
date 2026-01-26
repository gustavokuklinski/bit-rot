This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to fix the following issues:

On the NPCs, I want to create some interaction by Right click on the friendly NPCs. A context menu: 'Talk'. (remove the follow option)

I want to create a new NPC modal with some pre setted dialogs as a XML file located at: game/data/npc/dialogs.xml like:

<npc_dialog>
    <options player_question="How is going on?" npc_awnser="It was fast, I just escaped with: [inventory_list] and [clothes_list]" required="true" />
    <options player_question="Give me a tip?" npc_awnser="You can use an Axe or Primitive Axe to chop tress." type="random" />
    <options player_question="Give me a tip?" npc_awnser="Be carefull, some people went rogue!" type="random" />
    <options player_question="Give me a tip?" npc_awnser="Stay away from the infected!" type="random" />
    <options player_question="Give me a tip?" npc_awnser="Search for Magazines, this can keep your sanity alive." type="random" />
    <options player_question="Give me a tip?" npc_awnser="I'm feeling dizzy..." type="random" />
<npc_dialog>



The code is in python. Show the file and the changed parts of the code to be fixed. Explain the changes step by step.