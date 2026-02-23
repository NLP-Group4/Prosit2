import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function ApiReferencePage({ theme, onThemeToggle }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Navbar theme={theme} onThemeToggle={onThemeToggle} />
            <main style={{ flex: 1, padding: '120px 20px', textAlign: 'center' }}>
                <div className="container">
                    <h1 style={{ fontSize: '3rem', marginBottom: '20px' }}>API Reference</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Detailed documentation for the Interius API endpoints.</p>
                    <div style={{ marginTop: '60px', padding: '40px', background: 'var(--bg-secondary)', borderRadius: '12px' }}>
                        <p>Content coming soon.</p>
                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}
