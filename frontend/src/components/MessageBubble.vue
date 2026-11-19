<script setup>
import { computed } from 'vue'

const props = defineProps({ message: { type: Object, required: true } })

// Minimal, safe markdown: escape HTML first, then bold, bullets and line breaks.
const html = computed(() => {
  const esc = props.message.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return esc
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^#{1,6}\s*(.+)$/gm, '<strong>$1</strong>')
    .replace(/^\s*[-*]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m.replace(/\n/g, '')}</ul>`)
    .replace(/\n/g, '<br>')
})
</script>

<template>
  <div class="bubble" :class="message.role">
    <div v-html="html"></div>
    <div v-if="message.sources?.length" class="sources">
      <span v-for="s in message.sources" :key="s.id" class="chip" :title="s.title">{{ s.id }}</span>
    </div>
    <details v-if="message.steps?.length" class="steps">
      <summary>Agent activity · {{ message.steps.length }} tool call{{ message.steps.length > 1 ? 's' : '' }}</summary>
      <ol>
        <li v-for="(s, i) in message.steps" :key="i">
          <span class="agent" :class="s.agent">{{ s.agent }}</span>
          → <code>{{ s.tool }}</code>
          <span class="input">{{ Object.values(s.input).join(', ') }}</span>
        </li>
      </ol>
    </details>
  </div>
</template>
