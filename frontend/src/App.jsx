import React, { useEffect, useState } from "react";

const BASE = "http://localhost:8000/api/v1";

const TYPE_LABELS = {
  scholarship: "Scholarship",
  welfare_scheme: "Welfare",
  financial_aid: "Financial aid",
  skill_training: "Skill training",
  subsidy: "Subsidy",
  job_notification: "Job",
  competitive_exam: "Exam",
  pension: "Pension",
  certificate: "Certificate",
};

const SchemeCard = ({ scheme, showScore }) => {
  const typeLabel = TYPE_LABELS[scheme.opportunity_type] || scheme.opportunity_type || "Scheme";
  const link = scheme.application_url || scheme.source_url;
  return (
    <article className="group bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-lg hover:border-teal-200/80 transition-all duration-200">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <span className="inline-block px-2.5 py-0.5 rounded-lg bg-teal-50 text-teal-700 text-xs font-semibold uppercase tracking-wide mb-2">
            {typeLabel}
          </span>
          <h3 className="text-lg font-bold text-slate-800 mb-1.5 leading-snug">
            {scheme.title}
          </h3>
        </div>
        {showScore && scheme.match_score != null && (
          <span className="shrink-0 px-2.5 py-1 rounded-full bg-teal-100 text-teal-800 text-xs font-semibold">
            {Math.round(scheme.match_score * 100)}% match
          </span>
        )}
      </div>
      <p className="text-sm text-slate-600 leading-relaxed mb-4">
        {scheme.ai_summary || scheme.description || "No description."}
      </p>
      {link && (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-teal-700 hover:text-teal-800"
        >
          Apply or learn more
          <span className="opacity-70 group-hover:translate-x-0.5 transition-transform" aria-hidden>→</span>
        </a>
      )}
    </article>
  );
};

