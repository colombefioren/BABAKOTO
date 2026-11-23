# babakoto-common

Small pieces shared by the services. Today: `BodySizeLimitMiddleware`, an ASGI middleware that
rejects oversized HTTP bodies before multipart or JSON parsing buffers them.
