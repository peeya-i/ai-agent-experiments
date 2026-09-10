"""Unit tests for plant-care-skill: template integrity, manifest, and tool routines."""

from pathlib import Path
import pytest
import yaml

BASE_DIR = Path(__file__).parent.parent
SKILL_DIR = BASE_DIR / "skills" / "plant-care-skill"
TEMPLATE_PATH = SKILL_DIR / "templates" / "plant_info.md"
MANIFEST_PATH = SKILL_DIR / "SKILL.md"

import sys
sys.path.append(str(SKILL_DIR / "scripts"))
from plant_tools import (
    get_plant_care_template,
    get_plant_care_instructions,
    list_common_houseplants,
)


def test_template_file_exists_and_has_comprehensive_sections():
    """Verify plant_info.md exists and contains all required comprehensive care sections."""
    assert TEMPLATE_PATH.exists()
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "# Plant Info" in content
    assert "## Plant Information" in content
    assert "## 1. Soil and Potting" in content
    assert "## 2. Light" in content
    assert "## 3. Watering" in content
    assert "## 4. Temperature and Humidity" in content
    assert "## 5. Routine Maintenance" in content or "## 5. Maintenance" in content
    assert "## 6. Propagation" in content
    assert "7. Common Pests" in content or "Pests" in content
    assert "Safety" in content or "Toxicity" in content


def test_skill_manifest_yaml():
    """Verify SKILL.md contains valid YAML frontmatter and required keywords/tools."""
    assert MANIFEST_PATH.exists()
    content = MANIFEST_PATH.read_text(encoding="utf-8")
    assert content.startswith("---")
    parts = content.split("---", 2)
    assert len(parts) >= 3

    meta = yaml.safe_load(parts[1])
    assert meta["name"] == "plant-care-skill"
    assert "plant" in meta["keywords"]
    assert "care" in meta["keywords"]
    assert "tools" in meta
    tool_names = [t["name"] for t in meta["tools"]]
    assert "get_plant_care_instructions" in tool_names
    assert "get_plant_care_template" in tool_names


def test_get_plant_care_template():
    """Verify get_plant_care_template returns complete markdown text."""
    template = get_plant_care_template()
    assert isinstance(template, str)
    assert len(template) > 500
    assert "Soil and Potting" in template
    assert "Watering" in template


def test_get_plant_care_instructions_known_plant():
    """Verify care guide generation for a known curated plant (Monstera)."""
    res = get_plant_care_instructions("Monstera Deliciosa")
    assert res["status"] == "success"
    assert res["matched_profile"] is True
    guide = res["formatted_guide"]
    assert "Monstera deliciosa" in guide
    assert "Araceae" in guide
    assert "Soil and Potting" in guide
    assert "Watering & Moisture" in guide
    assert "Toxic to cats and dogs" in guide


def test_get_plant_care_instructions_snake_plant():
    """Verify care guide generation for Snake Plant."""
    res = get_plant_care_instructions("Snake Plant")
    assert res["status"] == "success"
    assert res["matched_profile"] is True
    guide = res["formatted_guide"]
    assert "Dracaena trifasciata" in guide
    assert "Asparagaceae" in guide
    assert "drought-tolerant" in guide.lower() or "soak-and-dry" in guide.lower()


def test_get_plant_care_instructions_generic_fallback():
    """Verify fallback guide generation for any unlisted plant."""
    res = get_plant_care_instructions("Calathea Orbifolia")
    assert res["status"] == "success"
    assert res["matched_profile"] is False
    guide = res["formatted_guide"]
    assert "Calathea Orbifolia" in guide
    assert "Soil and Potting" in guide
    assert "Light Requirements" in guide


def test_list_common_houseplants():
    """Verify list_common_houseplants returns curated botanical profiles."""
    plants = list_common_houseplants()
    assert isinstance(plants, list)
    assert len(plants) >= 4
    names = [p["name"] for p in plants]
    assert any("Monstera" in n for n in names)
    assert any("Snake Plant" in n for n in names)
    assert any("Fiddle Leaf" in n for n in names)
