import { Play, Globe, FileText, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import "../../styles/quickactions.css";

export default function QuickActions() {

    const navigate = useNavigate();

    return (

        <div className="quick-card">

            <h2>Quick Actions</h2>

            <button
                className="quick-btn blue"
                onClick={() => navigate("/website-config")}
            >
                <Globe size={18} />
                Configure Website
            </button>

            <button
                className="quick-btn green"
                onClick={() => navigate("/audits")}
            >
                <Play size={18} />
                Start Browser Audit
            </button>

            <button
                className="quick-btn purple"
                style={{ background: "rgba(139, 92, 246, 0.1)", color: "#7c3aed", border: "1px solid rgba(139, 92, 246, 0.2)" }}
                onClick={() => navigate("/data-quality")}
            >
                <ShieldCheck size={18} />
                Assess Data Quality
            </button>

            <button
                className="quick-btn orange"
                onClick={() => navigate("/reports")}
            >
                <FileText size={18} />
                Generate Report
            </button>

        </div>

    );

}