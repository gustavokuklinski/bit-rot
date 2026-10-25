# BitRot_Vanilla
path: `data.rot/mods/BitRot_Vanilla`
version: [VERSION](./VERSION)
repository: https://github.com/gustavokuklinski/bit-rot/

## About
This is the vanilla version of BitRot.
The main files fallback for this version is located at the default game library: `./data.rot/lib/`
All major updates will be located there.

_If you want to go ahead, take your risk._ 

This is a simple Bit Rot modding testing tool.
* Create new items, crafts, quests, clothes, balance for the game
* Improve the game sprites

## Build with AI-agentic tool:a
List below the agentic tools, LLM or another AI used at your project:
Art: [NAME_AI_AG_LLM_ETC]
Code: [NAME_AI_AG_LLM_ETC]
Design: [NAME_AI_AG_LLM_ETC]

## Config your mod:
Setup where your mod will work.

```json
{
    "name": "BitRot_Vanilla", # Mod name
    "version": "0.0.0.1", # Mod version
    "author": "Kukaroack", # Mod Author
    "logo": "./sprites/mod_logo.png", # Mod logo
    "description": "BitRot Vanilla - Official game mod", # Mod summary
    "repository": "https://github.com/gustavokuklinski/bit-rot/", # Mod repository
    "overide_dir":[
        "./data.rot/lib/*" # Mod work directory
        ],
    "editor_config": [], # Empty is all
    "fallack": true # If false mode will override config instead add to default  
}
```