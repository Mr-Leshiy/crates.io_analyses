import argparse
import pandas
import matplotlib.pyplot as plt


def main(args):
    dt = pandas.concat([pandas.read_csv(f) for f in args.csv])
    print(f"Total crates amount: {dt.size}")
    advisories_failure_amount = dt["advisories"].value_counts().get(False, default=0)
    print(
        f"Advisories failure: {advisories_failure_amount}/{dt.size} = {advisories_failure_amount / dt.size * 100}%"
    )
    bans_failure_amount = dt["bans"].value_counts().get(False, default=0)
    print(
        f"Bans failure: {bans_failure_amount}/{dt.size} = {bans_failure_amount / dt.size * 100}%"
    )
    licences_failure_amount = dt["licenses"].value_counts().get(False, default=0)
    print(
        f"Licenses failure: {licences_failure_amount}/{dt.size} = {licences_failure_amount / dt.size * 100}%"
    )
    sources_failure_amount = dt["sources"].value_counts().get(False, default=0)
    print(
        f"Sources failure: {sources_failure_amount}/{dt.size} = {sources_failure_amount / dt.size * 100}%"
    )

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

    advisories_groupped = (
        pandas.cut(dt[dt["advisories"] == False]["downloads"], bins=download_bins)
        .value_counts()
        .sort_index()
    )
    plt.figure()
    advisories_groupped.plot.bar(
        title="Downloads Distribution (Advisories = False)",
        xlabel="Download Range",
        ylabel="Number of Entries",
        color="skyblue",
        edgecolor="black",
    )
    plt.show()

    bans_groupped = (
        pandas.cut(dt[dt["bans"] == False]["downloads"], bins=download_bins)
        .value_counts()
        .sort_index()
    )
    plt.figure()
    bans_groupped.plot.bar(
        title="Downloads Distribution (Bans = False)",
        xlabel="Download Range",
        ylabel="Number of Entries",
        color="skyblue",
        edgecolor="black",
    )
    plt.show()

    licences_groupped = (
        pandas.cut(dt[dt["licenses"] == False]["downloads"], bins=download_bins)
        .value_counts()
        .sort_index()
    )
    plt.figure()
    licences_groupped.plot.bar(
        title="Downloads Distribution (Licenses = False)",
        xlabel="Download Range",
        ylabel="Number of Entries",
        color="skyblue",
        edgecolor="black",
    )
    plt.show()

    sources_groupped = (
        pandas.cut(dt[dt["sources"] == False]["downloads"], bins=download_bins)
        .value_counts()
        .sort_index()
    )
    plt.figure()
    sources_groupped.plot.bar(
        title="Downloads Distribution (Sources = False)",
        xlabel="Download Range",
        ylabel="Number of Entries",
        color="skyblue",
        edgecolor="black",
    )
    plt.show()


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
