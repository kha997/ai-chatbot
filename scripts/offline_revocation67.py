"""Local fake source authority. Delivery is a committed dummy event, not a business action."""
from threading import Lock

from scripts.offline_heldout67 import (
    Invalid, TENANTS, canonical, digest, integer, is_hash, parse, reference, shape,
)


class Stopped(ValueError):
    pass


class Gate:
    """One immutable source version and monotonic revocation tombstone.

    A fake clock tick is supplied by the trusted caller, not chat text. Only
    the gate can append a delivery. Checking authority and appending delivery
    share the same lock; an external renderer cannot reuse this as a live lease.
    """

    def __init__(self, tenant, ref, start, end):
        try:
            if (type(tenant) is not str or tenant not in TENANTS or type(ref) is not tuple
                    or reference(list(ref))[0] != tenant or not integer(start)
                    or not integer(end, start+1)):
                raise Stopped("invalid-authority")
        except Invalid:
            raise Stopped("invalid-authority") from None
        self._tenant, self._ref, self._start, self._end = tenant, ref, start, end
        self._tick = 0
        self._events = []
        self._stopped = False
        self._tickets = {}
        self._reads = []
        self._outputs = []
        self._lock = Lock()

    @property
    def reads(self):
        with self._lock:
            return tuple(self._reads)

    @property
    def outputs(self):
        with self._lock:
            return tuple(self._outputs)

    @property
    def events(self):
        with self._lock:
            return tuple(self._events)

    def _matches(self, ref):
        if type(ref) is not tuple:
            return False
        try:
            return reference(list(ref)) == self._ref
        except Invalid:
            return False

    def _advance(self, tick):
        if not integer(tick, self._tick):
            self._invalidate()
            return False
        self._tick = tick
        return not self._stopped

    def _active(self):
        return not self._events and self._start <= self._tick < self._end

    def _invalidate(self):
        self._stopped = True
        self._tickets.clear()

    def invalidate(self):
        """Simulate loss of the trusted source epoch; do not recover authority."""
        with self._lock:
            self._invalidate()

    def begin(self, ref, tick):
        with self._lock:
            if not self._matches(ref) or not self._advance(tick) or not self._active():
                return None
            ticket = object()  # in-memory identity, not serializable/routable
            self._tickets[ticket] = len(self._events)
            self._reads.append((self._ref, self._tick))
            return ticket

    def _valid_ticket(self, ticket):
        return (type(ticket) is object and self._tickets.get(ticket) == len(self._events)
                and self._active())

    def prepare(self, ticket, tick):
        """Stage a reference without publishing it or granting delivery authority."""
        with self._lock:
            return ticket if self._advance(tick) and self._valid_ticket(ticket) else None

    def deliver(self, ticket, tick):
        with self._lock:
            if not self._advance(tick) or not self._valid_ticket(ticket):
                return None
            del self._tickets[ticket]
            self._outputs.append(self._ref)
            return self._ref

    def revoke(self, ref, sequence, tick):
        with self._lock:
            if (not self._matches(ref) or not integer(sequence, 1) or not integer(tick)
                    or self._stopped):
                self._invalidate()
                raise Stopped("revocation-authority")
            if self._events and (sequence, tick) == self._events[0]:
                return False   # an exact redelivery has no effect
            if self._events or sequence != 1 or not self._advance(tick):
                self._invalidate()
                raise Stopped("revocation-order")
            self._events.append((sequence, tick))
            self._tickets.clear()
            return True

    def checkpoint(self):
        """Return bytes and digest. The caller must persist/pin independently."""
        with self._lock:
            raw = canonical({"schema": "offline67-revoke-v1", "tenant": self._tenant,
                             "ref": list(self._ref), "start": self._start, "end": self._end,
                             "tick": self._tick, "events": [list(row) for row in self._events],
                             "stopped": self._stopped})
            return raw, digest(raw)

    @classmethod
    def restore(cls, raw, approved_sha):
        try:
            if not is_hash(approved_sha) or type(raw) is not bytes or digest(raw) != approved_sha:
                raise Stopped("checkpoint-pin")
            record = parse(raw)
            shape(record, "schema tenant ref start end tick events stopped")
            if (record["schema"] != "offline67-revoke-v1" or not integer(record["tick"])
                    or type(record["stopped"]) is not bool or type(record["events"]) is not list
                    or len(record["events"]) > 1):
                raise Stopped("checkpoint-schema")
            gate = cls(record["tenant"], reference(record["ref"]), record["start"], record["end"])
            for event in record["events"]:
                if (type(event) is not list or len(event) != 2
                        or not integer(event[1], 0, record["tick"])):
                    raise Stopped("checkpoint-event")
                gate.revoke(gate._ref, *event)
            gate._tick = record["tick"]
            if record["stopped"]:
                gate.invalidate()
            return gate
        except Invalid:
            raise Stopped("checkpoint-schema") from None
