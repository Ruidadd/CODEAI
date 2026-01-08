import { NextRequest, NextResponse } from 'next/server'
import { getProjects, createProject, updateProject, deleteProject } from '@/lib/storage'

// Get all projects
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const userId = searchParams.get('userId')

    if (!userId) {
      return NextResponse.json(
        { error: 'User ID is required' },
        { status: 400 }
      )
    }

    const projects = await getProjects(userId)
    return NextResponse.json({ projects })
  } catch (error) {
    console.error('Error fetching projects:', error)
    return NextResponse.json(
      { error: 'Failed to fetch projects' },
      { status: 500 }
    )
  }
}

// Create a new project
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name, description, userId, htmlContent, cssContent, jsContent } = body

    if (!name || !userId) {
      return NextResponse.json(
        { error: 'Name and userId are required' },
        { status: 400 }
      )
    }

    const project = await createProject({
      name,
      description: description || '',
      userId,
      htmlContent: htmlContent || '',
      cssContent: cssContent || '',
      jsContent: jsContent || '',
    })

    return NextResponse.json({ project }, { status: 201 })
  } catch (error) {
    console.error('Error creating project:', error)
    return NextResponse.json(
      { error: 'Failed to create project' },
      { status: 500 }
    )
  }
}

// Update a project
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { id, name, description, htmlContent, cssContent, jsContent } = body

    if (!id) {
      return NextResponse.json(
        { error: 'Project ID is required' },
        { status: 400 }
      )
    }

    const project = await updateProject(id, {
      ...(name && { name }),
      ...(description !== undefined && { description }),
      ...(htmlContent !== undefined && { htmlContent }),
      ...(cssContent !== undefined && { cssContent }),
      ...(jsContent !== undefined && { jsContent }),
    })

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({ project })
  } catch (error) {
    console.error('Error updating project:', error)
    return NextResponse.json(
      { error: 'Failed to update project' },
      { status: 500 }
    )
  }
}

// Delete a project
export async function DELETE(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const id = searchParams.get('id')

    if (!id) {
      return NextResponse.json(
        { error: 'Project ID is required' },
        { status: 400 }
      )
    }

    const deleted = await deleteProject(id)

    if (!deleted) {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting project:', error)
    return NextResponse.json(
      { error: 'Failed to delete project' },
      { status: 500 }
    )
  }
}
