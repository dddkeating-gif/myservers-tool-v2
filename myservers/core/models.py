from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HostSet:
    internal_primary: str = ""
    internal_secondary: str = ""
    external_primary: str = ""
    external_secondary: str = ""


@dataclass
class Server:
    name: str
    hosts: HostSet

