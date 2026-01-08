import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Web Generator - Create Websites with AI',
  description: 'Generate beautiful, responsive websites using AI. Powered by Gemini, Claude, and GPT models.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
