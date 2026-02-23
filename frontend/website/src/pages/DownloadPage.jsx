import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import './DownloadPage.css';

export default function DownloadPage({ theme, onThemeToggle }) {
  const [os, setOS] = useState('');
  const [arch, setArch] = useState('');

  useEffect(() => {
    // Detect user's operating system
    const detectOS = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const platform = navigator.platform?.toLowerCase() || '';
      
      // Detect macOS
      if (userAgent.includes('mac') || platform.includes('mac')) {
        setOS('mac');
        // Default to Apple Silicon (arm64) as it's the current standard
        // Users can select Intel version from "Other Platforms" if needed
        setArch('arm64');
        return;
      }
      
      // Detect Windows
      if (userAgent.includes('win') || platform.includes('win')) {
        setOS('windows');
        const isWin64 = userAgent.includes('win64') || userAgent.includes('wow64');
        setArch(isWin64 ? 'x64' : 'x86');
        return;
      }
      
      // Detect Linux
      if (userAgent.includes('linux') || platform.includes('linux')) {
        setOS('linux');
        const isARM = userAgent.includes('arm') || userAgent.includes('aarch64');
        setArch(isARM ? 'arm64' : 'x64');
        return;
      }
      
      // Handle unknown platforms - default to mac
      setOS('unknown');
      setArch('arm64');
    };
    
    detectOS();
  }, []);

  const downloads = {
    mac: {
      name: 'macOS (Apple Silicon)',
      url: 'https://github.com/yourorg/interius/releases/latest/download/Interius-macOS-arm64.dmg',
      size: '120 MB',
      requirements: ['macOS 11.0 or later', 'Apple Silicon (M1/M2/M3/M4)', '4GB RAM', '500MB disk space'],
      instructions: [
        'Download the .dmg file',
        'Open the downloaded file',
        'Drag Interius to Applications folder',
        'Launch from Applications folder',
        'If prompted, allow the app in System Preferences > Security & Privacy'
      ]
    },
    'mac-intel': {
      name: 'macOS (Intel)',
      url: 'https://github.com/yourorg/interius/releases/latest/download/Interius-macOS-x64.dmg',
      size: '125 MB',
      requirements: ['macOS 10.15 or later', 'Intel processor', '4GB RAM', '500MB disk space'],
      instructions: [
        'Download the .dmg file',
        'Open the downloaded file',
        'Drag Interius to Applications folder',
        'Launch from Applications folder',
        'If prompted, allow the app in System Preferences > Security & Privacy'
      ]
    },
    windows: {
      name: 'Windows',
      url: 'https://github.com/yourorg/interius/releases/latest/download/Interius-Setup.exe',
      size: '95 MB',
      requirements: ['Windows 10 or later', '4GB RAM', '500MB disk space'],
      instructions: [
        'Download the .exe installer',
        'Run the installer as Administrator',
        'Follow the installation wizard',
        'Launch from Start menu or Desktop shortcut',
        'Allow firewall access if prompted'
      ]
    },
    linux: {
      name: 'Linux',
      url: 'https://github.com/yourorg/interius/releases/latest/download/Interius.AppImage',
      size: '110 MB',
      requirements: ['Ubuntu 20.04+ or equivalent', '4GB RAM', '500MB disk space'],
      instructions: [
        'Download the .AppImage file',
        'Make it executable: chmod +x Interius.AppImage',
        'Run: ./Interius.AppImage',
        'Or integrate with your desktop environment',
        'Ensure Docker daemon is running'
      ]
    }
  };

  const currentDownload = downloads[os] || downloads.mac;

  return (
    <>
      <Navbar theme={theme} onThemeToggle={onThemeToggle} />
      <div className="download-page">
        <section className="download-hero">
          <h1>Download Interius API Builder</h1>
          <p>Desktop app for AI-powered backend generation with local Docker testing</p>
        </section>

        <section className="download-primary">
          {os === 'unknown' ? (
            <>
              <h2>Choose Your Platform</h2>
              <p className="download-arch-note">We couldn't detect your operating system. Please select your platform below.</p>
            </>
          ) : (
            <>
              <h2>Download for {currentDownload.name}</h2>
              {arch === 'arm64' && os === 'mac' && (
                <p className="download-arch-note">Apple Silicon (M1/M2/M3/M4) Mac detected</p>
              )}
              {arch === 'x64' && os === 'mac' && (
                <p className="download-arch-note">Intel Mac detected</p>
              )}
              {os === 'windows' && arch === 'x64' && (
                <p className="download-arch-note">64-bit Windows detected</p>
              )}
              {os === 'linux' && (
                <p className="download-arch-note">{arch === 'arm64' ? 'ARM64' : 'x64'} Linux detected</p>
              )}
              <a href={currentDownload.url} className="download-button" download>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download Now
              </a>
              <p className="download-size">{currentDownload.size}</p>
            </>
          )}
        </section>

        {os !== 'unknown' && (
          <>
            <section className="download-requirements">
              <h3>System Requirements</h3>
              <ul>
                {currentDownload.requirements.map((req, i) => (
                  <li key={i}>{req}</li>
                ))}
              </ul>
            </section>

            <section className="download-instructions">
              <h3>Installation Instructions</h3>
              <ol>
                {currentDownload.instructions.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </section>
          </>
        )}

        <section className="download-docker-notice">
          <div className="docker-notice-content">
            <h3>Docker Desktop Required</h3>
            <p>
              Interius uses Docker to deploy and test generated backends locally. 
              When you launch the app for the first time, you'll be prompted to install Docker Desktop 
              if it's not already on your system. The installation will be handled automatically.
            </p>
            <p style={{ marginTop: '1rem', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
              Alternatively, you can install Docker Desktop manually before launching Interius:
            </p>
            <a 
              href="https://www.docker.com/products/docker-desktop" 
              target="_blank" 
              rel="noopener noreferrer"
              className="docker-link"
            >
              docker.com/products/docker-desktop
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          </div>
        </section>

        <section className="download-all-platforms">
          <h3>Other Platforms</h3>
          <div className="platform-grid">
            {Object.entries(downloads).map(([key, platform]) => (
              <div key={key} className={`platform-card ${os === key ? 'current' : ''}`}>
                <h4>{platform.name}</h4>
                <p className="platform-size">{platform.size}</p>
                <a href={platform.url} className="platform-download" download>
                  Download
                </a>
              </div>
            ))}
          </div>
        </section>
      </div>
      <Footer />
    </>
  );
}
