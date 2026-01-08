"use client"

import { useState, useCallback, useRef } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CodeEditor } from '@/components/editor/CodeEditor'
import { LivePreview } from '@/components/preview/LivePreview'
import {
  Sparkles,
  Send,
  Loader2,
  Download,
  Save,
  Trash2,
  Home,
  Wand2,
  Code,
  Palette,
  Bug,
  Zap,
  Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'

type TaskType = 'ui-design' | 'code-gen' | 'optimization' | 'debug' | 'general'
type AIModel = 'gemini' | 'claude' | 'gpt' | 'auto'

const TASK_OPTIONS = [
  { value: 'ui-design', label: 'UI Design', icon: Palette, description: 'Generate visual layouts' },
  { value: 'code-gen', label: 'Code Generation', icon: Code, description: 'Write functional code' },
  { value: 'optimization', label: 'Optimization', icon: Zap, description: 'Improve existing code' },
  { value: 'debug', label: 'Debug', icon: Bug, description: 'Fix issues in code' },
  { value: 'general', label: 'General', icon: Wand2, description: 'General assistance' },
]

const MODEL_OPTIONS = [
  { value: 'auto', label: 'Auto (Recommended)' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'claude', label: 'Claude (Anthropic)' },
  { value: 'gpt', label: 'GPT-4 (OpenAI)' },
]

const EXAMPLE_PROMPTS = [
  'Create a modern landing page for a SaaS product with a hero section, features grid, and pricing cards',
  'Design a responsive navigation bar with a logo, menu items, and a call-to-action button',
  'Build a user profile card component with avatar, name, bio, and social links',
  'Create a dark-themed dashboard layout with sidebar navigation and stats cards',
  'Design a contact form with name, email, message fields and validation styles',
]

export default function GeneratorPage() {
  const [prompt, setPrompt] = useState('')
  const [taskType, setTaskType] = useState<TaskType>('ui-design')
  const [model, setModel] = useState<AIModel>('auto')
  const [isGenerating, setIsGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState('html')

  // Code states
  const [htmlCode, setHtmlCode] = useState(`<div class="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center p-4">
  <div class="text-center">
    <h1 class="text-4xl font-bold text-white mb-4">Welcome to AI Web Generator</h1>
    <p class="text-gray-400 mb-6">Describe what you want to build, and watch the magic happen!</p>
    <button class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-medium transition-colors">
      Get Started
    </button>
  </div>
</div>`)
  const [cssCode, setCssCode] = useState('')
  const [jsCode, setJsCode] = useState('')

  // Generation info
  const [generationInfo, setGenerationInfo] = useState<{
    model: string
    tokensUsed: number
    cost: number
  } | null>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || isGenerating) return

    setIsGenerating(true)
    setGenerationInfo(null)

    try {
      const response = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          taskType,
          model: model === 'auto' ? undefined : model,
        }),
      })

      const data = await response.json()

      if (data.error) {
        throw new Error(data.error)
      }

      // Update code based on task type
      const code = data.extractedCode || data.content

      if (taskType === 'ui-design' || taskType === 'general') {
        // Check if response contains HTML
        if (code.includes('<') && code.includes('>')) {
          setHtmlCode(code)
          setActiveTab('preview')
        }
      } else if (taskType === 'code-gen') {
        // Try to detect code type
        if (code.includes('function') || code.includes('const') || code.includes('let')) {
          setJsCode(code)
          setActiveTab('javascript')
        } else if (code.includes('<')) {
          setHtmlCode(code)
          setActiveTab('html')
        }
      }

      setGenerationInfo({
        model: data.model,
        tokensUsed: data.tokensUsed,
        cost: data.cost,
      })
    } catch (error) {
      console.error('Generation error:', error)
      alert(error instanceof Error ? error.message : 'Failed to generate. Please check your API keys.')
    } finally {
      setIsGenerating(false)
    }
  }, [prompt, taskType, model, isGenerating])

  const handleStreamGenerate = useCallback(async () => {
    if (!prompt.trim() || isGenerating) return

    setIsGenerating(true)
    setGenerationInfo(null)

    let fullContent = ''

    try {
      const response = await fetch('/api/ai/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          taskType,
          model: model === 'auto' ? undefined : model,
        }),
      })

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)
              if (parsed.chunk) {
                fullContent += parsed.chunk
                // Update preview in real-time
                if (taskType === 'ui-design') {
                  setHtmlCode(fullContent)
                }
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }

      setActiveTab('preview')
    } catch (error) {
      console.error('Stream error:', error)
      alert('Failed to stream. Please try regular generation.')
    } finally {
      setIsGenerating(false)
    }
  }, [prompt, taskType, model, isGenerating])

  const handleExport = useCallback(() => {
    const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Website</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
${cssCode}
  </style>
</head>
<body>
${htmlCode}
  <script>
${jsCode}
  </script>
</body>
</html>`

    const blob = new Blob([fullHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'generated-website.html'
    a.click()
    URL.revokeObjectURL(url)
  }, [htmlCode, cssCode, jsCode])

  const handleClear = useCallback(() => {
    setHtmlCode('')
    setCssCode('')
    setJsCode('')
    setPrompt('')
    setGenerationInfo(null)
  }, [])

  const handleExampleClick = (example: string) => {
    setPrompt(example)
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/95 backdrop-blur-sm sticky top-0 z-50">
        <div className="flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 text-white hover:text-blue-400 transition-colors">
              <Home className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-500" />
              <span className="font-semibold text-white">AI Web Generator</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleClear}>
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
            <Button variant="ghost" size="sm">
              <Save className="h-4 w-4 mr-1" />
              Save
            </Button>
            <Button variant="secondary" size="sm" onClick={handleExport}>
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Left Panel - Input & Controls */}
        <div className="w-96 border-r border-gray-800 flex flex-col bg-gray-900/50">
          {/* Task Type Selector */}
          <div className="p-4 border-b border-gray-800">
            <label className="text-sm font-medium text-gray-400 mb-2 block">Task Type</label>
            <div className="grid grid-cols-5 gap-1">
              {TASK_OPTIONS.map((task) => {
                const Icon = task.icon
                return (
                  <button
                    key={task.value}
                    onClick={() => setTaskType(task.value as TaskType)}
                    className={cn(
                      'flex flex-col items-center p-2 rounded-lg transition-colors',
                      taskType === task.value
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'hover:bg-gray-800 text-gray-400'
                    )}
                    title={task.description}
                  >
                    <Icon className="h-5 w-5 mb-1" />
                    <span className="text-xs">{task.label.split(' ')[0]}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Model Selector */}
          <div className="p-4 border-b border-gray-800">
            <label className="text-sm font-medium text-gray-400 mb-2 block">AI Model</label>
            <Select
              value={model}
              onChange={(e) => setModel(e.target.value as AIModel)}
              options={MODEL_OPTIONS}
              className="bg-gray-800 border-gray-700 text-white"
            />
          </div>

          {/* Prompt Input */}
          <div className="flex-1 p-4 flex flex-col">
            <label className="text-sm font-medium text-gray-400 mb-2 block">
              Describe what you want to create
            </label>
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Create a modern landing page with a hero section, feature cards, and a contact form..."
              className="flex-1 min-h-[200px] p-3 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  handleGenerate()
                }
              }}
            />

            {/* Generate Buttons */}
            <div className="mt-4 flex gap-2">
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="flex-1"
              >
                {isGenerating ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                Generate
              </Button>
              <Button
                onClick={handleStreamGenerate}
                disabled={isGenerating || !prompt.trim()}
                variant="secondary"
                title="Stream generation for real-time preview"
              >
                <Zap className="h-4 w-4" />
              </Button>
            </div>

            {/* Generation Info */}
            {generationInfo && (
              <div className="mt-4 p-3 rounded-lg bg-gray-800 text-sm">
                <div className="flex items-center gap-2 text-gray-400 mb-2">
                  <Info className="h-4 w-4" />
                  <span>Generation Info</span>
                </div>
                <div className="space-y-1 text-gray-300">
                  <p>Model: <span className="text-blue-400">{generationInfo.model}</span></p>
                  <p>Tokens: <span className="text-green-400">{generationInfo.tokensUsed}</span></p>
                  <p>Cost: <span className="text-yellow-400">${generationInfo.cost.toFixed(4)}</span></p>
                </div>
              </div>
            )}
          </div>

          {/* Example Prompts */}
          <div className="p-4 border-t border-gray-800">
            <p className="text-sm font-medium text-gray-400 mb-2">Try an example:</p>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {EXAMPLE_PROMPTS.map((example, index) => (
                <button
                  key={index}
                  onClick={() => handleExampleClick(example)}
                  className="w-full text-left p-2 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-gray-800 transition-colors line-clamp-2"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel - Editor & Preview */}
        <div className="flex-1 flex flex-col">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <div className="border-b border-gray-800 px-4">
              <TabsList className="bg-transparent border-0 h-12">
                <TabsTrigger value="preview" className="data-[state=active]:bg-gray-800">
                  Preview
                </TabsTrigger>
                <TabsTrigger value="html" className="data-[state=active]:bg-gray-800">
                  HTML
                </TabsTrigger>
                <TabsTrigger value="css" className="data-[state=active]:bg-gray-800">
                  CSS
                </TabsTrigger>
                <TabsTrigger value="javascript" className="data-[state=active]:bg-gray-800">
                  JavaScript
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="preview" className="flex-1 m-0">
              <LivePreview html={htmlCode} css={cssCode} js={jsCode} className="h-full" />
            </TabsContent>

            <TabsContent value="html" className="flex-1 m-0">
              <CodeEditor
                value={htmlCode}
                onChange={setHtmlCode}
                language="html"
              />
            </TabsContent>

            <TabsContent value="css" className="flex-1 m-0">
              <CodeEditor
                value={cssCode}
                onChange={setCssCode}
                language="css"
              />
            </TabsContent>

            <TabsContent value="javascript" className="flex-1 m-0">
              <CodeEditor
                value={jsCode}
                onChange={setJsCode}
                language="javascript"
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
