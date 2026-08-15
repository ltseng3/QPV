"""Typed errors used throughout QOrchSim."""


class QOrchSimError(Exception):
    """Base class for simulator errors."""


class ConfigurationError(QOrchSimError):
    """Raised for invalid configuration."""


class UnsupportedSequenceVersionError(QOrchSimError):
    """Raised when SeQUeNCe is absent or has an unsupported version."""


class PastEventError(QOrchSimError):
    """Raised when an event is scheduled before current simulation time."""


class DuplicateEventError(QOrchSimError):
    """Raised for duplicate event identifiers or duplicate subscriptions."""


class InvalidStateTransitionError(QOrchSimError):
    """Raised for invalid protocol or device state transitions."""


class InvalidDeviceStateError(QOrchSimError):
    """Raised when a device operation is invalid in its current state."""


class ResourceUnavailableError(QOrchSimError):
    """Raised when a requested resource cannot be allocated."""


class ProtocolViolationError(QOrchSimError):
    """Raised for malformed or inconsistent protocol input."""


class FreshnessViolationError(ProtocolViolationError):
    """Raised for stale nonce or telemetry-epoch use."""


class UnknownRoundError(ProtocolViolationError):
    """Raised when a message references an unknown round."""


class QuantumStateValidationError(QOrchSimError):
    """Raised when a quantum state is not physical within tolerance."""


class TraceSerializationError(QOrchSimError):
    """Raised when a trace record cannot be serialized."""
