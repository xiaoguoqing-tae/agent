<template>
  <div class="markdown-body" v-html="renderedHtml"></div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

// highlight.js
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import php from 'highlight.js/lib/languages/php'
import javascript from 'highlight.js/lib/languages/javascript'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'

// 只注册一次语言
if (!hljs.getLanguage('python')) {
  hljs.registerLanguage('python', python)
  hljs.registerLanguage('php', php)
  hljs.registerLanguage('py', python)
  hljs.registerLanguage('javascript', javascript)
  hljs.registerLanguage('js', javascript)
  hljs.registerLanguage('bash', bash)
  hljs.registerLanguage('sh', bash)
  hljs.registerLanguage('json', json)
}

import 'highlight.js/styles/github.css'

const props = defineProps({
  content: { type: String, default: '' }
})

// ========== 全局代码存储 ==========
if (typeof window !== 'undefined') {
  if (!window.__codeIdCounter) window.__codeIdCounter = 0
  if (!window.__codeStorage) window.__codeStorage = new Map()
}

function generateId() {
  return `code-${Date.now()}-${window.__codeIdCounter++}`
}

// ========== 高亮函数（自己控制）==========
function highlightCode(code, lang) {
  const language = lang ? lang.toLowerCase() : ''
  
  if (language && hljs.getLanguage(language)) {
    try {
      return hljs.highlight(code, { language }).value
    } catch (e) {
      console.warn('高亮失败:', e)
    }
  }
  
  // 自动检测或返回原始代码（转义后）
  try {
    return hljs.highlightAuto(code).value
  } catch (e) {
    return escapeHtml(code)
  }
}

// HTML 转义
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// ========== 确保 marked 只配置一次 ==========
if (!window.__markedConfigured) {
  
  const renderer = new marked.Renderer()
  
  // ========== 关键：完全自己控制代码块渲染和高亮 ==========
  renderer.code = function({ text, lang, escaped }) {
    const language = (lang || '').toLowerCase()
    const displayLang = lang || 'text'
    
    // 生成 ID 并存储原始代码（用于复制）
    const codeId = generateId()
    window.__codeStorage.set(codeId, text)
    
    // 自己调用高亮，得到带 <span> 的 HTML
    const highlightedHtml = highlightCode(text, language)
    
    // 返回完整结构：header + 高亮后的代码
    // 关键：highlightedHtml 已经包含 <span class="hljs-xxx">，直接插入
    return `
      <div class="code-block-wrapper">
        <div class="code-header">
          <span class="code-lang">${displayLang.toUpperCase()}</span>
          <button class="copy-btn" onclick="window.copyCodeById('${codeId}')" type="button">
            <svg class="copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span class="copy-text">复制</span>
          </button>
        </div>
        <div class="code-content">
          <pre><code class="hljs language-${language}">${highlightedHtml}</code></pre>
        </div>
      </div>
    `
  }

  // 行内代码也自己处理
  renderer.codespan = function({ text }) {
    // 行内代码简单高亮或转义
    const highlighted = highlightCode(text, '')
    // 去掉外层包裹，只保留内容
    const inner = highlighted.replace(/^<span class="hljs-[^"]*">|<\/span>$/g, '')
    return `<code>${inner || escapeHtml(text)}</code>`
  }

  marked.setOptions({
    renderer: renderer,
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
  })
  
  window.__markedConfigured = true
}

// ========== 复制函数 ==========
if (typeof window !== 'undefined' && !window.copyCodeById) {
  window.copyCodeById = async function(codeId) {
    const storage = window.__codeStorage
    
    if (!storage || !storage.has(codeId)) {
      console.error('找不到代码，ID:', codeId)
      alert('复制失败：代码不存在')
      return
    }
    
    // 关键：获取存储的原始代码（纯文本，无 HTML）
    const originalCode = storage.get(codeId)
    
    try {
      await navigator.clipboard.writeText(originalCode)
      
      // 更新按钮状态
      const buttons = document.querySelectorAll(`button[onclick="window.copyCodeById('${codeId}')"]`)
      buttons.forEach(btn => {
        const textSpan = btn.querySelector('.copy-text')
        if (textSpan) {
          btn.classList.add('copied')
          textSpan.innerText = '已复制!'
          setTimeout(() => {
            btn.classList.remove('copied')
            textSpan.innerText = '复制'
          }, 2000)
        }
      })
    } catch (err) {
      console.error('复制失败:', err)
      alert('复制失败：' + err.message)
    }
  }
}

