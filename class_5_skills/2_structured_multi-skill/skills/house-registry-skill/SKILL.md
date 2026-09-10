---
name: house-registry-skill
description: Strict registry resolution for property assets, resident locations, and house colors using flat-file database records.
keywords:
  - house
  - home
  - house color
  - resident
  - registry
  - address
  - property
  - owner
regex_targets:
  - "(?i)\\b(house|home|resident|registry|property)\\b"
  - "(?i)\\b(color|city|country|lives in|house color)\\b"
tools:
  - name: lookup_house_record
    description: Look up house registry records (resident name, city, country, house color) strictly from the flat-file database. Returns exact records or non-existence without hallucination.
    parameters:
      name:
        type: string
        description: Name of the person / resident to look up (e.g., 'Smith', 'Johnson', 'Davis').
  - name: list_registry_records
    description: Retrieve the full list of verified registry records from the local flat-file database.
    parameters: {}
---

# House Registry Skill

## Standard Operating Procedure (SOP)
1. **Strict Non-Hallucination Policy**: You MUST NOT guess, extrapolate, or invent property or resident details. Only information verified through containment scanning over `./data/registry.csv` may be reported.
2. **Case-Insensitive Containment Matching**: Normalize user-supplied names and query strings to lowercase and perform exact or containment matching against the database entries.
3. **Field Reporting**: When a record is found, report exact stored attributes: Resident Name, City, Country, and House Color.
4. **Missing Record Handling**: If a requested resident or query cannot be found within the registry, explicitly state that no record exists in the verified database. Do not attempt to fabricate an answer.
