import { useState } from "react";
import { Bell, ShieldCheck, Trash2 } from "lucide-react";
import "../../styles/topbar.css";

export default function Topbar() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([
    { 
      id: 1, 
      title: "Audit Completed", 
      message: "The comprehensive compliance audit for 'amazon.in' has been successfully completed.", 
      time: "Just now" 
    },
    { 
      id: 2, 
      title: "Website Configured", 
      message: "New website 'flipkart.com' has been successfully configured and added to the monitoring dashboard.", 
      time: "5m ago" 
    }
  ]);

  const clearNotifications = () => {
    setNotifications([]);
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1>Dark Pattern Compliance Auditor</h1>
        <p>Intelligent Automated Compliance Auditing Framework</p>
      </div>

      <div className="topbar-right">
        <div className="system-badge">
          <ShieldCheck size={16} className="status-ok-icon" />
          <span>System Active</span>
        </div>
        
        <div className="notifications-wrapper">
          <button 
            className="notification-btn" 
            aria-label="Notifications"
            onClick={() => setShowNotifications(!showNotifications)}
          >
            <Bell size={18} />
            {notifications.length > 0 && <span className="notification-dot"></span>}
          </button>

          {showNotifications && (
            <div className="notifications-dropdown">
              <div className="notifications-header">
                <h3>Notifications</h3>
                {notifications.length > 0 && (
                  <button onClick={clearNotifications} className="clear-notifications-btn" title="Clear all">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              <ul className="notifications-list">
                {notifications.length === 0 ? (
                  <li className="notification-empty">No new notifications</li>
                ) : (
                  notifications.map((notif) => (
                    <li key={notif.id} className="notification-item">
                      <div className="notification-content">
                        <span className="notification-title">{notif.title}</span>
                        <p className="notification-message">{notif.message}</p>
                        <span className="notification-time">{notif.time}</span>
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}