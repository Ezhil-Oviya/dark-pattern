import "../../styles/statuscard.css";

export default function StatusCard({

    title,

    status,

    icon,

    color

}){

    return(

        <div className="status-box">

            <div
                className="status-icon"
                style={{
                    background:color
                }}
            >

                {icon}

            </div>

            <div>

                <h3>{title}</h3>

                <p
    style={{
        color:
            status==="connected" ||
            status==="online" ||
            status==="ready"

            ? "#16A34A"

            : "#DC2626"
    }}
>

    ● {status}

</p>

            </div>

        </div>

    );

}