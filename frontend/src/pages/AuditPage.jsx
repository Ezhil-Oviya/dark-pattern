import { useState } from "react";

import Layout from "../components/layout/Layout";

import AuditForm from "../components/audit/AuditForm";
import AuditProgress from "../components/audit/AuditProgress";
import AuditResult from "../components/audit/AuditResult";

import { startAudit } from "../services/automationService";

import "../styles/audit.css";

export default function AuditPage(){

    const [loading,setLoading]=useState(false);

    const [result,setResult]=useState(null);

    async function handleAudit(id){

        try{

            setLoading(true);

            setResult(null);

            const data=await startAudit(id);

            setResult(data);

        }

        catch(e){

            console.log(e);

            alert("Audit Failed");

        }

        finally{

            setLoading(false);

        }

    }

    return(

        <Layout>

            <AuditForm

                onStart={handleAudit}

                loading={loading}

            />

            <AuditProgress

                loading={loading}

            />

            <AuditResult

                result={result}

            />

        </Layout>

    );

}