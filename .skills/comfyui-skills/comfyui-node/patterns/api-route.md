# Custom HTTP API Routes Pattern

## When to Use

Use this pattern when your node needs to expose **custom HTTP endpoints** on the ComfyUI server. Common cases:

- File upload (images, models, configs)
- Fetching external data (remote model lists, API responses)
- Serving custom static assets
- Webhook receivers
- Health/status endpoints
- Proxying requests to external services

ComfyUI uses **aiohttp**. You access the server instance via `PromptServer.instance` and register routes with decorators.

---

## Complete Working Example: File Upload + Listing

```python
# nodes_file_upload.py

import os
import json
import time
import folder_paths
from aiohttp import web
from server import PromptServer


# ---------------------------------------------------------------------------
# Directory setup
# ---------------------------------------------------------------------------

UPLOAD_DIR = os.path.join(folder_paths.get_input_directory(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@PromptServer.instance.routes.post("/upload/image")
async def upload_image(request):
    """
    POST /upload/image
    Content-Type: multipart/form-data

    Form fields:
      - image: the file to upload
      - subfolder: (optional) subfolder within uploads/
      - overwrite: (optional) "true" to replace existing files

    Returns JSON:
      { "name": "filename.png", "subfolder": "", "type": "input", "path": "uploads/filename.png" }
    """
    try:
        reader = await request.multipart()

        # Read the file field
        field = await reader.next()
        if field is None:
            return web.json_response(
                {"error": "No file field in request"},
                status=400
            )

        filename = field.filename
        if not filename:
            return web.json_response(
                {"error": "No filename provided"},
                status=400
            )

        # Read optional fields
        subfolder = ""
        overwrite = False
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "subfolder":
                subfolder = (await part.text()).strip()
            elif part.name == "overwrite":
                overwrite = (await part.text()).strip().lower() == "true"

        # Sanitize filename
        safe_filename = os.path.basename(filename)
        target_dir = os.path.join(UPLOAD_DIR, subfolder)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, safe_filename)

        # Check overwrite
        if os.path.exists(target_path) and not overwrite:
            name, ext = os.path.splitext(safe_filename)
            target_path = os.path.join(target_dir, f"{name}_{int(time.time())}{ext}")
            safe_filename = os.path.basename(target_path)

        # Write file
        size = 0
        with open(target_path, "wb") as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)
                size += len(chunk)

        rel_path = os.path.relpath(target_path, folder_paths.get_input_directory())

        return web.json_response({
            "name": os.path.basename(target_path),
            "subfolder": subfolder,
            "type": "input",
            "path": rel_path,
            "size": size,
        })

    except Exception as e:
        return web.json_response(
            {"error": str(e)},
            status=500
        )


@PromptServer.instance.routes.get("/upload/list")
async def list_uploads(request):
    """
    GET /upload/list?subfolder=

    Returns JSON array of uploaded files.
    """
    try:
        subfolder = request.query.get("subfolder", "").strip()
        target_dir = os.path.join(UPLOAD_DIR, subfolder)

        if not os.path.isdir(target_dir):
            return web.json_response([], status=200)

        files = []
        for name in sorted(os.listdir(target_dir)):
            path = os.path.join(target_dir, name)
            if os.path.isfile(path):
                files.append({
                    "name": name,
                    "size": os.path.getsize(path),
                    "modified": os.path.getmtime(path),
                })

        return web.json_response(files)

    except Exception as e:
        return web.json_response(
            {"error": str(e)},
            status=500
        )


@PromptServer.instance.routes.delete("/upload/delete")
async def delete_upload(request):
    """
    DELETE /upload/delete?filename=&subfolder=

    Deletes an uploaded file.
    """
    try:
        filename = request.query.get("filename", "").strip()
        subfolder = request.query.get("subfolder", "").strip()

        if not filename:
            return web.json_response(
                {"error": "filename parameter required"},
                status=400
            )

        target_path = os.path.join(UPLOAD_DIR, subfolder, os.path.basename(filename))

        if not os.path.exists(target_path):
            return web.json_response(
                {"error": "File not found"},
                status=404
            )

        os.remove(target_path)
        return web.json_response({"deleted": filename})

    except Exception as e:
        return web.json_response(
            {"error": str(e)},
            status=500
        )


@PromptServer.instance.routes.get("/status/health")
async def health_check(request):
    """Simple health check endpoint."""
    return web.json_response({
        "status": "ok",
        "timestamp": time.time(),
    })


# ---------------------------------------------------------------------------
# ComfyUI Nodes
# ---------------------------------------------------------------------------

class UploadedImageNode:
    """Loads an image from the uploads directory."""

    @classmethod
    def INPUT_TYPES(cls):
        # Dynamically list uploaded files
        upload_files = []
        if os.path.isdir(UPLOAD_DIR):
            for f in sorted(os.listdir(UPLOAD_DIR)):
                if os.path.isfile(os.path.join(UPLOAD_DIR, f)):
                    upload_files.append(f)

        return {
            "required": {
                "filename": (upload_files if upload_files else ["no_uploads"],),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "load"
    CATEGORY = "image"

    def load(self, filename):
        import torch
        from PIL import Image
        import numpy as np

        path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Upload not found: {filename}")

        img = Image.open(path).convert("RGB")
        arr = np.array(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0)  # (1, H, W, 3)

        return (tensor,)


class APIFetcherNode:
    """Fetches JSON data from a URL and exposes it as a string."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url": ("STRING", {"default": "http://localhost:8188/status/health"}),
                "method": (["GET", "POST"],),
            },
            "optional": {
                "headers": ("STRING", {
                    "multiline": True,
                    "default": "{}",
                    "tooltip": "JSON object of headers"
                }),
                "body": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Request body (for POST)"
                }),
            },
        }

    RETURN_TYPES = ("STRING", "INT",)
    RETURN_NAMES = ("response_body", "status_code",)
    FUNCTION = "fetch"
    CATEGORY = "api"

    def fetch(self, url, method, headers="{}", body=""):
        import requests

        try:
            headers_dict = json.loads(headers) if headers.strip() else {}
        except json.JSONDecodeError:
            return ("Invalid JSON in headers", 0)

        try:
            if method == "GET":
                resp = requests.get(url, headers=headers_dict, timeout=10)
            else:
                resp = requests.post(url, headers=headers_dict, data=body, timeout=10)

            return (resp.text, resp.status_code)

        except requests.RequestException as e:
            return (str(e), 0)


NODE_CLASS_MAPPINGS = {
    "UploadedImageNode": UploadedImageNode,
    "APIFetcherNode": APIFetcherNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UploadedImageNode": "Uploaded Image",
    "APIFetcherNode": "API Fetcher",
}
```

