import os
from openai import OpenAI
from typing import Dict, Any

class LLMExplainer:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "mock-key"
        base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        if os.getenv("OPENROUTER_API_KEY"):
            base_url = "https://openrouter.ai/api/v1"
            
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("LLM_MODEL", "google/gemini-2.5-flash" if "openrouter" in base_url else "gpt-4o-mini")

    def explain_move(self, payload: Dict[str, Any]) -> str:
        """Translates engine statistics into pedagogical, chess-coach instruction."""
        if os.getenv("OPENAI_API_KEY") is None and os.getenv("OPENROUTER_API_KEY") is None:
            return "Evaluation completed. Set API keys to generate the coaching breakdown."

        tactics_str = ", ".join(payload.get("tactics_detected", [])) or "None"
        is_forced = "Yes" if payload.get("is_forced", False) else "No"

        prompt = f"""
You are a highly analytical chess coach explaining game analysis to a student.
Use the following facts to explain the move:

FACTS:
- Position (FEN): {payload['position']}
- Move Played: {payload['played_move']}
- Classification: {payload['classification']}
- Forced Move: {is_forced}
- Evaluation Before: {payload['evaluation_before']}
- Evaluation After: {payload['evaluation_after']}
- Best Move: {payload['best_move']}
- Continuation Line: {", ".join(payload['principal_variation'])}
- Tactics Identified: {tactics_str}

COACHING DIRECTIONS:
1. Explain why this move was a {payload['classification']}. Reference the transition in evaluation ({payload['evaluation_before']} to {payload['evaluation_after']}).
2. If forced, explain the necessity.
3. If tactics ({tactics_str}) are present, explain the specific mechanism (e.g., how the pin limits defense, or how the fork was executed or allowed).
4. Highlight the strategic difference between the played move and the best alternative ({payload['best_move']}).
5. Keep explanations direct, concise, and focused on learning. Do not mention system parameters or computational constraints. Limit to two structured paragraphs.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional chess coach. You do not calculate moves; you interpret provided engine data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Calculated successfully, but explanation generation experienced a temporary issue: {str(e)}"
