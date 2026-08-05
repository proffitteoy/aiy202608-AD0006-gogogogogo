# RiskTrace Demo SQL Seed

本目录包含 9 份用于本地 demo 展示的事件补充 SQL。

这些 SQL 以 [`demo/scenarios/energy-transition/seed_energy_rally_social_opinions.sql`](/F:/RiskTrace/demo/scenarios/energy-transition/seed_energy_rally_social_opinions.sql) 为模板生成，统一做了以下约束：

- 仅适用于 demo tenant `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`
- 仅补充模拟社交帖子与模拟观点归因，不改写原始事件主体
- 所有新增记录均显式标记 `simulated`、`manual_demo_seed`、`internal_demo_only`
- 通过 `(tenant_id, platform, source_id)` 幂等 upsert `raw_documents`
- 重建对应事件下这批 `demo-manual-v1 / seed-20260805` 的 `opinion_records`

## 已绑定真实事件

| 文件 | event_id |
| --- | --- |
| `event01_energy_forum.sql` | `59ca0f47-482d-4087-93ac-1d53b421caec` |
| `event02_realestate_whitelist.sql` | `17c948f5-7aef-474e-9bb2-1a7ef2e45d72` |
| `event03_realestate_delivery.sql` | `d45648f1-b09b-4119-aeb3-932534c79752` |
| `event04_pbc_policy.sql` | `3ea356d1-922f-4182-884c-bb2e0dcffd0a` |
| `event05_bank_npl.sql` | `7c6199a0-2a2c-434c-892a-45f4ca3d67bd` |
| `event06_deepseek_bank.sql` | `d6c8ee46-2ec3-432b-b43c-a6c6cb88370e` |
| `event07_deepseek_privacy.sql` | `e2f2e0ba-bd6d-4cf0-b41a-6e1ca6444fbf` |
| `event08_realestate_outlook.sql` | `bcc8d804-3281-43b3-9ed3-0c54bb2b5595` |
| `event09_deepseek_moment.sql` | `8542aadd-38cc-4b0e-9993-05ea4be6d9ee` |

## 已验证执行命令

从仓库根目录执行：

```powershell
Get-ChildItem demo\scenarios\energy-transition\risktrace_seed\*.sql |
  Sort-Object Name |
  ForEach-Object {
    & 'D:\PostgreSQL\bin\psql.exe' `
      -w -h 127.0.0.1 -p 55432 -U risktrace -d risktrace `
      -v ON_ERROR_STOP=1 `
      -f $_.FullName
  }
```

## 当前核验结果

已查库确认，上述 9 个事件每个都已补齐：

- `documents = 6`
- `social_documents = 5`
- `opinions = 5`