---

## Route Registration Patterns

### GET Route

```python
@PromptServer.instance.routes.get("/my/endpoint")
async def my_handler(request):
    # Access query params
    param = request.query.get("key", "default")

    # Return JSON
    return web.json_response({"result": param})
```

### POST Route

```python
@PromptServer.instance.routes.post("/my/endpoint")
async def my_handler(request):
    # JSON body
    data = await request.json()

    # Form data
    # data = await request.post()

    return web.json_response({"received": data})
```

### Multiple Methods

```python
@PromptServer.instance.routes.route("*", "/my/endpoint")
async def my_handler(request):
    if request.method == "GET":
        return web.json_response({"method": "get"})
    elif request.method == "POST":
        return web.json_response({"method": "post"})
```

### Static File Serving

```python
from aiohttp import web

# Serve a directory of static files
PromptServer.instance.app.router.add_static(
    "/my_assets/",
    path="/absolute/path/to/assets",
    show_index=False,
)
```

### Middleware

```python
@web.middleware
async def auth_middleware(request, handler):
    token = request.headers.get("Authorization")
    if token != "Bearer my-secret":
        return web.json_response({"error": "Unauthorized"}, status=401)
    return await handler(request)

# Add before routes are registered
# PromptServer.instance.app.middlewares.append(auth_middleware)
```

---

## Key Considerations

| Concern | Guidance |
|---|---|
| **`PromptServer.instance`** | This is a singleton available after ComfyUI starts. Import it at module level and use the `@…routes.get/post` decorators directly. |
| **Async handlers** | All route handlers must be `async def`. Use `await` for I/O operations. |
| **JSON responses** | Always use `web.json_response()` for structured data. It sets `Content-Type: application/json` automatically. |
| **Error handling** | Wrap logic in `try/except` and return appropriate HTTP status codes (400, 404, 500). |
| **File paths** | Use `folder_paths.get_input_directory()` or `folder_paths.get_output_directory()` to get ComfyUI's configured paths. Never hardcode absolute paths. |
| **Security** | Sanitize all user input (filenames, paths). Never pass raw user input to `os.path.join` without `os.path.basename()`. Validate file extensions. |
| **CORS** | ComfyUI does not enable CORS by default. If you need browser-side fetch from a different origin, you must add CORS headers via middleware. |
| **Port** | Routes are served on the same port as ComfyUI (default 8188). |
| **Conflict** | Route paths must be unique. Use a namespace prefix (e.g., `/myplugin/...`) to avoid collisions with other extensions. |
| **Testing** | Test routes with `curl` or a REST client: `curl http://localhost:8188/status/health` |

---

## Variations

### 1. WebSocket Endpoint

```python
@PromptServer.instance.routes.get("/my/ws")
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str(f"Echo: {msg.data}")
        elif msg.type == web.WSMsgType.ERROR:
            break

    return ws
```

### 2. Proxy to External API

```python
@PromptServer.instance.routes.get("/proxy/civitai/models")
async def proxy_civitai(request):
    import requests

    api_key = os.environ.get("CIVITAI_API_KEY", "")
    resp = requests.get(
        "https://civitai.com/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"limit": request.query.get("limit", "10")},
        timeout=15,
    )
    return web.json_response(resp.json(), status=resp.status_code)
```

### 3. Streaming Response

```python
@PromptServer.instance.routes.get("/stream/progress")
async def stream_progress(request):
    response = web.StreamResponse()
    response.content_type = "text/event-stream"
    await response.prepare(request)

    for i in range(100):
        await response.write(f"data: {json.dumps({'progress': i})}\n\n".encode())
        await asyncio.sleep(0.1)

    await response.write_eof()
    return response
```

### 4. File Download

```python
@PromptServer.instance.routes.get("/download/output")
async def download_output(request):
    filename = request.query.get("filename", "")
    path = os.path.join(folder_paths.get_output_directory(), os.path.basename(filename))

    if not os.path.exists(path):
        return web.json_response({"error": "Not found"}, status=404)

    return web.FileResponse(
        path,
        headers={
            "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'
        },
    )
```
