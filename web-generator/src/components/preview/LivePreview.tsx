"use client"

import { useEffect, useRef, useState } from 'react'
import { RefreshCw, Smartphone, Monitor, Tablet } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface LivePreviewProps {
  html: string
  css: string
  js: string
  className?: string
}

type ViewportSize = 'mobile' | 'tablet' | 'desktop'

const VIEWPORT_SIZES: Record<ViewportSize, { width: string; label: string; icon: React.ReactNode }> = {
  mobile: { width: '375px', label: 'Mobile', icon: <Smartphone className="h-4 w-4" /> },
  tablet: { width: '768px', label: 'Tablet', icon: <Tablet className="h-4 w-4" /> },
  desktop: { width: '100%', label: 'Desktop', icon: <Monitor className="h-4 w-4" /> },
}

export function LivePreview({ html, css, js, className }: LivePreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [viewport, setViewport] = useState<ViewportSize>('desktop')
  const [key, setKey] = useState(0)

  const generatePreviewDoc = () => {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    ${css}
  </style>
</head>
<body>
  ${html}
  <script>
    try {
      ${js}
    } catch (e) {
      console.error('Preview JS Error:', e);
    }
  </script>
</body>
</html>
    `.trim()
  }

  useEffect(() => {
    if (iframeRef.current) {
      const doc = iframeRef.current.contentDocument
      if (doc) {
        doc.open()
        doc.write(generatePreviewDoc())
        doc.close()
      }
    }
  }, [html, css, js, key])

  const handleRefresh = () => {
    setKey((k) => k + 1)
  }

  return (
    <div className={cn("flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden", className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-1">
          {(Object.keys(VIEWPORT_SIZES) as ViewportSize[]).map((size) => (
            <Button
              key={size}
              variant={viewport === size ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewport(size)}
              title={VIEWPORT_SIZES[size].label}
            >
              {VIEWPORT_SIZES[size].icon}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {viewport === 'desktop' ? 'Full Width' : VIEWPORT_SIZES[viewport].width}
          </span>
          <Button variant="ghost" size="sm" onClick={handleRefresh} title="Refresh Preview">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Preview Area */}
      <div className="flex-1 overflow-auto bg-white flex justify-center p-4">
        <div
          style={{
            width: VIEWPORT_SIZES[viewport].width,
            height: '100%',
            transition: 'width 0.3s ease',
          }}
          className="bg-white shadow-lg"
        >
          <iframe
            key={key}
            ref={iframeRef}
            className="w-full h-full border-0"
            title="Preview"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
      </div>
    </div>
  )
}
