import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './WaitlistModal.css';

export default function WaitlistModal({ isOpen, onClose }) {
    const [email, setEmail] = useState('');
    const [os, setOs] = useState('mac'); // 'mac' | 'windows' | 'linux'
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (!email) {
            setError('Please provide an email address.');
            return;
        }

        setLoading(true);
        // Simulate API call to join waitlist
        try {
            await new Promise((r) => setTimeout(r, 1000));
            setSuccess(true);
        } catch (err) {
            setError('Something went wrong. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const resetAndClose = () => {
        setEmail('');
        setOs('mac');
        setSuccess(false);
        setError('');
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    className="waitlist-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                >
                    <div className="waitlist-backdrop" onClick={resetAndClose} />
                    <motion.div
                        className="waitlist-modal"
                        initial={{ opacity: 0, scale: 0.96, y: 8 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.96, y: 8 }}
                        transition={{ duration: 0.2 }}
                    >
                        <button className="waitlist-close" onClick={resetAndClose} aria-label="Close">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                        </button>

                        {!success ? (
                            <>
                                <div className="waitlist-header">
                                    <div className="waitlist-logo-wrapper">
                                        <img src="/mini.svg" alt="Interius" width={24} />
                                    </div>
                                    <h2>Join the Waitlist</h2>
                                    <p>Get early access to the Interius IDE.</p>
                                </div>

                                <form className="waitlist-form" onSubmit={handleSubmit}>
                                    <div className="waitlist-field">
                                        <label>Email address</label>
                                        <input
                                            type="email"
                                            placeholder="you@example.com"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                        />
                                    </div>

                                    <div className="waitlist-os-selection">
                                        <label>Preferred Operating System</label>
                                        <div className="waitlist-radio-group">
                                            <label>
                                                <input
                                                    type="radio"
                                                    name="os"
                                                    value="mac"
                                                    checked={os === 'mac'}
                                                    onChange={(e) => setOs(e.target.value)}
                                                />
                                                macOS
                                            </label>
                                            <label>
                                                <input
                                                    type="radio"
                                                    name="os"
                                                    value="windows"
                                                    checked={os === 'windows'}
                                                    onChange={(e) => setOs(e.target.value)}
                                                />
                                                Windows
                                            </label>
                                            <label>
                                                <input
                                                    type="radio"
                                                    name="os"
                                                    value="linux"
                                                    checked={os === 'linux'}
                                                    onChange={(e) => setOs(e.target.value)}
                                                />
                                                Linux
                                            </label>
                                        </div>
                                    </div>

                                    {error && (
                                        <div style={{ color: '#ef4444', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
                                            {error}
                                        </div>
                                    )}

                                    <button className="waitlist-submit" type="submit" disabled={loading}>
                                        {loading ? 'Submitting...' : 'Join Waitlist'}
                                    </button>
                                </form>
                            </>
                        ) : (
                            <div className="waitlist-success">
                                <div className="waitlist-success-icon">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                                </div>
                                <h3>You're on the list!</h3>
                                <p>We've added <strong>{email}</strong> to our early access queue. We'll be in touch soon.</p>
                            </div>
                        )}
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
