import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import ThemeToggle from "../../components/theme/ThemeToggle";
import { useTheme } from "../../components/theme/useTheme";
import { apiGet } from "../../services/api";
import { createLogger } from "../../shared/logger-global/index.js";
import etexLogoDark from "../../assets/brand/etex-logo-dark.png";
import etexLogoLight from "../../assets/brand/etex-logo-light.png";

import "./hub.css";

const log = createLogger("pages.hub");

function Hub() {
  const [page, setPage] = useState(null);
  const [error, setError] = useState(null);
  const { resolvedTheme } = useTheme();
  // Filenames are theme targets: *-light = dark ink, *-dark = white reverse
  const brandLogo =
    resolvedTheme === "light" ? etexLogoLight : etexLogoDark;

  useEffect(() => {
    apiGet("/api/auth")
      .catch((err) => {
        log.warn("Failed to resolve identity", { context: { error: String(err) } });
      })
      .then(() => apiGet("/api/hub"))
      .then((data) => {
        log.debug("Hub API loaded", { context: { toolCount: data?.categories?.length } });
        setPage(data);
      })
      .catch((err) => {
        log.error("Failed to load Hub", { context: { error: String(err) } });
        setError("Unable to load Hub.");
      });
  }, []);

  // --------------------------------------------------
  // Loading
  // --------------------------------------------------

  if (!page && !error) {
    return <div className="hub-loading">Loading...</div>;
  }

  // --------------------------------------------------
  // Error
  // --------------------------------------------------

  if (error) {
    return <div className="hub-loading">{error}</div>;
  }

  // --------------------------------------------------
  // Hub
  // --------------------------------------------------

  return (
    <div className="hub">
      <div className="hub-container">

        {/* =========================
            HEADER
        ========================== */}

        <header className="hub-header">
          <div className="brand">

            <img
              src={brandLogo}
              alt="Etex"
              className="etex-logo"
            />

            <span className="brand-divider" />

            <span className="mate-name">
              {page.brand.name}
            </span>

            <span className="mate-icon">
              ✧
            </span>

          </div>

          <ThemeToggle />
        </header>


        {/* =========================
            WELCOME
        ========================== */}

        <section className="welcome-section">

          <div className="welcome-content">

            <h1>
              {page.welcome.greeting}
            </h1>

            <p>
              {page.welcome.description}
            </p>

          </div>


          <div className="welcome-illustration">

            <img
              src={page.welcome.image}
              alt=""
            />

          </div>

        </section>


        {/* =========================
            CATEGORIES
        ========================== */}

        {page.categories.map((category) => (

          <section
            key={category.name}
            className="category-section"
          >

            <h2 className="category-title">
              {category.name}
            </h2>


            <div className="tools-grid">

              {category.tools.map((tool) =>
                tool.available === false ? (
                  <div
                    key={tool.id ?? tool.name}
                    className="tool-card is-coming-soon"
                    aria-disabled="true"
                  >
                    <div className="tool-icon">
                      {tool.icon ? (
                        <img src={tool.icon} alt="" />
                      ) : (
                        "✧"
                      )}
                    </div>
                    <div className="tool-bookmark">♧</div>
                    <span className="tool-badge">Coming soon</span>
                    <h3>{tool.name}</h3>
                    <p>{tool.description}</p>
                  </div>
                ) : (
                  <Link
                    key={tool.id ?? tool.name}
                    to={tool.path}
                    className="tool-card"
                  >
                    <div className="tool-icon">
                      {tool.icon ? (
                        <img src={tool.icon} alt="" />
                      ) : (
                        "✧"
                      )}
                    </div>
                    <div className="tool-bookmark">♧</div>
                    <h3>{tool.name}</h3>
                    <p>{tool.description}</p>
                  </Link>
                ),
              )}

            </div>

          </section>

        ))}

      </div>


      {/* =========================
          FOOTER
      ========================== */}

      {page.footer?.logo && (

        <div className="hub-footer">

          <img
            src={brandLogo}
            alt="Etex"
          />

        </div>

      )}

    </div>
  );
}

export default Hub;
