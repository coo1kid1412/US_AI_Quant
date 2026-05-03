# ACT_12: 配置富途OpenD网关

## 1. ACT概述

### 1.1 目标
配置富途OpenD网关，建立本地与富途服务器的加密通信通道，实现行情和交易指令的安全传输。

### 1.2 范围
- 下载并安装富途OpenD（Mac版）
- 配置RSA密钥对
- 配置OpenD连接参数（端口、登录信息）
- 测试OpenD与富途牛牛的通信

### 1.3 前置条件
- 富途牛牛客户端已安装并登录
- 已拥有富途账户
- Mac OS系统（Intel或Apple Silicon）

## 2. 详细需求

### 2.1 功能需求
- OpenD网关可正常启动
- RSA密钥对生成并配置正确
- OpenD与富途牛牛建立连接
- 端口监听正常（默认11111）

### 2.2 技术需求
- OpenD版本：最新稳定版
- RSA密钥：2048位
- 通信协议：TCP加密
- 配置文件：trdEnv（模拟/真实环境）

### 2.3 依赖项
- 富途牛牛客户端运行中
- 网络畅通（需连接富途服务器）
- RSA密钥生成工具（openssl）

## 3. 验收标准

### 3.1 完成定义
- [ ] OpenD网关已下载并安装
- [ ] RSA密钥对已生成
- [ ] OpenD配置文件已设置
- [ ] OpenD成功启动并监听端口
- [ ] OpenD与富途牛牛连接成功
- [ ] Review报告已编写

### 3.2 测试标准
```bash
# 1. 生成RSA密钥
openssl genrsa -out private.key 2048
openssl rsa -in private.key -pubout -out public.key

# 2. 检查端口监听
lsof -i :11111

# 3. Python连接测试
python -c "from futu import OpenQuoteContext; ctx = OpenQuoteContext(); print('连接成功')"
```

## 4. 注意事项

### 4.1 风险点
- **安全警告**：RSA私钥必须妥善保管，不可提交到Git仓库
- OpenD免费版仅支持模拟交易
- 同一账户只能在一个OpenD实例登录
- 长时间不操作会自动断开连接

### 4.2 常见问题
**Q: OpenD启动失败**
A: 
1. 检查端口是否被占用
2. 确认富途牛牛已登录
3. 查看OpenD日志排查错误

**Q: RSA密钥配置错误**
A: 
1. 确认密钥格式正确（PEM格式）
2. 确认公钥已在OpenD后台配置
3. 私钥路径在代码中配置正确

**Q: 连接后无法获取行情**
A: 
1. 确认订阅类型正确（K线、逐笔、报价等）
2. 检查订阅额度
3. 确认股票代码格式

### 4.3 最佳实践
- 使用模拟环境（SIMULATE）进行测试
- 生产环境使用环境变量存储密钥路径
- 定期更新OpenD到最新版本
- 监控OpenD运行状态，异常时自动重连

## 5. 参考资料
- OpenD配置指南：https://openapi.futunn.com/futu-api-doc/intro/FutuOpenDGuide.html
- RSA密钥生成：https://openapi.futunn.com/futu-api-doc/intro/APICertificate.html
- 常见问题FAQ：https://openapi.futunn.com/futu-api-doc/qa/
