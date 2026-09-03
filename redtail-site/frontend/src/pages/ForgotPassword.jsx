import React from "react";
import { Link } from "react-router-dom";
import { Mail, ArrowLeft } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";

// There's no real account/password-reset system in production — the Lore
// login is a single shared password, not per-user accounts.
export default function ForgotPassword() {
  return (
    <AuthLayout
      icon={Mail}
      title="Password resets"
      subtitle="Not available yet"
      footer={
        <Link to="/login" className="text-primary font-medium hover:underline">
          <ArrowLeft className="w-3 h-3 inline mr-1" />Back to log in
        </Link>
      }
    >
      <p className="text-sm text-foreground text-center">
        Lore access is a single shared password, not per-user accounts, so there's nothing here to reset yet.
        Reach out to the team directly if you've lost the password.
      </p>
    </AuthLayout>
  );
}
