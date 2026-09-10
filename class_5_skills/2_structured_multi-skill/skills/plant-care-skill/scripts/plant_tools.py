"""Horticultural reference routines and template formatting for plant-care-skill."""

from pathlib import Path
from typing import Any, Dict, List, Optional

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "plant_info.md"

# Curated reference database of popular indoor & ornamental plants
KNOWN_PLANT_PROFILES: Dict[str, Dict[str, Any]] = {
    "monstera": {
        "common_name": "Monstera Deliciosa (Swiss Cheese Plant)",
        "scientific_name": "Monstera deliciosa",
        "family": "Araceae",
        "native_region": "Tropical rainforests of Southern Mexico and Central America",
        "growth_habit": "Climbing evergreen epiphyte; indoor height 6-10 ft; moderate to fast growth",
        "soil": "Chunky, well-draining aroid mix: 40% peat/coco coir, 30% orchid bark, 20% perlite, 10% worm castings (pH 5.5 - 7.0)",
        "light": "Bright, indirect sunlight. Can tolerate gentle morning direct sun; harsh afternoon direct rays scorch foliage.",
        "watering": "Water when top 2-3 inches of soil feel dry. Soak thoroughly until water drains freely from bottom; reduce in winter.",
        "temp_humidity": "Ideal 18°C - 27°C (65°F - 80°F). Avoid temperatures below 10°C (50°F). Prefers >60% humidity; tolerates normal indoor 40-50%.",
        "maintenance": "Fertilize monthly in spring/summer with balanced water-soluble foliage fertilizer (20-20-20). Repot every 1-2 years.",
        "propagation": "Stem cuttings with at least 1 node and aerial root placed in water or damp sphagnum moss; air layering.",
        "safety": "Toxic to cats and dogs (ASPCA). Contains insoluble calcium oxalate crystals causing oral irritation and vomiting.",
    },
    "snake plant": {
        "common_name": "Snake Plant (Mother-in-Law's Tongue)",
        "scientific_name": "Dracaena trifasciata (formerly Sansevieria trifasciata)",
        "family": "Asparagaceae",
        "native_region": "Tropical West Africa (Nigeria to Congo)",
        "growth_habit": "Upright, architectural rhizomatous succulent; indoor height 2-4 ft; slow growth",
        "soil": "Gritty, fast-draining cactus/succulent soil mix with coarse sand, perlite, and pumice (pH 6.0 - 7.5)",
        "light": "Extremely versatile: thrives in bright indirect light; tolerates low light and full direct morning sun.",
        "watering": "Drought-tolerant soak-and-dry: allow soil to dry completely between waterings (every 2-4 weeks). Winter: once every 6 weeks.",
        "temp_humidity": "Ideal 15°C - 29°C (60°F - 85°F). Not cold-hardy; keep above 10°C (50°F). Thrives in average to low household humidity (30-50%).",
        "maintenance": "Minimal fertilizing: 1-2 times during active spring/summer growth at half-strength. Prune only damaged outer leaves.",
        "propagation": "Rhizome division during repotting (best method) or leaf cuttings in water/soil (variegated edges may revert to green).",
        "safety": "Toxic to pets (dogs and cats). Contains saponins that cause gastrointestinal irritation and nausea.",
    },
    "fiddle leaf fig": {
        "common_name": "Fiddle Leaf Fig",
        "scientific_name": "Ficus lyrata",
        "family": "Moraceae",
        "native_region": "Lowland tropical rainforests of Western Africa",
        "growth_habit": "Upright indoor tree; mature indoor height 6-10 ft; moderate growth",
        "soil": "Rich, well-aerated potting mix: peat moss, pine bark, perlite with excellent drainage (pH 6.0 - 6.8)",
        "light": "Demands abundant bright, filtered/indirect sunlight. Needs 4-6 hours of consistent bright light near an East or South-facing window.",
        "watering": "Water thoroughly when the top 1-2 inches of soil dry out. Ensure pot drains completely; sensitive to cold drafts and soggy roots.",
        "temp_humidity": "Ideal 18°C - 24°C (65°F - 75°F). Sensitive to drafts and temperatures below 13°C (55°F). Enjoys medium-to-high humidity (>50%).",
        "maintenance": "Fertilize once a month with 3-1-2 high-nitrogen fertilizer during spring/summer. Wipe broad leaves regularly with a damp cloth.",
        "propagation": "Stem tip cuttings or air layering during warm summer months.",
        "safety": "Toxic to dogs and cats (ASPCA). White sap contains proteolytic enzymes and ficin, causing oral and dermal irritation.",
    },
    "pothos": {
        "common_name": "Golden Pothos (Devil's Ivy)",
        "scientific_name": "Epipremnum aureum",
        "family": "Araceae",
        "native_region": "Moist rainforests of French Polynesia (Mo'orea)",
        "growth_habit": "Trailing/climbing vining plant; vine length 6-10 ft indoors; fast growth",
        "soil": "Standard nutrient-rich potting soil amended with perlite and peat moss (pH 6.1 - 6.8)",
        "light": "Medium to bright indirect light for vibrant variegation. Exceptionally tolerant of low light and artificial office lighting.",
        "watering": "Water when top 50% of the soil has dried out. Drooping leaves signal thirst; resilient to occasional missed waterings.",
        "temp_humidity": "Ideal 18°C - 29°C (65°F - 85°F). Minimum safe temp 10°C (50°F). Tolerates standard room humidity (40-60%).",
        "maintenance": "Trim trailing vines to encourage bushy growth. Feed monthly during growing season with balanced houseplant fertilizer.",
        "propagation": "Very easy: stem cuttings with 2-3 nodes placed in clean water root within 7-14 days.",
        "safety": "Toxic to dogs and cats due to insoluble calcium oxalates. Causes swelling, drooling, and digestive distress.",
    },
    "peace lily": {
        "common_name": "Peace Lily",
        "scientific_name": "Spathiphyllum wallisii",
        "family": "Araceae",
        "native_region": "Tropical rainforests of Central and South America",
        "growth_habit": "Clumping herbaceous perennial with white flower spathes; height 1-3 ft; moderate growth",
        "soil": "Moisture-retentive yet well-aerated potting mix containing peat, perlite, and compost (pH 5.8 - 6.5)",
        "light": "Thrives in low to medium indirect light; direct sunlight burns delicate leaves. White blooms appear reliably in bright indirect spots.",
        "watering": "Keep soil evenly moist but never waterlogged. Dramatic wilting signals need for water, rebounds quickly after hydration.",
        "temp_humidity": "Ideal 18°C - 27°C (65°F - 80°F). Cold sensitive (<12°C/54°F). Prefers elevated humidity (>50%); mist or use pebble tray.",
        "maintenance": "Prune spent blooms at base of flower stalk. Feed every 6 weeks during spring/summer at 1/4 strength.",
        "propagation": "Crown and rhizome division during spring repotting.",
        "safety": "Toxic to pets and children. Insoluble calcium oxalates cause oral burning, difficulty swallowing, and nausea.",
    },
}


