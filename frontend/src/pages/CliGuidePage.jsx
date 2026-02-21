import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function CliGuidePage({ onOpenLogin, theme, onThemeToggle }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Navbar onLoginClick={onOpenLogin} theme={theme} onThemeToggle={onThemeToggle} />
            <main style={{ flex: 1, padding: '120px 20px', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
                <header style={{ textAlign: 'center', marginBottom: '80px' }}>
                    <h1 style={{ fontSize: 'clamp(2.5rem, 5vw, 4rem)', fontWeight: '700', letterSpacing: '-0.03em', marginBottom: '20px' }}>
                        CLI Guide
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '700px', margin: '0 auto', lineHeight: '1.6' }}>
                        Power your local development flow using the Interius command-line tool. Connect your codebase to your agentic environments everywhere.
                    </p>
                </header>

                <section style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '60px',
                    marginBottom: '100px',
                    flexDirection: 'row-reverse' /* image left, text right */
                }} className="about-split-section">
                    <div style={{ flex: 1 }}>
                        <h2 style={{ fontSize: '1.8rem', fontWeight: '600', marginBottom: '20px', lineHeight: '1.3' }}>
                            The ultimate control plane for your IDE. Run, debug, and trace your multiagent systems from the shell.
                        </h2>
                        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <li style={{ position: 'relative', paddingLeft: '24px' }}>
                                <span style={{ position: 'absolute', left: 0, top: '8px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                                <strong style={{ color: 'var(--text-primary)' }}>Instant Synchronization:</strong> Link your remote instances by running <code style={{ background: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.9em', fontFamily: 'var(--font-mono)' }}>interius link</code>. Any change made in the browser chat reflects locally instantly.
                            </li>
                            <li style={{ position: 'relative', paddingLeft: '24px' }}>
                                <span style={{ position: 'absolute', left: 0, top: '8px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                                <strong style={{ color: 'var(--text-primary)' }}>Secure Headless Execution:</strong> Grants the agent access to safely orchestrate test suites, linting, and git operations using isolated containers.
                            </li>
                            <li style={{ position: 'relative', paddingLeft: '24px' }}>
                                <span style={{ position: 'absolute', left: 0, top: '8px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                                <strong style={{ color: 'var(--text-primary)' }}>Extensible Workflows:</strong> Define custom triggers and scripts in <code style={{ background: 'var(--bg-tertiary)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.9em', fontFamily: 'var(--font-mono)' }}>.interius.yml</code> for continuous evaluations.
                            </li>
                        </ul>
                    </div>
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
                        <div style={{
                            width: '100%',
                            background: '#1a1a2e',
                            borderRadius: '16px',
                            border: '1px solid var(--border-subtle)',
                            boxShadow: 'var(--shadow-lg), 0 20px 40px -10px rgba(0, 0, 0, 0.4)',
                            overflow: 'hidden',
                            aspectRatio: '4/3',
                            display: 'flex',
                            flexDirection: 'column'
                        }}>
                            <div style={{ height: '40px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', padding: '0 16px', gap: '8px', background: '#252542' }}>
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444' }} />
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b' }} />
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981' }} />
                                <span style={{ marginLeft: 'auto', fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)' }}>bash - ~/projects/myapp</span>
                            </div>
                            <div style={{ padding: '20px', flex: 1, color: 'rgba(255,255,255,0.8)', fontSize: '13px', fontFamily: 'var(--font-mono)', lineHeight: '1.6' }}>
                                <div style={{ display: 'flex', gap: '8px' }}><span style={{ color: '#10b981' }}>$</span> <span>npm i -g @interius/cli</span></div>
                                <div style={{ color: 'rgba(255,255,255,0.4)' }}>+ @interius/cli@1.2.0</div>
                                <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: '12px' }}>added 42 packages in 2s</div>

                                <div style={{ display: 'flex', gap: '8px' }}><span style={{ color: '#10b981' }}>$</span> <span>interius link --token=sk_live_***</span></div>
                                <div style={{ color: '#3b82f6' }}>✓ Authenticated as Adu</div>
                                <div style={{ color: '#10b981' }}>✓ Linked local directory to project "Prosit-2"</div>
                                <div style={{ color: 'rgba(255,255,255,0.4)', marginTop: '8px' }}>Waiting for agent commands...</div>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
