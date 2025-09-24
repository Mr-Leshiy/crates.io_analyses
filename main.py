import csv
import asyncio
import aiohttp
import aiofiles
import tempfile

CRATES_IO_URL = "https://crates.io/api"


def endpoint_url(endpoint):
    return f"{CRATES_IO_URL}/{endpoint}"


async def main():
    fname = "crates_info.csv"
    print(f"Loading crates info into the {fname}")
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

            info = await crates_info(s, "?sort=new")

            crates = await asyncio.gather(
                *[
                    analyse_crate(
                        s, crate["name"], crate["newest_version"], crate["updated_at"]
                    )
                    for crate in info["crates"]
                ]
            )
            writer.writerows(crates)

            current_amount = len(crates)
            next_page = info["meta"]["next_page"]
            total_amount = info["meta"]["total"]

            while next_page:
                print(
                    f"{round(current_amount / total_amount * 100, 2)}%",
                    end="\r",
                    flush=True,
                )

                info = await crates_info(s, next_page)

                crates = await asyncio.gather(
                    *[
                        analyse_crate(s, crate["name"], crate["newest_version"])
                        for crate in info["crates"]
                    ]
                )
                writer.writerows(crates)

                current_amount += len(crates)
                next_page = info["meta"]["next_page"]

            print(f"All crates info loaded, total crates amount: {len(crates)}")


async def analyse_crate(
    s: aiohttp.ClientSession, name: str, version: str, upload_time: str
):
    crate_name = f"{name}_{version}"
    fname = f"{crate_name}.tar.gz"
    with tempfile.TemporaryDirectory(dir="./") as tmpdirname:
        async with (
            s.get(endpoint_url(f"v1/crates/{name}/{version}/download")) as resp,
            aiofiles.open(f"{tmpdirname}/{fname}", "wb") as f,
        ):
            if resp.content_type != "application/gzip":
                raise "Is not 'application/gzip'"

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
    asyncio.run(main())
