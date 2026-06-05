"""Serial target communication module for scatools."""

import serial


class Target:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, timeout=1):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=timeout,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def clean(self):
        waiting = self.ser.in_waiting
        if waiting:
            return self.ser.read(waiting)
        return b""

    def send(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()

    def recvn(self, n: int, timeout=None) -> bytes:
        old_timeout = self.ser.timeout
        if timeout is not None:
            self.ser.timeout = timeout
        try:
            out = bytearray()
            while len(out) < n:
                chunk = self.ser.read(n - len(out))
                if not chunk:
                    break
                out.extend(chunk)
            return bytes(out)
        finally:
            if timeout is not None:
                self.ser.timeout = old_timeout

    def recvuntil(self, delim: bytes, timeout=None) -> bytes:
        old_timeout = self.ser.timeout
        if timeout is not None:
            self.ser.timeout = timeout
        try:
            out = bytearray()
            while not out.endswith(delim):
                b = self.ser.read(1)
                if not b:
                    break
                out.extend(b)
            return bytes(out)
        finally:
            if timeout is not None:
                self.ser.timeout = old_timeout
