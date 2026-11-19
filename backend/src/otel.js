// OpenTelemetry GenAI tracing for Datadog LLM Observability (Agent Observability).
//
// Why OTel and not the dd-trace LLM Obs SDK: the Execution Graph draws its edges from span
// links between spans of the same trace, which dd-trace JS cannot emit. OTel can.
//
// - src/agents/runAgent.js creates `invoke_agent`, `chat` and `execute_tool` spans plus the links
//   (the OpenAI SDK has no native OTel instrumentation, so chat spans are created by hand).
// - Export goes straight to Datadog's OTLP intake with LLM Obs conversion enabled
//   (OTEL_EXPORTER_OTLP_TRACES_ENDPOINT / _HEADERS, set by start.sh). service.name -> ml_app.
import { NodeTracerProvider } from '@opentelemetry/sdk-trace-node';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { OTLPTraceExporter as OTLPProtoExporter } from '@opentelemetry/exporter-trace-otlp-proto';
import { OTLPTraceExporter as OTLPJsonExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { logger } from './logger.js';

/** Logs every OTLP export result: OTel swallows exporter errors (bad key, wrong endpoint) by default. */
class LoggingExporter {
  constructor(inner, endpoint) {
    this.inner = inner;
    this.endpoint = endpoint;
  }

  export(spans, resultCallback) {
    this.inner.export(spans, (result) => {
      if (result.code === 0) {
        logger.info({ event: 'otel.export', status: 'ok', spans: spans.length, endpoint: this.endpoint }, 'OTLP export succeeded');
      } else {
        logger.error(
          { event: 'otel.export', status: 'error', spans: spans.length, endpoint: this.endpoint, err: result.error },
          'OTLP export failed',
        );
      }
      resultCallback(result);
    });
  }

  shutdown() {
    return this.inner.shutdown();
  }

  forceFlush() {
    return this.inner.forceFlush?.() ?? Promise.resolve();
  }
}

export const otelEnabled = Boolean(process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT);

const spanProcessors = [];
if (otelEnabled) {
  const json = process.env.OTEL_EXPORTER_OTLP_TRACES_PROTOCOL === 'http/json';
  const exporter = json ? new OTLPJsonExporter() : new OTLPProtoExporter();
  spanProcessors.push(new BatchSpanProcessor(new LoggingExporter(exporter, process.env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT)));
}

export const provider = new NodeTracerProvider({
  resource: resourceFromAttributes({
    'service.name': process.env.OTEL_SERVICE_NAME || 'bitstalk-deal-buddy',
    'service.version': process.env.DD_VERSION || '1.0.0',
    'deployment.environment.name': process.env.DD_ENV || 'pov',
    dd_llmobs_enabled: true,
  }),
  spanProcessors,
});
provider.register();

export async function shutdownTracing() {
  await provider.shutdown().catch(() => {});
}
