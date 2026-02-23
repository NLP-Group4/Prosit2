import { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import DemoSection from '../components/DemoSection';
import Features from '../components/Features';
import Waitlist from '../components/Waitlist';
import Footer from '../components/Footer';
import WaitlistModal from '../components/WaitlistModal';

export default function LandingPage({ theme, onThemeToggle }) {
    const [waitlistOpen, setWaitlistOpen] = useState(false);

    return (
        <>
            <Navbar theme={theme} onThemeToggle={onThemeToggle} />
            <Hero onOpenWaitlist={() => setWaitlistOpen(true)} />
            <DemoSection />
            <Features onOpenWaitlist={() => setWaitlistOpen(true)} />
            <Waitlist onOpenWaitlist={() => setWaitlistOpen(true)} />
            <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
            <Footer />
        </>
    );
}
