"""
Benchmark comparison utility.

This script compares benchmark results between two runs (e.g., baseline vs current)
and detects performance regressions. It can be used in CI to fail builds when
performance degrades beyond acceptable thresholds.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path to import framework
sys.path.insert(0, str(Path(__file__).parent))
from framework import BenchmarkResult, load_results, compare_results


def compare_benchmark_files(
    baseline_path: Path,
    current_path: Path,
    threshold: float = 0.10
) -> Tuple[bool, str]:
    """
    Compare two benchmark result files.

    Args:
        baseline_path: Path to baseline results JSON file
        current_path: Path to current results JSON file
        threshold: Regression threshold as fraction (default: 0.10 for 10%)

    Returns:
        Tuple of (success: bool, summary: str)
        success is True if no regressions detected
    """
    # Load both result sets
    try:
        baseline_results = load_results(baseline_path)
        current_results = load_results(current_path)
    except FileNotFoundError as e:
        return False, f"Error: Could not find file: {e}"
    except json.JSONDecodeError as e:
        return False, f"Error: Invalid JSON in file: {e}"

    # Create lookup dictionaries
    baseline_dict = {r.name: r for r in baseline_results}
    current_dict = {r.name: r for r in current_results}

    # Track overall status
    all_passed = True
    regressions = []
    improvements = []
    warnings = []
    missing = []

    print("\n" + "=" * 70)
    print("BENCHMARK COMPARISON RESULTS")
    print("=" * 70)
    print(f"Baseline: {baseline_path}")
    print(f"Current:  {current_path}")
    print(f"Threshold: {threshold * 100}%")
    print("=" * 70)

    # Compare each benchmark
    for name in sorted(current_dict.keys()):
        current = current_dict[name]

        if name not in baseline_dict:
            missing.append(name)
            print(f"⚠️  NEW: {name} (no baseline)")
            continue

        baseline = baseline_dict[name]

        # Calculate regression
        regression_pct = (current.p95_ms - baseline.p95_ms) / baseline.p95_ms

        if regression_pct > threshold:
            # Regression detected
            all_passed = False
            regressions.append((name, regression_pct, baseline.p95_ms, current.p95_ms))
            print(f"❌ REGRESSION: {name}")
            print(f"   P95: {baseline.p95_ms:.2f}ms → {current.p95_ms:.2f}ms ({regression_pct*100:+.1f}%)")
        elif regression_pct > 0:
            # Slight increase but within threshold
            warnings.append((name, regression_pct, baseline.p95_ms, current.p95_ms))
            print(f"⚠️  {name}")
            print(f"   P95: {baseline.p95_ms:.2f}ms → {current.p95_ms:.2f}ms ({regression_pct*100:+.1f}%)")
        else:
            # Improvement
            improvement_pct = abs(regression_pct)
            improvements.append((name, improvement_pct, baseline.p95_ms, current.p95_ms))
            print(f"✅ {name}")
            print(f"   P95: {baseline.p95_ms:.2f}ms → {current.p95_ms:.2f}ms ({regression_pct*100:+.1f}%)")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total benchmarks: {len(current_dict)}")
    print(f"Improvements:     {len(improvements)}")
    print(f"Warnings:         {len(warnings)}")
    print(f"Regressions:      {len(regressions)}")
    print(f"New benchmarks:   {len(missing)}")
    print("=" * 70)

    # Build detailed summary text
    summary_parts = []

    if regressions:
        summary_parts.append("## 🚨 Performance Regressions Detected\n")
        for name, pct, baseline, current in regressions:
            summary_parts.append(
                f"- **{name}**: P95 {baseline:.2f}ms → {current:.2f}ms ({pct*100:+.1f}%)\n"
            )

    if warnings:
        summary_parts.append("\n## ⚠️ Performance Changes (Within Threshold)\n")
        for name, pct, baseline, current in warnings:
            summary_parts.append(
                f"- **{name}**: P95 {baseline:.2f}ms → {current:.2f}ms ({pct*100:+.1f}%)\n"
            )

    if improvements:
        summary_parts.append("\n## ✅ Performance Improvements\n")
        for name, pct, baseline, current in improvements:
            summary_parts.append(
                f"- **{name}**: P95 {baseline:.2f}ms → {current:.2f}ms (-{pct*100:.1f}%)\n"
            )

    if missing:
        summary_parts.append("\n## 📊 New Benchmarks\n")
        for name in missing:
            summary_parts.append(f"- **{name}** (no baseline for comparison)\n")

    summary = "".join(summary_parts)

    if all_passed:
        print("\n✅ All benchmarks passed!")
    else:
        print("\n❌ Performance regressions detected!")

    return all_passed, summary


def generate_comparison_report(
    baseline_path: Path,
    current_path: Path,
    output_path: Path,
    threshold: float = 0.10
) -> None:
    """
    Generate a detailed comparison report in JSON format.

    Args:
        baseline_path: Path to baseline results
        current_path: Path to current results
        output_path: Path to save comparison report
        threshold: Regression threshold
    """
    baseline_results = load_results(baseline_path)
    current_results = load_results(current_path)

    baseline_dict = {r.name: r for r in baseline_results}
    current_dict = {r.name: r for r in current_results}

    comparisons = []

    for name in current_dict.keys():
        current = current_dict[name]

        if name not in baseline_dict:
            comparisons.append({
                "name": name,
                "status": "new",
                "current": current.to_dict()
            })
            continue

        baseline = baseline_dict[name]
        regression_pct = (current.p95_ms - baseline.p95_ms) / baseline.p95_ms

        if regression_pct > threshold:
            status = "regression"
        elif regression_pct > 0:
            status = "warning"
        else:
            status = "improvement"

        comparisons.append({
            "name": name,
            "status": status,
            "regression_pct": regression_pct,
            "baseline": baseline.to_dict(),
            "current": current.to_dict()
        })

    report = {
        "baseline_path": str(baseline_path),
        "current_path": str(current_path),
        "threshold": threshold,
        "comparisons": comparisons
    }

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nComparison report saved to {output_path}")


def main():
    """Main entry point for the comparison tool."""
    parser = argparse.ArgumentParser(
        description="Compare Chroma benchmark results and detect regressions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two local result files
  python compare.py baseline.json current.json

  # Set custom threshold (20% regression allowed)
  python compare.py baseline.json current.json --threshold 0.20

  # Generate detailed comparison report
  python compare.py baseline.json current.json --report comparison.json

Exit codes:
  0 - No regressions detected
  1 - Regressions detected or error occurred
"""
    )

    parser.add_argument(
        "baseline",
        type=Path,
        help="Path to baseline benchmark results JSON file"
    )
    parser.add_argument(
        "current",
        type=Path,
        help="Path to current benchmark results JSON file"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="Regression threshold as fraction (default: 0.10 for 10%%)"
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Path to save detailed comparison report JSON"
    )

    args = parser.parse_args()

    # Validate threshold
    if args.threshold < 0:
        print("Error: threshold must be non-negative", file=sys.stderr)
        return 1

    # Perform comparison
    success, summary = compare_benchmark_files(
        args.baseline,
        args.current,
        args.threshold
    )

    # Generate detailed report if requested
    if args.report:
        generate_comparison_report(
            args.baseline,
            args.current,
            args.report,
            args.threshold
        )

    # Exit with appropriate code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
