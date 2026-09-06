import React, { useState, useEffect, useRef } from 'react';
import {
  uploadDocument,
  askQuestion,
  getDocumentInfo,
  clearKnowledgeBase,
} from './services/api';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [chunkCount, setChunkCount] = useState(0);
  const [statusMsg, setStatusMsg] = useState(null);
  const [history, setHistory] = useState([]);
  const fileInputRef = useRef(null);
  const threadEndRef = useRef(null);

  const refreshDocInfo = async () => {
    const res = await getDocumentInfo();
    if (res.success) setChunkCount(res.data.total_chunks || 0);
  };

  useEffect(() => {
    refreshDocInfo();
  }, []);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, loading]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setStatusMsg(null);
    const res = await uploadDocument(file);
    if (res.success) {
      setStatusMsg(`Indexed "${res.data.filename}" — ${res.data.chunks_created} chunks`);
      await refreshDocInfo();
    } else {
      setError(res.error);
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;
    const q = question.trim();
    setLoading(true);
    setError(null);
    setQuestion('');
    const res = await askQuestion(q);
    if (res.success) {
      setHistory((prev) => [
        ...prev,
        { question: q, answer: res.data.answer, sources: res.data.sources || [] },
      ]);
    } else {
      setError(res.error);
    }
    setLoading(false);
  };

  const handleClear = async () => {
    if (!window.confirm('Remove all documents from the index?')) return;
    setLoading(true);
    setError(null);
    const res = await clearKnowledgeBase();
    if (res.success) {
      setChunkCount(0);
      setHistory([]);
      setStatusMsg('Index cleared');
    } else {
      setError(res.error);
    }
    setLoading(false);
  };

  return (
    <div className="page">
      <header className="masthead">
        <div>
          <h1 className="masthead-title">
            Docu<span>Mind</span>
          </h1>
          <div className="masthead-sub">Personal document Q&A</div>
        </div>
        <div className={`index-tag ${chunkCount > 0 ? '' : 'empty'}`}>
          Index · <b>{chunkCount}</b> chunk{chunkCount === 1 ? '' : 's'}
        </div>
      </header>
      <div className="rule-thin" />

      <div className="grid">
        <aside className="col-left">
          <div className="section-label">Library</div>

          <div
            className={`drop ${uploading ? 'busy' : ''}`}
            onClick={() => !uploading && fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md"
              onChange={handleUpload}
              disabled={uploading}
            />
            <svg
              className="drop-icon"
              width="22" height="22" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.5"
            >
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
              <path d="M14 3v5h5" />
              <path d="M12 12v5M9.5 14.5 12 12l2.5 2.5" />
            </svg>
            <div className="drop-title">
              {uploading ? 'Indexing…' : 'Add a document'}
            </div>
            <div className="drop-meta">PDF / TXT / MD</div>
          </div>

          {statusMsg && <div className="notice">{statusMsg}</div>}
          {error && <div className="notice error">{error}</div>}

          <button className="btn-clear" onClick={handleClear} disabled={loading || chunkCount === 0}>
            Clear documents
          </button>

          <div className="method">
            <div className="section-label">How it works</div>
            <ol>
              <li>Upload a PDF, text or markdown file.</li>
              <li>The text is split and embedded into a local vector index.</li>
              <li>Questions are answered from those passages, with sources.</li>
            </ol>
          </div>
        </aside>

        <section className="col-right">
          <div className="thread-head">
            <h2>Transcript</h2>
            <p>Answers come only from your files.</p>
          </div>

          <div className="thread">
            {history.length === 0 && !loading && (
              <div className="empty">
                <h3>No documents added yet.</h3>
                <p>
                  Upload a PDF, TXT, or MD file on the left, then ask a question about it.
                </p>
                <div className="examples">
                  <div className="example">
                    <em>Lecture notes</em>
                    <span>What are the main points in this document?</span>
                  </div>
                  <div className="example">
                    <em>Research report</em>
                    <span>Summarise the key findings in three bullets.</span>
                  </div>
                  <div className="example">
                    <em>Policy document</em>
                    <span>What does it say about deadlines?</span>
                  </div>
                </div>
              </div>
            )}

            {history.map((item, idx) => (
              <article className="entry" key={idx}>
                <div className="entry-q">
                  <span>{item.question}</span>
                </div>
                <div className="entry-a">
                  <span>{item.answer}</span>
                </div>
                {item.sources?.length > 0 && (
                  <div className="sources">
                    <span className="sources-label">Sources</span>
                    {item.sources.map((s, i) => (
                      <span key={i} className="source">{s}</span>
                    ))}
                  </div>
                )}
              </article>
            ))}

            {loading && (
              <div className="working">
                <div className="bar"><span /></div>
                Looking through your documents…
              </div>
            )}
            <div ref={threadEndRef} />
          </div>

          <form className="composer" onSubmit={handleAsk}>
            <span className="caret">&gt;</span>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your documents"
              disabled={loading}
            />
            <button className="btn-send" type="submit" disabled={loading || !question.trim()}>
              Ask
            </button>
          </form>
        </section>
      </div>

      <div className="colophon">
        <span>DocuMind — retrieval-augmented document Q&amp;A</span>
        <span>React · FastAPI · Vector search</span>
      </div>
    </div>
  );
}

export default App;
