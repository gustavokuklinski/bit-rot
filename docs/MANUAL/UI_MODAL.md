# UI Modal System

## How Modals Work
Modals in *Bit Rot* are data-driven floating UI windows managed through a central list (`game.modals`). 

* **Z-Order & Focus:** Modals are rendered in order. Clicking anywhere on a modal automatically brings it to the top of the stack (`game.modals.append(game.modals.pop(index))`), making it the active focus window.
* **Dragging:** Clicking and dragging on a modal's header bar (`35px` height) updates its top-left screen position, which is clamped within the game window boundaries and cached in `game.last_modal_positions`.
* **Cleanup & Distance Capping:** Modals maintain distance proximity checks (`_cleanup_modals`). If the player moves too far away from a physical world container, corpse, or vehicle, the modal automatically closes itself.
* **Scrolling:** Modals supporting long text or lists utilize standardized scrollbars (`draw_scrollbar`) driven by mouse wheel events or drag-and-drop thumb tracking.

---

## Detailed List of Game Modals

| Modal Type | Identifier String | Purpose & Functionality |
| :--- | :--- | :--- |
| **Player Status** | `'status'` | Displays the multi-tab survivor overview. Tabs include **Health** (vitals bars, temperature, time of day), **Status** (vitals breakdown), **Record** (skills, levels, XP progression), and **Quests** (journal and milestone tracker). |
| **Inventory** | `'inventory'` | Manages player inventory slots (15 base slots) and includes dynamic tabs for any containers currently carried inside the player's inventory/belt/gear. |
| **Gear** | `'gear'` | Displays character paper-doll equipment slots (Head, Hair, Facial, Body, Arms, Legs, Feet, Util slots). Like inventory, it dynamically spawns tabs for worn containers. |
| **Nearby / Ground** | `'nearby'` | Scans the immediate surroundings (`1.5` tiles) and lists all nearby world containers, corpses, and a dedicated **Ground** tab containing loose items on the floor. |
| **Container View** | `'container'` | Opens the slot grid for a specific targeted world container (e.g., Chests, Maptile lockers, Vehicle Trunks). Generates loot dynamically from XML definitions upon first opening. |
| **Messages / Chat** | `'messages'` | Displays the message log (All, Chat, Player, Zombie) with elastic window-stretching capabilities and includes the **Chat/Console input bar** for text and debug commands (`%rot`). |
| **Slots Overview** | `'slots'` | Provides a unified scrolling master view aggregating every single container currently on your person (inventory, belt, and equipped bags/clothing pockets) into one screen. |
| **Text Reader** | `'text'` | Opens a formatted reading window for Books, Notes, ID cards, and dynamic lore items, with custom placeholder replacement (`[PLAYER NAME]`, recipes, quests). |
| **Mobile Phone** | `'mobile'` | Interactive device modal featuring **Clock** (time/weather), **Map** (tactical chunk/world cartography map), **Apps** (SD Card module slots), and **Radio** (frequency dial and broadcast receiver). |
| **Vehicle Dashboard** | `'vehicle'` | Manages vehicles. Contains a **Vehicle** tab (motor/light switches, speedometer, dashboard fuel/battery gauges) and a **Mechanics** tab (inspecting and installing Motor, Key, Fuel tank, Battery, and Tires). |
| **Crafting Bench** | `'crafting'` | Full-screen crafting interface containing tabs for **Known Recipes**, **Craft**, **Repair**, and **Dismantle**, complete with instant search filters, batch quantity selectors (`ONE`, `HALF`, `ALL`), and ingredient tooltips. |
| **Tactical Map** | `'big_map'` | Full-screen cartography map opened from Cartography items or map documents, supporting mouse drag panning and zoom controls (`2x` to `32x`). |
| **NPC Dialog** | `'npc_dialog'` | Handles conversations with survivors. Includes **Current Dialog** (dynamic branching question/answer choices), **Special Dialogs** (memory logs), and a **Trade** shop tab to buy items using *Money WBRL*. |
| **Help & Tutorial** | `'help'` | Markdown-based manual reader featuring categorized tabs powered by local markdown documentation (`en_US_help.md`) with embedded scrolling. |