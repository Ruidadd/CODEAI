"use client"

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sparkles, Code, Eye, Zap, Brain, CreditCard } from 'lucide-react'

export default function Home() {
  const features = [
    {
      icon: <Brain className="h-8 w-8 text-blue-500" />,
      title: 'Multi-Model AI',
      description: 'Intelligent task routing between Gemini (UI), Claude (Code), and GPT (Optimization)',
    },
    {
      icon: <Eye className="h-8 w-8 text-green-500" />,
      title: 'Live Preview',
      description: 'See your changes in real-time with responsive viewport switching',
    },
    {
      icon: <Code className="h-8 w-8 text-purple-500" />,
      title: 'Code Editor',
      description: 'Built-in Monaco editor with syntax highlighting and auto-complete',
    },
    {
      icon: <Zap className="h-8 w-8 text-yellow-500" />,
      title: 'Fast Generation',
      description: 'Stream-based generation for instant feedback as AI creates your code',
    },
    {
      icon: <Sparkles className="h-8 w-8 text-pink-500" />,
      title: 'Smart Prompts',
      description: 'Optimized prompts for each AI model to get the best results',
    },
    {
      icon: <CreditCard className="h-8 w-8 text-cyan-500" />,
      title: 'Stripe Integration',
      description: 'Seamless subscription management with Stripe payments',
    },
  ]

  const modelCapabilities = [
    {
      name: 'Google Gemini',
      color: 'bg-blue-500',
      tasks: ['UI/UX Design', 'Visual Layouts', 'Color Schemes', 'Responsive Design'],
    },
    {
      name: 'Claude (Anthropic)',
      color: 'bg-orange-500',
      tasks: ['Code Generation', 'Complex Logic', 'Debugging', 'Documentation'],
    },
    {
      name: 'GPT-4 (OpenAI)',
      color: 'bg-green-500',
      tasks: ['Optimization', 'Refactoring', 'Best Practices', 'General Tasks'],
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation */}
      <nav className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-blue-500" />
              <span className="text-xl font-bold text-white">AI Web Generator</span>
            </div>
            <div className="flex items-center gap-4">
              <Link href="/pricing">
                <Button variant="ghost">Pricing</Button>
              </Link>
              <Link href="/generator">
                <Button>Start Building</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            Build Websites with
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500">
              {' '}AI Power
            </span>
          </h1>
          <p className="text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
            Describe what you want, and our multi-model AI system will generate beautiful,
            responsive websites in seconds. Powered by Gemini, Claude, and GPT.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/generator">
              <Button size="lg" className="text-lg px-8">
                <Sparkles className="mr-2 h-5 w-5" />
                Start Generating
              </Button>
            </Link>
            <Link href="/pricing">
              <Button size="lg" variant="outline" className="text-lg px-8">
                View Pricing
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* AI Models Section */}
      <section className="py-16 px-4 bg-gray-800/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-4">
            Intelligent Model Selection
          </h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            Each AI model excels at different tasks. Our system automatically routes your
            requests to the best model for optimal results.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {modelCapabilities.map((model) => (
              <Card key={model.name} className="bg-gray-900/50 border-gray-700">
                <CardHeader>
                  <div className={`w-3 h-3 rounded-full ${model.color} mb-2`} />
                  <CardTitle className="text-white">{model.name}</CardTitle>
                  <CardDescription>Best for:</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {model.tasks.map((task) => (
                      <li key={task} className="flex items-center text-gray-300">
                        <span className={`w-1.5 h-1.5 rounded-full ${model.color} mr-2`} />
                        {task}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            Everything You Need
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <Card key={feature.title} className="bg-gray-800/50 border-gray-700">
                <CardHeader>
                  {feature.icon}
                  <CardTitle className="text-white">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-400">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Build Something Amazing?
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Start generating professional websites with AI today.
          </p>
          <Link href="/generator">
            <Button size="lg" className="text-lg px-12 py-6">
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 px-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-500" />
            <span className="text-gray-400">AI Web Generator</span>
          </div>
          <p className="text-gray-500 text-sm">
            Powered by Gemini, Claude, and GPT
          </p>
        </div>
      </footer>
    </div>
  )
}
