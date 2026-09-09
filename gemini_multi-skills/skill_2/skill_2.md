---
name: user_house_information
description: >-
  Use this skill when the user asks questions about their house, such as the color
  of the house and/or the city where the house is located. Tells the LLM to use
  the tools in the same folder to answer questions about the user's house.
---

# User House Information Skill (Skill 2)

## Name
`user_house_information`

## Description
A specialized Gemini skill that tells the LLM to use the tools in the same folder (`tools.py`)
to answer questions regarding the user's house. The user's house has the following
fixed private facts:
- **Color of the house**: Always **blue**
- **City where the house is located**: Always **San Jose**

## Instructions for the LLM
1. **Always Use the Skill Tools**: Whenever the user asks questions about their house (e.g. its color, its location/city, or both), you must invoke the tools in this same folder rather than guessing.
2. **Execute Tools Based on User Question**:
   - To get the color of the house: invoke `get_house_color()`.
   - To get the city where the house is located: invoke `get_house_city()`.
   - To answer compound or arbitrary natural language questions about the house: invoke `get_private_house_information(question=...)`.
3. **Consistency**:
   - The house color is always blue.
   - The city where the house is located is always San Jose.
4. **Multi-Step Coordination**:
   - If the user asks a question that connects the house location to another skill (for example: "What is the weather in the city where my house is located?"), first execute `get_house_city()` from this skill (which returns "San Jose"), and then use `get_weather(city="San Jose")` from `skill_1`.

## Tools

### get_house_color
- **Purpose**: Retrieve the color of the user's house.
- **Parameters**: None
- **Returns**:
  - `color`: "blue"
  - `answer`: "The color of the house is blue."

### get_house_city
- **Purpose**: Retrieve the city where the user's house is located.
- **Parameters**: None
- **Returns**:
  - `city`: "San Jose"
  - `answer`: "The house is located in San Jose."

### get_private_house_information
- **Purpose**: Answer questions about the user's house (color and/or city location).
- **Parameters**:
  - `question` (string, required): The user's natural language question about the house.
- **Returns**:
  - `house_color`: "blue" (if requested or applicable)
  - `house_city`: "San Jose" (if requested or applicable)
  - `answer`: Formatted answer string

## Example Questions
- "What is the color of my house?"
- "Where is my house located?"
- "What city is my house in and what color is it painted?"
- "What is the weather and local time where my house is?"
