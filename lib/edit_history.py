"""Document-wide session history, independent of widgets and file offsets."""
from dataclasses import dataclass, field
from datetime import datetime
import time
import zlib


@dataclass(frozen=True)
class DocumentState:
    payload: bytes = field(repr=False)
    briefings: tuple
    artwork: tuple = field(repr=False)
    counters: tuple = field(repr=False)
    selection: tuple = field(default=('Allied', 0), compare=False)
    cursors: tuple = field(default=('1.0', '1.0'), compare=False)
    presentation: tuple = field(default=(), repr=False)

    document: object = field(default=None, repr=False)

    @classmethod
    def capture(cls, data, briefings, artwork, counters, selection, cursors, presentation=None, document=None):
        # Full states keep variable-length blocks and opaque data exact. Compress
        # scenario bytes; immutable artwork pixels are shared between states.
        return cls(zlib.compress(data, 1), tuple(briefings), tuple(sorted(artwork.items())),
                   tuple(sorted(counters.items())), selection, cursors, tuple(sorted((presentation or {}).items())), document)

    @property
    def data(self):
        return zlib.decompress(self.payload)


@dataclass(frozen=True)
class Edit:
    before: DocumentState
    after: DocumentState
    label: str
    details: str
    time: str = field(default_factory=lambda: datetime.now().strftime('%H:%M:%S'))


class EditHistory:
    def __init__(self):
        self.reset(None)

    def reset(self, initial, *, saved=True, label='Opened scenario'):
        self.initial = initial
        self.initial_label = label
        self.entries = []
        self.position = 0
        self.saved_position = 0 if saved and initial is not None else None
        self.break_group()

    def break_group(self):
        self._merge_key = None
        self._merge_time = 0

    @property
    def can_undo(self):
        return self.position > 0

    @property
    def can_redo(self):
        return self.position < len(self.entries)

    def state_at(self, position):
        if not 0 <= position <= len(self.entries):
            raise IndexError('Invalid history position')
        return self.entries[position-1].after if position else self.initial

    def record(self, before, after, label, details='', *, merge_key=None, now=None):
        if before == after:
            return False
        now = time.monotonic() if now is None else now
        merge = (merge_key is not None and merge_key == self._merge_key
                 and now-self._merge_time < 1.0 and self.position == len(self.entries)
                 and self.position > 0 and self.saved_position != self.position
                 and self.entries[-1].after == before)
        if self.saved_position is not None and self.saved_position > self.position:
            self.saved_position = None
        del self.entries[self.position:]
        if merge:
            previous = self.entries.pop()
            self.position -= 1
            before = previous.before
        if before != after:
            self.entries.append(Edit(before, after, label, details))
            self.position += 1
        self._merge_key, self._merge_time = merge_key, now
        return True

    def move(self, position):
        state = self.state_at(position)
        self.position = position
        self.break_group()
        return state

    def mark_saved(self):
        self.saved_position = self.position
        self.break_group()
