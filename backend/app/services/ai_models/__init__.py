"""
AI Deep Learning Models for Dark Pattern Detection.
Includes:
- SACM-Net: State-Aware Cross-Modal Fusion Network for Basket Sneaking
- CGPD-Net: Context-Gated Prerequisite Disentanglement Network for Forced Action
"""
from app.services.ai_models.sacm_net import StateAwareBasketSneakingNet, get_sacm_model
from app.services.ai_models.cgpd_net import ContextGatedForcedActionNet, get_cgpd_model

__all__ = [
    "StateAwareBasketSneakingNet",
    "get_sacm_model",
    "ContextGatedForcedActionNet",
    "get_cgpd_model",
]
