import { Pencil, Trash2, Globe } from "lucide-react";

import "../../styles/tables.css";

export default function WebsiteTable({
  websites,
  onEdit,
  onDelete
}) {
  return (
    <div className="table-card">

      <div className="table-header">

        <h2>Configured Websites</h2>

        <span>
          {websites.length} Website(s)
        </span>

      </div>

      {websites.length === 0 ? (

        <div className="empty-table">

          <Globe size={60} color="#94A3B8" />

          <h3>No Websites Configured</h3>

          <p>
            Add your first website to begin compliance auditing.
          </p>

        </div>

      ) : (

        <table className="website-table">

          <thead>

            <tr>

              <th>Platform</th>

              <th>Category</th>

              <th>Crawl</th>

              <th>Pages</th>

              <th>Status</th>

              <th>Actions</th>

            </tr>

          </thead>

          <tbody>

            {websites.map((website) => (

              <tr key={website.id}>

                <td>

                  <div className="platform-cell">

                    <div className="platform-icon">

                      🌐

                    </div>

                    <div>

                      <strong>

                        {website.platform}

                      </strong>

                      <br />

                      <small>

                        {website.url}

                      </small>

                    </div>

                  </div>

                </td>

                <td>

                  {website.category}

                </td>

                <td>

                  {website.crawl_depth}

                </td>

                <td>

                  {website.max_pages}

                </td>

                <td>

                  <span className="status-ready">

                    Ready

                  </span>

                </td>

                <td>

                  <button
                    className="edit-btn"
                    onClick={() => onEdit(website)}
                  >

                    <Pencil size={16} />

                    Edit

                  </button>

                  <button
                    className="delete-btn"
                    onClick={() => onDelete(website.id)}
                  >

                    <Trash2 size={16} />

                    Delete

                  </button>

                </td>

              </tr>

            ))}

          </tbody>

        </table>

      )}

    </div>
  );
}