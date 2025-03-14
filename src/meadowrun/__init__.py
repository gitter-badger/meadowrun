import asyncio
import sys
import traceback
import warnings
from typing import Any

if sys.platform == "win32":
    # The default event loop type was changed from the selector event loop to the
    # proactor event loop in python 3.8. To make meadowrun work on python 3.7, we need
    # to use proactor event loops--aiohttp and asyncio.subprocess don't seem to work
    # with the selector event loop
    if sys.version_info < (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # There's a bug in the proactor event loop that causes messages like "Exception
    # ignored in: # <function _ProactorBasePipeTransport.__del__ at 0x...>" to be
    # printed. We make extensive use of aiohttp, so we produce lots of messages like
    # this. Below is monkey-patching the fix for this issue, see
    # https://github.com/python/cpython/pull/92842/files via
    # https://github.com/python/cpython/issues/83413 and
    # https://github.com/aio-libs/aiohttp/issues/4324 We should keep an eye on that
    # change and refine this version check as the fix gets backported to older versions
    # of python
    if sys.version_info < (3, 12):
        try:
            from asyncio.proactor_events import _ProactorBasePipeTransport

            def new__del__(self: Any, _warn: Any = warnings.warn) -> None:
                if self._sock is not None:
                    _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
                    self._sock.close()

            # we can't just do a simple assignment because that causes a mypy error as
            # described in https://github.com/python/mypy/issues/2427 and we can't just
            # "type: ignore" that error because we will get a "type: ignore unused"
            # error on Linux (even though that seems like it should work based on
            # https://github.com/python/mypy/issues/8547 and
            # https://github.com/python/mypy/issues/8823). Luckily the setattr
            # workaround works.
            setattr(_ProactorBasePipeTransport, "__del__", new__del__)
        except Exception:
            traceback.print_exc()


from meadowrun.run_job import (
    AllocCloudInstance,
    AllocCloudInstances,
    Deployment,
    run_command,
    run_function,
    run_map,
)
from meadowrun.run_job_local import LocalHost
from meadowrun.run_job_core import SshHost

from meadowrun.meadowrun_pb2 import (
    AwsSecret,
    AzureSecret,
    ContainerAtDigest,
    ContainerAtTag,
    GitRepoBranch,
    GitRepoCommit,
    ServerAvailableContainer,
    ServerAvailableFile,
    ServerAvailableFolder,
    ServerAvailableInterpreter,
)


__all__ = [
    "AllocCloudInstance",
    "AllocCloudInstances",
    "Deployment",
    "run_command",
    "run_function",
    "run_map",
    "LocalHost",
    "SshHost",
    "AwsSecret",
    "AzureSecret",
    "ContainerAtDigest",
    "ContainerAtTag",
    "GitRepoBranch",
    "GitRepoCommit",
    "ServerAvailableContainer",
    "ServerAvailableFile",
    "ServerAvailableFolder",
    "ServerAvailableInterpreter",
]
