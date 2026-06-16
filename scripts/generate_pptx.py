"""Generates a PowerPoint presentation (docs/presentation.pptx) summarizing the MRO training pipeline project.
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

# Programmatically check and install python-pptx if missing
try:
    import pptx
except ImportError:
    print("python-pptx is not installed. Installing it via pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-pptx"])
    import pptx

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


def create_presentation() -> None:
    prs = Presentation()
    
    # Define color scheme
    color_bg = RGBColor(11, 15, 25)        # Dark Blue
    color_card = RGBColor(17, 24, 39)       # Card BG
    color_text = RGBColor(243, 244, 246)    # Off-white
    color_sub = RGBColor(156, 163, 175)     # Gray text
    color_primary = RGBColor(56, 189, 248)  # Light Blue Accent
    color_accent = RGBColor(129, 140, 248)  # Indigo
    
    # Slide Dimensions (16:9 widescreen)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Background helper
    def set_slide_background(slide):
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = color_bg
        
    # Helper to add standard header to slide
    def add_slide_header(slide, title_text, tag_text=""):
        # Header text box
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.2))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = "Arial"
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = color_text
        
        if tag_text:
            p_tag = tf.add_paragraph()
            p_tag.text = f"// {tag_text}"
            p_tag.font.name = "Arial"
            p_tag.font.size = Pt(13)
            p_tag.font.bold = True
            p_tag.font.color.rgb = color_primary
            
    # Helper to add bullet point list
    def add_bullet_list(slide, items, left, top, width, height, font_size=16):
        box = slide.shapes.add_textbox(left, top, width, height)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        for idx, item in enumerate(items):
            p = tf.add_paragraph() if idx > 0 else tf.paragraphs[0]
            p.text = "• " + item[0]
            p.font.name = "Arial"
            p.font.size = Pt(font_size)
            p.font.bold = True
            p.font.color.rgb = color_text
            p.space_after = Pt(2)
            
            p_desc = tf.add_paragraph()
            p_desc.text = "  " + item[1]
            p_desc.font.name = "Arial"
            p_desc.font.size = Pt(font_size - 3)
            p_desc.font.color.rgb = color_sub
            p_desc.space_after = Pt(12)
            
        return box

    # Slide 1: Title Slide (Blank Layout)
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.5))
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    p = tf.paragraphs[0]
    p.text = "5G MRO RL Pipeline Deep-Dive"
    p.font.name = "Arial"
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = color_text
    p.space_after = Pt(8)
    
    p2 = tf.add_paragraph()
    p2.text = "Under-the-Hood Data Pipeline, Gymnasium Simulation, and Multi-Agent Architecture"
    p2.font.name = "Arial"
    p2.font.size = Pt(20)
    p2.font.color.rgb = color_primary
    p2.space_after = Pt(48)
    
    p3 = tf.add_paragraph()
    p3.text = "AltioStar Tokyo MRO Stream | Devika · Harshit · Ananyaa · Shourya"
    p3.font.name = "Arial"
    p3.font.size = Pt(16)
    p3.font.bold = True
    p3.font.color.rgb = color_accent
    p3.space_after = Pt(4)
    
    p4 = tf.add_paragraph()
    p4.text = "WINNIIO × Amity 2026 | June 2026"
    p4.font.name = "Arial"
    p4.font.size = Pt(13)
    p4.font.color.rgb = color_sub

    # Slide 2: Ingestion & Schema Mapper
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "The Ingestion Data Pipeline", "Data Engineering")
    
    bullets_p1 = [
        ("Raw Operator CSV Files", "Ingests 4 base files: site database (75 cells), neighbor relations (763 pairs), PM data (216K rows), and monthly KPI summary (75 rows)."),
        ("Relation-Level Compilation", "Merges and compiles cell-level PM and relation parameters into a high-granularity 2.2M-row relation-level PM dataset (pm_data_relation_level.csv)."),
        ("Set-Based Schema Mapper", "Auto-detects CSV types and maps columns. Uses set signature matching (cols.issubset) in schema_mapper.py to remain 100% order-independent (shuffled column proof)."),
        ("Double Caching Performance", "Caches dataframes and pre-grouped relation slices in memory to reduce env boot time from minutes to under 50 milliseconds.")
    ]
    add_bullet_list(slide, bullets_p1, Inches(0.8), Inches(1.8), Inches(6.5), Inches(5.0))
    
    card_box = slide.shapes.add_textbox(Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "📊 CSV to State Lifecycle"
    cp.font.name = "Arial"
    cp.font.size = Pt(22)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(16)
    
    cp2 = ctf.add_paragraph()
    cp2.text = "1. Raw CSV Ingestion\n   ↓\n2. Set-based Signature Mapping (schema_mapper.py)\n   ↓\n3. Pre-Grouped Relation Indices Caching\n   ↓\n4. Fast O(1) Gymnasium Env Access"
    cp2.font.name = "Arial"
    cp2.font.size = Pt(16)
    cp2.font.color.rgb = color_text

    # Slide 3: Gymnasium MRO Env
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Gymnasium Environment Simulation", "Under the Hood")
    
    bullets_p2 = [
        ("Observation Space", "9-dimensional vector per relation (handover attempts, successes, failures: too early, too late, wrong cell, correct cell, ping-pongs, average RSRP/SINR)."),
        ("Action Space", "Continuous Cell Individual Offset (CIO) delta adjustments per neighbor relation, bounded strictly to [-2.0, 2.0] dB."),
        ("Data-Driven State Transitions", "No slow physical propagation math. Environment performs binary search to find the nearest historical CIO database configuration and samples outcomes from the real distribution."),
        ("Fast Step Simulation", "Optimized grouping and caches yield O(1) transitions, allowing 100k rollout steps to run in seconds on CPU.")
    ]
    add_bullet_list(slide, bullets_p2, Inches(0.8), Inches(1.8), Inches(6.5), Inches(5.0))
    
    card_box = slide.shapes.add_textbox(Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "🧠 Simulation Model"
    cp.font.name = "Arial"
    cp.font.size = Pt(22)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(16)
    
    cp2 = ctf.add_paragraph()
    cp2.text = "Physics modeling is slow and error-prone. By slicing the 2.2M-row database and caching outcomes per relation, the env acts as a high-fidelity lookup simulator that behaves exactly like the real radio network."
    cp2.font.name = "Arial"
    cp2.font.size = Pt(16)
    cp2.font.color.rgb = color_text

    # Slide 4: Reward Tuning & Ship Gate
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Reward Engineering & Ship Gate", "Model Safety")
    
    bullets_p3 = [
        ("v2 Rate-Based Reward", "Normalizes by percentage rates directly (bounded and consistent): Reward = HOSR * 1.0 - failure_rate * 5.0 - PP_rate * 2.0."),
        ("Asymmetric Boundary Penalties", "Introduces asymmetric barrier functions to env (punishes HOSR < 95% and PP > 5% with large negative penalties) to guide PPO policy convergence."),
        ("Automated Ship Gate Validator", "Built ship_gate.py checking results against strictly HOSR > 99% and PP < 5%. Outputs exit code 0/1 for CI/CD gates."),
        ("Statistical Significance Check", "Evaluates sweep results across 5 independent seeds to ensure repeatability and prevent random seed selection bias.")
    ]
    add_bullet_list(slide, bullets_p3, Inches(0.8), Inches(1.8), Inches(6.5), Inches(5.0))
    
    card_box = slide.shapes.add_textbox(Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "🛡️ Ship Gate Criteria"
    cp.font.name = "Arial"
    cp.font.size = Pt(22)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(16)
    
    cp2 = ctf.add_paragraph()
    cp2.text = "• HOSR: Strictly > 99.0% (99.0% = FAIL)\n• Ping-Pong: Strictly < 5.0% (5.0% = FAIL)\n\nChecked automatically on every sweep results JSON file before code merges to staging."
    cp2.font.name = "Arial"
    cp2.font.size = Pt(16)
    cp2.font.color.rgb = color_text

    # Slide 5: Agent Roles
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Multi-Agent System Architecture", "Agent Execution Roles")
    
    roles_left = [
        ("Atlas (Product Owner)", "Orchestrates sprint goals, phase gates, daily reports, and blocker escalations."),
        ("Pipeline (Data Engineer)", "Responsible for CSV ingestion, schema mapper auto-detection, data validation, and Parquet exports."),
        ("Spectrum (RF Domain Lead)", "RF domain expert. Enforces 3GPP constraints, configures valid CIO ranges, and guides reward calibration."),
        ("Forge (ML Engineer)", "Builds the Gymnasium environment, handles PPO convergence loops, and runs Optuna parameter sweeps.")
    ]
    
    roles_right = [
        ("Deploy (DevOps)", "Docker containment, environment locks, and K8s manifests targeting CU-CP K8s pods."),
        ("Lens (Visualization)", "Generates interactive Streamlit dashboards, HTML presentations, and PowerPoint decks."),
        ("Sentinel (QA & Validation)", "Property-based tests (Hypothesis), adversarial input audits, and automated ship gate verification.")
    ]
    
    add_bullet_list(slide, roles_left, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), font_size=15)
    add_bullet_list(slide, roles_right, Inches(6.8), Inches(1.8), Inches(5.6), Inches(5.0), font_size=15)

    # Slide 6: Results & ONNX
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "100k Sweep & ONNX Export", "Phase 3 Results")
    
    bullets_p5 = [
        ("100k Sweeps (16/16 Completed)", "PPO trained across 4 variants x 4 scenarios. Variant v2 baseline achieves HOSR: 99.99% and Ping-Pong: 0.00%."),
        ("Optuna Hyperparameter Tuning", "Optimized learning rate, batch size, rollout steps, and discount factor to resolve baseline HOSR stagnation."),
        ("ONNX Exporter (Complete)", "export_onnx.py converts PyTorch model zip checkpoint into deployment-ready ONNX models for CU-CP K8s deployment."),
        ("Tensor Clamping Bounds", "Applied torch.clamp matching environment action limits [-2.0, 2.0] to guarantee ONNX predictions match SB3 deterministic predictions.")
    ]
    add_bullet_list(slide, bullets_p5, Inches(0.8), Inches(1.8), Inches(6.5), Inches(5.0))
    
    card_box = slide.shapes.add_textbox(Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "🎯 Verification Performance"
    cp.font.name = "Arial"
    cp.font.size = Pt(22)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(16)
    
    stats = [
        ("Random Baseline HOSR", "79.25%"),
        ("Trained Agent HOSR", "99.99%"),
        ("Absolute HOSR Delta", "+20.74%"),
        ("Trained Agent PP Rate", "0.00%"),
        ("Regression Tests", "262/262 passed")
    ]
    for lbl, val in stats:
        sp_stat = ctf.add_paragraph()
        sp_stat.text = f"• {lbl}: {val}"
        sp_stat.font.name = "Arial"
        sp_stat.font.size = Pt(16)
        sp_stat.font.bold = True
        sp_stat.font.color.rgb = color_text
        sp_stat.space_after = Pt(4)

    # Save the presentation
    output_path = Path("docs/presentation.pptx")
    prs.save(str(output_path))
    print(f"Presentation saved successfully to {output_path}!")


if __name__ == "__main__":
    create_presentation()
