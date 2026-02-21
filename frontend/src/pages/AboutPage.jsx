import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const TEAM = [
    {
        name: "Nicole N. Nanka-Bruce",
        role: "Research Engineer",
        image: "/team/nicole.png",
        bio: "Specializes in multiagent orchestration and the evaluation methodologies of autonomous AI systems."
    },
    {
        name: "Joseph A. Ajegetina",
        role: "Research Engineer",
        image: "/team/joseph.png",
        bio: "Leads the architectural design of distributed agentic environments and scalable state mechanisms."
    },
    {
        name: "Innocent F. Chikwanda",
        role: "Research Engineer",
        image: "/team/innocent.png",
        bio: "Focuses on optimizing hybrid vector search architectures and retrieval-augmented generation pipelines."
    },
    {
        name: "Elijah K. A. Boateng",
        role: "Research Engineer",
        image: "/team/elijah.png",
        bio: "Drives the development of Interius interfaces and the robust integration of post-training LLMs."
    }
];

export default function AboutPage({ onOpenLogin, theme, onThemeToggle }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Navbar onLoginClick={onOpenLogin} theme={theme} onThemeToggle={onThemeToggle} />

            <main style={{ flex: 1, padding: '120px 20px', maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
                <header style={{ textAlign: 'center', marginBottom: '80px' }}>
                    <h1 style={{ fontSize: 'clamp(2.5rem, 5vw, 4rem)', fontWeight: '700', letterSpacing: '-0.03em', marginBottom: '20px' }}>
                        About Interius
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '700px', margin: '0 auto', lineHeight: '1.6' }}>
                        We are a group of researchers and engineers from Ashesi University building agentic infrastructure to automate, orchestrate, and accelerate software development.
                    </p>
                </header>

                <section style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '60px',
                    marginBottom: '100px',
                    flexDirection: 'row'
                }} className="about-split-section">
                    <div style={{ flex: 1 }}>
                        <h2 style={{ fontSize: '1.8rem', fontWeight: '600', marginBottom: '20px', lineHeight: '1.3' }}>
                            Interius is your proactive AI engineer for complete software ecosystems. It can help you:
                        </h2>
                        <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <li style={{ position: 'relative', paddingLeft: '24px' }}>
                                <span style={{ position: 'absolute', left: 0, top: '8px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                                <strong style={{ color: 'var(--text-primary)' }}>Architect complete backends:</strong> Describe what you want to build, and Interius generates fully-typed APIs, models, and robust SQL infrastructure reflecting modern development patterns.
                            </li>
                            <li style={{ position: 'relative', paddingLeft: '24px' }}>
                                <span style={{ position: 'absolute', left: 0, top: '8px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                                <strong style={{ color: 'var(--text-primary)' }}>Maintain active memory:</strong> Using vector search and hierarchical LLM orchestration, it understands multi-file projects, preserving context as your codebase evolves.
                            </li>
                            <li style={{ position: 'relative', paddingLeft: '24px' }}>
                                <span style={{ position: 'absolute', left: 0, top: '8px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-green)' }} />
                                <strong style={{ color: 'var(--text-primary)' }}>Iterate continuously:</strong> Validate the state of the codebase, intelligently debug production errors, and securely execute terminal commands locally.
                            </li>
                        </ul>
                    </div>
                    <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
                        <div style={{
                            width: '100%',
                            background: 'var(--bg-primary)',
                            borderRadius: '16px',
                            border: '1px solid var(--border-subtle)',
                            boxShadow: 'var(--shadow-lg), 0 20px 40px -10px rgba(16, 185, 129, 0.1)',
                            overflow: 'hidden',
                            aspectRatio: '4/3',
                            display: 'flex',
                            flexDirection: 'column'
                        }}>
                            <div style={{ height: '40px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', padding: '0 16px', gap: '8px' }}>
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444' }} />
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b' }} />
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981' }} />
                            </div>
                            <div style={{ padding: '24px', flex: 1, background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px', fontFamily: 'var(--font-mono)' }}>
                                    $ interius init<br />
                                    <span style={{ color: 'var(--accent-green)' }}>Initializing new workspace...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section>
                    <h2 style={{ fontSize: '2rem', fontWeight: '600', marginBottom: '40px', textAlign: 'center' }}>Meet the Team</h2>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(4, 1fr)',
                        gap: '20px'
                    }}>
                        {TEAM.map((member, idx) => (
                            <div key={idx} style={{ textAlign: 'center' }}>
                                <div style={{
                                    width: '140px',
                                    height: '140px',
                                    margin: '0 auto 20px',
                                    borderRadius: '50%',
                                    overflow: 'hidden',
                                    border: '4px solid var(--bg-secondary)',
                                    boxShadow: 'var(--shadow-md)',
                                    background: 'var(--border-subtle)'
                                }}>
                                    <img
                                        src={member.image}
                                        alt={member.name}
                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                        onError={(e) => {
                                            e.target.onerror = null;
                                            e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(member.name)}&background=random&size=200`;
                                        }}
                                    />
                                </div>
                                <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '4px' }}>{member.name}</h3>
                                <div style={{ color: 'var(--accent-green)', fontSize: '0.9rem', fontWeight: '500', marginBottom: '12px' }}>{member.role}</div>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.5' }}>
                                    {member.bio}
                                </p>
                            </div>
                        ))}
                    </div>
                </section>
            </main>

            <Footer />
        </div>
    );
}
