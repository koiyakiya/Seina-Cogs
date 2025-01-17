"""
MIT License

Copyright (c) 2024-present japandotorg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# isort: off
import io
import os
import sys
import asyncio
import logging
import platform
from typing import ClassVar, Dict, Final, Optional, Tuple

import discord
import aiohttp

import pathlib
import zipfile
import tarfile
import rich.progress

from redbot.core import data_manager

from .exceptions import DownloadFailed

# isort: on


log: logging.Logger = logging.getLogger("red.seina.screenshot.downloader")


class DriverManager:
    DRIVER_LATEST_RELEASE_URL: Final[str] = (
        "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
    )
    DRIVER_RELEASE_TAG_URL: ClassVar[str] = (
        "https://api.github.com/repos/mozilla/geckodriver/releases/tags/{version}"
    )
    FIREFOX_DOWNLOAD_URL: ClassVar[str] = (
        "https://archive.mozilla.org/pub/firefox/nightly/latest-mozilla-central/firefox-{version}.en-US.{system}.{ext}"
    )
    TOR_EXPERT_BUNDLE_URL: ClassVar[str] = (
        "https://archive.org/download/tor-expert-bundle/tor-expert-bundle-{system}.{ext}"
    )

    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self._tor_process: asyncio.subprocess.Process = discord.utils.MISSING
        self.__session: aiohttp.ClientSession = session or aiohttp.ClientSession()
        self.__event: asyncio.Event = asyncio.Event()

    @property
    def __environ(self) -> Dict[str, str]:
        environ: Dict[str, str] = os.environ.copy()
        if self.tor_location:
            environ["LD_LIBRARY_PATH"] = str(self.tor_location / "tor")
        return environ

    @property
    def data_directory(self) -> pathlib.Path:
        return data_manager.cog_data_path(raw_name="Screenshot") / "data"

    @property
    def driver_location(self) -> Optional[pathlib.Path]:
        return (
            loc[0]
            if (
                loc := list(self.data_directory.glob("geckodriver-{}*".format(self.get_os())))
                or (loc := list(self.data_directory.glob("geckodrive-{}*".format(self.get_os()))))
            )
            else None
        )

    @property
    def firefox_location(self) -> Optional[pathlib.Path]:
        return (
            loc[0]
            if (loc := list(self.data_directory.glob("firefox-{}/firefox*".format(self.get_os()))))
            else None
        )

    @property
    def tor_location(self) -> Optional[pathlib.Path]:
        return (
            loc[0]
            if (loc := list(self.data_directory.glob("tor-{}*".format(self.get_os()))))
            else None
        )

    @staticmethod
    def get_os_name() -> str:
        if platform.machine().lower().startswith("aarch"):
            return "linux-aarch"
        if platform.system().lower() == "linux":
            return "linux"
        elif platform.system().lower() == "windows":
            return "win"
        raise RuntimeError()

    @staticmethod
    def get_firefox_system() -> str:
        if platform.machine().lower() == "aarch64":
            return "linux-aarch64"
        elif platform.system().lower() == "linux":
            if platform.machine().endswith("64"):
                return "linux-x86_64"
            else:
                return "linux-i686"
        elif platform.system().lower() == "windows":
            if platform.machine().endswith("64"):
                return "win64"
            else:
                return "win32"
        raise RuntimeError("Not a supported device.")

    def get_os(self) -> str:
        return "{}{}".format(self.get_os_name(), 64 if platform.machine().endswith("64") else 32)

    def set_driver_downloaded(self) -> None:
        self.__event.set()

    def get_firefox_download_url(self, version: str) -> str:
        return self.FIREFOX_DOWNLOAD_URL.format(
            version=version,
            system=self.get_firefox_system(),
            ext="zip" if self.get_os().startswith("win") else "tar.bz2",
        )

    def get_tor_download_url(self) -> str:
        return self.TOR_EXPERT_BUNDLE_URL.format(
            system=self.get_os(),
            ext="tar.bz2" if self.get_os().startswith("linux-aarch64") else "tar.gz",
        )

    async def wait_until_driver_downloaded(self) -> None:
        await self.__event.wait()

    async def execute_tor_binary(self) -> Optional[asyncio.subprocess.Process]:
        if self.tor_location is not None:
            process: asyncio.subprocess.Process = await asyncio.subprocess.create_subprocess_shell(
                (
                    "{0}/tor/tor -f {0}/torrc"
                    if not self.get_os().startswith("win")
                    else "{0}/tor/tor.exe -f {0}/torrc"
                ).format(self.tor_location),
                env=self.__environ,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            self._tor_process: asyncio.subprocess.Process = process
            log.info("Connected to tor successfully with ip:port 127.0.0.1:21666")

    async def get_latest_release_version(self) -> str:
        async with self.__session.get(url=self.DRIVER_LATEST_RELEASE_URL) as response:
            json: Dict[str, str] = await response.json()
        version: str = json.get("tag_name", "v0.35.0")
        return version

    async def get_driver_download_url(self) -> str:
        version: str = await self.get_latest_release_version()
        async with self.__session.get(
            self.DRIVER_RELEASE_TAG_URL.format(version=version)
        ) as response:
            json = await response.json()
        assets = json["assets"]
        name: str = "{}-{}-{}.".format("geckodriver", version, self.get_os())
        output_dict = [asset for asset in assets if asset["name"].startswith(name)]
        url: str = output_dict[0]["browser_download_url"]
        return url

    async def get_firefox_archive(self) -> Tuple[str, bytes]:
        url: str = self.get_firefox_download_url("132.0a1")
        log.info("Downloading firefox - %s" % url)
        async with self.__session.get(url=url) as response:
            if response.status == 404:
                raise DownloadFailed("Could not find firefox with url: '%s'" % url, retry=False)
            elif 400 <= response.status < 600:
                raise DownloadFailed(retry=True)
            response.raise_for_status()
            byte: bytearray = bytearray()
            byte_num: int = 0
            with rich.progress.Progress(
                rich.progress.SpinnerColumn(),
                rich.progress.TextColumn("[progress.description]{task.description}"),
                rich.progress.BarColumn(),
                rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                rich.progress.TimeRemainingColumn(),
                rich.progress.TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task(
                    "[red.seina.screenshot.downloader] Downloading Firefox",
                    total=response.content_length,
                )
                chunk: bytes = await response.content.read(1024)
                while chunk:
                    byte.extend(chunk)
                    size: int = sys.getsizeof(chunk)
                    byte_num += size
                    progress.update(task, advance=size)
                    chunk: bytes = await response.content.read(1024)
        return url, bytes(byte)

    async def get_driver_archive(self) -> Tuple[str, bytes]:
        url: str = await self.get_driver_download_url()
        log.info("Downloading driver - %s" % url)
        async with self.__session.get(url=url) as response:
            if response.status == 404:
                raise DownloadFailed("Could not find a driver with url: '%s" % url, retry=False)
            elif 400 <= response.status < 600:
                raise DownloadFailed(retry=True)
            response.raise_for_status()
            byte: bytearray = bytearray()
            byte_num: int = 0
            with rich.progress.Progress(
                rich.progress.SpinnerColumn(),
                rich.progress.TextColumn("[progress.description]{task.description}"),
                rich.progress.BarColumn(),
                rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                rich.progress.TimeRemainingColumn(),
                rich.progress.TimeElapsedColumn(),
            ) as progress:
                task: rich.progress.TaskID = progress.add_task(
                    "[red.seina.screenshot.downloader] Downloading driver",
                    total=response.content_length,
                )
                chunk: bytes = await response.content.read(1024)
                while chunk:
                    byte.extend(chunk)
                    size: int = sys.getsizeof(chunk)
                    byte_num += size
                    progress.update(task, advance=size)
                    chunk: bytes = await response.content.read(1024)
        return url, bytes(byte)

    async def get_tor_archive(self) -> Tuple[str, bytes]:
        url: str = self.get_tor_download_url()
        log.info("Downloading tor - %s" % url)
        async with self.__session.get(url=url) as response:
            if response.status == 404:
                raise DownloadFailed(
                    "Could not find tor expert bundle with url: '%s'" % url, retry=False
                )
            elif 400 <= response.status < 600:
                raise DownloadFailed(retry=True)
            response.raise_for_status()
            byte: bytearray = bytearray()
            byte_num: int = 0
            with rich.progress.Progress(
                rich.progress.SpinnerColumn(),
                rich.progress.TextColumn("[progress.description]{task.description}"),
                rich.progress.BarColumn(),
                rich.progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                rich.progress.TimeRemainingColumn(),
                rich.progress.TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task(
                    "[red.seina.screenshot.downloader] Downloading Tor",
                    total=response.content_length,
                )
                chunk: bytes = await response.content.read(1024)
                while chunk:
                    byte.extend(chunk)
                    size: int = sys.getsizeof(chunk)
                    byte_num += size
                    progress.update(task, advance=size)
                    chunk: bytes = await response.content.read(1024)
        return url, bytes(byte)

    async def download_and_extract_firefox(self) -> None:
        url, byte = await self.get_firefox_archive()
        if url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(byte), mode="r") as zip:
                await asyncio.to_thread(lambda: zip.extractall(path=self.data_directory))
        elif url.endswith("tar.bz2"):
            tar: tarfile.TarFile = tarfile.TarFile.open(fileobj=io.BytesIO(byte), mode="r:bz2")
            await asyncio.to_thread(lambda: tar.extractall(path=self.data_directory))
        else:
            raise DownloadFailed("Failed to download firefox.")
        path: pathlib.Path = list(self.data_directory.glob("firefox*"))[0]
        name: str = path.name + "-{}".format(self.get_os())
        os.rename(path, self.data_directory / name)
        log.info("Downloaded firefox successfully with location: {}".format(self.firefox_location))

    async def download_and_extract_driver(self) -> None:
        url, byte = await self.get_driver_archive()
        if url.endswith(".zip"):
            with zipfile.ZipFile(file=io.BytesIO(byte), mode="r") as zip:
                await asyncio.to_thread(lambda: zip.extractall(path=self.data_directory))
        elif url.endswith(".tar.gz"):
            tar: tarfile.TarFile = tarfile.TarFile.open(fileobj=io.BytesIO(byte), mode="r:gz")
            await asyncio.to_thread(lambda: tar.extractall(path=self.data_directory))
        else:
            raise DownloadFailed("Failed to download the driver.")
        path: pathlib.Path = list(self.data_directory.glob("geckodriver*"))[0]
        idx: int = path.name.rfind(".")
        name: str = path.name[:idx] + "-{}".format(self.get_os())
        os.rename(
            path,
            (
                self.data_directory / "{}.exe".format(name)
                if self.get_os().startswith("win")
                else self.data_directory / name
            ),
        )
        log.info("Downloaded driver successfully with location: {}".format(self.driver_location))

    async def download_and_extract_tor(self) -> None:
        url, byte = await self.get_tor_archive()
        if url.endswith("bz2"):
            tar: tarfile.TarFile = tarfile.TarFile.open(fileobj=io.BytesIO(byte), mode="r:bz2")
            await asyncio.to_thread(lambda: tar.extractall(path=self.data_directory))
        elif url.endswith("gz"):
            tar: tarfile.TarFile = tarfile.TarFile.open(fileobj=io.BytesIO(byte), mode="r:gz")
            await asyncio.to_thread(
                lambda: tar.extractall(path=self.data_directory / "tor-{}".format(self.get_os()))
            )
        else:
            raise DownloadFailed("Failed to download tor.")
        if self.tor_location is not None:
            file: pathlib.Path = self.tor_location / "torrc"
            with file.open("w", encoding="utf-8") as t:
                t.write(
                    """
                    # Ports
                    SOCKSPort 21666
                    ControlPort 27666
                    
                    # Logs
                    Log debug file {}
                    DataDirectory {}
                    """.format(
                        self.data_directory / "tor.log", self.tor_location / "teb-data"
                    )
                )
        log.info("Downloaded tor successfully with location: {}".format(self.tor_location))
