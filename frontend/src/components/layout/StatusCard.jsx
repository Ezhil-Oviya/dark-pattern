import "../../styles/statuscard.css";

export default function StatusCard({
    title,
    status,
    icon,
    color
}) {
    const isOnline =
        status === "connected" ||
        status === "online" ||
        status === "ready";

    const bgTranslucent = color.includes("var(")
        ? color.replace(")", "-light)")
        : color + "15";

    return (
        <div className="status-box">
            <div
                className="status-icon"
                style={{
                    backgroundColor: bgTranslucent,
                    color: color
                }}
            >
                {icon}
            </div>

            <div className="status-info">
                <h3>{title}</h3>
                <span className={`status-badge ${isOnline ? "online" : "offline"}`}>
                    <span className="status-dot"></span>
                    {status}
                </span>
            </div>
        </div>
    );
}