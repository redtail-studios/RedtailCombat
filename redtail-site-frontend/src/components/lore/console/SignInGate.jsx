import React, { useState } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import PixelButton from "@/components/PixelButton";
import PixelFrame from "@/components/PixelFrame";
import { useDashboardAuth } from "@/lib/DashboardAuthContext";
import { Loader2 } from "lucide-react";

const fieldClass = "h-11 rounded-none bg-ink border-white/15 font-mono text-sm";

export default function SignInGate() {
  const { dashboardLogin } = useDashboardAuth();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("waitlist");

  // sign-in state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginErr, setLoginErr] = useState("");

  // waitlist state
  const [first, setFirst] = useState("");
  const [last, setLast] = useState("");
  const [email, setEmail] = useState("");
  const [wlErr, setWlErr] = useState("");
  const [wlOk, setWlOk] = useState(false);
  const [wlLoading, setWlLoading] = useState(false);

  const openGate = () => {
    setMode("waitlist");
    setLoginErr("");
    setOpen(true);
  };

  const handleLogin = (e) => {
    e.preventDefault();
    setLoginErr("");
    const result = dashboardLogin(username.trim(), password);
    if (!result.success) {
      setLoginErr("Wrong username or password.");
      return;
    }
    setOpen(false);
  };

  const handleWaitlist = async (e) => {
    e.preventDefault();
    setWlErr("");
    setWlOk(false);
    if (!first.trim() || !last.trim()) {
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
        body: JSON.stringify({ first_name: first.trim(), last_name: last.trim(), email: email.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Something went wrong");
      setWlOk(true);
      setFirst(""); setLast(""); setEmail("");
    } catch (err) {
      setWlErr(err.message || "Something went wrong. Try again.");
    } finally {
      setWlLoading(false);
    }
  };

  return (
    <>
      <PixelFrame tone="red" inner="p-8 sm:p-10 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-pulse mb-3">Internal tool · sign-in required</p>
        <h3 className="font-pixel text-base sm:text-lg text-platinum mb-3">Launch the Lore console</h3>
        <p className="text-platinum/70 max-w-xl mx-auto mb-6">
          Scrape the market, generate a live report, or upload a game to redesign — from the same real data behind this page.
        </p>
        <PixelButton onClick={openGate}>▸ Launch Lore</PixelButton>
      </PixelFrame>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md bg-panel border-white/15 text-platinum rounded-none p-0 overflow-hidden">
          <DialogTitle className="sr-only">{mode === "signin" ? "Sign in to Lore" : "Join the Lore waitlist"}</DialogTitle>
          <div className="p-[2px] bg-pulse">
            <div className="bg-panel p-8">
              {mode === "signin" ? (
                <form onSubmit={handleLogin} className="space-y-4">
                  <p className="font-mono text-xs uppercase tracking-[0.22em] text-pulse font-bold">Restricted</p>
                  <h2 className="font-pixel text-base leading-relaxed text-platinum">Sign in to Lore</h2>
                  <div className="space-y-2">
                    <Label htmlFor="lore-user" className="font-mono text-xs uppercase tracking-wider text-platinum/60">Username</Label>
                    <Input id="lore-user" autoComplete="username" autoFocus value={username}
                      onChange={(e) => setUsername(e.target.value)} className={fieldClass} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lore-pass" className="font-mono text-xs uppercase tracking-wider text-platinum/60">Password</Label>
                    <Input id="lore-pass" type="password" autoComplete="current-password" value={password}
                      onChange={(e) => setPassword(e.target.value)} className={fieldClass} />
                  </div>
                  {loginErr && <p className="text-pulse font-mono text-xs">{loginErr}</p>}
                  <PixelButton type="submit" className="w-full">Enter ▸</PixelButton>
                  <p className="text-center font-mono text-xs text-platinum/60">
                    Not a member?{" "}
                    <button type="button" onClick={() => setMode("waitlist")} className="text-moss font-medium hover:underline">
                      Join our waitlist
                    </button>
                  </p>
                </form>
              ) : (
                <form onSubmit={handleWaitlist} className="space-y-4">
                  <p className="font-mono text-xs uppercase tracking-[0.22em] text-pulse font-bold">Waitlist</p>
                  <h2 className="font-pixel text-base leading-relaxed text-platinum">Join the Lore waitlist</h2>
                  <div className="space-y-2">
                    <Label htmlFor="lore-first" className="font-mono text-xs uppercase tracking-wider text-platinum/60">First name</Label>
                    <Input id="lore-first" autoComplete="given-name" autoFocus value={first}
                      onChange={(e) => setFirst(e.target.value)} className={fieldClass} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lore-last" className="font-mono text-xs uppercase tracking-wider text-platinum/60">Last name</Label>
                    <Input id="lore-last" autoComplete="family-name" value={last}
                      onChange={(e) => setLast(e.target.value)} className={fieldClass} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lore-email" className="font-mono text-xs uppercase tracking-wider text-platinum/60">Email</Label>
                    <Input id="lore-email" type="email" autoComplete="email" value={email}
                      onChange={(e) => setEmail(e.target.value)} className={fieldClass} />
                  </div>
                  {wlErr && <p className="text-pulse font-mono text-xs">{wlErr}</p>}
                  {wlOk && <p className="text-moss font-mono text-xs">You're on the list — we'll be in touch.</p>}
                  <PixelButton type="submit" className="w-full" disabled={wlLoading}>
                    {wlLoading ? (<><Loader2 className="w-4 h-4 animate-spin" /> Joining…</>) : "Join waitlist ▸"}
                  </PixelButton>
                  <p className="text-center font-mono text-xs text-platinum/60">
                    Already a member?{" "}
                    <button type="button" onClick={() => setMode("signin")} className="text-moss font-medium hover:underline">
                      Sign in here
                    </button>
                  </p>
                </form>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
