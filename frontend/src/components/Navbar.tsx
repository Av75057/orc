import { Link, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/artifacts", label: "Artifacts" },
  { to: "/evidence", label: "Evidence" },
  { to: "/logs", label: "Logs" },
];

export default function Navbar() {
  const loc = useLocation();
  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
        <span className="font-bold text-lg text-indigo-600">GRACE</span>
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className={
              loc.pathname === l.to
                ? "text-indigo-600 font-medium"
                : "text-gray-600 hover:text-gray-900"
            }
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

