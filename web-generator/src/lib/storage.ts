// Simple file-based storage for development
// In production, replace with Prisma + PostgreSQL

import { promises as fs } from 'fs'
import path from 'path'

const DATA_DIR = path.join(process.cwd(), 'data')

interface Project {
  id: string
  name: string
  description: string
  htmlContent: string
  cssContent: string
  jsContent: string
  userId: string
  createdAt: string
  updatedAt: string
}

interface User {
  id: string
  email: string
  name?: string
  stripeCustomerId?: string
  stripeSubscriptionId?: string
  createdAt: string
}

// Ensure data directory exists
async function ensureDataDir() {
  try {
    await fs.mkdir(DATA_DIR, { recursive: true })
  } catch {
    // Directory might already exist
  }
}

// Generate simple ID
function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2)
}

// Projects
export async function getProjects(userId: string): Promise<Project[]> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'projects.json')

  try {
    const data = await fs.readFile(filePath, 'utf-8')
    const projects: Project[] = JSON.parse(data)
    return projects.filter(p => p.userId === userId)
  } catch {
    return []
  }
}

export async function createProject(data: Omit<Project, 'id' | 'createdAt' | 'updatedAt'>): Promise<Project> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'projects.json')

  let projects: Project[] = []
  try {
    const existingData = await fs.readFile(filePath, 'utf-8')
    projects = JSON.parse(existingData)
  } catch {
    // File doesn't exist yet
  }

  const newProject: Project = {
    ...data,
    id: generateId(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }

  projects.push(newProject)
  await fs.writeFile(filePath, JSON.stringify(projects, null, 2))

  return newProject
}

export async function updateProject(id: string, data: Partial<Project>): Promise<Project | null> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'projects.json')

  try {
    const existingData = await fs.readFile(filePath, 'utf-8')
    const projects: Project[] = JSON.parse(existingData)
    const index = projects.findIndex(p => p.id === id)

    if (index === -1) return null

    projects[index] = {
      ...projects[index],
      ...data,
      updatedAt: new Date().toISOString(),
    }

    await fs.writeFile(filePath, JSON.stringify(projects, null, 2))
    return projects[index]
  } catch {
    return null
  }
}

export async function deleteProject(id: string): Promise<boolean> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'projects.json')

  try {
    const existingData = await fs.readFile(filePath, 'utf-8')
    const projects: Project[] = JSON.parse(existingData)
    const filtered = projects.filter(p => p.id !== id)

    await fs.writeFile(filePath, JSON.stringify(filtered, null, 2))
    return filtered.length !== projects.length
  } catch {
    return false
  }
}

// Users
export async function getUser(id: string): Promise<User | null> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'users.json')

  try {
    const data = await fs.readFile(filePath, 'utf-8')
    const users: User[] = JSON.parse(data)
    return users.find(u => u.id === id) || null
  } catch {
    return null
  }
}

export async function createUser(data: Omit<User, 'id' | 'createdAt'>): Promise<User> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'users.json')

  let users: User[] = []
  try {
    const existingData = await fs.readFile(filePath, 'utf-8')
    users = JSON.parse(existingData)
  } catch {
    // File doesn't exist yet
  }

  const newUser: User = {
    ...data,
    id: generateId(),
    createdAt: new Date().toISOString(),
  }

  users.push(newUser)
  await fs.writeFile(filePath, JSON.stringify(users, null, 2))

  return newUser
}

export async function updateUser(id: string, data: Partial<User>): Promise<User | null> {
  await ensureDataDir()
  const filePath = path.join(DATA_DIR, 'users.json')

  try {
    const existingData = await fs.readFile(filePath, 'utf-8')
    const users: User[] = JSON.parse(existingData)
    const index = users.findIndex(u => u.id === id)

    if (index === -1) return null

    users[index] = { ...users[index], ...data }
    await fs.writeFile(filePath, JSON.stringify(users, null, 2))
    return users[index]
  } catch {
    return null
  }
}
