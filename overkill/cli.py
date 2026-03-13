from __future__ import annotations

import argparse
import json
from pathlib import Path

from overkill.demo_server import serve_demo
from overkill.discovery import build_best_supported_episode_export, build_overview
from overkill.ingest_markdown import expand_markdown_inputs, import_markdown_bundles
from overkill.taxonomy import build_bundle_audit
from overkill.validation import BundleValidationError, load_and_validate_bundle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="overkill", description="Overkill research-bundle tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-bundle", help="Validate a research input bundle")
    validate.add_argument("bundle_path", type=Path, help="Path to a bundle directory")
    validate.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable summary")

    summarize = subparsers.add_parser("summarize-bundles", help="Summarize all bundles under a root")
    summarize.add_argument(
        "--bundles-root",
        type=Path,
        default=Path("research/input/gptpro"),
        help="Root directory containing bundle folders",
    )
    summarize.add_argument(
        "--prompt-path",
        type=Path,
        default=Path("gptpro.md"),
        help="Path to the active GPT Pro prompt file for active-target parsing",
    )
    summarize.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable summary")

    audit = subparsers.add_parser(
        "audit-bundles",
        help="Write a bundle taxonomy/provisional-status audit report",
    )
    audit.add_argument(
        "--bundles-root",
        type=Path,
        default=Path("research/input/gptpro"),
        help="Root directory containing bundle folders",
    )
    audit.add_argument(
        "--prompt-path",
        type=Path,
        default=Path("gptpro.md"),
        help="Path to the active GPT Pro prompt file for active-target parsing",
    )
    audit.add_argument(
        "--taxonomy-path",
        type=Path,
        default=Path("research/derived/bundle_relationships.json"),
        help="Path to the machine-readable bundle relationship manifest",
    )
    audit.add_argument(
        "--output",
        type=Path,
        default=Path("research/derived/bundle_audit.json"),
        help="Where to write the bundle audit JSON",
    )
    audit.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable summary")

    export_demo = subparsers.add_parser("export-demo-data", help="Write demo overview JSON for static serving")
    export_demo.add_argument(
        "--bundles-root",
        type=Path,
        default=Path("research/input/gptpro"),
        help="Root directory containing bundle folders",
    )
    export_demo.add_argument(
        "--prompt-path",
        type=Path,
        default=Path("gptpro.md"),
        help="Path to the active GPT Pro prompt file",
    )
    export_demo.add_argument(
        "--output",
        type=Path,
        default=Path("static/data/index/bundles.json"),
        help="Where to write the exported overview JSON",
    )
    export_demo.add_argument(
        "--taxonomy-path",
        type=Path,
        default=Path("research/derived/bundle_relationships.json"),
        help="Path to the machine-readable bundle relationship manifest",
    )

    export_best = subparsers.add_parser(
        "export-best-supported-episodes",
        help="Write a filtered export of the strongest currently publishable episodes",
    )
    export_best.add_argument(
        "--bundles-root",
        type=Path,
        default=Path("research/input/gptpro"),
        help="Root directory containing bundle folders",
    )
    export_best.add_argument(
        "--prompt-path",
        type=Path,
        default=Path("gptpro.md"),
        help="Path to the active GPT Pro prompt file",
    )
    export_best.add_argument(
        "--taxonomy-path",
        type=Path,
        default=Path("research/derived/bundle_relationships.json"),
        help="Path to the machine-readable bundle relationship manifest",
    )
    export_best.add_argument(
        "--output",
        type=Path,
        default=Path("static/data/index/best_supported_episodes.json"),
        help="Where to write the filtered episode export JSON",
    )

    serve = subparsers.add_parser("serve-demo", help="Serve a live local demo that polls current bundle data")
    serve.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    serve.add_argument("--port", type=int, default=8765, help="Port to bind")
    serve.add_argument(
        "--bundles-root",
        type=Path,
        default=Path("research/input/gptpro"),
        help="Root directory containing bundle folders",
    )
    serve.add_argument(
        "--prompt-path",
        type=Path,
        default=Path("gptpro.md"),
        help="Path to the active GPT Pro prompt file",
    )

    ingest = subparsers.add_parser(
        "ingest-markdown-bundles",
        help="Import GPT Pro markdown bundles into the repo contract with dedupe/no-overwrite defaults",
    )
    ingest.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Markdown files and/or directories containing markdown bundle files",
    )
    ingest.add_argument(
        "--pattern",
        default="overkill_*_research_bundle*.md",
        help="Glob pattern used when an input path is a directory",
    )
    ingest.add_argument(
        "--bundles-root",
        type=Path,
        default=Path("research/input/gptpro"),
        help="Root directory containing bundle folders",
    )
    ingest.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing bundle directories for matching conflict_ids",
    )
    ingest.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip post-import contract validation (not recommended)",
    )
    ingest.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable summary")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-bundle":
        try:
            result = load_and_validate_bundle(args.bundle_path)
        except BundleValidationError as exc:
            if args.as_json:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            else:
                print(f"validation failed: {exc}")
            return 1

        summary = {
            "ok": True,
            "bundle_path": str(result.bundle_path),
            "conflict_id": result.conflict.conflict_id,
            "episode_count": len(result.episodes),
            "source_count": len(result.sources),
            "claim_count": len(result.claims),
            "estimate_count": len(result.estimates),
            "assumption_count": len(result.assumptions),
            "open_question_count": len(result.open_questions),
        }
        if args.as_json:
            print(json.dumps(summary, indent=2))
        else:
            print(
                "bundle valid: "
                f"{summary['conflict_id']} "
                f"(episodes={summary['episode_count']}, "
                f"sources={summary['source_count']}, "
                f"claims={summary['claim_count']}, "
                f"estimates={summary['estimate_count']})"
            )
        return 0

    if args.command == "summarize-bundles":
        overview = build_overview(args.bundles_root, prompt_path=args.prompt_path)
        if args.as_json:
            print(json.dumps(overview, indent=2))
        else:
            print(
                f"bundles: total={overview['bundle_count']} "
                f"valid={overview['valid_bundle_count']} "
                f"invalid={overview['invalid_bundle_count']}"
            )
            if overview["active_target"]:
                print(f"active target: {overview['active_target'].get('conflict_name', 'unknown')}")
            for bundle in overview["bundles"]:
                print(f"- {bundle['bundle_id']}: {bundle['status']}")
        return 0

    if args.command == "audit-bundles":
        audit = build_bundle_audit(
            args.bundles_root,
            prompt_path=args.prompt_path,
            taxonomy_path=args.taxonomy_path,
        )
        if args.as_json:
            print(json.dumps(audit, indent=2))
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
            print(f"wrote bundle audit: {args.output}")
        return 0

    if args.command == "export-demo-data":
        overview = build_overview(
            args.bundles_root,
            prompt_path=args.prompt_path,
            taxonomy_path=args.taxonomy_path,
        )
        best_supported = build_best_supported_episode_export(
            args.bundles_root,
            prompt_path=args.prompt_path,
            taxonomy_path=args.taxonomy_path,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(overview, indent=2) + "\n", encoding="utf-8")
        best_supported_path = args.output.with_name("best_supported_episodes.json")
        best_supported_path.write_text(json.dumps(best_supported, indent=2) + "\n", encoding="utf-8")
        print(f"exported demo data: {args.output}")
        print(f"exported best-supported episodes: {best_supported_path}")
        return 0

    if args.command == "export-best-supported-episodes":
        payload = build_best_supported_episode_export(
            args.bundles_root,
            prompt_path=args.prompt_path,
            taxonomy_path=args.taxonomy_path,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"exported best-supported episodes: {args.output}")
        return 0

    if args.command == "serve-demo":
        serve_demo(
            host=args.host,
            port=args.port,
            bundle_root=args.bundles_root,
            prompt_path=args.prompt_path,
        )
        return 0

    if args.command == "ingest-markdown-bundles":
        try:
            markdown_files = expand_markdown_inputs(args.inputs, pattern=args.pattern)
        except ValueError as exc:
            if args.as_json:
                print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            else:
                print(f"ingest failed: {exc}")
            return 1

        summary = import_markdown_bundles(
            markdown_files=markdown_files,
            bundles_root=args.bundles_root,
            overwrite=args.overwrite,
            validate=not args.skip_validation,
        )

        payload = {
            "ok": summary.error_count == 0,
            "inputs": [str(path) for path in markdown_files],
            **summary.as_dict(),
        }

        if args.as_json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                "ingest summary: "
                f"created={len(summary.created)} "
                f"skipped_existing={len(summary.skipped_existing)} "
                f"skipped_duplicate_inputs={len(summary.skipped_duplicate_inputs)} "
                f"errors={summary.error_count}"
            )
            for record in summary.created:
                print(f"- created {record.conflict_id}: {record.bundle_path}")
            for record in summary.skipped_existing:
                print(f"- skipped existing {record.conflict_id}: {record.bundle_path}")
            for record in summary.skipped_duplicate_inputs:
                print(
                    f"- skipped duplicate input {record.source_path} "
                    f"(kept {record.kept_source_path})"
                )
            for label, records in (
                ("parse error", summary.failed_parse),
                ("validation error", summary.failed_validation),
                ("write error", summary.failed_write),
            ):
                for record in records:
                    print(f"- {label} [{record.conflict_id}] {record.source_path}: {record.reason}")

        return 1 if summary.error_count else 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
