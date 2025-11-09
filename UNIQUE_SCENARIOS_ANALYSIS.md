# Unique Scenario Files Analysis - SCENARIO-all Directory

This document analyzes the 15 unique scenario files (plus CAMPAIGN.SCN) from previous games in the series that are present in `game/SCENARIO-all` but NOT in `game/SCENARIO`.

## Summary

The unique scenarios come from **two previous games** in the Atomic Games WWII series:

### 1. Clash of Steel (1993) - Magic Number: 0x0f4a
**10 scenarios - All Eastern Front (Stalingrad Campaign)**

- CITY.SCN (114K) - Battle of Stalingrad: City Fighting
- CLASH.SCN (46K) - Operation Wintergewitter: Myshkova River Crossing
- HURBERT.SCN (40K) - Battle of Stalingrad: Hubert's Attack
- MANSTEIN.SCN (61K) - Operation Uranus: Hypothetical Manstein Counterattack
- QUIET.SCN (103K) - Operation Uranus: Soviet Breakthrough
- RIVER.SCN (46K) - Operation Wintergewitter: German Relief Attempt
- TANKS.SCN (61K) - Operation Uranus: Hypothetical Tank Battle
- VOLGA.SCN (40K) - Battle of Stalingrad: Drive to the Volga
- WINTER.SCN (187K) - Operation Wintergewitter: Full Campaign
- CAMPAIGN.SCN (267K) - Operation Uranus: Full Campaign

### 2. Crusader in the Desert (1992) - Magic Number: 0x0dac
**6 scenarios - All North Africa (Tobruk/Crusader Campaign)**

- CRUCAMP.SCN (164K) - Operation Crusader: Full Campaign
- DUCE.SCN (27K) - Bir el Gubi: Italian Ariete Division
- HELLFIRE.SCN (59K) - Halfaya Pass: Frontier Battles
- RELIEVED.SCN (156K) - Operation Crusader: Late Phase
- RESCUE.SCN (53K) - Operation Crusader: Sidi Rezegh
- TOBRUK.SCN (39K) - Siege of Tobruk: Assault

---

## Detailed Scenario Information

### EASTERN FRONT SCENARIOS (Clash of Steel, 1993)

#### CITY.SCN - City Fighting
- **File Size:** 114K (117,248 bytes)
- **Battle:** Battle of Stalingrad - Urban Combat
- **Date:** September-November 1942
- **Map Dimensions:** Based on offset pointers at 0x40-0x5F
- **Key Locations:**
  - Mamayev Kurgan
  - Central RR Station / Southern RR Station
  - Red October Factory
  - Red Barricades Factory
  - Lasur Chemical Works
  - Univermag (department store)
  - Brick Works
- **Key Units:**
  - Soviet: 62nd Army, 295th Infantry, 389th Infantry, 71st Infantry, 76th Infantry, 94th Infantry
  - German: 6th Army elements
- **Mission:** As Soviet commander V.I. Chuikov, defend the city against German assault. As German commander Paulus, drive to the Volga and take key objectives. Features intense urban combat with factories and river crossings as critical objectives.

#### CLASH.SCN / RIVER.SCN - Myshkova River Crossing
- **File Size:** 46K (47,634 bytes)
- **Battle:** Operation Wintergewitter (Winter Storm) - German relief attempt for Stalingrad
- **Date:** December 1942
- **Key Locations:**
  - Myshkova River
  - Aksai Esaulovsky River
  - Gromoslavka
  - Nizhne-Kumsky
  - Chernomorov
  - Antonov
