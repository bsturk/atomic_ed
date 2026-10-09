"""D-Day unit labels from INVADE.EXE's DescStr and TypeStr tables.

Object 3 offsets 0x6c64 and 0x6df0; PrintUnitName/OkToPrintType combine them.
These are descriptors and classes, not battalion/company sizes.
"""

TYPE_DESCRIPTIONS = (
    '',  # 0
    'Airborne',  # 1
    'Heavy',  # 2
    'Semi-Motor',  # 3
    'Motorized',  # 4
    'Mot Light',  # 5
    'Mot Heavy',  # 6
    'Mech Recon',  # 7
    'Glider',  # 8
    'Fortress',  # 9
    'Naval',  # 10
    'SP AT',  # 11
    'RR Constr',  # 12
    'Rocket',  # 13
    'Coastal',  # 14
    'Light',  # 15
    'Regimental',  # 16
    'Corps',  # 17
    'Korps',  # 18
    'Divisional',  # 19
    'KG',  # 20
    'Combat',  # 21
    'Towed',  # 22
    'Arm. Fld',  # 23
    'Field',  # 24
    'Ost',  # 25
    'Garrison',  # 26
    'Tank Destroyer',  # 27
    'Recon',  # 28
    'Security',  # 29
    'Battleship',  # 30
    'Hvy Cruiser',  # 31
    'Monitor',  # 32
    'Lt Cruiser',  # 33
    'Destroyer',  # 34
    'Hvy Bomber',  # 35
    'Med Bomber',  # 36
    'Lt Bomber',  # 37
    'Fighter',  # 38
    'Panzer',  # 39
    'Tank',  # 40
    'Hvy Mortar',  # 41
    'Light Tank',  # 42
    'Armee',  # 43
    'Heavy AA',  # 44
    'Light AA',  # 45
    'Airborne AA',  # 46
    'Light Panzer',  # 47
    'Mach. Gun',  # 48
    'Light Flak',  # 49
    'Bicycle',  # 50
    'Heavy Flak',  # 51
    'Assault Gun',  # 52
    'Mot Hvy Flak',  # 53
    'Mot Lt Flak',  # 54
    'Mot Recon',  # 55
    'Mot MG',  # 56
    'Ground Attk',  # 57
    'Mountain',  # 58
    'Ski',  # 59
    'Police',  # 60
    'Construct',  # 61
    'Artillery',  # 62
    'Bridging',  # 63
    'Ranger',  # 64
    'Armored',  # 65
    'Motorcycle',  # 66
    'SP',  # 67
    'Brigade',  # 68
    'Airb MG',  # 69
    'Army',  # 70
    'Rifle',  # 71
    'Sub MG',  # 72
    'Mortar',  # 73
    'Mot. Rifle',  # 74
    'Heavy Tank',  # 75
    'Cavalry',  # 76
    'Cav_Recon',  # 77
    'Brigade',  # 78
    'Motorized',  # 79
    'Mech Recon',  # 80
    'Assault Gun',  # 81
    'Police',  # 82
    'Corps',  # 83
    'Motorized',  # 84
    'Rocket',  # 85
    '',  # 86
    'Rifle',  # 87
    'Divisional',  # 88
    'Recon',  # 89
    'Towed',  # 90
    'Observation',  # 91
    'Front',  # 92
    'Mech Engineer',  # 93
    'Air Transport',  # 94
    'Air Recce',  # 95
    'CCA',  # 96
    'CCB',  # 97
    'Airbne Recce',  # 98
)
UNIT_CLASSES = ('Infantry', '', 'Engineer', 'Anti-Tank', 'Artillery', '', 'Group', 'HQ', '')
STANDALONE_DESCRIPTIONS = {0x47, 0x40, 0x3e, 0x4a, 0x4c, 0x4d, 0x5d}


def unit_type_name(type_code, unit_class=None):
    if not 0 <= type_code < len(TYPE_DESCRIPTIONS):
        return f'Type {type_code}'
    description = TYPE_DESCRIPTIONS[type_code]
    if unit_class is None:
        return description or f'Type {type_code}'
    if type_code not in STANDALONE_DESCRIPTIONS and 0 <= unit_class < len(UNIT_CLASSES):
        description = f'{description} {UNIT_CLASSES[unit_class]}'.strip()
    return description or f'Type {type_code} / class {unit_class}'
