# SPDX-FileCopyrightText: AISEC Pentesting Team
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import binascii
from typing import Any, Optional, TypedDict

from gallia.transports.base import BaseTransport, TargetURI

_TCP_SPEC_TYPE = TypedDict("_TCP_SPEC_TYPE", {})
tcp_spec: dict[Any, Any] = {}
assertion_str = "bug: transport is not connected"


class TCPTransport(BaseTransport, scheme="tcp", spec=tcp_spec):
    def __init__(
        self,
        target: TargetURI,
        reader: Optional[asyncio.StreamReader] = None,
        writer: Optional[asyncio.StreamWriter] = None,
    ) -> None:
        super().__init__(target)
        self.reader = reader
        self.writer = writer

    async def connect(self, timeout: Optional[float] = None) -> None:
        assert (
            self.reader is None and self.writer is None
        ), "bug: transport is already connected"
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.target.hostname, self.target.port), timeout
        )

    async def reconnect(self, timeout: Optional[float] = None) -> None:
        await self.close()
        await self.connect(timeout)

    async def close(self) -> None:
        assert self.reader is not None and self.writer is not None, assertion_str

        self.writer.close()
        await self.writer.wait_closed()
        self.reader = None
        self.writer = None

    async def write(
        self,
        data: bytes,
        timeout: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> int:
        assert self.reader is not None and self.writer is not None, assertion_str

        t = tags + ["write"] if tags is not None else ["write"]
        self.logger.trace(data.hex(), tags=t)

        self.writer.write(data)
        await asyncio.wait_for(self.writer.drain(), timeout)
        return len(data)

    async def read(
        self,
        timeout: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> bytes:
        assert self.reader is not None and self.writer is not None, assertion_str

        data = await asyncio.wait_for(self.reader.read(self.BUFSIZE), timeout)

        t = tags + ["read"] if tags is not None else ["read"]
        self.logger.trace(data.hex(), extra={"tags": t})
        return data

    async def sendto(
        self,
        data: bytes,
        dst: int,
        timeout: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> int:
        raise RuntimeError("sendto() is not implemented")

    async def recvfrom(
        self,
        timeout: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> tuple[int, bytes]:
        raise RuntimeError("recvfrom() is not implemented")


class TCPLineSepTransport(TCPTransport, scheme="tcp-lines", spec=tcp_spec):
    async def write(
        self,
        data: bytes,
        timeout: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> int:
        assert self.reader is not None and self.writer is not None, assertion_str

        t = tags + ["write"] if tags is not None else ["write"]
        self.logger.trace(data.hex(), extra={"tags": t})

        self.writer.write(binascii.hexlify(data) + b"\n")
        await asyncio.wait_for(self.writer.drain(), timeout)
        return len(data)

    async def read(
        self,
        timeout: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> bytes:
        assert self.reader is not None and self.writer is not None, assertion_str

        data = await asyncio.wait_for(self.reader.readline(), timeout)
        d = data.decode().strip()

        t = tags + ["read"] if tags is not None else ["read"]
        self.logger.trace(d, extra={"tags": t})

        return binascii.unhexlify(d)
