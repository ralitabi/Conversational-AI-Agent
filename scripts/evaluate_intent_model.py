"""
Intent Classification Evaluation Suite
=======================================
Strict evaluation with:
  - Per-intent accuracy breakdown
  - Per-service accuracy breakdown
  - Confidence-threshold enforcement (correct but low-confidence = "weak")
  - Top-3 accuracy (does true label appear in top-3 candidates?)
  - Misclassification pair analysis
  - Hardest-cases report (wrong + low-confidence-correct)
  - Confusion matrix (full + per-service)
  - Plots: per-intent accuracy bar, confidence histogram, confusion matrix
  - HTML report
"""
from __future__ import annotations

import html as html_module
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from backend.intent_classifier import IntentClassifier

# --- Thresholds ---------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.20   # below this a "correct" answer is still flagged WEAK
STRONG_CONFIDENCE    = 0.45   # above this is a firm prediction
TOP_K                = 3      # rank at which we check top-K accuracy
PASS_ACCURACY        = 0.90   # >= 90% = PASS
WARN_ACCURACY        = 0.75   # 75--89% = WARN, < 75% = FAIL


# --- Data loading -------------------------------------------------------------

def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"  [SKIP] Bad JSON line {line_no} in {file_path.name}: {exc}")
    return rows


def find_eval_files(datasets_root: Path) -> List[Path]:
    return sorted(datasets_root.glob("*/eval_set.jsonl"))


def find_intent_files(datasets_root: Path) -> List[Path]:
    return sorted(
        p for p in datasets_root.glob("*/*.json")
        if "intent" in p.stem.lower()
    )


def load_intent_examples(intent_file: Path) -> List[Dict[str, Any]]:
    try:
        with intent_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"  [SKIP] Cannot load {intent_file.name}: {exc}")
        return []

    if not isinstance(data, list):
        return []

    rows: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text  = str(item.get("text", "")).strip()
        label = str(item.get("intent", "")).strip()
        if text and label:
            rows.append({
                "text":        text,
                "label":       label,
                "service":     str(item.get("service", intent_file.parent.name)).strip(),
                "source_file": str(intent_file),
            })
    return rows


