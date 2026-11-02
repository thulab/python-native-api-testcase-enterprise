"""PLM 执行适配：用平台注入的 K8s 实例地址覆盖 conf/config.yml。

测试代码统一通过 ``yaml.safe_load`` 读取 ``../conf/config.yml``；这里在 pytest
加载测试模块前包一层，避免逐个修改测试文件。PLM 执行（存在
``PLM_AUTOMATION_TYPE``）时缺少 IOTDB_HOST/IOTDB_PORT 直接失败，不回落
到 127.0.0.1。本地手工运行不设置这些环境变量时行为不变。
"""

import os
import sys

import yaml

_original_safe_load = yaml.safe_load
_printed_endpoint = False


def _env(name):
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _apply_plm_overrides(config):
    global _printed_endpoint

    plm_type = _env("PLM_AUTOMATION_TYPE")
    host = _env("IOTDB_HOST")
    port = _env("IOTDB_PORT")
    if plm_type is not None and (host is None or port is None):
        raise RuntimeError(
            "PLM 执行必须提供 K8s 实例连接地址 IOTDB_HOST/IOTDB_PORT"
            f"（当前 host={host or '<未设置>'}, port={port or '<未设置>'}），"
            "不会使用 conf/config.yml 的默认地址"
        )

    if host is not None or port is not None:
        effective_host = host or config.get("host")
        effective_port = port or config.get("port")
        if effective_host and effective_port:
            config["host"] = effective_host
            config["port"] = str(effective_port)
            config["node_urls"] = [f"{effective_host}:{effective_port}"]
            if _env("IOTDB_IS_CLUSTER") is not None:
                config["enable_cluster"] = _env("IOTDB_IS_CLUSTER").lower() == "true"
            else:
                config["enable_cluster"] = False
            if plm_type is not None and not _printed_endpoint:
                print(
                    f"[plm] 使用 K8s 实例地址 {effective_host}:{effective_port}",
                    file=sys.stderr,
                    flush=True,
                )
                _printed_endpoint = True

    user = _env("IOTDB_USER")
    password = _env("IOTDB_PASSWORD")
    if user is not None:
        config["username"] = user
    if password is not None:
        config["password"] = password
    return config


def _safe_load(stream):
    data = _original_safe_load(stream)
    if isinstance(data, dict) and ("host" in data or "node_urls" in data):
        data = _apply_plm_overrides(data)
    return data


yaml.safe_load = _safe_load
