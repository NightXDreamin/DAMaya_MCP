import io
import sys

class LoggingBinaryStream(object):
    def __init__(self, stream, name):
        self.stream = stream
        self.name = name
    def read(self, *args, **kwargs):
        return self.stream.read(*args, **kwargs)
    def write(self, data, *args, **kwargs):
        return self.stream.write(data, *args, **kwargs)
    def __getattr__(self, name):
        return getattr(self.stream, name)

class WritableTextIOWrapper(io.TextIOWrapper):
    def __init__(self, original_stream, *args, **kwargs):
        # We must initialize the base TextIOWrapper with the binary stream
        super(WritableTextIOWrapper, self).__init__(original_stream, *args, **kwargs)
        self._buffer = original_stream

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, value):
        self._buffer = value

# Re-create streams using WritableTextIOWrapper
# We use line_buffering=True for stdout/stderr to match standard behavior
sys.stdin = WritableTextIOWrapper(sys.stdin.buffer, encoding=sys.stdin.encoding, errors=sys.stdin.errors)
sys.stdout = WritableTextIOWrapper(sys.stdout.buffer, encoding=sys.stdout.encoding, errors=sys.stdout.errors, line_buffering=True)
sys.stderr = WritableTextIOWrapper(sys.stderr.buffer, encoding=sys.stderr.encoding, errors=sys.stderr.errors, line_buffering=True)

# Emulate injection
sys.stdin.buffer = LoggingBinaryStream(sys.stdin.buffer, "stdin_buf")
sys.stdout.buffer = LoggingBinaryStream(sys.stdout.buffer, "stdout_buf")

print("Wrapped successfully!")
print("stdin.buffer:", sys.stdin.buffer)
print("stdout.buffer:", sys.stdout.buffer)
