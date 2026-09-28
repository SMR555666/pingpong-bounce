# PingPong Bounce Detection

乒乓球多视角落点检测比赛项目。输入比赛视频，输出每次触台的帧号和画面像素坐标。默认开发乒乓球主赛题，篮球附加题保留官方参考实现。

**当前状态：仓库骨架。尚未导入官方 `participant.zip`，未实现新模型，未进行真实视频推理或计分。** 本项目不猜测官方 `Solution` 方法签名，导入后以官方示例为准。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `participant/` | 导入后生成的完整官方工程，保留原目录结构 |
| `participant/pingpang/participant/solution.py` | 乒乓球算法入口，使用官方 `Solution` 接口 |
| `participant/pingpang/participant/configs/` | 模型和推理配置 |
| `participant/pingpang/participant/weights/` | 本地模型权重，不提交 Git |
| `participant/basketball/participant/` | 篮球官方基线；暂不改动 |
| `tools/project.py` | 导入、框架字节校验和联合自测 |
| `docs/competition.md` | 提供的赛题原文 |
| `docs/framework-sha256.json` | 首次导入时自动生成的框架文件哈希，随代码提交 |
| `Dockerfile` | 基于官方镜像构建提交镜像 |

结构参考 [EventVAD](https://github.com/YihuaJerry/EventVAD) 的简洁项目组织方式；未复制其代码、模型或依赖。赛题工程使用 `participant/`，不额外创建重复的 `src/` 算法入口。

## 1. 导入官方示例

在仓库根目录执行，辅助脚本只需要 Python 3.10 标准库：

```bash
python tools/project.py import /path/to/participant.zip
python tools/project.py check
```

ZIP 必须包含赛题描述的外层 `participant/`，同时包含两个任务。导入保留官方文件内容和参考实现，拒绝覆盖已有工程。该命令会解压验证视频，请预留空间。

导入后的修改范围：各任务内层的 `solution.py`、`weights/`、`configs/`。不要修改 `core/`、`run.py`、`validate.py`、联合入口或官方自检脚本。`check` 仅对首次导入版本做本地字节校验，不证明包来源，也不替代组委会完整性检查。不要为了让校验通过而重建或修改哈希记录。

## 2. 环境和数据

优先使用平台指定镜像 `pytorch 2.1.2-ubuntu22.04-p3.10-cuda11.8`，或组委会 `sport-base_v1.tar`。不要在已有官方环境中升级或替换 torch、numpy、onnxruntime、TensorRT。平台首次安装命令见 [赛题原文](docs/competition.md)，本仓库不提供自动升级依赖的安装脚本。

- 训练集：下载 `pp_train_data.zip`，在本地 `data/` 下管理；实际标注格式在取得数据后确认。
- 验证集：导入工程后位于两个任务各自的 `public_data/`。
- 权重：放到对应任务内层的 `weights/`，并在 `configs/` 中记录相对路径。
- 数据、视频、模型权重、推理输出和镜像均已加入 Git 忽略规则；Docker 构建会包含本地权重。
- 在另一台机器克隆后，需从官方包恢复 `public_data/` 并另行恢复权重；已有工程不要重复运行 import。

## 3. 开发和自测

先阅读官方 `solution.py` 与自检脚本，按真实接口开发。若只做乒乓球，篮球代码原样保留。

在 Linux / 官方容器环境执行：

```bash
python tools/project.py check
python tools/project.py run --output outputs/baseline
```

`run` 创建 `participant/input/pingpang` 与 `basketball` 的验证集软链接，执行原始 `run_all.sh`。输出目录非空时拒绝覆盖；下一次实验指定新目录。具体输出子目录由官方入口决定，每个任务应有 `predictions.jsonl`、`run_status.json`、`run.log`。失败时查看日志和官方脚本说明。

取得官方包后，还应根据其帮助说明执行 `check_env.py`、`check_solution.py`；此处不假定它们的所在位置或参数。

乒乓球预测格式（由官方框架负责最终输出）：

```json
{"video_id":"v000001","frame_id":123,"x":960.0,"y":540.0}
```

注意：帧号 0 基，坐标为原始画面像素且必须是 float。训练集以 720p 为主，评测全为 1080p；缩放、裁剪或 letterbox 后必须还原坐标。不能越界，不能通过直接缩放帧号替代时序对齐。

精度按三个视角分别计算 F1（容差 ±1 帧、50 px），精度占 75 分、速度占 25 分。先记录官方基线，再比较算法改动；不要把仓库骨架的检查结果当成比赛分数。

## 4. 构建提交镜像

以下命令中的 `OFFICIAL_IMAGE_NAME:TAG` 必须替换为 `docker load` 输出的实际镜像名。

```bash
docker load -i /path/to/sport-base_v1.tar
python tools/project.py check
docker build --build-arg BASE_IMAGE=OFFICIAL_IMAGE_NAME:TAG -t sport-vision-submit:latest .
```

Dockerfile 不安装或升级基础组件。正式评测没有在线安装环节；如方案新增其他依赖，需提前审核兼容性并打入镜像。验证数据不进入镜像。构建前确认本地模型权重齐全。

可使用验证集模拟挂载（先运行第 3 节建立输入链接；将两个数据目录分别挂载，避免容器内软链接失效）：

```bash
mkdir -p outputs/docker-public
docker run --rm --gpus all \
  -v "$PWD/participant/pingpang/public_data:/participant/input/pingpang:ro" \
  -v "$PWD/participant/basketball/public_data:/participant/input/basketball:ro" \
  -v "$PWD/outputs/docker-public:/participant/output" \
  sport-vision-submit:latest /participant/input /participant/output

docker save sport-vision-submit:latest -o sport-vision-submit.tar
```

赛题限制：最多两张 4090、单卡显存 <24 GB、每任务全程 <7200 秒、新增镜像空间 <50 GB、输出 <1 GB。正式提交前仍需在官方环境完整跑通两任务。

## 5. 团队协作

仓库：`SMR555666/pingpong-bounce`（私有）。

```bash
git clone https://github.com/SMR555666/pingpong-bounce.git
cd pingpong-bounce
git switch -c baseline
```

导入官方包后，提交代码与框架校验记录；数据、模型权重和输出在本地管理。提交前用 `git status --short` 检查暂存区。后续按功能建立实验分支，通过 Pull Request 合并。本项目没有为官方代码擅自添加开源许可证。

## 接下来

1. 提供并导入官方 `participant.zip`，确认实际 `Solution` 接口和运行依赖。
2. 在官方环境跑通原始基线，记录各视角 F1 和 FPS。
3. 仅在参赛代码区迭代球检测、轨迹与触台事件判断；训练流程等取得标注样例后再添加。
