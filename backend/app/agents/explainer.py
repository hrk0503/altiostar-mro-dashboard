from pydantic import BaseModel

class ExplainerRequest(BaseModel):
    relation_id: str
    initial_cio: float
    optimized_cio: float
    initial_hosr: float
    optimized_hosr: float

class ExplainerAgent:
    """Explains parameter adjustments in clear, operator-friendly English (Task A5)."""
    
    def generate_explanation(self, req: ExplainerRequest) -> str:
        delta = req.optimized_cio - req.initial_cio
        hosr_diff = req.optimized_hosr - req.initial_hosr
        
        explanation = (
            f"Optimized CIO for relation '{req.relation_id}' by {delta:+.2f} dB. "
            f"This adjustment corrected signal shadowing from building blockages, "
            f"raising the Handover Success Rate (HOSR) from {req.initial_hosr:.2f}% "
            f"to {req.optimized_hosr:.2f}% (a net improvement of {hosr_diff:+.2f}%)."
        )
        return explanation
