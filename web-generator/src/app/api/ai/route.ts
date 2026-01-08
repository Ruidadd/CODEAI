import { NextRequest, NextResponse } from 'next/server'
import { generateWithAI, extractCode, type TaskType, type AIModel, MODEL_CAPABILITIES, TASK_MODEL_MAP } from '@/lib/ai-router'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { prompt, taskType, model } = body as {
      prompt: string
      taskType: TaskType
      model?: AIModel
    }

    if (!prompt) {
      return NextResponse.json(
        { error: 'Prompt is required' },
        { status: 400 }
      )
    }

    const validTaskTypes: TaskType[] = ['ui-design', 'code-gen', 'optimization', 'debug', 'general']
    if (!validTaskTypes.includes(taskType)) {
      return NextResponse.json(
        { error: 'Invalid task type' },
        { status: 400 }
      )
    }

    const response = await generateWithAI(prompt, taskType, model)

    // Extract code from the response
    const extractedCode = extractCode(response.content)

    return NextResponse.json({
      success: true,
      content: response.content,
      extractedCode,
      model: response.model,
      modelInfo: MODEL_CAPABILITIES[response.model],
      suggestedModel: TASK_MODEL_MAP[taskType],
      tokensUsed: response.tokensUsed,
      cost: response.cost,
    })
  } catch (error) {
    console.error('AI Generation Error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to generate' },
      { status: 500 }
    )
  }
}

// GET endpoint to get model info
export async function GET() {
  return NextResponse.json({
    models: MODEL_CAPABILITIES,
    taskModelMap: TASK_MODEL_MAP,
    taskTypes: ['ui-design', 'code-gen', 'optimization', 'debug', 'general'],
  })
}
