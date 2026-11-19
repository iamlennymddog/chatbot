// Versioned prompt templates, tracked in Datadog LLM Observability (Prompt Tracking).
// Every LLM span carries `_dd.ml_obs.prompt_tracking` (JSON: id, version, chat_template, variables),
// so LLM Observability groups calls per prompt and version, diffs versions and opens them in
// Playground. Bump `version` whenever a template changes.
// https://docs.datadoghq.com/llm_observability/monitoring/prompt_tracking/

/** Fills {{name}} placeholders from variables. */
export function renderTemplate(template, variables = {}) {
  return template.replace(/\{\{(\w+)\}\}/g, (_, name) => String(variables[name] ?? ''));
}

/** Value of the `_dd.ml_obs.prompt_tracking` span attribute for one LLM call. */
export function promptTracking(prompt, userMessage) {
  const variables = Object.fromEntries(Object.entries(prompt.variables ?? {}).map(([k, v]) => [k, String(v)]));
  return JSON.stringify({
    id: prompt.id,
    version: prompt.version,
    chat_template: [
      { role: 'system', content: prompt.template },
      { role: 'user', content: '{{user_message}}' },
    ],
    variables: { ...variables, user_message: String(userMessage ?? '') },
  });
}
