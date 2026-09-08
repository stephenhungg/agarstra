import type { Metadata } from "next";
import "./globals.css";
import "./agarstra.css";
export const metadata: Metadata = {
  title: "agarstra — Old worlds. New dimensions.",
  description:
    "From game ROMs to editable 3D worlds. Explore agarstra’s provenance-first workflow for extraction, Blender authoring, visual review, and playable remakes.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-paper text-ink antialiased">{children}</body>
    </html>
  );
}
