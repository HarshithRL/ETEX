function FileExplorer({ files, storage }) {
  return (
    <aside className="ws-files">
      <div className="ws-panel-header">
        <strong>PROJECT FILES</strong>
        <button type="button" aria-label="Add file">＋</button>
      </div>

      <div className="ws-file-search">
        <span aria-hidden="true">⌕</span>
        <input type="text" placeholder="Search files..." />
      </div>

      <div className="ws-file-section">
        <div className="ws-file-section-title">
          INPUTS
          <span>{files.inputsCount}</span>
        </div>
        {files.inputs.map((group) => (
          <div key={group.folder} className="ws-file-folder-block">
            <div className="ws-file-folder">📁 {group.folder}</div>
            {group.files.map((name) => (
              <button key={name} type="button" className="ws-file-item">
                {name}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="ws-file-section">
        <div className="ws-file-section-title">
          AI GENERATED
          <span>{files.generated.length}</span>
        </div>
        {files.generated.map((name) => (
          <button key={name} type="button" className="ws-file-item">
            {name}
          </button>
        ))}
      </div>

      <div className="ws-file-section">
        <div className="ws-file-section-title">
          ARTIFACTS
          <span>{files.artifacts.length}</span>
        </div>
        {files.artifacts.map((name) => (
          <div key={name} className="ws-artifact-item">
            📁 {name}
          </div>
        ))}
      </div>

      <div className="ws-storage">
        <span>Storage used</span>
        <strong>{storage.label}</strong>
        <div className="ws-storage-bar">
          <span style={{ width: `${storage.percent}%` }} />
        </div>
      </div>
    </aside>
  );
}

export default FileExplorer;
