#!/usr/bin/env python3
"""
Small helper script to generate a configurable amount of BilligHistory points inside an
InfluxDB with random credit losses per entry.
Use the docker-compose inside the repo to create an InfluxDB without authentication.
InfluxDB connection information are taken from the environment, see the documentation
about ``Settings`` and ``InfluxDB interaction``.
"""

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from asyncio import run
from dataclasses import replace
from datetime import datetime, timedelta
from random import randint

from os_credits.credits.models import BillingHistory
from os_credits.influx.client import InfluxDBClient

INITIAL_CREDITS = 100_000
PROJECT = "history_test"
ENTRIES = 20_000
RANDOM_INTERVAL = [1, 5]
BILLING_INTERVAL_SECONDS = 1800
METRIC = "generated_credits"


async def main() -> int:
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter, description=__doc__
    )
    parser.add_argument(
        "-c",
        "--initial-credits",
        type=int,
        help="Amount of initial credits",
        default=INITIAL_CREDITS,
    )
    parser.add_argument("-p", "--project", default=PROJECT, help="Name of the project")
    parser.add_argument(
        "-e",
        "--entries",
        default=ENTRIES,
        type=int,
        help="How many entries should be created",
    )
    parser.add_argument(
        "-i",
        "--credits-interval",
        type=int,
        nargs=2,
        default=RANDOM_INTERVAL,
        help="Interval used for random credits amount",
    )
    parser.add_argument(
        "-t",
        "--time-interval",
        type=int,
        default=BILLING_INTERVAL_SECONDS,
        help="How many seconds should pass between each bill",
    )
    parser.add_argument(
        "-m",
        "--metric",
        default=METRIC,
        help="Name of the metric to bill for (will be used as friendly name as well)",
    )

    args = parser.parse_args()

    client = InfluxDBClient()

    if not await client.ensure_history_db_exists():
        print("Credits history db does not exist. Aborting")
        return 1

    billing_interval = timedelta(seconds=args.time_interval)
    billing_point = BillingHistory(
        measurement=args.project,
        time=datetime.now() - billing_interval * args.entries,
        credits_left=args.initial_credits - randint(*args.credits_interval),
        metric_name=args.metric,
        metric_friendly_name=args.metric,
    )
    points = [billing_point]

    for _ in range(args.entries - 1):
        billing_point = replace(
            billing_point,
            credits_left=billing_point.credits_left - randint(*args.credits_interval),
            time=billing_point.time + billing_interval,
        )
        points.append(billing_point)
    print("Generated points. Sending to InfluxDB now")
    await client.write_billing_history(points)

    return 0


if __name__ == "__main__":
    exit(run(main()))
