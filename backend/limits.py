"""Single-worker limits for expensive endpoints and incoming multipart bodies."""
from starlette.responses import JSONResponse
from starlette.formparsers import MultiPartException


class RequestLimits:
    def __init__(self, app, upload_bytes, max_uploads=2, max_chats=16):
        self.app = app
        self.upload_path = "/api/v1/documents"
        self.capacity = {self.upload_path: max_uploads, "/api/v1/chat": max_chats, "/chat": max_chats}
        self.active = dict.fromkeys(self.capacity, 0)
        # Allow the multipart headers and conversation ID in addition to the file.
        self.max_body = upload_bytes + 64 * 1024

    async def __call__(self, scope, receive, send):
        path = scope.get("path")
        if scope.get("method") != "POST" or path not in self.capacity:
            return await self.app(scope, receive, send)
        if self.active[path] >= self.capacity[path]:
            response = JSONResponse({"error": "service busy, retry shortly"}, status_code=429,
                                    headers={"Retry-After": "2"})
            return await response(scope, receive, send)

        oversized = False
        total = 0

        async def bounded_receive():
            nonlocal oversized, total
            message = await receive()
            total += len(message.get("body", b""))
            if total > self.max_body:
                oversized = True
                # The multipart parser closes all its temporary files on this exception.
                raise MultiPartException("upload body too large")
            return message

        async def bounded_send(message):
            if oversized and message["type"] == "http.response.start":
                message = {**message, "status": 413}
            await send(message)

        self.active[path] += 1
        try:
            if path == self.upload_path:
                return await self.app(scope, bounded_receive, bounded_send)
            return await self.app(scope, receive, send)
        finally:
            self.active[path] -= 1
