import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    results_dir = ROOT / "results"
    output_csv = results_dir / "temporal_eval_summary.csv"
    
    rows = []
    
    # 1. Parse Shibuya Baseline
    shibuya_path = results_dir / "experiment_v2_baseline.json"
    if shibuya_path.exists():
        with open(shibuya_path) as f:
            data = json.load(f)
        eval_data = data.get("evaluation", {})
        rows.append({
            "Geography": "shibuya_baseline",
            "Season/Variant": "baseline",
            "Training Set HOSR (%)": "99.99 (Full)",
            "Test Set HOSR (%)": f"{eval_data.get('ho_success_rate', 0.0):.4f}",
            "Ping-Pong Rate (%)": f"{eval_data.get('pingpong_rate', 0.0):.4f}",
            "Generalization Gap (%)": "N/A",
            "Source File": "experiment_v2_baseline.json"
        })

    # 2. Parse Kyiv
    kyiv_path = results_dir / "kyiv_temporal_evaluation.json"
    if kyiv_path.exists():
        with open(kyiv_path) as f:
            data = json.load(f)
        for res in data.get("results", []):
            geo = res.get("geography", "")
            eval_data = res.get("evaluation", {})
            full_hosr = 0.0
            if "autumn" in geo:
                full_hosr = 96.905
            elif "spring" in geo:
                full_hosr = 97.1931
            elif "summer" in geo:
                full_hosr = 96.6977
            elif "winter" in geo:
                full_hosr = 95.5229
                
            test_hosr = eval_data.get("ho_success_rate", 0.0)
            gap = test_hosr - full_hosr
            rows.append({
                "Geography": geo,
                "Season/Variant": geo.split("_")[-1],
                "Training Set HOSR (%)": f"{full_hosr:.4f}",
                "Test Set HOSR (%)": f"{test_hosr:.4f}",
                "Ping-Pong Rate (%)": f"{eval_data.get('pingpong_rate', 0.0):.4f}",
                "Generalization Gap (%)": f"{gap:+.4f}",
                "Source File": "kyiv_temporal_evaluation.json"
            })

    # 3. Parse Helsinki
    helsinki_path = results_dir / "helsinki_temporal_evaluation.json"
    if helsinki_path.exists():
        with open(helsinki_path) as f:
            data = json.load(f)
        for res in data.get("results", []):
            geo = res.get("geography", "")
            eval_data = res.get("evaluation", {})
            full_hosr = 0.0
            if "autumn" in geo:
                full_hosr = 96.7265
            elif "spring" in geo:
                full_hosr = 97.2056
            elif "summer" in geo:
                full_hosr = 96.8434
            elif "winter" in geo:
                full_hosr = 95.002
                
            test_hosr = eval_data.get("ho_success_rate", 0.0)
            gap = test_hosr - full_hosr
            rows.append({
                "Geography": geo,
                "Season/Variant": geo.split("_")[-1],
                "Training Set HOSR (%)": f"{full_hosr:.4f}",
                "Test Set HOSR (%)": f"{test_hosr:.4f}",
                "Ping-Pong Rate (%)": f"{eval_data.get('pingpong_rate', 0.0):.4f}",
                "Generalization Gap (%)": f"{gap:+.4f}",
                "Source File": "helsinki_temporal_evaluation.json"
            })

    # 4. Parse Tokyo
    tokyo_path = results_dir / "tokyo_eval_results.json"
    if tokyo_path.exists():
        with open(tokyo_path) as f:
            data = json.load(f)
        for season_name, res in data.get("seasons", {}).items():
            train_eval = res.get("train_evaluation", {})
            test_eval = res.get("test_evaluation", {})
            train_hosr = train_eval.get("ho_success_rate", 0.0)
            test_hosr = test_eval.get("ho_success_rate", 0.0)
            gap = test_hosr - train_hosr
            rows.append({
                "Geography": season_name,
                "Season/Variant": season_name.split("_")[-1],
                "Training Set HOSR (%)": f"{train_hosr:.4f}",
                "Test Set HOSR (%)": f"{test_hosr:.4f}",
                "Ping-Pong Rate (%)": f"{test_eval.get('pingpong_rate', 0.0):.4f}",
                "Generalization Gap (%)": f"{gap:+.4f}",
                "Source File": "tokyo_eval_results.json"
            })

    # Write to CSV
    fields = ["Geography", "Season/Variant", "Training Set HOSR (%)", "Test Set HOSR (%)", "Ping-Pong Rate (%)", "Generalization Gap (%)", "Source File"]
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Successfully generated unified evaluation CSV: {output_csv}")

if __name__ == "__main__":
    main()
