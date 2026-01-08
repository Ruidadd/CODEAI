"use client"

import { useRef, useEffect } from 'react'
import Editor, { OnMount } from '@monaco-editor/react'
import type { editor } from 'monaco-editor'

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  language: 'html' | 'css' | 'javascript' | 'typescript'
  height?: string
  readOnly?: boolean
}

export function CodeEditor({
  value,
  onChange,
  language,
  height = '100%',
  readOnly = false,
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor
  }

  useEffect(() => {
    if (editorRef.current) {
      const model = editorRef.current.getModel()
      if (model && model.getValue() !== value) {
        model.setValue(value)
      }
    }
  }, [value])

  return (
    <Editor
      height={height}
      language={language}
      value={value}
      theme="vs-dark"
      onChange={(v) => onChange(v || '')}
      onMount={handleEditorDidMount}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
        wordWrap: 'on',
        readOnly,
        formatOnPaste: true,
        formatOnType: true,
      }}
    />
  )
}