// ========== 计算属性 ==========
const renderedHtml = computed(() => {
  if (!props.content?.trim()) return ''
  
  try {
    return marked.parse(props.content)
  } catch (err) {
    console.error('解析失败:', err)
    return `<pre>${escapeHtml(props.content)}</pre>`
  }
})
</script>

<style scoped>
/* 样式保持不变 */
.markdown-body { line-height: 1.6; color: #24292f; font-size: 14px; }
.markdown-body :deep(p) { margin: 0 0 12px 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }

.markdown-body :deep(h1, h2, h3, h4, h5, h6) { 
  margin: 16px 0 12px 0; 
  font-weight: 600; 
  line-height: 1.25; 
  color: #24292f; 
}
.markdown-body :deep(h1) { font-size: 1.5em; border-bottom: 1px solid #d8dee4; padding-bottom: 8px; }
.markdown-body :deep(h2) { font-size: 1.25em; border-bottom: 1px solid #d8dee4; padding-bottom: 6px; }
.markdown-body :deep(h3) { font-size: 1.125em; }

.markdown-body :deep(ul, ol) { padding-left: 24px; margin: 0 0 12px 0; }
.markdown-body :deep(li) { margin: 4px 0; }

.markdown-body :deep(blockquote) { 
  margin: 0 0 12px 0; 
  padding: 0 16px; 
  border-left: 4px solid #d0d7de; 
  color: #57606a; 
}

.markdown-body :deep(a) { color: #0969da; text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; }

.markdown-body :deep(table) { 
  width: 100%; 
  border-collapse: collapse; 
  margin: 12px 0; 
  display: block;
  overflow-x: auto;
}
.markdown-body :deep(th, td) { 
  padding: 8px 12px; 
  border: 1px solid #d0d7de; 
  text-align: left; 
}
.markdown-body :deep(th) { background: #f6f8fa; font-weight: 600; }

.markdown-body :deep(code:not(pre code)) { 
  padding: 2px 6px; 
  font-size: 85%; 
  background: rgba(175, 184, 193, 0.2); 
  border-radius: 6px; 
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; 
}

/* 代码块 */
.markdown-body :deep(.code-block-wrapper) { 
  margin: 12px 0; 
  border: 1px solid #d0d7de; 
  border-radius: 8px; 
  overflow: hidden; 
  background: #f6f8fa; 
}

.markdown-body :deep(.code-header) { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  padding: 8px 16px; 
  background: #f3f4f6; 
  border-bottom: 1px solid #d0d7de; 
  font-size: 12px; 
}

.markdown-body :deep(.code-lang) { 
  font-weight: 600; 
  color: #57606a; 
  text-transform: uppercase; 
  letter-spacing: 0.5px; 
}

.markdown-body :deep(.copy-btn) { 
  display: inline-flex; 
  align-items: center; 
  gap: 6px; 
  padding: 4px 10px; 
  font-size: 12px; 
  font-weight: 500; 
  color: #24292f; 
  background: #ffffff; 
  border: 1px solid rgba(27, 31, 36, 0.15); 
  border-radius: 6px; 
  cursor: pointer; 
  transition: all 0.2s; 
}

.markdown-body :deep(.copy-btn:hover) { background: #f3f4f6; }
.markdown-body :deep(.copy-btn.copied) { 
  background: #dafbe1; 
  border-color: #2da44e; 
  color: #1a7f37; 
}

.markdown-body :deep(.copy-icon) { width: 14px; height: 14px; }

.markdown-body :deep(.code-content) { 
  overflow-x: auto; 
  background: #ffffff; 
}

.markdown-body :deep(.code-content pre) { 
  margin: 0; 
  padding: 16px; 
  background: transparent; 
}

.markdown-body :deep(.code-content code) { 
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; 
  font-size: 13px; 
  line-height: 1.6; 
  color: #24292f; 
  background: transparent; 
}
</style>