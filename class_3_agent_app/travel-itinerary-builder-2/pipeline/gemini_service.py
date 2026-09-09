"""Gemini API client with primary/fallback model support and event tracking."""
import json
import logging
from typing import Dict, Any, Optional, Tuple
import config
from services.tracker import Tracker

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or "system"
        self.api_key = config.GEMINI_API_KEY
        self.primary_model = config.GEMINI_MODEL
        self.fallback_model = config.GEMINI_FALLBACK_MODEL
        self._client_type = None
        self._init_sdk()

    def _init_sdk(self):
        if not self.api_key:
            logger.warning("No GEMINI_API_KEY set. LLM calls will use realistic mock generator.")
            return

        # Attempt modern google-genai SDK first
        try:
            from google import genai
            self.genai_client = genai.Client(api_key=self.api_key)
            self._client_type = "google-genai"
            logger.info("Initialized modern google.genai Client")
            return
        except Exception as e:
            logger.info(f"Could not init modern google.genai ({e}), checking legacy google.generativeai")

        # Attempt legacy google.generativeai
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=self.api_key)
            self.legacy_genai = legacy_genai
            self._client_type = "google-generativeai"
            logger.info("Initialized legacy google.generativeai")
        except Exception as e:
            logger.warning(f"Could not init google.generativeai: {e}")
            self._client_type = None

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None, agent_source: str = "GeminiService") -> str:
        """Invokes Gemini with primary model, then falls back to fallback model if needed."""
        if not self.api_key or not self._client_type:
            req_payload = {
                "model": "mock_generator",
                "prompt": prompt,
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "system_instruction": system_instruction,
                "generation_config": {"temperature": 0.7}
            }
            Tracker.record_event(
                self.run_id,
                "model_request",
                agent_source,
                f"Sending prompt to simulated model generator",
                req_payload
            )
            resp_text, raw_meta = self._mock_response(prompt, agent_source)
            Tracker.record_event(
                self.run_id,
                "model_response",
                agent_source,
                f"Received response from simulated model generator",
                {
                    "model": "mock_generator",
                    "response": resp_text,
                    "text": resp_text,
                    "candidates": raw_meta.get("candidates", []),
                    "usage_metadata": raw_meta.get("usage_metadata", {}),
                    "model_version": raw_meta.get("model_version", "mock_generator"),
                    "raw_response": raw_meta
                }
            )
            return resp_text

        # 1. Try Primary Model
        try:
            req_payload = {
                "model": self.primary_model,
                "prompt": prompt,
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "system_instruction": system_instruction,
                "generation_config": {"temperature": 0.7, "system_instruction": system_instruction} if system_instruction else {"temperature": 0.7}
            }
            Tracker.record_event(
                self.run_id,
                "model_request",
                agent_source,
                f"Sending prompt to primary model: {self.primary_model}",
                req_payload
            )
            response_text, raw_meta = self._call_model(self.primary_model, prompt, system_instruction)
            Tracker.record_event(
                self.run_id,
                "model_response",
                agent_source,
                f"Received response from primary model: {self.primary_model}",
                {
                    "model": self.primary_model,
                    "response": response_text,
                    "text": response_text,
                    "candidates": raw_meta.get("candidates", []),
                    "usage_metadata": raw_meta.get("usage_metadata", {}),
                    "model_version": raw_meta.get("model_version", self.primary_model),
                    "response_id": raw_meta.get("response_id"),
                    "raw_response": raw_meta
                }
            )
            return response_text
        except Exception as primary_err:
            logger.warning(f"Primary model {self.primary_model} failed: {primary_err}. Trying fallback model {self.fallback_model}...")
            Tracker.record_event(
                self.run_id,
                "model_error",
                agent_source,
                f"Primary model {self.primary_model} failed ({primary_err}). Falling back to {self.fallback_model}",
                {
                    "primary_model": self.primary_model,
                    "error": str(primary_err),
                    "fallback_model": self.fallback_model
                }
            )

            # 2. Try Fallback Model
            try:
                fallback_req = {
                    "model": self.fallback_model,
                    "prompt": prompt,
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "system_instruction": system_instruction,
                    "generation_config": {"temperature": 0.7, "system_instruction": system_instruction} if system_instruction else {"temperature": 0.7},
                    "fallback_from": self.primary_model
                }
                Tracker.record_event(
                    self.run_id,
                    "model_request",
                    agent_source,
                    f"Sending fallback prompt to {self.fallback_model}",
                    fallback_req
                )
                response_text, raw_meta = self._call_model(self.fallback_model, prompt, system_instruction)
                Tracker.record_event(
                    self.run_id,
                    "model_response",
                    agent_source,
                    f"Received response from fallback model: {self.fallback_model}",
                    {
                        "model": self.fallback_model,
                        "response": response_text,
                        "text": response_text,
                        "candidates": raw_meta.get("candidates", []),
                        "usage_metadata": raw_meta.get("usage_metadata", {}),
                        "model_version": raw_meta.get("model_version", self.fallback_model),
                        "response_id": raw_meta.get("response_id"),
                        "raw_response": raw_meta
                    }
                )
                return response_text
            except Exception as fallback_err:
                logger.error(f"Fallback model {self.fallback_model} also failed: {fallback_err}. Using resilient fallback generator.")
                resp_text, raw_meta = self._mock_response(prompt, agent_source)
                Tracker.record_event(
                    self.run_id,
                    "model_error",
                    agent_source,
                    f"Both models failed. Activated resilient response generator.",
                    {
                        "primary_error": str(primary_err),
                        "fallback_error": str(fallback_err),
                        "simulated_response": resp_text
                    }
                )
                return resp_text

    def _call_model(self, model_name: str, prompt: str, system_instruction: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        if self._client_type == "google-genai":
            config_params = {}
            if system_instruction:
                config_params["system_instruction"] = system_instruction
            response = self.genai_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config_params if config_params else None
            )
            raw_meta = {}
            try:
                raw_meta = response.model_dump(mode="json", exclude_none=True)
            except Exception:
                try:
                    raw_meta = response.to_json_dict()
                except Exception:
                    raw_meta = {"text": getattr(response, "text", "")}
            return response.text, raw_meta

        elif self._client_type == "google-generativeai":
            model = self.legacy_genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            raw_meta = {}
            try:
                candidates_list = []
                for c in getattr(response, "candidates", []):
                    cand_dict = {"finish_reason": str(getattr(c, "finish_reason", ""))}
                    if hasattr(c, "content"):
                        cand_dict["content"] = {
                            "role": getattr(c.content, "role", "model"),
                            "parts": [{"text": p.text} for p in getattr(c.content, "parts", []) if hasattr(p, "text")]
                        }
                    if hasattr(c, "safety_ratings"):
                        cand_dict["safety_ratings"] = [
                            {"category": str(getattr(sr, "category", "")), "probability": str(getattr(sr, "probability", ""))}
                            for sr in getattr(c, "safety_ratings", [])
                        ]
                    candidates_list.append(cand_dict)
                usage_meta = getattr(response, "usage_metadata", None)
                usage_dict = {}
                if usage_meta:
                    usage_dict = {
                        "prompt_token_count": getattr(usage_meta, "prompt_token_count", None),
                        "candidates_token_count": getattr(usage_meta, "candidates_token_count", None),
                        "total_token_count": getattr(usage_meta, "total_token_count", None),
                    }
                raw_meta = {
                    "text": response.text,
                    "candidates": candidates_list,
                    "usage_metadata": usage_dict,
                    "model_version": model_name
                }
            except Exception as e:
                raw_meta = {"text": getattr(response, "text", ""), "error": str(e)}
            return response.text, raw_meta
        else:
            raise RuntimeError("No suitable Gemini client initialized")

    def _mock_response(self, prompt: str, agent_source: str) -> Tuple[str, Dict[str, Any]]:
        """Deterministic mock JSON response for fallback / test scenarios."""
        # Simple heuristic response based on agent_source
        if "Flight" in agent_source:
            text = json.dumps([
                {"carrier": "SkyWings Express", "route": "Direct", "travel_time_hours": 4.5, "estimated_cost": 320.0, "departure": "08:30 AM", "tier": "Economy Plus"},
                {"carrier": "Global Airway", "route": "1-Stop", "travel_time_hours": 6.2, "estimated_cost": 240.0, "departure": "01:15 PM", "tier": "Budget Economy"}
            ])
        elif "Hotel" in agent_source:
            text = json.dumps([
                {"name": "Central Grand Hotel", "neighborhood": "City Center", "safety_rating": "4.8/5", "nightly_rate": 140.0, "tier": "Comfort 4-Star"},
                {"name": "Boutique Travelers Inn", "neighborhood": "Old Town Arts Quarter", "safety_rating": "4.7/5", "nightly_rate": 85.0, "tier": "Boutique Budget"}
            ])
        elif "Activity" in agent_source:
            text = json.dumps([
                {"name": "Historic District Walking Tour", "neighborhood": "Old Town", "category": "Culture", "estimated_cost": 25.0, "duration_hours": 2.5},
                {"name": "Panoramic City Lookout & Gardens", "neighborhood": "Uptown Hills", "category": "Sightseeing", "estimated_cost": 15.0, "duration_hours": 2.0},
                {"name": "Artisan Culinary Market Tasting", "neighborhood": "River District", "category": "Food & Dining", "estimated_cost": 40.0, "duration_hours": 2.0},
                {"name": "Modern Art & Science Museum", "neighborhood": "River District", "category": "Museum", "estimated_cost": 20.0, "duration_hours": 3.0},
                {"name": "Sunset Harbor Cruise", "neighborhood": "Harborfront", "category": "Leisure", "estimated_cost": 35.0, "duration_hours": 1.5}
            ])
        elif "Scheduler" in agent_source:
            text = json.dumps({
                "note": "Structured day grouping by geographic zone with budget optimization.",
                "total_estimated_cost": 650.0
            })
        else:
            text = json.dumps({"status": "ok", "message": "Simulated output"})

        raw_meta = {
            "model_version": "mock_generator_v1",
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [{"text": text}]
                    },
                    "finish_reason": "STOP",
                    "index": 0
                }
            ],
            "usage_metadata": {
                "prompt_token_count": len(prompt.split()),
                "candidates_token_count": len(text.split()),
                "total_token_count": len(prompt.split()) + len(text.split())
            }
        }
        return text, raw_meta
