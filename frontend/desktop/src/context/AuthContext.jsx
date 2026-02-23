import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Hydrate from localStorage
        const token = localStorage.getItem('auth_token');
        const email = localStorage.getItem('user_email');
        if (token && email) {
            setUser({ id: email, email, name: email.split('@')[0] });
        }
        setLoading(false);
    }, []);

    const signUp = async (email, password, name) => {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Registration failed');
        }
        return await res.json();
    };

    const signIn = async (email, password) => {
        const formData = new URLSearchParams();
        formData.append('username', email); // FastAPI OAuth2PasswordRequestForm uses 'username'
        formData.append('password', password);

        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Invalid credentials');
        }

        const data = await res.json();
        localStorage.setItem('auth_token', data.access_token);
        localStorage.setItem('user_email', email);
        setUser({ id: email, email, name: email.split('@')[0] });

        return data;
    };

    const signInWithOAuth = async (provider) => {
        throw new Error("OAuth not supported by FastAPI backend MVP");
    };

    const logout = async () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_email');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, signUp, signIn, signInWithOAuth, logout }}>
            {!loading && children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
