import { useNavigate } from "react-router-dom";
import NewProjectChrome from "./NewProjectChrome";
import {
  NEW_PROJECT_CHAT_PATH,
  NEW_PROJECT_FORM_PATH,
} from "./paths";
import "./NewProject.css";

function NewProject() {
  const navigate = useNavigate();

  return (
    <NewProjectChrome crumbs={[{ label: "New project" }]}>
      <header className="new-project-hero">
        <span className="new-project-eyebrow">
          CREATE A SOURCING PROJECT
        </span>
        <h1>How would you like to start?</h1>
        <p>
          Both paths end with a traceable knowledge graph built from your
          brief and vendor documents.
        </p>
      </header>

      <section className="new-project-cards" aria-label="Start options">
        <article className="new-project-card">
          <span className="new-project-option">OPTION 1</span>
          <h2>Chat with the procurement agent</h2>
          <p>
            Describe what you are buying in conversation. Upload vendor
            proposals as you go. The agent fills in the brief for you.
          </p>
          <button
            className="primary-button"
            type="button"
            onClick={() => navigate(NEW_PROJECT_CHAT_PATH)}
          >
            Start chatting
          </button>
        </article>

        <article className="new-project-card">
          <span className="new-project-option">OPTION 2</span>
          <h2>Fill the brief manually</h2>
          <p>
            Use the structured form to enter project details, weighted
            requirements, and upload vendor files — the current wizard.
          </p>
          <button
            className="secondary-button"
            type="button"
            onClick={() => navigate(NEW_PROJECT_FORM_PATH)}
          >
            Open form
          </button>
        </article>
      </section>
    </NewProjectChrome>
  );
}

export default NewProject;
