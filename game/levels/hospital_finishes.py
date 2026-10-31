"""Material roles shared by the two versions of the same hospital."""


def hospital_palette(peaceful):
    common = {
        "brushed_metal": "brushed_steel", "bed_linen": "linen_ivory",
        "bed_blanket": "blanket_sage", "privacy_fabric": "curtain_sage",
        "ceramic": "ceramic_white", "furniture_wood": "oak_veneer",
        "sofa_fabric": "vinyl_burgundy", "chair_fabric": "vinyl_sage",
        "roof_concrete": "ceiling_concrete",
    }
    if peaceful:
        return common | {
            "hospital_tiles": "tile_cream_clean", "wall_tile_clinical": "tile_mint_clean",
            "wall_tile_ward": "paint_sage", "plaster": "paint_ivory",
            "hospital_floor": "terrazzo_gray", "lobby_floor": "terrazzo_gray",
            "clinical_floor": "tile_mint_clean", "ward_floor": "linoleum_sage",
            "office_floor": "linoleum_blue_clean", "storage_floor": "terrazzo_brown",
            "concrete": "terrazzo_gray", "stair_wall": "stair_diamond_burgundy",
            "rail_metal": "metal_scratched_dark", "skirting": "metal_scratched_dark",
            "rust": "brushed_steel", "rust_iron_heavy": "enamel_white",
            "medical_enamel": "enamel_white", "wood": "oak_veneer",
            "concrete_cracked": "paint_ivory", "door_aged_wood": "door_painted_teal",
            "ceiling_room": "ceiling_clean", "ceiling_clinical": "ceiling_clean",
            "ceiling_mold": "ceiling_clean", "wall_tile_frame": "paint_ivory",
            "door_panel": "paint_mint",
        }
    return common | {
        "hospital_tiles": "hospital_tile_ruined", "wall_tile_clinical": "hospital_tile_mint",
        "wall_tile_ward": "plaster_peeling_green", "plaster": "plaster_water_damage",
        "hospital_floor": "floor_tile_dirty", "lobby_floor": "floor_tile_dirty",
        "clinical_floor": "hospital_checker", "ward_floor": "linoleum_green",
        "office_floor": "linoleum_blue_gray", "storage_floor": "concrete_damp",
        "concrete": "concrete_cracked", "stair_wall": "stair_diamond_cold",
        "rail_metal": "rust_iron_heavy", "skirting": "metal_chipped_olive",
        "rust": "metal_scratched_dark", "medical_enamel": "metal_chipped_white",
        "wood": "door_aged_wood", "furniture_wood": "door_aged_wood",
        "bed_linen": "linen_worn", "bed_blanket": "blanket_worn",
        "sofa_fabric": "vinyl_burgundy_worn", "chair_fabric": "vinyl_sage_worn",
        "privacy_fabric": "curtain_worn", "ceiling_room": "ceiling_stained",
        "ceiling_clinical": "ceiling_acoustic_panels", "wall_tile_frame": "concrete_cracked",
        "door_panel": "door_aged_wood",
    }


MATERIAL_ROLES = frozenset(hospital_palette(False)) | frozenset(hospital_palette(True))
