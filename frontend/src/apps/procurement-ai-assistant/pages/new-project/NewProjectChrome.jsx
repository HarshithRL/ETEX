import { Link } from "react-router-dom";
import { PROJECTS_LIST_PATH } from "./paths";

function NewProjectChrome({ crumbs, children }) {
  return (
    <div className="new-project-page">
      <div className="new-project-container">
        <div className="new-project-topbar">
          <nav className="new-project-breadcrumb" aria-label="Breadcrumb">
            <Link to={PROJECTS_LIST_PATH}>Projects</Link>
            {crumbs.map((crumb) => (
              <span key={crumb.label} className="new-project-crumb">
                <span aria-hidden="true">/</span>
                {crumb.to ? (
                  <Link to={crumb.to}>{crumb.label}</Link>
                ) : (
                  <strong>{crumb.label}</strong>
                )}
              </span>
            ))}
          </nav>

          <Link className="new-project-cancel" to={PROJECTS_LIST_PATH}>
            Cancel
          </Link>
        </div>

        {children}
      </div>
    </div>
  );
}

export default NewProjectChrome;
