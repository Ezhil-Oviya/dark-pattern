"""
AI Deep Learning Models for Dark Pattern Detection.
Includes:
- SACM-Net: State-Aware Cross-Modal Fusion Network (Basket Sneaking)
- CGPD-Net: Context-Gated Prerequisite Disentanglement Network (Forced Action)
- TRSA-Net: Temporal-Recurrent Scarcity Authenticity Network (False Urgency)
- EGCS-Transformer: Emotion-Grounded Contrastive Sentiment Network (Confirmshaming)
"""
from app.services.ai_models.sacm_net import StateAwareBasketSneakingNet, get_sacm_model
from app.services.ai_models.cgpd_net import ContextGatedForcedActionNet, get_cgpd_model
from app.services.ai_models.trsa_net import TemporalScarcityNet, get_trsa_model
from app.services.ai_models.egcs_net import EmotionGroundedConfirmshamingNet, get_egcs_model

__all__ = [
    "StateAwareBasketSneakingNet",
    "get_sacm_model",
    "ContextGatedForcedActionNet",
    "get_cgpd_model",
    "TemporalScarcityNet",
    "get_trsa_model",
    "EmotionGroundedConfirmshamingNet",
    "get_egcs_model",
]
