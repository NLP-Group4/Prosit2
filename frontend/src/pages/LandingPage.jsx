import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import DemoSection from '../components/DemoSection';
import Features from '../components/Features';
import Waitlist from '../components/Waitlist';
import Footer from '../components/Footer';
import WaitlistModal from '../components/WaitlistModal';
import { useState } from 'react';

export default function LandingPage({ loginOpen, setLoginOpen, theme, onThemeToggle }) {
    const [waitlistOpen, setWaitlistOpen] = useState(false);

    return (
        <>
            <Navbar onLoginClick={() => setLoginOpen(true)} theme={theme} onThemeToggle={onThemeToggle} />
            <Hero onTryClick={() => setLoginOpen(true)} onOpenWaitlist={() => setWaitlistOpen(true)} />
            <DemoSection onOpenLogin={() => setLoginOpen(true)} />
            <Features onTryApp={() => setLoginOpen(true)} onOpenWaitlist={() => setWaitlistOpen(true)} />
            <Waitlist onTryApp={() => setLoginOpen(true)} onOpenWaitlist={() => setWaitlistOpen(true)} />
            <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
            <Footer />
        </>
    );
}
