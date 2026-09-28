# Hybrid Dark Pattern Detection Architecture (Module 5)

## Overview & Background

The **Dark Pattern Compliance Auditor / Intelligent Automated Compliance Auditing Framework** employs a **Hybrid Detection Architecture** designed for explainability, high precision, local reproducibility, and zero external paid API dependencies.

- **Review II Implementation**:
  - Deterministic syntactic rule-based detectors for **False Urgency** and **Confirmshaming** using regular expressions, countdown timer tokens, and structured linguistic guilt categories.
  - These Review II detectors remain 100% rule-based and have been preserved unchanged.

- **Final Review Implementation**:
  - AI-assisted semantic classification layer for **Forced Action** and **Basket Sneaking**.
  - Upgraded to utilize a **genuine pretrained NLP Sentence Transformer** (`sentence-transformers/all-MiniLM-L6-v2`) to derive dense vector embeddings and evaluate semantic similarity against project-curated category reference prototypes, followed by multi-stage deterministic DOM and evidence validation.

---

## 1. Architectural Blueprint

```
                     +---------------------------------------+
                     |         M3 / M4 Evidence Record       |
                     |  (DOM Elements, Metrics, Screenshots) |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |         Candidate Extraction          |
                     |  (Targeted Subsets, Not Entire DOM)   |
                     +---------------------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
         +-----------------------+               +-------------------------------+
         |   Rule-Based Layer    |               |    Pretrained Transformer     |
         | (Regex & Heuristics)  |               |  (all-MiniLM-L6-v2 Embeddings)|
         +-----------------------+               +-------------------------------+
             |               |                               |
             v               v                               v
       False Urgency   Confirmshaming              Semantic Similarity &
                                                     Contrast Margin
                                                             |
                                                             v
                                              +------------------------------+
                                              | DOM & Evidence Deterministic |
                                              |       Validation Layer       |
                                              +------------------------------+
                                                             |
                                             +---------------+---------------+
                                             |                               |
                                             v                               v
                                       Forced Action                  Basket Sneaking
                                             |                               |
                                             +---------------+---------------+
                                                             |
                                                             v
                                              +------------------------------+
                                              |   Standard DetectionFinding  |
                                              |  (DETECTED / NOT_DETECTED /  |
                                              |    INSUFFICIENT_EVIDENCE)    |
                                              +------------------------------+
```

---

## 2. Rule-Based vs. Transformer + DOM Validation Layer

| Dimension | Rule-Based Layer (Review II) | Transformer + DOM Validation Layer (Final Review) |
| :--- | :--- | :--- |
| **Patterns Handled** | False Urgency, Confirmshaming | Forced Action, Basket Sneaking |
| **Technology** | Regular expressions, keyword ensembles, linguistic pattern matching | `sentence-transformers/all-MiniLM-L6-v2` (384-d dense embeddings) + Cosine Similarity + Deterministic DOM Validation |
| **Training Status** | Handcrafted deterministic rule engine | **Pretrained base transformer** (the project does NOT claim to train or fine-tune BERT on small data) |
| **Role of NLP** | None | Understands dense semantic intent of candidate phrasing relative to prototype concepts |
| **Role of DOM Validation** | Direct property checks | Verifies physical interaction state (e.g., preselected checkboxes, lack of guest alternative, dismissible overlays) |
| **Finding Schema** | `pattern`, `status`, `detected`, `confidence`, `reason`, `evidence` | `pattern`, `status`, `detected`, `model_score` (semantic similarity float), `validation_status` ("PASSED"/"FAILED"), `confidence` (DOM validation integer), `reason`, `evidence` |

---

## 3. Candidate Extraction (Selective DOM Processing)

To prevent latency and avoid feeding entire raw HTML documents to the transformer, `candidate_extractor.py` extracts only targeted candidate elements:

- **Forced Action Candidates**:
  - Modals & dialog overlays (`modals`)
  - Required checkboxes (`checkboxes[required=True]`)
  - Gating buttons and navigation links
  - Page-level alternative pathway indicators (`Continue as guest`, `Skip`, `Dismiss`)

- **Basket Sneaking Candidates**:
  - Checkboxes and toggles (`checkboxes`, `inputs[type=checkbox]`)
  - Cart items and unsolicited items (`cart_items`, `cart_interaction`)
  - Add-ons, protection plans, extended warranties, donations, and recurring subscriptions

---

## 4. Forced Action Methodology

### Detection Flow
1. **Candidate Extraction**: Identifies interactive gating modals, required inputs, and blocking barriers.
2. **Transformer Semantic Scoring**:
   - `PatternSemanticClassifier.classify_forced_action(text, context)` encodes candidate text into a 384-dimensional dense vector using `all-MiniLM-L6-v2`.
   - Computes cosine similarity $S_{pos}$ against coercive gating reference prototypes (e.g., *"Create an account to continue reading"*, *"Download our app to continue"*, *"Subscribe before accessing"*) and $S_{benign}$ against benign/voluntary interaction prototypes (*"Continue as guest"*, *"Terms & Conditions"*, *"Shipping address"*).
   - Derives `model_score` from $S_{pos}$ and the semantic contrast margin $\Delta = S_{pos} - S_{benign}$.