def get_plant_care_template() -> str:
    """Retrieve the comprehensive markdown template for formatting plant care and botanical information.

    Returns:
        The markdown text template loaded from skills/plant-care-skill/templates/plant_info.md.
    """
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    return "# Plant Info and Care Guide\n\nTemplate file not found."


def get_plant_care_instructions(plant_name: str) -> Dict[str, Any]:
    """Get standardized, comprehensive plant care instructions and botanical guide for a specific plant name.

    Args:
        plant_name: Common or scientific name of the plant (e.g., 'Monstera Deliciosa', 'Snake Plant', 'Fiddle Leaf Fig').

    Returns:
        A structured dictionary containing:
        - status: 'success'
        - plant_name: Requested plant name
        - matched_profile: Botanical profile details (family, soil, light, watering, safety) if matched
        - care_template: The comprehensive template markdown text
        - instructions_markdown: Pre-formatted markdown guide matching the template structure.
    """
    clean_name = plant_name.strip()
    norm_name = clean_name.lower()

    # Match against known profile or generate structured parameters
    profile = None
    for key, data in KNOWN_PLANT_PROFILES.items():
        if key in norm_name or norm_name in key:
            profile = data
            break

    template_text = get_plant_care_template()

    if profile:
        formatted_guide = f"""# Plant Info and Comprehensive Care Guide

## Plant Information
* **Common Name:** {profile['common_name']}
* **Scientific Name:** *{profile['scientific_name']}*
* **Family:** {profile['family']}
* **Native Region & Habitat:** {profile['native_region']}
* **Growth Habit & Mature Size:** {profile['growth_habit']}
* **General Overview:** Highly regarded ornamental plant prized for indoor foliage aesthetics and adaptable growth.

---

## 1. Soil and Potting
* **Soil Type & Mix:** {profile['soil']}
* **Drainage Requirements:** Free-draining container with drainage holes is required to prevent water stagnation.
* **Pot Sizing:** Pot with 1-2 inches of root clearance; terracotta or ceramic recommended.

---

## 2. Light Requirements
* **Light Preference:** {profile['light']}
* **Window Placement:** Near East or shaded South/West-facing windows with diffused lighting.

---

## 3. Watering & Moisture
* **Watering Technique & Frequency:** {profile['watering']}
* **Water Quality:** Best with filtered or room-temperature tap water allowed to sit for 24 hours.
* **⚠️ Overwatering Warnings:** Ensure roots never sit in standing saucer water.

---

## 4. Temperature and Humidity
* **Temperature Range:** {profile['temp_humidity']}
* **Humidity:** Maintain recommended levels via pebble trays or room humidifiers.

---

## 5. Routine Maintenance & Grooming
* **Maintenance & Fertilizing:** {profile['maintenance']}

---

## 6. Propagation
* **Recommended Methods:** {profile['propagation']}

---

### ⚠️ Important Safety & Toxicity Note
* **Toxicity:** {profile['safety']}
* **Precautions:** Keep out of reach of curious dogs, cats, and small children. Wash hands after pruning.
"""
    else:
        formatted_guide = f"""# Plant Info and Comprehensive Care Guide

## Plant Information
* **Common Name:** {clean_name}
* **Family & Origin:** Botanical family specific to {clean_name}.
* **General Overview:** Standard horticultural care guide for {clean_name}.

---

## 1. Soil and Potting
* **Soil Type & Mix:** Nutrient-rich, well-draining indoor potting mix amended with perlite (30%) and organic compost.
* **Potting:** Container with unobstructed drainage holes.

---

## 2. Light Requirements
* **Light Preference:** Medium to bright indirect sunlight; protect delicate foliage from intense direct midday sun.

---

## 3. Watering & Moisture
* **Watering Frequency:** Allow top 1-2 inches of substrate to dry out between waterings. Reduce frequency in winter dormancy.

---

## 4. Temperature and Humidity
* **Temperature Range:** Average indoor temperature of 18°C - 24°C (65°F - 75°F); keep away from cold drafts.
* **Humidity:** 40% - 60% ambient relative humidity.

---

## 5. Routine Maintenance & Grooming
* **Maintenance:** Feed monthly with balanced water-soluble fertilizer at half-strength during active growing season.

---

## 6. Propagation
* **Recommended Methods:** Stem cuttings in water or potting soil; division during spring repotting.

---

### ⚠️ Important Safety & Toxicity Note
* **Toxicity:** Check specific toxicity status before placing near pets. Use gardening gloves when pruning.
"""

    return {
        "status": "success",
        "plant_name": clean_name,
        "matched_profile": profile is not None,
        "profile_summary": profile if profile else {"name": clean_name, "general": "Standard indoor horticultural protocol"},
        "care_template": template_text,
        "formatted_guide": formatted_guide,
    }


def list_common_houseplants() -> List[Dict[str, str]]:
    """List popular and common houseplants with their botanical classifications.

    Returns:
        A list of dictionaries with common name, scientific name, family, and pet safety note.
    """
    return [
        {
            "name": p["common_name"],
            "scientific_name": p["scientific_name"],
            "family": p["family"],
            "pet_safety": p["safety"].split(".")[0],
        }
        for p in KNOWN_PLANT_PROFILES.values()
    ]
