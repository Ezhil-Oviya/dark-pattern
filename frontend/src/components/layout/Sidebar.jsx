import {
  LayoutDashboard,
  Globe,
  PlayCircle,
  FileSearch,
  FileText,
  Bot,
  Shield
} from "lucide-react";
import { NavLink } from "react-router-dom";
import "../../styles/sidebar.css";

export default function Sidebar() {
  const menuItems = [
    {
      title: "Dashboard",
      path: "/dashboard",
      icon: <LayoutDashboard size={18} />
    },
    {
      title: "Website Config",
      path: "/website-config",
      icon: <Globe size={18} />
    },
    {
      title: "Browser Automation",
      path: "/audits",
      icon: <PlayCircle size={18} />
    },
    {
      title: "Evidence Collection",
      path: "/evidence",
      icon: <FileSearch size={18} />
    },
    {
      title: "Reports",
      path: "/reports",
      icon: <FileText size={18} />
    },
    {
      title: "AI Compliance Bot",
      path: "/bot",
      icon: <Bot size={18} />
    }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon-wrapper">
          <Shield size={24} className="logo-icon" />
        </div>
        <div>
          <h2>DPCA</h2>
          <p className="logo-subtitle">Compliance Auditor</p>
        </div>
      </div>

      <div className="menu-label">Auditing Engine</div>
      
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              isActive
                ? "sidebar-link active"
                : "sidebar-link"
            }
          >
            <span className="icon-span">{item.icon}</span>
            <span className="title-span">{item.title}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="version-badge">v1.1.0-prod</span>
      </div>
    </aside>
  );
}