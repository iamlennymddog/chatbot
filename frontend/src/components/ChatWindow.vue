<script setup>
import { ref, nextTick, watch } from 'vue'
import { useChat } from '../composables/useChat'
import MessageBubble from './MessageBubble.vue'

const { messages, loading, error, send } = useChat()
const input = ref('')
const scroller = ref(null)

const suggestions = [
  'Best iPhone deal?',
  'Cheap phone under R300 per month',
  'Compare Galaxy S26 Ultra and Pixel 10 Pro',
  'Uncapped home internet options',
  'Roaming for a trip to Europe',
  'Prepaid data bundles',
]

async function submit(text = input.value) {
  if (!text.trim()) return
  input.value = ''
  await send(text)
}

watch(
  () => [messages.value.length, loading.value],
  async () => {
    await nextTick()
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
  },
)
</script>

<template>
  <main class="chat">
    <section ref="scroller" class="messages">
      <MessageBubble v-for="(m, i) in messages" :key="i" :message="m" />
      <div v-if="loading" class="bubble assistant typing"><span></span><span></span><span></span></div>
      <div v-if="error" class="error">⚠️ {{ error }}</div>
    </section>

    <div class="suggestions">
      <button v-for="s in suggestions" :key="s" :disabled="loading" @click="submit(s)">{{ s }}</button>
    </div>

    <form class="composer" @submit.prevent="submit()">
      <input v-model="input" :disabled="loading" placeholder="Ask about phones, data bundles, deals..." autofocus />
      <button type="submit" :disabled="loading || !input.trim()">Send</button>
    </form>
  </main>
</template>
