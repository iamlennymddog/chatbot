import { ref } from 'vue'

const sessionId = crypto.randomUUID()

export function useChat() {
  const messages = ref([
    {
      role: 'assistant',
      content:
        "Howzit! I'm **BitsTalk Deal Buddy**. Tell me your budget, how much data you use, or the phone you're eyeing, and I'll find you the best summer deal.",
    },
  ])
  const loading = ref(false)
  const error = ref('')

  async function send(text) {
    const content = text.trim()
    if (!content || loading.value) return
    error.value = ''
    messages.value.push({ role: 'user', content })
    loading.value = true
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Id': sessionId },
        body: JSON.stringify({
          sessionId,
          messages: messages.value.map(({ role, content }) => ({ role, content })),
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`)
      messages.value.push({ role: 'assistant', content: data.reply, sources: data.sources, steps: data.steps })
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  return { messages, loading, error, send, sessionId }
}
