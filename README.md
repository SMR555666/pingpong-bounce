# PingPong Bounce Detection

乒乓球多视角落点检测比赛项目。输入比赛视频，输出每次触台的帧号和画面像素坐标。默认开发乒乓球主赛题，篮球附加题保留官方参考实现。

**当前状态：已导入官方 `participant.zip` 和参考实现，尚未训练新模型或在 GPU 环境跑完整验证。** 官方 `Solution` 实现四个生命周期方法：`prepare`、`reset`、`process_frame`、`finish_video`。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `participant/` | 官方工程；框架、示例代码、官方参考权重和公开验证集均已入库 |
| `participant/pingpang/participant/solution.py` | 乒乓球算法入口，使用官方 `Solution` 接口 |
| `participant/pingpang/participant/configs/` | 模型和推理配置 |
| `participant/pingpang/participant/weights/` | 已包含官方参考权重 `ball.onnx` |
| `participant/basketball/participant/` | 篮球官方基线；暂不改动 |
| `tools/project.py` | 导入与框架字节校验 |
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

ZIP 支持单层 `participant/`，也支持本次官方包的双层 `participant/participant/` 包装。导入保留官方文件内容和参考实现，拒绝覆盖已有工程。已导入的仓库无需再次运行此命令。

算法修改放在各任务内层 `participant/` 代码区；优先改 `solution.py`，模型和配置放 `weights/`、`configs/`。不要修改 `core/`、`run.py`、`validate.py`、联合入口或官方自检脚本。`check` 仅对首次导入版本做本地字节校验，不证明包来源，也不替代组委会完整性检查。不要为了让校验通过而重建或修改哈希记录。

## 2. 环境和数据

优先使用平台指定镜像 `pytorch 2.1.2-ubuntu22.04-p3.10-cuda11.8`，或组委会 `sport-base_v1.tar`。不要在已有官方环境中升级或替换 torch、numpy、onnxruntime、TensorRT。平台首次安装命令见 [赛题原文](docs/competition.md)，本仓库不提供自动升级依赖的安装脚本。

- 训练集：下载 `pp_train_data.zip`，在本地 `data/` 下管理；实际标注格式在取得数据后确认。
- 验证集：导入工程后位于两个任务各自的 `public_data/`。
- 官方参考权重：`ball.onnx`、`player.onnx` 已包含在对应任务内层的 `participant/weights/`，克隆本私有仓库即可获取。
- 公开验证集：两个任务的 `participant/<task>/public_data/` 均已入库，包含 manifest、GT 和共 17 个视频。训练数据、新增训练权重、推理输出与镜像仍不入 Git。

## 3. 开发和自测

官方基线已包含球检测、落点判定及篮球跟踪的代码。`pingpang/participant/solution.py` 的四个方法按官方 `core/types.py` 接口实现。`ball.onnx` 在 `prepare` 中转换为 TensorRT 引擎。可先看 `participant/README.md` 和两个任务的 `scripts/check_solution.py`。

静态校验（普通 Python 环境即可）：

```bash
python tools/project.py check
python participant/pingpang/integrity.py --verify
python participant/basketball/integrity.py --verify
```

完整推理须在官方 GPU 环境进行。仓库已包含官方包的两个权重和两套 `public_data/`；确保文件下载完整，工程映射到容器内 `/participant`，并挂载验证数据到 `/participant/input/<task>`。参考命令见下一节。平台里直接调用 `/participant/run_all.sh /participant/input /participant/output`。

快速自检入口位于 `participant/<task>/scripts/check_env.py` 和 `check_solution.py`，具体参数参看 `--help`。输出的 `run.log` 与 `run_status.json` 应同时检查。**这里的字节校验通过只说明框架文件没有改变，不代表模型已跑通。**

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

可使用验证集模拟挂载（克隆仓库后即可使用）：

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
```

代码、框架校验记录、两个官方 ONNX 权重和两套公开验证集均已入库。提交前运行 `git status --short`，检查暂存区。后续按功能建立实验分支并通过 Pull Request 合并。本项目没有为官方代码添加开源许可证。

## 接下来

1. 使用仓库自带的两个模型权重和公开验证集，在官方 GPU 环境跑通原始基线，记录各视角 F1 和 FPS。
2. 在参赛代码区迭代球检测、轨迹与触台事件判断；训练流程取得训练集标注后再添加。
