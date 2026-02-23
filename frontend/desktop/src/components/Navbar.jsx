import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import InteriusLogo from './InteriusLogo';
import ThemeToggle from './ThemeToggle';
import './Navbar.css';

export default function Navbar({ theme, onThemeToggle }) {
  const { user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 80);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <motion.nav
      className={`navbar${scrolled ? ' scrolled' : ''}`}
      initial={{ y: -56 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="navbar-inner">
        <div className="navbar-logo">
          <InteriusLogo />
        </div>
        <div className="navbar-actions">
          <ThemeToggle theme={theme} onToggle={onThemeToggle} />
          {user && (
            <button className="navbar-logout" onClick={logout}>
              Log out
            </button>
          )}
        </div>
      </div>
    </motion.nav>
  );
}
