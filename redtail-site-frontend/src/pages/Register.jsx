import { Navigate } from "react-router-dom";

// /login now collects waitlist info first (name + email) before showing the
// sign-in form, so there's no separate "join" flow to keep here.
export default function Register() {
  return <Navigate to="/login" replace />;
}
