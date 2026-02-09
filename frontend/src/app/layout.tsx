import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Hardware Digest',
  description: 'AI-powered decision tracking for hardware engineering teams',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 font-sans antialiased">
        {children}
      </body>
    </html>
  )
}