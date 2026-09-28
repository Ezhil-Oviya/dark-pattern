import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing sentence_transformers and torch safely
_TRANSFORMER_AVAILABLE = False
try:
    import torch
    from sentence_transformers import SentenceTransformer, util
    _TRANSFORMER_AVAILABLE = True
except ImportError:
    logger.warning("[AI] sentence-transformers or torch not installed. Semantic classifier will operate in fallback mode.")


class BaseAIClassifier(ABC):
    """Abstract interface for AI/NLP semantic pattern classifiers."""

    @abstractmethod
    def classify_forced_action(
        self,
        candidate_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Classifies whether candidate text exhibits Forced Action coercive intent.
        Returns: (model_score: float [0.0 - 1.0], metadata: Dict)
        Note: model_score represents semantic similarity derived from the pretrained
        embedding model and is not a calibrated statistical probability.
        """
        pass

    @abstractmethod
    def classify_basket_sneaking(
        self,
        candidate_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Classifies whether candidate text denotes an optional paid add-on / warranty / insurance / service.
        Returns: (model_score: float [0.0 - 1.0], metadata: Dict)
        Note: model_score represents semantic similarity derived from the pretrained
        embedding model and is not a calibrated statistical probability.
        """
        pass


class PatternSemanticClassifier(BaseAIClassifier):
    """
    Pretrained Transformer-Based Semantic Classifier for Dark Pattern Detection.

    Architecture & Model Specification:
    - Base Model: sentence-transformers/all-MiniLM-L6-v2 (Pretrained Sentence Transformer, 384-d dense vectors)
    - Approach: Prototype-based semantic similarity using normalized vector embeddings and cosine distance.
    - Category Prototypes: Project-curated reference concepts for coercive gating and commercial add-ons vs. benign elements.
    - Offline / Local: Runs entirely locally using cached weights without external paid cloud APIs.
    - Lifecycle: Thread-safe singleton with prototype embeddings computed once at startup.
    - Statistical Note: model_score represents dense semantic cosine similarity / contrast margin
      against category prototypes and is not a population-calibrated probability.
    """

    _instance: Optional["PatternSemanticClassifier"] = None
    _lock = threading.Lock()

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    # Reference prototypes for Forced Action: Coercive gating vs. Benign / Voluntary interactions
    FORCED_ACTION_POSITIVE_PROTOTYPES = [
        {"concept": "coercive_account_gating", "text": "Create an account to continue reading this article and access full research"},
        {"concept": "coercive_account_gating", "text": "Please sign up or register to continue reading and view content"},
        {"concept": "coercive_account_gating", "text": "Sign up or register before continuing to checkout or access dashboard"},
        {"concept": "coercive_account_gating", "text": "Register your account to access search results"},
        {"concept": "forced_app_download", "text": "Download our mobile app to continue viewing prices or discounts"},
        {"concept": "forced_subscription_gate", "text": "Subscribe to our premium service before accessing the requested file or feature"},
        {"concept": "forced_notification_optin", "text": "Enable browser push notifications to proceed to the download page"},
        {"concept": "social_sharing_wall", "text": "Share this website on social media like Facebook or Twitter to unlock coupon code"},
        {"concept": "forced_rating_gate", "text": "Rate our application 5 stars to continue using free features"},
        {"concept": "unrelated_data_harvesting", "text": "Enter your personal phone number, annual income, or employer name to download"},
        {"concept": "forced_promotional_consent", "text": "I agree to receive promotional marketing emails, partner ads, and daily SMS offers"},
        {"concept": "mandatory_coercive_gate", "text": "Mandatory registration or subscription required before proceeding"},
    ]

    FORCED_ACTION_BENIGN_PROTOTYPES = [
        {"concept": "guest_alternative", "text": "Continue as guest without creating an account"},
        {"concept": "guest_alternative", "text": "Guest checkout alternative available"},
        {"concept": "explicitly_optional", "text": "Account registration is optional and voluntary"},
        {"concept": "explicitly_optional", "text": "You may optionally create an account to save your purchase history"},
        {"concept": "login_convenience", "text": "Login to save your personal preferences"},
        {"concept": "legitimate_terms", "text": "I accept the Terms and Conditions and Privacy Policy"},
        {"concept": "legitimate_shipping", "text": "Shipping Address: Full Name, Street, City, Postal Code"},
        {"concept": "legitimate_payment", "text": "Credit Card Number, Expiration Date, CVV Code"},
        {"concept": "dismissible_skip", "text": "Skip this step and proceed directly to dashboard"},
        {"concept": "standard_login", "text": "Sign In with Google, Apple ID, or Email"},
        {"concept": "standard_login_button", "text": "Log In button"},
    ]

    # Reference prototypes for Basket Sneaking: Optional paid add-ons vs. Benign line items / consent
    BASKET_SNEAKING_POSITIVE_PROTOTYPES = [
        {"concept": "device_protection_plan", "text": "Add 2-Year Accidental Damage Protection Plan or device care protection"},
        {"concept": "extended_warranty", "text": "Extended Warranty Care Pack for 3 Years"},
        {"concept": "recurring_subscription_addon", "text": "VIP Club Membership (Auto-renews at ₹299/mo) and express delivery protection"},
        {"concept": "delivery_theft_insurance", "text": "Include package loss, damage, and theft shipping insurance surcharge"},
        {"concept": "charitable_donation_addon", "text": "Donate to Green Earth Foundation or charity with this order"},
        {"concept": "charitable_donation_addon", "text": "Add optional donation or charity contribution to child care or foundation"},
        {"concept": "gift_wrapping_addon", "text": "Add premium gift wrapping and custom greeting card"},
        {"concept": "priority_handling_surcharge", "text": "Priority order processing and rush express handling fee"},
        {"concept": "commercial_addon_product", "text": "Add screen cleaning kit, tempered glass, or accessory bundle to cart"},
        {"concept": "unsolicited_gratuity_addon", "text": "Add driver tip or delivery partner gratuity"},
        {"concept": "device_protection_plan", "text": "Device Protection Plan covering accidental liquid damage and theft"},
        {"concept": "commercial_addon_product", "text": "Unsolicited paid add-on, protection plan, insurance, or membership item"},
    ]

    BASKET_SNEAKING_BENIGN_PROTOTYPES = [
        {"concept": "mandatory_legal_terms", "text": "I agree to the Terms of Service and Privacy Policy"},
        {"concept": "session_persistence_toggle", "text": "Remember me / Keep me signed in on this computer"},
        {"concept": "government_tax_line_item", "text": "Goods and Services Tax (GST 18%) / Sales Tax line item"},
        {"concept": "standard_logistics_fee", "text": "Standard ground shipping delivery logistics fee"},
        {"concept": "form_convenience_toggle", "text": "Billing address is the same as shipping address"},
        {"concept": "product_recommendation", "text": "Customers who bought this item also bought / Recommended products carousel"},
        {"concept": "legitimate_payment_field", "text": "Required credit card payment method and billing details"},
    ]

    def __init__(self):
        logger.info(f"[AI] Initializing PatternSemanticClassifier with pretrained model: {self.MODEL_NAME}...")
        self.model_name = self.MODEL_NAME
        self.model_type = "pretrained_sentence_transformer"
        self._model: Optional[Any] = None
        self._is_ready = False

        # Precomputed prototype embeddings
        self._emb_fa_pos: Optional[Any] = None
        self._emb_fa_benign: Optional[Any] = None
        self._emb_bs_pos: Optional[Any] = None
        self._emb_bs_benign: Optional[Any] = None

        self._load_model_and_prototypes()

    def _load_model_and_prototypes(self):
        """Loads the SentenceTransformer and pre-computes normalized prototype embeddings."""
        if not _TRANSFORMER_AVAILABLE:
            logger.warning("[AI] Transformers libraries unavailable. Running in fallback mode.")
            return

        try:
            # Load pretrained model from local cache
            self._model = SentenceTransformer(self.MODEL_NAME)

            # Precompute prototype embeddings (normalized for cosine similarity)
            fa_pos_texts = [p["text"] for p in self.FORCED_ACTION_POSITIVE_PROTOTYPES]
            fa_benign_texts = [p["text"] for p in self.FORCED_ACTION_BENIGN_PROTOTYPES]
            bs_pos_texts = [p["text"] for p in self.BASKET_SNEAKING_POSITIVE_PROTOTYPES]
            bs_benign_texts = [p["text"] for p in self.BASKET_SNEAKING_BENIGN_PROTOTYPES]

            self._emb_fa_pos = self._model.encode(fa_pos_texts, convert_to_tensor=True, normalize_embeddings=True)
            self._emb_fa_benign = self._model.encode(fa_benign_texts, convert_to_tensor=True, normalize_embeddings=True)

            self._emb_bs_pos = self._model.encode(bs_pos_texts, convert_to_tensor=True, normalize_embeddings=True)
            self._emb_bs_benign = self._model.encode(bs_benign_texts, convert_to_tensor=True, normalize_embeddings=True)

            self._is_ready = True
            logger.info(f"[AI] Pretrained Sentence Transformer ({self.MODEL_NAME}) and prototype embeddings loaded successfully.")
        except Exception as e:
            logger.error(f"[AI] Failed to load SentenceTransformer model ({self.MODEL_NAME}): {e}", exc_info=True)
            self._is_ready = False

    @classmethod
    def get_instance(cls) -> "PatternSemanticClassifier":
        """Thread-safe singleton getter."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = PatternSemanticClassifier()
        return cls._instance

    def classify_forced_action(
        self,
        candidate_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Classifies Forced Action semantic intent using pretrained transformer embeddings.
        Compares candidate embedding against coercive gating prototypes vs. benign interaction prototypes.
        """
        if not candidate_text or not candidate_text.strip():
            return 0.0, {"signals": [], "model": self.model_name, "status": "empty_input"}

        if not self._is_ready or self._model is None:
            logger.warning("[AI] SentenceTransformer not ready. Returning safe fallback score.")
            return 0.0, {"signals": [], "model": self.model_name, "status": "model_unavailable"}

        try:
            cleaned_text = candidate_text.strip()
            emb_cand = self._model.encode(cleaned_text, convert_to_tensor=True, normalize_embeddings=True)

            # Cosine similarity against positive (coercive) and benign prototypes
            sim_pos_vec = util.cos_sim(emb_cand, self._emb_fa_pos)[0]
            sim_benign_vec = util.cos_sim(emb_cand, self._emb_fa_benign)[0]

            max_pos_idx = int(torch.argmax(sim_pos_vec))
            max_benign_idx = int(torch.argmax(sim_benign_vec))

            s_pos = float(sim_pos_vec[max_pos_idx])
            s_benign = float(sim_benign_vec[max_benign_idx])
            margin = s_pos - s_benign

            matched_positive_concept = self.FORCED_ACTION_POSITIVE_PROTOTYPES[max_pos_idx]["concept"]
            matched_benign_concept = self.FORCED_ACTION_BENIGN_PROTOTYPES[max_benign_idx]["concept"]

            # Derive semantic score from embedding similarity and contrast margin
            if margin >= 0.05 and s_pos >= 0.40:
                # Strong semantic alignment with coercive gating concepts
                model_score = max(0.72, min(0.98, s_pos + max(0.0, margin * 0.3)))
            elif margin >= -0.05 and s_pos >= 0.40:
                # Moderate alignment with coercive intent
                model_score = max(0.40, min(0.69, s_pos * 0.85))
            elif s_pos >= 0.35 and margin < -0.05:
                # Closer to benign concepts (e.g., terms, guest alternative, optional)
                model_score = max(0.05, min(0.25, s_pos * 0.3))
            else:
                model_score = max(0.0, s_pos * 0.2)

            # Contextual adjustments
            if context:
                if context.get("has_alternative") or context.get("guest_option_present"):
                    model_score = min(model_score, 0.15)
                if context.get("is_dismissible"):
                    model_score = max(0.0, model_score - 0.25)

            model_score = round(float(model_score), 2)
            signals = [matched_positive_concept] if model_score >= 0.40 else []

            return model_score, {
                "signals": signals,
                "positive_similarity": round(s_pos, 3),
                "benign_similarity": round(s_benign, 3),
                "semantic_margin": round(margin, 3),
                "matched_concept": matched_positive_concept,
                "matched_benign_concept": matched_benign_concept,
                "model": self.model_name,
                "representation": "dense_sentence_embedding",
            }
        except Exception as e:
            logger.error(f"[AI] Error during Forced Action embedding classification: {e}", exc_info=True)
            return 0.0, {"signals": [], "model": self.model_name, "error": str(e)}

    def classify_basket_sneaking(
        self,
        candidate_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Classifies Basket Sneaking add-on semantic intent using pretrained transformer embeddings.
        Compares candidate embedding against commercial add-on prototypes vs. benign cart/terms prototypes.
        """
        if not candidate_text or not candidate_text.strip():
            return 0.0, {"signals": [], "model": self.model_name, "status": "empty_input"}

        if not self._is_ready or self._model is None:
            logger.warning("[AI] SentenceTransformer not ready. Returning safe fallback score.")
            return 0.0, {"signals": [], "model": self.model_name, "status": "model_unavailable"}

        try:
            cleaned_text = candidate_text.strip()
            emb_cand = self._model.encode(cleaned_text, convert_to_tensor=True, normalize_embeddings=True)

            # Cosine similarity against positive (add-on) and benign prototypes
            sim_pos_vec = util.cos_sim(emb_cand, self._emb_bs_pos)[0]
            sim_benign_vec = util.cos_sim(emb_cand, self._emb_bs_benign)[0]

            max_pos_idx = int(torch.argmax(sim_pos_vec))
            max_benign_idx = int(torch.argmax(sim_benign_vec))

            s_pos = float(sim_pos_vec[max_pos_idx])
            s_benign = float(sim_benign_vec[max_benign_idx])
            margin = s_pos - s_benign

            matched_positive_concept = self.BASKET_SNEAKING_POSITIVE_PROTOTYPES[max_pos_idx]["concept"]
            matched_benign_concept = self.BASKET_SNEAKING_BENIGN_PROTOTYPES[max_benign_idx]["concept"]

            # Derive semantic score from embedding similarity and contrast margin
            if margin >= 0.05 and s_pos >= 0.40:
                # Strong semantic alignment with commercial add-on / warranty / insurance / donation
                model_score = max(0.75, min(0.98, s_pos + max(0.0, margin * 0.3)))
            elif margin >= -0.05 and s_pos >= 0.35:
                model_score = max(0.40, min(0.69, s_pos * 0.85))
            elif s_pos >= 0.35 and margin < -0.05:
                # Closer to benign (e.g. Terms, GST, shipping, session)
                model_score = max(0.05, min(0.25, s_pos * 0.3))
            else:
                model_score = max(0.0, s_pos * 0.2)

            model_score = round(float(model_score), 2)
            signals = [matched_positive_concept] if model_score >= 0.40 else []

            return model_score, {
                "signals": signals,
                "signals_matched": [matched_positive_concept],
                "positive_similarity": round(s_pos, 3),
                "benign_similarity": round(s_benign, 3),
                "semantic_margin": round(margin, 3),
                "matched_concept": matched_positive_concept,
                "matched_benign_concept": matched_benign_concept,
                "model": self.model_name,
                "representation": "dense_sentence_embedding",
            }
        except Exception as e:
            logger.error(f"[AI] Error during Basket Sneaking embedding classification: {e}", exc_info=True)
            return 0.0, {"signals": [], "model": self.model_name, "error": str(e)}


def get_ai_classifier() -> BaseAIClassifier:
    """Factory function returning the singleton AI classifier."""
    return PatternSemanticClassifier.get_instance()
