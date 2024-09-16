import { Metadata } from "next";

export const SITE_CONFIG: Metadata = {
  title: {
    // write a default title for Multi Channel Business Ghat a ai powered website builder suggest something unique and catchy don't use the same words of ai powered website builder give a unique name
    default: "Multi Channel Business Ghat",
    template: `%s | Multi Channel Business Ghat`,
  },
  description:
    "Multi Channel Business Ghat is an AI powered website builder that helps you create a website in minutes. No coding skills required. Get started for free!",
  icons: {
    icon: [
      {
        url: "/icons/favicon.ico",
        href: "/icons/favicon.ico",
      },
    ],
  },
  openGraph: {
    title: "Multi Channel Business Ghat",
    description: "Multi Channel Business Ghat",
    images: [
      {
        url: "/assets/og-image.png",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    creator: "@shreyassihasane",
    title: "Multi Channel Business Ghat",
    description: "Multi Channel Business Ghat",
    images: [
      {
        url: "/assets/og-image.png",
      },
    ],
  },
  metadataBase: new URL("https://mutil-platform-chatbot.vercel.app/"),
};
