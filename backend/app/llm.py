import os
from openai import OpenAI
from typing import Dict, Any

class LLMExplainer:
    def __init__(self):
        # Works out of the box with OpenAI or OpenRouter (just set OPENROUTER_API_KEY and custom BASE_URL)
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "mock-key"
        base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        
        # Configure fallback to support free endpoint structures on OpenRouter
        if os.getenv("OPENROUTER_API_KEY"):
            base_url = "https://openrouter.ai/api/v1"
            
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        # Standard free-tier models (e.g., Gemini Flash or Llama 3 via OpenRouter)
        self.model = os.getenv("LLM_MODEL", "google/gemini-2.5-flash" if "openrouter" in base_url else "gpt-4o-mini")

    def explain_move(self, payload: Dict[str, Any]) -> str:
        """
        Takes structured, validated data from Stockfish and asks the LLM to write
        an educational analysis. The LLM is strictly prohibited from doing chess math.
        """
        if os.getenv("OPENAI_API_KEY") is None and os.getenv("OPENROUTER_API_KEY") is None:
            return "AI Key not configured. Engine evaluation indicates this move was analyzed successfully."

        prompt = f"""
You are an expert chess Grandmaster and world-class chess coach. Your goal is to explain a move's positional, strategic, and tactical features based STRICTLY on the objective evaluation statistics provided by the Stockfish chess engine.

Do not calculate evaluations or list alternative coordinates that are not in the context. Rely strictly on the telemetry below.

CONTEXT DATA:
- Played Move: {payload['played_move']}
- Stockfish Assessment: This move was a {payload['classification']}
- Evaluation Before: {payload['evaluation_before']}
- Evaluation After: {payload['evaluation_after']}
- Engine's Preferred Best Move: {payload['best_move']}
- Principal Continuation (Best Lines): {", ".join(payload['principal_variation'])}
- Position (FEN): {payload['position']}

GUIDELINES FOR YOUR RESPONSE:
1. Explain concisely why the played move is classified as a {payload['classification']}. If it's a Blunder or Mistake, clearly state what defensive or offensive resource was overlooked.
2. Discuss positional factors: King safety, pawn structures, development, open files, piece activity, or coordination problems introduced or solved by this move.
3. Compare the played move with the engine's suggested best move ({payload['best_move']}). 
4. Maintain an encouraging, educational tone suitable for an ambitious student of the game. Keep the response limited to 2-3 structured paragraphs. Do not mention "as an AI" or refer to computational parameters. Write cleanly.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional, pedagogical Chess Grandmaster Coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"The calculation completed, but the educational engine explanation service is temporarily offline: {str(e)}"
