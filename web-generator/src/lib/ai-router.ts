import { GoogleGenerativeAI } from '@google/generative-ai'
import OpenAI from 'openai'
import Anthropic from '@anthropic-ai/sdk'

// AI Model types
export type AIModel = 'gemini' | 'claude' | 'gpt'
export type TaskType = 'ui-design' | 'code-gen' | 'optimization' | 'debug' | 'general'

// Task to model mapping - which model is best for each task
export const TASK_MODEL_MAP: Record<TaskType, AIModel> = {
  'ui-design': 'gemini',      // Gemini excels at visual/UI tasks
  'code-gen': 'claude',       // Claude is great for code generation
  'optimization': 'gpt',      // GPT is good at optimization suggestions
  'debug': 'claude',          // Claude is excellent at debugging
  'general': 'gpt',           // GPT for general tasks
}

// Model capabilities description
export const MODEL_CAPABILITIES = {
  gemini: {
    name: 'Google Gemini',
    strengths: ['UI/UX Design', 'Visual layouts', 'Color schemes', 'Responsive design'],
    bestFor: 'Frontend UI generation and visual design tasks',
    model: 'gemini-1.5-flash',
  },
  claude: {
    name: 'Claude (Anthropic)',
    strengths: ['Code generation', 'Complex logic', 'Debugging', 'Documentation'],
    bestFor: 'Backend code, complex algorithms, and code review',
    model: 'claude-sonnet-4-20250514',
  },
  gpt: {
    name: 'GPT-4 (OpenAI)',
    strengths: ['General tasks', 'Optimization', 'Refactoring', 'Best practices'],
    bestFor: 'General coding tasks and optimization',
    model: 'gpt-4o',
  },
}

// Initialize AI clients
const getGeminiClient = () => {
  if (!process.env.GOOGLE_AI_API_KEY) {
    throw new Error('GOOGLE_AI_API_KEY is not configured')
  }
  return new GoogleGenerativeAI(process.env.GOOGLE_AI_API_KEY)
}

const getOpenAIClient = () => {
  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY is not configured')
  }
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
}

const getAnthropicClient = () => {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('ANTHROPIC_API_KEY is not configured')
  }
  return new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
}

// System prompts for different task types
const SYSTEM_PROMPTS: Record<TaskType, string> = {
  'ui-design': `You are an expert UI/UX designer and frontend developer.
Generate modern, responsive, and visually appealing HTML/CSS code.
- Use Tailwind CSS classes for styling
- Create clean, semantic HTML structure
- Ensure mobile-first responsive design
- Include hover states and smooth transitions
- Follow accessibility best practices (WCAG)
Return ONLY the HTML code without any explanation.`,

  'code-gen': `You are an expert full-stack developer.
Generate clean, efficient, and well-documented code.
- Follow best practices and design patterns
- Include error handling
- Write type-safe code when applicable
- Add helpful comments for complex logic
Return ONLY the code without any explanation.`,

  'optimization': `You are an expert code optimizer.
Analyze and improve the given code for:
- Performance optimization
- Code readability
- Best practices
- Security improvements
Return the optimized code with brief comments explaining changes.`,

  'debug': `You are an expert debugger.
Analyze the code and:
- Identify bugs and issues
- Explain the root cause
- Provide fixed code
Return the corrected code with explanations.`,

  'general': `You are a helpful coding assistant.
Help with the given task, providing clear and concise responses.
When generating code, ensure it is clean and well-structured.`,
}

export interface AIResponse {
  content: string
  model: AIModel
  tokensUsed: number
  cost: number
}

// Generate with Gemini
async function generateWithGemini(prompt: string, systemPrompt: string): Promise<AIResponse> {
  const genAI = getGeminiClient()
  const model = genAI.getGenerativeModel({ model: MODEL_CAPABILITIES.gemini.model })

  const result = await model.generateContent({
    contents: [
      { role: 'user', parts: [{ text: `${systemPrompt}\n\n${prompt}` }] }
    ],
  })

  const response = result.response
  const text = response.text()
  const tokensUsed = response.usageMetadata?.totalTokenCount || 0

  return {
    content: text,
    model: 'gemini',
    tokensUsed,
    cost: tokensUsed * 0.000001, // Approximate cost
  }
}

