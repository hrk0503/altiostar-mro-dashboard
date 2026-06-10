# Altiostar MRO Pipeline — Architecture

This document maps out the 7-autonomous-agent architecture powering the WINNIIO AltioStar Mobility Robustness Optimisation (MRO) training platform. The system operates symmetrically through the Atlas orchestration layer, transitioning sequential data engineering steps into robust deployment pipelines.

```mermaid
graph TD
    %% Base Input Data
    CSV[Operator CSV Data] --> Pipeline

    %% Agent Execution Pipeline
    Pipeline[Pipeline Agent<br/>• Auto-detect CSV schema<br/>• Validate & Normalize] --> Spectrum
    Spectrum[Spectrum Agent<br/>• Telecom Domain Lead<br/>• 3GPP Validation] --> Forge
    Forge[Forge Agent<br/>• Gymnasium Environment<br/>• PPO Training & ONNX] --> Sentinel
    Sentinel[Sentinel Agent<br/>• Automated QA Layer<br/>• Property-Based Tests] --> Deploy
    Deploy[Deploy Agent<br/>• DevOps & CI/CD<br/>• Docker / Helm / K8s] --> Lens
    Lens[Lens Agent<br/>• Streamlit UI Dashboard<br/>• Management PPTX/DOCX]

    %% Orchestration Backbone Control Flow
    Atlas[Atlas Agent<br/>• Product Owner / Scrum Master<br/>• Orchestrates All Agents] -.-> Pipeline
    Atlas -.-> Spectrum
    Atlas -.-> Forge
    Atlas -.-> Sentinel
    Atlas -.-> Deploy
    Atlas -.-> Lens

    %% Visual Styling
    style Atlas fill:#1f2937,stroke:#3b82f6,stroke-width:2px,color:#fff
    style CSV fill:#0f172a,stroke:#64748b,stroke-width:1px,color:#fff
    style Pipeline fill:#1e1b4b,stroke:#4f46e5,color:#fff
    style Spectrum fill:#1e1b4b,stroke:#4f46e5,color:#fff
    style Forge fill:#1e1b4b,stroke:#4f46e5,color:#fff
    style Sentinel fill:#581c87,stroke:#9333ea,color:#fff
    style Deploy fill:#1e1b4b,stroke:#4f46e5,color:#fff
    style Lens fill:#1c1917,stroke:#d6d3d1,color:#fff