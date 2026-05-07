# Python 原生接口测试工具使用说明

本仓库用于验证 Apache IoTDB Python native API

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
│  └─ config.yml                   # IoTDB 连接配置，包含单机/集群、账号、SSL、压缩、超时等参数
├─ example/                        # Python native API 示例代码
│  ├─ table/                       # 表模型示例
│  └─ tree/                        # 树模型示例
├─ tests/                          # pytest 测试目录
│  ├─ table/                       # 表模型测试用例，覆盖 TableSession、TableSessionPool、写入、查询等场景
│  ├─ tree/                        # 树模型测试用例，覆盖 Session、SessionPool、数据库、写入、查询、时间序列等场景
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

### 3. 安装 Apache IoTDB Python 客户端依赖

如果你已经有可用的 `apache-iotdb` wheel，直接安装即可：

```bash
python -m pip install /path/to/apache_iotdb-*.whl
```

没有的话需要从 IoTDB 源码构建：

```bash
git clone https://github.com/apache/iotdb.git
cd iotdb/iotdb-client/client-py
python -m pip install build
./release.sh # 仅支持在Linux/MacOS环境运行，若是需要在Windows环境运行，请自行在支持的环境编译后，再放到Windows环境安装
cd <python-native-api-testcase>
python -m pip install /path/to/apache_iotdb-*.whl
```

> 如需替换已有版本，可先执行 `python -m pip uninstall apache-iotdb` 卸载旧版本后，再重新安装

## 配置说明

测试默认读取的配置文件为：[`conf/config.yml`](conf/config.yml)。

当前配置项说明如下：

| 配置项 | 说明 |
| --- | --- |
| `enable_cluster` | 是否按集群模式连接 |
| `enable_session_pool` | 是否在部分测试中使用 `SessionPool` 分支 |
| `host` | 单机模式主机地址 |
| `port` | 单机模式端口 |
| `username` | 用户名，默认 `root` |
| `password` | 密码，默认 `root` |
| `node_urls` | 集群模式节点列表，格式如 `127.0.0.1:6667` |
| `use_ssl` | 是否启用 SSL 连接 |
| `ca_certs` | SSL 证书路径 |
| `enable_compression` | 是否启用 RPC 压缩 |
| `connection_timeout_in_ms` | 连接超时时间，单位毫秒 |

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
# 按文件执行
pytest tree/test_treemodel_session.py
pytest table/test_tablemodel_session.py
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
