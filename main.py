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


async def main():
    fname = "crates_info.csv"
    logger.info(f"Loading crates info into the {fname}")
    with open(fname, "w") as f:
        async with aiohttp.ClientSession() as s:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "name",
                    "version",
                    "upload_time",
                    "advisories",
                    "bans",
                    "licenses",
                    "sources",
                ]
            )

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


async def analyze_crates(s: aiohttp.ClientSession, crates: dict):
    return list(filter(
        # filter out all `None` elements returned by 'analyse_crate'
        lambda v: v != None,
        await asyncio.gather(
            *map(
                lambda c: analyse_crate(
                    s, c["name"], c["newest_version"], c["updated_at"]
                ),
                filter(lambda c: not c["yanked"], crates),
            ),
        ),
    ))


async def analyse_crate(
    s: aiohttp.ClientSession, name: str, version: str, upload_time: str
):
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
        await asyncio.subprocess.create_subprocess_exec(
            "tar",
            "-xf",
            f"{tmpdirname}/{fname}",
            "--strip-components=1",
            "-C",
            tmpdirname,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
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
        out, _ = await proc.communicate()

        if out == b"":
            return None

        out = out.decode("utf-8").strip().split(", ")
        advisories = out[0].split()[1] == "ok"
        bans = out[1].split()[1] == "ok"
        licenses = out[2].split()[1] == "ok"
        sources = out[3].split()[1] == "ok"
        return [
            name,
            version,
            upload_time,
            advisories,
            bans,
            licenses,
            sources,
        ]


async def crates_info(s: aiohttp.ClientSession, args: str):
    async with s.get(endpoint_url(f"v1/crates{args}")) as resp:
        return await resp.json()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
