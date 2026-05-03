# ACT_06: 安装Qlib框架

## 1. ACT概述

### 1.1 目标
验证Qlib框架已正确安装，确保可以在Mac OS上正常使用。

### 1.2 范围
- 验证pyqlib安装
- 验证Qlib导入
- 记录版本信息

### 1.3 前置条件
- Phase 1已完成
- Python虚拟环境已激活

## 2. 详细需求

### 2.1 功能需求
- Qlib 0.9.7已安装
- `import qlib` 无错误

### 2.2 验收标准
```bash
python -c "import qlib; print(f'Qlib {qlib.__version__} OK')"
```

## 3. 验收标准

### 3.1 完成定义
- [ ] Qlib导入成功
- [ ] 版本号正确（0.9.7）
- [ ] Review报告已编写

## 4. 注意事项

### 4.1 风险点
- 已完成安装，本ACT主要是验证
