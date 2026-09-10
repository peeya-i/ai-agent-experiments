---
name: plant-care-skill
description: Botanical reference and comprehensive plant care instructions formatted according to standardized horticultural templates.
keywords:
  - plant
  - plants
  - care
  - caring
  - instructions
  - information
  - plant-care
  - plant-info
  - botany
  - watering
  - repotting
  - propagation
  - soil
  - light
regex_targets:
  - "(?i)\\b(plant|plants|botany|flora|houseplant|gardening)\\b"
  - "(?i)\\b(care|caring|watering|soil|potting|fertiliz|repotting|pruning|propagation)\\b"
  - "(?i)\\b(plant-care|plant-info|plant care|plant info)\\b"
tools:
  - name: get_plant_care_template
    description: Retrieve the comprehensive markdown template for formatting plant care and botanical information.
    parameters: {}
  - name: get_plant_care_instructions
    description: Get standardized plant care instructions and botanical guide for a specific plant name.
    parameters:
      plant_name:
        type: string
        description: Common or scientific name of the plant (e.g., 'Monstera Deliciosa', 'Snake Plant', 'Fiddle Leaf Fig').
  - name: list_common_houseplants
    description: List popular and common houseplants with their botanical classifications.
    parameters: {}
---

# Plant Care Skill

## Standard Operating Procedure (SOP)
1. **Trigger Recognition**: Any user prompt mentioning plants, plant care, gardening, botanical advice, watering schedules, potting, soil, or propagation activates this skill.
2. **Template Retrieval & Adherence**: When delivering plant care recommendations, retrieve or follow the structured template from `./templates/plant_info.md`.
3. **Structured Comprehensive Output**: Populate all core sections:
   - **Plant Information**: Common name, scientific name, family, origin/native region, toxicity.
   - **1. Soil and Potting**: Recommended soil mix (drainage, aeration, pH), container type and sizing.
   - **2. Light**: Preferred intensity (bright indirect, direct, low light tolerance).
   - **3. Watering**: Detailed method (soak and dry, top watering), seasonal frequency, and overwatering risks.
   - **4. Temperature and Humidity**: Ideal range (°C and °F), cold hardiness thresholds, humidity targets.
   - **5. Maintenance**: Fertilization schedule, pruning guidelines, repotting intervals.
   - **6. Propagation**: Best methods (stem cuttings, division, water propagation) and step-by-step instructions.
   - **7. Pests and Troubleshooting**: Common pests (spider mites, fungus gnats) and symptoms (yellowing, brown tips).
   - **⚠️ Important Safety Note**: Explicit toxicity details for pets (cats, dogs) and humans, and contact precautions.
4. **Accuracy & Clarity**: Do not provide ambiguous or generic care; tailor each parameter specifically to the queried plant.
