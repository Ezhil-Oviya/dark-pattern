import {
  LayoutDashboard,
  Globe,
  PlayCircle,
  FileSearch,
  FileText,
  Bot
} from "lucide-react";

import { NavLink } from "react-router-dom";

import "../../styles/sidebar.css";

export default function Sidebar() {
  const menuItems = [
    {
      title: "Dashboard",
      path: "/dashboard",
      icon: <LayoutDashboard size={20} />
    },
    {
      title: "Website Configuration",
      path: "/website-config",
      icon: <Globe size={20} />
    },
    {
      title: "Browser Automation",
      path: "/audits",
      icon: <PlayCircle size={20} />
    },
    {
      title: "Evidence Collection",
      path: "/evidence",
      icon: <FileSearch size={20} />
    },
    {
      title: "Reports",
      path: "/reports",
      icon: <FileText size={20} />
    },
    {
      title: "AI Compliance Bot",
      path: "/bot",
      icon: <Bot size={20} />
    }
  ];

  return (
    <aside className="sidebar">

      <div className="sidebar-logo">

        <h2>DPCA</h2>

        <p>Compliance Auditor</p>

      </div>

      <nav>

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

            {item.icon}

            <span>{item.title}</span>

          </NavLink>

        ))}

      </nav>

    </aside>
  );
}