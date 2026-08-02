import { useEffect, useState } from "react";

import "../../styles/forms.css";

const initialForm = {
  platform: "",
  url: "",
  category: "Ecommerce",
  crawl_depth: 3,
  max_pages: 10,
  headless: true,
  capture_dom: true,
  capture_screenshots: true,
  login_required: false
};

export default function WebsiteForm({
  onSubmit,
  selectedWebsite,
  clearSelection
}) {
  const [formData, setFormData] = useState(initialForm);

  useEffect(() => {
    if (selectedWebsite) {
      setFormData(selectedWebsite);
    } else {
      setFormData(initialForm);
    }
  }, [selectedWebsite]);

  const handleChange = (e) => {
    const { name, value, checked, type } = e.target;

    setFormData((prev) => ({
      ...prev,
      [name]:
        type === "checkbox"
          ? checked
          : type === "number"
          ? Number(value)
          : value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!formData.platform.trim()) {
      alert("Platform Name is required");
      return;
    }

    if (!formData.url.trim()) {
      alert("Website URL is required");
      return;
    }

    onSubmit(formData);

    if (!selectedWebsite) {
      setFormData(initialForm);
    }
  };

  return (
    <div className="form-card">

      <div className="form-header">

        <h2>Website Configuration</h2>

        <p>
          Configure websites for automated compliance auditing.
        </p>

      </div>

      <form onSubmit={handleSubmit}>

        <div className="grid-two">

          <div className="form-group">

            <label>Platform Name</label>

            <input
              type="text"
              name="platform"
              placeholder="Amazon"
              value={formData.platform}
              onChange={handleChange}
            />

          </div>

          <div className="form-group">

            <label>Website URL</label>

            <input
              type="text"
              name="url"
              placeholder="https://amazon.in"
              value={formData.url}
              onChange={handleChange}
            />

          </div>

        </div>

        <div className="grid-three">

          <div className="form-group">

            <label>Category</label>

            <select
              name="category"
              value={formData.category}
              onChange={handleChange}
            >
              <option>Ecommerce</option>
              <option>Travel</option>
              <option>Banking</option>
              <option>Insurance</option>
            </select>

          </div>

          <div className="form-group">

            <label>Crawl Depth</label>

            <input
              type="number"
              name="crawl_depth"
              value={formData.crawl_depth}
              onChange={handleChange}
            />

          </div>

          <div className="form-group">

            <label>Maximum Pages</label>

            <input
              type="number"
              name="max_pages"
              value={formData.max_pages}
              onChange={handleChange}
            />

          </div>

        </div>

        <div className="checkbox-section">

          <label>

            <input
              type="checkbox"
              name="headless"
              checked={formData.headless}
              onChange={handleChange}
            />

            Headless Browser

          </label>

          <label>

            <input
              type="checkbox"
              name="capture_dom"
              checked={formData.capture_dom}
              onChange={handleChange}
            />

            Capture DOM

          </label>

          <label>

            <input
              type="checkbox"
              name="capture_screenshots"
              checked={formData.capture_screenshots}
              onChange={handleChange}
            />

            Capture Screenshots

          </label>

          <label>

            <input
              type="checkbox"
              name="login_required"
              checked={formData.login_required}
              onChange={handleChange}
            />

            Login Required

          </label>

        </div>

        <div className="button-row">

          <button
            className="save-btn"
            type="submit"
          >
            {selectedWebsite
              ? "Update Website"
              : "Save Website"}
          </button>

          {selectedWebsite && (

            <button
              type="button"
              className="cancel-btn"
              onClick={clearSelection}
            >
              Cancel
            </button>

          )}

        </div>

      </form>

    </div>
  );
}