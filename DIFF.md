# 方案：Skill 系统 + Builtin 插件

## 新增内容

### 1. 框架内置插件（loyan/builtin/）
位置：loyan/builtin/
说明：随包分发，用户不能修改

内容：
- metadata.toml → 插件配置
- main.py → 入口
- modules/ → 功能模块
  - chat.py → /chat /ai
  - persona.py → /persona
  - help.py → /帮助 /菜单
  - system.py → /关机 /重启 /开机
  - about.py → /关于

### 2. Skill 系统（loyan/brain/skill/）
位置：loyan/brain/skill/
说明：Skill 基础设施

内容：
- base.py → Skill 基类
- registry.py → 注册表
- loader.py → 加载器
- decorator.py → 装饰器

### 3. 用户可覆盖版本（storage/plugins/builtin/）
位置：storage/plugins/builtin/
说明：用户可自定义，覆盖框架版本

内容：
- metadata.toml
- main.py

## 修改内容

.gitignore
- 新增：!storage/plugins/builtin/
- 新增：!storage/plugins/builtin/**

## 废弃内容

loyan/plugins/ → 删除
- Help_plugin/ → 迁移到 storage/plugins/
- Xiaoyu_plugin/ → 迁移到 storage/plugins/

## 统计

新增：12个文件，约550行
修改：1个文件，约5行
废弃：loyan/plugins/目录

## 原则

✓ 新增 Skill 系统
✓ builtin 有 modules 目录
✓ builtin 有 metadata.toml
✓ builtin 在 loyan/ 里（pip 包分发）
✓ Brain 不被背叛
