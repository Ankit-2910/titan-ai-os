"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mail, Lock, Eye, EyeOff, ArrowRight, Loader2 } from "lucide-react";
import { authApi, tokenStorage } from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const tokens =
        mode === "login"
          ? await authApi.login(email, password)
          : await authApi.register(email, password, fullName || undefined);
      tokenStorage.set(tokens);
      router.push("/select");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="titan-auth-root">
      {/* Animated gradient orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {/* Grid overlay */}
      <div className="grid-overlay" />

      <div className="auth-card">
        {/* Logo */}
        <div className="logo-wrap">
          <div className="logo-box">
            <svg width="44" height="44" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="tg" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
                  <stop offset="0" stopColor="#c4b5fd" />
                  <stop offset="0.55" stopColor="#7c3aed" />
                  <stop offset="1" stopColor="#4338ca" />
                </linearGradient>
              </defs>
              <path d="M50 10 L86 30 L86 70 L50 90 L14 70 L14 30 Z" fill="none" stroke="url(#tg)" strokeWidth="3" strokeLinejoin="round" />
              <path d="M50 22 L74 36 L74 64 L50 78 L26 64 L26 36 Z" fill="url(#tg)" opacity="0.12" />
              <path d="M36 40 L64 40 M50 40 L50 68" fill="none" stroke="url(#tg)" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>

        <h1 className="titan-title">TITAN</h1>
        <p className="titan-subtitle">ENTERPRISE AI OPERATING SYSTEM</p>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === "register" && (
            <div className="input-wrap">
              <span className="input-icon"><Mail size={16} /></span>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Full name"
              />
            </div>
          )}

          <div className="input-wrap">
            <span className="input-icon"><Mail size={16} /></span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </div>

          <div className="input-wrap">
            <span className="input-icon"><Lock size={16} /></span>
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
            <button
              type="button"
              className="eye-btn"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>

          {error && <div className="error-box">{error}</div>}

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <>
                {mode === "login" ? "Sign in" : "Create account"}
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        <p className="switch-mode">
          {mode === "login" ? "Don't have an account?" : "Already have an account?"}{" "}
          <button
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
          >
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>

        <div className="powered-by">
          POWERED BY <span>SHIVANCHAL CONSULTANTS</span>
        </div>
      </div>

      <style jsx>{`
        .titan-auth-root {
          min-height: 100vh;
          background: #08080c;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.5;
          animation: float 12s ease-in-out infinite;
        }
        .orb-1 {
          width: 400px; height: 400px;
          background: #7c3aed;
          top: -100px; left: 50%;
          transform: translateX(-50%);
          opacity: 0.35;
        }
        .orb-2 {
          width: 300px; height: 300px;
          background: #4338ca;
          bottom: -80px; left: -80px;
          animation-delay: -4s;
        }
        .orb-3 {
          width: 250px; height: 250px;
          background: #6366f1;
          top: 40%; right: -60px;
          animation-delay: -8s;
        }
        @keyframes float {
          0%, 100% { transform: translateY(0) translateX(-50%); }
          50% { transform: translateY(30px) translateX(-50%); }
        }
        .grid-overlay {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(124,58,237,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(124,58,237,0.04) 1px, transparent 1px);
          background-size: 50px 50px;
          mask-image: radial-gradient(ellipse at center, black, transparent 75%);
        }
        .auth-card {
          position: relative;
          z-index: 10;
          width: 360px;
          padding: 40px 32px;
          background: rgba(18, 18, 26, 0.7);
          backdrop-filter: blur(20px);
          border: 0.5px solid rgba(167, 139, 250, 0.18);
          border-radius: 24px;
          display: flex;
          flex-direction: column;
          align-items: center;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
          animation: cardIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes cardIn {
          from { opacity: 0; transform: translateY(20px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .logo-wrap { margin-bottom: 22px; }
        .logo-box {
          width: 72px; height: 72px;
          border-radius: 20px;
          background: linear-gradient(145deg, #1a1530, #0d0a1a);
          display: flex; align-items: center; justify-content: center;
          border: 0.5px solid rgba(167, 139, 250, 0.4);
          box-shadow: 0 0 40px rgba(124, 58, 237, 0.35);
          animation: glow 3s ease-in-out infinite;
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 40px rgba(124,58,237,0.35); }
          50% { box-shadow: 0 0 60px rgba(124,58,237,0.55); }
        }
        .titan-title {
          font-size: 32px;
          font-weight: 600;
          letter-spacing: 7px;
          margin: 0 0 6px;
          background: linear-gradient(90deg, #e9d5ff, #a78bfa, #818cf8);
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
          background-size: 200% auto;
          animation: shimmer 4s linear infinite;
        }
        @keyframes shimmer {
          to { background-position: 200% center; }
        }
        .titan-subtitle {
          font-size: 11px;
          color: #8b8b9e;
          letter-spacing: 2.5px;
          margin: 0 0 30px;
        }
        .auth-form {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .input-wrap {
          position: relative;
          display: flex;
          align-items: center;
        }
        .input-icon {
          position: absolute;
          left: 14px;
          color: #a78bfa;
          display: flex;
        }
        .input-wrap input {
          width: 100%;
          height: 46px;
          padding: 0 14px 0 42px;
          background: rgba(255, 255, 255, 0.04);
          border: 0.5px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          color: #fff;
          font-size: 14px;
          outline: none;
          transition: all 0.2s;
        }
        .input-wrap input::placeholder { color: #5a5a6e; }
        .input-wrap input:focus {
          border-color: rgba(167, 139, 250, 0.5);
          background: rgba(124, 58, 237, 0.08);
          box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.12);
        }
        .eye-btn {
          position: absolute;
          right: 14px;
          background: none;
          border: none;
          color: #6b6b7e;
          cursor: pointer;
          display: flex;
        }
        .error-box {
          background: rgba(226, 75, 74, 0.12);
          border: 0.5px solid rgba(226, 75, 74, 0.3);
          color: #f09595;
          font-size: 12px;
          padding: 10px 12px;
          border-radius: 10px;
        }
        .submit-btn {
          height: 48px;
          margin-top: 4px;
          background: linear-gradient(90deg, #7c3aed, #6366f1);
          border: none;
          border-radius: 12px;
          color: #fff;
          font-size: 14px;
          font-weight: 500;
          letter-spacing: 0.5px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4);
          transition: all 0.2s;
        }
        .submit-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 6px 28px rgba(124, 58, 237, 0.55);
        }
        .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .spin { animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .switch-mode {
          margin-top: 22px;
          font-size: 13px;
          color: #8b8b9e;
        }
        .switch-mode button {
          background: none;
          border: none;
          color: #a78bfa;
          font-weight: 500;
          cursor: pointer;
          font-size: 13px;
        }
        .powered-by {
          margin-top: 26px;
          font-size: 10px;
          color: #5a5a6e;
          letter-spacing: 1.5px;
        }
        .powered-by span { color: #a78bfa; }
      `}</style>
    </div>
  );
}
