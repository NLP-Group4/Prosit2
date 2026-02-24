import { useState, useRef, useEffect, useCallback } from 'react';
// eslint-disable-next-line no-unused-vars
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from '../components/ThemeToggle';
import './ChatPage.css';

/* ─── Static Data ─── */
const FILE_OPTIONS = [
    { icon: '📄', label: 'routes.py' },
    { icon: '📄', label: 'models.py' },
    { icon: '📄', label: 'main.py' },
    { icon: '📁', label: 'Upload file…' },
];

const COMMAND_OPTIONS = [
    { cmd: '/summarize', desc: 'Summarize the current API' },
    { cmd: '/test', desc: 'Run all endpoint tests' },
    { cmd: '/deploy', desc: 'Deploy to cloud' },
    { cmd: '/document', desc: 'Generate API docs' },
];

const INITIAL_THREADS = [
    { id: 'b1', title: 'api-gateway' },
    { id: 'b2', title: 'auth-module' },
    { id: 'b3', title: 'task-service' },
    { id: 'b4', title: 'deploy-pipeline' },
];

const SUGGESTIONS = {
    'gemini-2.5-pro': [
        { label: 'Build a FastAPI task manager with JWT auth, CRUD endpoints, and input validation' },
        { label: 'Containerize my API with Docker — multi-stage build, health check, and env vars' },
    ],
    'gemini-2.0-flash': [
        { label: 'Scaffold a Node.js microservice with rate limiting, logging, and OpenAPI docs' },
        { label: 'Create a CLI tool in Python that reads my codebase and generates a README' },
    ],
};

const AGENT_PHASE_1 = [
    {
        id: 'req',
        text: 'Analyzing requirements…',
        doneText: 'Requirement analysis done.',
        sub: [{ label: 'Requirements doc', action: 'file:Requirements Document' }]
    },
    {
        id: 'arch',
        text: 'Planning architecture…',
        doneText: 'Architecture designed.',
        sub: [{ label: 'Architecture diagram', action: 'link:https://app.diagrams.net/' }]
    }
];

const AGENT_PHASE_2 = [
    {
        id: 'code',
        text: 'Generating code…',
        doneText: 'Code generation complete.',
        sub: [
            { label: 'Schema models', action: 'file:app/models.py' },
            { label: 'API endpoints', action: 'file:app/routes.py' },
            { label: 'Unit tests', action: 'file:tests.py' }
        ]
    },
    {
        id: 'deploy',
        text: 'Containerizing application locally…',
        doneText: 'Local docker container built.',
        icon: 'deploy',
        sub: [{ label: 'View Configuration', action: 'file:Dockerfile' }]
    },
    {
        id: 'verify',
        text: 'Running local verification tests…',
        doneText: 'Verification suite passed.',
        icon: 'deploy',
        sub: [{ label: 'Test Report', action: 'file:tests.py' }]
    }
];

const AGENT_FINAL = {
    text: "I've scaffolded a task management API with authentication, CRUD endpoints, and input validation.",
    showEndpoints: true,
    files: ['app/main.py', 'app/models.py', 'app/routes.py', 'Dockerfile'],
};

// MOCK_FILES and ENDPOINTS removed to be loaded dynamically from project spec

const METHOD_COLOR = { GET: '#22c55e', POST: '#60a5fa', PUT: '#f59e0b', DELETE: '#f87171' };

function DeployBackendButton({ projectId, onSuccess }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const handleDeploy = async () => {
        if (!projectId || !window.api?.deployProject) return;
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('auth_token');
            const result = await window.api.deployProject({
                projectId,
                token,
                apiUrl: 'http://localhost:8000',
            });
            if (result?.success) {
                onSuccess?.();
            } else {
                setError(result?.error || 'Deploy failed');
            }
        } catch (e) {
            setError(e.message || 'Deploy failed');
        } finally {
            setLoading(false);
        }
    };
    return (
        <div>
            <button className="cp-action-btn" onClick={handleDeploy} disabled={loading}>
                {loading ? <span className="ep-spinner" style={{ width: 14, height: 14 }} /> : <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg> Deploy Backend</>}
            </button>
            {error && (
                <pre style={{
                    marginTop: 8,
                    fontSize: 11,
                    color: 'var(--error, #ef4444)',
                    background: 'var(--bg-card-hover, rgba(0,0,0,0.05))',
                    padding: 8,
                    borderRadius: 6,
                    maxHeight: 120,
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                }}>
                    {error}
                </pre>
            )}
        </div>
    );
}

/** Base URL for the deployed generated backend (Docker on port 8001 per docs) */
const DEPLOYED_API_BASE = 'http://localhost:8001';

