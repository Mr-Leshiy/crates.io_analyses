import argparse
import pandas
import matplotlib.pyplot as plt

download_bins = [
        0,
        100,
        1_000,
        10_000,
        100_000,
        1_000_000,
        10_000_000,
        float("inf"),
]

def analyze(dt: pandas.DataFrame, criteria: str):
    failure_amount = dt[criteria].value_counts().get(False, default=0)
    print(
        f"{criteria} failure: {failure_amount}/{dt.size} = {failure_amount / dt.size * 100}%"
    )

    groupped = (
        pandas.cut(dt[dt[criteria] == False]["downloads"], bins=download_bins)
        .value_counts()
        .sort_index()
    )
    plt.figure()
    groupped.plot.bar(
        title=f"Downloads Distribution ({criteria} = False)",
        xlabel="Download Range",
        ylabel="Number of Entries",
        color="skyblue",
        edgecolor="black",
    )
    plt.show()

def main(args):
    dt = pandas.concat([pandas.read_csv(f) for f in args.csv])
    dt = dt.drop_duplicates(subset='name', keep=False)
    print(f"Total crates amount: {dt.size}")
    analyze(dt, "advisories")
    analyze(dt, "bans")
    analyze(dt, "licenses")
    analyze(dt, "sources")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="crates.io gatheting tool.")
    parser.add_argument(
        "--csv",
        type=str,
        action="append",
        required=True,
        help="The list of analysed crates info csv files",
    )
    args = parser.parse_args()
    main(args)
