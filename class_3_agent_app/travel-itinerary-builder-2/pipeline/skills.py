"""Gemini skills for the Scheduler agent to enrich itineraries with local culture, hidden gems, and smart clustering."""
from typing import Dict, Any, List
from pipeline.gemini_service import GeminiService
from services.tracker import Tracker

class LocalVibeSkill:
    """Skill to generate authentic insider tips, local customs, and neighborhood ambiance notes."""
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.name = "Skill:LocalVibe"
        self._cache: Dict[str, str] = {}

    def execute(self, destination: str, neighborhood: str, day_number: int) -> str:
        cache_key = f"{destination.strip().lower()}:{neighborhood.strip().lower()}:{day_number}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = f"""
Provide one fun, highly practical 1-sentence local insider tip or secret etiquette for exploring the '{neighborhood}' district of {destination} on Day {day_number}.
Be concise, inspiring, and culturally authentic.
"""
        Tracker.record_event(
            self.run_id,
            "skill_request",
            self.name,
            f"Generating local vibe tip for Day {day_number} in {neighborhood}",
            {"destination": destination, "neighborhood": neighborhood, "day": day_number, "prompt": prompt}
        )
        tip = self.gemini.generate_content(prompt, agent_source=self.name)
        cleaned = tip.strip().strip('"')
        if not cleaned or len(cleaned) < 5 or "{" in cleaned:
            defaults = [
                f"Local tip: Visit {neighborhood}'s small artisan espresso bars before 10 AM for fresh pastries straight from the stone oven.",
                f"Insider advice: The pedestrian alleys in {neighborhood} are best explored on foot right around golden hour for photography.",
                f"Secret spot: Look out for historic courtyard passages tucked behind the main boulevard for quiet artisan cafes.",
                f"Pro-tip: Download the local transit contactless card on your phone for seamless transfers around {neighborhood}."
            ]
            cleaned = defaults[(day_number - 1) % len(defaults)]

        self._cache[cache_key] = cleaned

        Tracker.record_event(
            self.run_id,
            "skill_response",
            self.name,
            f"Local vibe tip generated for Day {day_number} in {neighborhood}",
            {
                "destination": destination,
                "neighborhood": neighborhood,
                "day": day_number,
                "prompt_sent": prompt,
                "raw_model_response": tip,
                "result_tip": cleaned
            }
        )
        return cleaned


class HiddenGemSkill:
    """Skill to recommend an unexpected, delightfully off-the-beaten-path mini stop."""
    def __init__(self, gemini: GeminiService, run_id: str):
        self.gemini = gemini
        self.run_id = run_id
        self.name = "Skill:HiddenGem"
        self._cache: Dict[str, Dict[str, Any]] = {}

    def execute(self, destination: str, interests: List[str]) -> Dict[str, Any]:
        interests_key = tuple(sorted([i.strip().lower() for i in interests])) if interests else ()
        cache_key = f"{destination.strip().lower()}:{interests_key}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt = f"""
Suggest ONE charming, low-cost or free 'hidden gem' activity in {destination} catering to interests: {', '.join(interests)}.
Return ONLY valid JSON with keys: "title", "neighborhood", "description", "estimated_cost" (number).
"""
        Tracker.record_event(
            self.run_id,
            "skill_request",
            self.name,
            f"Discovering hidden gem in {destination}",
            {"interests": interests, "prompt": prompt}
        )
        resp = self.gemini.generate_content(prompt, agent_source=self.name)
        gem_data = None
        try:
            import json
            cleaned = resp.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            if isinstance(data, dict) and "title" in data:
                gem_data = data
        except Exception:
            pass

        if not gem_data:
            gem_data = {
                "title": f"Secret Garden & Vintage Book Arcade",
                "neighborhood": "Artisan Quarter",
                "description": "A tucked-away historic glass arcade with antique bookstalls and a quiet courtyard fountain.",
                "estimated_cost": 0.0
            }

        self._cache[cache_key] = gem_data

        Tracker.record_event(
            self.run_id,
            "skill_response",
            self.name,
            f"Discovered hidden gem in {destination}: {gem_data.get('title')}",
            {
                "destination": destination,
                "interests": interests,
                "prompt_sent": prompt,
                "raw_model_response": resp,
                "gem_result": gem_data
            }
        )
        return gem_data
