"""CLI entry point: python -m property_pipeline <command> [options]"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="property_pipeline",
        description="Property transaction processing pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run_month
    p_run = sub.add_parser("run_month", help="Process a month's bank files")
    p_run.add_argument("month", help="Month string, e.g. OCT2025")
    p_run.add_argument("--bank-dir", help="Bank download directory override")
    p_run.add_argument("--db", help="Database path override")
    p_run.add_argument("--output-dir", help="Output directory override")
    p_run.add_argument("--use-ml", action="store_true", help="Use ML model to override catch_all / low-confidence labels")
    p_run.add_argument("--model", help="Path to ML model file (default: data/property/ml_model.joblib)")

    # finalize_month
    p_fin = sub.add_parser("finalize_month", help="Copy draft to checked/")
    p_fin.add_argument("month", help="Month string, e.g. OCT2025")
    p_fin.add_argument("--db", help="Database path override")
    p_fin.add_argument("--source-dir", help="Source directory (generated/)")

    # review_month
    p_rev = sub.add_parser("review_month", help="Apply review queue corrections")
    p_rev.add_argument("month", help="Month string, e.g. OCT2025")
    p_rev.add_argument("--db", help="Database path override")

    # backtest
    p_bt = sub.add_parser("backtest", help="Run backtest against ground truth")
    p_bt.add_argument("--months", nargs="*", help="Specific months to test (default: all)")
    p_bt.add_argument("--bank-dir", help="Bank download directory override")
    p_bt.add_argument("--checked-dir", help="Checked directory override")

    # seed_db
    p_seed = sub.add_parser("seed_db", help="Initialise DB and seed rules/properties")
    p_seed.add_argument("--db", help="Database path override")

    # load_historical
    p_load = sub.add_parser("load_historical", help="Bulk load checked XLSX ground truth into DB")
    p_load.add_argument("--months", nargs="*", help="Months to load (default: all with XLSX in checked/)")
    p_load.add_argument("--bank-dir", help="Bank download directory override")
    p_load.add_argument("--checked-dir", help="Checked directory override")
    p_load.add_argument("--db", help="Database path override")

    # grade_rules
    p_grade = sub.add_parser("grade_rules", help="Compute rule_performance from historical labels")
    p_grade.add_argument("--db", help="Database path override")

    # train_ml
    p_train = sub.add_parser("train_ml", help="Train ML model from historical labels in DB")
    p_train.add_argument("--db", help="Database path override")
    p_train.add_argument("--model", help="Output path for model file")

    args = parser.parse_args()

    if args.command == "run_month":
        from .pipeline import run_month
        result = run_month(
            args.month,
            bank_download_dir=args.bank_dir,
            db_path=args.db,
            output_dir=args.output_dir,
            use_ml=getattr(args, "use_ml", False),
            model_path=args.model if getattr(args, "model", None) else None,
        )
        print(f"\nDone. {result['total_transactions']} transactions, {result['needs_review']} need review.")

    elif args.command == "finalize_month":
        from .pipeline import finalize_month
        path = finalize_month(args.month, db_path=args.db, source_dir=args.source_dir)
        print(f"\nFinalized: {path}")

    elif args.command == "review_month":
        from .pipeline import review_month
        review_month(args.month, db_path=args.db)

    elif args.command == "backtest":
        from .backtest import run_backtest_all
        bd = Path(args.bank_dir) if args.bank_dir else None
        cd = Path(args.checked_dir) if args.checked_dir else None
        run_backtest_all(bank_download_dir=bd, checked_dir=cd, months=args.months)

    elif args.command == "seed_db":
        from .pipeline import seed_db
        seed_db(db_path=args.db)
        print("Database seeded.")

    elif args.command == "load_historical":
        from .historical import load_historical_into_db
        bd = Path(args.bank_dir) if args.bank_dir else None
        cd = Path(args.checked_dir) if args.checked_dir else None
        result = load_historical_into_db(
            months=args.months,
            bank_download_dir=bd,
            checked_dir=cd,
            db_path=args.db,
        )
        print(f"\nLoaded {result['total_labels']} manual labels from {len(result['by_month'])} months.")

    elif args.command == "grade_rules":
        from .historical import grade_rules
        grade_rules(db_path=args.db)

    elif args.command == "train_ml":
        from .ml_model import train
        from .config import MODEL_PATH
        res = train(db_path=args.db, model_path=getattr(args, "model", None) or MODEL_PATH)
        if res.get("ok"):
            print(f"Model trained on {res['n']} samples, saved to {res['path']}")
        else:
            print(f"Training skipped: {res.get('reason', 'unknown')} (n={res.get('n', 0)})")
            sys.exit(1)


if __name__ == "__main__":
    main()
