import os
from fpdf import FPDF

class OverviewPDF(FPDF):
    def header(self):
        # Title banner
        self.set_fill_color(30, 41, 59) # Slate Dark (#1E293B)
        self.rect(0, 0, 210, 28, 'F')
        
        # Title text
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 15)
        self.set_xy(10, 5)
        self.cell(190, 8, "LifeAtlas Intern Ecosystem Overview", align="C")
        
        # Subtitle
        self.set_font("Helvetica", "I", 9)
        self.set_xy(10, 13)
        self.cell(190, 5, "Cross-Stream Scope, Goals, and Challenges - Phase 2/3 Transition", align="C")
        self.set_xy(10, 18)
        self.cell(190, 5, "Date: June 10, 2026 | Prepared by: Shourya (MRO Lead)", align="C")
        self.ln(12)

    def draw_card(self, x, y, w, h, title, phase, problem, work, stack):
        # Draw card container
        self.set_fill_color(248, 250, 252) # Light gray slate (#F8FAFC)
        self.set_draw_color(226, 232, 240) # Slate border (#E2E8F0)
        self.set_line_width(0.3)
        self.rect(x, y, w, h, 'DF')
        
        # Draw card header
        self.set_fill_color(51, 65, 85) # Slate Medium (#334155)
        self.rect(x, y, w, 7, 'F')
        
        # Header title
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8.5)
        self.set_xy(x + 3, y + 1.5)
        self.cell(w - 20, 4, title)
        
        # Header phase
        self.set_font("Helvetica", "B", 7)
        self.set_xy(x + w - 25, y + 1.5)
        self.cell(22, 4, phase, align="R")
        
        # Card Body
        self.set_text_color(15, 23, 42) # Slate Dark text (#0F172A)
        
        # Problem Section
        self.set_font("Helvetica", "B", 7.5)
        self.set_xy(x + 3, y + 9)
        self.cell(w - 6, 4, "Core Problem:")
        self.set_font("Helvetica", "", 7.5)
        self.set_xy(x + 3, y + 13)
        self.multi_cell(w - 6, 3.2, problem)
        
        # Current Work Section
        self.set_font("Helvetica", "B", 7.5)
        self.set_xy(x + 3, y + 33)
        self.cell(w - 6, 4, "Current Focus:")
        self.set_font("Helvetica", "", 7.5)
        self.set_xy(x + 3, y + 37)
        self.multi_cell(w - 6, 3.2, work)
        
        # Tech Stack Section
        self.set_font("Helvetica", "B", 7.5)
        self.set_xy(x + 3, y + 62)
        self.cell(w - 6, 4, "Tech Stack:")
        self.set_font("Helvetica", "I", 7.5)
        self.set_xy(x + 3, y + 66)
        self.multi_cell(w - 6, 3.2, stack)

def generate_pdf():
    pdf = OverviewPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # Grid variables
    w = 92
    h = 77
    col1_x = 10
    col2_x = 108
    
    row1_y = 33
    row2_y = 115
    row3_y = 197
    
    # ── CARD 1: Boardy ──────────────────────────────────────────────────
    pdf.draw_card(
        x=col1_x, y=row1_y, w=w, h=h,
        title="1. Boardy (AI Matchmaking)",
        phase="Phase 2/3",
        problem="Cold outreach & LinkedIn networking are broken. Boardy replaces them with a 5-minute automated voice conversation and intelligent matching to connect founders with relevant network contacts.",
        work="Building a custom voice pipeline using Pipecat (Silero VAD, AssemblyAI STT, OpenRouter LLM, Cartesia TTS) to replace Retell AI and reduce per-call API cost from ~$0.19 to ~$0.02. Replacing Voyage/Claude with local models.",
        stack="Pipecat, Python, OpenAI/OpenRouter APIs, Cartesia TTS, local BGE/Ollama models."
    )
    
    # ── CARD 2: DataPro+ ──────────────────────────────────────────────────
    pdf.draw_card(
        x=col1_x, y=row2_y, w=w, h=h,
        title="2. DataPro+ (Datacenter Deals)",
        phase="Phase 0 (70%)",
        problem="Gated and complex datacenter investment deals that require intensive role-based NDA workflows, manual referral tracking, and lead management for land, power, and infrastructure opportunities.",
        work="Building a secure dealflow platform featuring AI-based PDF extraction for documents, modular contract blocks (for identity/NDAs), and a data migration framework. Monetized through 1-3% deal fees.",
        stack="React, Vite, Tailwind CSS, FastAPI, Supabase, Gemini AI."
    )
    
    # ── CARD 3: VSAB (Digital Twin) ───────────────────────────────────────
    pdf.draw_card(
        x=col1_x, y=row3_y, w=w, h=h,
        title="3. VSAB (Production Digital Twin)",
        phase="Phase 2",
        problem="Lack of real-time factory floor monitoring and production optimization for VSAB Gruppen (Swedish manufacturer). Needs automated risk detection with penalty formulas for delay tracking.",
        work="Split in two teams: Team A is building a Streamlit dashboard with an integrated AI assistant, animated sketch views, and product comparison metrics. Team B is building a 3D WebGL factory simulation with layout migration.",
        stack="Streamlit, Three.js, WebGL, D3, Recharts, Pandas, Python."
    )
    
    # ── CARD 4: Security (ZeroClaw) ───────────────────────────────────────
    pdf.draw_card(
        x=col2_x, y=row1_y, w=w, h=h,
        title="4. Security & Auditing (ZeroClaw)",
        phase="Phase 2 -> 3",
        problem="Security risks across active production codebases and container boundaries. Need to detect credential leaks, unsafe injection patterns, and verify tenant isolation boundaries in Supabase.",
        work="Fully integrated Secret and Code Pattern scanners. Setting up automated test suites for Auth Bypass, Session Management, and Rate Limiting on FastAPI. Auditing the Stream 3 digital twin container sandbox.",
        stack="FastAPI, Supabase RLS, Python (ZeroClaw Scanner), Docker, CI/CD Gates."
    )
    
    # ── CARD 5: Life Planning Intelligence (LPI) ──────────────────────────
    pdf.draw_card(
        x=col2_x, y=row2_y, w=w, h=h,
        title="5. LPI (Life Goals & SMILE)",
        phase="Phase 2 -> 3",
        problem="Helping users plan, structure, and track progress on life goals using the SMILE methodology, which requires complex activity ingestion, scoring algorithms, and recommendations.",
        work="Developing Supabase persistence layers, establishing dual-sync logging, resolving database silent migration bugs, connecting React frontend components to FastAPI endpoints, and creating activity pipelines.",
        stack="FastAPI, Supabase, React, Python, MCP servers, mypy, ruff."
    )
    
    # ── CARD 6: MRO Tokyo (Our Stream) ────────────────────────────────────
    pdf.draw_card(
        x=col2_x, y=row3_y, w=w, h=h,
        title="6. MRO Optimization (Our Stream)",
        phase="Phase 2 -> 3",
        problem="Optimizing Altiostar's Tokyo 5G network handovers. Need to dynamically adjust Cell Individual Offsets (CIO) across 763 neighbor relations to keep call drops low under environmental stress.",
        work="Trained PPO RL models on relation-level PM data for 50k steps. Built an automated Ship Gate Validator to check production thresholds (HO Success >99%, Ping-Pong <5%) and created a policy ONNX exporter.",
        stack="Python, Stable-Baselines3, PPO, PyTorch, ONNX, Streamlit, MLflow."
    )
    
    output_path = "docs/2026-06-10-cross-stream-overview.pdf"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    print(f"PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    generate_pdf()