const AadharVerification = ({ onVerified }) => {
  const [step, setStep] = useState(1);
  const [aadhar, setAadhar] = useState("");
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (aadhar.length !== 12 || !/^\d+$/.test(aadhar)) {
      setError("Please enter a valid 12-digit Aadhar number.");
      return;
    }
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch(`${BASE}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aadhar_number: aadhar }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send OTP");
      setStep(2);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const res = await fetch(`${BASE}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aadhar_number: aadhar, otp }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Invalid OTP");
      if (data.is_verified) {
        onVerified();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-2xl border border-teal-200 shadow-sm mb-8">
      <div className="flex items-center gap-3 mb-4">
        <span className="flex items-center justify-center w-8 h-8 rounded-full bg-teal-100 text-teal-700 text-lg">🛡️</span>
        <div>
          <h2 className="text-lg font-bold text-slate-800">Become a Verified User</h2>
          <p className="text-sm text-slate-600">Verify your Aadhar to unlock premium features and schemes.</p>
        </div>
      </div>

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      {step === 1 ? (
        <form onSubmit={handleSendOtp} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Enter 12-digit Aadhar Number"
            value={aadhar}
            onChange={(e) => setAadhar(e.target.value)}
            maxLength={12}
            className="flex-1 p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 outline-none"
          />
          <button
            type="submit"
            disabled={isLoading || aadhar.length !== 12}
            className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 disabled:opacity-50 whitespace-nowrap"
          >
            {isLoading ? "Sending..." : "Send OTP"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerifyOtp} className="col-span-1">
          <p className="text-sm text-slate-600 mb-3">OTP sent to the mobile number registered with Aadhar ending in {aadhar.slice(-4)}.</p>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Enter 6-digit OTP (e.g. 123456)"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              className="flex-1 p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 outline-none"
            />
            <button
              type="submit"
              disabled={isLoading || !otp}
              className="px-6 py-3 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-700 disabled:opacity-50 whitespace-nowrap"
            >
              {isLoading ? "Verifying..." : "Verify"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

const LoginScreen = ({ onLogin, onGuest }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    const endpoint = isSignUp ? "register" : "login";
    try {
      const res = await fetch(`${BASE}/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-teal-500 via-teal-600 to-slate-900 p-6">
      <div className="w-full max-w-md bg-white/95 backdrop-blur-sm p-8 rounded-3xl shadow-2xl border border-white/20">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-slate-900 mb-2">CivicSense <span className="text-teal-600">AI</span></h1>
          <p className="text-slate-600">{isSignUp ? "Create an account" : "Sign in"} to discover schemes tailored for you</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-2xl text-sm flex items-center gap-2">
            <span className="text-red-500 text-lg">⚠</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3.5 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-teal-500 outline-none transition bg-slate-50"
              placeholder="e.g. demo@civicsense.ai"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3.5 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-teal-500 outline-none transition bg-slate-50"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-teal-600 text-white py-4 rounded-2xl font-bold hover:bg-teal-700 transition-all shadow-lg shadow-teal-900/20 disabled:opacity-70 mt-2"
          >
            {isLoading ? (isSignUp ? "Creating account..." : "Signing in...") : (isSignUp ? "Sign Up" : "Sign In")}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError("");
            }}
            className="text-teal-600 font-semibold hover:text-teal-700 transition-colors text-sm"
          >
            {isSignUp ? "Already have an account? Sign In" : "Don't have an account? Sign Up"}
          </button>
        </div>

        <div className="mt-8 flex flex-col gap-4">
          <div className="relative flex items-center">
            <div className="flex-grow border-t border-slate-200"></div>
            <span className="flex-shrink mx-4 text-slate-400 text-sm">OR</span>
            <div className="flex-grow border-t border-slate-200"></div>
          </div>
          <button
            onClick={onGuest}
            className="w-full bg-slate-100 text-slate-700 py-3.5 rounded-2xl font-semibold hover:bg-slate-200 transition-colors"
          >
            Continue as Guest
          </button>
        </div>
      </div>
    </div>
  );
};

const UserProfileDashboard = ({ user, profile, onBack, onLogout }) => {
  return (
    <div className="max-w-3xl mx-auto bg-white rounded-3xl shadow-xl border border-slate-200/80 overflow-hidden">
      <div className="bg-teal-800 p-8 text-white relative">
        <button
          onClick={onBack}
          className="absolute top-6 left-6 text-teal-100 hover:text-white flex items-center gap-2 text-sm font-medium transition-colors"
        >
          <span aria-hidden="true">&larr;</span> Back to Dashboard
        </button>

        <div className="flex flex-col items-center mt-8">
          <div className="w-24 h-24 bg-teal-600 rounded-full border-4 border-white shadow-md flex items-center justify-center text-4xl font-bold mb-4">
            {user.email === 'guest' ? 'G' : user.email.charAt(0).toUpperCase()}
          </div>
          <h2 className="text-2xl font-bold">{user.email === 'guest' ? 'Guest User' : user.email}</h2>
          <div className="flex gap-2 mt-3">
            <span className="px-3 py-1 rounded-full bg-teal-900/50 text-teal-100 text-xs font-semibold uppercase tracking-wider">
              {user.role}
            </span>
            {user.is_verified && (
              <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-100 border border-green-500/30 text-xs font-bold shadow-sm flex items-center gap-1">
                ✅ Verified
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="p-8">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-slate-800">Profile Details</h3>
          <button
            onClick={onLogout}
            className="px-5 py-2 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 text-sm font-medium transition-colors"
          >
            Logout
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50 p-6 rounded-2xl border border-slate-100">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Age</p>
            <p className="text-slate-800 font-medium">{profile.age || "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Education</p>
            <p className="text-slate-800 font-medium">{profile.education || "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Occupation</p>
            <p className="text-slate-800 font-medium">{profile.occupation || "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Interests</p>
            <p className="text-slate-800 font-medium">{profile.interests || "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Annual Income</p>
            <p className="text-slate-800 font-medium">{profile.income ? `₹${profile.income}` : "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Gender</p>
            <p className="text-slate-800 font-medium capitalize">{profile.gender || "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">State</p>
            <p className="text-slate-800 font-medium">{profile.state || "Not provided"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Category</p>
            <p className="text-slate-800 font-medium">{profile.category || "Not provided"}</p>
          </div>
        </div>
      </div>
    </div>
  );
};


export default function App() {
  const [user, setUser] = useState(null);
  const [currentView, setCurrentView] = useState("home");
  const [schemes, setSchemes] = useState([]);
  const [matched, setMatched] = useState([]);

  const [profile, setProfile] = useState({
    age: "",
    income: "",
    gender: "",
    state: "",
    category: "",
    education: "",
    occupation: "",
    interests: "",
  });

  const [isLoadingSchemes, setIsLoadingSchemes] = useState(true);
  const [isMatching, setIsMatching] = useState(false);
  const [matchAttempted, setMatchAttempted] = useState(false);
  const [lastTotalMatches, setLastTotalMatches] = useState(null);
  const [error, setError] = useState(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState(null);

  useEffect(() => {
    fetchSchemes();
  }, []);

  const loadSchemesFromCsv = async () => {
    setError(null);
    setSeedMessage(null);
    setIsSeeding(true);
    try {
      const res = await fetch(`${BASE}/seed-from-csv`, { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || "Failed to load CSV");
        return;
      }
      setSeedMessage(data.message || `Loaded ${data.inserted ?? 0} schemes.`);
      await fetchSchemes();
      setLastTotalMatches(data.inserted ?? 0);
    } catch (err) {
      setError("Could not load schemes from CSV. Is the backend running?");
      console.error(err);
    } finally {
      setIsSeeding(false);
    }
  };

  const [aiStatusMessage, setAiStatusMessage] = useState(null);

  const fetchSchemes = async () => {
    try {
      setIsLoadingSchemes(true);
      const res = await fetch(`${BASE}/schemes`);
      const data = await res.json();
      setSchemes(data.results || []);
    } catch (err) {
      setError("Could not load schemes.");
      console.error(err);
    } finally {
      setIsLoadingSchemes(false);
    }
  };

  const handleChange = (e) => {
    setProfile({
      ...profile,
      [e.target.name]: e.target.value,
    });
  };

  const matchSchemes = async (e) => {
    e.preventDefault();

    setError(null);
    setIsMatching(true);
    setMatched([]);

    const payload = {
      age: profile.age ? Number(profile.age) : null,
      annual_income: profile.income ? Number(profile.income) : null,
      gender: profile.gender?.toLowerCase() || null,
      state: profile.state || null,
      caste_category: profile.category || null,
      education: profile.education || null,
      occupation: profile.occupation || null,
      interests: profile.interests || null,
    };

    try {
      const res = await fetch(`${BASE}/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const msg = data.detail
          ? (Array.isArray(data.detail) ? data.detail.map((d) => d.msg || JSON.stringify(d)).join(", ") : String(data.detail))
          : `Request failed (${res.status})`;
        setError(msg);
        return;
      }

      const totalFromApi = data.total_matches ?? (data.top_matches?.length ?? 0) + (data.recommendations?.length ?? 0);
      setLastTotalMatches(totalFromApi);

      const combined = [
        ...(data.top_matches || []),
        ...(data.recommendations || []),
        ...(data.matches || []),
      ].filter(Boolean);

      setMatched(combined);

      // Check if fallback was used
      const usedFallback = combined.some(s =>
        s.ai_reasoning && s.ai_reasoning.includes("AI unavailable")
      );

      if (usedFallback) {
        setAiStatusMessage("Generative AI matched quota limit. Precise Offline Rules used instead.");
        setTimeout(() => setAiStatusMessage(null), 8000);
      } else if (combined.length > 0) {
        setAiStatusMessage("Matches generated successfully using AI!");
        setTimeout(() => setAiStatusMessage(null), 5000);
      }

    } catch (err) {
      console.error(err);
      setError("Matching failed. Is the backend running at http://localhost:8000?");
    } finally {
      setIsMatching(false);
      setMatchAttempted(true);
    }
  };

  const [loadingSchemeUrl, setLoadingSchemeUrl] = useState(null);

  const handleSchemeClick = (e, scheme) => {
    e.preventDefault();
    const link = scheme.application_url || scheme.source_url || `https://www.google.com/search?q=${encodeURIComponent(scheme.title + " official government scheme")}`;

    setLoadingSchemeUrl(scheme.id || scheme.title);

    // Simulate loading for 800ms before navigating
    setTimeout(() => {
      window.open(link, '_blank', 'noopener,noreferrer');
      setLoadingSchemeUrl(null);
    }, 800);
  };

  if (!user) {
    return <LoginScreen onLogin={(u) => setUser(u)} onGuest={() => setUser({ email: "guest", role: "guest" })} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-teal-50/30 text-slate-900 relative flex flex-col">
      {/* Marquee Banner */}
      {schemes.length > 0 && (
        <div className="w-full bg-teal-800 text-teal-50 py-2.5 overflow-hidden flex whitespace-nowrap shadow-sm border-b border-teal-900 sticky top-0 z-50">
          <div className="animate-marquee-ltr flex items-center gap-12 pr-12 hover:[animation-play-state:paused]">
            {[...schemes, ...schemes, ...schemes, ...schemes].map((scheme, idx) => (
              <button
                key={idx}
                onClick={(e) => handleSchemeClick(e, scheme)}
                className="font-semibold text-sm tracking-wide cursor-pointer hover:text-white hover:underline transition-colors flex items-center gap-2"
              >
                ✨ {scheme.title}
                {loadingSchemeUrl === (scheme.id || scheme.title) && (
                  <span className="w-3.5 h-3.5 border-2 border-teal-100 border-t-white rounded-full animate-spin inline-block" aria-hidden="true"></span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* AI Status Toast Notification */}
      {aiStatusMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-fade-in-up">
          <div className={`px-6 py-4 rounded-2xl shadow-2xl border flex items-center gap-3 backdrop-blur-md ${aiStatusMessage.includes("unavailable") || aiStatusMessage.includes("Offline")
            ? "bg-amber-500/90 border-amber-400 text-white"
            : "bg-teal-600/90 border-teal-500 text-white"
            }`}>
            <span className="text-xl" aria-hidden="true">
              {aiStatusMessage.includes("unavailable") || aiStatusMessage.includes("Offline") ? "⚡" : "✨"}
            </span>
            <p className="font-semibold">{aiStatusMessage}</p>
            <button
              onClick={() => setAiStatusMessage(null)}
              className="ml-4 p-1 hover:bg-white/20 rounded-full transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="pt-8 md:pt-12 lg:pt-12 p-6 md:p-10 lg:p-12 max-w-6xl mx-auto w-full flex-1">

        <header className="mb-12 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div className="text-center md:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-100 text-teal-800 text-sm font-medium mb-4">
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" aria-hidden />
              Government schemes made simple
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
              CivicSense <span className="text-teal-600">AI</span>
              {user.is_verified && (
                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-800 text-sm font-bold shadow-sm" title="Aadhar Verified">
                  ✅ Verified
                </span>
              )}
            </h1>
            <p className="text-slate-600 mt-2 text-lg max-w-xl">
              Hello, <span className="font-semibold text-teal-700">{user.email === 'guest' ? 'Guest' : user.email}</span>!
            </p>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setCurrentView('profile')}
              title="View Profile"
              className="w-12 h-12 rounded-full bg-teal-100 text-teal-800 font-bold text-lg flex items-center justify-center shadow-sm border border-teal-200 hover:bg-teal-200 hover:shadow transition-all focus:ring-2 focus:ring-teal-500 focus:outline-none"
            >
              {user.email === 'guest' ? 'G' : user.email.charAt(0).toUpperCase()}
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-2xl flex items-start gap-3 shadow-sm" role="alert">
            <span className="text-red-500 shrink-0 text-lg" aria-hidden>⚠</span>
            <span>{error}</span>
          </div>
        )}

        {currentView === 'profile' ? (
          <UserProfileDashboard
            user={user}
            profile={profile}
            onBack={() => setCurrentView('home')}
            onLogout={() => setUser(null)}
          />
        ) : (
          <div className="flex flex-col lg:flex-row gap-8 lg:gap-10">
            {/* Profile & Verification */}
            <div className="w-full lg:w-[22rem] shrink-0">
              {user.role !== 'guest' && !user.is_verified && (
                <AadharVerification onVerified={() => setUser({ ...user, is_verified: true })} />
              )}
              <div className="bg-white p-6 rounded-2xl shadow-lg border border-slate-200/80 sticky top-6">
                <h2 className="text-xl font-bold text-slate-800 mb-1">
                  Your profile
                </h2>
                <p className="text-sm text-slate-500 mb-5">We use this to find the best schemes for you.</p>

                <form onSubmit={matchSchemes} noValidate className="space-y-4">
                  <label className="block text-sm font-semibold text-slate-700">Age</label>
                  <input
                    type="number"
                    name="age"
                    min="1"
                    max="100"
                    value={profile.age}
                    onChange={handleChange}
                    placeholder="e.g. 25"
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-slate-50/50"
                  />

                  <label className="block text-sm font-semibold text-slate-700">Education</label>
                  <input
                    type="text"
                    name="education"
                    value={profile.education}
                    onChange={handleChange}
                    placeholder="e.g. 12th Pass, Graduate"
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-slate-50/50"
                  />

                  <label className="block text-sm font-semibold text-slate-700">Occupation</label>
                  <input
                    type="text"
                    name="occupation"
                    value={profile.occupation}
                    onChange={handleChange}
                    placeholder="e.g. Student, Farmer, Small Business"
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-slate-50/50"
                  />

                  <label className="block text-sm font-semibold text-slate-700">Interests</label>
                  <input
                    type="text"
                    name="interests"
                    value={profile.interests}
                    onChange={handleChange}
                    placeholder="e.g. Technology, Education, Sports"
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-slate-50/50"
                  />

                  <label className="block text-sm font-semibold text-slate-700">Annual income (₹)</label>
                  <input
                    type="number"
                    name="income"
                    min="0"
                    value={profile.income}
                    onChange={handleChange}
                    placeholder="e.g. 2,00,000"
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-slate-50/50"
                  />

                  <label className="block text-sm font-semibold text-slate-700">Gender</label>
                  <select
                    name="gender"
                    value={profile.gender}
                    onChange={handleChange}
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-white"
                  >
                    <option value="">Select gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>

                  <label className="block text-sm font-semibold text-slate-700">State</label>
                  <input
                    type="text"
                    name="state"
                    value={profile.state}
                    onChange={handleChange}
                    placeholder="e.g. Maharashtra"
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-slate-50/50"
                  />

                  <label className="block text-sm font-semibold text-slate-700">Category</label>
                  <select
                    name="category"
                    value={profile.category}
                    onChange={handleChange}
                    className="w-full p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none transition bg-white"
                  >
                    <option value="">Select category</option>
                    <option value="General">General</option>
                    <option value="OBC">OBC</option>
                    <option value="SC">SC</option>
                    <option value="ST">ST</option>
                  </select>

                  <button
                    type="submit"
                    disabled={isMatching}
                    className="w-full bg-teal-600 text-white py-3.5 rounded-xl font-semibold hover:bg-teal-700 active:bg-teal-800 transition disabled:opacity-60 disabled:cursor-not-allowed mt-3 shadow-md shadow-teal-900/10"
                  >
                    {isMatching ? "Finding matches…" : "Match schemes"}
                  </button>
                </form>
              </div>
            </div>

            {/* Results */}
            <div className="flex-1 min-w-0 space-y-12">
              <section>
                <h2 className="text-2xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <span className="w-1 h-7 rounded-full bg-teal-500" aria-hidden />
                  Matched for you
                  {matched.length > 0 && (
                    <span className="text-base font-normal text-slate-500">
                      {matched.length} scheme{matched.length !== 1 ? "s" : ""}
                    </span>
                  )}
                </h2>

                {isMatching && (
                  <div className="p-10 bg-white rounded-2xl border border-slate-200/80 shadow-sm flex flex-col items-center justify-center gap-4">
                    <div className="flex gap-1.5" aria-hidden>
                      <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:0ms]" />
                      <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:150ms]" />
                      <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:300ms]" />
                    </div>
                    <p className="text-slate-600 font-medium">Finding schemes that match your profile…</p>
                  </div>
                )}

                {!isMatching && matched.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {matched.map((s, i) => (
                      <SchemeCard key={s.id || i} scheme={s} showScore />
                    ))}
                  </div>
                )}

                {!isMatching && matched.length === 0 && (
                  <div className="p-10 bg-white rounded-2xl border border-slate-200/80 shadow-sm text-center space-y-5">
                    {!matchAttempted ? (
                      <>
                        <p className="text-slate-600">Fill in your profile and click <strong>Match schemes</strong> to see personalised results.</p>
                        <div className="h-12 w-48 mx-auto rounded-xl bg-slate-100 animate-pulse" aria-hidden />
                      </>
                    ) : lastTotalMatches === 0 ? (
                      <>
                        <p className="font-semibold text-slate-800">No schemes in the database yet</p>
                        <p className="text-sm text-slate-600 max-w-md mx-auto">
                          Place <code className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">schemes.csv</code> in the project root, then load it below.
                        </p>
                        <button
                          type="button"
                          onClick={loadSchemesFromCsv}
                          disabled={isSeeding}
                          className="px-5 py-2.5 bg-teal-600 text-white rounded-xl font-semibold hover:bg-teal-700 disabled:opacity-60 transition shadow-md shadow-teal-900/10"
                        >
                          {isSeeding ? "Loading…" : "Load schemes from CSV"}
                        </button>
                        {seedMessage && <p className="text-teal-700 text-sm font-medium">{seedMessage}</p>}
                      </>
                    ) : (
                      <>
                        <p className="text-slate-600">No schemes matched this time. Try changing age, income, state or category.</p>
                        <button
                          type="button"
                          onClick={matchSchemes}
                          className="text-teal-600 font-semibold hover:text-teal-700"
                        >
                          Match again
                        </button>
                      </>
                    )}
                  </div>
                )}
              </section>

              <section>
                <h2 className="text-2xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <span className="w-1 h-7 rounded-full bg-slate-400" aria-hidden />
                  Browse all schemes
                </h2>

                {isLoadingSchemes ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[1, 2, 3, 4].map((i) => (
                      <div key={i} className="bg-white p-5 rounded-2xl border border-slate-200/80 animate-pulse" aria-hidden>
                        <div className="h-5 w-24 rounded-lg bg-slate-200 mb-3" />
                        <div className="h-5 w-full rounded bg-slate-200 mb-2" />
                        <div className="h-4 w-3/4 rounded bg-slate-100" />
                      </div>
                    ))}
                  </div>
                ) : schemes.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {schemes.map((s, i) => (
                      <SchemeCard key={s.id || i} scheme={s} />
                    ))}
                  </div>
                ) : (
                  <div className="p-10 bg-white rounded-2xl border border-slate-200/80 text-slate-600 text-center">
                    No schemes to browse yet. Start the backend and load data to see the list.
                  </div>
                )}
              </section>
            </div>
          </div>
        )}
      </div>
    </div >
  );
}