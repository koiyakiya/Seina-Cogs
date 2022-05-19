"""
MIT License

Copyright (c) 2022-present japandotorg

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

from typing import Any

from ...engine import AdaptedConnection
from .pymysql import MySQLDialect_pymysql

class AsyncAdapt_aiomysql_cursor:
    server_side: bool
    await_: Any
    def __init__(self, adapt_connection) -> None: ...
    @property
    def description(self): ...
    @property
    def rowcount(self): ...
    @property
    def arraysize(self): ...
    @arraysize.setter
    def arraysize(self, value) -> None: ...
    @property
    def lastrowid(self): ...
    def close(self) -> None: ...
    def execute(self, operation, parameters: Any | None = ...): ...
    def executemany(self, operation, seq_of_parameters): ...
    def setinputsizes(self, *inputsizes) -> None: ...
    def __iter__(self): ...
    def fetchone(self): ...
    def fetchmany(self, size: Any | None = ...): ...
    def fetchall(self): ...

class AsyncAdapt_aiomysql_ss_cursor(AsyncAdapt_aiomysql_cursor):
    server_side: bool
    await_: Any
    def __init__(self, adapt_connection) -> None: ...
    def close(self) -> None: ...
    def fetchone(self): ...
    def fetchmany(self, size: Any | None = ...): ...
    def fetchall(self): ...

class AsyncAdapt_aiomysql_connection(AdaptedConnection):
    await_: Any
    dbapi: Any
    def __init__(self, dbapi, connection) -> None: ...
    def ping(self, reconnect): ...
    def character_set_name(self): ...
    def autocommit(self, value) -> None: ...
    def cursor(self, server_side: bool = ...): ...
    def rollback(self) -> None: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...

class AsyncAdaptFallback_aiomysql_connection(AsyncAdapt_aiomysql_connection):
    await_: Any

class AsyncAdapt_aiomysql_dbapi:
    aiomysql: Any
    pymysql: Any
    paramstyle: str
    def __init__(self, aiomysql, pymysql) -> None: ...
    def connect(self, *arg, **kw): ...

class MySQLDialect_aiomysql(MySQLDialect_pymysql):
    driver: str
    supports_statement_cache: bool
    supports_server_side_cursors: bool
    is_async: bool
    @classmethod
    def dbapi(cls): ...
    @classmethod
    def get_pool_class(cls, url): ...
    def create_connect_args(self, url): ...
    def is_disconnect(self, e, connection, cursor): ...
    def get_driver_connection(self, connection): ...

dialect = MySQLDialect_aiomysql