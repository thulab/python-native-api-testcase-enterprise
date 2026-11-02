# Python 原生接口测试工具使用说明

本仓库用于验证 TimechoDB Python native API

## 目录

- [项目说明](#项目说明)
- [环境](#环境)
- [安装](#安装)
- [配置说明](#配置说明)
- [执行测试](#执行测试)
- [条件性测试说明](#条件性测试说明)
- [用例命名约定](#用例命名约定)

## 项目结构

项目中的主要目录和文件如下：

```text
python-native-api-testcase/        # 仓库根目录
├─ assets/                         # README 或其他说明文档使用的图片资源
├─ conf/                           # 测试运行配置目录
│  └─ config.yml                   # TimechoDB 连接配置，包含单机/集群、账号、SSL、压缩、超时等参数
├─ example/                        # 示例代码目录
│  ├─ table/                       # 表模型示例
│  └─ tree/                        # 树模型示例
├─ tests/                          # 测试用例目录
│  ├─ table/                       # 表模型测试用例
│  ├─ tree/                        # 树模型测试用例
│  └─ .coveragerc                  # 覆盖率统计配置文件
├─ README.md                       # 项目使用说明
└─ requirements-dev.txt            # 本仓库测试和报告生成依赖
```

## 环境

- Python 3.11+
- pip3
- thrift 0.13+

> 本测试程序适用于 Ubuntu/MacOS 或者 Windows 操作系统

## 安装

### 1. 创建虚拟环境并激活

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 2. 安装测试依赖

```bash
python -m pip install -r requirements-dev.txt
```

### 3. 安装 Python 客户端依赖

如果你已经有可用的依赖 wheel 包，直接安装即可：

```bash
python -m pip install /path/to/apache_iotdb-*.whl
```

没有的话需要从 TimechoDB 源码构建：

```bash
git clone https://gitlab.timecho.com/r-d/db/timechodb.git
cd timechodb/iotdb-client/client-py
python -m pip install build
./release.sh # 仅支持在Linux/MacOS环境运行，若是需要在Windows环境运行，请自行在支持的环境编译后，再放到Windows环境安装
cd <python-native-api-testcase>
python -m pip install /path/to/apache_iotdb-*.whl
```

> 如需替换已有版本，可先执行 `python -m pip uninstall apache-iotdb` 卸载旧版本后，再重新安装

## 配置说明

测试默认读取的配置文件为：[`conf/config.yml`](conf/config.yml)。

当前配置项说明如下：

| 配置项 | 说明                            |
| --- |-------------------------------|
| `enable_cluster` | 是否按集群模式连接                     |
| `enable_session_pool` | 是否在部分测试中使用 `SessionPool` 分支   |
| `host` | 单机模式主机地址                      |
| `port` | 单机模式端口                        |
| `username` | 用户名，默认 `root`                 |
| `password` | 密码，默认 `TimechoDB@2021`        |
| `node_urls` | 集群模式节点列表，格式如 `127.0.0.1:6667` |
| `use_ssl` | 是否启用 SSL 连接                   |
| `ca_certs` | SSL 证书路径                      |
| `enable_compression` | 是否启用 RPC 压缩                   |
| `connection_timeout_in_ms` | 连接超时时间，单位毫秒                   |

## 使用

### 功能测试

```bash
# 测试代码中的配置文件路径写法是相对 `tests` 目录的，因此请先进入该目录
cd tests
# 全量执行
pytest
# 按测试模型执行
pytest tree
pytest table
# 生成 HTML 测试报告
pytest --html=report.html
pytest --html=../reports/report.html
```

### 覆盖率测试

覆盖率配置文件位于 `tests/.coveragerc`，用于屏蔽部分不需要的文件的覆盖情况：

```bash
# 测试代码中的配置文件路径写法是相对 `tests` 目录的，因此请先进入该目录
cd tests
# 执行覆盖率测试并输出报告
pytest --cov=iotdb --cov-report=html:../cov-report --cov-branch --cov-config=.coveragerc
```

常用参数说明：

- `--cov`：指定覆盖率目标包，这里是已安装到当前 Python 环境中的 `iotdb`
- `--cov-report`：指定报告输出格式和目录
- `--cov-branch`：启用分支覆盖率统计
- `--cov-config`：指定覆盖率配置文件，这里对应 `tests/.coveragerc`

## 开发

如果需要新增 pytest 用例，建议沿用当前仓库的命名方式：

- 测试文件名使用 `test_*.py`
- 测试函数名使用 `test_*`

## PLM 接入（start.sh）

仓库根目录的 `start.sh` 是 TimechoPLM 测试程序统一入口，不改变原有 pytest 用法：

```bash
sh start.sh prepare                 # 创建 .venv、安装 pytest/客户端依赖
sh start.sh list-cases --json       # 用例清单（stdout 仅 JSON）
sh start.sh case <CASE_ID>          # 单条用例，产物写 $PLM_REPORT_DIR
```

- `PLM_AUTOMATION_TYPE`：PLM 绑定的仓库类型（默认 `session-python`）。
- `PLM_REPORT_DIR`：JUnit XML 输出目录（相对仓库根，默认 `reports/`）。
- `IOTDB_HOST` / `IOTDB_PORT`：PLM 执行时由平台按 `k8sInstanceId` 注入 K8s 实例地址；PLM 执行缺少任一项时直接失败，**不会回退到 `conf/config.yml` 的 127.0.0.1**。手工本地运行可不设置。
- `IOTDB_USER` / `IOTDB_PASSWORD`：可选覆盖；PLM 不注入数据库账号/口令，默认使用 `conf/config.yml` 的 `root/TimechoDB@2021`。
- Python 客户端：`start.sh prepare` 优先使用 `PLM_IOTDB_PYTHON_CLIENT`（默认 `/root/test-program/timechodb-src/iotdb-client/client-py`）从 TimechoDB 源码安装；源码缺少 `iotdb/thrift` 时会先执行 `mvn -DskipTests -pl iotdb-client/client-py -am package` 生成。该源码客户端包含企业版 OBJECT 类型。
