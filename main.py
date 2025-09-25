import csv
import asyncio
import aiohttp
import aiofiles
import tempfile
import shutil
import logging

CRATES_IO_URL = "https://crates.io/api"
logger = logging.getLogger(__name__)


def endpoint_url(endpoint):
    return f"{CRATES_IO_URL}/{endpoint}"


class CrateInfo:
    def colum_names() -> list:
        return [
            "name",
            "version",
            "upload_time",
            "downloads",
            "recent_downloads",
            "advisories",
            "bans",
            "licenses",
            "sources",
        ]

    def to_row(
        name: str,
        version: str,
        upload_time: str,
        downloads: int,
        recent_downloads: int,
        advisories: bool,
        bans: bool,
        licenses: bool,
        sources: bool,
    ) -> list:
        return [
            name,
            version,
            upload_time,
            downloads,
            recent_downloads,
            advisories,
            bans,
            licenses,
            sources,
        ]


async def main():
    fname = "crates_info.csv"
    logger.info(f"Loading crates info into the {fname}")
    with open(fname, "w") as f:
        async with aiohttp.ClientSession() as s:
            writer = csv.writer(f)
            writer.writerow(CrateInfo.colum_names())

            info = await crates_info(s, "?sort=new&include_yanked=no")

            crates = await analyze_crates(s, info["crates"])
            processed_amount = len(crates)
            writer.writerows(crates)

            next_page = info["meta"]["next_page"]
            total_amount = info["meta"]["total"]

            while next_page:
                logger.info(f"processed {processed_amount}/{total_amount}")

                info = await crates_info(s, f"{next_page}")
                crates = await analyze_crates(s, info["crates"])
                processed_amount += len(crates)
                writer.writerows(crates)
                next_page = info["meta"]["next_page"]

            logger.info(
                f"All crates info loaded, total amount: {total_amount}, processed amount: {processed_amount}"
            )


async def analyze_crates(s: aiohttp.ClientSession, crates: list):
    crates_iter = filter(lambda c: not c["yanked"], crates)
    crates_iter = map(
        lambda c: analyse_crate(s, c["name"], c["newest_version"], c["updated_at"]),
        crates_iter,
    )
    # filter out all `None` elements returned by 'analyse_crate'
    crates_iter = filter(lambda v: v != None, await asyncio.gather(*crates_iter))
    crates_iter = map(
        lambda v: CrateInfo.to_row(
            name=v[1]["name"],
            version=v[1]["newest_version"],
            upload_time=v[1]["updated_at"],
            downloads=v[1]["downloads"],
            recent_downloads=v[1]["recent_downloads"],
            advisories=v[0][0],
            bans=v[0][1],
            licenses=v[0][2],
            sources=v[0][3],
        ),
        zip(crates_iter, crates),
    )
    return list(crates_iter)


async def analyse_crate(
    s: aiohttp.ClientSession, name: str, version: str, upload_time: str
) -> tuple[bool, bool, bool, bool]:
    "Return 'None' if cannot analyse the crate for some reason"

    crate_name = f"{name}_{version}"
    fname = f"{crate_name}.tar.gz"
    with tempfile.TemporaryDirectory(dir="./") as tmpdirname:
        async with (
            s.get(endpoint_url(f"v1/crates/{name}/{version}/download")) as resp,
            aiofiles.open(f"{tmpdirname}/{fname}", "wb") as f,
        ):
            if resp.content_type != "application/gzip":
                return None

            chunk_size = 1024 * 4
            while True:
                data = await resp.content.read(chunk_size)
                if not data:
                    break
                await f.write(data)

        # unpack archive
        proc = await asyncio.subprocess.create_subprocess_exec(
            "tar",
            "-xf",
            f"{tmpdirname}/{fname}",
            "--strip-components=1",
            "-C",
            tmpdirname,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        # copy `deny.toml` file to that crate dir
        shutil.copyfile("./deny.toml", f"{tmpdirname}/deny.toml", follow_symlinks=True)

        # run 'cargo deny check'
        proc = await asyncio.subprocess.create_subprocess_exec(
            "cargo",
            "deny",
            "check",
            cwd=f"{tmpdirname}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        out, _ = await proc.communicate()

        if out == b"":
            return None

        out = out.decode("utf-8").strip().split(", ")
        advisories = out[0].split()[1] == "ok"
        bans = out[1].split()[1] == "ok"
        licenses = out[2].split()[1] == "ok"
        sources = out[3].split()[1] == "ok"
        return (advisories, bans, licenses, sources)


async def crates_info(s: aiohttp.ClientSession, args: str):
    async with s.get(endpoint_url(f"v1/crates{args}")) as resp:
        return await resp.json()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