3. **Deterministic DOM & Context Validation**:
   - **Alternative Path Verification**: Checks if a guest alternative (`Continue as guest`, `Skip`) is available. If present, validation flags the interaction as voluntary (`NOT_DETECTED`).
   - **Prerequisite Legitimacy**: Validates that required inputs are not standard legal agreements (Terms/Privacy) or logistics/payment fields (Shipping address, CVV).
   - **Overlay Dismissibility**: Checks if modal dialogs have functional close buttons.
4. **Outcome**:
   - `DETECTED`: Coercive gating semantics ($\text{model\_score} \ge 0.70$) + DOM validation PASSED (no alternative path, not dismissible).
   - `NOT_DETECTED`: Voluntary guest alternative available, or element is standard legitimate checkout field.
   - `INSUFFICIENT_EVIDENCE`: Neutral authentication buttons (`Log In`, `Create an account`) without coercive gating.

---

## 5. Basket Sneaking Methodology

### Detection Flow
1. **Candidate Extraction**: Extracts checkboxes, cart items, and price-bearing components.
2. **Transformer Semantic Scoring**:
   - `PatternSemanticClassifier.classify_basket_sneaking(text, context)` encodes candidate text into a 384-dimensional dense vector.
   - Computes cosine similarity against commercial add-on prototypes (*extended warranty*, *accidental damage protection*, *VIP membership*, *donation*, *gift wrap*, *driver tip*) vs. benign line items (*Terms & Conditions*, *GST / sales tax*, *standard ground shipping*, *remember me*).
   - Produces `model_score` reflecting whether the item represents an optional commercial add-on.
3. **Deterministic DOM State Validation**:
   - Inspects physical selection state:
     - `is_checked == True`: Preselected by default -> DOM validation PASSED -> `DETECTED`.
     - `is_checked == False`: Offered cleanly in unchecked state -> DOM validation FAILED -> `NOT_DETECTED` (clean cart).
     - `is_checked is None`: Inconclusive selection attribute -> `INSUFFICIENT_EVIDENCE`.
4. **Outcome**:
   - `DETECTED`: Optional add-on semantics + Preselected/checked in DOM.
   - `NOT_DETECTED`: Add-on is unchecked (voluntary choice), or cart contains only standard transparent fees.
   - `INSUFFICIENT_EVIDENCE`: Add-on text detected but DOM selection state cannot be conclusively determined.

---

## 6. Pretrained NLP Model Specification

- **Model Identifier**: `sentence-transformers/all-MiniLM-L6-v2`
- **Model Architecture**: 6-layer MiniLM transformer with 384-dimensional output embeddings, mean pooling, and cosine similarity metric.
- **Framework / Libraries**: `sentence-transformers`, `torch`, `transformers`.
- **Pretrained vs. Fine-Tuned**:
  - The model is **pretrained** by the open-source community on over 1 billion sentence pairs.
  - The project **does not claim to fine-tune or train the base language model** on the 38 project samples.
  - Instead, the 38 project samples serve as prototype reference concepts and evaluation test cases.
- **Local & Offline Execution**:
  - Runs fully locally using cached weights in Hugging Face Hub cache.
  - Zero external paid APIs, zero data sent to third-party servers.
- **Singleton Lifecycle**:
  - Loaded once via `PatternSemanticClassifier.get_instance()`.
  - Prototype embeddings are precomputed once on startup and reused across all pages and audits.
- **Fault-Tolerant Fallback**:
  - If the model cannot be loaded (e.g. environment missing dependencies), the classifier logs a warning and returns safe fallback values without crashing the complete compliance audit.
  - Rule-based detectors (False Urgency, Confirmshaming) continue uninterrupted.

---

## 7. Disclaimers & Statistical Limitations

1. **Cosine Similarity vs. Statistical Probability**:
   - `model_score` is a dense semantic cosine similarity float ($0.0 - 1.0$) relative to category reference prototypes.
   - It is **not** a population-calibrated Bayesian or frequentist probability. Terminology such as "calibrated probability" is explicitly avoided.
2. **Confidence Metric**:
   - `final_confidence` is an evidence-backed integer ($0 - 100$) reflecting deterministic DOM validation and structural corroboration (e.g., presence of price, preselection state, unsolicited insertion).
3. **Evaluation Scope**:
   - The project benchmark dataset (`dark_patterns_benchmark.json`) contains 38 curated e-commerce compliance samples (20 Forced Action, 18 Basket Sneaking).
   - Evaluation demonstrates functional verification and behavioral alignment on curated scenarios rather than broad statistical generalization across the entire web.