// Generate with Claude
async function generateWithClaude(prompt: string, systemPrompt: string): Promise<AIResponse> {
  const client = getAnthropicClient()

  const message = await client.messages.create({
    model: MODEL_CAPABILITIES.claude.model,
    max_tokens: 4096,
    system: systemPrompt,
    messages: [{ role: 'user', content: prompt }],
  })

  const content = message.content[0].type === 'text' ? message.content[0].text : ''
  const tokensUsed = message.usage.input_tokens + message.usage.output_tokens

  return {
    content,
    model: 'claude',
    tokensUsed,
    cost: tokensUsed * 0.000015, // Approximate cost
  }
}

// Generate with GPT
async function generateWithGPT(prompt: string, systemPrompt: string): Promise<AIResponse> {
  const client = getOpenAIClient()

  const completion = await client.chat.completions.create({
    model: MODEL_CAPABILITIES.gpt.model,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: prompt },
    ],
    max_tokens: 4096,
  })

  const content = completion.choices[0]?.message?.content || ''
  const tokensUsed = completion.usage?.total_tokens || 0

  return {
    content,
    model: 'gpt',
    tokensUsed,
    cost: tokensUsed * 0.00003, // Approximate cost
  }
}

// Main AI Router function
export async function generateWithAI(
  prompt: string,
  taskType: TaskType,
  preferredModel?: AIModel
): Promise<AIResponse> {
  // Determine which model to use
  const model = preferredModel || TASK_MODEL_MAP[taskType]
  const systemPrompt = SYSTEM_PROMPTS[taskType]

  try {
    switch (model) {
      case 'gemini':
        return await generateWithGemini(prompt, systemPrompt)
      case 'claude':
        return await generateWithClaude(prompt, systemPrompt)
      case 'gpt':
        return await generateWithGPT(prompt, systemPrompt)
      default:
        throw new Error(`Unknown model: ${model}`)
    }
  } catch (error) {
    console.error(`Error with ${model}:`, error)
    // Fallback to another model if primary fails
    const fallbackModels: AIModel[] = ['gemini', 'claude', 'gpt'].filter(m => m !== model) as AIModel[]

    for (const fallback of fallbackModels) {
      try {
        console.log(`Trying fallback model: ${fallback}`)
        switch (fallback) {
          case 'gemini':
            return await generateWithGemini(prompt, systemPrompt)
          case 'claude':
            return await generateWithClaude(prompt, systemPrompt)
          case 'gpt':
            return await generateWithGPT(prompt, systemPrompt)
        }
      } catch (fallbackError) {
        console.error(`Fallback ${fallback} also failed:`, fallbackError)
        continue
      }
    }

    throw new Error('All AI models failed to generate response')
  }
}

// Helper to extract code from AI response
export function extractCode(response: string, language?: string): string {
  // Try to extract code blocks
  const codeBlockRegex = language
    ? new RegExp(`\`\`\`${language}\\s*([\\s\\S]*?)\`\`\``, 'i')
    : /```(?:\w+)?\s*([\s\S]*?)```/

  const match = response.match(codeBlockRegex)
  if (match) {
    return match[1].trim()
  }

  // If no code block, return the whole response (might be just code)
  return response.trim()
}

// Streaming generation (for real-time updates)
export async function* streamWithAI(
  prompt: string,
  taskType: TaskType,
  preferredModel?: AIModel
): AsyncGenerator<string> {
  const model = preferredModel || TASK_MODEL_MAP[taskType]
  const systemPrompt = SYSTEM_PROMPTS[taskType]

  switch (model) {
    case 'gemini': {
      const genAI = getGeminiClient()
      const geminiModel = genAI.getGenerativeModel({ model: MODEL_CAPABILITIES.gemini.model })
      const result = await geminiModel.generateContentStream({
        contents: [{ role: 'user', parts: [{ text: `${systemPrompt}\n\n${prompt}` }] }],
      })
      for await (const chunk of result.stream) {
        yield chunk.text()
      }
      break
    }
    case 'claude': {
      const client = getAnthropicClient()
      const stream = await client.messages.stream({
        model: MODEL_CAPABILITIES.claude.model,
        max_tokens: 4096,
        system: systemPrompt,
        messages: [{ role: 'user', content: prompt }],
      })
      for await (const event of stream) {
        if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
          yield event.delta.text
        }
      }
      break
    }
    case 'gpt': {
      const client = getOpenAIClient()
      const stream = await client.chat.completions.create({
        model: MODEL_CAPABILITIES.gpt.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: prompt },
        ],
        max_tokens: 4096,
        stream: true,
      })
      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content
        if (content) yield content
      }
      break
    }
  }
}
