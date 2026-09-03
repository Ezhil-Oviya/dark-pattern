import { Bell, ShieldCheck, User } from "lucide-react";
import "../../styles/topbar.css";

export default function Topbar() {
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
        
        <button className="notification-btn" aria-label="Notifications">
          <Bell size={18} />
          <span className="notification-dot"></span>
        </button>

        <div className="profile-badge">
          <div className="avatar-wrapper">
            <User size={16} />
          </div>
          <div className="profile-info">
            <span className="profile-name">Administrator</span>
            <span className="profile-role">Compliance Officer</span>
          </div>
        </div>
      </div>
    </header>
  );
}