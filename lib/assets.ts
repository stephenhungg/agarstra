import assetMap from "./asset-map.json";
/** Resolve captured source URLs to same-origin files; unknown URLs remain intact. */
export function asset(source: string): string {
  if (!source.startsWith("http")) return source;
  return (
    (assetMap as Record<string, string>)[new URL(source).pathname] ?? source
  );
}
