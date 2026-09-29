import unittest
import torch
from app.services.ai_models.sacm_net import StateAwareBasketSneakingNet, get_sacm_model
from app.services.ai_models.cgpd_net import ContextGatedForcedActionNet, get_cgpd_model


class TestMultimodalNeuralModels(unittest.TestCase):
    """Unit tests for SACM-Net and CGPD-Net deep learning models."""

    def test_sacm_net_forward_pass(self):
        """Verify SACM-Net forward pass shapes and output logits."""
        model = StateAwareBasketSneakingNet(
            text_embed_dim=384,
            visual_embed_dim=512,
            dom_feature_dim=6,
            hidden_dim=256,
            num_classes=2,
        )
        batch_size = 4
        text_emb = torch.randn(batch_size, 384)
        vis_emb = torch.randn(batch_size, 512)
        dom_features = torch.randn(batch_size, 6)

        logits, attn_weights = model(text_emb, vis_emb, dom_features)
        self.assertEqual(logits.shape, (batch_size, 2))
        self.assertIsNotNone(attn_weights)

    def test_sacm_engine_prediction(self):
        """Verify SACMInferenceEngine prediction on preselected add-on."""
        engine = get_sacm_model()
        dummy_embedding = torch.randn(384)
        result = engine.predict(
            text_embedding=dummy_embedding,
            is_preselected=True,
            has_price=True,
            price_value=299.0,
            is_unsolicited_cart=True,
        )
        self.assertIn("p_sneaking", result)
        self.assertIn("p_clean", result)
        self.assertIn("SACM-Net", result["model_name"])

    def test_cgpd_net_forward_pass(self):
        """Verify CGPD-Net forward pass and CCPA gate behavior."""
        model = ContextGatedForcedActionNet(
            text_embed_dim=384,
            visual_embed_dim=512,
            context_dim=4,
            hidden_dim=256,
            num_classes=5,
        )
        batch_size = 3
        text_emb = torch.randn(batch_size, 384)
        vis_emb = torch.randn(batch_size, 512)
        context_features = torch.tensor([
            [1.0, 0.0, 1.0, 0.0],  # Guest option present -> Gate should suppress violation
            [0.0, 0.0, 1.0, 0.0],  # No guest option, modal blocking -> Violation
            [0.0, 1.0, 0.0, 0.0],  # Dismissible
        ])

        logits, gate_weight, attn_weights = model(text_emb, vis_emb, context_features)
        self.assertEqual(logits.shape, (batch_size, 5))
        self.assertEqual(gate_weight.shape, (batch_size, 1))

    def test_cgpd_engine_ccpa_compliance_gating(self):
        """Verify CCPA alternative-path gating zeroes out violation when guest option is present."""
        engine = get_cgpd_model()
        dummy_embedding = torch.randn(384)

        # Case 1: Trapped behind modal with no guest option -> Should evaluate as potential forced action
        res_trapped = engine.predict(
            text_embedding=dummy_embedding,
            has_guest_alternative=False,
            is_dismissible=False,
            is_modal_overlay=True,
            is_legitimate_prerequisite=False,
        )
        self.assertIn("p_forced_action", res_trapped)
        self.assertIn("CCPA Guidelines 2023", res_trapped["legal_framework"])

        # Case 2: Guest option is present -> CCPA dictates NO Forced Action
        res_guest = engine.predict(
            text_embedding=dummy_embedding,
            has_guest_alternative=True,
            is_dismissible=True,
            is_modal_overlay=True,
            is_legitimate_prerequisite=False,
        )
        self.assertFalse(res_guest["is_detected"])
        self.assertEqual(res_guest["ccpa_category"], "CLEAN_VOLUNTARY")


if __name__ == "__main__":
    unittest.main()
