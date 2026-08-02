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

import Sidebar from "../components/layout/Sidebar";
import Topbar from "../components/layout/Topbar";
import DashboardCard from "../components/layout/DashboardCard";
import StatusCard from "../components/layout/StatusCard";
import QuickActions from "../components/layout/QuickActions";
import { useNavigate } from "react-router-dom";

import { getWebsites } from "../services/websiteService";
import { getHealth } from "../services/healthService";

import Layout from "../components/layout/Layout";

import "../styles/dashboard.css";

export default function DashboardPage(){

    const [websites,setWebsites]=useState([]);

const [health,setHealth]=useState({

    backend:"offline",

    database:"offline",

    browser:"offline"

});

    const navigate = useNavigate();

    useEffect(()=>{

        load();

        loadHealth();

    },[]);

    const load=async()=>{

        try{

            const data=await getWebsites();

            setWebsites(data);

        }

        catch(e){

            console.log(e);

        }

    };

    const loadHealth = async () => {

    try{

        const data = await getHealth();

        setHealth(data);

    }

    catch{

        setHealth({

            backend:"offline",

            database:"offline",

            browser:"offline"

        });

    }

};

    

    return(

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

    value="0"

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

                    title="Backend"

                    status={health.backend}

                    color="#22C55E"

                    icon={<Server/>}

                />

                <StatusCard

                    title="MongoDB"

                    status={health.database}

                    color="#2563EB"

                    icon={<Database/>}

                />

                <StatusCard

                    title="Browser"

                    status={health.browser}

                    color="#F59E0B"

                    icon={<MonitorSmartphone/>}

                />

            </div>

            <div
            style={{
            display:"grid",
            gridTemplateColumns:"2fr 1fr",
            gap:"25px"
            }}
           >
            <div className="recent-card">

                <div className="recent-header">

                    <h2>

                        Recent Websites

                    </h2>

                    <span>

                        {websites.length} Websites

                    </span>

                </div>

                {

                    websites.map(site=>(

                        <div
                            key={site.id}
                            className="recent-item"
                        >

                            <div>

                                <strong>

                                    {site.platform}

                                </strong>

                                <br/>

                                <small>

                                    {site.url}

                                </small>

                            </div>

                            <span className="ready">

                                Ready

                            </span>

                        </div>

                    ))

                }

            </div>

        </div>

        <QuickActions/>

      </Layout>

    );

}