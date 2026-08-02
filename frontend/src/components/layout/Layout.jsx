import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function Layout({ children }) {

    return (

        <>

            <Sidebar />

            <Topbar />

            <div className="dashboard-container">

                {children}

            </div>

        </>

    );

}