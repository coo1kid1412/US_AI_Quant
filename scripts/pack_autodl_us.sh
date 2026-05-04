#!/bin/bash
# ============================================================
# US_AI_Quant AutoDL 数据打包脚本
# ============================================================
# 打包内容:
#   1. US stock qlib数据 (~450MB压缩后~120MB)
#   2. HIST概念矩阵数据 (stock2concept + stock_index)
#   3. 训练代码 (scripts + src/research/model)
#
# 用法: bash scripts/pack_autodl_us.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$PROJECT_DIR/autodl_package"

echo "========================================="
echo "  US_AI_Quant AutoDL 数据打包"
echo "========================================="

# ---------- 1. 检查数据 ----------
echo ""
echo "[1/4] 检查数据..."
QLIB_US_DATA="$HOME/.qlib/qlib_data/us_data"
CONCEPT_DIR="$PROJECT_DIR/data/hist"

if [ ! -d "$QLIB_US_DATA" ]; then
    echo "ERROR: US stock数据不存在: $QLIB_US_DATA"
    exit 1
fi

if [ ! -f "$CONCEPT_DIR/stock2concept_sp500.npy" ]; then
    echo "ERROR: 概念矩阵不存在，请先运行:"
    echo "  python scripts/build_us_concept_data.py --market sp500"
    exit 1
fi

US_SIZE=$(du -sh "$QLIB_US_DATA" | cut -f1)
echo "  US stock数据: $US_SIZE ($QLIB_US_DATA)"
echo "  概念矩阵: $CONCEPT_DIR"

# ---------- 2. 创建输出目录 ----------
echo ""
echo "[2/4] 创建打包目录..."
mkdir -p "$OUTPUT_DIR"

# ---------- 3. 打包qlib US数据 ----------
echo ""
echo "[3/4] 打包数据..."

# 3a. qlib US数据
echo "  打包US stock数据..."
US_PACK="$OUTPUT_DIR/qlib_us_data_${TIMESTAMP}.tar.gz"
tar -czf "$US_PACK" -C "$HOME/.qlib/qlib_data" us_data
US_PACK_SIZE=$(du -sh "$US_PACK" | cut -f1)
echo "  -> $US_PACK_SIZE"

# 3b. 概念矩阵 + 训练代码打包
echo "  打包训练代码和概念数据..."
CODE_PACK="$OUTPUT_DIR/hist_us_code_${TIMESTAMP}.tar.gz"

# 创建临时目录结构
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/hist_us_train/src/research/model"
mkdir -p "$TMPDIR/hist_us_train/data/hist"
mkdir -p "$TMPDIR/hist_us_train/scripts"
mkdir -p "$TMPDIR/hist_us_train/results/hist_us"

# 复制训练代码
cp "$PROJECT_DIR/scripts/train_hist_us.py" "$TMPDIR/hist_us_train/scripts/"
cp "$PROJECT_DIR/src/research/model/us_alpha_handler.py" "$TMPDIR/hist_us_train/src/research/model/"
touch "$TMPDIR/hist_us_train/src/__init__.py"
touch "$TMPDIR/hist_us_train/src/research/__init__.py"
touch "$TMPDIR/hist_us_train/src/research/model/__init__.py"

# 复制概念数据
cp "$CONCEPT_DIR/stock2concept_sp500.npy" "$TMPDIR/hist_us_train/data/hist/"
cp "$CONCEPT_DIR/stock_index_sp500.npy" "$TMPDIR/hist_us_train/data/hist/"
cp "$CONCEPT_DIR/concept_meta_sp500.json" "$TMPDIR/hist_us_train/data/hist/" 2>/dev/null || true

# 复制AutoDL脚本
cp "$PROJECT_DIR/scripts/autodl_setup_us.sh" "$TMPDIR/hist_us_train/" 2>/dev/null || true
cp "$PROJECT_DIR/scripts/autodl_train_us.py" "$TMPDIR/hist_us_train/" 2>/dev/null || true

tar -czf "$CODE_PACK" -C "$TMPDIR" hist_us_train
rm -rf "$TMPDIR"

CODE_PACK_SIZE=$(du -sh "$CODE_PACK" | cut -f1)
echo "  -> $CODE_PACK_SIZE"

# ---------- 4. 生成说明 ----------
echo ""
echo "[4/4] 生成上传说明..."

cat > "$OUTPUT_DIR/AUTODL_INSTRUCTIONS.txt" << EOF
=============================================
  US_AI_Quant AutoDL GPU训练部署说明
=============================================
打包时间: $(date '+%Y-%m-%d %H:%M:%S')

文件清单:
  1. qlib_us_data_${TIMESTAMP}.tar.gz ($US_PACK_SIZE) - US stock数据
  2. hist_us_code_${TIMESTAMP}.tar.gz ($CODE_PACK_SIZE) - 训练代码+概念数据

====== AutoDL操作步骤 ======

Step 1: 创建实例
  - 平台: https://www.autodl.com
  - 镜像: PyTorch 2.0+ / Python 3.10+
  - 推荐GPU: RTX 4090 (24GB, ~1.29元/时)
  - 预计训练时间: 100 epochs ~25分钟

Step 2: 上传数据 (选一种方式)
  方式A - scp上传:
    scp -P <端口> $US_PACK root@<IP>:/root/
    scp -P <端口> $CODE_PACK root@<IP>:/root/
  
  方式B - AutoDL网盘上传后在实例内复制

Step 3: SSH登录实例
    ssh -p <端口> root@<IP>

Step 4: 解压和部署
    # 解压US数据
    mkdir -p ~/.qlib/qlib_data
    tar -xzf /root/qlib_us_data_${TIMESTAMP}.tar.gz -C ~/.qlib/qlib_data/

    # 解压训练代码
    tar -xzf /root/hist_us_code_${TIMESTAMP}.tar.gz -C /root/

    # 安装依赖
    cd /root/hist_us_train
    bash autodl_setup_us.sh

Step 5: 开始训练
    cd /root/hist_us_train
    python autodl_train_us.py --epochs 100 --early-stop 15 --gpu 0

Step 6: 下载结果 (在本地Mac执行)
    scp -P <端口> root@<IP>:/root/hist_us_train/results/hist_us/hist_us_best.pt \\
        ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/
    scp -P <端口> root@<IP>:/root/hist_us_train/results/hist_us/eval_results.json \\
        ~/WorkSpace/QoderWorkspace/US_AI_Quant/results/hist_us/

Step 7: 关机
    ⚠️ 训练完成后立即关机释放实例! (按小时计费)
=============================================
EOF

echo ""
echo "========================================="
echo "  打包完成!"
echo "========================================="
echo ""
echo "  US数据包:  $US_PACK ($US_PACK_SIZE)"
echo "  代码包:    $CODE_PACK ($CODE_PACK_SIZE)"
echo "  操作说明:  $OUTPUT_DIR/AUTODL_INSTRUCTIONS.txt"
echo ""
echo "下一步: 上传到AutoDL并按说明操作"
echo ""
