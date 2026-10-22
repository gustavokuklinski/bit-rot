### 1. God mode
| Command | Info |
| :--- | :--- |
| `%rot god` | God mode |

### 2. Item, Cloth and Vehicle spawn
| Command | Info |
| :--- | :--- |
| `%rot item "[ITEM_NAME]"` | Spawn item in inventory | 
| `%rot cloth "[CLOTH_NAME]"`| Spawn cloth in inventory | 
| `%rot vehicle "[VEHICLE_NAME]"`| Spawn vehicle near player | 

### 3. Weather controls
| Command | Info |
| :--- | :--- |
| `%rot weather rain`| Starts the rainfall effect and rain audio. | 
| `%rot weather fog`| Starts the heavy fog blanket and camera ease mask. | 
| `%rot weather rain_fog`| Combines rainfall and heavy fog simultaneously. | 
| `%rot weather clear`| Clears all rain and fog effects. | 
| `%rot time sun`| Jumps to 12:00 (midday daylight), switches ambient audio to daytime, and restores full day lighting. | 
| `%rot time night`| Jumps to 00:00 (midnight), switches ambient audio to nighttime, and engages dark ambient lighting. | 

### 4. Zombies, animals and NPCs

#### 4.1. Remove
| Command | Info |
| :--- | :--- |
| `%rot remove zombies`| Instantly removes all zombies from the active chunk and memory | 
| `%rot remove npc`| Instantly removes all NPCs from the active chunk and memory | 
| `%rot remove animals`| Instantly removes all animals from the active chunk and memory | 

#### 4.2. Spawn
| Command | Info |
| :--- | :--- |
| `%rot spawn zombies`| Respawns zombies on the map's 'Z' markers | 
| `%rot spawn npc`| Respawns NPCs on the map's 'NPC' and 'SNPC' markers | 
| `%rot spawn animals`| Respawns diverse animals on the map's 'ANM' markers | 

#### 4.3. Debug Info
| Command | Info |
| :--- | :--- |
| `%rot radius all`| Display a radius debug on Zombies and Hostile NPCs | 
| `%rot radius hostilenpc`| Display a radius debug on Hostile NPCs | 
| `%rot radius off`| Turn off the radius | 

### 5. Server
The game Multiplayer is based only at player chats and Radio communictions

| Command | Info |
| :--- | :--- |
| `%rot server` | View server status |
| `%rot server port [PORT]` | Open server at selected port |
| `%rot server peer [N]` | Open server with max peers |
| `%rot server open` | Server status and connected peers as default: 4 peers at port 7071 |
| `%rot <FREQ> "[TEXT_MESSAGE]"` | Send text message to peer |
| `%rot <FREQ> send "[ITEM_NAME]"` | Send inventory item to peer at the same radio frequency |