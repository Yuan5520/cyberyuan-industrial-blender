# 来源与取舍

调研日期：2026-10-28。以下是编写依据，不是运行时指令或自动安装清单。具体 Blender API 与导出选项仍需按使用环境核验。

## 专业与第一方资料

| 来源 | 本 skill 采用的要点 |
|---|---|
| [Blender Clean Up](https://docs.blender.org/manual/en/latest/modeling/meshes/editing/mesh/cleanup.html) | 去重、松散几何、退化面各有不同作用，避免把一个清理工具当作全面修复 |
| [Blender Editing Normals](https://docs.blender.org/manual/en/5.1/modeling/meshes/editing/mesh/normals.html) | 面朝向与自定义着色法线区分，结合 Face Orientation 检查 |
| [Blender Weighted Normal](https://docs.blender.org/manual/en/5.0/modeling/modifiers/normals/weighted_normal.html) | 加权法线用于着色控制，不能修复几何缺陷 |
| [Blender Mesh Analysis](https://docs.blender.org/manual/en/latest/modeling/meshes/mesh_analysis.html) | 厚度、相交与非平面面片检查；内置分析有范围与性能限制，且很多规则面向打印 |
| [Blender Join](https://docs.blender.org/UATEST/manual/en/dev/scene_layout/object/editing/join.html) | 合并对象保留多种数据，但输入修改器/约束/父级不会自动得到正确处理 |
| [Blender Parenting](https://docs.blender.org/manual/en/5.0/scene_layout/object/editing/parent.html) | 父级变换传播、父逆矩阵与局部坐标 |
| [Blender glTF](https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html) | 交换材质、节点转换和实际导出能力需要独立验证 |
| [Blender glTF 网格说明](https://docs.blender.org/manual/en/3.2/addons/import_export/scene_gltf2.html) | UV/法线不连续会产生导出顶点拆分，不自动代表坏网格 |
| [Adobe The PBR Guide, Part 2](https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2) | 金属/粗糙度工作流、表面涂层、真实反射与颜色信息 |
| [Adobe Color Management](https://experienceleague.adobe.com/en/docs/substance-3d/ecosystem/renderers/color-management/color-management) | 颜色与非颜色数据贴图的不同处理 |
| [Jonathan Lampel / CG Cookie](https://www.cgcookie.com/courses/core-fundamentals-mesh-modeling) | 依据用途判断拓扑、真实尺寸、灰模比例与硬表面方法。只读取公开课程说明，未声称观看付费课程 |
| [Thiago Klafke 模块化环境](https://www.thiagoklafke.com/tutorials/modular-environments/) | 模块接点、网格基准、枢轴和复用；不照搬旧引擎格式和固定尺寸体系 |
| [fSpy 教程](https://fspy.io/tutorial/) | 透视相机匹配与已知尺寸锚点；不把单张照片当正交图 |
| [Khronos 深度精度说明](https://wikis.khronos.org/opengl/Depth_Buffer_Precision) | 共面表面与深度精度都可能造成 Z-fighting，需要查明原因 |
| [OpenUSD Model Hierarchy](https://openusd.org/release/glossary.html#model-hierarchy) | 用组件和总装组织可理解的大型场景；这里只借鉴思想，不要求安装 USD 流程 |

## 公开 agent skills 与 MCP

| 来源 | 借鉴 | 没有照搬的部分 |
|---|---|---|
| [CheshireJCat/create-3d-model-skill](https://github.com/CheshireJCat/create-3d-model-skill/blob/main/skills/create-3d-model/SKILL.md) | 输入分类、场景范围、灰模与多视角检查、分段修改、导出回读 | 覆盖全部 3D 门类的路由规模和固定命名前缀 |
| [EL4CTEO 硬表面](https://github.com/EL4CTEO/blender-skills/blob/main/skills/blender-hardsurface-modeling/SKILL.md) | 按用途选择 mid-poly、烘焙或细分，轮廓先行 | 固定比例倒角、通用面数与绝对化拓扑规则 |
| [EL4CTEO 资产检查](https://github.com/EL4CTEO/blender-skills/blob/main/skills/blender-asset-qa/SKILL.md) | 数字检查加视觉检查、检查修改器求值结果 | 统一距离容差、把所有不接触都判错、统一填洞/焊接、跳过检查视作完成 |
| [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill/blob/main/plugin/skills/blender-modeling/SKILL.md) | 小段执行、结构化反馈、按任务加载专业流程 | 通用固定倒角/细分配方、用穿插掩盖所有接缝、将 Delete Loose 当作内部面修复 |
| [Wonham/blender-cli-modeling](https://github.com/Wonham/blender-cli-modeling/blob/main/SKILL.md) | MCP 交互与新进程回读互补 | 自动更改用户偏好或固定软件版本要求 |
| [MCP for Blender](https://github.com/ahujasid/mcp-for-blender) | 读取现场工具能力、执行 bpy、观察结果 | 安装/升级命令和外部生成服务不作为建模的默认前置 |

上游仓库自述的效果或测试数量不是本 skill 的验证结果。这里只吸收方法并编写独立规则与检查脚本；没有直接复制上游程序。

## 工厂级流程增补依据

调研日期：2026-10-29。采用“布局约束 + 独立组件 + 总装复核”的方法，不引入 SOLIDWORKS、Inventor、USD 或游戏引擎作为默认依赖。部分官方帮助直接打开只返回外壳或抓取错误，对应要点同时核对官方搜索索引正文；不将资料审读说成已操作这些软件。

| 第一方来源 | 采用的要点与迁移边界 |
|---|---|
| [SOLIDWORKS Design Methods](https://help.solidworks.com/2024/english/SolidWorks/sldworks/c_Design_Methods.htm) / [Assembly Layout Sketch](https://help.solidworks.com/2021/english/SolidWorks/sldworks/c_Assembly_Layout_Sketch.htm) | 结合自上而下布局约束与自下而上组件复用；Blender 无须照搬全约束草图、特征历史或 CAD 配合求解 |
| [Blender Scene Properties](https://docs.blender.org/manual/en/latest/scene_layout/scene/properties.html) | 区分单位显示与实际几何/行为；明确换算，另做尺度与导出验证 |
| [Autodesk Factory Landing Surfaces](https://help.autodesk.com/cloudhelp/2022/ENU/FDU/files/Inventor-Factory-Help/About-Creating-Factory-Assets/To-Create-Assets/FDU_Inventor_Factory_Help_About_Creating_Factory_Assets_To_Create_Assets_To_Define_Landing_Surfaces_html.html) / [Create Factory Assets Reference](https://help.autodesk.com/cloudhelp/2023/ENU/FDU/files/Inventor-Factory-Help/About-Creating-Factory-Assets/To-Create-Assets/To-Create-Factory-Assets/FDU_Inventor_Factory_Help_About_Creating_Factory_Assets_To_Create_Assets_To_Create_Factory_Assets_Create_Factory_Assets_Reference_html.html) | 落地面、插入点和连接点分别负责姿态、定位与对接；不要求统一包围盒中心原点 |
| [SOLIDWORKS Assembly Envelopes](https://help.solidworks.com/2022/English/SolidWorks/sldworks/c_Assembly_Envelopes.htm) / [Inventor Simplify](https://help.autodesk.com/cloudhelp/2026/ENU/Inventor-Help/files/SIMPLIFY-PART.htm) | 包络可作参考/简化表达；结合工厂任务区分占地、运动与检修范围是本 skill 的应用归纳，不是统一安全净距标准 |
| [SOLIDWORKS Interference Detection](https://help.solidworks.com/2025/English/SolidWorks/sldworks/t_detecting_interferences.htm) / [Clearance Verification](https://help.solidworks.com/2026/English/SolidWorks/sldworks/HIDD_DVE_CLEARANCE.htm) / [Dynamic Clearance](https://help.solidworks.com/2023/english/SolidWorks/sldworks/t_Dynamic_Clearance_SWassy_probs.htm) | 实体重叠、最小间隙和运动中的间隙是不同检查；Blender 的 AABB 或离散姿态不等于精确实体或连续全行程验证 |
| [Blender Collection Instancing](https://docs.blender.org/manual/en/latest/scene_layout/object/properties/instancing/collection.html) / [OpenUSD Model Hierarchy](https://openusd.org/release/glossary.html#model-hierarchy) | 同型资产复用和有意义的组件/总装边界；实例实化、导出后重查父子层级和接口，不强制采用 USD |
| [Unreal FBX Static Mesh Pipeline](https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine) | 明确导出枢轴、模型/碰撞/接口职责及导入验证；引擎专属命名与版本仅在该引擎确为目标时使用 |

### 实际审读的 SolidWorks agent skills

以下公开文件已实际读取，作为外部方法参考，未安装、执行或直接复制其脚本。前两项核查到 MIT；第三项未确认许可，仅归纳设计思路。

| 文件与许可 | 借鉴与不采用的内容 |
|---|---|
| [wzyn20051216/solidworks-automation-skill](https://github.com/wzyn20051216/solidworks-automation-skill/blob/main/SKILL.md) · [MIT](https://github.com/wzyn20051216/solidworks-automation-skill/blob/main/LICENSE) | 参考资料、数值与图像证据、建模/装配/导出分别验证；不引入其本机路径、安装或运行会话假设 |
| [kbedrich/solidworks-agent](https://github.com/kbedrich/solidworks-agent/blob/main/skills/solidworks/SKILL.md) · [MIT](https://github.com/kbedrich/solidworks-agent/blob/main/LICENSE) | 单位/接口/未知项先行，逐步构建、测量、保存和回读；不把 CAD 多实体策略变成按材质拆散 Blender 刚性 Mesh |
| [jianjwu/codex_to_solidworks](https://github.com/jianjwu/codex_to_solidworks/blob/main/skills/solidworks-ai-modeling/SKILL.md) · 未确认许可 | 先判断构造类型和主体，再孔槽/阵列，最后处理倒角细节；不直接复制指令、宏或代码，不照搬全约束草图门槛 |

审读时三个文件的 blob SHA 依次为 `3c8b6488ddcf42a87d3baa4fd72054d0160680fc`、`3b0843ce1ad380d0a30f7a77536cde93d8ba174b`、`6352e543e99d8f35e9ae27bc36212c555bda63b8`。这是文件内容标识，不是对其软件实测结果的背书。

## 本次会话明确的用户要求

参考图片和真实尺度先行；先纠正结构再做材质；关注正反视图、非对称性、护罩数量、附件与连接完整性；复用现成机械臂；地轨等使用可拼接模块；运动件独立；相对固定结构合并为 Mesh；总装按功能分层，避免几百个直接子物体；导出原点清楚；排查重复点面、反向面与异常碎片；纯模型与灯光/运行脚本区分交付。

这些要求已经抽象为通用工作方式，不保留任何具体开发项目的路径、尺寸、对象数量或修改授权。

2026-10-29 增补的明确要求：工厂先按统一比例拆成组件级独立制作；可委派子代理，每类都执行参考检索等完整流程；找不到指定外形时使用通用组件并记录估算；最后核对空间关系组成整体。现场 DWG 经验用于补充来源/单位矛盾、符号数量语义、非正交边界、局部原点和并行写入边界，不把个案数值设为默认标准。
