# Context Menu

## 1. Item Actions (Player Inventory, Belt, and Gear)
| Option | Description | Requirements / When It Appears |
| :--- | :--- | :--- |
| **Equip** | Opens a submenu (`Belt 1–5` or Gear slots like `Head`, `Body`, `Legs`, `Util 1–3`) to equip the item directly into a specific slot. Slots with occupied gear show a red `*`. | Appears on weapons, tools, clothes, containers, and items with `allow_belt="true"`. |
| **Unequip** | Moves an equipped item from the Belt HUD or Gear slot back into the player’s main inventory. | Only appears on items currently equipped on the Belt or Gear. |
| **Use** | Starts a timed action to consume food, drinks, medicines, drugs, or read recipe magazines. Restores or reduces player stats (HP, stamina, water, food). | Consumables (`consumable_*`) and potable liquids. |
| **Reload** | Inserts compatible ammunition into an equipped ranged firearm, or refills fuel for utility tools (e.g., matches/oil for lanterns). | Ranged weapons and refuelable utility items. |
| **Get bullets** | Unloads all loaded ammunition from a firearm back into the inventory or drops it on the ground if full. | Ranged weapons with `load > 0`. |
| **Turn on / Turn off** | Toggles powered electronics or lights (e.g., Mobile phone, Flashlight, Campfire, Lantern). | Utility items with state properties. Campfires can only be toggled when placed on the ground. |
| **Drop** | Drops the item on the ground next to the player. Liquid items without a container spill and are destroyed. | Any item in inventory, belt, or gear. |
| **Drop one** | Drops exactly 1 unit from a stackable item. | Stackable items with `load > 1`. |
| **Drop all** | Drops all remaining units of a stackable item. | Stackable items with `load > 1`. |
| **Place** | Enters tile-placement mode, allowing the player to snap and place the item onto an adjacent valid ground tile (e.g., Campfires, Barricades). | Placeable items. |
| **Read** | Opens books, letters, notes, or IDs in the text viewer modal (`text`). | Items of type `text`. |
| **Open / Inspect** | Opens the container view (e.g., backpack, vest, cargo pockets), opens the mobile phone modal, or displays the world map for Cartography map items. | Containers, Mobile phones, and Cartography maps. |
| **Send to** | Opens a submenu of valid destinations (`Inventory`, `Belt`, or specific containers/pockets) to move items. Liquids will only display containers that have `allow_liquid="true"` and space available. | Items in containers, nearby, or player possession. |
| **Crafts** | Opens a submenu showing related craft, repair, and dismantle recipes for that item, plus an `Open Craft` option that filters the crafting menu. | Items that are ingredients, repair targets, or dismantle sources. |
| **Install on Vehicle** | Opens a submenu (`Key Slot`, `Fuel Tank`, `Engine`, `Battery`, or tire slots) to install the part or pour fuel into a nearby vehicle. Non-key parts are only enabled when the vehicle has its key in the ignition slot. | Compatible vehicle parts or fuel in player possession when near a vehicle. |

---

## 2. Vehicles & Vehicle Equipment
| Option | Description | Requirements / When It Appears |
| :--- | :--- | :--- |
| **Vehicle options** | Opens the Vehicle dashboard modal to view mechanics, speed, headlights, and engine status. | Right-clicking a vehicle on the world map (Requires key in key slot). |
| **Trunk** | Opens the vehicle storage container modal. | Right-clicking a vehicle on the world map (Requires key in key slot). |
| **Send to -> Inventory** | Removes an installed vehicle component (Engine, Battery, Key, Tires) and places it into the player's inventory. | Right-clicking a part in the Vehicle Mechanics tab (Requires key in key slot). |
| **Remove fuel to** | Opens a submenu of valid player liquid containers (`allow_liquid="true"`) to siphon fuel units out of the vehicle tank. | Right-clicking the Fuel slot in the Vehicle Mechanics tab (Requires key in key slot). |

---

## 3. World Map Tiles (Doors, Windows, Barricades, and Ports)
| Option | Description | Requirements / When It Appears |
| :--- | :--- | :--- |
| **Open door/window** | Toggles a closed door or window to its open state. | Interacting with a closed door/window within interaction range (cannot be barricaded). |
| **Close door/window** | Toggles an open door or window to its closed state. If the player is standing in the doorway, it prevents closing. | Interacting with an open door/window. |
| **Place barricade** | Uses a barricade item and required tools from player inventory to mount a defensive barricade on the tile. | Intact door or window without an existing barricade. |
| **Remove barricade** | Disassembles an existing barricade using tools (Crowbar, Hammer) and returns the barricade item to inventory. | Barricaded door or window. |
| **Repair Door/Window** | Reconstructs broken doors/windows using raw materials (wood, nails, hinges) and magazine recipes. | Broken doors or windows (`_broke`). |
| **Travel to** | Opens a submenu displaying reachable island sectors or the Lobby chunk along with their required fuel cost. Selecting a sector consumes fuel and teleports the boat and player. | Right-clicking a boat (`tp_boat`) at the port/shore. |
| **Toggle Light** | Switches streetlamps and map lights on or off. | Right-clicking map light fixtures. |

---

## 4. Containers, Ground, and NPCs
| Option | Description | Requirements / When It Appears |
| :--- | :--- | :--- |
| **Talk** | Opens the NPC dialogue modal to initiate conversations, accept quests, and trade. | Right-clicking a friendly, non-aggroed NPC within range. |
| **Open (Corpse)** | Opens the corpse container window to loot gear, clothing, and dropped belongings. | Right-clicking a corpse on the ground. |
| **Grab / Grab One / Grab Half / Grab All** | Transmits solid items from the ground or nearby containers directly into the player's inventory. Liquids do not show Grab options to prevent bare-hand pickup. | Items lying on the ground or inside nearby containers. |
| **Status / Inventory / Gear** | Opens the corresponding player modal. | Right-clicking on the player character itself. |
