# 华强北元器件价格监控

监控立创商城、华强北网(ICSMART)、Allchips、云汉芯城等平台的元器件报价与变化，
SQLite 存储历史，自动检测涨跌幅并告警，Rich 终端报表展示。

## 快速开始

```bash
pip install -r requirements.txt
python main.py init                      # 初始化 + 导入默认型号
python main.py fetch STM32F103C8T6       # 抓取一次
python main.py price STM32F103C8T6       # 看各来源最新报价(按价格升序)
python main.py history STM32F103C8T6     # 价格历史
python main.py alerts                    # 价格变化告警
python main.py watch --interval 30       # 每30分钟定时监控
```

## 解析架构(配置化 + 多策略)

针对电商站点 **JS 动态渲染 / 反爬** 的现实，解析与抓取解耦：

```
抓取(rule_scraper) ── API JSON ┐
                                ├─► 解析引擎(parser) ── 内嵌JSON(__NEXT_DATA__等)
搜索页 HTML ────────────────────┘                    ── XHR/API JSON
                                                      ── DOM 选择器(兜底)
```

- **`parse_rules.py`** — 各站点的「字段候选键 / CSS 选择器」声明式配置。**校准只改这里，不动代码。**
- **`parser.py`** — 纯函数解析引擎（不碰网络），含递归商品数组定位、阶梯价处理。
- **反爬检测** — 自动识别网络策略/WAF 拦截、验证码页、JS 挑战页，给出明确诊断并优雅降级。

### 用 fixture 测试台校准真实站点

线上结构会变，无需联网即可校准：

```bash
# 1. 浏览器 F12 采集真实样本(XHR 的 JSON 或整页 HTML), 存到 tests/fixtures/
# 2. 在 tests/test_parsers.py 加一条用例指向该样本
# 3. 跑测试, 不对就改 parse_rules.py 的候选键/选择器, 重跑
pytest tests/test_parsers.py -q
```

详见 `tests/fixtures/README.md`。

## 注意

- 这些站点多为 JS 渲染且有反爬，`parse_rules.py` 内是**基于常见约定的候选规则**，
  真实抓取前请用 fixture 测试台按线上实际结构校准。
- 若运行环境的网络策略未放行目标域名，抓取会返回 `Host not in allowlist` 类拦截，
  需在本地或放行了对应域名的环境下运行。

## 测试

```bash
pytest tests/ -q     # 45 个用例: 存储/告警 + 解析引擎 fixture 测试
```
