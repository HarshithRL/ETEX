import { useRef, useState } from "react";
import {
  FILE_ACCEPT,
  addStagedFiles,
  formatFileSize,
} from "./stagedFiles";

function StagedFileDropzone({
  files,
  onFilesChange,
  compact = false,
  heading = "Drop PDF, DOCX, or XLSX files here",
  hint = "Up to 40 MB per file. Files are staged until you create the project.",
}) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [fileErrors, setFileErrors] = useState([]);

  function stageIncoming(incoming) {
    const { files: next, errors } = addStagedFiles(files, incoming);
    onFilesChange(next);
    setFileErrors(errors);
  }

  return (
    <>
      <div
        className={`new-project-dropzone${compact ? " new-project-dropzone-compact" : ""}${
          dragging ? " is-dragging" : ""
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          stageIncoming(Array.from(event.dataTransfer.files || []));
        }}
      >
        <p>{heading}</p>
        <small>{hint}</small>
        <input
          ref={inputRef}
          type="file"
          accept={FILE_ACCEPT}
          multiple
          hidden
          onChange={(event) => {
            stageIncoming(Array.from(event.target.files || []));
            event.target.value = "";
          }}
        />
        <button
          className="secondary-button"
          type="button"
          onClick={() => inputRef.current?.click()}
        >
          Browse files
        </button>
      </div>

      {!compact && (
        <div className="new-project-staged">
          <span className="new-project-staged-label">STAGED</span>
          <p className="new-project-staged-status">
            {files.length
              ? `${files.length} file${files.length === 1 ? "" : "s"} staged`
              : "No files staged yet"}
          </p>
        </div>
      )}

      {fileErrors.length > 0 && (
        <ul className="new-project-file-errors">
          {fileErrors.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <ul className="new-project-file-list">
          {files.map((file) => (
            <li key={`${file.name}-${file.size}`}>
              <span>
                {file.name}
                <small>{formatFileSize(file.size)}</small>
              </span>
              <button
                type="button"
                className="new-project-remove"
                aria-label={`Remove ${file.name}`}
                onClick={() =>
                  onFilesChange(
                    files.filter(
                      (item) =>
                        !(item.name === file.name && item.size === file.size),
                    ),
                  )
                }
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default StagedFileDropzone;