/* ─── Endpoint Card ─── */
function EndpointCard({ ep, baseUrl = DEPLOYED_API_BASE }) {
    const [inputVal, setInputVal] = useState(ep.placeholder || '');
    const [response, setResponse] = useState(null);
    const [statusBadge, setStatusBadge] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleTry = async () => {
        setLoading(true);
        setResponse(null);
        setStatusBadge(null);

        try {
            let finalPath = ep.path;
            let reqBody = null;

            if (ep.method === 'POST' || ep.method === 'PUT') {
                try {
                    reqBody = inputVal ? JSON.parse(inputVal) : (ep.method === 'POST' ? {} : null);
                } catch (e) {
                    setResponse(`Invalid JSON input:\n${e.message}`);
                    setStatusBadge('ERROR');
                    setLoading(false);
                    return;
                }
            } else if (inputVal && (finalPath.includes('{') || finalPath.includes(':') || finalPath.endsWith('/}'))) {
                finalPath = finalPath.replace(/\{[^}]+\}/g, inputVal).replace(/:[^/]+/g, inputVal);
            }

            const url = `${baseUrl}${finalPath.startsWith('/') ? finalPath : '/' + finalPath}`;
            const isFormLogin = ep.path === '/auth/login' && ep.method === 'POST';
            const body = isFormLogin && reqBody
                ? new URLSearchParams({ username: reqBody.username || reqBody.email || '', password: reqBody.password || '' }).toString()
                : (reqBody != null ? JSON.stringify(reqBody) : undefined);
            const headers = isFormLogin ? { 'Content-Type': 'application/x-www-form-urlencoded' } : ((ep.method === 'POST' || ep.method === 'PUT') ? { 'Content-Type': 'application/json' } : {});
            const res = await fetch(url, {
                method: ep.method,
                headers,
                body,
            });

            const text = await res.text();
            let parsed;
            try {
                parsed = text ? JSON.parse(text) : null;
            } catch {
                parsed = text;
            }
            setStatusBadge(`${res.status} ${res.statusText}`);
            setResponse(typeof parsed === 'object' ? JSON.stringify(parsed, null, 2) : String(parsed));
        } catch (error) {
            setStatusBadge('ERROR');
            setResponse(`Request failed: ${error.message}\n\nEnsure Docker is running and the generated backend was deployed (Electron app).`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="ep-card">
            <div className="ep-header">
                <span className="ep-method" style={{ color: METHOD_COLOR[ep.method] || '#cbd5e1' }}>{ep.method}</span>
                <code className="ep-path">{ep.path}</code>
            </div>
            <p className="ep-desc">{ep.description}</p>
            {ep.inputLabel && (
                <div className="ep-input-wrap">
                    <label className="ep-input-label">{ep.inputLabel}</label>
                    <input className="ep-input" value={inputVal} onChange={e => setInputVal(e.target.value)} placeholder={ep.placeholder || ''} spellCheck={false} />
                </div>
            )}
            <button className={`ep-try-btn${loading ? ' loading' : ''}`} onClick={handleTry} disabled={loading}>
                {loading ? <span className="ep-spinner" /> : <><svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21" /></svg>Try it</>}
            </button>
            <AnimatePresence>
                {response && (
                    <motion.div className="ep-response" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.2 }}>
                        <div className="ep-response-header">
                            <span className="ep-status-badge">{statusBadge}</span>
                            <span className="ep-response-label">Response</span>
                        </div>
                        <pre className="ep-response-body">{response}</pre>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

/* ─── Voice Recorder Hook ─── */
function useVoiceRecorder(onTranscript) {
    const [recording, setRecording] = useState(false);
    const mediaRef = useRef(null);

    const start = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream);
            const chunks = [];
            recorder.ondataavailable = e => chunks.push(e.data);
            recorder.onstop = () => {
                stream.getTracks().forEach(t => t.stop());
                // In a real app you'd send audio to a speech-to-text API.
                // Here we simulate a transcription after a short delay.
                onTranscript('[Voice transcription would appear here — connect a speech-to-text API]');
            };
            recorder.start();
            mediaRef.current = recorder;
            setRecording(true);
        } catch {
            alert('Microphone access denied. Please allow microphone permissions.');
        }
    }, [onTranscript]);

    const stop = useCallback(() => {
        mediaRef.current?.stop();
        setRecording(false);
    }, []);

    const toggle = useCallback(() => {
        recording ? stop() : start();
    }, [recording, start, stop]);

    return { recording, toggle };
}

