import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ScrollToTop from './components/ScrollToTop';
import LandingPage from './pages/LandingPage';
import DownloadPage from './pages/DownloadPage';
import DocsPage from './pages/DocsPage';
import ApiReferencePage from './pages/ApiReferencePage';
import CliGuidePage from './pages/CliGuidePage';
import AboutPage from './pages/AboutPage';
import ResearchPage from './pages/ResearchPage';
import ResearchPostPage from './pages/ResearchPostPage';
import './App.css';

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('interius-theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('interius-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((p) => (p === 'dark' ? 'light' : 'dark'));

  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<LandingPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/download" element={<DownloadPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/docs" element={<DocsPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/api" element={<ApiReferencePage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/cli" element={<CliGuidePage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/about" element={<AboutPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/research" element={<ResearchPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="/research/:id" element={<ResearchPostPage theme={theme} onThemeToggle={toggleTheme} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
