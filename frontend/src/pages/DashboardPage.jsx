import { useEffect, useState } from "react";
import {
    Globe,
    PlayCircle,
    ShieldAlert,
    FileText,
    Database,
    Server,
    MonitorSmartphone
} from "lucide-react";

import Layout from "../components/layout/Layout";
import DashboardCard from "../components/layout/DashboardCard";
import StatusCard from "../components/layout/StatusCard";
import QuickActions from "../components/layout/QuickActions";
import { useNavigate } from "react-router-dom";
import { getWebsites } from "../services/websiteService";
import { getHealth } from "../services/healthService";
import { getAudits } from "../services/automationService";
import "../styles/dashboard.css";

export default function DashboardPage(){

    const [websites,setWebsites]=useState([]);
    const [auditCount, setAuditCount]=useState(0);

const [health,setHealth]=useState({

    backend:"offline",

    database:"offline",

    browser:"offline"

});


    const navigate = useNavigate();

    useEffect(() => {
        load();

        loadAuditsCount();

        loadHealth();
    }, []);

    const load = async () => {
        try {
            const data = await getWebsites();
            setWebsites(data);
        } catch (e) {
            console.log(e);
        }
    };

    const loadAuditsCount = async () => {
        try {
            const list = await getAudits();
            setAuditCount(Array.isArray(list) ? list.length : 0);
        } catch (e) {
            console.error("Failed to load audits count:", e);
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

    icon={<Globe color="#2563EB"/>}

    color="#2563EB"

    onClick={() => navigate("/website-config")}

/>

<DashboardCard

    title="Audits"

    value={auditCount}

    icon={<PlayCircle color="#22C55E"/>}

    color="#22C55E"

    onClick={() => navigate("/audits")}

/>

<DashboardCard

    title="Violations"

    value="0"

    icon={<ShieldAlert color="#F59E0B"/>}

    color="#F59E0B"

/>

<DashboardCard

    title="Reports"

    value="0"

    icon={<FileText color="#EF4444"/>}

    color="#EF4444"

    onClick={() => navigate("/reports")}

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
                            websites.slice(0, 5).map(site => (
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
        </Layout>
    );
}