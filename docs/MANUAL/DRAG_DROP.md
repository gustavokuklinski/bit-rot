# Drag Drop

The drag-and-drop mechanics handle how items move between inventory slots, containers, the player belt, gear slots, vehicle equipment, and the game world. 

Below is the complete list of distinct drag operations available in the game:

## 1. Standard Slot-to-Slot Transfer (`inventory`, `belt`, `gear`, `container`)
* **How it works:** Left-clicking and dragging an item from any inventory container or slot to another valid destination slot.
* **Behavior:** 
  * If the target slot is empty, the item is moved there.
  * If the target slot contains a stackable, matching item, the items automatically merge (subject to stack capacities).
  * If the target slot contains a *different* item, the two items swap positions.

## 2. Stack Splitting (`SHIFT + Drag`)
* **How it works:** Holding the `Left Shift` or `Right Shift` key while starting a drag on a stackable item (e.g., ammo, resources, consumables with load > 1).
* **Behavior:** Splits exactly **1 unit** off the stack to be dragged under the cursor, leaving the remaining quantity in the origin slot. Dropping the single unit creates or merges it into a new stack.

## 3. Belt HUD Equipping & Unequipping
* **How it works:** Dragging an item from the inventory/container modal onto one of the 5 Belt slots at the bottom of the screen (or vice-versa).
* **Behavior:** 
  * Validates whether the item allows belt equipment (`allow_belt="true"`). Liquids and non-belt-compatible items are rejected.
  * Equipping a weapon to the belt automatically syncs it as the active combat weapon.

## 4. Gear Slot Worn Equipment
* **How it works:** Dragging clothing, armor, or utility bags from an inventory/container onto the specialized character gear slots (Head, Body, Legs, Feet, Arms, Util, etc.).
* **Behavior:** Validates slot compatibility (e.g., trousers cannot go on feet). Swapping items automatically equips the new piece and moves the old piece back into inventory or drops it if inventory is full.

## 5. Vehicle Equipment Installation (`Mechanics` Tab)
* **How it works:** Dragging parts (Motor, Battery, Tires, Fuel Units, Keys) from inventory onto the respective vehicle slots in the Vehicle modal's *Mechanics* tab.
* **Behavior:** 
  * Enforces security rules: Non-key parts (tires, motor, battery, fuel) cannot be installed or removed unless a valid vehicle key is inserted into the vehicle's **Key** slot.
  * Refueling pours liquid from a fuel container/unit directly into the vehicle's fuel tank.

## 6. External Container / Nearby Looting
* **How it works:** Dragging items between the player's personal inventory and an external container modal (e.g., Chests, Maptile containers, Corpses, Vehicle Trunks, or Ground tabs).
* **Behavior:** 
  * Enforces weight capacity limits (`container.weight * 5.0` or vehicle `max_weight`).
  * Triggers a timed action bar ("Looting / Storing") proportional to item weight when interacting with external world containers.

## 7. Mobile Phone App / SD Card Slotting (`Mobile` Modal)
* **How it works:** Dragging an SD Card item into one of the 5 app slots inside the Mobile Phone modal (`Apps` tab).
* **Behavior:** Unlocks active phone modules/apps (such as radar maps, trackers, or registers) in real-time. Removing the card instantly revives tracking modules.

## 8. World Drop & Spill Actions
* **How it works:** Dragging an item out of any UI modal and releasing the mouse button over the active game world area.
* **Behavior:** 
  * For solid items: Drops the item onto a free tile near the player's world position.
  * For liquid items: Instantly pours/spills the liquid onto the ground (or into a targeted map tile liquid container like a well), destroying the loose container contents if not caught by a container.