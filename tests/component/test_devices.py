from qorchsim.core.event_bus import EventBus
from qorchsim.core.random_streams import RandomStreams
from qorchsim.core.scheduler import DeterministicScheduler
from qorchsim.devices.capabilities import MemoryCapabilities, MeasurementCapabilities, QndCapabilities
from qorchsim.devices.measurement import TimedMeasurementDevice
from qorchsim.devices.qnd_detector import QndDetector, QndOutcome
from qorchsim.devices.quantum_memory import TimedQuantumMemory
from qorchsim.quantum.operations import DensityMatrixQuantumOperations


def test_memory_storage_interval_and_retrieval_noise() -> None:
    bus = EventBus()
    scheduler = DeterministicScheduler(bus, 100_000)
    operations = DensityMatrixQuantumOperations()
    rng = RandomStreams(1)
    memory = TimedQuantumMemory(
        "m",
        MemoryCapabilities(10, 20, 1.0, 1.0, 1_000, 500, 10_000),
        scheduler,
        bus,
        operations,
        rng.generator("memory"),
    )
    qubit = operations.prepare_bb84("q", "state", 1, 0)
    observed = {}

    def loaded(success: bool) -> None:
        assert success
        scheduler.schedule_after(100, 20, __import__("qorchsim.core.events", fromlist=["DomainEvent"]).DomainEvent("request", "retrieve", None))

    def retrieve_handler(event) -> None:
        memory.retrieve(lambda output, dwell: observed.update(output=output, dwell=dwell))

    bus.subscribe("retrieve", retrieve_handler)
    memory.load(qubit, loaded)
    scheduler.run()
    assert observed["output"] is not None
    assert observed["dwell"] == 120


def test_measurement_occurs_at_completion() -> None:
    bus = EventBus()
    scheduler = DeterministicScheduler(bus, 10_000)
    operations = DensityMatrixQuantumOperations()
    device = TimedMeasurementDevice(
        "d",
        MeasurementCapabilities(10, 20, 1.0, 0),
        scheduler,
        bus,
        operations,
        RandomStreams(1).generator("measurement"),
    )
    qubit = operations.prepare_bb84("q", "s", 0, 1)
    observed = {}
    device.measure(qubit, 0, lambda result: observed.update(result=result, time=int(scheduler.now_ps())))
    assert observed == {}
    scheduler.run()
    assert observed == {"result": 1, "time": 30}


def test_qnd_dark_count_without_photon() -> None:
    bus = EventBus()
    scheduler = DeterministicScheduler(bus, 10_000)
    operations = DensityMatrixQuantumOperations()
    detector = QndDetector(
        "qnd",
        QndCapabilities(10, 1, 1e12, 1, 0, 0, 100),
        scheduler,
        bus,
        operations,
        RandomStreams(1).generator("qnd"),
    )
    observed = []
    detector.open_gate("g", 0, observed.append)
    scheduler.run()
    assert observed[0].outcome is QndOutcome.DARK_COUNT
    assert observed[0].qubit is None
