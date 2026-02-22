import { motion } from 'framer-motion';
import './Hero.css';

export default function Hero({ onTryClick, onOpenWaitlist }) {
    return (
        <section className="hero" id="top">
            <div className="container hero-content">
                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2, duration: 0.6 }}
                >
                    Interius<span className="hero-period">.</span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.35, duration: 0.5 }}
                >
                    Describe your API. Interius builds, tests, and ships it.
                </motion.p>

                <motion.div
                    className="hero-actions"
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.5 }}
                >
                    <button className="btn-primary" onClick={onTryClick}>
                        Try Interius
                    </button>
                    <button className="btn-secondary" onClick={onOpenWaitlist}>
                        Join the IDE waitlist
                    </button>
                </motion.div>
            </div>
        </section>
    );
}
