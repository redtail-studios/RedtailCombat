import React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";

// There's no real account/password-reset system in production (see
// ForgotPassword.jsx) — nothing ever issues a reset link, so this page
// always shows the same message.
export default function ResetPassword() {
  return (
    <AuthLayout
      icon={AlertTriangle}
      title="Password resets"
      subtitle="Not available yet"
      footer={
        <Link to="/login" className="text-primary font-medium hover:underline">
          Back to log in
        </Link>
      }
    >
      <p className="text-sm text-foreground text-center">
        Lore access is a single shared password, not per-user accounts, so there's no reset link to redeem here.
        Reach out to the team directly if you've lost the password.
      </p>
    </AuthLayout>
  );
}
