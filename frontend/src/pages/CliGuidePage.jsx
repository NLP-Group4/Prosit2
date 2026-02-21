import { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function CliGuidePage({ onOpenLogin, theme, onThemeToggle }) {
    const containerRef = useRef(null);
    const { scrollYProgress } = useScroll({
        target: containerRef,
        offset: ["start end", "center center"]
    });

    // 3D rotations based on scroll
    // Starts tipped back by 40 degrees, and flat when in center
    const rotateX = useTransform(scrollYProgress, [0, 1], [40, 0]);
    const opacity = useTransform(scrollYProgress, [0, 1], [0.4, 1]);
    const scale = useTransform(scrollYProgress, [0, 1], [0.9, 1]);
    const y = useTransform(scrollYProgress, [0, 1], [50, 0]);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Navbar onLoginClick={onOpenLogin} theme={theme} onThemeToggle={onThemeToggle} />
            <main style={{ flex: 1, width: '100%', overflowX: 'hidden' }}>

                {/* Intro Hero to provide scrolling room */}
                <section style={{ height: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', textAlign: 'center', padding: '0 20px' }}>
                    <h1 style={{ fontSize: 'clamp(3rem, 6vw, 5rem)', fontWeight: '700', letterSpacing: '-0.03em', marginBottom: '20px' }}>
                        CLI Guide
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '600px' }}>
                        The ultimate control plane for your IDE. Run, debug, and trace your multiagent systems straight from the shell.
                    </p>
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5, duration: 1 }}
                        style={{ marginTop: '40px', color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}
                    >
                        <span>Scroll</span>
                        <motion.div
                            animate={{ y: [0, 5, 0] }}
                            transition={{ repeat: Infinity, duration: 2 }}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>
                        </motion.div>
                    </motion.div>
                </section>

                {/* 3D Scrolling Terminal Section */}
                <section ref={containerRef} style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', perspective: '1200px', padding: '0 20px' }}>
                    <motion.div style={{
                        width: '100%',
                        maxWidth: '1200px',
                        rotateX,
                        opacity,
                        scale,
                        y,
                        transformStyle: 'preserve-3d',
                        background: '#1a1a2e',
                        borderRadius: '16px',
                        border: '1px solid var(--border-subtle)',
                        boxShadow: 'var(--shadow-xl), 0 40px 100px -20px #38bdf840',
                        overflow: 'hidden',
                        aspectRatio: '16/11', // Elongated slightly
                        display: 'flex',
                        flexDirection: 'column'
                    }}>
                        <div style={{ height: '44px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', padding: '0 16px', gap: '8px', background: '#252542' }}>
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444' }} />
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#f59e0b' }} />
                            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981' }} />
                            <span style={{ marginLeft: 'auto', fontSize: '12px', color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--font-mono)' }}>bash - ~/projects/myapp</span>
                        </div>
                        <div style={{ padding: '40px', flex: 1, color: 'rgba(255,255,255,0.85)', fontSize: 'clamp(12px, 1.2vw, 16px)', fontFamily: 'var(--font-mono)', lineHeight: '1.8' }}>
                            <div style={{ display: 'flex', gap: '16px' }}><span style={{ color: '#10b981' }}>$</span> <span>npm i -g @interius/cli</span></div>
                            <div style={{ color: 'rgba(255,255,255,0.4)' }}>+ @interius/cli@1.2.0</div>
                            <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: '24px' }}>added 42 packages in 2s</div>

                            <div style={{ display: 'flex', gap: '16px', color: '#38bdf8' }}><span style={{ color: '#10b981' }}>$</span> <span>interius "Look through my documents and find the todo app and build the APIs for it"</span></div>
                            <div style={{ color: '#3b82f6', marginTop: '12px' }}>✓ Authenticated as Elijah</div>
                            <div style={{ color: '#10b981' }}>✓ Linked local directory to project "todo-app"</div>

                            <motion.div
                                initial={{ opacity: 0 }}
                                whileInView={{ opacity: 1 }}
                                viewport={{ once: false, margin: '-100px' }}
                                transition={{ delay: 0.5, duration: 1 }}
                                style={{ color: 'rgba(255,255,255,0.8)', marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}
                            >
                                <div style={{ display: 'flex', gap: '8px', color: '#f59e0b' }}>
                                    <span>&gt;</span>
                                    <span>Analyzing documents... found 4 schemas (User, Task, List, Tag)</span>
                                </div>
                                <div style={{ color: '#10b981' }}>✓ Generated REST endpoints, models, and controllers</div>
                                <div style={{ color: '#10b981' }}>✓ Configured SQLite database connection</div>
                                <div style={{ color: '#10b981' }}>✓ Containerizing API layer...</div>

                                <div style={{ marginTop: '20px', paddingLeft: '16px', borderLeft: '2px solid rgba(255,255,255,0.2)' }}>
                                    <div style={{ fontWeight: 600, color: '#ffffff' }}>App is ready!</div>
                                    <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Directory:</span>
                                        <span style={{ color: '#38bdf8' }}>~/documents/todo-app/api</span>
                                    </div>
                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Container:</span>
                                        <span style={{ color: '#38bdf8' }}>docker run -p 8080:8080 interius/todo-app</span>
                                    </div>
                                    <div style={{ display: 'flex', gap: '12px' }}>
                                        <span style={{ color: 'rgba(255,255,255,0.5)' }}>Endpoint:</span>
                                        <a href="#" style={{ color: '#10b981', textDecoration: 'none' }}>http://localhost:8080/docs</a>
                                    </div>
                                </div>
                                <div style={{ marginTop: '32px', color: 'rgba(255,255,255,0.3)', fontSize: '0.85em', fontFamily: 'var(--font-mono)' }}>
                                    Press <span style={{ color: 'rgba(255,255,255,0.6)' }}>⌘+C</span> or <span style={{ color: 'rgba(255,255,255,0.6)' }}>Ctrl+C</span> to quit
                                </div>
                                <div style={{ marginTop: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
                                    <span style={{ color: '#10b981', fontWeight: 600 }}>&gt;&gt;</span>
                                    <motion.span
                                        animate={{ opacity: [1, 0] }}
                                        transition={{ repeat: Infinity, duration: 1 }}
                                        style={{ width: '8px', height: '16px', background: '#10b981', display: 'inline-block' }}
                                    />
                                </div>
                            </motion.div>
                        </div>
                    </motion.div>
                </section>

                {/* Coming Soon Footer */}
                <section style={{ height: '40vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle at center, rgba(56, 189, 248, 0.05) 0%, transparent 60%)' }}>
                    <h2 style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '-0.02em', background: 'var(--text-gradient)', WebkitBackgroundClip: 'text' }}>
                        Coming soon
                    </h2>
                </section>
            </main>
            <Footer />
        </div>
    );
}
