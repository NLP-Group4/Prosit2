import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import ChatPage from './pages/ChatPage';
import LoginModal from './components/LoginModal';
import './App.css';

function AppContent() {
  const { user } = useAuth();
  const [loginOpen, setLoginOpen] = useState(!user);
  const [theme, setTheme] = useState(() => localStorage.getItem('interius-theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('interius-theme', theme);
  }, [theme]);

  useEffect(() => {
    // Show login modal if not authenticated
    if (!user) {
      setLoginOpen(true);
    }
  }, [user]);

  const toggleTheme = () => setTheme((p) => (p === 'dark' ? 'light' : 'dark'));

  return (
    <>
      {user ? (
        <ChatPage theme={theme} onThemeToggle={toggleTheme} />
      ) : (
        <div className="login-screen">
          <div className="login-screen-logo">
            <img src="/mini.svg" alt="Interius" width={56} height={56} />
          </div>
          <h1>Welcome to Interius API Builder</h1>
          <p>Sign in to start generating backends</p>
        </div>
      )}
      <LoginModal isOpen={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
