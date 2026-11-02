"""A tiny object-store client for the offsite backups (Phase 3 §25.4 step 8, H2).

Litestream replicates the precious files itself; this client does the few things
around it that Litestream doesn't: upload / list / prune the weekly catalog
snapshots, download one for ``mm db pull``, and age out the replicas of deleted
accounts. Two backends behind one URL (the same URL Litestream takes):

* ``s3://<bucket>[/<prefix>]?endpoint=https://<account>.r2.cloudflarestorage.com``
  — any S3-compatible store (Cloudflare R2 in production), signed with AWS
  Signature V4 over plain ``httpx`` (path-style requests, region ``auto`` unless
  ``?region=`` says otherwise). No SDK dependency.
* ``file:///<absolute dir>`` — a directory, for rehearsals and tests.

Credentials are passed in (``offsite.credentials`` reads them through
:mod:`magic_manager.secrets`); they never appear in a URL, a log line or an error
message.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit
from xml.etree import ElementTree

import httpx

TIMEOUT = httpx.Timeout(60.0, connect=15.0)
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_CHUNK = 1024 * 1024


class StoreError(RuntimeError):
    """The object store refused or failed a request (never carries a credential)."""


@dataclass(frozen=True)
class Location:
    """A parsed offsite URL."""
    scheme: str                 # 's3' | 'file'
    bucket: str = ""            # s3 only
    prefix: str = ""            # key prefix ('' or 'a/b', no slashes at the ends)
    endpoint: str = ""          # s3 only: https://host[:port]
    region: str = "auto"
    root: Path | None = None    # file only


def parse_url(url: str) -> Location:
    """Parse ``s3://bucket/prefix?endpoint=…`` or ``file:///dir``; ValueError otherwise."""
    u = urlsplit((url or "").strip())
    if u.scheme == "file":
        if u.netloc not in ("", "localhost") or not u.path.startswith("/"):
            raise ValueError("a file:// offsite URL needs an absolute path (file:///abs/dir)")
        return Location("file", root=Path(u.path))
    if u.scheme != "s3":
        raise ValueError("the offsite URL must start with s3:// or file://")
    if not u.netloc or u.username or u.password:
        raise ValueError("an s3:// offsite URL is s3://<bucket>/<prefix>?endpoint=https://… (no credentials in it)")
    q = parse_qs(u.query)
    endpoint = (q.get("endpoint") or [""])[0].rstrip("/")
    e = urlsplit(endpoint)
    if e.scheme not in ("https", "http") or not e.hostname or e.path not in ("", "/") or e.username:
        raise ValueError("an s3:// offsite URL needs ?endpoint=https://<host> (e.g. https://<account>.r2.cloudflarestorage.com)")
    if e.scheme == "http" and e.hostname not in ("localhost", "127.0.0.1"):
        raise ValueError("the offsite endpoint must use https (plain http only for localhost)")
    region = (q.get("region") or ["auto"])[0] or "auto"
    return Location("s3", bucket=u.netloc, prefix=u.path.strip("/"), endpoint=endpoint, region=region)


def child_url(url: str, sub: str) -> str:
    """``url`` with ``/<sub>`` appended to its path (the query string kept) — the
    replica URL Litestream uses for one database under the base URL."""
    u = urlsplit(url.strip())
    path = u.path.rstrip("/") + "/" + sub.strip("/")
    return f"{u.scheme}://{u.netloc}{path}" + (f"?{u.query}" if u.query else "")


@dataclass(frozen=True)
class Credentials:
    access_key_id: str
    secret_access_key: str

    def __repr__(self) -> str:  # never print the secret
        return f"Credentials(access_key_id={self.access_key_id[:4]}…)"


@dataclass(frozen=True)
class Obj:
    key: str               # relative to the store's prefix
    size: int
    modified: datetime     # UTC


class Store:
    """``put`` / ``get`` / ``list`` / ``delete`` on keys relative to the URL's prefix."""

    def put(self, key: str, src: Path) -> None: raise NotImplementedError
    def get(self, key: str, dest: Path) -> None: raise NotImplementedError
    def list(self, prefix: str = "") -> list[Obj]: raise NotImplementedError
    def delete(self, key: str) -> None: raise NotImplementedError


def _check_key(key: str) -> str:
    parts = key.split("/")
    if not key or key.startswith("/") or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"bad object key {key!r}")
    return key


class FileStore(Store):
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / _check_key(key)

    def put(self, key: str, src: Path) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f".{dest.name}.part")
        shutil.copyfile(src, tmp)
        os.replace(tmp, dest)

    def get(self, key: str, dest: Path) -> None:
        src = self._path(key)
        if not src.is_file():
            raise StoreError(f"no object {key}")
        shutil.copyfile(src, dest)

    def list(self, prefix: str = "") -> list[Obj]:
        if not self.root.is_dir():
            return []
        out = []
        for p in self.root.rglob("*"):
            if not p.is_file() or p.name.startswith("."):
                continue
            key = p.relative_to(self.root).as_posix()
            if key.startswith(prefix):
                st = p.stat()
                out.append(Obj(key, st.st_size, datetime.fromtimestamp(st.st_mtime, UTC)))
        return sorted(out, key=lambda o: o.key)

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


# ---------- AWS Signature V4 (S3) ----------

def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _uri_encode(s: str, *, slash: bool) -> str:
    return quote(s, safe="-_.~" + ("/" if not slash else ""))


def query_string(query: dict[str, str]) -> str:
    """The canonical (sorted, strictly encoded) query string — also what is sent."""
    return "&".join(f"{_uri_encode(k, slash=True)}={_uri_encode(v, slash=True)}" for k, v in sorted(query.items()))


