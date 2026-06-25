"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HeartPulse, Server, School, Sparkles, ArrowRight, LogOut,
} from "lucide-react";
import { authApi, tokenStorage, domainStorage } from "@/lib/api";

interface SectorCard {
  key: string;
  name: string;
  tagline: string;
  icon: React.ReactNode;
  featured: boolean;
}

const SECTORS: SectorCard[] = [
  {
    key: "healthcare",
    name: "Healthcare OS",
    tagline: "Hospitals & clinics",
    icon: <HeartPulse size={26} />,
    featured: true,
  },
  {
    key: "it",
    name: "IT Operations OS",
    tagline: "SME tech firms",
    icon: <Server size={26} />,
    featured: false,
  },
  {
    key: "education",
    name: "Education OS",
    tagline: "Coaching & schools",
    icon: <School size={26} />,
    featured: false,
  },
  {
    key: "general",
    name: "General",
    tagline: "All-purpose AI",
    icon: <Sparkles size={26} />,
    featured: false,
  },
];

export default function SelectPage() {
  const router = useRouter();
  const [userName, setUserName] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    const token = tokenStorage.getAccess();
    if (!token) {
      router.push("/login");
      return;
    }
    authApi.me()
      .then((u) => setUserName(u.full_name || u.email))
      .catch(() => {
        tokenStorage.clear();
        router.push("/login");
      });
  }, []);

  function chooseSector(key: string) {
    setSelected(key);
    domainStorage.set(key);
    setTimeout(() => router.push("/dashboard"), 400);
  }

  async function logout() {
    await authApi.logout();
    router.push("/login");
  }

  return (
    <div className="select-root">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="grid-overlay" />

      <button className="logout-btn" onClick={logout}>
        <LogOut size={14} /> Logout
      </button>

      <div className="select-content">
        <div className="header">
          <h1 className="title">Choose your workspace</h1>
          <p className="subtitle">
            {userName ? `Welcome, ${userName}. ` : ""}
            TITAN transforms into a specialist for your sector
          </p>
        </div>

        <div className="grid">
          {SECTORS.map((s) => (
            <button
              key={s.key}
              className={`card ${s.featured ? "featured" : ""} ${selected === s.key ? "selected" : ""}`}
              onClick={() => chooseSector(s.key)}
            >
              {s.featured && <span className="badge">Recommended</span>}
              <div className="card-icon">{s.icon}</div>
              <div className="card-name">{s.name}</div>
              <div className="card-tagline">{s.tagline}</div>
              <div className="card-arrow"><ArrowRight size={16} /></div>
            </button>
          ))}
        </div>

        <div className="powered-by">
          POWERED BY <span>SHIVANCHAL CONSULTANTS</span>
        </div>
      </div>

      <style jsx>{`
        .select-root {
          min-height: 100vh;
          background: #08080c;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          overflow: hidden;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          padding: 24px;
        }
        .orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(90px);
          opacity: 0.3;
        }
        .orb-1 {
          width: 400px; height: 400px;
          background: #7c3aed;
          top: -120px; left: 50%;
          transform: translateX(-50%);
        }
        .orb-2 {
          width: 300px; height: 300px;
          background: #4338ca;
          bottom: -100px; right: -60px;
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
        .logout-btn {
          position: absolute;
          top: 24px; right: 24px;
          z-index: 20;
          display: flex;
          align-items: center;
          gap: 6px;
          background: rgba(255,255,255,0.04);
          border: 0.5px solid rgba(255,255,255,0.1);
          color: #8b8b9e;
          font-size: 13px;
          padding: 8px 14px;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .logout-btn:hover { color: #fff; background: rgba(255,255,255,0.08); }
        .select-content {
          position: relative;
          z-index: 10;
          width: 100%;
          max-width: 680px;
          animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .header { text-align: center; margin-bottom: 36px; }
        .title {
          font-size: 28px;
          font-weight: 500;
          letter-spacing: 1px;
          margin: 0 0 10px;
          background: linear-gradient(90deg, #e9d5ff, #a78bfa, #818cf8);
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .subtitle {
          font-size: 14px;
          color: #8b8b9e;
          margin: 0;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 14px;
        }
        .card {
          position: relative;
          background: rgba(124,58,237,0.05);
          border: 0.5px solid rgba(255,255,255,0.08);
          border-radius: 18px;
          padding: 28px 18px;
          text-align: center;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .card:hover {
          transform: translateY(-4px);
          border-color: rgba(167,139,250,0.4);
          background: rgba(124,58,237,0.1);
          box-shadow: 0 12px 30px rgba(124,58,237,0.2);
        }
        .card.featured {
          border-color: rgba(167,139,250,0.3);
          background: rgba(124,58,237,0.08);
        }
        .card.selected {
          transform: scale(0.96);
          border-color: #a78bfa;
          box-shadow: 0 0 0 3px rgba(124,58,237,0.3);
        }
        .badge {
          position: absolute;
          top: 12px; right: 12px;
          font-size: 9px;
          letter-spacing: 0.5px;
          color: #c4b5fd;
          background: rgba(124,58,237,0.2);
          padding: 3px 8px;
          border-radius: 8px;
        }
        .card-icon {
          width: 56px; height: 56px;
          margin-bottom: 16px;
          border-radius: 16px;
          background: linear-gradient(145deg, #1a1530, #0d0a1a);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #a78bfa;
          border: 0.5px solid rgba(167,139,250,0.3);
        }
        .card-name {
          font-size: 15px;
          font-weight: 500;
          color: #fff;
          margin-bottom: 4px;
        }
        .card-tagline {
          font-size: 12px;
          color: #8b8b9e;
          margin-bottom: 14px;
        }
        .card-arrow {
          color: #6b6b7e;
          transition: all 0.2s;
        }
        .card:hover .card-arrow {
          color: #a78bfa;
          transform: translateX(3px);
        }
        .powered-by {
          text-align: center;
          margin-top: 36px;
          font-size: 10px;
          color: #5a5a6e;
          letter-spacing: 1.5px;
        }
        .powered-by span { color: #a78bfa; }
      `}</style>
    </div>
  );
}
