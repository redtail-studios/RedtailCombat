import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LogIn, UserPlus, Loader2 } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";
import { useDashboardAuth } from "@/lib/DashboardAuthContext";

const HAS_LOGGED_IN_KEY = "lore_has_logged_in";
const fieldClass = "h-12 rounded-none bg-ink border-white/15 font-mono";

export default function Login() {
  const navigate = useNavigate();
  const { dashboardLogin } = useDashboardAuth();
  // Returning players who've signed in before on this browser skip straight
  // to the sign-in form; everyone else sees the waitlist first.
  const [mode, setMode] = useState(() =>
    localStorage.getItem(HAS_LOGGED_IN_KEY) === "true" ? "signin" : "waitlist"
  );

  // sign-in state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginErr, setLoginErr] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // waitlist state
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [wlErr, setWlErr] = useState("");
  const [wlOk, setWlOk] = useState(false);
  const [wlLoading, setWlLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginErr("");
    setLoginLoading(true);
    await new Promise((r) => setTimeout(r, 300)); // brief UX delay, matches PixelButton loading feel
    const result = dashboardLogin(username.trim(), password);
    setLoginLoading(false);
    if (!result.success) {
      setLoginErr(result.error || "Wrong username or password.");
      return;
    }
    localStorage.setItem(HAS_LOGGED_IN_KEY, "true");
    navigate("/dashboard");
  };

  const handleWaitlist = async (e) => {
    e.preventDefault();
    setWlErr("");
    setWlOk(false);
    if (!firstName.trim() || !lastName.trim()) {
      setWlErr("First and last name are required.");
      return;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
      setWlErr("Enter a valid email address.");
      return;
    }
    setWlLoading(true);
    try {
      const r = await fetch("/api/lore/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ first_name: firstName.trim(), last_name: lastName.trim(), email: email.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Something went wrong");
      setWlOk(true);
      setFirstName(""); setLastName(""); setEmail("");
    } catch (err) {
      setWlErr(err.message || "Something went wrong. Try again.");
    } finally {
      setWlLoading(false);
    }
  };

  if (mode === "signin") {
    return (
      <AuthLayout icon={LogIn} title="PLAYER LOGIN" subtitle="continue your run">
        {loginErr && (
          <div className="mb-4 p-3 bg-pulse/10 border border-pulse/40 text-pulse text-sm font-mono">
            {loginErr}
          </div>
        )}
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              autoComplete="username"
              autoFocus
              placeholder="lore"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={fieldClass}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={fieldClass}
              required
            />
          </div>
          <Button type="submit" className="w-full h-12 rounded-none font-pixel text-[10px] uppercase tracking-wider bg-pulse text-ink hover:bg-[#ff4747]" disabled={loginLoading}>
            {loginLoading ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Logging in...</>) : "Log in"}
          </Button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-panel px-3 text-platinum/50 font-mono">not a player yet?</span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          onClick={() => setMode("waitlist")}
          className="w-full h-12 rounded-none font-pixel text-[10px] uppercase tracking-wider bg-ink border-moss text-moss hover:bg-moss hover:text-ink shadow-[0_0_18px_rgba(180,255,57,0.25)]"
        >
          Join the waitlist
        </Button>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout icon={UserPlus} title="JOIN THE WAITLIST" subtitle="restricted tool · request access">
      <form onSubmit={handleWaitlist} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="firstName">First name</Label>
          <Input
            id="firstName"
            autoComplete="given-name"
            autoFocus
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className={fieldClass}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="lastName">Last name</Label>
          <Input
            id="lastName"
            autoComplete="family-name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className={fieldClass}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={fieldClass}
            required
          />
        </div>
        {wlErr && (
          <div className="p-3 bg-pulse/10 border border-pulse/40 text-pulse text-sm font-mono">{wlErr}</div>
        )}
        {wlOk && (
          <div className="p-3 bg-moss/10 border border-moss/40 text-moss text-sm font-mono">
            You're on the list — we'll be in touch.
          </div>
        )}
        <Button type="submit" className="w-full h-12 rounded-none font-pixel text-[10px] uppercase tracking-wider bg-pulse text-ink hover:bg-[#ff4747]" disabled={wlLoading}>
          {wlLoading ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Joining...</>) : "Join waitlist"}
        </Button>
      </form>

      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-panel px-3 text-platinum/50 font-mono">already a player?</span>
        </div>
      </div>

      <Button
        type="button"
        variant="outline"
        onClick={() => setMode("signin")}
        className="w-full h-12 rounded-none font-pixel text-[10px] uppercase tracking-wider bg-ink border-moss text-moss hover:bg-moss hover:text-ink shadow-[0_0_18px_rgba(180,255,57,0.25)]"
      >
        Sign in
      </Button>
    </AuthLayout>
  );
}
