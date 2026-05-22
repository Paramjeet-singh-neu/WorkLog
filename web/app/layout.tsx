import type { Metadata } from "next";
import Link from "next/link";
import { getSession } from "@/lib/session";
import "./globals.css";

export const metadata: Metadata = {
  title: "Worklog",
  description: "Discord-native updates for project-building cohorts.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getSession();

  return (
    <html lang="en">
      <body>
        <main className="shell">
          <nav className="nav">
            <Link href="/">
              <strong>Worklog</strong>
            </Link>
            <div className="nav-links">
              <Link href="/">Feed</Link>
              <Link href="/showcase">Showcase</Link>
              <Link href="/admin">Admin</Link>
              {session ? <Link href="/profile">Profile</Link> : null}
              {session ? (
                <a className="button secondary" href="/api/auth/logout">
                  Log out
                </a>
              ) : (
                <a className="button" href="/api/auth/login">
                  Log in with Discord
                </a>
              )}
            </div>
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}
