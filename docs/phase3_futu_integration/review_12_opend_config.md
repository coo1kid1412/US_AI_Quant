# Review Report: ACT_12 - 配置富途OpenD网关

## 验收状态: PASS

## 1. 验收概要

| 项目 | 内容 |
|------|------|
| ACT编号 | ACT_12 |
| ACT名称 | 配置富途OpenD网关 |
| 验收日期 | 2026-05-03 |
| 验收结果 | PASS |

## 2. 配置环境

| 组件 | 版本/信息 |
|------|-----------|
| FutuOpenD | 10.4.6408 |
| 应用路径 | /Applications/Futu_OpenD.app |
| 监听地址 | 127.0.0.1:11111 |
| 牛牛号 | 7952365 |
| 加密模式 | 禁用（无加密） |
| 时区 | UTC+8 |

## 3. 配置步骤

### 3.1 RSA密钥生成
```bash
mkdir -p ~/.futu/keys
openssl genrsa -out ~/.futu/keys/private.key 2048
openssl rsa -in ~/.futu/keys/private.key -pubout -out ~/.futu/keys/public.key
```

### 3.2 OpenD CLI配置
- 登录方式：牛牛号 + 密码
- 监听地址：127.0.0.1
- 监听端口：11111
- 加密私钥：**留空**（关键配置）
- 期货交易API时区：UTC+8

### 3.3 关键发现：加密配置
**问题**：配置加密私钥后，Python SDK连接出现 `ProtobufBody Parse Err!` 和 `Send Packet Encrypt Failed`

**根因**：Python SDK与OpenD的加密设置必须一致。当OpenD配置了加密私钥，Python端需要 `SysConfig.enable_proto_encrypt(True)` + `SysConfig.set_init_rsa_file()`；反之都不配置。

**解决方案**：双端均不配置加密（OpenD CLI的"加密私钥"留空 + Python端 `SysConfig.enable_proto_encrypt(False)`）

## 4. 验证结果

| 验证项 | 结果 | 说明 |
|--------|------|------|
| OpenD启动 | PASS | CLI界面正常显示，端口11111监听 |
| TCP连通性 | PASS | `socket.connect_ex(('127.0.0.1', 11111))` 返回0 |
| 协议握手 | PASS | Python SDK成功建立连接 |
| 行情上下文 | PASS | OpenQuoteContext初始化成功 |
| 交易上下文 | PASS | OpenSecTradeContext初始化成功 |
| 交易解锁 | PASS | 模拟交易解锁成功 |

## 5. 注意事项

1. FutuOpenD（独立应用）与富途牛牛内置OpenAPI是两个独立组件
2. 必须先启动富途牛牛并登录，再启动FutuOpenD
3. 每次重启OpenD后需要重新解锁交易
4. protobuf版本需降级至4.x以确保兼容性
