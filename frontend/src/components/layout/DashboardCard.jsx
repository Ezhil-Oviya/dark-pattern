import "../../styles/dashboard.css";

export default function DashboardCard({

    title,

    value,

    icon,

    color,

    onClick

}){

    return(

        <div
            className="dashboard-card"
            style={{
                borderTop:`5px solid ${color}`,
                cursor:"pointer"
            }}
            onClick={onClick}
        >

            <div className="dashboard-icon">

                {icon}

            </div>

            <div>

                <h2>{value}</h2>

                <p>{title}</p>

            </div>

        </div>

    );

}