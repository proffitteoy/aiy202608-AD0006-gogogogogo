# 第三方软件与许可证

本文汇总 RiskTrace 仓库中直接复制、裁剪或以本地路径引用的第三方开源内容。它用于帮助分发者定位原始许可证与 NOTICE，不替代各组件目录内的法律文本。

## 仓库内保留的第三方内容

| 组件 | 仓库中的版本/快照 | 上游项目 | 许可证 | 本地许可证与 NOTICE | 在 RiskTrace 中的边界 |
| --- | --- | --- | --- | --- | --- |
| Apache ECharts | 6.1.0，包版本标记为 `6.1.0-risktrace-vendored` | [apache/echarts](https://github.com/apache/echarts) | Apache-2.0 | [`LICENSE`](apps/web/vendor/echarts/LICENSE) · [`NOTICE`](apps/web/vendor/echarts/NOTICE) | 保留运行所需 ESM 产物和最小类型声明，用于工作台时间线 |
| React Flow | 12.11.2 | [xyflow/xyflow](https://github.com/xyflow/xyflow) | MIT | [`LICENSE`](apps/web/vendor/xyflow-react/LICENSE) | 本地路径依赖，用于工作台传导图 |
| XYFlow System | 0.0.79 | [xyflow/xyflow](https://github.com/xyflow/xyflow) | MIT | [`LICENSE`](apps/web/vendor/xyflow-system/LICENSE) | React Flow 的本地系统依赖 |
| Sentence Transformers | 5.7.0.dev0 | [huggingface/sentence-transformers](https://github.com/huggingface/sentence-transformers) | Apache-2.0 | [`LICENSE`](apps/api/vendor/sentence-transformers/LICENSE) · [`NOTICE`](apps/api/vendor/sentence-transformers/NOTICE.txt) | 可选 embedding 依赖；默认 API 安装不启用，仓库不包含模型权重 |
| pgvector | 0.8.6 | [pgvector/pgvector](https://github.com/pgvector/pgvector) | PostgreSQL License | [`LICENSE`](infra/pgvector/LICENSE) | 以本地源码构建 PostgreSQL 扩展镜像 |

## RiskTrace 所做的包装或裁剪

- ECharts 的本地包清单只暴露仓库实际使用的 ESM 构建产物，并保留上游 `LICENSE` 与 `NOTICE`。
- React Flow 与 XYFlow System 通过本地包清单接入 Next.js；上游版权声明与 MIT 文本保留在各目录。
- Sentence Transformers 作为 `embeddings` extra 的本地路径源；RiskTrace 的惰性适配器不修改上游许可，也不附带或重新分发模型权重。
- pgvector 的 Dockerfile 从当前目录构建源码，不在构建时远程拉取另一份源码快照。

上述包装、类型声明和 RiskTrace 自写适配代码在可分离范围内适用根目录 [MIT License](LICENSE)；第三方源码、构建产物、版权声明与 NOTICE 继续适用上表对应许可证。

## 包管理器依赖与运行时镜像

`apps/api/uv.lock`、`apps/web/package-lock.json` 与根 `package-lock.json` 记录包管理器解析结果，但锁文件不是许可证文本。通过 PyPI/npm 安装的其他依赖，以及 `compose.yaml` 引用的 PostgreSQL、Redis、MinIO 等镜像，仍分别受其发行包或镜像内所附许可证约束；本仓库没有用根目录 MIT License 对它们重新授权。

## 分发检查

发布源码、容器镜像或二进制包前，应至少确认：

1. 上表中的 `LICENSE` 与 `NOTICE` 仍随对应第三方内容分发。
2. 裁剪或升级组件后，同步更新版本、上游链接和本地许可证路径。
3. 新增本地源码快照前，记录来源版本、许可证、NOTICE 要求与实际运行用途。
4. 模型权重和数据集单独核对许可，不因使用 Sentence Transformers 代码而自动获得模型或数据的分发权。
