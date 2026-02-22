import { Link } from 'react-router-dom';
import './Footer.css';

export default function Footer() {
    return (
        <footer className="footer" id="about">
            <div className="container">
                <div className="footer-grid">
                    <div className="footer-col">
                        <h4>Product</h4>
                        <ul>
                            <li><a href="#features">Features</a></li>
                            <li><a href="#demo">Demo</a></li>
                        </ul>
                    </div>
                    <div className="footer-col">
                        <h4>Developers</h4>
                        <ul>
                            <li><Link to="/docs">Documentation</Link></li>
                            <li><Link to="/api">API Reference</Link></li>
                            <li><Link to="/cli">CLI Guide</Link></li>
                        </ul>
                    </div>
                    <div className="footer-col">
                        <h4>Company</h4>
                        <ul>
                            <li><Link to="/about">About</Link></li>
                            <li><Link to="/research">Research</Link></li>
                        </ul>
                    </div>
                    <div className="footer-col">
                        <h4>Terms &amp; Policies</h4>
                        <ul>
                            <li><a href="#">Terms of Use</a></li>
                            <li><a href="#">Privacy Policy</a></li>
                            <li><a href="#">Security</a></li>
                        </ul>
                    </div>
                </div>
            </div>
        </footer>
    );
}
