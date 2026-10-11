# App package initialization
import sys
import socket

if sys.platform == "win32":
    _orig_listen = socket.socket.listen
    def _safe_listen(self, *args, **kwargs):
        try:
            return _orig_listen(self, *args, **kwargs)
        except OSError as e:
            # WinError 10022 occurs in multi-process workers when asyncio calls listen() on already-listening socket
            if getattr(e, "winerror", None) == 10022 or getattr(e, "errno", None) == 10022:
                return
            raise
    socket.socket.listen = _safe_listen
