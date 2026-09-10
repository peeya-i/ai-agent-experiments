"""Unit tests for house-registry-skill flat-file database routines."""

import pytest
import sys
from pathlib import Path

# Add skill path
SKILL_PATH = Path(__file__).parent.parent / "skills" / "house-registry-skill" / "scripts"
if str(SKILL_PATH) not in sys.path:
    sys.path.insert(0, str(SKILL_PATH))

from registry_tools import lookup_house_record, list_registry_records, search_by_criteria


def test_lookup_smith_record():
    """Verify exact match for Smith from specification: Smith,New York,USA,red."""
    res = lookup_house_record("Smith")
    assert res["status"] == "found"
    assert res["name"] == "Smith"
    assert res["city"] == "New York"
    assert res["country"] == "USA"
    assert res["house_color"] == "red"


def test_lookup_case_insensitivity():
    """Verify case-insensitive containment matching."""
    res_lower = lookup_house_record("smith")
    assert res_lower["status"] == "found"
    assert res_lower["name"] == "Smith"

    res_upper = lookup_house_record("TANAKA")
    assert res_upper["status"] == "found"
    assert res_upper["city"] == "Tokyo"
    assert res_upper["house_color"] == "white"


def test_lookup_non_existent_blocks_hallucination():
    """Verify unknown residents return not_found status without hallucinated data."""
    res = lookup_house_record("UnknownResident999")
    assert res["status"] == "not_found"
    assert "No record found" in res["message"]


def test_list_registry_records():
    """Verify all database rows are returned."""
    res = list_registry_records()
    assert res["status"] == "success"
    assert res["total_count"] >= 10
    names = [row["name"] for row in res["records"]]
    assert "Smith" in names
    assert "Johnson" in names
    assert "Tanaka" in names


def test_search_by_criteria():
    """Verify filtering records by city and house color."""
    res_city = search_by_criteria(city="London")
    assert res_city["match_count"] >= 1
    assert res_city["matches"][0]["name"] == "Johnson"

    res_color = search_by_criteria(house_color="green")
    assert res_color["match_count"] >= 1
    assert res_color["matches"][0]["name"] == "Davis"
