"use client"

import { useState, useCallback } from 'react'

type TaskType = 'ui-design' | 'code-gen' | 'optimization' | 'debug' | 'general'
type AIModel = 'gemini' | 'claude' | 'gpt'

interface GenerationResult {
  content: string
  extractedCode: string
  model: AIModel
  tokensUsed: number
  cost: number
}

interface UseAIReturn {
  generate: (prompt: string, taskType: TaskType, model?: AIModel) => Promise<GenerationResult | null>
  streamGenerate: (
    prompt: string,
    taskType: TaskType,
    onChunk: (chunk: string) => void,
    model?: AIModel
  ) => Promise<void>
  isLoading: boolean
  error: string | null
}

export function useAI(): UseAIReturn {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generate = useCallback(async (
    prompt: string,
    taskType: TaskType,
    model?: AIModel
  ): Promise<GenerationResult | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, taskType, model }),
      })

      const data = await response.json()

      if (data.error) {
        throw new Error(data.error)
      }

      return {
        content: data.content,
        extractedCode: data.extractedCode,
        model: data.model,
        tokensUsed: data.tokensUsed,
        cost: data.cost,
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Generation failed'
      setError(message)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [])

  const streamGenerate = useCallback(async (
    prompt: string,
    taskType: TaskType,
    onChunk: (chunk: string) => void,
    model?: AIModel
  ): Promise<void> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/ai/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, taskType, model }),
      })

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader available')

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
                onChunk(parsed.chunk)
              }
              if (parsed.error) {
                throw new Error(parsed.error)
              }
            } catch {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Stream failed'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { generate, streamGenerate, isLoading, error }
}
