#!/bin/bash
# ============================================================
# AutoDL 环境部署脚本 - US_AI_Quant HIST模型
# ============================================================
# 用法: SSH登录AutoDL后, cd /root/hist_us_train && bash autodl_setup_us.sh
# ============================================================

set -e

echo "========================================="
echo "  AutoDL 环境部署 - US HIST模型"
echo "========================================="

# 1. Python环境
echo ""
echo "[1/5] 检查Python环境..."
if command -v python3 &>/dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi
PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "  Python: $PYTHON_VERSION"

# 2. 安装依赖
echo ""
echo "[2/5] 安装依赖..."
$PYTHON -m pip install --upgrade pip -q

echo "  -> pyqlib..."
pip install pyqlib -q 2>/dev/null || pip install pyqlib --break-system-packages -q

echo "  -> torch (跳过如已安装)..."
$PYTHON -c "import torch; print('  torch已安装:', torch.__version__)" 2>/dev/null || \
    pip install torch torchvision torchaudio -q

echo "  -> 其他依赖..."
pip install pandas numpy -q

echo "  依赖安装完成"

# 3. 验证数据
echo ""
echo "[3/5] 验证数据..."
US_DATA="$HOME/.qlib/qlib_data/us_data"
if [ ! -d "$US_DATA" ]; then
    echo "ERROR: US数据不存在: $US_DATA"
    echo "请先解压: tar -xzf qlib_us_data_*.tar.gz -C ~/.qlib/qlib_data/"
    exit 1
fi

US_STOCKS=$(ls "$US_DATA/features/" | wc -l)
echo "  US数据: $US_DATA ($US_STOCKS 只股票)"

# 检查概念数据
CONCEPT_DIR="$(pwd)/data/hist"
if [ ! -f "$CONCEPT_DIR/stock2concept_sp500.npy" ]; then
    echo "ERROR: 概念矩阵不存在: $CONCEPT_DIR/stock2concept_sp500.npy"
    exit 1
fi
echo "  概念数据: OK"

# 4. 验证GPU + 环境
echo ""
echo "[4/5] 验证GPU环境..."
$PYTHON -c "
import torch
import numpy as np
import pandas as pd

print('  torch:', torch.__version__)
print('  numpy:', np.__version__)
print('  pandas:', pd.__version__)
print('  CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('  GPU:', torch.cuda.get_device_name(0))
    mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print('  显存: %.1f GB' % mem)
else:
    print('  WARNING: 无GPU, 将使用CPU训练(很慢)')

import qlib
print('  qlib: OK')
"

# 5. 验证训练脚本
echo ""
echo "[5/5] 验证训练脚本..."
if [ ! -f "scripts/train_hist_us.py" ]; then
    echo "ERROR: 训练脚本不存在"
    exit 1
fi
if [ ! -f "src/research/model/us_alpha_handler.py" ]; then
    echo "ERROR: 自定义handler不存在"
    exit 1
fi
echo "  训练脚本: OK"
echo "  自定义handler: OK"

# 生成快速训练脚本
cat > train_quick.sh << 'TRAINEOF'
#!/bin/bash
echo "开始训练 US HIST模型..."
python autodl_train_us.py --epochs 100 --early-stop 15 --gpu 0

echo ""
echo "训练完成！"
echo "模型: results/hist_us/hist_us_best.pt"
echo "结果: results/hist_us/eval_results.json"
echo ""
echo "下载到本地Mac:"
echo "scp -P <端口> root@<IP>:/root/hist_us_train/results/hist_us/hist_us_best.pt \\"
echo "    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/"
echo "scp -P <端口> root@<IP>:/root/hist_us_train/results/hist_us/eval_results.json \\"
echo "    ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/"
TRAINEOF
chmod +x train_quick.sh

echo ""
echo "========================================="
echo "  部署完成!"
echo "========================================="
echo ""
echo "开始训练:"
echo "  bash train_quick.sh"
echo "  或: python autodl_train_us.py --epochs 100 --gpu 0"
echo ""
echo "训练完成后记得下载模型并关机!"
echo ""
