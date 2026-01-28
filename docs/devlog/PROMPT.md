Update your context with the new updated code

This is my full code. The code is working. Read the code and understand it's design patterns and code design. Never make any unnecessary changes to the working code. Never create unnecessary functions or procedures to the working code. Always try to use what is in the current code and what is working. Use elegant and creative ways to create the following:

On the player status, I want to increase the width if the modal and split in two columns:
Column 1 as default showing player stats
Column 2 with a image of the player.

The Zombie and hostiles NPCs hit will now set a random part of the <body> of the player as shown on the player.xml:
<body>
    <head value="100.0" defence="0.0" />
    <legs value="100.0" defence="0.0" />
    <feet value="100.0" defence="0.0" />
    <torso value="100.0" defence="0.0" />
    <hand value="100.0" defence="0.0" />
    <body value="100.0" defence="0.0" />
</body>

When those values are 100% the player health is 100%. When the player set a Cloth it will increase the defence of this part, making the Zombie hit always the part with less defence. 

The Bandages and Medkit will always recover the more dammaged body part of the player or if the player right click the context menu will show a list of the dammaged parts to apply the bandage.

The screenshot show how I want it to look like.

Show me step by step to make this implementation withut break the current code.

The code is in python. Show the file and the changed parts of the code to be fixed. Explain the changes step by step.