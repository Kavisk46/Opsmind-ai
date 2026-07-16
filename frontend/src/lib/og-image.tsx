import { ImageResponse } from "next/og";

// Shared by src/app/opengraph-image.tsx and src/app/twitter-image.tsx —
// Next.js requires each file convention to export its own `default`, so the
// actual rendering lives here once instead of being duplicated per file.
export const OG_IMAGE_ALT =
  "OpsMind AI — enterprise knowledge intelligence platform";
export const OG_IMAGE_SIZE = { width: 1200, height: 630 };
export const OG_IMAGE_CONTENT_TYPE = "image/png";

export function renderOgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#171717",
        }}
      >
        <div
          style={{
            display: "flex",
            fontSize: 88,
            fontWeight: 700,
            color: "#fafafa",
          }}
        >
          OpsMind AI
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 32,
            color: "#a3a3a3",
            marginTop: 20,
          }}
        >
          Enterprise knowledge intelligence, unified.
        </div>
      </div>
    ),
    OG_IMAGE_SIZE
  );
}