def detect_keys(row: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    text_key  = next((k for k in ["text", "question", "user_query", "query"] if k in row), None)
    label_key = next((k for k in ["label", "expected_intent", "intent"] if k in row), None)
    return (text_key, label_key) if text_key and label_key else None


# --- Core evaluation ----------------------------------------------------------

def evaluate_rows(
    classifier: IntentClassifier,
    rows: List[Dict[str, Any]],
    dataset_name: str,
    source_name: str,
) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()

    records: List[Dict[str, Any]] = []

    for row in rows:
        keys = detect_keys(row)
        if keys is None:
            continue

        text_key, label_key = keys
        text         = str(row[text_key]).strip()
        true_label   = str(row[label_key]).strip()
        service      = str(row.get("service", dataset_name)).strip() or dataset_name

        if not text or not true_label:
            continue

        # Use classify() to get full candidate list for top-K
        try:
            result = classifier.classify(text, selected_service=service)
        except Exception:
            result = {}

        predicted_label = result.get("intent") or ""
        confidence      = float(result.get("confidence", 0.0))
        candidates      = result.get("candidates", []) or []

        top_k_labels = [c.get("intent", "") for c in candidates[:TOP_K]]
        correct      = true_label == predicted_label
        top_k_hit    = true_label in top_k_labels
        confident_ok = correct and confidence >= CONFIDENCE_THRESHOLD

        records.append({
            "dataset":          dataset_name,
            "source_name":      source_name,
            "service":          service,
            "text":             text,
            "true_label":       true_label,
            "predicted_label":  predicted_label,
            "confidence":       round(confidence, 4),
            "correct":          correct,
            "top_k_correct":    top_k_hit,
            "confident_correct": confident_ok,
            "top_k_candidates": ", ".join(top_k_labels),
        })

    return pd.DataFrame(records)


def evaluate_eval_file(classifier: IntentClassifier, p: Path) -> pd.DataFrame:
    return evaluate_rows(classifier, load_jsonl(p), p.parent.name, str(p))


def evaluate_intent_file(classifier: IntentClassifier, p: Path) -> pd.DataFrame:
    return evaluate_rows(classifier, load_intent_examples(p), p.parent.name, str(p))


# --- Aggregate views ----------------------------------------------------------

def per_intent_summary(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("true_label")
        .agg(
            samples          = ("correct", "size"),
            correct          = ("correct", "sum"),
            accuracy         = ("correct", "mean"),
            top_k_accuracy   = ("top_k_correct", "mean"),
            confident_hits   = ("confident_correct", "sum"),
            avg_confidence   = ("confidence", "mean"),
            min_confidence   = ("confidence", "min"),
        )
        .reset_index()
        .rename(columns={"true_label": "intent"})
    )
    agg["accuracy"]       = agg["accuracy"].round(4)
    agg["top_k_accuracy"] = agg["top_k_accuracy"].round(4)
    agg["avg_confidence"] = agg["avg_confidence"].round(4)
    agg["min_confidence"] = agg["min_confidence"].round(4)
    agg["grade"] = agg["accuracy"].map(
        lambda a: "PASS" if a >= PASS_ACCURACY else ("WARN" if a >= WARN_ACCURACY else "FAIL")
    )
    return agg.sort_values("accuracy", ascending=True)


def per_service_summary(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("service")
        .agg(
            samples         = ("correct", "size"),
            accuracy        = ("correct", "mean"),
            top_k_accuracy  = ("top_k_correct", "mean"),
            macro_f1        = ("correct", lambda x: f1_score(
                df.loc[x.index, "true_label"],
                df.loc[x.index, "predicted_label"],
                average="macro", zero_division=0,
            )),
            avg_confidence  = ("confidence", "mean"),
            weak_pct        = ("confident_correct", lambda x: 1 - x.mean()),
        )
        .reset_index()
    )
    for col in ["accuracy", "top_k_accuracy", "macro_f1", "avg_confidence", "weak_pct"]:
        agg[col] = agg[col].round(4)
    agg["grade"] = agg["accuracy"].map(
        lambda a: "PASS" if a >= PASS_ACCURACY else ("WARN" if a >= WARN_ACCURACY else "FAIL")
    )
    return agg.sort_values("accuracy", ascending=True)


def per_dataset_summary(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("dataset")
        .agg(
            samples         = ("correct", "size"),
            accuracy        = ("correct", "mean"),
            top_k_accuracy  = ("top_k_correct", "mean"),
            avg_confidence  = ("confidence", "mean"),
        )
        .reset_index()
    )
    for col in ["accuracy", "top_k_accuracy", "avg_confidence"]:
        agg[col] = agg[col].round(4)
    agg["grade"] = agg["accuracy"].map(
        lambda a: "PASS" if a >= PASS_ACCURACY else ("WARN" if a >= WARN_ACCURACY else "FAIL")
    )
    return agg.sort_values("accuracy", ascending=False)


def misclassification_pairs(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    errors = df[~df["correct"]].copy()
    if errors.empty:
        return pd.DataFrame(columns=["true_label", "predicted_label", "count", "examples"])

    pairs = (
        errors.groupby(["true_label", "predicted_label"])
        .agg(count=("text", "size"), examples=("text", lambda x: " | ".join(list(x)[:2])))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(top_n)
    )
    return pairs


def hardest_cases(df: pd.DataFrame, n: int = 30) -> pd.DataFrame:
    """Wrong predictions + correct-but-low-confidence, sorted by confidence."""
    hard = df[~df["correct"] | (df["correct"] & (df["confidence"] < CONFIDENCE_THRESHOLD))].copy()
    hard = hard.sort_values("confidence", ascending=True)
    return hard[["service", "text", "true_label", "predicted_label", "confidence", "correct"]].head(n)


def confidence_buckets(df: pd.DataFrame) -> pd.DataFrame:
    bins   = [0, 0.10, 0.20, 0.35, 0.50, 0.70, 1.01]
    labels = ["0--0.10", "0.10--0.20", "0.20--0.35", "0.35--0.50", "0.50--0.70", "0.70+"]
    df2    = df.copy()
    df2["bucket"] = pd.cut(df2["confidence"], bins=bins, labels=labels, right=False)
    tbl = (
        df2.groupby("bucket", observed=True)
        .agg(
            samples  = ("correct", "size"),
            accuracy = ("correct", "mean"),
        )
        .reset_index()
    )
    tbl["accuracy"] = tbl["accuracy"].round(4)
    return tbl


# --- Console output -----------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    return "#" * filled + "." * (width - filled)


def print_summary(df: pd.DataFrame) -> None:
    y_true = df["true_label"]
    y_pred = df["predicted_label"]
    acc    = accuracy_score(y_true, y_pred)
    topk   = df["top_k_correct"].mean()
    conf   = df["confidence"].mean()
    weak   = (~df["confident_correct"] & df["correct"]).sum()
    wrong  = (~df["correct"]).sum()

    grade  = "PASS" if acc >= PASS_ACCURACY else ("WARN" if acc >= WARN_ACCURACY else "FAIL")
    grade_symbol = {"PASS": "[OK]", "WARN": "!", "FAIL": "[X]"}[grade]

    print("\n" + "=" * 68)
    print("  OVERALL EVALUATION RESULTS")
    print("=" * 68)
    print(f"  Samples evaluated   : {len(df)}")
    print(f"  Accuracy            : {acc:.4f}  {_bar(acc)}  [{grade_symbol} {grade}]")
    print(f"  Top-{TOP_K} accuracy    : {topk:.4f}  {_bar(topk)}")
    print(f"  Avg confidence      : {conf:.4f}  {_bar(conf)}")
    print(f"  Wrong predictions   : {wrong}  ({wrong/len(df)*100:.1f}%)")
    print(f"  Correct but weak    : {weak}  (conf < {CONFIDENCE_THRESHOLD})")
    print("=" * 68)


def print_per_service(df: pd.DataFrame) -> None:
    svc = per_service_summary(df)
    print("\n" + "-" * 68)
    print("  PER-SERVICE BREAKDOWN")
    print("-" * 68)
    hdr = f"  {'Service':<30}  {'N':>5}  {'Acc':>7}  {'Top-K':>7}  {'F1':>6}  {'Grade'}"
    print(hdr)
    print("  " + "-" * 64)
    for _, r in svc.iterrows():
        grade_sym = {"PASS": "[OK]", "WARN": "!", "FAIL": "[X]"}.get(r["grade"], "?")
        print(
            f"  {r['service']:<30}  {r['samples']:>5}  "
            f"{r['accuracy']:>7.4f}  {r['top_k_accuracy']:>7.4f}  "
            f"{r['macro_f1']:>6.4f}  {grade_sym} {r['grade']}"
        )


def print_per_intent(df: pd.DataFrame) -> None:
    intent = per_intent_summary(df)
    print("\n" + "-" * 68)
    print("  PER-INTENT ACCURACY (sorted worst -> best)")
    print("-" * 68)
    hdr = f"  {'Intent':<42}  {'N':>4}  {'Acc':>7}  {'Top-K':>7}  {'AvgConf':>8}  {'Grade'}"
    print(hdr)
    print("  " + "-" * 64)
    for _, r in intent.iterrows():
        grade_sym = {"PASS": "[OK]", "WARN": "!", "FAIL": "[X]"}.get(r["grade"], "?")
        print(
            f"  {r['intent']:<42}  {r['samples']:>4}  "
            f"{r['accuracy']:>7.4f}  {r['top_k_accuracy']:>7.4f}  "
            f"{r['avg_confidence']:>8.4f}  {grade_sym} {r['grade']}"
        )


def print_misclassifications(df: pd.DataFrame) -> None:
    pairs = misclassification_pairs(df, top_n=15)
    if pairs.empty:
        print("\n  No misclassifications!")
        return

    print("\n" + "-" * 68)
    print("  TOP MISCLASSIFICATION PAIRS")
    print("-" * 68)
    for _, r in pairs.iterrows():
        print(f"  {r['true_label']:<38}  ->  {r['predicted_label']:<38}  (x{r['count']})")
        for ex in str(r["examples"]).split(" | "):
            print(f"       \"{ex.strip()}\"")


def print_confidence_buckets(df: pd.DataFrame) -> None:
    tbl = confidence_buckets(df)
    print("\n" + "-" * 68)
    print("  ACCURACY BY CONFIDENCE BUCKET")
    print("-" * 68)
    print(f"  {'Bucket':<14}  {'Samples':>8}  {'Accuracy':>10}")
    print("  " + "-" * 38)
    for _, r in tbl.iterrows():
        print(f"  {str(r['bucket']):<14}  {r['samples']:>8}  {r['accuracy']:>10.4f}")


def print_hardest_cases(df: pd.DataFrame) -> None:
    hard = hardest_cases(df, n=15)
    if hard.empty:
        return
    print("\n" + "-" * 68)
    print("  HARDEST CASES  (wrong | correct but low-confidence)")
    print("-" * 68)
    for _, r in hard.iterrows():
        flag = "WRONG" if not r["correct"] else "WEAK"
        print(f"  [{flag:<5}] conf={r['confidence']:.4f}  [{r['service']}]")
        print(f"    text     : \"{r['text']}\"")
        print(f"    true     : {r['true_label']}")
        if not r["correct"]:
            print(f"    got      : {r['predicted_label']}")


def print_classification_report(df: pd.DataFrame) -> None:
    print("\n" + "-" * 68)
    print("  SKLEARN CLASSIFICATION REPORT")
    print("-" * 68)
    print(classification_report(df["true_label"], df["predicted_label"], zero_division=0))


# --- Plots --------------------------------------------------------------------

def _brand_cmap() -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list("brand", ["#c00000", "#bfbfbf", "#ffffff"])


def save_confusion_matrix_plot(df: pd.DataFrame, output_dir: Path) -> None:
    y_true  = df["true_label"]
    y_pred  = df["predicted_label"]
    labels  = sorted(set(y_true) | set(y_pred))
    cm      = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df   = pd.DataFrame(cm, index=labels, columns=labels)

    fw = max(14, len(labels) * 0.9)
    fh = max(11, len(labels) * 0.7)
    fig, ax = plt.subplots(figsize=(fw, fh))
    im = ax.imshow(cm_df.values, cmap=_brand_cmap(), aspect="auto")

    ax.set_title("Intent Classification --- Confusion Matrix", fontsize=15, pad=14)
    ax.set_xlabel("Predicted Label", fontsize=11)
    ax.set_ylabel("True Label", fontsize=11)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)

    mx  = cm_df.values.max() if cm_df.values.size else 0
    thr = mx / 2 if mx else 0
    for i in range(cm_df.shape[0]):
        for j in range(cm_df.shape[1]):
            v   = cm_df.iat[i, j]
            col = "white" if (v > thr and v != 0) else "black"
            ax.text(j, i, str(v), ha="center", va="center", color=col, fontsize=7)

    cb = fig.colorbar(im, ax=ax)
    cb.set_label("Count", rotation=270, labelpad=16)
    plt.tight_layout()
    out = output_dir / "confusion_matrix.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def save_per_intent_bar_chart(df: pd.DataFrame, output_dir: Path) -> None:
    intent_df = per_intent_summary(df).sort_values("accuracy", ascending=True)
    intents   = intent_df["intent"].tolist()
    accs      = intent_df["accuracy"].tolist()
    topks     = intent_df["top_k_accuracy"].tolist()

    colors = [
        "#c00000" if a < WARN_ACCURACY else ("#e6a817" if a < PASS_ACCURACY else "#1a7a3e")
        for a in accs
    ]

    fig, ax = plt.subplots(figsize=(12, max(6, len(intents) * 0.45)))
    y = np.arange(len(intents))

    bars = ax.barh(y, accs, color=colors, height=0.5, label="Accuracy", zorder=2)
    ax.scatter(topks, y, color="#0f4ca3", s=50, zorder=3, label=f"Top-{TOP_K} Accuracy", marker="D")

    ax.axvline(PASS_ACCURACY, color="#1a7a3e", linestyle="--", linewidth=1.2, alpha=0.8, label=f"Pass ({PASS_ACCURACY})")
    ax.axvline(WARN_ACCURACY, color="#e6a817", linestyle="--", linewidth=1.2, alpha=0.8, label=f"Warn ({WARN_ACCURACY})")

    for bar, a in zip(bars, accs):
        ax.text(
            min(a + 0.01, 0.99), bar.get_y() + bar.get_height() / 2,
            f"{a:.2%}", va="center", ha="left", fontsize=8.5,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(intents, fontsize=9)
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("Accuracy", fontsize=11)
    ax.set_title("Per-Intent Accuracy", fontsize=14, pad=12)
    ax.grid(axis="x", linestyle=":", alpha=0.5, zorder=0)
    ax.legend(fontsize=9, loc="lower right")
    plt.tight_layout()
    out = output_dir / "per_intent_accuracy.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def save_confidence_histogram(df: pd.DataFrame, output_dir: Path) -> None:
    correct_conf   = df[df["correct"]]["confidence"]
    incorrect_conf = df[~df["correct"]]["confidence"]

    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.linspace(0, 1, 26)

    ax.hist(correct_conf,   bins=bins, alpha=0.7, color="#1a7a3e", label="Correct",   edgecolor="white", linewidth=0.4)
    ax.hist(incorrect_conf, bins=bins, alpha=0.7, color="#c00000", label="Incorrect", edgecolor="white", linewidth=0.4)

    ax.axvline(CONFIDENCE_THRESHOLD, color="#e6a817", linestyle="--", linewidth=1.5, label=f"Low-confidence threshold ({CONFIDENCE_THRESHOLD})")
    ax.axvline(STRONG_CONFIDENCE,    color="#0f4ca3", linestyle="--", linewidth=1.5, label=f"Strong threshold ({STRONG_CONFIDENCE})")

    ax.set_xlabel("Confidence Score", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title("Confidence Score Distribution --- Correct vs. Incorrect", fontsize=13, pad=12)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle=":", alpha=0.4)
    plt.tight_layout()
    out = output_dir / "confidence_histogram.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


def save_dataset_summary_table(df: pd.DataFrame, output_dir: Path) -> None:
    summary_df = per_dataset_summary(df).copy()
    summary_df["accuracy"]       = summary_df["accuracy"].map(lambda x: f"{x:.4f}")
    summary_df["top_k_accuracy"] = summary_df["top_k_accuracy"].map(lambda x: f"{x:.4f}")
    summary_df["avg_confidence"] = summary_df["avg_confidence"].map(lambda x: f"{x:.4f}")

    fig_h = max(3, 0.55 * (len(summary_df) + 2))
    fig, ax = plt.subplots(figsize=(11, fig_h))
    ax.axis("off")

    table = ax.table(
        cellText=summary_df.values,
        colLabels=summary_df.columns,
        loc="center", cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.55)

    grade_col = list(summary_df.columns).index("grade")
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#808080")
        if row == 0:
            cell.set_facecolor("#c00000")
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        else:
            base = "#f2f2f2" if row % 2 == 1 else "#d9d9d9"
            cell.set_facecolor(base)
            if col == grade_col:
                val = summary_df.iloc[row - 1, grade_col]
                cell.set_facecolor(
                    "#c8f0d4" if val == "PASS"
                    else ("#fff3cd" if val == "WARN" else "#f4cccc")
                )

    plt.title("Dataset-Level Accuracy", fontsize=13, pad=10)
    plt.tight_layout()
    out = output_dir / "dataset_accuracy_table.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {out}")


# --- HTML report --------------------------------------------------------------

def _grade_badge(grade: str) -> str:
    color = {"PASS": "#1a7a3e", "WARN": "#7c5e00", "FAIL": "#c00000"}.get(grade, "#333")
    bg    = {"PASS": "#c8f0d4", "WARN": "#fff3cd", "FAIL": "#f4cccc"}.get(grade, "#eee")
    return (
        f'<span style="background:{bg};color:{color};padding:2px 8px;'
        f'border-radius:4px;font-weight:700;font-size:0.82em">{grade}</span>'
    )


def _conf_bar(value: float) -> str:
    pct   = round(value * 100)
    color = "#1a7a3e" if value >= STRONG_CONFIDENCE else ("#e6a817" if value >= CONFIDENCE_THRESHOLD else "#c00000")
    return (
        f'<div style="display:flex;align-items:center;gap:6px">'
        f'<div style="background:#e0e0e0;border-radius:3px;height:10px;width:80px;overflow:hidden">'
        f'<div style="background:{color};height:100%;width:{pct}%"></div></div>'
        f'<span style="font-size:0.85em">{value:.4f}</span>'
        f'</div>'
    )


def save_html_report(
    df: pd.DataFrame,
    output_dir: Path,
) -> None:
    y_true = df["true_label"]
    y_pred = df["predicted_label"]
    acc    = accuracy_score(y_true, y_pred)
    topk   = df["top_k_correct"].mean()
    conf   = df["confidence"].mean()
    wrong  = int((~df["correct"]).sum())
    weak   = int((df["correct"] & (df["confidence"] < CONFIDENCE_THRESHOLD)).sum())

    intent_df   = per_intent_summary(df)
    service_df  = per_service_summary(df)
    pairs_df    = misclassification_pairs(df, top_n=20)
    hard_df     = hardest_cases(df, n=25)
    bucket_df   = confidence_buckets(df)

    grade      = "PASS" if acc >= PASS_ACCURACY else ("WARN" if acc >= WARN_ACCURACY else "FAIL")
    grade_html = _grade_badge(grade)

    def df_to_html_table(d: pd.DataFrame, row_color_col: Optional[str] = None) -> str:
        if d.empty:
            return "<p><em>No data.</em></p>"

        col_html = "".join(
            f'<th style="background:#c00000;color:white;padding:6px 10px;text-align:left">{html_module.escape(str(c))}</th>'
            for c in d.columns
        )
        rows_html = ""
        for i, (_, row) in enumerate(d.iterrows()):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            cells = ""
            for col_name, val in row.items():
                cell_bg = bg
                if col_name == "grade" or col_name == row_color_col:
                    g = str(val)
                    cell_bg = (
                        "#c8f0d4" if g == "PASS"
                        else ("#fff3cd" if g == "WARN" else "#f4cccc" if g == "FAIL" else bg)
                    )
                if col_name == "avg_confidence" or col_name == "confidence":
                    try:
                        cell_html = _conf_bar(float(val))
                    except Exception:
                        cell_html = html_module.escape(str(val))
                elif col_name == "correct":
                    cell_html = (
                        '<span style="color:#1a7a3e;font-weight:700">[OK]</span>' if val
                        else '<span style="color:#c00000;font-weight:700">[X]</span>'
                    )
                else:
                    cell_html = html_module.escape(str(val))

                cells += f'<td style="padding:5px 10px;border-bottom:1px solid #e0e0e0;background:{cell_bg}">{cell_html}</td>'
            rows_html += f"<tr>{cells}</tr>"

        return (
            '<table style="border-collapse:collapse;width:100%;font-size:0.88em">'
            f'<thead><tr>{col_html}</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            "</table>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Intent Evaluation Report</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;margin:0;padding:24px;color:#1e293b}}
  h1{{color:#c00000;margin-bottom:4px}}
  h2{{color:#123b7a;border-bottom:2px solid #c00000;padding-bottom:4px;margin-top:32px}}
  .card{{background:white;border-radius:10px;padding:22px 28px;margin-bottom:22px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .metrics{{display:flex;gap:20px;flex-wrap:wrap;margin-top:12px}}
  .metric{{background:#f5f8ff;border:1px solid #d0dcf5;border-radius:8px;padding:14px 20px;min-width:160px;text-align:center}}
  .metric-val{{font-size:2em;font-weight:700;color:#123b7a}}
  .metric-lbl{{font-size:0.8em;color:#64748b;margin-top:2px}}
  .note{{background:#fff3cd;border:1px solid #f0c040;border-radius:6px;padding:10px 14px;font-size:0.87em;margin-top:12px}}
  img{{max-width:100%;border-radius:8px;margin-top:12px}}
  p.sub{{color:#64748b;font-size:0.9em;margin:4px 0 12px}}
</style>
</head>
<body>

<div class="card">
  <h1>Intent Classification --- Evaluation Report</h1>
  <p class="sub">Bradford Council Assistant &nbsp;|&nbsp; Total samples: <strong>{len(df)}</strong></p>
  <div class="metrics">
    <div class="metric"><div class="metric-val">{acc:.2%}</div><div class="metric-lbl">Overall Accuracy</div></div>
    <div class="metric"><div class="metric-val">{topk:.2%}</div><div class="metric-lbl">Top-{TOP_K} Accuracy</div></div>
    <div class="metric"><div class="metric-val">{conf:.4f}</div><div class="metric-lbl">Avg Confidence</div></div>
    <div class="metric"><div class="metric-val">{wrong}</div><div class="metric-lbl">Wrong Predictions</div></div>
    <div class="metric"><div class="metric-val">{weak}</div><div class="metric-lbl">Correct but Weak<br><span style="font-size:0.65em;color:#9ca3af">(conf &lt; {CONFIDENCE_THRESHOLD})</span></div></div>
    <div class="metric" style="background:#f5fff8;border-color:#b7f0cc"><div class="metric-val">{grade_html}</div><div class="metric-lbl">Overall Grade</div></div>
  </div>
  <div class="note">
    <strong>Thresholds:</strong>
    Pass >= {PASS_ACCURACY:.0%} &nbsp;|&nbsp;
    Warn >= {WARN_ACCURACY:.0%} &nbsp;|&nbsp;
    Fail &lt; {WARN_ACCURACY:.0%} &nbsp;&nbsp;-&nbsp;&nbsp;
    Confidence: Strong >= {STRONG_CONFIDENCE} &nbsp;|&nbsp; Low &lt; {CONFIDENCE_THRESHOLD}
  </div>
</div>

<div class="card">
  <h2>Per-Service Summary</h2>
  {df_to_html_table(service_df, row_color_col="grade")}
</div>

<div class="card">
  <h2>Per-Intent Accuracy (worst -> best)</h2>
  {df_to_html_table(intent_df, row_color_col="grade")}
  <img src="per_intent_accuracy.png" alt="Per-intent accuracy bar chart">
</div>

<div class="card">
  <h2>Accuracy by Confidence Bucket</h2>
  <p class="sub">Shows how prediction accuracy varies across confidence levels.</p>
  {df_to_html_table(bucket_df)}
  <img src="confidence_histogram.png" alt="Confidence histogram">
</div>

<div class="card">
  <h2>Confusion Matrix</h2>
  <img src="confusion_matrix.png" alt="Confusion matrix">
</div>

<div class="card">
  <h2>Top Misclassification Pairs</h2>
  <p class="sub">Most frequent true->predicted error combinations.</p>
  {df_to_html_table(pairs_df)}
</div>

<div class="card">
  <h2>Hardest Cases</h2>
  <p class="sub">Wrong predictions and correct-but-low-confidence examples, sorted by ascending confidence.</p>
  {df_to_html_table(hard_df, row_color_col="correct")}
</div>

<div class="card">
  <h2>Dataset-Level Summary</h2>
  <img src="dataset_accuracy_table.png" alt="Dataset accuracy table">
</div>

</body>
</html>"""

    out = output_dir / "evaluation_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Saved: {out}")


# --- File outputs -------------------------------------------------------------

def save_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    y_true = df["true_label"]
    y_pred = df["predicted_label"]
    acc    = accuracy_score(y_true, y_pred)

    # CSVs
    df.to_csv(output_dir / "intent_eval_results.csv", index=False)
    df[~df["correct"]].to_csv(output_dir / "intent_eval_errors.csv", index=False)
    hardest_cases(df, n=50).to_csv(output_dir / "hardest_cases.csv", index=False)
    per_intent_summary(df).to_csv(output_dir / "per_intent_summary.csv", index=False)
    per_service_summary(df).to_csv(output_dir / "per_service_summary.csv", index=False)
    misclassification_pairs(df).to_csv(output_dir / "misclassification_pairs.csv", index=False)
    build_confusion_matrix_df(df).to_csv(output_dir / "confusion_matrix.csv")
    confidence_buckets(df).to_csv(output_dir / "confidence_buckets.csv", index=False)

    with open(output_dir / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Samples: {len(df)}\nAccuracy: {acc:.4f}\n\n")
        f.write(classification_report(y_true, y_pred, zero_division=0))

    # Plots
    save_confusion_matrix_plot(df, output_dir)
    save_per_intent_bar_chart(df, output_dir)
    save_confidence_histogram(df, output_dir)
    save_dataset_summary_table(df, output_dir)

    # HTML report
    save_html_report(df, output_dir)

    print("\n" + "=" * 68)
    print("  OUTPUTS SAVED")
    print("=" * 68)
    saved = [
        "intent_eval_results.csv",
        "intent_eval_errors.csv",
        "hardest_cases.csv",
        "per_intent_summary.csv",
        "per_service_summary.csv",
        "misclassification_pairs.csv",
        "confusion_matrix.csv",
        "confidence_buckets.csv",
        "classification_report.txt",
        "confusion_matrix.png",
        "per_intent_accuracy.png",
        "confidence_histogram.png",
        "dataset_accuracy_table.png",
        "evaluation_report.html",
    ]
    for name in saved:
        print(f"  {output_dir / name}")


def build_confusion_matrix_df(df: pd.DataFrame) -> pd.DataFrame:
    y_true = df["true_label"]
    y_pred = df["predicted_label"]
    labels = sorted(set(y_true) | set(y_pred))
    cm     = confusion_matrix(y_true, y_pred, labels=labels)
    return pd.DataFrame(cm, index=labels, columns=labels)


# --- Entry point --------------------------------------------------------------

def main() -> None:
    project_root  = Path(__file__).resolve().parent.parent
    datasets_root = project_root / "datasets"
    output_dir    = project_root / "evaluation"

    print("=" * 68)
    print("  INTENT EVALUATION SUITE --- Bradford Council Assistant")
    print("=" * 68)
    print(f"  Datasets root : {datasets_root}")
    print(f"  Output dir    : {output_dir}")
    print(f"  Thresholds    : pass={PASS_ACCURACY}  warn={WARN_ACCURACY}  low-conf={CONFIDENCE_THRESHOLD}")

    if not datasets_root.exists():
        print(f"\n  ERROR: Datasets folder not found: {datasets_root}")
        return

    classifier = IntentClassifier(datasets_root=datasets_root)

    eval_files   = find_eval_files(datasets_root)
    intent_files = find_intent_files(datasets_root)

    all_results: List[pd.DataFrame] = []

    if eval_files:
        print(f"\n  Found {len(eval_files)} eval_set.jsonl file(s).")
        for p in eval_files:
            print(f"  -> {p}")
            df = evaluate_eval_file(classifier, p)
            if not df.empty:
                all_results.append(df)
    else:
        print(f"\n  No eval_set.jsonl found --- using {len(intent_files)} intent JSON file(s).")
        for p in intent_files:
            print(f"  -> {p}")
            df = evaluate_intent_file(classifier, p)
            if not df.empty:
                all_results.append(df)

    if not all_results:
        print("\n  No evaluation data could be processed.")
        return

    final_df = pd.concat(all_results, ignore_index=True)

    print_summary(final_df)
    print_per_service(final_df)
    print_per_intent(final_df)
    print_confidence_buckets(final_df)
    print_misclassifications(final_df)
    print_hardest_cases(final_df)
    print_classification_report(final_df)

    print("\n" + "-" * 68)
    print("  Generating outputs ...")
    save_outputs(final_df, output_dir)


if __name__ == "__main__":
    main()
