import "../../styles/dashboard.css";

export default function DashboardCard({
    title,
    value,
    icon,
    color,
    onClick
}) {
    // Calculate light translucent background for the icon wrapper
    const bgTranslucent = color.includes("var(")
        ? color.replace(")", "-light)")
        : color + "15";

    return (
        <div
            className="dashboard-card"
            onClick={onClick}
            style={{ cursor: onClick ? "pointer" : "default" }}
        >
            <div
                className="dashboard-icon"
                style={{
                    backgroundColor: bgTranslucent,
                    color: color
                }}
            >
                {icon}
            </div>

            <div className="dashboard-card-info">
                <h2>{value}</h2>
                <p>{title}</p>
            </div>
        </div>
    );
}