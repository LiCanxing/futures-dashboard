# Task: Iwencai CLI + news-search 技能安装

**时间**: 2026-05-22 22:01 GMT+8
**目标**: 安装 Iwencai SkillHub CLI 和 news-search 技能，配置环境变量

## 执行结果

1. **Iwencai SkillHub CLI**: 已安装到 `/Users/licanxing/.local/bin/iwencai-skillhub-cli`
   - 从 `https://www.iwencai.com/skillhub/static/0.0.4/` 下载安装
   - 安装脚本解压过程中遇到路径问题，手动解压后执行 `iwencai-install.sh` 解决

2. **news-search 技能**: 已安装到 `~/.openclaw/workspace/skills/news-search/`
   - 通过 `iwencai-skillhub-cli install news-search` 安装
   - 财经资讯搜索引擎，覆盖官媒、主流财经媒体、垂直行业网站

3. **环境变量**: 已存在于 `~/.zshrc`
   - `IWENCAI_BASE_URL=https://openapi.iwencai.com`
   - `IWENCAI_API_KEY` 已配置
