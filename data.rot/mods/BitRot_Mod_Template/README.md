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
- `/data.rot/lib/*` 
```json
{
    "overide_dir":[  # Select folders to overide
        "/data.rot/lib/*" 
        ], 
    "fallack": true  # Complete dir with: data.rot/lib
}
```