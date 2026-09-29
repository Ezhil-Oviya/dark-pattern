import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class ContextGatedForcedActionNet(nn.Module):
    """
    Context-Gated Prerequisite Disentanglement Network (CGPD-Net)
    Specifically designed for CCPA 2023 Compliant Forced Action Dark Pattern Detection.

    Architecture:
    1. Dual-Head NLP Disentangler:
       - Coercive Demand Sub-Network (Registration, App Download, Social Share)
       - Legitimate Utility Sub-Network (Shipping Address, Payment CVV, Terms & Conditions)
       - Net Coercive Vector: Delta = ReLU(h_coercive - h_legitimate)
    2. Visual Occlusion & Modal Barrier Stream (Full-page / Overlay Visual features: 512-d -> 256-d)
    3. Multi-Head Cross-Attention (Net Coercive Queries over Visual Barrier Keys/Values)
    4. CCPA Alternative-Path Gate: G_alt = 1 - Sigmoid(W_a [has_guest_option; has_close_button])
       (Enforces legal requirement: If voluntary alternative exists, violation is zeroed out)
    5. Multi-Label CCPA Category Classification Head
    """

    CCPA_CLASSES = [
        "CLEAN_VOLUNTARY",
        "FORCED_ACCOUNT_CREATION",
        "FORCED_APP_DOWNLOAD",
        "DATA_HARVESTING_WALL",
        "SOCIAL_RATING_WALL",
    ]

    def __init__(
        self,
        text_embed_dim: int = 384,
        visual_embed_dim: int = 512,
        context_dim: int = 4,
        hidden_dim: int = 256,
        num_classes: int = 5,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes

        # 1. Dual-Head Disentanglement Stream
        self.text_shared = nn.Sequential(
            nn.Linear(text_embed_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
        )
        self.coercive_head = nn.Linear(hidden_dim, hidden_dim)
        self.legitimate_head = nn.Linear(hidden_dim, hidden_dim)

        # 2. Visual Occlusion & Barrier Stream
        self.vis_proj = nn.Sequential(
            nn.Linear(visual_embed_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
        )

        # 3. Cross-Modal Attention
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=4, batch_first=True, dropout=0.1
        )

        # 4. Global CCPA Alternative-Path Gate
        self.alt_gate = nn.Sequential(
            nn.Linear(context_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

        # 5. Multi-Class / Multi-Label CCPA Classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes),
        )

    def forward(
        self,
        text_emb: torch.Tensor,
        vis_emb: torch.Tensor,
        context_features: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            text_emb: [Batch, text_embed_dim]
            vis_emb: [Batch, visual_embed_dim]
            context_features: [Batch, context_dim] (has_guest, has_skip, is_dismissible, is_blocking_modal)

        Returns:
            logits: [Batch, num_classes]
            gate_weight: [Batch, 1]
            attn_weights: [Batch, 1, 1]
        """
        if text_emb.dim() == 1:
            text_emb = text_emb.unsqueeze(0)
        if vis_emb.dim() == 1:
            vis_emb = vis_emb.unsqueeze(0)
        if context_features.dim() == 1:
            context_features = context_features.unsqueeze(0)

        # 1. Disentangle Text Intent
        shared = self.text_shared(text_emb)
        h_coercive = F.relu(self.coercive_head(shared))
        h_legitimate = F.relu(self.legitimate_head(shared))
        # Net coercive force cancels out standard shipping/payment fields
        net_coercive = F.relu(h_coercive - h_legitimate).unsqueeze(1)  # [B, 1, 256]

        # 2. Visual Occlusion Projection
        h_vis = self.vis_proj(vis_emb).unsqueeze(1)                    # [B, 1, 256]

        # 3. Cross-Attention
        attn_out, attn_weights = self.cross_attention(
            query=net_coercive, key=h_vis, value=h_vis
        )
        attn_out = attn_out.squeeze(1)                                  # [B, 256]

        # 4. CCPA Alternative-Path Gating
        # If guest option or skip button is present, gate_activation -> 1.0, so (1 - gate) -> 0.0
        gate_activation = self.alt_gate(context_features)
        gate_weight = 1.0 - gate_activation                            # [B, 1]
        gated_fused = attn_out * gate_weight

        # 5. Logits
        logits = self.classifier(gated_fused)
        return logits, gate_weight, attn_weights


class CGPDInferenceEngine:
    """
    Thread-safe inference wrapper for CGPD-Net.
    Executes CCPA 2023 compliant Forced Action classification.
    """

    _instance: Optional["CGPDInferenceEngine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ContextGatedForcedActionNet(
            text_embed_dim=384,
            visual_embed_dim=512,
            context_dim=4,
            hidden_dim=256,
            num_classes=5,
        ).to(self.device)
        self.model.eval()

    @classmethod
    def get_instance(cls) -> "CGPDInferenceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = CGPDInferenceEngine()
        return cls._instance

    def predict(
        self,
        text_embedding: torch.Tensor,
        has_guest_alternative: bool,
        is_dismissible: bool,
        is_modal_overlay: bool = False,
        is_legitimate_prerequisite: bool = False,
        visual_features: Optional[torch.Tensor] = None,
    ) -> Dict[str, Any]:
        """
        Executes CCPA-compliant Forced Action prediction.
        """
        with torch.no_grad():
            if text_embedding.dim() == 1:
                text_tensor = text_embedding.unsqueeze(0).to(self.device)
            else:
                text_tensor = text_embedding.to(self.device)

            if visual_features is not None:
                vis_tensor = visual_features.to(self.device)
            else:
                vis_prior = torch.zeros((1, 512), device=self.device)
                if is_modal_overlay:
                    vis_prior[:, :256] = 1.0  # modal barrier signature
                if not is_dismissible:
                    vis_prior[:, 256:] = 0.8  # trapped / no-close signature
                vis_tensor = vis_prior

            # Context features: [has_guest_alt, is_dismissible, is_modal, is_legit]
            ctx_vec = torch.tensor(
                [
                    [
                        1.0 if has_guest_alternative else 0.0,
                        1.0 if is_dismissible else 0.0,
                        1.0 if is_modal_overlay else 0.0,
                        1.0 if is_legitimate_prerequisite else 0.0,
                    ]
                ],
                dtype=torch.float32,
                device=self.device,
            )

            logits, gate_weight, attn_weights = self.model(text_tensor, vis_tensor, ctx_vec)
            probs = F.softmax(logits, dim=-1)[0]
            
            p_clean = float(probs[0].item())
            # Sum of violation probabilities
            p_forced = float(torch.sum(probs[1:]).item())
            top_class_idx = int(torch.argmax(probs).item())
            predicted_category = ContextGatedForcedActionNet.CCPA_CLASSES[top_class_idx]

            # If guest alternative exists, CCPA dictates it is not forced action
            is_detected = (not has_guest_alternative) and (not is_dismissible) and (not is_legitimate_prerequisite) and (p_forced >= 0.5)

            return {
                "p_forced_action": p_forced,
                "p_clean": p_clean,
                "ccpa_category": predicted_category if is_detected else "CLEAN_VOLUNTARY",
                "gate_weight": float(gate_weight[0, 0].item()),
                "is_detected": bool(is_detected),
                "model_name": "CGPD-Net (Context-Gated Prerequisite Disentanglement Network)",
                "legal_framework": "CCPA Guidelines 2023 (Section 4 - Forced Action)",
            }


def get_cgpd_model() -> CGPDInferenceEngine:
    return CGPDInferenceEngine.get_instance()
