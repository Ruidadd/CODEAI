# 解析 fixture 测试台

把**真实页面样本**存到这里, 跑 `pytest tests/test_parsers.py` 即可离线校准
解析规则, 无需联网、无需绕过反爬。

## 怎么采集真实样本

由于这些站点多为 JS 渲染 + 反爬, 推荐用浏览器开发者工具采集:

### 1. JSON 接口样本(最优先)
打开站点搜索某型号 → F12 → Network → XHR 标签 → 找到返回商品列表的请求
→ 右键 Copy → Copy response → 存为 `tests/fixtures/<source>_api.json`

### 2. 内嵌 JSON / 整页 HTML 样本
F12 → Network → Doc → 选中文档请求 → Copy response, 或浏览器"另存为网页(仅HTML)"
→ 存为 `tests/fixtures/<source>_search.html`
(适用于 Next.js `__NEXT_DATA__`、Nuxt `__NUXT__` 等内嵌数据的站点)

## 校准流程

1. 采集样本放入本目录
2. 在 `test_parsers.py` 仿照现有用例加一条, 指定 fixture 文件 + 对应站点 rule
3. 跑测试看解析出的 PriceInfo 是否正确
4. 不对就调 `huaqiangbei_monitor/parse_rules.py` 里该站点的候选键 / 选择器, 重跑
5. 全绿后, 真实抓取(在能联网的环境)即可复用同一套规则

> 当前目录下的 `*_sample.*` 是**演示用合成样本**, 仅证明解析引擎工作正常,
> 字段结构未必与线上一致 —— 请用真实采集样本替换后再做生产抓取。
