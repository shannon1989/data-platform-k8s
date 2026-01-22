PlantUML Style Guide (Server Render)

1. Use single-line macros only.
2. Do NOT break macro parameters into multiple lines.
3. Always include @startuml / @enduml.
4. Prefer PlantUMLServer render in VS Code.
5. Local render only if complex macro syntax is required.


```plantuml
@startuml C4_Elements
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml


Person(user, "Data Engineer / Analyst", "Consumes on-chain analytics data")

System_Ext(chain, "Blockchain Network", "Ethereum / BSC / Sui RPC")

System(system, "On-chain Data Platform", "RPC Sliding Window + Kafka + Commit Coordinator")

System_Ext(bi, "BI / Analytics", "Metabase / SQL / Dashboards")

Rel(user, bi, "Queries")
Rel(bi, system, "Reads committed data")
Rel(system, chain, "Fetches blocks / logs")

@enduml
```