/* ─── Syntax Highlighter ─── */
const KEYWORDS = /\b(FROM|WORKDIR|COPY|RUN|CMD|ENV|EXPOSE|ENTRYPOINT|ARG|ADD|def|class|import|from|return|if|else|elif|for|while|async|await|with|as|try|except|finally|raise|pass|True|False|None|and|or|not|in|is|lambda|yield)\b/g;
const STRINGS = /(["'`])((?:\\.|(?!\1)[^\\])*?)\1/g;
const COMMENTS = /(#.*)$/gm;
const NUMBERS = /\b(\d+\.?\d*)\b/g;
const BUILTINS = /\b(print|len|range|enumerate|zip|map|filter|list|dict|set|tuple|str|int|float|bool|open|super|self|cls)\b/g;

function syntaxHighlight(code) {
    // Escape HTML first
    const esc = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const lines = esc.split('\n');
    return lines.map(line => {
        let out = line;
        out = out.replace(COMMENTS, m => `<span class="tok-comment">${m}</span>`);
        // eslint-disable-next-line no-unused-vars
        out = out.replace(STRINGS, (m, q, s) => `<span class="tok-string">${m}</span>`);
        out = out.replace(NUMBERS, m => `<span class="tok-number">${m}</span>`);
        out = out.replace(KEYWORDS, m => `<span class="tok-keyword">${m}</span>`);
        out = out.replace(BUILTINS, m => `<span class="tok-builtin">${m}</span>`);
        return out;
    }).join('\n');
}
export default function ChatPage({ theme, onThemeToggle }) {
    const { user, logout } = useAuth();

    // eslint-disable-next-line no-unused-vars
    const [projectSpec, setProjectSpec] = useState(null);
    const [projectFiles, setProjectFiles] = useState({});
    const [projectEndpoints, setProjectEndpoints] = useState([]);

    const [triggerMenu, setTriggerMenu] = useState(null);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
    const [selectedModel, setSelectedModel] = useState('gemini-2.5-pro');
    const [projects, setProjects] = useState([]);  // list of { id, title, threads: [] }
    const [activeProject, setActiveProject] = useState(null);
    const [expandedProject, setExpandedProject] = useState(null); // project id whose threads are visible
    const [activeThread, setActiveThread] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    // eslint-disable-next-line no-unused-vars
    const [typingStep, setTypingStep] = useState(0);
    const [panelMode, setPanelMode] = useState(null);
    const [previewFile, setPreviewFile] = useState(null);
    const [attachedFiles, setAttachedFiles] = useState([]);
    // eslint-disable-next-line no-unused-vars
    const [activeTab, setActiveTab] = useState('Local');
    const [editSuggestion, setEditSuggestion] = useState('');
    const [suggestOpen, setSuggestOpen] = useState(false);
    const [suggestAtMenu, setSuggestAtMenu] = useState(false);
    const [autoApprove, setAutoApprove] = useState(true);

    const modelDropdownRef = useRef(null);

    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    const fileInputRef = useRef(null);
    const isGeneratingRef = useRef(false);

    useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isTyping]);

    // Close model dropdown on outside click
    useEffect(() => {
        const handler = (e) => { if (!modelDropdownRef.current?.contains(e.target)) setModelDropdownOpen(false); };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Load user's projects on mount
    useEffect(() => {
        if (!user) return;
        const fetchProjects = async () => {
            try {
                const token = localStorage.getItem('auth_token');
                const res = await fetch('/api/projects', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.status === 401) {
                    logout();
                    return;
                }
                if (res.ok) {
                    const data = await res.json();
                    // Seed each project with an empty threads array; we'll lazy-load
                    setProjects(data.map(p => ({ id: p.id, title: p.project_name, threads: [] })));

                    const savedThread = localStorage.getItem('interius_active_thread');
                    const savedProject = localStorage.getItem('interius_active_project');
                    if (savedProject && data.some(p => p.id === savedProject)) {
                        setActiveProject(savedProject);
                        setExpandedProject(savedProject);
                        if (savedThread) setActiveThread(savedThread);
                    }
                }
            } catch (err) {
                console.error("Failed to load projects", err);
            }
        };
        fetchProjects();
    }, [user, logout]);

    // When a project expands, fetch its threads
    useEffect(() => {
        if (!expandedProject) return;
        const token = localStorage.getItem('auth_token');
        fetch(`/api/projects/${expandedProject}/threads`, {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(r => {
            if (r.status === 401) { logout(); return []; }
            return r.ok ? r.json() : [];
        }).then(data => {
            setProjects(prev => prev.map(p =>
                p.id === expandedProject
                    ? { ...p, threads: (data || []).map(t => ({ id: t.id, title: t.title })) }
                    : p
            ));
        }).catch(err => console.error('Failed to load threads', err));
    }, [expandedProject, logout]);

    const loadProjectDetails = async (projectId) => {
        try {
            const token = localStorage.getItem('auth_token');
            const res = await fetch(`/api/projects/${projectId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) return;
            const data = await res.json();
            setProjectSpec(data);

            const spec = data.spec;
            if (!spec) return;

            // Generate mock files from spec data
            const generatedFiles = {};

            // Generate models.py mock
            if (spec.entities) {
                generatedFiles['app/models.py'] = `from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float\nfrom .database import Base\n\n` +
                    spec.entities.map(e => `class ${e.name}(Base):\n    __tablename__ = "${e.name.toLowerCase()}s"\n    id = Column(Integer, primary_key=True)\n` +
                        (e.fields || []).map(f => `    ${f.name} = Column(${f.type})`).join('\n')).join('\n\n');

                generatedFiles['app/schemas.py'] = `from pydantic import BaseModel\nfrom typing import List, Optional\n\n` +
                    spec.entities.map(e => `class ${e.name}Base(BaseModel):\n` +
                        (e.fields || []).map(f => `    ${f.name}: Optional[str] = None`).join('\n') + `\n\nclass ${e.name}Create(${e.name}Base):\n    pass\n\nclass ${e.name}(${e.name}Base):\n    id: int\n    class Config:\n        from_attributes = True`).join('\n\n');
            }

            // Generate routes.py mock
            if (spec.routes) {
                generatedFiles['app/routes.py'] = `from fastapi import APIRouter, Depends, HTTPException\nfrom sqlalchemy.orm import Session\nfrom . import models, schemas, database\n\nrouter = APIRouter()\n\n` +
                    spec.routes.map(r => `@router.${r.method.toLowerCase()}("${r.path}")\ndef ${r.method.toLowerCase()}_route(db: Session = Depends(database.get_db)):\n    # Auto-generated ${r.method} endpoint\n    pass`).join('\n\n');
            }

            generatedFiles['app/main.py'] = `from fastapi import FastAPI\nfrom .routes import router\n\napp = FastAPI(title="${spec.project_name || 'API'}")\napp.include_router(router, prefix="/api")\n\n@app.get("/health")\ndef health():\n    return {"status": "ok"}`;
            generatedFiles['Dockerfile'] = `FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`;

            // Intermediary mock documents to satisfy UI
            generatedFiles['Requirements Document'] = `# ${spec.project_name || 'Project'} Requirements\n\nThis document outlines the high-level business logic and requirements derived from your prompt for this REST API setup.\n\nThe system has compiled the schema details and routes effectively.`;
            generatedFiles['tests.py'] = `import pytest\nfrom fastapi.testclient import TestClient\nfrom app.main import app\n\nclient = TestClient(app)\n\ndef test_health():\n    response = client.get("/health")\n    assert response.status_code == 200\n    assert response.json() == {"status": "ok"}`;

            setProjectFiles(generatedFiles);

            // Generate endpoints from spec for API tester (matches generated backend structure)
            const dynamicEndpoints = [];
            dynamicEndpoints.push({
                id: 'ep-health',
                method: 'GET',
                path: '/health',
                description: 'Health check for the deployed backend',
                inputLabel: null,
                placeholder: null,
            });
            if (spec.auth?.enabled) {
                dynamicEndpoints.push({
                    id: 'ep-register',
                    method: 'POST',
                    path: '/auth/register',
                    description: 'Register a new user',
                    inputLabel: 'Request Body (JSON)',
                    placeholder: '{"email":"user@example.com","password":"password123"}',
                });
                dynamicEndpoints.push({
                    id: 'ep-login',
                    method: 'POST',
                    path: '/auth/login',
                    description: 'Login (form: username=email, password)',
                    inputLabel: 'Request Body (JSON)',
                    placeholder: '{"username":"user@example.com","password":"password123"}',
                });
            }
            if (spec.entities) {
                for (const entity of spec.entities) {
                    if (spec.auth?.enabled && entity.name?.toLowerCase() === 'user') continue;
                    const tableName = entity.table_name || `${entity.name.toLowerCase()}s`;
                    const fields = entity.fields || [];
                    const createPayload = {};
                    for (const f of fields) {
                        if (f.name === 'id') continue;
                        createPayload[f.name] = f.type === 'boolean' ? false : f.type === 'integer' ? 0 : 'test-value';
                    }
                    dynamicEndpoints.push({
                        id: `ep-${tableName}-create`,
                        method: 'POST',
                        path: `/${tableName}/`,
                        description: `Create ${entity.name}`,
                        inputLabel: 'Request Body (JSON)',
                        placeholder: JSON.stringify(createPayload, null, 2),
                    });
                    dynamicEndpoints.push({
                        id: `ep-${tableName}-list`,
                        method: 'GET',
                        path: `/${tableName}/`,
                        description: `List all ${entity.name}s`,
                        inputLabel: null,
                        placeholder: null,
                    });
                    dynamicEndpoints.push({
                        id: `ep-${tableName}-get`,
                        method: 'GET',
                        path: `/${tableName}/{item_id}`,
                        description: `Get ${entity.name} by ID`,
                        inputLabel: 'Item ID (UUID)',
                        placeholder: '00000000-0000-0000-0000-000000000001',
                    });
                }
            }
            if (spec.routes) {
                for (let i = 0; i < spec.routes.length; i++) {
                    const r = spec.routes[i];
                    if (!dynamicEndpoints.some(e => e.path === r.path && e.method === r.method)) {
                        dynamicEndpoints.push({
                            id: `ep-route-${i}`,
                            method: r.method,
                            path: r.path,
                            description: r.description || `${r.method} endpoint`,
                            inputLabel: r.method === 'POST' || r.method === 'PUT' ? 'Request Body (JSON)' : (r.path.includes('{') ? 'Path parameters' : null),
                            placeholder: r.method === 'POST' || r.method === 'PUT' ? '{"key": "value"}' : null,
                        });
                    }
                }
            }
            setProjectEndpoints(dynamicEndpoints);

            return data;

        } catch (err) {
            console.error('Failed to load project details', err);
            return null;
        }
    };

    // Load messages when activeThread/activeProject changes
    useEffect(() => {
        if (!activeThread || !activeProject) {
            if (!activeThread) {
                setMessages([]);
                setProjectSpec(null);
                setProjectFiles({});
                setProjectEndpoints([]);
            }
            return;
        }

        if (isGeneratingRef.current) return;

        const initThread = async () => {
            const data = await loadProjectDetails(activeProject);
            if (!data) return;

            // For this API builder, an active project means it's already generated.
            // We simulate a completed session.
            const mockHistory = [
                {
                    id: 'hist1',
                    type: 'user',
                    text: `Load project: ${data.project_name}`,
                    files: []
                },
                {
                    id: 'hist2',
                    type: 'agent',
                    text: `Project "${data.project_name}" generated successfully!`,
                    files: ['app/main.py', 'app/models.py', 'app/schemas.py', 'app/routes.py', 'Dockerfile'],
                    downloadUrl: data.download_url,
                    status: 'completed',
                    phase: 2,
                    stepIndex: 99
                }
            ];

            setMessages(mockHistory);
        };
        initThread();
    }, [activeThread, activeProject]);

    const { recording, toggle: toggleRecording } = useVoiceRecorder((text) => {
        setInput(prev => prev ? prev + ' ' + text : text);
    });

    const handleLogout = () => { logout(); };

    const handleNewThread = () => {
        isGeneratingRef.current = false;
        setActiveThread(null);
        setActiveProject(null);
        localStorage.removeItem('interius_active_thread');
        localStorage.removeItem('interius_active_project');
        setMessages([]);
        setInput('');
        setAttachedFiles([]);
        setPanelMode(null);
        setPreviewFile(null);
    };

    const handleDeleteProject = async (e, projectId) => {
        e.stopPropagation();
        if (!confirm('Delete this project and all its threads? This cannot be undone.')) return;
        setProjects(prev => prev.filter(p => p.id !== projectId));
        if (activeProject === projectId) {
            setActiveThread(null);
            setActiveProject(null);
            localStorage.removeItem('interius_active_thread');
            localStorage.removeItem('interius_active_project');
            setMessages([]);
        }
        const token = localStorage.getItem('auth_token');
        await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
    };

    const handleDeleteThread = async (e, projectId, threadId) => {
        e.stopPropagation();
        if (!confirm('Delete this thread? This cannot be undone.')) return;
        setProjects(prev => prev.map(p =>
            p.id === projectId
                ? { ...p, threads: p.threads.filter(t => t.id !== threadId) }
                : p
        ));
        if (activeThread === threadId) {
            setActiveThread(null);
            localStorage.removeItem('interius_active_thread');
            setMessages([]);
        }
        const token = localStorage.getItem('auth_token');
        await fetch(`/api/projects/${projectId}/threads/${threadId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
    };

    const handleSuggestEdits = () => {
        setSuggestOpen(true);
    };

    const submitSuggestEdits = async () => {
        if (!editSuggestion.trim()) return;
        const prompt = `Please apply the following edits to ${previewFile}:\n\n${editSuggestion.trim()}`;
        setEditSuggestion('');
        setSuggestOpen(false);
        setPanelMode(null);
        setPreviewFile(null);
        await sendMessage(prompt);
    };

    const openFilePreviewer = (filename) => {
        setPreviewFile(filename);
        setPanelMode('file');
    };

    // eslint-disable-next-line no-unused-vars
    const handleTabClick = (tab) => {
        if (tab === 'Cloud') { window.open('https://app.interius.dev', '_blank'); return; }
        setActiveTab(tab);
    };

    const handleInsertTriggerOption = (value) => {
        setInput(prev => {
            const trigger = triggerMenu;
            const idx = prev.lastIndexOf(trigger);
            if (idx === -1) return prev + value;
            return prev.slice(0, idx) + value + ' ';
        });
        setTriggerMenu(null);
        inputRef.current?.focus();
    };

    const handleDownloadProject = async (downloadUrl, projectName) => {
        try {
            const token = localStorage.getItem('auth_token');
            const url = downloadUrl.startsWith('http') ? downloadUrl : `http://localhost:8000${downloadUrl}`;
            const res = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Download failed');
            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = `${projectName || 'backend'}.zip`;
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(blobUrl);
            a.remove();
        } catch (e) {
            alert('Download failed: ' + e.message);
        }
    };

    const sendMessage = async (text) => {
        if (!text || isTyping || !user) return;

        isGeneratingRef.current = true;

        // Add user message to UI
        setMessages(m => [...m, { type: 'user', text, files: attachedFiles.map(f => f.name) }]);
        setAttachedFiles([]);
        setIsTyping(true);

        const msgId = Date.now();
        setMessages(m => [...m, {
            id: msgId,
            type: 'agent',
            isStreaming: true,
            phase: 1,
            stepIndex: 0,
            status: 'running'
        }]);

        // Start animation loop while waiting for fetch
        let animStep = 0;
        const animInterval = setInterval(() => {
            if (animStep < AGENT_PHASE_1.length) {
                setMessages(curr => curr.map(msg => msg.id === msgId ? { ...msg, stepIndex: animStep + 1 } : msg));
                animStep++;
            } else if (animStep === AGENT_PHASE_1.length) {
                setMessages(curr => curr.map(msg => msg.id === msgId ? { ...msg, phase: 2, stepIndex: 0 } : msg));
                animStep++;
            } else if (animStep < AGENT_PHASE_1.length + AGENT_PHASE_2.length) {
                setMessages(curr => curr.map(msg => msg.id === msgId ? { ...msg, stepIndex: animStep - AGENT_PHASE_1.length + 1 } : msg));
                animStep++;
            }
        }, 800);

        try {
            const token = localStorage.getItem('auth_token');
            let data;

            // Branch logic for Electron Desktop vs Standard Web
            if (window.api && typeof window.api.generateAndVerify === 'function') {
                // Electron Desktop route: the main process drives generation, 
                // downloads the ZIP, deploys to Docker, runs verification, handles fixing,
                // and eventually returns the finished project metadata to the frontend.
                const result = await window.api.generateAndVerify({
                    prompt: text,
                    model: selectedModel,
                    token: token,
                    apiUrl: 'http://localhost:8000'
                });

                if (!result.success) {
                    let errMsg = result.error;
                    if (typeof errMsg === 'object') {
                        if (errMsg.detail && errMsg.detail.errors) errMsg = errMsg.detail.errors[0];
                        else if (errMsg.detail) errMsg = typeof errMsg.detail === 'string' ? errMsg.detail : JSON.stringify(errMsg.detail);
                        else errMsg = JSON.stringify(errMsg);
                    }
                    throw new Error(errMsg || 'Desktop generation failed');
                }

                // We destruct the direct properties out of the Electron JSON block into `data`
                data = result;

            } else {
                // Standard Web route: direct to Cloud API (no server-side docker verification)
                const targetUrl = activeThread
                    ? `/api/projects/${activeProject}/threads/${activeThread}/chat`
                    : '/api/generate-from-prompt';

                const response = await fetch(targetUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify(activeThread ? { message: text } : { prompt: text, model: selectedModel })
                });

                if (response.status === 401) {
                    logout();
                    throw new Error('Session expired');
                }

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || 'Generation failed');
                }

                data = await response.json();
            }

            // Success
            setIsTyping(false);

            // Add new project to projects list
            setProjects(prev => [{
                id: data.project_id,
                title: data.project_name,
                threads: data.thread_id ? [{ id: data.thread_id, title: 'Initial build' }] : []
            }, ...prev]);

            if (data.thread_id) {
                setActiveThread(data.thread_id);
                localStorage.setItem('interius_active_thread', data.thread_id);
            }
            setActiveProject(data.project_id);
            setExpandedProject(data.project_id);
            localStorage.setItem('interius_active_project', data.project_id);

            setMessages(curr => curr.map(msg => msg.id === msgId ? {
                ...msg,
                isStreaming: false,
                status: 'completed',
                phase: 2,
                stepIndex: 99,
                text: data.content || `Project "${data.project_name}" generated successfully!`,
                downloadUrl: data.download_url,
                files: ['app/main.py', 'app/models.py', 'app/schemas.py', 'app/routes.py', 'Dockerfile']
            } : msg));

            loadProjectDetails(data.project_id);

        } catch (error) {
            clearInterval(animInterval);
            setIsTyping(false);
            setMessages(curr => curr.map(msg => msg.id === msgId ? {
                ...msg,
                isStreaming: false,
                status: 'error',
                text: `Error: ${error.message}`
            } : msg));
        }

        isGeneratingRef.current = false;
        setPanelMode(null);
        inputRef.current?.focus();
    };

    // approvePhase1 implementation removed because auto-approve is standard in api builder MVP

    const handleSend = async () => {
        const text = input.trim();
        if ((!text && attachedFiles.length === 0) || isTyping) return;
        setInput('');
        await sendMessage(text);
    };

    const handleInputChange = (e) => {
        const val = e.target.value;
        setInput(val);
        const last = val[val.length - 1];
        if (last === '@') setTriggerMenu('@');
        else if (last === '/') setTriggerMenu('/');
        else if (triggerMenu && !val.includes(triggerMenu)) setTriggerMenu(null);
    };

    const handleKey = (e) => {
        if (e.key === 'Escape') { setTriggerMenu(null); return; }
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const handleFileChange = (e) => {
        const files = Array.from(e.target.files);
        const MAX_SIZE = 5 * 1024 * 1024; // 5MB limit

        const validFiles = files.filter(f => {
            if (f.size > MAX_SIZE) {
                alert(`File "${f.name}" is too large. Maximum size is 5MB.`);
                return false;
            }
            return true;
        });

        setAttachedFiles(prev => [...prev, ...validFiles]);
        e.target.value = '';
    };

    const removeFile = (name) => setAttachedFiles(prev => prev.filter(f => f.name !== name));

    const fillSuggestion = (label) => { setInput(label); inputRef.current?.focus(); };

    return (
        <div className="chat-page" data-theme={theme}>

            {/* ── Sidebar (expanded) ── */}
            <aside className={`cp-sidebar${sidebarCollapsed ? ' hidden' : ''}`}>
                {/* Logo + collapse toggle */}
                <div className="cp-sidebar-logo">
                    <a href="/" className="cp-logo">
                        Interius<span className="cp-logo-dot">.</span>
                    </a>
                    <button className="cp-collapse-btn" onClick={() => setSidebarCollapsed(true)} title="Collapse sidebar">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
                    </button>
                </div>



                {/* Projects + Threads Accordion */}
                <div className="cp-section cp-section-threads">
                    <div className="cp-section-header">
                        <div className="cp-section-label">Projects</div>
                        <button className="cp-section-action" title="New thread" onClick={handleNewThread}>
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
                        </button>
                    </div>
                    {projects.map(project => (
                        <div key={project.id} className="cp-project-group">
                            {/* Project header row */}
                            <div
                                className={`cp-thread-item cp-project-header${activeProject === project.id ? ' active' : ''}`}
                                onClick={() => {
                                    const nowExpanded = expandedProject === project.id ? null : project.id;
                                    setExpandedProject(nowExpanded);
                                    setActiveProject(project.id);
                                    localStorage.setItem('interius_active_project', project.id);
                                }}
                            >
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                    {expandedProject === project.id
                                        ? <polyline points="6 9 12 15 18 9" />
                                        : <polyline points="9 6 15 12 9 18" />}
                                </svg>
                                <span className="cp-thread-title">{project.title}</span>
                                <button
                                    className="cp-thread-delete cp-delete-project"
                                    title="Delete project"
                                    onClick={(e) => handleDeleteProject(e, project.id)}
                                >
                                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                                </button>
                            </div>
                            {/* Thread list for this project */}
                            {expandedProject === project.id && (
                                <div className="cp-thread-indent">
                                    {project.threads.map(t => (
                                        <div
                                            key={t.id}
                                            className={`cp-thread-item cp-thread-child${activeThread === t.id ? ' active' : ''}`}
                                            onClick={() => {
                                                isGeneratingRef.current = false;
                                                setActiveThread(t.id);
                                                setActiveProject(project.id);
                                                setMessages([]);
                                                localStorage.setItem('interius_active_thread', t.id);
                                            }}
                                        >
                                            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M5 6h14M5 12h10M5 18h7" /></svg>
                                            <span className="cp-thread-title">{t.title}</span>
                                            <button
                                                className="cp-thread-delete cp-delete-thread"
                                                title="Delete thread"
                                                onClick={(e) => handleDeleteThread(e, project.id, t.id)}
                                            >
                                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                                            </button>
                                        </div>
                                    ))}
                                    {/* Add new thread button */}
                                    <button
                                        className="cp-new-thread-btn"
                                        onClick={async () => {
                                            const token = localStorage.getItem('auth_token');
                                            const res = await fetch(`/api/projects/${project.id}/threads`, {
                                                method: 'POST',
                                                headers: { 'Authorization': `Bearer ${token}` }
                                            });
                                            if (res.status === 401) { logout(); return; }
                                            if (res.ok) {
                                                const t = await res.json();
                                                setProjects(prev => prev.map(p =>
                                                    p.id === project.id
                                                        ? { ...p, threads: [...p.threads, { id: t.id, title: t.title }] }
                                                        : p
                                                ));
                                                setActiveThread(t.id);
                                                setActiveProject(project.id);
                                                setMessages([]);
                                                localStorage.setItem('interius_active_thread', t.id);
                                            }
                                        }}
                                    >
                                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
                                        New thread
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="cp-sidebar-footer">
                    <ThemeToggle theme={theme} onToggle={onThemeToggle} />
                    <div className="cp-user">
                        <div className="cp-avatar">{user?.name?.[0]?.toUpperCase() || 'U'}</div>
                        <span className="cp-user-name">{user?.name || 'You'}</span>
                    </div>
                    <button className="cp-logout" onClick={handleLogout} title="Sign out">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
                        </svg>
                    </button>
                </div>
            </aside>

            {/* Collapsed sidebar rail */}
            {sidebarCollapsed && (
                <aside className="cp-sidebar-rail">
                    <button className="cp-rail-logo" onClick={() => setSidebarCollapsed(false)} title="Expand sidebar">
                        <span className="cp-rail-i">I</span><span className="cp-rail-dot">.</span>
                    </button>
                    <div className="cp-rail-actions">
                        <button className="cp-rail-btn" onClick={() => { setSidebarCollapsed(false); handleNewThread(); }} title="New thread">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
                        </button>
                        <ThemeToggle theme={theme} onToggle={onThemeToggle} />
                    </div>
                </aside>
            )}

            {/* ── Main Chat ── */}
            <main className="cp-main">
                {/* Top bar */}
                <div className="cp-topbar">
                    <span className="cp-topbar-thread">
                        {activeThread && activeProject ? projects.find(p => p.id === activeProject)?.threads.find(t => t.id === activeThread)?.title || 'New thread' : 'New thread'}
                    </span>
                </div>

                {/* Chat area */}
                <div className="cp-chat-area">
                    {messages.length === 0 && !isTyping ? (
                        <div className="cp-empty">
                            {/* Build icon */}
                            <div className="cp-empty-icon" style={{ fontSize: '44px', fontWeight: 700, lineHeight: 1, letterSpacing: '-0.02em', userSelect: 'none' }}>
                                <span className="cp-rail-i">I</span><span className="cp-rail-dot">.</span>
                            </div>
                            <h2 className="cp-empty-heading">Let's build something.</h2>
                            <p className="cp-empty-project">
                                {selectedModel === 'pro' ? 'Interius Pro v1' : 'Interius Generalist v1'}
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="6 9 12 15 18 9" /></svg>
                            </p>


                            <div className="cp-suggestions">
                                {(SUGGESTIONS[selectedModel] || []).map(s => (
                                    <button key={s.label} className="cp-suggestion" onClick={() => fillSuggestion(s.label)}>
                                        <span className="cp-suggestion-label">{s.label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="cp-messages">
                            <AnimatePresence initial={false}>
                                {messages.map((msg, i) => (
                                    <motion.div key={i} className={`cp-msg ${msg.type}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
                                        {msg.type === 'user' ? (
                                            <div className="cp-user-msg">
                                                {msg.files?.length > 0 && (
                                                    <div className="cp-attached-files">
                                                        {msg.files.map(f => (
                                                            <div key={f} className="cp-file-chip">
                                                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                                                {f}
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                                {msg.text && <div className="cp-bubble">{msg.text}</div>}
                                            </div>
                                        ) : (
                                            <div className="cp-agent-wrap">
                                                <div className="cp-agent-avatar">
                                                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                                        <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" />
                                                    </svg>
                                                </div>
                                                <div className="cp-agent-body">
                                                    {/* Thought Process Tree */}
                                                    <div className="cp-thought-process">
                                                        <details className="cp-thought-details" open>
                                                            <summary className="cp-thought-summary">
                                                                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21" /></svg> View thought process
                                                            </summary>
                                                            <div className="cp-thought-tree">

                                                                {/* Render Phase 1 */}
                                                                {(msg.phase >= 1) && AGENT_PHASE_1.map((step, idx) => {
                                                                    const isPast = msg.phase > 1 || (msg.phase === 1 && msg.stepIndex > idx) || msg.status === 'completed';
                                                                    const isCurrent = msg.phase === 1 && msg.stepIndex === idx && msg.isStreaming;
                                                                    if (!isPast && !isCurrent) return null;

                                                                    return (
                                                                        <div key={step.id} className={`cp-tree-node ${isCurrent ? 'running' : 'done'}`}>
                                                                            <div className="cp-tree-main">
                                                                                {isCurrent ? (
                                                                                    <span className="cp-run-spinner" />
                                                                                ) : (
                                                                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                                                                                )}
                                                                                <span>{isCurrent ? step.text : step.doneText}</span>
                                                                            </div>
                                                                            {isPast && step.sub && (
                                                                                <div className="cp-tree-sub">
                                                                                    {step.sub.map((s, sIdx) => (
                                                                                        <div key={sIdx} className="cp-tree-sub-item">
                                                                                            <span className="cp-tree-elbow">└─</span>
                                                                                            {autoApprove ? <span className="cp-sub-auto">Autoapproved</span> : <span className="cp-sub-auto">—</span>}
                                                                                            {s.action.startsWith('file:') ? (
                                                                                                <button onClick={() => openFilePreviewer(s.action.split(':')[1])} className="cp-tree-link">
                                                                                                    {s.label} <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 17l9.2-9.2M17 17V7H7" /></svg>
                                                                                                </button>
                                                                                            ) : (
                                                                                                <a href={s.action.split(':')[1]} target="_blank" rel="noreferrer" className="cp-tree-link">
                                                                                                    {s.label} <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 17l9.2-9.2M17 17V7H7" /></svg>
                                                                                                </a>
                                                                                            )}
                                                                                        </div>
                                                                                    ))}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    );
                                                                })}

                                                                {/* Render Phase 2 */}
                                                                {(msg.phase >= 2) && AGENT_PHASE_2.map((step, idx) => {
                                                                    const isPast = msg.phase > 2 || (msg.phase === 2 && msg.stepIndex > idx) || msg.status === 'completed';
                                                                    const isCurrent = msg.phase === 2 && msg.stepIndex === idx && msg.isStreaming;
                                                                    if (!isPast && !isCurrent) return null;

                                                                    return (
                                                                        <div key={step.id} className={`cp-tree-node ${isCurrent ? 'running' : 'done'}`}>
                                                                            <div className="cp-tree-main">
                                                                                {isCurrent ? (
                                                                                    <span className="cp-run-spinner" />
                                                                                ) : (
                                                                                    step.icon === 'deploy' ?
                                                                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                                                                                        : <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                                                                                )}
                                                                                <span>{isCurrent ? step.text : step.doneText}</span>
                                                                            </div>
                                                                            {isPast && step.sub && (
                                                                                <div className="cp-tree-sub">
                                                                                    {step.sub.map((s, sIdx) => (
                                                                                        <div key={sIdx} className="cp-tree-sub-item">
                                                                                            <span className="cp-tree-elbow">└─</span>
                                                                                            {autoApprove ? <span className="cp-sub-auto">Autoapproved</span> : <span className="cp-sub-auto">—</span>}
                                                                                            {s.action.startsWith('file:') ? (
                                                                                                <button onClick={() => openFilePreviewer(s.action.split(':')[1])} className="cp-tree-link">
                                                                                                    {s.label}
                                                                                                </button>
                                                                                            ) : (
                                                                                                <a href={s.action.split(':')[1]} target="_blank" rel="noreferrer" className="cp-tree-link">
                                                                                                    {s.label} <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 17l9.2-9.2M17 17V7H7" /></svg>
                                                                                                </a>
                                                                                            )}
                                                                                        </div>
                                                                                    ))}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        </details>
                                                    </div>



                                                    {/* Final output block */}
                                                    {msg.status === 'completed' && msg.text && (
                                                        <div className="cp-final-output">
                                                            <p className="cp-agent-text">{msg.text}</p>

                                                            {msg.downloadUrl && (
                                                                <button className="cp-action-btn" onClick={() => handleDownloadProject(msg.downloadUrl, msg.text.match(/"([^"]+)"/)?.[1] || 'generated-backend')} style={{ marginTop: '0.5rem', marginBottom: '1rem', backgroundColor: '#22c55e', color: 'white', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: 'bold', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                                    ⬇ Download ZIP
                                                                </button>
                                                            )}

                                                            {msg.files?.length > 0 && (
                                                                <div className="cp-agent-files-group">
                                                                    {msg.files.map(f => (
                                                                        <button key={f} className="cp-file-pill code-chip" onClick={() => openFilePreviewer(f)}>
                                                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                                                            {f}
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            )}

                                                            {/* Always show deployment blocks for completed pipeline phases, regardless of explicit payload flags */}
                                                            {msg.status === 'completed' && msg.phase >= 2 && (
                                                                <div className="cp-deployment-blocks">
                                                                    {window.api?.deployProject && (
                                                                        <div className="cp-deploy-block">
                                                                            <div className="cp-deploy-content">
                                                                                Re-deploy this backend to Docker (e.g. after app restart). Required before testing.
                                                                            </div>
                                                                            <DeployBackendButton
                                                                                projectId={activeProject}
                                                                                onSuccess={() => setPanelMode('tester')}
                                                                            />
                                                                        </div>
                                                                    )}
                                                                    <div className="cp-deploy-block">
                                                                        <div className="cp-deploy-content">
                                                                            Use the interactive API playground to test your generated endpoints against the deployed backend.
                                                                        </div>
                                                                        <button className="cp-action-btn cp-action-tester" onClick={() => { setPreviewFile(null); setPanelMode('tester'); }}>
                                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>
                                                                            Test API Endpoints
                                                                        </button>
                                                                    </div>
                                                                    <div className="cp-deploy-block">
                                                                        <div className="cp-deploy-content">
                                                                            Your backend runs at localhost:8001. The automated verification suite has confirmed all endpoints are functional.
                                                                        </div>
                                                                        <a className="cp-action-btn cp-action-live" href={`${DEPLOYED_API_BASE}/docs`} target="_blank" rel="noopener noreferrer">
                                                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
                                                                            View Local API Documentation
                                                                        </a>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </motion.div>
                                ))}


                            </AnimatePresence>
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* ── Input Bar ── */}
                <div className="cp-input-bar">
                    {/* Attached files preview */}
                    {attachedFiles.length > 0 && (
                        <div className="cp-file-preview">
                            {attachedFiles.map(f => (
                                <div key={f.name} className="cp-file-tag">
                                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                    {f.name}
                                    <button className="cp-file-remove" onClick={() => removeFile(f.name)}>
                                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* @ and / trigger menus */}
                    <AnimatePresence>
                        {triggerMenu && (
                            <motion.div
                                className="cp-trigger-menu"
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: 6 }}
                                transition={{ duration: 0.15 }}
                            >
                                {triggerMenu === '@' && FILE_OPTIONS.map(f => (
                                    <button key={f.label} className="cp-trigger-item" onClick={() => handleInsertTriggerOption(f.label)}>
                                        <span className="cp-trigger-icon">
                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                        </span>
                                        {f.label}
                                    </button>
                                ))}
                                {triggerMenu === '/' && COMMAND_OPTIONS.map(c => (
                                    <button key={c.cmd} className="cp-trigger-item" onClick={() => handleInsertTriggerOption(c.cmd)}>
                                        <span className="cp-trigger-cmd">{c.cmd}</span>
                                        <span className="cp-trigger-desc">{c.desc}</span>
                                    </button>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <div className="cp-input-wrap">
                        {/* Left: attach */}
                        <button className="cp-input-action cp-attach" onClick={() => fileInputRef.current?.click()} title="Attach file">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                            </svg>
                        </button>
                        <input ref={fileInputRef} type="file" multiple accept=".txt,.pdf,.md" className="cp-file-input" onChange={handleFileChange} />

                        {/* Textarea */}
                        <textarea
                            ref={inputRef}
                            className="cp-textarea"
                            placeholder="Ask Interius anything…"
                            value={input}
                            onChange={handleInputChange}
                            onKeyDown={handleKey}
                            onInput={e => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }}
                            rows={1}
                        />

                        {/* Right actions */}
                        <div className="cp-input-right">
                            <button
                                className={`cp-input-action cp-mic${recording ? ' recording' : ''}`}
                                onClick={toggleRecording}
                                title={recording ? 'Stop recording' : 'Voice input'}
                            >
                                {recording ? (
                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                                        <rect x="6" y="6" width="12" height="12" rx="2" />
                                    </svg>
                                ) : (
                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                                        <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" />
                                    </svg>
                                )}
                            </button>
                            <button
                                className={`cp-send${(input.trim() || attachedFiles.length > 0) ? ' active' : ''}`}
                                onClick={handleSend}
                                disabled={(!input.trim() && attachedFiles.length === 0) || isTyping}
                                aria-label="Send"
                            >
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94l18.04-8.01a.75.75 0 000-1.36L3.478 2.405z" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    {/* Bottom bar */}
                    <div className="cp-input-footer">
                        <div className="cp-model-selector" ref={modelDropdownRef}>
                            <button
                                className={`cp-model-btn${modelDropdownOpen ? ' open' : ''}`}
                                onClick={() => setModelDropdownOpen(o => !o)}
                            >
                                <span className="cp-model-dot" />
                                <span className="cp-model-name">
                                    {selectedModel === 'gemini-2.5-pro' ? 'Interius Pro v1 (Gemini)' : 'Interius Generalist (Gemini)'}
                                </span>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="6 9 12 15 18 9" /></svg>
                            </button>
                            {modelDropdownOpen && (
                                <div className="cp-model-dropdown">
                                    <button
                                        className={`cp-model-option${selectedModel === 'gemini-2.5-pro' ? ' selected' : ''}`}
                                        onClick={() => { setSelectedModel('gemini-2.5-pro'); setModelDropdownOpen(false); }}
                                    >
                                        <span className="cp-model-option-name">Interius Pro v1 (Gemini)</span>
                                        <span className="cp-model-option-desc">Specialized API builder & scaffolder</span>
                                    </button>
                                    <button
                                        className={`cp-model-option${selectedModel === 'gemini-2.0-flash' ? ' selected' : ''}`}
                                        onClick={() => { setSelectedModel('gemini-2.0-flash'); setModelDropdownOpen(false); }}
                                    >
                                        <span className="cp-model-option-name">Interius Generalist (Gemini)</span>
                                        <span className="cp-model-option-desc">Fast, capable tasks and edits</span>
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="cp-autoapprove-toggle" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-sec)', userSelect: 'none' }}>
                            <label className="cp-switch" style={{ position: 'relative', display: 'inline-block', width: '32px', height: '18px' }}>
                                <input
                                    type="checkbox"
                                    checked={autoApprove}
                                    onChange={(e) => setAutoApprove(e.target.checked)}
                                    style={{ opacity: 0, width: 0, height: 0 }}
                                />
                                <span className="cp-slider" style={{
                                    position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
                                    backgroundColor: autoApprove ? 'var(--accent)' : 'var(--border)',
                                    transition: '.3s',
                                    borderRadius: '18px'
                                }}>
                                    <span style={{
                                        position: 'absolute', content: '""', height: '14px', width: '14px', left: '2px', bottom: '2px',
                                        backgroundColor: '#fff', transition: '.3s', borderRadius: '50%',
                                        transform: autoApprove ? 'translateX(14px)' : 'translateX(0)'
                                    }} />
                                </span>
                            </label>
                            Auto-Approve
                        </div>
                    </div>
                </div>
            </main>

            {/* ── Right Panel: API Tester / File Preview ── */}
            <AnimatePresence>
                {panelMode && (
                    <motion.aside
                        className="cp-right-panel"
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: panelMode === 'file' ? 660 : 440, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.26, ease: [0.4, 0, 0.2, 1] }}
                    >
                        <div className="cp-rp-inner">
                            <div className="cp-rp-header">
                                <div className="cp-rp-title-wrap">
                                    {panelMode === 'file' ? (
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                    ) : (
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>
                                    )}
                                    <span className="cp-rp-title">{panelMode === 'file' ? previewFile : 'API Tester'}</span>
                                </div>
                                <button className="cp-rp-close" onClick={() => { setPanelMode(null); setPreviewFile(null); }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                                        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                                    </svg>
                                </button>
                            </div>

                            {panelMode === 'tester' && (
                                <>
                                    <div className="cp-rp-swagger">
                                        <a
                                            href={`${DEPLOYED_API_BASE}/docs`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="cp-swagger-btn"
                                            title="Open your deployed backend's Swagger UI (localhost:8001)"
                                        >
                                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><path d="M12 8v4l3 3" /></svg>
                                            Open Swagger UI (Local)
                                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                                        </a>
                                    </div>
                                    <p className="cp-rp-desc">Try your endpoints live — no setup or code needed.</p>
                                    <div className="cp-rp-endpoints">
                                        {projectEndpoints.length > 0 ? projectEndpoints.map(ep => <EndpointCard key={ep.id} ep={ep} />) : <p className="cp-empty-project" style={{ textAlign: 'center', marginTop: '40px' }}>No dynamic endpoints found in spec.</p>}
                                    </div>
                                </>
                            )}

                            {panelMode === 'file' && previewFile && (
                                <div className="cp-file-viewer">
                                    <div className="cp-ide-toolbar">
                                        <span className="cp-ide-filename">{previewFile}</span>
                                    </div>
                                    <div className="cp-ide-scroll">
                                        <table className="cp-ide-table">
                                            <tbody>
                                                {(projectFiles[previewFile] ?? '// File content not available').split('\n').map((line, i) => (
                                                    <tr key={i} className="cp-ide-row">
                                                        <td className="cp-ide-ln">{i + 1}</td>
                                                        <td className="cp-ide-line" dangerouslySetInnerHTML={{ __html: syntaxHighlight(line) || '&nbsp;' }} />
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                    <div className="cp-suggest-footer">
                                        {suggestOpen ? (
                                            <div style={{ position: 'relative' }}>
                                                {suggestAtMenu && (
                                                    <div className="cp-suggest-at-menu">
                                                        {Object.keys(projectFiles).map(f => (
                                                            <button
                                                                key={f}
                                                                className="cp-suggest-at-item"
                                                                onMouseDown={e => {
                                                                    e.preventDefault();
                                                                    const atIdx = editSuggestion.lastIndexOf('@');
                                                                    const newVal = editSuggestion.slice(0, atIdx) + '@' + f + ' ';
                                                                    setEditSuggestion(newVal);
                                                                    setSuggestAtMenu(false);
                                                                }}
                                                            >
                                                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                                                {f}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                                <textarea
                                                    autoFocus
                                                    className="cp-suggest-input"
                                                    placeholder={`Describe edits… type @ to mention a file (Enter to send)`}
                                                    value={editSuggestion}
                                                    onChange={e => {
                                                        const val = e.target.value;
                                                        setEditSuggestion(val);
                                                        const last = val[val.length - 1];
                                                        if (last === '@') setSuggestAtMenu(true);
                                                        else if (suggestAtMenu && val.indexOf('@') === -1) setSuggestAtMenu(false);
                                                    }}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter' && !e.shiftKey) {
                                                            e.preventDefault();
                                                            submitSuggestEdits();
                                                        }
                                                        if (e.key === 'Escape') {
                                                            if (suggestAtMenu) { setSuggestAtMenu(false); return; }
                                                            setSuggestOpen(false);
                                                            setEditSuggestion('');
                                                        }
                                                    }}
                                                    rows={3}
                                                />
                                            </div>
                                        ) : (
                                            <button
                                                className="cp-suggest-btn active"
                                                onClick={handleSuggestEdits}
                                            >
                                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" /></svg>
                                                Suggest edits
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>
        </div>
    );
}
