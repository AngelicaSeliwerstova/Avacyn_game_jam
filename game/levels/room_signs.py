"""Readable third-floor door plaques, shared with the texture generator."""

PATIENT_SIGN_WIDTH = 1.65
PATIENT_SIGN_HEIGHT = 0.42
PATIENT_SIGNS = {f"patient_room_{index}": f"ПАЛАТА {301 + index}" for index in range(8)}
PATIENT_SIGNS.update({
    "patient_nurse_room": "ПОСТ\nМЕДСЕСТРЫ",
    "patient_east_entry": "ПАЛАТА 309",
    "patient_ward_313": "ПАЛАТА 313",
    "patient_child_room": "КОМНАТА",
    "patient_south_west": "ПАЛАТА 310",
    "patient_south_center": "ПАЛАТА 311",
    "patient_south_east": "ПАЛАТА 312",
})
