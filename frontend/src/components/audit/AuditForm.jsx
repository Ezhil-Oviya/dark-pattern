import { useEffect, useState } from "react";

import { getWebsites } from "../../services/websiteService";

export default function AuditForm({ onStart, loading }) {

    const [websites, setWebsites] = useState([]);

    const [selected, setSelected] = useState("");

    useEffect(() => {

        load();

    }, []);

    async function load(){

        const data = await getWebsites();

        setWebsites(data);

        if(data.length>0){

            setSelected(data[0].id);

        }

    }

    return(

        <div className="card">

            <h2>Browser Automation</h2>

            <label>Select Website</label>

            <select
                value={selected}
                onChange={(e)=>setSelected(e.target.value)}
            >

                {
                    websites.map(site=>(
                        <option
                            key={site.id}
                            value={site.id}
                        >
                            {site.platform}
                        </option>
                    ))
                }

            </select>

            <button

                className="primary-btn"

                disabled={loading}

                onClick={()=>onStart(selected)}

            >

                {loading ? "Running Audit..." : "Start Audit"}

            </button>

        </div>

    );

}