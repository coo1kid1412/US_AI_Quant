#!/bin/bash
# ============================================================
# US_AI_Quant HIST模型 - AutoDL GPU训练操作手册
# ============================================================
# 前提: AutoDL实例已创建(RTX 4090, PyTorch 2.0+镜像)
#
# 在AutoDL控制台 → 容器实例 → 你的实例 → 找到:
#   - SSH指令: ssh -p XXXXX root@region-X.autodl.pro
#   - 登录密码: 你设置的密码
#
# 将下面的 <PORT> 替换为你的端口号
# 将下面的 <ADDRESS> 替换为你的地址(如 region-1.autodl.pro)
# ============================================================

# ===================== Step 2: 上传数据 =====================
# 在你的 Mac 终端执行 (不是AutoDL里)
# 上传到 /root/autodl-tmp (数据盘,关机不丢失)

# 2a. 上传US stock数据 (~839MB, 约3-5分钟)
scp -P <PORT> ~/WorkSpace/QoderWorkspace/US_AI_Quant/autodl_package/qlib_us_data_20260504_122202.tar.gz \
    root@<ADDRESS>:/root/autodl-tmp/

# 2b. 上传训练代码包 (~20KB, 秒传)
scp -P <PORT> ~/WorkSpace/QoderWorkspace/US_AI_Quant/autodl_package/hist_us_code_20260504_122202.tar.gz \
    root@<ADDRESS>:/root/autodl-tmp/

# ===================== Step 3: SSH登录 =====================
ssh -p <PORT> root@<ADDRESS>
# 输入你的实例密码

# ============================================================
# ===== 以下所有命令都在 AutoDL 实例内执行 =====
# ============================================================

# ===================== Step 4: 解压和部署 =====================

# 4a. 解压US stock数据到qlib目录
mkdir -p ~/.qlib/qlib_data
tar -xzf /root/autodl-tmp/qlib_us_data_20260504_122202.tar.gz -C ~/.qlib/qlib_data/
# 验证: 应该看到 calendars/ features/ instruments/ 等目录
ls ~/.qlib/qlib_data/us_data/

# 4b. 解压训练代码
tar -xzf /root/autodl-tmp/hist_us_code_20260504_122202.tar.gz -C /root/
# 验证: 应该看到完整的项目结构
ls /root/hist_us_train/

# 4c. 开启学术加速(加速pip下载)
source /etc/network_turbo

# 4d. 安装依赖(PyTorch镜像已预装torch, 只需装qlib)
pip install pyqlib numpy pandas -q

# 4e. 验证环境
python -c "
import torch, qlib, numpy, pandas
print('torch:', torch.__version__)
print('CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    print('显存: %.1f GB' % (torch.cuda.get_device_properties(0).total_memory/1024**3))
print('qlib: OK')
print('numpy:', numpy.__version__)
print('pandas:', pandas.__version__)
"

# ===================== Step 5: 开始训练 =====================
cd /root/hist_us_train

# 方式A: 使用包装脚本(推荐)
python autodl_train_us.py --epochs 100 --early-stop 15 --gpu 0

# 方式B: 直接调用训练脚本
# python scripts/train_hist_us.py --market sp500 --epochs 100 --early-stop 15 --gpu 0 --seed 42

# 训练预计时间: RTX 4090 约25分钟, RTX 3090 约40分钟
# 训练输出在: /root/hist_us_train/results/hist_us/

# ===================== Step 6: 下载结果 =====================
# 训练完成后, 回到你的 Mac 终端执行:

# 6a. 创建本地目录(如不存在)
mkdir -p ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us

# 6b. 下载模型权重
scp -P <PORT> root@<ADDRESS>:/root/hist_us_train/results/hist_us/hist_us_best.pt \
    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/

# 6c. 下载评估结果
scp -P <PORT> root@<ADDRESS>:/root/hist_us_train/results/hist_us/eval_results.json \
    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/

# 6d. 下载预测数据和训练历史
scp -P <PORT> root@<ADDRESS>:/root/hist_us_train/results/hist_us/predictions.pkl \
    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/
scp -P <PORT> root@<ADDRESS>:/root/hist_us_train/results/hist_us/train_ic_history.csv \
    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/
scp -P <PORT> root@<ADDRESS>:/root/hist_us_train/results/hist_us/valid_ic_history.csv \
    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/

# ===================== Step 7: 关机 =====================
# ⚠️ 重要: 在AutoDL控制台点击"关机"释放GPU资源!
# RTX 4090 按 ~1.29元/小时 计费, 用完即关
# 数据在 /root/autodl-tmp 中关机后仍保留, 下次开机可复用
