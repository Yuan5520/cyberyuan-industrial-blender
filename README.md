# CyberYuan 工业场景建模 Skill

**版本：0.2.0 · 作者：[CyberYuan / Yuan5520](https://github.com/Yuan5520)**

面向 Blender 与 Blender MCP 的工业设备、机加工单元和整厂建模工作流，适用于工业可视化与可交互数字孪生。

从图纸、照片和参考资料出发，统一比例与坐标，拆分可复用组件；逐组件完成参考检索、结构建模与验证，再装配并核对空间关系。

## 能力

- 工厂级建模：单位与坐标、组件分类、组件任务合同、独立制作、实例复用与总装核对。
- 参考驱动：区分确定尺寸、比例推导、参考估算与通用示意；资料缺失时保留估算依据。
- 工业结构：功能层级、固定结构合并、活动件轴心与随动、插入点与模块接口。
- 质量检查：基础及修改器求值网格、法线、重叠与退化几何、材质、导出与新进程回读。
- 可选组件委派：独立文件并行制作，共享实时 Blender 场景的写操作统一调度。

## 文件

| 路径 | 内容 |
|---|---|
| [SKILL.md](SKILL.md) | Skill 入口与建模流程 |
| [references/factory-workflow.md](references/factory-workflow.md) | 工厂级建模准则 |
| [references/component-job-contract.md](references/component-job-contract.md) | 组件任务、接口与交付合同 |
| [references/sources.md](references/sources.md) | 专业资料与外部方法来源 |
| [references/test-cases.md](references/test-cases.md) | 验证记录、测试场景与覆盖边界 |
| [scripts/audit_asset.py](scripts/audit_asset.py) | 在 Blender 内运行的只读资产审计 |
| [scripts/self_test.py](scripts/self_test.py) | 在隔离 Blender 后台进程运行的回归夹具 |
| [agents/openai.yaml](agents/openai.yaml) | Codex 界面元数据 |

## 安装与使用

使用、修改或分发前，请先阅读 [LICENSE](LICENSE) 并取得所需授权。获授权后可安装到个人 skills 目录：

```sh
git clone https://github.com/Yuan5520/cyberyuan-industrial-blender.git ~/.codex/skills/cyberyuan-industrial-blender
```

需要已配置的 Blender 与可用的 Blender MCP 连接。Skill 本身不会自动安装、升级插件或修改全局设置。审计和夹具脚本依赖 Blender Python，不能直接用系统 Python 代替运行。

调用示例：

```text
使用 $cyberyuan-industrial-blender 分析这份车间布局图，统一尺度与坐标，
按厂房、加工机柜、工件和辅助设施拆分组件，逐类检索参考并独立建模，
最后装配并检查占地、接口、运动空间与估算项。
```

验证应覆盖当前参考模型、导出文件和实际目标环境。历史隔离夹具的通过结果只证明对应测试范围；具体记录见 [测试场景](references/test-cases.md)。制造尺寸、机械安全及工程认证需要相应工程依据。

## 版权与来源

Copyright © 2026 CyberYuan. All rights reserved, to the extent of rights held by CyberYuan.

完整内容公开可读，采用保留权利的发布方式；具体范围见 [LICENSE](LICENSE) 和 [NOTICE.md](NOTICE.md)。GitHub 平台条款允许的浏览与 fork 等权利照其条款执行，其他使用授权请联系作者。

第三方软件、公开资料与通用建模方法的权利仍归相应权利人；来源记录保留在仓库中。引用项目时，请注明作者、版本及[仓库链接](https://github.com/Yuan5520/cyberyuan-industrial-blender)。署名本身不替代使用授权。

Industrial equipment and factory assembly workflows for Blender agents: shared scale and coordinates, reference-driven component modelling, reusable assets, spatial assembly checks, and bounded mesh/export validation.