def sign(method: str, host: str, path: str, query: dict[str, str], headers: dict[str, str],
         payload_sha256: str, creds: Credentials, region: str, now: datetime) -> dict[str, str]:
    """The headers to add to an S3 request (``Authorization``, ``x-amz-date``,
    ``x-amz-content-sha256``). ``path`` is the raw (unencoded) path; ``headers`` are
    any other headers to sign (lower-case names)."""
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = amz_date[:8]
    signed = {k.lower(): " ".join(str(v).split()) for k, v in headers.items()}
    signed.update({"host": host, "x-amz-content-sha256": payload_sha256, "x-amz-date": amz_date})
    names = sorted(signed)
    canonical = "\n".join([
        method,
        _uri_encode(path, slash=False),
        query_string(query),
        "".join(f"{n}:{signed[n]}\n" for n in names),
        ";".join(names),
        payload_sha256,
    ])
    scope = f"{day}/{region}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key = _hmac(_hmac(_hmac(_hmac(("AWS4" + creds.secret_access_key).encode(), day), region), "s3"), "aws4_request")
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    return {
        "Authorization": f"AWS4-HMAC-SHA256 Credential={creds.access_key_id}/{scope}, "
                         f"SignedHeaders={';'.join(names)}, Signature={signature}",
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_sha256,
    }


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


class S3Store(Store):
    def __init__(self, loc: Location, creds: Credentials, *, client: httpx.Client | None = None) -> None:
        if not creds.access_key_id or not creds.secret_access_key:
            raise StoreError("offsite credentials are missing")
        self.loc, self.creds = loc, creds
        self.host = urlsplit(loc.endpoint).netloc
        self.client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=False)

    def _key(self, key: str) -> str:
        _check_key(key)
        return f"{self.loc.prefix}/{key}" if self.loc.prefix else key

    def _request(self, method: str, path: str, *, query: dict[str, str] | None = None,
                 content=None, payload_sha256: str = _EMPTY_SHA256, headers: dict[str, str] | None = None,
                 stream: bool = False) -> httpx.Response:
        query = query or {}
        extra = dict(headers or {})
        auth = sign(method, self.host, path, query, extra, payload_sha256, self.creds, self.loc.region,
                    datetime.now(UTC))
        url = self.loc.endpoint + _uri_encode(path, slash=False) + (f"?{query_string(query)}" if query else "")
        req = self.client.build_request(method, url, content=content,
                                        headers={**extra, **auth})
        try:
            resp = self.client.send(req, stream=stream)
        except httpx.HTTPError as e:
            raise StoreError(f"{method} {path}: {type(e).__name__}") from None
        if resp.status_code >= 300:
            body = resp.read().decode(errors="replace") if stream else resp.text
            code = ""
            try:
                code = ElementTree.fromstring(body).findtext("Code") or ""
            except ElementTree.ParseError:
                pass
            resp.close()
            raise StoreError(f"{method} {path}: HTTP {resp.status_code} {code}".rstrip())
        return resp

    def put(self, key: str, src: Path) -> None:
        src = Path(src)
        digest = file_sha256(src)
        size = src.stat().st_size

        def body() -> Iterator[bytes]:
            with open(src, "rb") as f:
                yield from iter(lambda: f.read(_CHUNK), b"")

        self._request("PUT", f"/{self.loc.bucket}/{self._key(key)}", content=body(), payload_sha256=digest,
                      headers={"content-length": str(size)}).close()

    def get(self, key: str, dest: Path) -> None:
        resp = self._request("GET", f"/{self.loc.bucket}/{self._key(key)}", stream=True)
        try:
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(_CHUNK):
                    f.write(chunk)
        finally:
            resp.close()

    def list(self, prefix: str = "") -> list[Obj]:
        if prefix.startswith("/") or ".." in prefix.split("/"):
            raise ValueError(f"bad prefix {prefix!r}")
        base = f"{self.loc.prefix}/" if self.loc.prefix else ""
        full, strip = base + prefix, len(base)
        out: list[Obj] = []
        token = None
        while True:
            q = {"list-type": "2", "prefix": full}
            if token:
                q["continuation-token"] = token
            resp = self._request("GET", f"/{self.loc.bucket}", query=q)
            root = ElementTree.fromstring(resp.content)
            ns = root.tag[: root.tag.index("}") + 1] if root.tag.startswith("{") else ""
            for c in root.findall(f"{ns}Contents"):
                key = c.findtext(f"{ns}Key") or ""
                stamp = (c.findtext(f"{ns}LastModified") or "").replace("Z", "+00:00")
                out.append(Obj(key[strip:], int(c.findtext(f"{ns}Size") or 0), datetime.fromisoformat(stamp)))
            if (root.findtext(f"{ns}IsTruncated") or "").lower() != "true":
                break
            token = root.findtext(f"{ns}NextContinuationToken")
            if not token:
                break
        return out

    def delete(self, key: str) -> None:
        self._request("DELETE", f"/{self.loc.bucket}/{self._key(key)}").close()


def open_store(url: str, creds: Credentials | None) -> Store:
    loc = parse_url(url)
    if loc.scheme == "file":
        return FileStore(loc.root)  # type: ignore[arg-type]
    if creds is None:
        raise StoreError("offsite credentials are missing (MM_OFFSITE_ACCESS_KEY_ID / MM_OFFSITE_SECRET_ACCESS_KEY)")
    return S3Store(loc, creds)
