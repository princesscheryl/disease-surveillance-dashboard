"""
fetch_greater_accra.py

Extracts Greater Accra districts from ghana_districts.geojson and matches
them to the database district names.

Usage:
    python fetch_greater_accra.py

Output:
    greater_accra_districts.geojson
"""

import json

INPUT_FILE = "ghana_districts.geojson"
OUTPUT_FILE = "greater_accra_districts.geojson"

# Name mapping: GeoJSON name -> the database
#to fix common mismatches between the GeoJSON and the database
NAME_FIXES = {
    "Accra Metropolis": "Accra Metropolitan",
    "Ningo/prampram": "Ningo Prampram District",
    "Kpone Katamanso": "Kpone Katamanso Municipal",
    "La Dade-kotopon": "La Dade-Kotopon Municipal",
    "Shai Osudoku": "Shai Osudoku District",
    "Korle Klottey Municipal": "Korle-Klottey Municipal",
    "Weija Gbawe Municipal": "Weija-Gbawe Municipal",
    # New mappings found
    "Ada East": "Ada East District",
    "Ada West": "Ada West District",
    "Ga East": "Ga East Municipal",
    "Ayawaso West": "Ayawaso West Municipal",
    "La-nkwantanang-madina": "La Nkwantanang-Madina Municipal",
}


# List of Greater Accra districts we are looking for in the database
GREATER_ACCRA_DISTRICTS = [
    "Accra Metropolitan",
    "Tema Metropolitan",
    "Ga South Municipal",
    "Ga West Municipal",
    "Ga East Municipal",
    "Ga Central Municipal",
    "Ga North Municipal",
    "Adenta Municipal",
    "Ashaiman Municipal",
    "Tema West Municipal",
    "Tema East Municipal",
    "Tema Central Municipal",
    "Ledzokuku Municipal",
    "Kpone Katamanso Municipal",
    "La Dade-Kotopon Municipal",
    "Ningo Prampram District",
    "Shai Osudoku District",
    "Ada East District",
    "Ada West District",
    "Ayawaso West Municipal",
    "Ayawaso East Municipal",
    "Ayawaso North Municipal",
    "Ayawaso Central Municipal",
    "Ablekuma West Municipal",
    "Ablekuma Central Municipal",
    "Ablekuma North Municipal",
    "Ablekuma South Municipal",
    "Korle-Klottey Municipal",
    "Okaikoi North Municipal",
    "Okaikoi South Municipal",
    "Ashiedu Keteke Municipal",
    "Weija-Gbawe Municipal",
    "La Nkwantanang-Madina Municipal",
    "Krobo Municipal",
]


def fetch_greater_accra():
    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_features = len(data["features"])
    print(f"Found {total_features} districts in Ghana")

    matched_features = []
    matched_names = set()

    for feature in data["features"]:
        shape_name = feature["properties"]["shapeName"]
        
        # Apply name fix if we have a mapping
        fixed_name = NAME_FIXES.get(shape_name, shape_name)
        
        # Check if this is a Greater Accra district we want
        if fixed_name in GREATER_ACCRA_DISTRICTS:
            # Update the name in the feature to match database
            feature["properties"]["shapeName"] = fixed_name
            matched_features.append(feature)
            matched_names.add(fixed_name)
            print(f"  Matched: {shape_name} -> {fixed_name}")

    # Create new GeoJSON with only Greater Accra districts
    output_data = {
        "type": "FeatureCollection",
        "crs": data.get("crs"),
        "features": matched_features
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(matched_features)} Greater Accra districts to {OUTPUT_FILE}")
    
    # Show which districts not found
    missing = set(GREATER_ACCRA_DISTRICTS) - matched_names
    if missing:
        print(f"\nCould not find {len(missing)} districts:")
        for name in sorted(missing):
            print(f"  - {name}")
    else:
        print("\nFound all districts!")


if __name__ == "__main__":
    fetch_greater_accra()