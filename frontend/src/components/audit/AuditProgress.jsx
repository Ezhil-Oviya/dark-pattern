export default function AuditProgress({ loading }) {

    if (!loading) return null;

    return (

        <div className="card">

            <h2>Audit Running...</h2>

            <br/>

            <p> Launching Chromium Browser</p>

            <p> Opening Website</p>

            <p> Waiting for Full Page Load</p>

            <p> Capturing Screenshot</p>

            <p> Saving HTML DOM</p>

            <p> Generating Audit Result...</p>

        </div>

    );

}