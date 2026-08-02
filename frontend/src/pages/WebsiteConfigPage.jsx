import { useEffect, useState } from "react";

import WebsiteForm from "../components/dashboard/WebsiteForm";
import WebsiteTable from "../components/dashboard/WebsiteTable";
import Sidebar from "../components/layout/Sidebar";
import Topbar from "../components/layout/Topbar";
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

  useEffect(() => {
    loadWebsites();
  }, []);

  const loadWebsites = async () => {

    try {

      const data = await getWebsites();

      setWebsites(data);

    } catch (error) {

      console.error(error);

      alert("Failed to load websites.");

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
    console.log("FULL ERROR:", error);

    if (error.response) {
      console.log("Status:", error.response.status);
      console.log("Response:", error.response.data);
    } else if (error.request) {
      console.log("No response from backend");
      console.log(error.request);
    } else {
      console.log(error.message);
    }

    alert("Operation failed.");
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

      alert("Website deleted.");

      loadWebsites();

    } catch (error) {

      console.error(error);

      alert("Delete failed.");

    }

  };

  const clearSelection = () => {

    setSelectedWebsite(null);

  };

  if (loading) {

    return <h2 style={{ padding: "30px" }}>Loading...</h2>;

  }

  return (
    <Layout>

    <div className="dashboard-container">

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

    </div>

  </Layout>
);

}