import { useEffect, useState } from "react";

import WebsiteForm from "../components/dashboard/WebsiteForm";
import WebsiteTable from "../components/dashboard/WebsiteTable";
import Layout from "../components/layout/Layout";

import {
  getWebsites,
  createWebsite,
  updateWebsite,
  deleteWebsite
} from "../services/websiteService";

export default function WebsiteConfigPage() {
  const [websites, setWebsites] = useState([]);
  const [selectedWebsite, setSelectedWebsite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadWebsites();
  }, []);

  const loadWebsites = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await getWebsites();
      setWebsites(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load websites:", error);
      const detail = error.response?.data?.detail || error.message || "Failed to load websites from backend.";
      setErrorMsg(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (website) => {
    console.log("Sending to backend:", website);

    try {
      let response;
      if (selectedWebsite) {
        response = await updateWebsite(selectedWebsite.id, website);
        alert("Website updated successfully.");
      } else {
        response = await createWebsite(website);
        alert("Website added successfully.");
      }

      console.log("Backend Response:", response);
      setSelectedWebsite(null);
      await loadWebsites();
    } catch (error) {
      console.error("Save error:", error);
      const detail = error.response?.data?.detail || error.message || "Operation failed.";
      alert(`Save failed: ${detail}`);
    }
  };

  const handleEdit = (website) => {
    setSelectedWebsite(website);
  };

  const handleDelete = async (id) => {
    const confirmDelete = window.confirm(
      "Are you sure you want to delete this website?"
    );
    if (!confirmDelete) return;

    try {
      await deleteWebsite(id);
      alert("Website deleted successfully.");
      loadWebsites();
    } catch (error) {
      console.error("Delete error:", error);
      const detail = error.response?.data?.detail || error.message || "Delete failed.";
      alert(`Delete failed: ${detail}`);
    }
  };

  const clearSelection = () => {
    setSelectedWebsite(null);
  };

  return (
    <Layout>
      {errorMsg && (
        <div style={{
          backgroundColor: "#FEF2F2",
          border: "1px solid #FCA5A5",
          borderRadius: "8px",
          padding: "12px 16px",
          marginBottom: "20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          color: "#991B1B"
        }}>
          <div>
            <strong>Database Notice: </strong>
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={loadWebsites}
            style={{
              backgroundColor: "#DC2626",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "4px",
              padding: "6px 12px",
              cursor: "pointer",
              fontWeight: 500
            }}
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748B" }}>
          <h3>Loading website configurations...</h3>
        </div>
      ) : (
        <>
          <WebsiteForm
            onSubmit={handleSave}
            selectedWebsite={selectedWebsite}
            clearSelection={clearSelection}
          />

          <WebsiteTable
            websites={websites}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        </>
      )}
    </Layout>
  );
}