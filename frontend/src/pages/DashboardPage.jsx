import { useEffect, useState } from "react";
import {
    Globe,
    PlayCircle,
    ShieldAlert,
    FileText,
    Database,
    Server,
    MonitorSmartphone,
    Layers,
    ShieldCheck
} from "lucide-react";

import Layout from "../components/layout/Layout";
import DashboardCard from "../components/layout/DashboardCard";
import StatusCard from "../components/layout/StatusCard";
import QuickActions from "../components/layout/QuickActions";
import { useNavigate } from "react-router-dom";
import { getWebsites } from "../services/websiteService";
import { getHealth } from "../services/healthService";
import { getAudits } from "../services/automationService";
import { ALL_PATTERNS, PATTERN_ICONS } from "../config/patterns";
import "../styles/dashboard.css";

export default function DashboardPage() {
    const [websites, setWebsites] = useState([]);
    const [auditCount, setAuditCount] = useState(0);
    const [totalViolations, setTotalViolations] = useState(0);
    const [patternDistribution, setPatternDistribution] = useState({});
    const [health, setHealth] = useState({
        backend: "offline",
        database: "offline",
        browser: "offline"
    });

    const navigate = useNavigate();

    useEffect(() => {
        load();
        loadAuditsStats();
        loadHealth();
    }, []);

    const load = async () => {
        try {
            const data = await getWebsites();
            setWebsites(Array.isArray(data) ? data : []);
        } catch (e) {
            console.log(e);
        }
    };

    const loadAuditsStats = async () => {
        try {
            const list = await getAudits();
            const safeList = Array.isArray(list) ? list : [];
            setAuditCount(safeList.length);

            let violations = 0;
            const dist = {};
            ALL_PATTERNS.forEach(p => { dist[p] = 0; });

            safeList.forEach(audit => {
                violations += audit.total_dark_pattern_findings || 0;
                const summaries = audit.dark_pattern_summary || [];
                summaries.forEach(s => {
                    if ((s.status === "DETECTED" || s.detected) && dist[s.pattern] !== undefined) {
                        dist[s.pattern] += (s.total_instances || 1);
                    }
                });
            });

            setTotalViolations(violations);
            setPatternDistribution(dist);
        } catch (e) {
            console.error("Failed to load audits stats:", e);
        }
    };

    const loadHealth = async () => {
        try {
            const data = await getHealth();
            setHealth(data);
        } catch {
            setHealth({
                backend: "offline",
                database: "offline",
                browser: "offline"
            });
        }
    };

    return (
        <Layout>
            <div className="dashboard-cards">
                <DashboardCard
                    title="Configured Websites"
                    value={websites.length}
                    icon={<Globe color="#2563EB" />}
                    color="#2563EB"
                    onClick={() => navigate("/website-config")}
                />

                <DashboardCard
                    title="Audits Completed"
                    value={auditCount}
                    icon={<PlayCircle color="#22C55E" />}
                    color="#22C55E"
                    onClick={() => navigate("/audits")}
                />

                <DashboardCard
                    title="Violations Detected"
                    value={totalViolations}
                    icon={<ShieldAlert color="#F59E0B" />}
                    color="#F59E0B"
                    onClick={() => navigate("/evidence")}
                />

                <DashboardCard
                    title="Data Quality"
                    value="Audit Ready"
                    icon={<ShieldCheck color="#6366F1" />}
                    color="#6366F1"
                    onClick={() => navigate("/data-quality")}
                />
            </div>

            <div className="status-grid">
                <StatusCard
                    title="Automation Engine"
                    status={health.backend}
                    color="var(--primary)"
                    icon={<Server size={20} />}
                />
                <StatusCard
                    title="Database Store"
                    status={health.database}
                    color="var(--success)"
                    icon={<Database size={20} />}
                />
                <StatusCard
                    title="Browser Instance"
                    status={health.browser}
                    color="var(--warning)"
                    icon={<MonitorSmartphone size={20} />}
                />
            </div>

            <div className="dashboard-grid-layout">
                <div className="recent-card">
                    <div className="recent-header">
                        <h2>Dark Pattern Distribution (8 Categories)</h2>
                        <span className="badge-count">{totalViolations} Detected</span>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "12px" }}>
                        {ALL_PATTERNS.map(pat => {
                            const count = patternDistribution[pat] || 0;
                            const pct = totalViolations > 0 ? Math.round((count / totalViolations) * 100) : 0;
                            const icon = PATTERN_ICONS[pat] || "⚠️";

                            return (
                                <div key={pat} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", padding: "8px 12px", borderRadius: "6px", background: "#f8fafc", border: "1px solid #e2e8f0" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: "180px" }}>
                                        <span>{icon}</span>
                                        <strong style={{ fontSize: "13px", color: "#334155" }}>{pat}</strong>
                                    </div>
                                    <div style={{ flex: 1, background: "#e2e8f0", height: "8px", borderRadius: "4px", overflow: "hidden" }}>
                                        <div style={{ width: `${Math.max(pct, count > 0 ? 5 : 0)}%`, height: "100%", background: count > 0 ? "#f59e0b" : "#94a3b8", borderRadius: "4px" }} />
                                    </div>
                                    <span style={{ fontSize: "12px", fontWeight: "bold", color: count > 0 ? "#b45309" : "#64748b", minWidth: "60px", textAlign: "right" }}>
                                        {count} ({pct}%)
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    <div className="recent-card">
                        <div className="recent-header">
                            <h2>Recent Configured Websites</h2>
                            <span className="badge-count">{websites.length} Sites</span>
                        </div>

                        <div className="recent-items-list">
                            {websites.length === 0 ? (
                                <div className="empty-state">
                                    <Globe size={32} className="empty-icon" />
                                    <p>No websites configured. Configure a site to get started.</p>
                                </div>
                            ) : (
                                websites.slice(0, 4).map(site => (
                                    <div key={site.id || site.url} className="recent-item">
                                        <div className="recent-item-meta">
                                            <strong>{site.platform}</strong>
                                            <span>{site.url}</span>
                                        </div>
                                        <span className="badge-ready">Ready</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <QuickActions />
                </div>
            </div>
        </Layout>
    );
}