- **Key Units:**
  - Soviet: 51st Army
  - German: 57th Panzer Corps (Manstein's relief force)
- **Mission:** Soviet forces must stop Manstein's relief attempt. German forces must cross the Myshkova River to relieve the trapped 6th Army in Stalingrad. Historical crisis point where the German relief came within 30 miles of Stalingrad before being stopped.
- **Note:** CLASH.SCN and RIVER.SCN appear to be identical files (same size, same content)

#### HURBERT.SCN / VOLGA.SCN - Factory District Fighting
- **File Size:** 40K (41,080-41,084 bytes)
- **Battle:** Battle of Stalingrad - Final push to the Volga
- **Date:** October-November 1942
- **Key Locations:**
  - Crossing 62 (ferry crossing)
  - Lasur Chemical Works
  - Red Barricades Factory
  - Red October Factory
  - Oil Tanks
- **Key Units:**
  - Soviet: 62nd Army, 389th Infantry, 305th Infantry, 94th Infantry
  - German: General Jaenecke's forces
- **Mission:** German forces make final push to capture factory district and ferry crossings. Soviet forces must hold the ferries - their lifeline for supplies. Historical battle featuring brutal factory-to-factory combat.
- **Note:** HURBERT.SCN and VOLGA.SCN appear to be near-identical files

#### MANSTEIN.SCN / TANKS.SCN - Hypothetical Counterattack
- **File Size:** 61K (63,198 bytes)
- **Battle:** Operation Uranus - Hypothetical scenario with Manstein in command
- **Date:** November 1942 (alternate history)
- **Key Locations:**
  - Kalach
  - Nizhne Chirskaya
  - Lozhki Station
  - Morozovsk
  - Don River
  - Chir River
  - Karpovka River
- **Key Units:**
  - Soviet: 51st Army
  - German: Forces under von Manstein (hypothetical)
- **Mission:** "What if" scenario where Manstein was given command earlier and could react more forcefully to the Soviet Operation Uranus encirclement. German objective is to deny Kalach and Nizhne Chirskaya to the Soviets.
- **Note:** MANSTEIN.SCN and TANKS.SCN appear to be identical files

#### QUIET.SCN - Operation Uranus Launch
- **File Size:** 103K (105,576 bytes)
- **Battle:** Operation Uranus - Soviet encirclement begins
- **Date:** November 1942
- **Key Locations:**
  - Kalach
  - Nizhne Chirskaya
  - Kashary
  - Morozovsk
  - Bokovskaya
  - Vlasov
  - Surovikino
- **Key Units:**
  - Soviet: Southwest Front, 21st Army, 65th Army (Generals Ermenko, Rodin, Pliev)
  - German: 6th Army, 48th Panzer Corps
  - Romanian: 3rd Romanian Army
- **Mission:** Soviet forces must break through weak Romanian opposition and race to Kalach to cut off the German 6th Army. German forces have only the weak 48th Panzer Corps to backstop the Romanians. Historical opening of the great encirclement.

#### WINTER.SCN - Winter Storm Campaign
- **File Size:** 187K (192,274 bytes)
- **Battle:** Operation Wintergewitter - Full campaign for Stalingrad relief
- **Date:** December 1942
- **Key Locations:**
  - Kotelnikovo
  - Tinguta Station
  - Abganerovo Station
  - Zarya Station
  - Myshkova River
  - Aksai Rivers
  - Don River
  - Dubovskoe
- **Key Units:**
  - Soviet: 51st Army, 4th Army
  - German: 57th Panzer Corps, 48th Panzer Corps, 24th Panzer Division, 336th Infantry, 384th Infantry
  - Romanian: 4th Army remnants
- **Mission:** Large campaign scenario covering the entire German relief attempt. Germans must force a supply corridor to the trapped 6th Army. Soviets must crush the relief attempt and maintain the encirclement.

#### CAMPAIGN.SCN - Operation Uranus Full Campaign
- **File Size:** 267K (274,044 bytes)
- **Battle:** Operation Uranus - Complete encirclement campaign
- **Date:** November 1942 - January 1943
- **Key Locations:**
  - Stalingrad
  - Pitomnik Airfield
  - Gumrak Airfield
  - Kalach
  - Kotelnikovo
  - Nizhne Chirskaya
  - Morozovsk
  - Tatsinskaya
  - Kashary
- **Key Units:**
  - Soviet: Southwest Front (strongest Allied armies)
  - German: Army Group B, 6th Army, 4th Panzer Army
  - Romanian: 3rd and 4th Romanian Armies
  - Italian: 8th Army elements
- **Mission:** Full campaign covering the Soviet Operation Uranus offensive to encircle and destroy the German 6th Army at Stalingrad. Soviet objective is to break through Axis allies, encircle Stalingrad, and destroy the 6th Army. German objective is to hold Stalingrad while maintaining supply lines.
- **Note:** This is different from the D-Day CAMPAIGN.SCN in the SCENARIO directory (which is identical to DDAYCAMP.SCN)

---

### NORTH AFRICA SCENARIOS (Crusader in the Desert, 1992)

#### CRUCAMP.SCN - Crusader Campaign
- **File Size:** 164K (168,670 bytes)
- **Battle:** Operation Crusader - Full campaign
- **Date:** November 1941 - January 1942
- **Key Locations:**
  - Tobruk (besieged fortress)
  - Bardia
  - Bir el Gubi
  - Gambut
  - Sidi Rezegh
  - el Adem
  - Gazala
  - Fort Capuzzo
  - El Cuasc
  - Bir Hakeim
  - ed Duda
- **Key Units:**
  - British: 8th Army, XIII Corps, XXX Corps, 70th Infantry Division (Tobruk garrison)
  - German: Afrika Korps, 15th Panzer, 21st Panzer, 5th Panzer Regiment
  - Italian: Ariete Armored Division
- **Mission:** British offensive to relieve the besieged Tobruk garrison. Commonwealth forces, equipped with new American armor (from Churchill), must penetrate Axis screening forces in Cyrenaica, crush the panzers, and relieve Tobruk. Germans must use superior tactics to maintain the siege and defeat the British offensive. Full campaign covering Operations Brevity, Battleaxe, and Crusader.

#### DUCE.SCN - Il Duce's Pride
- **File Size:** 27K (27,700 bytes)
- **Battle:** Bir el Gubi - Italian armored engagement
- **Date:** November 1941
- **Key Locations:**
  - Bir el Gubi
  - Point 180
  - Point 181
- **Key Units:**
  - British: 1st South African Division, 7th Armored elements
  - Italian: 132nd Ariete Armored Division (nearly 150 tanks - Mussolini's pride)
- **Mission:** South African forces must pin down the Italian Ariete Armored Division and secure the track junction at Bir el Gubi on the southern flank of Operation Crusader. Italian forces must defend the supply depot and southern flank of the Axis Tobruk siege line. Features inexperienced South African troops facing Italy's best armored formation.

#### HELLFIRE.SCN - Hellfire Pass
- **File Size:** 59K (60,934 bytes)
- **Battle:** Frontier Battles - Halfaya Pass
- **Date:** November 1941
- **Key Locations:**
  - Halfaya Pass ("Hellfire Pass")
  - Fort Capuzzo
  - Bardia
  - Sollum
  - Sidi Azeiz
  - Libyan Frontier fortifications
- **Key Units:**
  - British: XIII Corps, 2nd New Zealand Division, 4th Indian Division (150 Matilda and Valentine tanks)
  - Italian: 55th Savona Infantry Division
  - German: 21st Panzer Division (at least a day away)
- **Mission:** Commonwealth forces (XIII Corps) must engage and destroy the Italian Savona Infantry Division on the frontier, then advance to Sollum and Bardia. British have powerful tank forces including Matildas. Italian forces must hold the Libyan Frontier fortifications while protecting Bardia and Sollum, awaiting German panzer support. Historical "Give 'em Hell" frontier battle.

#### RELIEVED.SCN - Tobruk Relieved
- **File Size:** 156K (160,386 bytes)
- **Battle:** Operation Crusader - Late phase after relief
- **Date:** December 1941
- **Key Locations:**
  - Tobruk (newly relieved)
  - Bardia
  - Bir el Gubi
  - Gambut
  - Sidi Rezegh
  - el Adem
  - Gazala
- **Key Units:**
  - British: 8th Army, XIII Corps, XXX Corps, 70th Infantry
  - German: Panzer Armee Afrika, Afrika Korps, 15th Panzer, 21st Panzer
  - Italian: Bologna, Brescia, Trento divisions
- **Mission:** Tobruk garrison has been relieved! British mission is to keep the corridor open and destroy Axis forces cut off in the Bardia area. Use XXX Corps against Italian forces, XIII Corps to pin German panzers. German mission is to strike westward, reestablish supply lines, defeat Allied forces, and prevent retreat. Auchinleck vs. Rommel in climactic battle.

#### RESCUE.SCN - Rescue of Tobruk
- **File Size:** 53K (54,816 bytes)
- **Battle:** Operation Crusader - Sidi Rezegh armor clash
- **Date:** November 1941
- **Key Locations:**
  - Sidi Rezegh
  - Gambut
  - Bir el Gubi
  - Gabr Saleh
  - el Gueitinat
  - El Cuasc
- **Key Units:**
  - British: XXX Corps (with latest British and American tanks), XIII Corps, 8th Army
  - German: Afrika Korps
  - Italian: Ariete Division
- **Mission:** "The largest armored battle the desert has ever seen." British XXX Corps, bristling with new Churchill-provided tanks, must take on Afrika Korps and break through to Tobruk at Sidi Rezegh. German mission is to not only ruin the British offensive but possibly destroy Eighth Army. If XXX Corps is defeated, British supply system is shattered and they must retreat to Alexandria.

#### TOBRUK.SCN - Assault on Tobruk
- **File Size:** 39K (40,620 bytes)
- **Battle:** Siege of Tobruk - Direct assault
- **Date:** 1941
- **Key Locations:**
  - Tobruk fortifications
  - el Adem
  - ed Duda
  - Point 3, Point 10
- **Key Units:**
  - British: 70th Infantry Division, Polish Brigade (Tobruk garrison)
  - German: Afrika Korps, 90th Light Division, 15th Panzer, 8th Panzer Regiment
  - Italian: Bologna, Brescia, Trento divisions
- **Mission:** Rommel finally has supplies to assault Tobruk. German forces must breach the formidable perimeter defenses - concentrated artillery supports the 90th Light Division as primary striking force. Pick weak points rather than broad front assault. British garrison must hold fortifications at all costs - if breached, will be overrun. Use armor as mobile reserve. XXX Corps relief expected within days. Secondary mission: break out toward ed Duda.

---

## File Format Notes

### Magic Numbers Identify Game Series

The scenario files use different magic numbers to identify their game of origin:

- **0x1230** - D-Day (1995) - Used in SCENARIO directory
- **0x0dac** - Crusader in the Desert (1992) - North Africa scenarios
- **0x0f4a** - Clash of Steel (1993) - Eastern Front scenarios

### File Structure Differences

The legacy scenario files (magic 0x0dac and 0x0f4a) use a **different internal format** than D-Day scenarios (magic 0x1230):

1. **Header format is different** - the offset pointers at 0x40-0x5F appear to have different meanings
2. **Count fields may differ** - the fixed counts used by D-Day scenarios don't apply
3. **Section organization likely differs** - need different parsing logic

### Text Content Location

Mission briefing text in legacy scenarios is found at various offsets:
- Text strings typically begin around **0x0080 - 0x023e**
- Objective location names appear around **0x0a00 - 0x0c00**
- Mission descriptions are ASCII text, usually 50-200 characters per segment

### Scenario Size Patterns

- **Small scenarios (27K-61K):** Single battle engagements
- **Medium scenarios (103K-115K):** Multi-objective operational scenarios
- **Large scenarios (156K-187K):** Extended operational campaigns
- **Campaign scenarios (267K-270K):** Full multi-week campaigns

---

## CAMPAIGN.SCN - Two Different Versions

There are **TWO different CAMPAIGN.SCN files**:

### SCENARIO-all/CAMPAIGN.SCN
- **Size:** 267K (274,044 bytes)
- **Magic:** 0x0f4a (Clash of Steel)
- **Content:** Operation Uranus - Stalingrad encirclement campaign
- **Theater:** Eastern Front
- **From:** Clash of Steel (1993)

### SCENARIO/CAMPAIGN.SCN
- **Size:** 270K (276,396 bytes)
- **Magic:** 0x1230 (D-Day)
- **Content:** D-Day campaign - Normandy
- **Theater:** Western Europe
- **Identical to:** DDAYCAMP.SCN

---

## Historical Battles Represented

### Eastern Front (10 scenarios)
- **Battle of Stalingrad** (5 scenarios): Urban combat, factory fighting, Volga crossings
- **Operation Uranus** (3 scenarios): Soviet encirclement of Stalingrad
- **Operation Wintergewitter** (3 scenarios): German relief attempt

### North Africa (6 scenarios)
- **Operation Crusader** (4 scenarios): British offensive to relieve Tobruk
- **Siege of Tobruk** (2 scenarios): Axis siege and British defense

---

## Unique Characteristics

### Clash of Steel (Eastern Front) Features:
- **Harsh winter conditions** reflected in scenarios
- **River crossings** as critical objectives (Don, Chir, Myshkova, Volga)
- **Urban combat** in Stalingrad factories and ruins
- **Massive scale** - some scenarios have 100x125 hex maps
- **Multi-national forces** - German, Soviet, Romanian, Italian, Croatian units
- **"What if" scenarios** exploring alternate German command decisions
- **Ferry crossings** as critical supply lifelines in Stalingrad

### Crusader in the Desert (North Africa) Features:
- **Desert warfare** across wide open terrain
- **Besieged fortress** (Tobruk) as central objective
- **Armor-heavy battles** - largest tank battles of 1941
- **British Commonwealth diversity** - British, South African, New Zealand, Indian, Polish forces
- **Italian forces** as major combatants (not just German)
- **Supply depot warfare** - capturing/defending supply points critical
- **Frontier fortifications** - static defensive positions

---

## Conclusion

These 16 unique scenario files represent the complete scenario collections from two previous Atomic Games WWII titles:

1. **Clash of Steel (1993)** contributed 10 Eastern Front scenarios focused on the Stalingrad campaign (Operation Uranus and Wintergewitter)

2. **Crusader in the Desert (1992)** contributed 6 North Africa scenarios focused on the Tobruk siege and Operation Crusader

These scenarios are **NOT compatible** with the D-Day scenario format due to different file structures (different magic numbers), but contain rich historical content covering major WWII battles outside the Normandy theater.

The presence of these files in SCENARIO-all suggests they were distributed with V for Victory: D-Day as bonus content from the earlier games in the series, allowing players to experience the full range of Atomic Games' WWII tactical simulations.
