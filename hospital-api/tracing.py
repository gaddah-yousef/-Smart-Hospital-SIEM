import hashlib
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def hash_patient_id(patient_id: str | None) -> str:
    if not patient_id:
        return "none"
    salt = os.getenv("JWT_SECRET_KEY", "hospital-local-salt")
    return hashlib.sha256(f"{salt}:{patient_id}".encode("utf-8")).hexdigest()[:16]


def configure_tracing(app, service_name: str = "hospital-api"):
    endpoint = os.getenv("TEMPO_OTLP_ENDPOINT", "http://tempo:4317").replace("http://", "")
    resource = Resource.create(
        {
            "service.name": service_name,
            "hospital.service": service_name,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FlaskInstrumentor().instrument_app(app)
    return trace.get_tracer(service_name)
