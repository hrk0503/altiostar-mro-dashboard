"""Generates a PowerPoint presentation (presentation.pptx) summarizing the MRO training pipeline project.
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
from pptx.enum.text import PP_ALIGN
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
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.2))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = "Arial"
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = color_text
        
        if tag_text:
            p_tag = tf.add_paragraph()
            p_tag.text = f"// {tag_text}"
            p_tag.font.name = "Arial"
            p_tag.font.size = Pt(14)
            p_tag.font.bold = True
            p_tag.font.color.rgb = color_primary
            
    # Helper to add bullet point list
    def add_bullet_list(slide, items, left, top, width, height, font_size=18):
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
            p.space_after = Pt(4)
            
            p_desc = tf.add_paragraph()
            p_desc.text = "  " + item[1]
            p_desc.font.name = "Arial"
            p_desc.font.size = Pt(font_size - 4)
            p_desc.font.color.rgb = color_sub
            p_desc.space_after = Pt(16)
            
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
    p.text = "AltioStar MRO Training Pipeline"
    p.font.name = "Arial"
    p.font.size = Pt(54)
    p.font.bold = True
    p.font.color.rgb = color_text
    p.space_after = Pt(8)
    
    p2 = tf.add_paragraph()
    p2.text = "Reinforcement Learning loops for 5G Handover Optimization"
    p2.font.name = "Arial"
    p2.font.size = Pt(22)
    p2.font.color.rgb = color_primary
    p2.space_after = Pt(48)
    
    p3 = tf.add_paragraph()
    p3.text = "Stream 4 | Harshit · Ananyaa · Shourya · Devika"
    p3.font.name = "Arial"
    p3.font.size = Pt(18)
    p3.font.bold = True
    p3.font.color.rgb = color_accent
    p3.space_after = Pt(4)
    
    p4 = tf.add_paragraph()
    p4.text = "WINNIIO × Amity 2026 | June 2026"
    p4.font.name = "Arial"
    p4.font.size = Pt(14)
    p4.font.color.rgb = color_sub

    # Slide 2: Phase 0 Foundation
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Phase 0: Foundational Setup", "Foundation Checkpoint")
    
    bullets_p0 = [
        ("Dev Environment Bootstrap", "Configured standard local runtimes (Gymnasium, PyTorch, Stable Baselines3, MLflow) on developers' platforms."),
        ("Cell-Level Gymnasium Environment", "Built MROEnv mapping cell parameters (Power, Tilt, CIO) to simulated ROP action modifications and KPI returns."),
        ("Synthetic Data Ingestion", "Integrated parser systems loading mock cluster metrics to feed env steps dynamically."),
        ("Verification testing", "Created regression checking utilities for step values, rewards, and telemetry integrity.")
    ]
    add_bullet_list(slide, bullets_p0, Inches(0.8), Inches(2.0), Inches(6.5), Inches(4.5))
    
    # Version card
    card_box = slide.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.5), Inches(4.5))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "🚀 tag: v0.1.0"
    cp.font.name = "Arial"
    cp.font.size = Pt(28)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(20)
    
    cp2 = ctf.add_paragraph()
    cp2.text = "Outcome:\nVerified a stable local runtime pipeline ready to ingest reinforcement learning training runs."
    cp2.font.name = "Arial"
    cp2.font.size = Pt(18)
    cp2.font.color.rgb = color_text

    # Slide 3: Phase 1 Implementation
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Phase 1: Core Pipeline & Training", "Core Development")
    
    bullets_p1 = [
        ("Relation-Level Environment (v2)", "Extended MROEnv to support granular relation pairs (source cell → target cell), handling 763 relations dynamically."),
        ("SB3 PPO Agent Convergence Loop", "Configured RL policy loops evaluated over consecutive epoch episodes."),
        ("Optuna Hyperparameter Sweeps", "Implemented automated sweeps tuning learning rate, batch size, steps, and discount factor (Gamma) with PPO."),
        ("Clean Tracking & Double Caching", "Resolved MLflow space encoding path bugs and cached dataframes to cut test runtime from hours to 18 seconds.")
    ]
    add_bullet_list(slide, bullets_p1, Inches(0.8), Inches(2.0), Inches(6.5), Inches(4.5))
    
    card_box = slide.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.5), Inches(4.5))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "🔥 tag: v0.2.0"
    cp.font.name = "Arial"
    cp.font.size = Pt(28)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(20)
    
    cp2 = ctf.add_paragraph()
    cp2.text = "Status: 100% Complete\nPassed 144 unit tests, fully green status on Ruff & Mypy, and merged cleanly to staging."
    cp2.font.name = "Arial"
    cp2.font.size = Pt(18)
    cp2.font.color.rgb = color_text

    # Slide 4: Pipeline Architecture
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Entire Training Pipeline Architecture", "System Architecture")
    
    steps = [
        ("1. Data Layer Ingestion", "Reads pm_data_relation_level.csv (142MB containing 2.2M rows)."),
        ("2. Validation & Caching", "Schema checks in schema_mapper.py / Cache layer optimizes boot times."),
        ("3. Gymnasium Simulation", "MROEnv runs relation step changes (observes 763 × 9 vectors, adjusts CIO deltas)."),
        ("4. SB3 PPO Training Loop", "PPO policy loops optimize parameters over rollouts (train_relation_ppo.py)."),
        ("5. Tracking & Model Store", "Logs trial parameters and convergence metrics to local SQLite database (mlflow.db)."),
        ("6. Dashboard Visualizer", "Streamlit app pulls mlflow_run_id results for comparative charts against random baseline.")
    ]
    
    # Left Column
    add_bullet_list(slide, steps[:3], Inches(0.8), Inches(2.0), Inches(5.5), Inches(4.5), font_size=16)
    # Right Column
    add_bullet_list(slide, steps[3:], Inches(6.8), Inches(2.0), Inches(5.5), Inches(4.5), font_size=16)

    # Slide 5: Current Results
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Current Results & Tuning Value", "Model Metrics")
    
    bullets_res = [
        ("Random Baseline Benchmark", "HOSR: 79.25% | PP Rate: 1.39% | Mean Reward: 38.47."),
        ("Trained PPO Agent (100k steps)", "HOSR: 79.27% | Mean Reward: 8,304,784.40 (Robust Policy Convergence)."),
        ("Optuna Sweep Optimization", "Best Trial: LR ~ 0.00056, batch_size: 128, n_steps: 2048, gamma ~ 0.9817.\nYields highest reward: 8,311,482.33.")
    ]
    add_bullet_list(slide, bullets_res, Inches(0.8), Inches(2.0), Inches(6.5), Inches(4.5))
    
    # Stat boxes
    stat_box = slide.shapes.add_textbox(Inches(7.8), Inches(2.0), Inches(4.7), Inches(4.5))
    stf = stat_box.text_frame
    stf.word_wrap = True
    
    sp = stf.paragraphs[0]
    sp.text = "🎯 Key Metrics Summary:"
    sp.font.name = "Arial"
    sp.font.size = Pt(22)
    sp.font.bold = True
    sp.font.color.rgb = color_primary
    sp.space_after = Pt(20)
    
    stats = [
        ("PPO Conv Reward", "8.30 Million"),
        ("Optuna Best Reward", "8.31 Million"),
        ("Success Rate (HOSR)", "79.27%"),
        ("Unit Verification", "144/144 tests passed")
    ]
    for lbl, val in stats:
        sp_stat = stf.add_paragraph()
        sp_stat.text = f"{lbl}: {val}"
        sp_stat.font.name = "Arial"
        sp_stat.font.size = Pt(18)
        sp_stat.font.bold = True
        sp_stat.font.color.rgb = color_text
        sp_stat.space_after = Pt(8)

    # Slide 6: Future Work Phase 2
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    add_slide_header(slide, "Phase 2 Outlook & Roadmap", "Next Tasks")
    
    bullets_p2 = [
        ("ONNX Serialization & Model Export", "Convert Stable Baselines3 PyTorch model checkpoints to lightweight ONNX format to support high-frequency inference runtimes."),
        ("Production Deployment Pipeline", "Create inference loader classes pulling serialized parameters to calculate live CIO adjustments on network controllers."),
        ("MLflow Model Registry Integration", "Register candidate checkpoints, audit tags (Staging, Production), and archive legacy runs."),
        ("In-Field Validation Framework", "Establish shadow deployment metrics to audit agent predictions against live cell-level performance telemetry before enforcement.")
    ]
    add_bullet_list(slide, bullets_p2, Inches(0.8), Inches(2.0), Inches(6.5), Inches(4.5))
    
    card_box = slide.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.5), Inches(4.5))
    ctf = card_box.text_frame
    ctf.word_wrap = True
    
    cp = ctf.paragraphs[0]
    cp.text = "Phase 2 Target:"
    cp.font.name = "Arial"
    cp.font.size = Pt(22)
    cp.font.bold = True
    cp.font.color.rgb = color_primary
    cp.space_after = Pt(14)
    
    cp2 = ctf.add_paragraph()
    cp2.text = "Transitioning the offline training pipeline into a production-grade inference engine serving optimization updates directly to network controllers."
    cp2.font.name = "Arial"
    cp2.font.size = Pt(16)
    cp2.font.color.rgb = color_sub
    
    # Save the presentation
    output_path = Path("docs/presentation.pptx")
    prs.save(str(output_path))
    print(f"Presentation saved successfully to {output_path}!")


if __name__ == "__main__":
    create_presentation()
