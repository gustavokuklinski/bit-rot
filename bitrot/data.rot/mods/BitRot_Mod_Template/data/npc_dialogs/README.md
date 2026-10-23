# Creating Crafts

Read and understand the craft types.

## npc_dialogs/[TYPE: text].xml

npc_dialogs/chat.xml
```json
{
    "npc_chat": [
      {
        "id": "greeting",
        "options": [
          {
            "player_question": "Hello! How's it going?",
            "npc_answer": "I just escaped with: [inventory_list]. You look like you've seen better days too. See, I have some good stuff here if you needed.",
            "priority": 50
          }
        ]
      },
      {
        "id": "lore_branch",
        "options": [
          {
            "player_question": "What was it like when the Plague first hit?",
            "npc_answer": "It was chaos. The news said it was a new flu. Then people started bleeding from their eyes. Rio was a warzone in three days.",
            "priority": 10
          },
          {
            "player_question": "Why did Brazil fall so fast?",
            "npc_answer": "Carnival, my friend. Millions of people, sweaty and packed together. The perfect breeding ground for the Plague. The government tried to lock us down, but it was too late.",
            "priority": 10
          }
        ]
      }
    ]
}

```

## npc_dialogs/[TYPE: text].xml

npc_dialogs/tips.xml
```json
{
    "npc_tips": [
      {
        "id": "tips",
        "options": [
          {
            "player_question": "How do I stay alive out here?",
            "npc_answer": "Here's a map. This may save you.",
            "priority": 10,
            "gain_xp": "[lucky:25]",
            "dialog_type": "once",
            "award_item": "[Island Map]"
          },
          {
            "player_question": "Any way to get around faster?",
            "npc_answer": "Exxoil left keys in all their jeeps. Same ignition. Corporate cost-cutting. Try these—they might work.",
            "priority": 10,
            "req_level": "[lucky:3]",
            "gain_xp": "[lucky:25]",
            "dialog_type": "once",
            "award_item": "[Car Key Jeep]"
          },
          {
            "player_question": "The tool here looks like garbage!",
            "npc_answer": "The main engineer of the island built everything from blueprints. You can scavenge for them or use old books and zines. I have one, take it...",
            "priority": 10,
            "gain_xp": "[lucky:5]",
            "dialog_type": "once",
            "award_item": "[Blueprint]"
          },
          {
            "player_question": "How can I craft something around here?",
            "npc_answer": "You can find some magazines around and make some works.",
            "priority": 10,
            "gain_xp": "[lucky:5]",
            "dialog_type": "once"
          },
          {
            "player_question": "Is there any way to communicate around?",
            "npc_answer": "Use your mobile and check the radio! I think some people are still alive.",
            "priority": 10,
            "gain_xp": "[lucky:5]",
            "dialog_type": "once"
          }
        ]
      }
    ]
}

```