const API="http://localhost:8000/";

export default function AuditResult({result}){

    if(!result) return null;

    return(

        <div className="card">

            <h2>Audit Completed Successfully</h2>

            <table className="audit-table">

                <tbody>

                    <tr>

                        <td><strong>Platform</strong></td>

                        <td>{result.platform}</td>

                    </tr>

                    <tr>

                        <td><strong>Final URL</strong></td>

                        <td>{result.final_url}</td>

                    </tr>

                    <tr>

                        <td><strong>Audit Time</strong></td>

                        <td>{result.audit_time}</td>

                    </tr>

                </tbody>

            </table>

            <hr/>

            <h3>Captured Screenshot</h3>

            <img

                src={API+result.screenshot}

                alt="Screenshot"

                className="audit-image"

            />

            <br/><br/>

            <a

                href={API+result.screenshot}

                target="_blank"

                rel="noreferrer"

                className="primary-btn"

            >

                Open Screenshot

            </a>

        </div>

    );

}