import pytest
import yaml

from iotdb.table_session import TableSession, TableSessionConfig
from iotdb.utils.IoTDBConstants import TSDataType
from iotdb.utils.Tablet import ColumnType, Tablet

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""表模型 OBJECT 类型测试。"""

config_path = "../conf/config.yml"
OBJECT_TEST_DATABASE = "test_object_py"
OBJECT_CATEGORY_DATABASE = "test_object_category"
OBJECT_RESTRICT_DATABASE = "test_object_limit_false"

_session = None
_tables_created = []


def load_object_test_config():
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_object_connection_info():
    config = load_object_test_config()
    host = config.get("host")
    port = config.get("port")
    if not host or not port:
        first_node_url = config["node_urls"][0]
        host, port = first_node_url.rsplit(":", 1)
    return host, int(port), config["username"], config["password"]


def object_init_session():
    global _session, _tables_created

    host, port, username, password = get_object_connection_info()
    config = TableSessionConfig(
        node_urls=[f"{host}:{port}"],
        username=username,
        password=password,
    )
    _session = TableSession(config)
    _tables_created = []

    try:
        _session.execute_non_query_statement(f"DROP DATABASE {OBJECT_TEST_DATABASE}")
    except Exception:
        pass

    try:
        _session.execute_non_query_statement(f"CREATE DATABASE {OBJECT_TEST_DATABASE}")
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise

    _session.execute_non_query_statement(f"USE {OBJECT_TEST_DATABASE}")
    return _session


def object_get_session():
    assert _session is not None, "OBJECT test session is not initialized."
    return _session


def object_close_session():
    global _session, _tables_created

    if _session is None:
        return

    for table in _tables_created:
        try:
            _session.execute_non_query_statement(f"DROP TABLE {table}")
        except Exception:
            pass

    try:
        _session.execute_non_query_statement(f"DROP DATABASE {OBJECT_TEST_DATABASE}")
    except Exception:
        pass

    _session.close()
    _session = None
    _tables_created = []


def object_cleanup_tables():
    global _tables_created

    if _session is None:
        _tables_created = []
        return

    for table in _tables_created:
        try:
            _session.execute_non_query_statement(f"DROP TABLE {table}")
        except Exception:
            pass
    _tables_created = []


def object_create_table(sql):
    object_get_session().execute_non_query_statement(sql)
    table_name = sql.split("(", 1)[0].split()[-1].strip()
    _tables_created.append(table_name)


def read_object_content(table_name, where_clause="", order_by_time=True, column_name="obj_col"):
    sql = f"SELECT READ_OBJECT({column_name}) FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    if order_by_time:
        sql += " ORDER BY time"

    result = []
    with object_get_session().execute_query_statement(sql) as result_set:
        while result_set.has_next():
            row = result_set.next()
            result.append(row.get_fields()[0].get_binary_value())
    return result


def read_object_display(table_name, where_clause="", order_by_time=True, column_name="obj_col"):
    sql = f"SELECT {column_name} FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    if order_by_time:
        sql += " ORDER BY time"

    result = []
    with object_get_session().execute_query_statement(sql) as result_set:
        while result_set.has_next():
            row = result_set.next()
            result.append(row.get_fields()[0].get_string_value())
    return result


def assert_read_object_fails(
    table_name,
    where_clause="",
    expected_message_parts=None,
    column_name="obj_col",
):
    sql = f"SELECT READ_OBJECT({column_name}) FROM {table_name}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += " ORDER BY time"

    with pytest.raises(Exception) as exc_info:
        with object_get_session().execute_query_statement(sql) as result_set:
            while result_set.has_next():
                result_set.next()

    message = str(exc_info.value)
    if expected_message_parts:
        for part in expected_message_parts:
            assert part in message
    return message


def assert_object_display(display_value, expected_size=None, expect_null=False):
    if expect_null:
        assert display_value is None or str(display_value).lower() in ("null", "none", "")
        return

    assert display_value is not None
    text = str(display_value)
    assert text.lower() not in ("null", "none", "")
    if expected_size is not None and text.startswith("(Object)"):
        assert f"{expected_size} B" in text


def fetch_query_rows(sql, value_getter="string"):
    rows = []
    with object_get_session().execute_query_statement(sql) as result_set:
        while result_set.has_next():
            row = result_set.next()
            values = []
            for field in row.get_fields():
                if value_getter == "binary":
                    values.append(field.get_binary_value())
                elif value_getter == "int":
                    values.append(field.get_long_value())
                elif value_getter == "object":
                    values.append(field.get_object_value(field.get_data_type()))
                else:
                    values.append(field.get_string_value())
            rows.append(values)
    return rows


def assert_query_fails(sql, expected_message_parts=None):
    with pytest.raises(Exception) as exc_info:
        with object_get_session().execute_query_statement(sql) as result_set:
            while result_set.has_next():
                result_set.next()

    message = str(exc_info.value)
    if expected_message_parts:
        for part in expected_message_parts:
            assert part in message
    return message


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def make_table_session():
    host, port, username, password = get_object_connection_info()
    return TableSession(
        TableSessionConfig(
            node_urls=[f"{host}:{port}"],
            username=username,
            password=password,
        )
    )


@pytest.fixture()
def merged_object_case_session():
    session = make_table_session()
    try:
        for database_name in [OBJECT_CATEGORY_DATABASE, OBJECT_RESTRICT_DATABASE]:
            try:
                session.execute_non_query_statement(f"DROP DATABASE {database_name}")
            except Exception:
                pass
            session.execute_non_query_statement(f"CREATE DATABASE {database_name}")
        yield session
    finally:
        for database_name in [OBJECT_CATEGORY_DATABASE, OBJECT_RESTRICT_DATABASE]:
            try:
                session.execute_non_query_statement(f"DROP DATABASE {database_name}")
            except Exception:
                pass
        session.close()


# ============================================================================
# 01. 公共会话基类
# ============================================================================


class ObjectSessionTestBase:
    """OBJECT 集成测试公共会话基类。"""

    @classmethod
    def setup_class(cls):
        object_init_session()

    @classmethod
    def teardown_class(cls):
        object_close_session()


# ============================================================================
# 02. Tablet 写入测试
# ============================================================================


class TestTabletWrite(ObjectSessionTestBase):
    """Tablet 写入 OBJECT 列测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def test_01_basic_write(self):
        """用例01：使用 Tablet 写入单条 OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE t_basic(device STRING TAG, obj_col OBJECT FIELD)")

        payload = b"\xca\xfe\xba\xbe"
        tablet = Tablet(
            "t_basic",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, payload)
        session.insert(tablet)

        assert read_object_content("t_basic") == [payload]

    def test_02_multiple_rows(self):
        """用例02：使用 Tablet 连续写入多行 OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE t_multi(device STRING TAG, obj_col OBJECT FIELD)")

        payloads = [b"\x01\x02", b"\x03\x04", b"\x05\x06"]
        tablet = Tablet(
            "t_multi",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None], ["d2", None], ["d3", None]],
            [1, 2, 3],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        for row_index, payload in enumerate(payloads):
            tablet.add_value_object(row_index, 1, True, 0, payload)
        session.insert(tablet)

        with session.execute_query_statement("SELECT * FROM t_multi ORDER BY time") as result_set:
            rows = []
            while result_set.has_next():
                row = result_set.next()
                fields = row.get_fields()
                rows.append(
                    (
                        fields[0].get_string_value(),
                        fields[1].get_string_value(),
                        fields[2].get_string_value(),
                    )
                )

        assert [row[1] for row in rows] == ["d1", "d2", "d3"]
        for _, _, display_value in rows:
            assert_object_display(display_value, expected_size=2)
        assert read_object_content("t_multi") == payloads

    def test_03_multiple_columns(self):
        """用例03：单行中写入多个 OBJECT 列。"""
        session = object_get_session()
        object_create_table(
            "CREATE TABLE t_cols(device STRING TAG, o1 OBJECT FIELD, o2 OBJECT FIELD, o3 OBJECT FIELD)"
        )

        payloads = [b"obj1", b"obj2", b"obj3"]
        tablet = Tablet(
            "t_cols",
            ["device", "o1", "o2", "o3"],
            [TSDataType.STRING, TSDataType.OBJECT, TSDataType.OBJECT, TSDataType.OBJECT],
            [["d1", None, None, None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD, ColumnType.FIELD, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, payloads[0])
        tablet.add_value_object(0, 2, True, 0, payloads[1])
        tablet.add_value_object(0, 3, True, 0, payloads[2])
        session.insert(tablet)

        with session.execute_query_statement(
            "SELECT READ_OBJECT(o1), READ_OBJECT(o2), READ_OBJECT(o3) FROM t_cols"
        ) as result_set:
            row = result_set.next()
            fields = row.get_fields()
            assert fields[0].get_binary_value() == payloads[0]
            assert fields[1].get_binary_value() == payloads[1]
            assert fields[2].get_binary_value() == payloads[2]

    def test_04_single_row_mixed_columns(self):
        """用例04：单行混合写入普通列和 OBJECT 列。"""
        session = object_get_session()
        object_create_table(
            "CREATE TABLE t_mixed(device STRING TAG, i INT32 FIELD, f FLOAT FIELD, s STRING FIELD, obj OBJECT FIELD)"
        )

        payload = b"\xaa\xbb"
        tablet = Tablet(
            "t_mixed",
            ["device", "i", "f", "s", "obj"],
            [TSDataType.STRING, TSDataType.INT32, TSDataType.FLOAT, TSDataType.STRING, TSDataType.OBJECT],
            [["d1", 100, 1.5, "hello", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD, ColumnType.FIELD, ColumnType.FIELD, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 4, True, 0, payload)
        session.insert(tablet)

        with session.execute_query_statement("SELECT i, f, s, obj FROM t_mixed") as result_set:
            row = result_set.next()
            fields = row.get_fields()
            assert fields[0].get_int_value() == 100
            assert abs(fields[1].get_float_value() - 1.5) < 1e-6
            assert fields[2].get_string_value() == "hello"
            assert_object_display(fields[3].get_string_value(), expected_size=2)

        assert read_object_content("t_mixed", column_name="obj") == [payload]

    def test_05_multi_row_mixed_columns(self):
        """用例05：多行混合写入普通列和 OBJECT 列。"""
        session = object_get_session()
        object_create_table(
            "CREATE TABLE t_mixed(device STRING TAG, i INT32 FIELD, f FLOAT FIELD, s STRING FIELD, obj OBJECT FIELD)"
        )

        payloads = [b"\xaa\xbb", b"\xcc\xdd"]
        tablet = Tablet(
            "t_mixed",
            ["device", "i", "f", "s", "obj"],
            [TSDataType.STRING, TSDataType.INT32, TSDataType.FLOAT, TSDataType.STRING, TSDataType.OBJECT],
            [["d1", 100, 1.5, "hello", None], ["d2", 200, 2.5, "world", None]],
            [1, 2],
            [ColumnType.TAG, ColumnType.FIELD, ColumnType.FIELD, ColumnType.FIELD, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 4, True, 0, payloads[0])
        tablet.add_value_object(1, 4, True, 0, payloads[1])
        session.insert(tablet)

        with session.execute_query_statement("SELECT i, f, s, obj FROM t_mixed ORDER BY time") as result_set:
            rows = []
            while result_set.has_next():
                row = result_set.next()
                fields = row.get_fields()
                rows.append(
                    (
                        fields[0].get_int_value(),
                        fields[1].get_float_value(),
                        fields[2].get_string_value(),
                        fields[3].get_string_value(),
                    )
                )

        assert rows[0][0] == 100
        assert rows[1][0] == 200
        assert abs(rows[0][1] - 1.5) < 1e-6
        assert abs(rows[1][1] - 2.5) < 1e-6
        assert rows[0][2] == "hello"
        assert rows[1][2] == "world"
        assert_object_display(rows[0][3], expected_size=2)
        assert_object_display(rows[1][3], expected_size=2)
        assert read_object_content("t_mixed", column_name="obj") == payloads

    def test_06_add_by_name(self):
        """用例06：通过列名写入 OBJECT 值。"""
        session = object_get_session()
        object_create_table("CREATE TABLE t_name(device STRING TAG, obj_col OBJECT FIELD)")

        payload = b"test_data"
        tablet = Tablet(
            "t_name",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object_by_name("obj_col", 0, True, 0, payload)
        session.insert(tablet)

        assert read_object_content("t_name") == [payload]


# ============================================================================
# 03. 空值与空内容测试
# ============================================================================


class TestNullValues(ObjectSessionTestBase):
    """OBJECT 空值与空内容测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def test_01_empty_payload(self):
        """用例01：写入空 OBJECT 内容。"""
        session = object_get_session()
        object_create_table("CREATE TABLE n_empty(device STRING TAG, obj_col OBJECT FIELD)")

        tablet = Tablet(
            "n_empty",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, b"")
        session.insert(tablet)

        display = read_object_display("n_empty")
        assert len(display) == 1
        assert_object_display(display[0], expected_size=0)
        assert_read_object_fails("n_empty", expected_message_parts=["offset", "object size 0"])

    def test_02_sql_null(self):
        """用例02：在 OBJECT 列中写入 SQL NULL。"""
        session = object_get_session()
        object_create_table("CREATE TABLE n_sql(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO n_sql(time, device, obj_col) VALUES(1, 'd1', null)"
        )

        display = read_object_display("n_sql")
        assert len(display) == 1
        assert_object_display(display[0], expect_null=True)

        with session.execute_query_statement(
            "SELECT COUNT(*) FROM n_sql WHERE obj_col IS NULL"
        ) as result_set:
            assert result_set.next().get_fields()[0].get_long_value() == 1

        with session.execute_query_statement(
            "SELECT COUNT(*) FROM n_sql WHERE obj_col IS NOT NULL"
        ) as result_set:
            assert result_set.next().get_fields()[0].get_long_value() == 0

    def test_03_tablet_partial_null(self):
        """用例03：Tablet 中部分行写 OBJECT、部分行为空。"""
        session = object_get_session()
        object_create_table("CREATE TABLE n_partial(device STRING TAG, obj_col OBJECT FIELD)")

        tablet = Tablet(
            "n_partial",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None], ["d2", None], ["d3", None]],
            [1, 2, 3],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, b"row1")
        tablet.add_value_object(2, 1, True, 0, b"row3")
        session.insert(tablet)

        display = read_object_display("n_partial")
        assert len(display) == 3
        assert_object_display(display[0], expected_size=4)
        assert_object_display(display[1], expect_null=True)
        assert_object_display(display[2], expected_size=4)
        assert read_object_content("n_partial", "time = 1") == [b"row1"]
        assert read_object_content("n_partial", "time = 3") == [b"row3"]

        with session.execute_query_statement(
            "SELECT COUNT(*) FROM n_partial WHERE obj_col IS NULL"
        ) as result_set:
            assert result_set.next().get_fields()[0].get_long_value() == 1

    def test_04_alternating_null(self):
        """用例04：OBJECT 行与 SQL NULL 行交替写入。"""
        session = object_get_session()
        object_create_table("CREATE TABLE n_alt(device STRING TAG, obj_col OBJECT FIELD)")

        for time_value in range(1, 11):
            if time_value % 2 == 1:
                session.execute_non_query_statement(
                    f"INSERT INTO n_alt(time, device, obj_col) VALUES({time_value}, 'tag1', to_object(true, 0, X'62'))"
                )
            else:
                session.execute_non_query_statement(
                    f"INSERT INTO n_alt(time, device, obj_col) VALUES({time_value}, 'tag1', null)"
                )

        display = read_object_display("n_alt")
        assert len(display) == 10
        for index, value in enumerate(display):
            if index % 2 == 0:
                assert_object_display(value, expected_size=1)
            else:
                assert_object_display(value, expect_null=True)

        assert read_object_content("n_alt", "obj_col IS NOT NULL") == [b"\x62"] * 5

        with session.execute_query_statement(
            "SELECT COUNT(*) FROM n_alt WHERE obj_col IS NULL"
        ) as result_set:
            assert result_set.next().get_fields()[0].get_long_value() == 5


# ============================================================================
# 04. SQL 写入测试
# ============================================================================


class TestSQLWrite(ObjectSessionTestBase):
    """SQL 写入 OBJECT 测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def test_01_sql_to_object(self):
        """用例01：使用 SQL 的 to_object 函数写入 OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_to(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO sql_to(time, device, obj_col) VALUES(1, 'd1', to_object(true, 0, X'cafebabe'))"
        )

        assert read_object_content("sql_to") == [b"\xca\xfe\xba\xbe"]

    def test_02_sql_vs_tablet(self):
        """用例02：对比 SQL 写入和 Tablet 写入的 OBJECT 结果。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_vs(device STRING TAG, obj_col OBJECT FIELD)")

        payload = b"\xde\xad\xbe\xef"
        session.execute_non_query_statement(
            "INSERT INTO sql_vs(time, device, obj_col) VALUES(1, 'sql', to_object(true, 0, X'deadbeef'))"
        )

        tablet = Tablet(
            "sql_vs",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["tablet", None]],
            [2],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, payload)
        session.insert(tablet)

        assert read_object_content("sql_vs") == [payload, payload]

    def test_03_read_object_fails_with_zero_byte_row(self):
        """用例03：结果集中存在 0 字节 OBJECT 时，READ_OBJECT 应报错。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_zero_mix(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO sql_zero_mix(time, device, obj_col) VALUES(1, 'd1', to_object(true, 0, X'1234'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO sql_zero_mix(time, device, obj_col) VALUES(2, 'd2', to_object(true, 0, X''))"
        )

        display = read_object_display("sql_zero_mix")
        assert len(display) == 2
        assert_object_display(display[0], expected_size=2)
        assert_object_display(display[1], expected_size=0)
        assert_read_object_fails(
            "sql_zero_mix",
            expected_message_parts=["offset", "object size 0"],
        )

    def test_04_read_object_succeeds_after_filtering_to_normal_row(self):
        """用例04：过滤到正常 OBJECT 行后，READ_OBJECT 应成功。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_zero_filter(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO sql_zero_filter(time, device, obj_col) VALUES(1, 'd1', to_object(true, 0, X'1234'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO sql_zero_filter(time, device, obj_col) VALUES(2, 'd2', to_object(true, 0, X''))"
        )

        assert read_object_content("sql_zero_filter", "time = 1") == [b"\x12\x34"]

    def test_05_read_object_fails_after_filtering_to_zero_byte_row(self):
        """用例05：过滤到 0 字节 OBJECT 行后，READ_OBJECT 仍应报错。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_zero_filter(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO sql_zero_filter(time, device, obj_col) VALUES(1, 'd1', to_object(true, 0, X'1234'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO sql_zero_filter(time, device, obj_col) VALUES(2, 'd2', to_object(true, 0, X''))"
        )

        assert_read_object_fails(
            "sql_zero_filter",
            "time = 2",
            expected_message_parts=["offset", "object size 0"],
        )

    def test_06_select_still_returns_object_when_device_is_null(self):
        """用例06：device 为 SQL NULL 时，SELECT 仍应返回 OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_device_null(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO sql_device_null(time, device, obj_col) VALUES(1, null, to_object(true, 0, X'0102'))"
        )

        rows = fetch_query_rows("SELECT * FROM sql_device_null ORDER BY time")
        assert len(rows) == 1
        assert str(rows[0][1]).lower() in ("none", "null", "")
        assert rows[0][2] not in (None, "", "null", "None")

        display_rows = fetch_query_rows("SELECT device, obj_col FROM sql_device_null ORDER BY time")
        assert len(display_rows) == 1
        assert str(display_rows[0][0]).lower() in ("none", "null", "")
        assert display_rows[0][1] not in (None, "", "null", "None")

        assert read_object_content("sql_device_null") == [b"\x01\x02"]

    def test_07_select_still_returns_object_when_device_is_empty_string(self):
        """用例07：device 为空字符串时，SELECT 仍应返回 OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE sql_device_empty(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO sql_device_empty(time, device, obj_col) VALUES(1, '', to_object(true, 0, X'0304'))"
        )

        rows = fetch_query_rows("SELECT * FROM sql_device_empty ORDER BY time")
        assert len(rows) == 1
        assert rows[0][1] == ""
        assert rows[0][2] not in (None, "", "null", "None")

        display_rows = fetch_query_rows("SELECT device, obj_col FROM sql_device_empty ORDER BY time")
        assert len(display_rows) == 1
        assert display_rows[0][0] == ""
        assert display_rows[0][1] not in (None, "", "null", "None")

        assert read_object_content("sql_device_empty") == [b"\x03\x04"]


# ============================================================================
# 05. 分段写入测试
# ============================================================================


class TestSegmentedWrite(ObjectSessionTestBase):
    """OBJECT 分段写入测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def test_01_complete_write(self):
        """用例01：单段完整写入 OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE seg_full(device STRING TAG, obj_col OBJECT FIELD)")

        tablet = Tablet(
            "seg_full",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, b"\xca\xfe\xba\xbe")
        session.insert(tablet)

        assert read_object_content("seg_full") == [b"\xca\xfe\xba\xbe"]

    def test_02_first_segment(self):
        """用例02：仅写入第一段非 EOF OBJECT 数据。"""
        session = object_get_session()
        object_create_table("CREATE TABLE seg_first(device STRING TAG, obj_col OBJECT FIELD)")

        tablet = Tablet(
            "seg_first",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, False, 0, b"\xca\xfe")
        session.insert(tablet)

        display = read_object_display("seg_first")
        assert len(display) == 1
        assert_object_display(display[0], expect_null=True)

        rows = fetch_query_rows("SELECT READ_OBJECT(obj_col) FROM seg_first", value_getter="object")
        assert len(rows) == 1
        assert rows[0][0] in (None, b"", "")

    def test_03_segmented_write_complete(self):
        """用例03：通过多段合法片段完成 OBJECT 写入。"""
        session = object_get_session()
        object_create_table("CREATE TABLE seg_done(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO seg_done(time, device, obj_col) VALUES(1, 'd1', to_object(false, 0, X'696F'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO seg_done(time, device, obj_col) VALUES(1, 'd1', to_object(false, 2, X'7464'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO seg_done(time, device, obj_col) VALUES(1, 'd1', to_object(true, 4, X'62'))"
        )

        display = read_object_display("seg_done")
        assert len(display) == 1
        assert_object_display(display[0])
        assert read_object_content("seg_done") == [b"iotdb"]

    def test_04_segmented_write_offset_gap(self):
        """用例04：分段 offset 不连续时应报错。"""
        session = object_get_session()
        object_create_table("CREATE TABLE seg_gap(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO seg_gap(time, device, obj_col) VALUES(1, 'd1', to_object(false, 0, X'696F'))"
        )

        with pytest.raises(Exception):
            session.execute_non_query_statement(
                "INSERT INTO seg_gap(time, device, obj_col) VALUES(1, 'd1', to_object(true, 4, X'62'))"
            )

    def test_05_segmented_write_offset_zero_resets(self):
        """用例05：新片段 offset 为 0 时应重置之前内容。"""
        session = object_get_session()
        object_create_table("CREATE TABLE seg_reset(device STRING TAG, obj_col OBJECT FIELD)")

        session.execute_non_query_statement(
            "INSERT INTO seg_reset(time, device, obj_col) VALUES(1, 'd1', to_object(false, 0, X'696F'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO seg_reset(time, device, obj_col) VALUES(1, 'd1', to_object(true, 0, X'62'))"
        )

        display = read_object_display("seg_reset")
        assert len(display) == 1
        assert_object_display(display[0])
        assert read_object_content("seg_reset") == [b"b"]


# ============================================================================
# 06. Payload 大小测试
# ============================================================================


class TestPayloadSizes(ObjectSessionTestBase):
    """不同大小的 OBJECT 内容测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def write_and_verify(self, table_name, payload):
        session = object_get_session()
        object_create_table(f"CREATE TABLE {table_name}(device STRING TAG, obj_col OBJECT FIELD)")

        tablet = Tablet(
            table_name,
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, payload)
        session.insert(tablet)

        assert read_object_content(table_name) == [payload]

    def test_01_bytes(self):
        """用例01：写入 8 字节 payload。"""
        self.write_and_verify("size_8b", b"\x01\x02\x03\x04\x05\x06\x07\x08")

    def test_02_kb(self):
        """用例02：写入 1KB payload。"""
        self.write_and_verify("size_1kb", b"x" * 1024)

    def test_03_10kb(self):
        """用例03：写入 10KB payload。"""
        self.write_and_verify("size_10kb", b"x" * 10240)

    def test_04_100kb(self):
        """用例04：写入 100KB payload。"""
        self.write_and_verify("size_100kb", b"x" * 102400)

    def test_05_mb(self):
        """用例05：写入 1MB payload。"""
        self.write_and_verify("size_1mb", b"x" * (1024 * 1024))


# ============================================================================
# 07. 查询测试
# ============================================================================


class TestQueryMethods(ObjectSessionTestBase):
    """OBJECT 查询测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def test_01_read_object(self):
        """用例01：通过 READ_OBJECT 查询 OBJECT 值。"""
        session = object_get_session()
        object_create_table("CREATE TABLE q_read(device STRING TAG, obj_col OBJECT FIELD)")

        payload = b"\xca\xfe\xba\xbe\xde\xad\xbe\xef"
        tablet = Tablet(
            "q_read",
            ["device", "obj_col"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 1, True, 0, payload)
        session.insert(tablet)

        assert read_object_content("q_read") == [payload]

    def test_02_mixed_query(self):
        """用例02：普通列与 READ_OBJECT 混合查询。"""
        session = object_get_session()
        object_create_table("CREATE TABLE q_mixed(device STRING TAG, i INT32 FIELD, obj OBJECT FIELD)")

        payload = b"test"
        tablet = Tablet(
            "q_mixed",
            ["device", "i", "obj"],
            [TSDataType.STRING, TSDataType.INT32, TSDataType.OBJECT],
            [["d1", 100, None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD, ColumnType.FIELD],
        )
        tablet.add_value_object(0, 2, True, 0, payload)
        session.insert(tablet)

        with session.execute_query_statement("SELECT i, READ_OBJECT(obj) FROM q_mixed") as result_set:
            row = result_set.next()
            fields = row.get_fields()
            assert fields[0].get_int_value() == 100
            assert fields[1].get_binary_value() == payload


# ============================================================================
# 08. OBJECT 函数测试
# ============================================================================


class TestObjectFunctions(ObjectSessionTestBase):
    """OBJECT 相关函数测试。"""

    def setup_method(self, method):
        object_cleanup_tables()

    def teardown_method(self, method):
        object_cleanup_tables()

    def prepare_function_table(self):
        session = object_get_session()
        object_create_table(
            "CREATE TABLE func_obj(device STRING TAG, obj_col OBJECT FIELD, obj_col2 OBJECT FIELD)"
        )
        session.execute_non_query_statement(
            "INSERT INTO func_obj(time, device, obj_col, obj_col2) "
            "VALUES(1, 'd1', to_object(true, 0, X'0102030405'), null)"
        )
        session.execute_non_query_statement(
            "INSERT INTO func_obj(time, device, obj_col, obj_col2) "
            "VALUES(2, 'd1', null, to_object(true, 0, X'AA'))"
        )
        session.execute_non_query_statement(
            "INSERT INTO func_obj(time, device, obj_col, obj_col2) "
            "VALUES(3, 'd1', to_object(true, 0, X''), to_object(true, 0, X'BBCC'))"
        )

    def test_01_read_object_default(self):
        """用例01：默认读取完整 OBJECT 内容。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT READ_OBJECT(obj_col) FROM func_obj WHERE time = 1",
            "binary",
        ) == [[b"\x01\x02\x03\x04\x05"]]

    def test_02_read_object_with_offset_and_length(self):
        """用例02：按 offset 和 length 读取 OBJECT 片段。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT READ_OBJECT(obj_col, 1, 3) FROM func_obj WHERE time = 1",
            "binary",
        ) == [[b"\x02\x03\x04"]]

    def test_03_read_object_length_larger_than_remaining(self):
        """用例03：length 大于剩余长度时读取剩余内容。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT READ_OBJECT(obj_col, 3, 100) FROM func_obj WHERE time = 1",
            "binary",
        ) == [[b"\x04\x05"]]

    def test_04_read_object_negative_length_reads_remaining(self):
        """用例04：length 为负时读取剩余内容。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT READ_OBJECT(obj_col, 2, -1) FROM func_obj WHERE time = 1",
            "binary",
        ) == [[b"\x03\x04\x05"]]

    def test_05_read_object_negative_offset_fails(self):
        """用例05：offset 为负时应报错。"""
        self.prepare_function_table()
        assert_query_fails(
            "SELECT READ_OBJECT(obj_col, -1, 1) FROM func_obj WHERE time = 1",
            expected_message_parts=["offset"],
        )

    def test_06_read_object_offset_equal_to_size_fails(self):
        """用例06：offset 等于对象长度时应报错。"""
        self.prepare_function_table()
        assert_query_fails(
            "SELECT READ_OBJECT(obj_col, 5, 1) FROM func_obj WHERE time = 1",
            expected_message_parts=["offset"],
        )

    def test_07_read_object_zero_byte_object_fails(self):
        """用例07：读取 0 字节 OBJECT 时应报错。"""
        self.prepare_function_table()
        assert_query_fails(
            "SELECT READ_OBJECT(obj_col) FROM func_obj WHERE time = 3",
            expected_message_parts=["offset", "object size 0"],
        )

    def test_08_length_function(self):
        """用例08：正常 OBJECT 行的 LENGTH 结果校验。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT LENGTH(obj_col), LENGTH(obj_col2) FROM func_obj WHERE time = 1",
            "object",
        ) == [[5, None]]

    def test_09_length_for_zero_byte_object(self):
        """用例09：0 字节 OBJECT 行的 LENGTH 结果校验。"""
        self.prepare_function_table()
        rows = fetch_query_rows(
            "SELECT LENGTH(obj_col), LENGTH(obj_col2) FROM func_obj WHERE time = 3",
            "object",
        )
        assert rows[0][0] == 0
        assert rows[0][1] == 2

    def test_10_cast_object_as_string(self):
        """用例10：将 OBJECT 转为 STRING。"""
        self.prepare_function_table()
        rows = fetch_query_rows("SELECT CAST(obj_col AS STRING) FROM func_obj WHERE time = 1")
        assert len(rows) == 1
        assert rows[0][0] is not None

    def test_11_try_cast_object_as_string(self):
        """用例11：尝试将 OBJECT 转为 STRING。"""
        self.prepare_function_table()
        rows = fetch_query_rows("SELECT TRY_CAST(obj_col AS STRING) FROM func_obj WHERE time = 1")
        assert len(rows) == 1
        assert rows[0][0] is not None

    def test_12_coalesce_object(self):
        """用例12：OBJECT 列使用 COALESCE。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT READ_OBJECT(coalesce(obj_col, obj_col2)) FROM func_obj WHERE time = 2",
            "binary",
        ) == [[b"\xAA"]]

    def test_13_is_null_and_is_not_null(self):
        """用例13：OBJECT 列的 IS NULL / IS NOT NULL 判断。"""
        self.prepare_function_table()
        assert fetch_query_rows(
            "SELECT COUNT(*) FROM func_obj WHERE obj_col IS NULL",
            "object",
        ) == [[1]]
        assert fetch_query_rows(
            "SELECT COUNT(*) FROM func_obj WHERE obj_col IS NOT NULL",
            "object",
        ) == [[2]]


# ============================================================================
# 09. 错误处理测试
# ============================================================================


class TestErrorHandling:
    """Tablet 写入 OBJECT 的错误处理测试。"""

    def test_01_wrong_column_type(self):
        """用例01：向非 OBJECT 列写入 OBJECT 时应报错。"""
        tablet = Tablet("t", ["id", "str"], [TSDataType.STRING, TSDataType.STRING], [["x", "y"]], [1])
        with pytest.raises(TypeError):
            tablet.add_value_object(0, 1, True, 0, b"data")

    def test_02_row_index_out_of_range(self):
        """用例02：行索引越界时应报错。"""
        tablet = Tablet(
            "t",
            ["device", "obj"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        with pytest.raises(IndexError):
            tablet.add_value_object(10, 1, True, 0, b"data")

    def test_03_column_name_not_found(self):
        """用例03：列名不存在时应报错。"""
        tablet = Tablet(
            "t",
            ["device", "obj"],
            [TSDataType.STRING, TSDataType.OBJECT],
            [["d1", None]],
            [1],
            [ColumnType.TAG, ColumnType.FIELD],
        )
        with pytest.raises(KeyError):
            tablet.add_value_object_by_name("nonexistent", 0, True, 0, b"data")


# ============================================================================
# 10. OBJECT 类型约束与默认限制测试
# ============================================================================


def test_object_column_category_cases(merged_object_case_session):
    """用例01：OBJECT 只允许作为 FIELD，不允许作为 TAG 或 ATTRIBUTE。"""
    session = merged_object_case_session
    session.execute_non_query_statement(f"USE {OBJECT_CATEGORY_DATABASE}")
    session.execute_non_query_statement(
        "CREATE TABLE single_field(device STRING TAG, obj_col OBJECT FIELD)"
    )
    session.execute_non_query_statement(
        "INSERT INTO single_field(time, device, obj_col) VALUES(1, 'd1', to_object(false, 0, X'01'))"
    )
    session.execute_non_query_statement(
        "CREATE TABLE multi_field(device STRING TAG, obj1 OBJECT FIELD, obj2 OBJECT FIELD)"
    )
    session.execute_non_query_statement(
        "INSERT INTO multi_field(time, device, obj1, obj2) "
        "VALUES(1, 'd1', to_object(false, 0, X'01'), to_object(false, 0, X'0203'))"
    )

    with pytest.raises(Exception):
        session.execute_non_query_statement(
            "CREATE TABLE object_tag(obj_col OBJECT TAG, s STRING FIELD)"
        )

    with pytest.raises(Exception):
        session.execute_non_query_statement(
            "CREATE TABLE object_attr(device STRING TAG, obj_col OBJECT ATTRIBUTE, s STRING FIELD)"
        )


def test_object_restrict_limit_false_cases(merged_object_case_session):
    """用例02：默认 false 限制下，特殊命名场景应正常通过。"""
    session = merged_object_case_session
    session.execute_non_query_statement(f"USE {OBJECT_RESTRICT_DATABASE}")

    table_cases = ["tbl_ok_basic", "tbl.dot", "tbl..dot", "tbl./slash", r"tbl.\backslash"]
    field_cases = ["obj_col", "obj.col", "obj..col", "obj./col", r"obj.\col"]
    device_cases = ["d1", ".", "..", "a./b", r"a.\b"]

    for table_name in table_cases:
        session.execute_non_query_statement(
            f"CREATE TABLE {quote_identifier(table_name)}("
            f"{quote_identifier('device')} STRING TAG, "
            f"{quote_identifier('obj_col')} OBJECT FIELD)"
        )

    for index, field_name in enumerate(field_cases, start=1):
        session.execute_non_query_statement(
            f"CREATE TABLE {quote_identifier(f'tbl_field_case_{index}')}("
            f"{quote_identifier('device')} STRING TAG, "
            f"{quote_identifier(field_name)} OBJECT FIELD)"
        )

    for index, device_name in enumerate(device_cases, start=1):
        table_name = f"tbl_device_case_{index}"
        session.execute_non_query_statement(
            f"CREATE TABLE {quote_identifier(table_name)}("
            f"{quote_identifier('device')} STRING TAG, "
            f"{quote_identifier('obj_col')} OBJECT FIELD)"
        )
        session.execute_non_query_statement(
            f"INSERT INTO {quote_identifier(table_name)}(time, {quote_identifier('device')}, {quote_identifier('obj_col')}) "
            f"VALUES(1, '{device_name}', to_object(false, 0, X'01'))"
        )
