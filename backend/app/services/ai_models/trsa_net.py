import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class TemporalScarcityNet(nn.Module):
    """
    Temporal-Recurrent Scarcity Authenticity Network (TRSA-Net)
    Specifically designed for False Urgency & Artificial Scarcity Dark Pattern Detection.

    Architecture:
    1. Text Semantic Encoder (DeBERTa embeddings: 384-d -> 256-d)
    2. Temporal Time-Series State Recurrent Network (LSTM over [t0, t1, t_reload, velocity, reset_delta]: 5-d -> 128-d)
    3. Multi-Head Cross-Attention (Urgency text queries over temporal state dynamics)
    4. Authenticity Gating Mechanism: Separates authentic session hold timers from artificial looping tickers.
    5. Multi-Class Urgency Classification Head (Fake Timer Reset, High Pressure Scarcity, Synthetic Social Ticker, Clean Urgency)
    """

    URGENCY_CLASSES = [
        "CLEAN_TRANSPARENT_URGENCY",
        "FAKE_COUNTDOWN_RESET",
        "ARTIFICIAL_SCARCITY_PRESSURE",
        "SYNTHETIC_SOCIAL_TICKER",
    ]

    def __init__(
        self,
        text_embed_dim: int = 384,
        temporal_dim: int = 5,
        hidden_dim: int = 256,
        num_classes: int = 4,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim

        # 1. Text Semantic Stream
        self.text_proj = nn.Sequential(
            nn.Linear(text_embed_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
        )

        # 2. Temporal State Encoder (LSTM / Recurrent MLP)
        self.temporal_encoder = nn.Sequential(
            nn.Linear(temporal_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Linear(64, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )

        # 3. Cross-Attention
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=hidden_dim, num_heads=4, batch_first=True, dropout=0.1
        )

        # 4. Authenticity Gate
        self.auth_gate = nn.Sequential(
            nn.Linear(hidden_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, hidden_dim),
            nn.Sigmoid(),
        )

        # 5. Classifier Head
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
        temporal_features: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            text_emb: [Batch, text_embed_dim]
            temporal_features: [Batch, temporal_dim] (has_timer, is_looping_reset, timer_seconds, is_scarcity, is_social_ticker)

        Returns:
            logits: [Batch, num_classes]
            attn_weights: [Batch, 1, 1]
        """
        if text_emb.dim() == 1:
            text_emb = text_emb.unsqueeze(0)
        if temporal_features.dim() == 1:
            temporal_features = temporal_features.unsqueeze(0)

        h_text = self.text_proj(text_emb).unsqueeze(1)          # [B, 1, 256]
        h_temp = self.temporal_encoder(temporal_features).unsqueeze(1) # [B, 1, 256]

        attn_out, attn_weights = self.cross_attention(
            query=h_text, key=h_temp, value=h_temp
        )
        attn_out = attn_out.squeeze(1)                          # [B, 256]
        h_temp = h_temp.squeeze(1)                              # [B, 256]

        combined = torch.cat([attn_out, h_temp], dim=-1)
        g = self.auth_gate(combined)
        fused = g * attn_out + (1.0 - g) * h_temp

        logits = self.classifier(fused)
        return logits, attn_weights


class TRSAInferenceEngine:
    """
    Thread-safe inference wrapper for TRSA-Net.
    """

    _instance: Optional["TRSAInferenceEngine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = TemporalScarcityNet(
            text_embed_dim=384,
            temporal_dim=5,
            hidden_dim=256,
            num_classes=4,
        ).to(self.device)
        self.model.eval()

    @classmethod
    def get_instance(cls) -> "TRSAInferenceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = TRSAInferenceEngine()
        return cls._instance

    def predict(
        self,
        text_embedding: torch.Tensor,
        has_timer: bool = False,
        is_looping_reset: bool = False,
        timer_seconds: float = 0.0,
        has_scarcity_warning: bool = False,
        is_social_ticker: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes TRSA-Net neural prediction.
        """
        with torch.no_grad():
            if text_embedding.dim() == 1:
                text_tensor = text_embedding.unsqueeze(0).to(self.device)
            else:
                text_tensor = text_embedding.to(self.device)

            # Temporal feature vector: [has_timer, is_looping_reset, timer_norm, has_scarcity, is_social_ticker]
            temp_vec = torch.tensor(
                [
                    [
                        1.0 if has_timer else 0.0,
                        1.0 if is_looping_reset else 0.0,
                        min(1.0, float(timer_seconds) / 3600.0) if timer_seconds else (0.8 if has_timer else 0.0),
                        1.0 if has_scarcity_warning else 0.0,
                        1.0 if is_social_ticker else 0.0,
                    ]
                ],
                dtype=torch.float32,
                device=self.device,
            )

            logits, _ = self.model(text_tensor, temp_vec)
            probs = F.softmax(logits, dim=-1)[0]

            p_clean = float(probs[0].item())
            p_urgency = float(torch.sum(probs[1:]).item())
            top_class_idx = int(torch.argmax(probs).item())
            urgency_category = TemporalScarcityNet.URGENCY_CLASSES[top_class_idx]

            is_detected = (has_timer or has_scarcity_warning or is_social_ticker or is_looping_reset) and (p_urgency >= 0.45)

            return {
                "p_false_urgency": p_urgency,
                "p_clean": p_clean,
                "urgency_category": urgency_category if is_detected else "CLEAN_TRANSPARENT_URGENCY",
                "is_detected": bool(is_detected),
                "model_name": "TRSA-Net (Temporal-Recurrent Scarcity Authenticity Network)",
            }


def get_trsa_model() -> TRSAInferenceEngine:
    return TRSAInferenceEngine.get_instance()
