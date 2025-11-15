"""S3-backed consumer for Massive flatfiles.

This script connects to an S3-compatible endpoint (Massive's file store), lists objects
and optionally downloads them to a local directory.

Credentials and settings are read from environment variables (preferred):
 - MASSIVE_S3_ACCESS_KEY
 - MASSIVE_S3_SECRET_KEY
 - MASSIVE_S3_ENDPOINT (e.g. https://files.massive.com)
 - MASSIVE_S3_BUCKET (e.g. flatfiles)

Usage examples:
  # list objects only
  MASSIVE_S3_ACCESS_KEY=... MASSIVE_S3_SECRET_KEY=... MASSIVE_S3_ENDPOINT=https://files.massive.com MASSIVE_S3_BUCKET=flatfiles \
    .venv/bin/python extract/massive/s3_consumer.py --list-only

  # download all objects under optional prefix
  MASSIVE_S3_ACCESS_KEY=... MASSIVE_S3_SECRET_KEY=... MASSIVE_S3_ENDPOINT=https://files.massive.com MASSIVE_S3_BUCKET=flatfiles \
    .venv/bin/python extract/massive/s3_consumer.py --outdir extract/massive/raw --prefix todays/

The script avoids persisting credentials in the repo; set them in the environment before running.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


LOG = logging.getLogger("massive.s3_consumer")


def make_s3_client(access_key: str, secret_key: str, endpoint: Optional[str] = None):
    """Create an S3 client for the given endpoint using provided credentials."""
    cfg = Config(signature_version="s3v4")
    session = boto3.session.Session()
    client = session.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint,
        config=cfg,
    )
    return client


def list_objects(client, bucket: str, prefix: Optional[str] = None):
    paginator = client.get_paginator("list_objects_v2")
    kwargs = {"Bucket": bucket}
    if prefix:
        kwargs["Prefix"] = prefix
    for page in paginator.paginate(**kwargs):
        for obj in page.get("Contents", []):
            yield obj


def download_object(client, bucket: str, key: str, outdir: Path) -> Path:
    out_path = outdir / key
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    try:
        client.download_file(Bucket=bucket, Key=key, Filename=str(tmp_path))
        tmp_path.replace(out_path)
        return out_path
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="extract/massive/raw", help="Directory to write downloaded files")
    parser.add_argument("--bucket", default=None, help="Bucket name (overrides env MASSIVE_S3_BUCKET)")
    parser.add_argument("--endpoint", default=None, help="S3 endpoint URL (overrides env MASSIVE_S3_ENDPOINT)")
    parser.add_argument("--access-key", default=None, help="Access key (overrides env MASSIVE_S3_ACCESS_KEY)")
    parser.add_argument("--secret-key", default=None, help="Secret key (overrides env MASSIVE_S3_SECRET_KEY)")
    parser.add_argument("--prefix", default=None, help="Optional prefix to limit listing/download")
    parser.add_argument("--contains", default=None, help="Only include keys that contain this substring (case-insensitive)")
    parser.add_argument("--exclude-prefix", default=None, help="Skip keys that start with this prefix")
    parser.add_argument("--list-prefixes", action="store_true", help="List top-level prefixes (folders) and exit")
    parser.add_argument("--list-only", action="store_true", help="Only list objects, don't download")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    access_key = args.access_key or os.environ.get("MASSIVE_S3_ACCESS_KEY")
    secret_key = args.secret_key or os.environ.get("MASSIVE_S3_SECRET_KEY")
    endpoint = args.endpoint or os.environ.get("MASSIVE_S3_ENDPOINT")
    bucket = args.bucket or os.environ.get("MASSIVE_S3_BUCKET")

    if not all([access_key, secret_key, bucket]):
        LOG.error("Missing credentials or bucket. Provide MASSIVE_S3_ACCESS_KEY, MASSIVE_S3_SECRET_KEY and MASSIVE_S3_BUCKET in env or via flags.")
        raise SystemExit(2)

    client = make_s3_client(access_key, secret_key, endpoint)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.list_prefixes:
        LOG.info("Listing top-level prefixes in bucket=%s", bucket)
        try:
            resp = client.list_objects_v2(Bucket=bucket, Delimiter='/', MaxKeys=100)
            prefixes = [p.get('Prefix') for p in resp.get('CommonPrefixes', [])]
            if not prefixes:
                print("(no top-level prefixes found)")
            else:
                for p in prefixes:
                    print(p)
        except (BotoCoreError, ClientError) as e:
            LOG.exception("Failed to list prefixes: %s", e)
            raise SystemExit(1)
        return

    LOG.info("Listing objects in bucket=%s prefix=%s", bucket, args.prefix)
    found = []
    try:
        for obj in list_objects(client, bucket, prefix=args.prefix):
            key = obj["Key"]
            # apply filters
            if args.contains and args.contains.lower() not in key.lower():
                continue
            if args.exclude_prefix and key.startswith(args.exclude_prefix):
                continue
            size = obj.get("Size", 0)
            lastmod = obj.get("LastModified")
            print(f"{key}\t{size}\t{lastmod}")
            found.append({"Key": key, "Size": size, "LastModified": str(lastmod)})
            if not args.list_only:
                LOG.info("Downloading %s", key)
                try:
                    saved = download_object(client, bucket, key, outdir)
                    LOG.info("Saved %s", saved)
                except (BotoCoreError, ClientError) as e:
                    LOG.exception("Failed to download %s: %s", key, e)
    except (BotoCoreError, ClientError) as e:
        LOG.exception("S3 operation failed: %s", e)
        raise SystemExit(1)

    manifest_path = outdir / "manifest.json"
    with manifest_path.open("w") as mf:
        json.dump({"objects": found}, mf, indent=2)
    LOG.info("Wrote manifest %s (items=%d)", manifest_path, len(found))


if __name__ == "__main__":
    main()