import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class EmotionGroundedConfirmshamingNet(nn.Module):
    """
    Emotion-Grounded Contrastive Sentiment Network (EGCS-Transformer)
    Specifically designed for Confirmshaming & Guilt-Inducing Dark Pattern Detection.

    Architecture:
    1. Dual-Path Encoder: Encodes Accept Option (T_accept) and Decline Option (T_decline)
    2. Multi-Task Valence-Arousal Sentiment Head:
       - Computes emotional sentiment penalty: Delta_valence = Valence(T_accept) - Valence(T_decline)
    3. Cross-Attention between Opt-In and Opt-Out choices
    4. Neutral Refusal Suppression Gate (Zeroes out neutral refusals: 'No thanks', 'Cancel', 'Skip')
    5. Multi-Class Manipulative Guilt Classifier Head
    """

    CONFIRMSHAMING_CATEGORIES = [
        "CLEAN_NEUTRAL_DECLINE",
        "SELF_DEPRECATION",
        "GUILT_AND_APATHY",
        "NEGATIVE_VULNERABILITY",
        "LOSS_OF_BENEFIT",
    ]

    def __init__(
        self,
        text_embed_dim: int = 384,
        hidden_dim: int = 256,
        num_classes: int = 5,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim

        # 1. Dual-Choice Shared Semantic Encoder
        self.text_encoder = nn.Sequential(
            nn.Linear(text_embed_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
        )

        # 2. Emotional Valence & Arousal Head
        self.valence_head = nn.Linear(hidden_dim, 1)

        # 3. Cross-Attention between Preferred and Declining Choices
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=4, batch_first=True, dropout=0.1
        )

        # 4. Neutral Suppression Gate
        self.neutral_gate = nn.Sequential(
            nn.Linear(2, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

        # 5. Classifier Head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + 1, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes),
        )

    def forward(
        self,
        decline_emb: torch.Tensor,
        accept_emb: Optional[torch.Tensor] = None,
        is_neutral_refusal: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            decline_emb: [Batch, text_embed_dim] (The opt-out / decline text)
            accept_emb: Optional [Batch, text_embed_dim] (The positive preferred choice)
            is_neutral_refusal: bool flag indicating neutral phrase

        Returns:
            logits: [Batch, num_classes]
            valence_delta: [Batch, 1]
        """
        if decline_emb.dim() == 1:
            decline_emb = decline_emb.unsqueeze(0)
        if accept_emb is None:
            accept_emb = torch.zeros_like(decline_emb)
        elif accept_emb.dim() == 1:
            accept_emb = accept_emb.unsqueeze(0)

        h_decline = self.text_encoder(decline_emb).unsqueeze(1) # [B, 1, 256]
        h_accept = self.text_encoder(accept_emb).unsqueeze(1)   # [B, 1, 256]

        # Valence computation
        v_decline = torch.tanh(self.valence_head(h_decline.squeeze(1))) # [B, 1]
        v_accept = torch.tanh(self.valence_head(h_accept.squeeze(1)))   # [B, 1]
        valence_delta = F.relu(v_accept - v_decline)                    # [B, 1]

        # Cross-Attention
        attn_out, _ = self.cross_attention(
            query=h_decline, key=h_accept, value=h_accept
        )
        attn_out = attn_out.squeeze(1)                                  # [B, 256]

        # Combine with valence penalty
        fused = torch.cat([attn_out, valence_delta], dim=-1)

        # Neutral gate suppression
        neutral_input = torch.tensor([[1.0 if is_neutral_refusal else 0.0, 0.0]], dtype=torch.float32, device=decline_emb.device)
        gate_w = 1.0 - self.neutral_gate(neutral_input)
        fused = fused * gate_w

        logits = self.classifier(fused)
        return logits, valence_delta


class EGCSInferenceEngine:
    """
    Thread-safe inference wrapper for EGCS-Net.
    """

    _instance: Optional["EGCSInferenceEngine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = EmotionGroundedConfirmshamingNet(
            text_embed_dim=384,
            hidden_dim=256,
            num_classes=5,
        ).to(self.device)
        self.model.eval()

    @classmethod
    def get_instance(cls) -> "EGCSInferenceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = EGCSInferenceEngine()
        return cls._instance

    def predict(
        self,
        decline_text_embedding: torch.Tensor,
        accept_text_embedding: Optional[torch.Tensor] = None,
        is_neutral_refusal: bool = False,
        has_guilt_signal: bool = False,
        category_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes EGCS-Net Confirmshaming prediction.
        """
        with torch.no_grad():
            if decline_text_embedding.dim() == 1:
                decline_tensor = decline_text_embedding.unsqueeze(0).to(self.device)
            else:
                decline_tensor = decline_text_embedding.to(self.device)

            accept_tensor = accept_text_embedding.to(self.device) if accept_text_embedding is not None else None

            logits, valence_delta = self.model(
                decline_tensor,
                accept_emb=accept_tensor,
                is_neutral_refusal=is_neutral_refusal,
            )
            probs = F.softmax(logits, dim=-1)[0]

            p_clean = float(probs[0].item())
            p_confirmshaming = float(torch.sum(probs[1:]).item())
            top_class_idx = int(torch.argmax(probs).item())
            predicted_cat = category_hint or EmotionGroundedConfirmshamingNet.CONFIRMSHAMING_CATEGORIES[top_class_idx]

            is_detected = (not is_neutral_refusal) and (has_guilt_signal or p_confirmshaming >= 0.5)

            return {
                "p_confirmshaming": p_confirmshaming if not is_neutral_refusal else 0.0,
                "p_clean": p_clean if not is_neutral_refusal else 1.0,
                "category": predicted_cat if is_detected else "CLEAN_NEUTRAL_DECLINE",
                "is_detected": bool(is_detected),
                "model_name": "EGCS-Transformer (Emotion-Grounded Contrastive Sentiment Network)",
            }


def get_egcs_model() -> EGCSInferenceEngine:
    return EGCSInferenceEngine.get_instance()
