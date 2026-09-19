"""Canonical deterministic engineering graph for AI Code Architect."""

from .model import Edge, Graph, Node
from .builder import build_from_ingestion
from .trace import (
    TRACE_SCHEMA_VERSION,
    TRACE_STATES,
    Trace,
    TraceBoundary,
    TraceEngine,
    TraceRequest,
    TraceStep,
    CandidatePath,
    TraceValidationError,
    validate_trace_dict,
)

__all__ = [
    "Node", "Edge", "Graph", "build_from_ingestion",
    "TRACE_SCHEMA_VERSION", "TRACE_STATES",
    "Trace", "TraceBoundary", "TraceEngine", "TraceRequest",
    "TraceStep", "CandidatePath", "TraceValidationError",
    "validate_trace_dict",
]
