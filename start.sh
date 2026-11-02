#!/bin/sh
# ============================================================================
# python-native-api-testcase-enterprise 的 PLM 统一入口
#
# 测试框架：pytest
# PLM 调用：sh start.sh case '<CASE_ID>'   （cwd = 仓库根）
# 产物：$PLM_REPORT_DIR/case-<ID>.xml（JUnit XML，每个 testcase 带 case_id）
#
# 数据库连接通过环境变量覆盖（不设置时沿用 conf/config.yml）：
#   IOTDB_HOST / IOTDB_PORT / IOTDB_USER / IOTDB_PASSWORD / IOTDB_IS_CLUSTER
# PLM 执行时必须提供 IOTDB_HOST/IOTDB_PORT（K8s 实例返回的连接地址）。
# ============================================================================
set -u

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
cd "$REPO_ROOT" || exit 1

REPORTS_DIR="${PLM_REPORT_DIR:-reports}"
AUTOMATION_TYPE="${PLM_AUTOMATION_TYPE:-session-python}"
VENV="$REPO_ROOT/.venv"
PYTHON="${PYTHON:-$VENV/bin/python}"
PYTHON_CLIENT="${PLM_IOTDB_PYTHON_CLIENT:-/root/test-program/timechodb-src/iotdb-client/client-py}"

usage() {
    cat >&2 <<'EOF'
Usage: sh start.sh <command> [target]
  prepare              创建虚拟环境并安装测试依赖
  list-cases --json    输出用例清单 JSON（stdout 仅 JSON）
  case <case-id>       执行单条用例
  cases <id1,id2>      批量执行（兼容保留；PLM 只逐条派发）
  help                 帮助
EOF
}

safe_name() {
    printf '%s' "$1" | tr '/' '_'
}

ensure_venv() {
    if [ ! -x "$VENV/bin/python" ]; then
        python3 -m venv "$VENV" || return 1
    fi
    if [ ! -x "$PYTHON" ]; then
        PYTHON="$VENV/bin/python"
    fi
}

install_client() {
    if "$PYTHON" -c "import iotdb" >/dev/null 2>&1; then
        return 0
    fi
    if [ -d "$PYTHON_CLIENT" ]; then
        if [ -f "$PYTHON_CLIENT/pyproject.toml" ] || [ -f "$PYTHON_CLIENT/setup.py" ]; then
            "$PYTHON" -m pip install -q "$PYTHON_CLIENT" || return 1
        else
            tmp=$(mktemp -d) || return 1
            cp -R "$PYTHON_CLIENT/." "$tmp/" || { rm -rf "$tmp"; return 1; }
            if [ -f "$tmp/resources/pyproject.toml" ]; then
                cp "$tmp/resources/pyproject.toml" "$tmp/pyproject.toml" || { rm -rf "$tmp"; return 1; }
                sed -i 's/${iotdb_version}/2.0.11.dev0/' "$tmp/pyproject.toml" 2>/dev/null || true
            fi
            "$PYTHON" -m pip install -q "$tmp" || { rm -rf "$tmp"; return 1; }
            rm -rf "$tmp"
        fi
    else
        "$PYTHON" -m pip install -q apache-iotdb || return 1
    fi
}

prepare() {
    ensure_venv || return 1
    "$PYTHON" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
    "$PYTHON" -m pip install -q -r requirements-dev.txt || return 1
    install_client || return 1
    "$PYTHON" -c "import pytest, yaml, iotdb" || return 1
}

require_plm_iotdb_endpoint() {
    if [ -n "${PLM_AUTOMATION_TYPE:-}" ]; then
        if [ -z "${IOTDB_HOST:-}" ] || [ -z "${IOTDB_PORT:-}" ]; then
            echo "[plm] PLM 执行必须提供 K8s 实例连接地址 IOTDB_HOST/IOTDB_PORT" >&2
            return 2
        fi
    fi
    return 0
}

list_cases() {
    ensure_venv || return 1
    "$PYTHON" scripts/plm/plm_cases.py list --automation-type "$AUTOMATION_TYPE"
}

case_one() {
    [ -z "${1:-}" ] && { usage; return 2; }
    require_plm_iotdb_endpoint || return 2
    ensure_venv || return 1
    target=$( "$PYTHON" scripts/plm/plm_cases.py lookup "$1" ) || return 5

    case "$REPORTS_DIR" in
        /*) : ;;
        *) REPORTS_DIR="$REPO_ROOT/$REPORTS_DIR" ;;
    esac
    mkdir -p "$REPORTS_DIR"
    final="$REPORTS_DIR/case-$(safe_name "$1").xml"
    raw="$REPORTS_DIR/.pytest-$(safe_name "$1").xml"
    rm -f -- "$final" "$raw"

    # 测试代码的 config 路径相对 tests 目录，必须在 tests 下执行。
    cd "$REPO_ROOT/tests" || return 1
    "$PYTHON" -m pytest -q "$target" --junitxml="$raw" -p no:cacheprovider
    rc=$?
    cd "$REPO_ROOT" || return 1

    if ! "$PYTHON" scripts/plm/plm_cases.py junit-post "$raw" "$final" "$1"; then
        rm -f -- "$raw" "$final"
        return 1
    fi
    rm -f -- "$raw"
    return $rc
}

cases_batch() {
    [ -z "${1:-}" ] && { usage; return 2; }
    ok=0
    old_ifs=$IFS
    IFS=','
    for raw in $1; do
        id=$(printf '%s' "$raw" | tr -d '[:space:]')
        [ -z "$id" ] && continue
        case_one "$id" || ok=1
    done
    IFS=$old_ifs
    return $ok
}

command="${1:-help}"
target="${2:-}"
case "$command" in
    prepare) prepare ;;
    list-cases)
        [ "$target" = "--json" ] || { usage; exit 2; }
        list_cases
        ;;
    case) case_one "$target" ;;
    cases) cases_batch "$target" ;;
    help|-h|--help) usage ;;
    *) usage; exit 2 ;;
esac
