# OpenDeepSeek Artifact Manifest

Artifact Manifest is the first step toward making generated files visible as products instead of mysterious `/host` paths.

## Goal

When Hermes finishes a real file task, the Smart Bridge inspects the assistant response for `/host/OpenDeepSeek-Outputs/...` paths. If files exist under the allowed output root, Bridge writes a manifest and appends a Chinese artifact card to the Open WebUI response.

This is intentionally conservative:

- only files under `OpenDeepSeek-Outputs` are eligible
- hidden files are skipped
- `.env`, SSH keys, token/password-like filenames are skipped
- preview service is read-only
- preview service is bound to `127.0.0.1` by Docker Compose

## Environment

```env
OPDS_ARTIFACT_PORT=8770
OPDS_ARTIFACT_ROOT=/host/OpenDeepSeek-Outputs
OPDS_ARTIFACT_PUBLIC_BASE_URL=http://localhost:8770
OPDS_ARTIFACT_MAX_FILES=100
```

In Docker, `/host` is the authorized host directory mounted into Hermes and Bridge.

## Manifest Location

Manifests are written inside:

```text
/host/OpenDeepSeek-Outputs/.opendeepseek-artifacts/<task_id>/manifest.json
```

The hidden storage directory is internal metadata. The preview endpoint returns manifest JSON directly; it does not serve arbitrary hidden files.

## Schema

```json
{
  "schema_version": 1,
  "task_id": "20260506-203000-abc123def456",
  "title": "site",
  "type": "artifact",
  "route": "artifact:6:生成.*网页",
  "created_at": "2026-05-06T11:30:00+00:00",
  "container_root": "/host/OpenDeepSeek-Outputs/site",
  "local_root": "/Users/lauralyu/OpenDeepSeek-Outputs/site",
  "files": [
    {
      "path": "index.html",
      "mime": "text/html",
      "size_bytes": 12400,
      "preview_url": "http://localhost:8770/artifacts/20260506-203000-abc123def456/index.html"
    }
  ],
  "manifest_url": "http://localhost:8770/artifacts/20260506-203000-abc123def456/manifest.json"
}
```

## Endpoints

```text
GET /artifacts
GET /artifacts/<task_id>
GET /artifacts/<task_id>/manifest.json
GET /artifacts/<task_id>/<relative-file-path>
```

The file endpoint only serves files listed in the manifest and still checks that the final resolved path is under `OPDS_ARTIFACT_ROOT`.

## Response Card

After a successful file task, Bridge appends:

```markdown
OpenDeepSeek 产物卡片：
- 标题：site
- 本机路径：`/Users/lauralyu/OpenDeepSeek-Outputs/site`
- 容器路径：`/host/OpenDeepSeek-Outputs/site`
- 预览：http://localhost:8770/artifacts/<task_id>/index.html
- Manifest：http://localhost:8770/artifacts/<task_id>/manifest.json
- 文件：
  - `index.html` (text/html, 12400 bytes)
```

## Known Limits

- The first version is response-driven: if Hermes creates a file but does not mention the `/host/OpenDeepSeek-Outputs/...` path, Bridge cannot infer it.
- The preview service is local-only. It is not designed for public hosting.
- For multi-root tasks, the first valid output root is used.
- A richer Portal artifact center belongs to a later product milestone.
