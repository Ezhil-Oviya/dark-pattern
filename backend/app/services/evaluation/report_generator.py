import csv
import io
import logging
from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.evaluation.literature_repository import PublishedLiteratureRepository

logger = logging.getLogger(__name__)


class EvaluationReportGenerator:
    """
    Generates downloadable evaluation reports in CSV and PDF formats,
    incorporating empirical experimental results, category breakdowns,
    and verified published research citations.
    """

    @staticmethod
    def generate_csv(evaluation_data: Dict[str, Any]) -> str:
        """
        Exports the complete evaluation record to a clean, multi-section CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Metadata
        writer.writerow(["================================================================="])
        writer.writerow(["DARK PATTERN COMPLIANCE AUDITING FRAMEWORK: ALGORITHM EVALUATION REPORT"])
        writer.writerow(["================================================================="])
        writer.writerow(["Evaluation ID", evaluation_data.get("evaluation_id", "N/A")])
        writer.writerow(["Evaluation Date", evaluation_data.get("created_at", "N/A")])
        writer.writerow(["Dataset Name", evaluation_data.get("dataset_name", "N/A")])
        writer.writerow(["Dataset Version", evaluation_data.get("dataset_version", "N/A")])
        writer.writerow(["Dataset SHA-256 Checksum", evaluation_data.get("dataset_hash", "N/A")])
        writer.writerow(["Train/Test Split", evaluation_data.get("split_policy", "Stratified 70/30 (seed=42)")])
        writer.writerow(["Total Test Samples Evaluated", evaluation_data.get("test_sample_count", 0)])
        writer.writerow([])

        # 2. Overall Model Comparison (Experimental)
        writer.writerow(["-----------------------------------------------------------------"])
        writer.writerow(["SECTION 1: OUR EXPERIMENTAL RESULTS (SHARED HELD-OUT TEST DATASET)"])
        writer.writerow(["-----------------------------------------------------------------"])
        writer.writerow(["Algorithm / Model", "Paradigm", "Accuracy (%)", "Precision (%)", "Recall (%)", "F1-Score (%)", "FP Rate (%)", "Status"])

        # Proposed model
        p_met = evaluation_data.get("proposed_metrics", {})
        writer.writerow([
            evaluation_data.get("proposed_algorithm_name", "Proposed Architecture (Ours)"),
            evaluation_data.get("proposed_paradigm", "Multi-Modal Cross-Attention + DOM Gating"),
            p_met.get("accuracy", "N/A"),
            p_met.get("precision", "N/A"),
            p_met.get("recall", "N/A"),
            p_met.get("f1_score", "N/A"),
            p_met.get("false_positive_rate", "N/A"),
            "PROPOSED (OURS)"
        ])

        # Baseline models
        for b in evaluation_data.get("baseline_evaluations", []):
            b_met = b.get("metrics", {})
            writer.writerow([
                b.get("name", "N/A"),
                b.get("paradigm", "N/A"),
                b_met.get("accuracy", "N/A"),
                b_met.get("precision", "N/A"),
                b_met.get("recall", "N/A"),
                b_met.get("f1_score", "N/A"),
                b_met.get("false_positive_rate", "N/A"),
                "REPRODUCED BASELINE"
            ])
        writer.writerow([])

        # 3. Eight-Category Detection Analysis
        writer.writerow(["-----------------------------------------------------------------"])
        writer.writerow(["SECTION 2: EIGHT-CATEGORY DETECTION ANALYSIS (PROPOSED ALGORITHM)"])
        writer.writerow(["-----------------------------------------------------------------"])
        writer.writerow([
            "Category", "Status", "Total Evaluated", "Positive Ground Truth", "Negative Ground Truth",
            "True Positives (TP)", "False Positives (FP)", "True Negatives (TN)", "False Negatives (FN)",
            "Accuracy (%)", "Precision (%)", "Recall (%)", "F1-Score (%)"
        ])

        cat_breakdown = evaluation_data.get("category_breakdown", {})
        for cat, c_data in cat_breakdown.items():
            cm = c_data.get("confusion_matrix", {})
            writer.writerow([
                cat,
                c_data.get("status", "N/A"),
                c_data.get("support", 0),
                c_data.get("positive_ground_truth", 0),
                c_data.get("negative_ground_truth", 0),
                cm.get("true_positive", 0),
                cm.get("false_positive", 0),
                cm.get("true_negative", 0),
                cm.get("false_negative", 0),
                c_data.get("accuracy", "N/A"),
                c_data.get("precision", "N/A"),
                c_data.get("recall", "N/A"),
                c_data.get("f1_score", "N/A"),
            ])
        writer.writerow([])

        # 4. Literature Comparison
        writer.writerow(["-----------------------------------------------------------------"])
        writer.writerow(["SECTION 3: PUBLISHED RESEARCH BENCHMARKS (LITERATURE CONTEXT)"])
        writer.writerow(["-----------------------------------------------------------------"])
        writer.writerow([
            "Paper Title", "Authors", "Year", "DOI", "Model Architecture", "Dataset Used",
            "Reported Accuracy", "Reported Precision", "Reported Recall", "Reported F1", "Comparability Designation"
        ])
        for lit in PublishedLiteratureRepository.get_all_records():
            writer.writerow([
                lit.get("title", ""),
                lit.get("authors", ""),
                lit.get("year", ""),
                lit.get("doi", ""),
                lit.get("algorithm_or_model", ""),
                lit.get("dataset_name", ""),
                lit.get("reported_accuracy", "Not reported"),
                lit.get("reported_precision", "Not reported"),
                lit.get("reported_recall", "Not reported"),
                lit.get("reported_f1", "Not reported"),
                lit.get("comparability", ""),
            ])
        writer.writerow([])

        return output.getvalue()

    @staticmethod
    def generate_pdf(evaluation_data: Dict[str, Any]) -> bytes:
        """
        Generates a publication-grade academic PDF evaluation report using ReportLab.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e1b4b"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#312e81"),
            spaceBefore=14,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )
        table_text = ParagraphStyle(
            "TableText",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#0f172a")
        )
        table_header = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.white
        )

        elements = []

        # Document Header
        elements.append(Paragraph("Dark Pattern Compliance Auditing Framework", title_style))
        elements.append(Paragraph(
            "Empirical Algorithm Analysis & Comparative Evaluation Report<br/>"
            "<i>An Intelligent Automated Compliance Auditing Framework for Detecting and Verifying Dark Patterns on Indian E-Commerce Platforms</i>",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4f46e5"), spaceAfter=10))

        # Metadata Table
        meta_data = [
            [
                Paragraph("<b>Evaluation ID:</b>", table_text), Paragraph(str(evaluation_data.get("evaluation_id", "N/A")), table_text),
                Paragraph("<b>Evaluation Date:</b>", table_text), Paragraph(str(evaluation_data.get("created_at", "N/A")), table_text),
            ],
            [
                Paragraph("<b>Dataset:</b>", table_text), Paragraph(str(evaluation_data.get("dataset_name", "N/A")), table_text),
                Paragraph("<b>Dataset SHA-256:</b>", table_text), Paragraph(str(evaluation_data.get("dataset_hash", "N/A"))[:16] + "...", table_text),
            ],
            [
                Paragraph("<b>Split Protocol:</b>", table_text), Paragraph("Stratified 70/30 (Seed 42)", table_text),
                Paragraph("<b>Test Samples Evaluated:</b>", table_text), Paragraph(str(evaluation_data.get("test_sample_count", 0)), table_text),
            ]
        ]
        meta_table = Table(meta_data, colWidths=[100, 170, 110, 160])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # Section 1: Main Metric Summary Cards
        p_met = evaluation_data.get("proposed_metrics", {})
        elements.append(Paragraph("1. Primary Performance Metrics (Proposed Multi-Modal Architecture)", h2_style))

        cards_data = [
            [
                Paragraph("<b>ACCURACY</b>", table_header),
                Paragraph("<b>PRECISION</b>", table_header),
                Paragraph("<b>RECALL (DETECT RATE)</b>", table_header),
                Paragraph("<b>F1-SCORE</b>", table_header),
            ],
            [
                Paragraph(f"<font size=14><b>{p_met.get('accuracy', 'N/A')}%</b></font>", table_text),
                Paragraph(f"<font size=14><b>{p_met.get('precision', 'N/A')}%</b></font>", table_text),
                Paragraph(f"<font size=14><b>{p_met.get('recall', 'N/A')}%</b></font>", table_text),
                Paragraph(f"<font size=14><b>{p_met.get('f1_score', 'N/A')}%</b></font>", table_text),
            ],
            [
                Paragraph("Correct / All Evaluated", table_text),
                Paragraph("TP / (TP + FP)", table_text),
                Paragraph("TP / (TP + FN)", table_text),
                Paragraph("Harmonic Mean P & R", table_text),
            ]
        ]
        cards_table = Table(cards_data, colWidths=[135, 135, 135, 135])
        cards_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312e81")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eef2ff")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f8fafc")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#4f46e5")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(cards_table)
        elements.append(Spacer(1, 10))

        # Section 2: Algorithm Comparison Table (Proposed vs Baselines)
        elements.append(Paragraph("2. Comparative Benchmark (Proposed vs Reproduced Baselines on Identical Test Set)", h2_style))
        comp_rows = [
            [
                Paragraph("Algorithm Architecture", table_header),
                Paragraph("Paradigm", table_header),
                Paragraph("Accuracy", table_header),
                Paragraph("Precision", table_header),
                Paragraph("Recall", table_header),
                Paragraph("F1-Score", table_header),
                Paragraph("FP Rate", table_header),
            ],
            [
                Paragraph("<b>⭐ Proposed Architecture (Ours)</b>", table_text),
                Paragraph("Multi-Modal Cross-Attention + DOM Gating", table_text),
                Paragraph(f"{p_met.get('accuracy', 'N/A')}%", table_text),
                Paragraph(f"{p_met.get('precision', 'N/A')}%", table_text),
                Paragraph(f"{p_met.get('recall', 'N/A')}%", table_text),
                Paragraph(f"<b>{p_met.get('f1_score', 'N/A')}%</b>", table_text),
                Paragraph(f"{p_met.get('false_positive_rate', 'N/A')}%", table_text),
            ]
        ]

        for b in evaluation_data.get("baseline_evaluations", []):
            bm = b.get("metrics", {})
            comp_rows.append([
                Paragraph(b.get("name", "N/A"), table_text),
                Paragraph(b.get("paradigm", "N/A"), table_text),
                Paragraph(f"{bm.get('accuracy', 'N/A')}%", table_text),
                Paragraph(f"{bm.get('precision', 'N/A')}%", table_text),
                Paragraph(f"{bm.get('recall', 'N/A')}%", table_text),
                Paragraph(f"{bm.get('f1_score', 'N/A')}%", table_text),
                Paragraph(f"{bm.get('false_positive_rate', 'N/A')}%", table_text),
            ])

        comp_table = Table(comp_rows, colWidths=[150, 140, 50, 50, 50, 50, 50])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e1b4b")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ecfdf5")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(comp_table)
        elements.append(Spacer(1, 10))

        # Section 3: Eight-Category Breakdown
        elements.append(Paragraph("3. Category-Wise Performance Analysis (All 8 Dark-Pattern Categories)", h2_style))
        cat_rows = [
            [
                Paragraph("Dark Pattern Category", table_header),
                Paragraph("Status", table_header),
                Paragraph("Support", table_header),
                Paragraph("TP", table_header),
                Paragraph("FP", table_header),
                Paragraph("FN", table_header),
                Paragraph("Precision", table_header),
                Paragraph("Recall", table_header),
                Paragraph("F1-Score", table_header),
            ]
        ]
        cat_breakdown = evaluation_data.get("category_breakdown", {})
        for cat, c_data in cat_breakdown.items():
            cm = c_data.get("confusion_matrix", {})
            cat_rows.append([
                Paragraph(cat, table_text),
                Paragraph(c_data.get("status", "N/A"), table_text),
                Paragraph(str(c_data.get("support", 0)), table_text),
                Paragraph(str(cm.get("true_positive", 0)), table_text),
                Paragraph(str(cm.get("false_positive", 0)), table_text),
                Paragraph(str(cm.get("false_negative", 0)), table_text),
                Paragraph(f"{c_data.get('precision', 'N/A')}%" if c_data.get('precision') is not None else "N/A", table_text),
                Paragraph(f"{c_data.get('recall', 'N/A')}%" if c_data.get('recall') is not None else "N/A", table_text),
                Paragraph(f"<b>{c_data.get('f1_score', 'N/A')}%</b>" if c_data.get('f1_score') is not None else "N/A", table_text),
            ])

        cat_table = Table(cat_rows, colWidths=[130, 90, 45, 35, 35, 35, 55, 55, 60])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312e81")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(cat_table)
        elements.append(Spacer(1, 10))

        # Section 4: Literature Comparison
        elements.append(Paragraph("4. Published Academic Research Benchmarks (Literature Context)", h2_style))
        elements.append(Paragraph(
            "<i>Note: Literature metrics were reported on different corpora and tasks; they provide academic context rather than direct experimental equivalence.</i>",
            body_style
        ))
        elements.append(Spacer(1, 4))

        lit_rows = [
            [
                Paragraph("Paper & Citation", table_header),
                Paragraph("Model Paradigm", table_header),
                Paragraph("Reported F1", table_header),
                Paragraph("Reported Acc", table_header),
                Paragraph("Comparability & Scope", table_header),
            ]
        ]
        for lit in PublishedLiteratureRepository.get_all_records():
            citation_str = f"<b>{lit.get('authors', '').split(',')[0]} et al. ({lit.get('year', '')})</b><br/>{lit.get('title', '')[:45]}... (DOI: {lit.get('doi', '')})"
            lit_rows.append([
                Paragraph(citation_str, table_text),
                Paragraph(lit.get("algorithm_or_model", ""), table_text),
                Paragraph(lit.get("reported_f1", "Not reported"), table_text),
                Paragraph(lit.get("reported_accuracy", "Not reported"), table_text),
                Paragraph(f"<b>{lit.get('comparability', '')}</b><br/>{lit.get('comparability_reason', '')[:65]}...", table_text),
            ])

        lit_table = Table(lit_rows, colWidths=[150, 130, 60, 60, 140])
        lit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#475569")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(lit_table)

        # Build document
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
